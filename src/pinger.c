// SPDX-License-Identifier: GPL-2.0
/*
 * pinger.c - the "light task" whose QoS the partition is supposed to protect.
 *
 * Wakes on a fixed period, records how late the wakeup was, then does a fixed
 * amount of arithmetic and records how long that took. Two distributions come
 * out of it:
 *
 *   wake_us  - scheduling latency. Degrades when the domain the task is placed
 *              in is oversubscribed, or when it queues behind a 20 ms slice.
 *   work_us  - service time for a fixed quantum of work. Degrades when the CPU
 *              it landed on is clocked low. This is the direct cost of putting
 *              a latency-sensitive task on a high-EPP "little" core.
 *
 * Reporting both separates the two ways a placement policy can hurt an
 * interactive task, which a single "responsiveness" number would conflate.
 *
 * The work loop is a dependent-FP chain: it does not vectorise, it does not
 * fit in a store buffer, and its rate tracks core frequency almost exactly, so
 * work_us is a usable in-band frequency probe that needs no MSR access.
 */
#define _GNU_SOURCE
#include <errno.h>
#include <getopt.h>
#include <math.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <signal.h>
#include <time.h>
#include <unistd.h>

/*
 * The harness runs the pinger alongside a build of unknown duration and stops
 * it with SIGTERM when the build finishes. Handling the signal (rather than
 * dying on it) is what lets the measurement window be exactly the workload
 * window instead of a fixed guess padded with idle.
 */
static volatile sig_atomic_t stop_now;

static void on_stop(int sig)
{
	(void)sig;
	stop_now = 1;
}

static int cmp_double(const void *a, const void *b)
{
	double x = *(const double *)a, y = *(const double *)b;
	return (x > y) - (x < y);
}

static double pct(double *sorted, long n, double p)
{
	double idx;
	long i;

	if (n <= 0)
		return NAN;
	idx = p / 100.0 * (n - 1);
	i = (long)idx;
	if (i >= n - 1)
		return sorted[n - 1];
	return sorted[i] + (idx - i) * (sorted[i + 1] - sorted[i]);
}

static void emit(const char *name, double *v, long n)
{
	double mean = 0;

	qsort(v, n, sizeof(*v), cmp_double);
	for (long i = 0; i < n; i++)
		mean += v[i];
	mean = n ? mean / n : NAN;

	printf(",\"%s_mean\":%.2f,\"%s_p50\":%.2f,\"%s_p90\":%.2f,"
	       "\"%s_p99\":%.2f,\"%s_p999\":%.2f,\"%s_max\":%.2f",
	       name, mean, name, pct(v, n, 50), name, pct(v, n, 90),
	       name, pct(v, n, 99), name, pct(v, n, 99.9), name, pct(v, n, 100));
}

/*
 * Dependent double-precision FMA chain: one iteration per FMA latency, no ILP
 * for the machine to exploit, so the rate is a clean function of core clock.
 *
 * `sink` is volatile and written on every call: without it the whole loop is
 * pure and -O2 deletes it, which silently turns the benchmark into a timer
 * calibration of nothing. (It did, on the first run.)
 */
static volatile double sink;

static void burn(long iters)
{
	double x = 1.000000001;

	for (long i = 0; i < iters; i++)
		x = x * 1.0000000001 + 1e-12;
	sink = x;
}

/*
 * Calibrate iterations so one work quantum takes roughly `target_us` *at full
 * clock*. The 300 ms warm burn first is essential: calibrating straight out of
 * idle measures the 400 MHz ramp-up floor, and every later sample then looks
 * artificially fast. With the warm-up in place, `work_us / target_work_us` is
 * a direct ratio of "clock this task actually got" to "clock the machine can
 * deliver", which is the number the whole EPP question turns on.
 */
static long calibrate(double target_us)
{
	long iters = 1000;
	double warm_end;
	struct timespec w;

	clock_gettime(CLOCK_MONOTONIC, &w);
	warm_end = w.tv_sec + w.tv_nsec / 1e9 + 0.3;
	do {
		burn(200000);
		clock_gettime(CLOCK_MONOTONIC, &w);
	} while (w.tv_sec + w.tv_nsec / 1e9 < warm_end);

	for (int round = 0; round < 40; round++) {
		struct timespec a, b;
		double us;

		clock_gettime(CLOCK_MONOTONIC, &a);
		burn(iters);
		clock_gettime(CLOCK_MONOTONIC, &b);
		us = (b.tv_sec - a.tv_sec) * 1e6 + (b.tv_nsec - a.tv_nsec) / 1e3;

		if (us > target_us * 0.9 && us < target_us * 1.1)
			return iters;
		if (us < 1)
			iters *= 8;
		else
			iters = (long)(iters * (target_us / us));
		if (iters < 1)
			iters = 1;
	}
	return iters;
}

static void usage(const char *a0)
{
	fprintf(stderr,
"usage: %s [--hz N] [--dur S] [--work-us US] [--label NAME]\n"
"\n"
"  --hz N        wakeups per second        [100]\n"
"  --dur S       run for S seconds         [30]\n"
"  --work-us US  work per wakeup           [500]\n"
"  --warmup S    discard the first S seconds of samples [2]\n"
"  --label NAME  copied into the JSON output\n"
"\n"
"Prints one JSON object on stdout.\n", a0);
	exit(2);
}

int main(int argc, char **argv)
{
	double hz = 100, dur = 30, work_us = 500, warmup = 2;
	const char *label = "";
	struct timespec next, t_wake, t_done;
	double *wake, *work;
	long cap, n = 0, iters;
	long period_ns;
	double t0;

	static struct option opts[] = {
		{"hz",      required_argument, 0, 'H'},
		{"dur",     required_argument, 0, 'd'},
		{"work-us", required_argument, 0, 'w'},
		{"warmup",  required_argument, 0, 'W'},
		{"label",   required_argument, 0, 'L'},
		{"help",    no_argument,       0, 'h'},
		{0, 0, 0, 0},
	};

	for (int c; (c = getopt_long(argc, argv, "h", opts, NULL)) != -1; ) {
		switch (c) {
		case 'H': hz = atof(optarg); break;
		case 'd': dur = atof(optarg); break;
		case 'w': work_us = atof(optarg); break;
		case 'W': warmup = atof(optarg); break;
		case 'L': label = optarg; break;
		default: usage(argv[0]);
		}
	}
	if (hz <= 0 || dur <= 0)
		usage(argv[0]);

	period_ns = (long)(1e9 / hz);
	cap = (long)(dur * hz) + 64;
	wake = calloc(cap, sizeof(*wake));
	work = calloc(cap, sizeof(*work));
	if (!wake || !work) {
		fprintf(stderr, "pinger: out of memory\n");
		return 1;
	}

	/*
	 * Calibrate before the measurement window and before any load is
	 * applied, so `iters` is a fixed amount of work across every arm of the
	 * experiment. Calibrating under load would silently normalise away the
	 * very slowdown we are trying to measure.
	 */
	iters = calibrate(work_us);

	signal(SIGTERM, on_stop);
	signal(SIGINT, on_stop);

	clock_gettime(CLOCK_MONOTONIC, &next);
	t0 = next.tv_sec + next.tv_nsec / 1e9;

	while (!stop_now) {
		double late_us, busy_us, elapsed;

		next.tv_nsec += period_ns;
		while (next.tv_nsec >= 1000000000L) {
			next.tv_nsec -= 1000000000L;
			next.tv_sec++;
		}

		if (clock_nanosleep(CLOCK_MONOTONIC, TIMER_ABSTIME, &next, NULL) &&
		    errno != EINTR)
			break;

		clock_gettime(CLOCK_MONOTONIC, &t_wake);
		burn(iters);
		clock_gettime(CLOCK_MONOTONIC, &t_done);

		late_us = (t_wake.tv_sec - next.tv_sec) * 1e6 +
			  (t_wake.tv_nsec - next.tv_nsec) / 1e3;
		busy_us = (t_done.tv_sec - t_wake.tv_sec) * 1e6 +
			  (t_done.tv_nsec - t_wake.tv_nsec) / 1e3;

		elapsed = (t_wake.tv_sec + t_wake.tv_nsec / 1e9) - t0;
		if (elapsed >= warmup && n < cap) {
			wake[n] = late_us > 0 ? late_us : 0;
			work[n] = busy_us;
			n++;
		}
		if (elapsed >= dur)
			break;
	}

	printf("{\"label\":\"%s\",\"n\":%ld,\"hz\":%.1f,\"work_iters\":%ld,"
	       "\"target_work_us\":%.1f", label, n, hz, iters, work_us);
	emit("wake_us", wake, n);
	emit("work_us", work, n);
	printf("}\n");
	return 0;
}
