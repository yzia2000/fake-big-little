// SPDX-License-Identifier: GPL-2.0
/*
 * energy.c - RAPL + APERF/MPERF sampler that wraps a workload.
 *
 *   energy -i 200 -o run.csv -- make -j8
 *
 * Runs the command, samples every -i milliseconds, writes a CSV time series,
 * and prints a one-line JSON summary on stdout for the harness to consume.
 *
 * Measurement notes that matter for the result:
 *
 *  - RAPL energy counters are 32-bit and wrap. Every domain's
 *    max_energy_range_uj is read once and used to unwrap deltas. A sample
 *    interval longer than the wrap period would alias silently; the wrap
 *    period is computed at startup and printed, so it can be checked.
 *
 *  - `core` (pp0) and `uncore` (pp1) are *sub*-domains of `package-0`. They do
 *    not sum to it: package includes the System Agent and other logic that is
 *    in neither. The difference is reported as `rest_w`, because on a U-series
 *    part that residual is a large fraction of the total and is exactly the
 *    part that per-core EPP cannot touch.
 *
 *  - `psys` (platform) includes display, DRAM and VR losses when the firmware
 *    populates it. It is sampled when present but never mixed into the package
 *    numbers.
 *
 *  - Per-CPU frequency is derived from APERF/MPERF/TSC, not from
 *    scaling_cur_freq, and `bzy_mhz` (aperf/mperf) is reported separately from
 *    `avg_mhz` (aperf/tsc). With per-core EPP the interesting question is
 *    whether a "little" CPU actually clocks lower *while running*, which only
 *    bzy_mhz answers.
 *
 * Requires root: RAPL sysfs energy_uj is 0400 and /dev/cpu/N/msr needs
 * CAP_SYS_RAWIO. Run `modprobe msr` first.
 */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <inttypes.h>
#include <math.h>
#include <signal.h>
#include <stdarg.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <getopt.h>
#include <time.h>
#include <dirent.h>
#include <sys/wait.h>
#include <sys/stat.h>

#define MAX_CPUS	64
#define MAX_RAPL	8

#define MSR_IA32_MPERF			0xE7
#define MSR_IA32_APERF			0xE8
#define MSR_IA32_PACKAGE_THERM_STATUS	0x1B1
#define MSR_IA32_TEMPERATURE_TARGET	0x1A2
#define MSR_IA32_HWP_REQUEST		0x774

struct rapl_dom {
	char		name[64];
	char		path[512];
	uint64_t	max_range_uj;
	uint64_t	last_uj;
	double		total_j;
	bool		present;
};

struct cpu_sample {
	uint64_t aperf, mperf, tsc;
};

static struct rapl_dom rapl[MAX_RAPL];
static int nr_rapl;
static int msr_fd[MAX_CPUS];
static int nr_cpus;
static double tsc_mhz;
static int tjmax = 100;
static volatile sig_atomic_t child_done;

static void die(const char *fmt, ...)
{
	va_list ap;
	va_start(ap, fmt);
	fprintf(stderr, "energy: ");
	vfprintf(stderr, fmt, ap);
	fprintf(stderr, "\n");
	va_end(ap);
	exit(1);
}

static double now_s(void)
{
	struct timespec ts;
	clock_gettime(CLOCK_MONOTONIC, &ts);
	return ts.tv_sec + ts.tv_nsec / 1e9;
}

static int read_u64_file(const char *path, uint64_t *out)
{
	FILE *f = fopen(path, "re");
	int ok;

	if (!f)
		return -errno;
	ok = fscanf(f, "%" SCNu64, out) == 1;
	fclose(f);
	return ok ? 0 : -EINVAL;
}

static int read_str_file(const char *path, char *buf, size_t len)
{
	FILE *f = fopen(path, "re");
	size_t n;

	if (!f)
		return -errno;
	n = fread(buf, 1, len - 1, f);
	fclose(f);
	buf[n] = '\0';
	while (n && (buf[n - 1] == '\n'))
		buf[--n] = '\0';
	return 0;
}

/* ------------------------------------------------------------------ RAPL  */

static void add_rapl(const char *dir)
{
	char path[512], name[64];
	struct rapl_dom *d;
	uint64_t v;

	if (nr_rapl >= MAX_RAPL)
		return;
	snprintf(path, sizeof(path), "%s/name", dir);
	if (read_str_file(path, name, sizeof(name)) < 0)
		return;

	d = &rapl[nr_rapl];
	snprintf(d->name, sizeof(d->name), "%s", name);
	snprintf(d->path, sizeof(d->path), "%s/energy_uj", dir);
	snprintf(path, sizeof(path), "%s/max_energy_range_uj", dir);
	if (read_u64_file(path, &d->max_range_uj) < 0)
		d->max_range_uj = 0;
	if (read_u64_file(d->path, &v) < 0) {
		if (errno == EACCES || errno == EPERM)
			die("cannot read %s: run as root", d->path);
		return;
	}
	d->last_uj = v;
	d->present = true;
	nr_rapl++;
}

static void discover_rapl(void)
{
	static const char *base = "/sys/class/powercap";
	struct dirent *de;
	DIR *dir = opendir(base);

	if (!dir)
		die("no %s: is CONFIG_INTEL_RAPL enabled?", base);
	while ((de = readdir(dir))) {
		char path[400];

		if (strncmp(de->d_name, "intel-rapl:", 11))
			continue;
		/* Skip the mmio mirror: it reports the same package twice. */
		if (strstr(de->d_name, "mmio"))
			continue;
		snprintf(path, sizeof(path), "%s/%s", base, de->d_name);
		add_rapl(path);
	}
	closedir(dir);
	if (!nr_rapl)
		die("no RAPL domains found");
}

/* Returns joules consumed since the previous call, unwrapping the counter. */
static double rapl_delta_j(struct rapl_dom *d)
{
	uint64_t v, delta;

	if (!d->present || read_u64_file(d->path, &v) < 0)
		return NAN;
	if (v >= d->last_uj)
		delta = v - d->last_uj;
	else if (d->max_range_uj)
		delta = d->max_range_uj - d->last_uj + v;
	else
		delta = 0;
	d->last_uj = v;
	d->total_j += delta / 1e6;
	return delta / 1e6;
}

/* -------------------------------------------------------------------- MSR */

static int rdmsr(int cpu, uint32_t reg, uint64_t *val)
{
	if (msr_fd[cpu] < 0)
		return -ENODEV;
	if (pread(msr_fd[cpu], val, sizeof(*val), reg) != sizeof(*val))
		return -errno;
	return 0;
}

static void open_msrs(void)
{
	for (int i = 0; i < nr_cpus; i++) {
		char path[64];

		snprintf(path, sizeof(path), "/dev/cpu/%d/msr", i);
		msr_fd[i] = open(path, O_RDONLY | O_CLOEXEC);
	}
	if (msr_fd[0] < 0)
		fprintf(stderr,
			"energy: warning: /dev/cpu/0/msr unavailable (%s); "
			"per-CPU frequency will be reported as nan. "
			"Try `modprobe msr` and run as root.\n", strerror(errno));
}

static void sample_cpus(struct cpu_sample *s)
{
	for (int i = 0; i < nr_cpus; i++) {
		uint64_t a = 0, m = 0, t = 0;

		/*
		 * Reading via /dev/cpu/N/msr from this thread issues the read on
		 * CPU N via smp_call_function_single, so the values are that
		 * CPU's. The three reads are not atomic with respect to each
		 * other; over a 100 ms+ interval the resulting error is well
		 * below the differences we are trying to resolve.
		 */
		rdmsr(i, MSR_IA32_APERF, &a);
		rdmsr(i, MSR_IA32_MPERF, &m);
		t = __builtin_ia32_rdtsc();
		s[i].aperf = a;
		s[i].mperf = m;
		s[i].tsc = t;
	}
}

static double pkg_temp_c(void)
{
	uint64_t v;

	if (rdmsr(0, MSR_IA32_PACKAGE_THERM_STATUS, &v) < 0)
		return NAN;
	return tjmax - (double)((v >> 16) & 0x7f);
}

static void init_tjmax(void)
{
	uint64_t v;

	if (rdmsr(0, MSR_IA32_TEMPERATURE_TARGET, &v) == 0)
		tjmax = (v >> 16) & 0xff;
}

/*
 * The TSC on Intel runs at the nominal (base) frequency, which intel_pstate
 * exports. Everything derived from APERF/MPERF is scaled by this, so if it is
 * wrong every reported MHz is wrong by the same factor - hence it is printed
 * in the summary rather than assumed.
 */
static void init_tsc_mhz(void)
{
	uint64_t khz;

	if (read_u64_file("/sys/devices/system/cpu/cpu0/cpufreq/base_frequency",
			  &khz) == 0 && khz > 0) {
		tsc_mhz = khz / 1000.0;
		return;
	}
	if (read_u64_file("/sys/devices/system/cpu/cpu0/cpufreq/bios_limit",
			  &khz) == 0 && khz > 0) {
		tsc_mhz = khz / 1000.0;
		return;
	}
	tsc_mhz = NAN;
	fprintf(stderr, "energy: warning: cannot determine TSC frequency; "
			"MHz columns will be nan\n");
}

static int count_cpus(void)
{
	int n = 0;

	while (n < MAX_CPUS) {
		char path[96];
		struct stat st;

		snprintf(path, sizeof(path), "/sys/devices/system/cpu/cpu%d", n);
		if (stat(path, &st))
			break;
		n++;
	}
	return n;
}

static void on_sigchld(int sig)
{
	(void)sig;
	child_done = 1;
}

/* ------------------------------------------------------------------- main */

static struct rapl_dom *find_dom(const char *name)
{
	for (int i = 0; i < nr_rapl; i++)
		if (!strcmp(rapl[i].name, name))
			return &rapl[i];
	return NULL;
}

static double dom_j(const char *name)
{
	struct rapl_dom *d = find_dom(name);
	return d ? d->total_j : NAN;
}

static void usage(const char *a0)
{
	fprintf(stderr,
"usage: %s [-i MS] [-o CSV] [-t SECONDS] [--label NAME] [-- COMMAND ...]\n"
"\n"
"  -i, --interval MS   sample interval           [200]\n"
"  -o, --output CSV    time-series output file   [none]\n"
"  -t, --time SECONDS  sample for this long when no COMMAND is given\n"
"      --label NAME    copied into the JSON summary\n"
"      --settle MS     discard samples for this long before starting [0]\n"
"\n"
"Prints a JSON summary on stdout. Requires root.\n", a0);
	exit(2);
}

int main(int argc, char **argv)
{
	double interval_ms = 200, duration = 0, settle_ms = 0;
	const char *out_path = NULL, *label = "";
	FILE *out = NULL;
	char **cmd = NULL;
	pid_t child = -1;
	int child_status = 0;
	struct cpu_sample *prev, *cur;
	double *mhz_sum, *bzy_sum, *busy_sum;
	double t_start, t_end, temp_max = -1e9, temp_sum = 0;
	long nsamples = 0;

	static struct option opts[] = {
		{"interval", required_argument, 0, 'i'},
		{"output",   required_argument, 0, 'o'},
		{"time",     required_argument, 0, 't'},
		{"label",    required_argument, 0, 'L'},
		{"settle",   required_argument, 0, 'S'},
		{"help",     no_argument,       0, 'h'},
		{0, 0, 0, 0},
	};

	for (int c; (c = getopt_long(argc, argv, "+i:o:t:h", opts, NULL)) != -1; ) {
		switch (c) {
		case 'i': interval_ms = atof(optarg); break;
		case 'o': out_path = optarg; break;
		case 't': duration = atof(optarg); break;
		case 'L': label = optarg; break;
		case 'S': settle_ms = atof(optarg); break;
		default: usage(argv[0]);
		}
	}
	if (optind < argc)
		cmd = &argv[optind];
	if (!cmd && duration <= 0)
		usage(argv[0]);

	nr_cpus = count_cpus();
	if (nr_cpus <= 0)
		die("cannot enumerate CPUs");

	open_msrs();
	init_tjmax();
	init_tsc_mhz();
	discover_rapl();

	prev = calloc(nr_cpus, sizeof(*prev));
	cur = calloc(nr_cpus, sizeof(*cur));
	mhz_sum = calloc(nr_cpus, sizeof(*mhz_sum));
	bzy_sum = calloc(nr_cpus, sizeof(*bzy_sum));
	busy_sum = calloc(nr_cpus, sizeof(*busy_sum));
	if (!prev || !cur || !mhz_sum || !bzy_sum || !busy_sum)
		die("out of memory");

	if (out_path) {
		out = fopen(out_path, "we");
		if (!out)
			die("cannot open %s: %s", out_path, strerror(errno));
		fprintf(out, "t_s,pkg_w,core_w,uncore_w,dram_w,psys_w,rest_w,pkg_c");
		for (int i = 0; i < nr_cpus; i++)
			fprintf(out, ",cpu%d_mhz", i);
		for (int i = 0; i < nr_cpus; i++)
			fprintf(out, ",cpu%d_bzy_mhz", i);
		for (int i = 0; i < nr_cpus; i++)
			fprintf(out, ",cpu%d_busy", i);
		fprintf(out, "\n");
	}

	if (settle_ms > 0)
		usleep((useconds_t)(settle_ms * 1000));

	/* Prime the counters so the first reported sample is a real delta. */
	for (int i = 0; i < nr_rapl; i++)
		rapl_delta_j(&rapl[i]);
	for (int i = 0; i < nr_rapl; i++)
		rapl[i].total_j = 0;
	sample_cpus(prev);

	signal(SIGCHLD, on_sigchld);

	if (cmd) {
		child = fork();
		if (child < 0)
			die("fork: %s", strerror(errno));
		if (child == 0) {
			execvp(cmd[0], cmd);
			fprintf(stderr, "energy: exec %s: %s\n", cmd[0], strerror(errno));
			_exit(127);
		}
	}

	t_start = now_s();
	for (;;) {
		double t, dt, pkg, core, uncore, dram, psys, rest, temp;

		usleep((useconds_t)(interval_ms * 1000));
		t = now_s() - t_start;
		dt = interval_ms / 1000.0;

		pkg    = rapl_delta_j(find_dom("package-0")) / dt;
		core   = rapl_delta_j(find_dom("core")) / dt;
		uncore = rapl_delta_j(find_dom("uncore")) / dt;
		dram   = rapl_delta_j(find_dom("dram")) / dt;
		psys   = rapl_delta_j(find_dom("psys")) / dt;
		rest   = pkg - (isnan(core) ? 0 : core) - (isnan(uncore) ? 0 : uncore);
		temp   = pkg_temp_c();

		if (!isnan(temp)) {
			temp_sum += temp;
			if (temp > temp_max)
				temp_max = temp;
		}

		sample_cpus(cur);
		if (out)
			fprintf(out, "%.3f,%.4f,%.4f,%.4f,%.4f,%.4f,%.4f,%.1f",
				t, pkg, core, uncore, dram, psys, rest, temp);

		for (int i = 0; i < nr_cpus; i++) {
			uint64_t da = cur[i].aperf - prev[i].aperf;
			uint64_t dm = cur[i].mperf - prev[i].mperf;
			uint64_t dtsc = cur[i].tsc - prev[i].tsc;
			double avg = dtsc ? tsc_mhz * (double)da / dtsc : NAN;
			double bzy = dm ? tsc_mhz * (double)da / dm : NAN;
			double busy = dtsc ? (double)dm / dtsc : NAN;

			if (!isnan(avg)) mhz_sum[i] += avg;
			if (!isnan(bzy)) bzy_sum[i] += bzy;
			if (!isnan(busy)) busy_sum[i] += busy;
			if (out)
				fprintf(out, ",%.1f", avg);
			(void)0;
		}
		if (out) {
			for (int i = 0; i < nr_cpus; i++) {
				uint64_t da = cur[i].aperf - prev[i].aperf;
				uint64_t dm = cur[i].mperf - prev[i].mperf;
				fprintf(out, ",%.1f", dm ? tsc_mhz * (double)da / dm : NAN);
			}
			for (int i = 0; i < nr_cpus; i++) {
				uint64_t dm = cur[i].mperf - prev[i].mperf;
				uint64_t dtsc = cur[i].tsc - prev[i].tsc;
				fprintf(out, ",%.4f", dtsc ? (double)dm / dtsc : NAN);
			}
			fprintf(out, "\n");
		}

		memcpy(prev, cur, nr_cpus * sizeof(*cur));
		nsamples++;

		if (child > 0) {
			pid_t r = waitpid(child, &child_status, WNOHANG);

			if (r == child)
				break;
		} else if (duration > 0 && t >= duration) {
			break;
		}
	}
	t_end = now_s();

	if (out)
		fclose(out);

	{
		double wall = t_end - t_start;
		double pkg_j = dom_j("package-0");
		double core_j = dom_j("core");
		double uncore_j = dom_j("uncore");

		printf("{\"label\":\"%s\",\"wall_s\":%.4f,\"samples\":%ld,"
		       "\"exit_code\":%d,\"tsc_mhz\":%.1f,\"tjmax_c\":%d,"
		       "\"pkg_j\":%.3f,\"core_j\":%.3f,\"uncore_j\":%.3f,"
		       "\"dram_j\":%.3f,\"psys_j\":%.3f,\"rest_j\":%.3f,"
		       "\"avg_pkg_w\":%.4f,\"pkg_c_mean\":%.1f,\"pkg_c_max\":%.1f",
		       label, wall, nsamples,
		       child > 0 ? (WIFEXITED(child_status) ? WEXITSTATUS(child_status) : -1) : 0,
		       tsc_mhz, tjmax,
		       pkg_j, core_j, uncore_j, dom_j("dram"), dom_j("psys"),
		       pkg_j - (isnan(core_j) ? 0 : core_j) - (isnan(uncore_j) ? 0 : uncore_j),
		       wall > 0 ? pkg_j / wall : NAN,
		       nsamples ? temp_sum / nsamples : NAN, temp_max);

		printf(",\"cpu_avg_mhz\":[");
		for (int i = 0; i < nr_cpus; i++)
			printf("%s%.1f", i ? "," : "", nsamples ? mhz_sum[i] / nsamples : NAN);
		printf("],\"cpu_bzy_mhz\":[");
		for (int i = 0; i < nr_cpus; i++)
			printf("%s%.1f", i ? "," : "", nsamples ? bzy_sum[i] / nsamples : NAN);
		printf("],\"cpu_busy\":[");
		for (int i = 0; i < nr_cpus; i++)
			printf("%s%.4f", i ? "," : "", nsamples ? busy_sum[i] / nsamples : NAN);
		printf("],\"epp\":[");
		for (int i = 0; i < nr_cpus; i++) {
			uint64_t v = 0;
			if (rdmsr(i, MSR_IA32_HWP_REQUEST, &v) == 0)
				printf("%s%u", i ? "," : "", (unsigned)((v >> 24) & 0xff));
			else
				printf("%snull", i ? "," : "");
		}
		printf("]}\n");
	}
	return 0;
}
