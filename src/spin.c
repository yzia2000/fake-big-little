// SPDX-License-Identifier: GPL-2.0
/*
 * spin.c - place a known load on a known set of CPUs.
 *
 *   spin --cpus 0,4 --dur 20 --duty 100
 *
 * One thread per listed CPU, hard-affined to it, running a dependent FP chain
 * at the requested duty cycle. Used to construct the rail-coupling experiments:
 * the whole question is what the package does when CPU A is at turbo and CPU B
 * is nominally "little", so the load has to be placed exactly, not merely
 * offered to the scheduler.
 *
 * Reports the achieved iteration rate per CPU, which is a frequency proxy that
 * is independent of the MSR path used by energy(1) - if the two disagree, one
 * of them is wrong and the experiment is void.
 */
#define _GNU_SOURCE
#include <getopt.h>
#include <pthread.h>
#include <sched.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>

#define MAX_THREADS 64

struct worker {
	pthread_t	tid;
	int		cpu;
	double		dur;
	double		duty;		/* 0..1 */
	unsigned long	iters;
	double		busy_s;
	bool		affinity_ok;
};

static double now_s(void)
{
	struct timespec ts;
	clock_gettime(CLOCK_MONOTONIC, &ts);
	return ts.tv_sec + ts.tv_nsec / 1e9;
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

static void *run(void *arg)
{
	struct worker *w = arg;
	cpu_set_t set;
	double t_end;
	const long chunk = 20000;	/* ~20-60 us of work depending on clock */

	CPU_ZERO(&set);
	CPU_SET(w->cpu, &set);
	w->affinity_ok = pthread_setaffinity_np(pthread_self(), sizeof(set), &set) == 0;

	t_end = now_s() + w->dur;
	while (now_s() < t_end) {
		double a = now_s(), b;

		burn(chunk);
		w->iters += chunk;
		b = now_s();
		w->busy_s += b - a;

		if (w->duty < 1.0) {
			double idle = (b - a) * (1.0 / w->duty - 1.0);

			if (idle > 0)
				usleep((useconds_t)(idle * 1e6));
		}
	}
	return NULL;
}

static int parse_cpus(const char *s, int *out)
{
	int n = 0;
	const char *p = s;

	while (*p && n < MAX_THREADS) {
		char *end;
		long a = strtol(p, &end, 10), b;

		if (end == p)
			return -1;
		p = end;
		b = a;
		if (*p == '-') {
			p++;
			b = strtol(p, &end, 10);
			if (end == p)
				return -1;
			p = end;
		}
		for (long c = a; c <= b && n < MAX_THREADS; c++)
			out[n++] = (int)c;
		if (*p == ',')
			p++;
	}
	return n;
}

int main(int argc, char **argv)
{
	const char *cpulist = NULL;
	double dur = 10, duty = 1.0;
	const char *label = "";
	int cpus[MAX_THREADS], nr;
	struct worker w[MAX_THREADS];
	double t0;

	static struct option opts[] = {
		{"cpus",  required_argument, 0, 'c'},
		{"dur",   required_argument, 0, 'd'},
		{"duty",  required_argument, 0, 'u'},
		{"label", required_argument, 0, 'L'},
		{0, 0, 0, 0},
	};

	for (int c; (c = getopt_long(argc, argv, "", opts, NULL)) != -1; ) {
		switch (c) {
		case 'c': cpulist = optarg; break;
		case 'd': dur = atof(optarg); break;
		case 'u': duty = atof(optarg) / 100.0; break;
		case 'L': label = optarg; break;
		default:
			fprintf(stderr,
				"usage: %s --cpus LIST [--dur S] [--duty PCT] [--label N]\n",
				argv[0]);
			return 2;
		}
	}
	if (!cpulist) {
		fprintf(stderr, "spin: --cpus is required\n");
		return 2;
	}
	nr = parse_cpus(cpulist, cpus);
	if (nr <= 0) {
		fprintf(stderr, "spin: bad cpu list '%s'\n", cpulist);
		return 2;
	}
	if (duty <= 0 || duty > 1)
		duty = 1.0;

	t0 = now_s();
	for (int i = 0; i < nr; i++) {
		memset(&w[i], 0, sizeof(w[i]));
		w[i].cpu = cpus[i];
		w[i].dur = dur;
		w[i].duty = duty;
		if (pthread_create(&w[i].tid, NULL, run, &w[i])) {
			fprintf(stderr, "spin: cannot create thread for cpu%d\n", cpus[i]);
			return 1;
		}
	}
	for (int i = 0; i < nr; i++)
		pthread_join(w[i].tid, NULL);

	printf("{\"label\":\"%s\",\"wall_s\":%.4f,\"duty\":%.3f,\"threads\":[",
	       label, now_s() - t0, duty);
	for (int i = 0; i < nr; i++)
		printf("%s{\"cpu\":%d,\"affinity_ok\":%s,\"iters\":%lu,"
		       "\"busy_s\":%.4f,\"miters_per_busy_s\":%.3f}",
		       i ? "," : "", w[i].cpu, w[i].affinity_ok ? "true" : "false",
		       w[i].iters, w[i].busy_s,
		       w[i].busy_s > 0 ? w[i].iters / w[i].busy_s / 1e6 : 0.0);
	printf("]}\n");
	return 0;
}
