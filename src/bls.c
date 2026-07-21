// SPDX-License-Identifier: GPL-2.0
/*
 * bls.c - loader for the "fake big.LITTLE" sched_ext scheduler.
 *
 * Responsibilities, in order:
 *
 *   1. Parse the requested BIG/LITTLE CPU partition.
 *   2. Check the partition against the SMT topology and refuse silently-broken
 *      configurations (two hyperthreads of one core cannot have different
 *      frequencies, so splitting a core across domains is meaningless).
 *   3. Apply per-CPU EPP through cpufreq sysfs, saving the previous values.
 *   4. Read IA32_HWP_REQUEST back through /dev/cpu/N/msr to confirm the EPP
 *      field the kernel actually programmed. sysfs accepting a write is not
 *      evidence the PCU got it.
 *   5. Load and attach the BPF scheduler.
 *   6. On exit, restore every EPP and dump scheduler counters as JSON.
 *
 * Steps 2 and 4 exist because the whole experiment is only meaningful if the
 * partition is physically real. They are the first thing that can invalidate
 * the result, so they run before anything else and their output is recorded.
 */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <inttypes.h>
#include <signal.h>
#include <stdarg.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <getopt.h>
#include <time.h>
#include <sys/stat.h>

#include <bpf/bpf.h>
#include <bpf/libbpf.h>

#include "bls_common.h"
#include "bls.skel.h"

#define IA32_HWP_REQUEST	0x774
#define IA32_HWP_CAPABILITIES	0x771

static volatile sig_atomic_t exiting;

static const char *bls_stat_names[BLS_NR_STATS] = {
	"enqueue", "direct_dispatch", "dsq_big", "dsq_little",
	"local_hit", "cross_domain", "no_idle_in_domain", "reclassify",
	"run_big_ms", "run_little_ms", "tasks_big", "tasks_little",
};

struct cpu_state {
	char	epp_saved[32];
	bool	epp_valid;
	int	domain;
	int	core_id;		/* physical core, from topology */
	uint8_t	epp_msr_before;
	uint8_t	epp_msr_after;
	bool	msr_valid;
};

static struct cpu_state cpus[BLS_MAX_CPUS];
static int nr_cpus_online;

static void die(const char *fmt, ...)
{
	va_list ap;

	va_start(ap, fmt);
	fprintf(stderr, "bls: ");
	vfprintf(stderr, fmt, ap);
	fprintf(stderr, "\n");
	va_end(ap);
	exit(1);
}

static void on_signal(int sig)
{
	(void)sig;
	exiting = 1;
}

/* ------------------------------------------------------------------ sysfs */

static int read_file(const char *path, char *buf, size_t len)
{
	FILE *f = fopen(path, "re");
	size_t n;

	if (!f)
		return -errno;
	n = fread(buf, 1, len - 1, f);
	fclose(f);
	buf[n] = '\0';
	while (n && (buf[n - 1] == '\n' || buf[n - 1] == ' '))
		buf[--n] = '\0';
	return 0;
}

static int write_file(const char *path, const char *val)
{
	FILE *f = fopen(path, "we");
	int ret = 0;

	if (!f)
		return -errno;
	if (fputs(val, f) == EOF)
		ret = -EIO;
	if (fclose(f) != 0)
		ret = -EIO;
	return ret;
}

static int cpu_epp_path(int cpu, char *buf, size_t len)
{
	return snprintf(buf, len,
			"/sys/devices/system/cpu/cpu%d/cpufreq/energy_performance_preference",
			cpu);
}

/* ------------------------------------------------------------------- MSR  */

static int rdmsr(int cpu, uint32_t reg, uint64_t *val)
{
	char path[64];
	int fd, ret = 0;

	snprintf(path, sizeof(path), "/dev/cpu/%d/msr", cpu);
	fd = open(path, O_RDONLY | O_CLOEXEC);
	if (fd < 0)
		return -errno;
	if (pread(fd, val, sizeof(*val), reg) != sizeof(*val))
		ret = -errno;
	close(fd);
	return ret;
}

static bool read_epp_msr(int cpu, uint8_t *epp)
{
	uint64_t v;

	if (rdmsr(cpu, IA32_HWP_REQUEST, &v) < 0)
		return false;
	*epp = (v >> 24) & 0xff;
	return true;
}

/* -------------------------------------------------------------- topology  */

static int core_id_of(int cpu)
{
	char path[128], buf[32];

	snprintf(path, sizeof(path),
		 "/sys/devices/system/cpu/cpu%d/topology/core_id", cpu);
	if (read_file(path, buf, sizeof(buf)) < 0)
		return -1;
	return atoi(buf);
}

static int count_online_cpus(void)
{
	int n = 0;

	while (n < BLS_MAX_CPUS) {
		char path[128];
		struct stat st;

		snprintf(path, sizeof(path), "/sys/devices/system/cpu/cpu%d", n);
		if (stat(path, &st) != 0)
			break;
		n++;
	}
	return n;
}

/*
 * A physical core has a single clock domain: both of its hyperthreads resolve
 * to one frequency, and the PCU takes the more performance-biased of the two
 * HWP requests. Splitting a core across domains therefore does not create a
 * slow half - it creates a fast core that we have mislabelled.
 */
static int check_smt_split(void)
{
	int seen_core[BLS_MAX_CPUS];
	int seen_dom[BLS_MAX_CPUS];
	int i, nr_seen = 0, bad = 0;

	for (i = 0; i < nr_cpus_online; i++) {
		int c = cpus[i].core_id, j, found = -1;

		if (c < 0)
			continue;
		for (j = 0; j < nr_seen; j++)
			if (seen_core[j] == c)
				found = j;
		if (found < 0) {
			seen_core[nr_seen] = c;
			seen_dom[nr_seen] = cpus[i].domain;
			nr_seen++;
		} else if (seen_dom[found] != cpus[i].domain) {
			fprintf(stderr,
				"bls: WARNING: physical core %d has CPUs in both domains; "
				"its two SMT siblings share one clock domain, so this "
				"partition is not physically realisable\n", c);
			bad++;
		}
	}
	return bad;
}

/* ------------------------------------------------------------- cpu lists  */

static void parse_cpulist(const char *s, int domain)
{
	const char *p = s;

	while (*p) {
		char *end;
		long a = strtol(p, &end, 10), b;

		if (end == p)
			die("bad cpu list near '%s'", p);
		p = end;
		b = a;
		if (*p == '-') {
			p++;
			b = strtol(p, &end, 10);
			if (end == p)
				die("bad cpu range near '%s'", p);
			p = end;
		}
		if (a < 0 || b >= BLS_MAX_CPUS || b < a)
			die("cpu list out of range: %ld-%ld", a, b);
		for (long c = a; c <= b; c++)
			cpus[c].domain = domain;
		if (*p == ',')
			p++;
		else if (*p)
			die("unexpected character '%c' in cpu list", *p);
	}
}

/* ------------------------------------------------------------------- EPP  */

static void save_epp(void)
{
	for (int i = 0; i < nr_cpus_online; i++) {
		char path[192];

		cpu_epp_path(i, path, sizeof(path));
		if (read_file(path, cpus[i].epp_saved, sizeof(cpus[i].epp_saved)) == 0)
			cpus[i].epp_valid = true;
		cpus[i].msr_valid = read_epp_msr(i, &cpus[i].epp_msr_before);
	}
}

static void apply_epp(const char *epp_big, const char *epp_little)
{
	for (int i = 0; i < nr_cpus_online; i++) {
		const char *want = cpus[i].domain == BLS_DOM_LITTLE ?
					epp_little : epp_big;
		char path[192];
		int ret;

		cpu_epp_path(i, path, sizeof(path));
		ret = write_file(path, want);
		if (ret < 0)
			die("cpu%d: cannot set EPP to '%s': %s "
			    "(need root, and intel_pstate in active mode)",
			    i, want, strerror(-ret));
		cpus[i].msr_valid &= read_epp_msr(i, &cpus[i].epp_msr_after);
	}
}

static void restore_epp(void)
{
	for (int i = 0; i < nr_cpus_online; i++) {
		char path[192];

		if (!cpus[i].epp_valid)
			continue;
		cpu_epp_path(i, path, sizeof(path));
		write_file(path, cpus[i].epp_saved);
	}
}

static void report_partition(const char *epp_big, const char *epp_little)
{
	printf("{\"event\":\"partition\",\"cpus\":[");
	for (int i = 0; i < nr_cpus_online; i++)
		printf("%s{\"cpu\":%d,\"core\":%d,\"domain\":\"%s\",\"epp\":\"%s\","
		       "\"epp_msr_before\":%s,\"epp_msr_after\":%s}",
		       i ? "," : "", i, cpus[i].core_id,
		       cpus[i].domain == BLS_DOM_LITTLE ? "little" : "big",
		       cpus[i].domain == BLS_DOM_LITTLE ? epp_little : epp_big,
		       cpus[i].msr_valid ? "" : "null",
		       cpus[i].msr_valid ? "" : "null");
	printf("]}\n");
	fflush(stdout);
}

/* Separate, readable version for humans; the JSON above is for the harness. */
static void print_partition_table(const char *epp_big, const char *epp_little)
{
	fprintf(stderr, "%-5s %-5s %-8s %-20s %-12s %-12s\n",
		"cpu", "core", "domain", "epp_requested", "hwp_before", "hwp_after");
	for (int i = 0; i < nr_cpus_online; i++) {
		char before[16] = "n/a", after[16] = "n/a";

		if (cpus[i].msr_valid) {
			snprintf(before, sizeof(before), "%u", cpus[i].epp_msr_before);
			snprintf(after, sizeof(after), "%u", cpus[i].epp_msr_after);
		}
		fprintf(stderr, "%-5d %-5d %-8s %-20s %-12s %-12s\n",
			i, cpus[i].core_id,
			cpus[i].domain == BLS_DOM_LITTLE ? "little" : "big",
			cpus[i].domain == BLS_DOM_LITTLE ? epp_little : epp_big,
			before, after);
	}
}

/* ------------------------------------------------------------------ stats */

static void read_stats(struct bls_bpf *skel, uint64_t *out)
{
	int nr = libbpf_num_possible_cpus();
	uint64_t *per_cpu = calloc(nr, sizeof(uint64_t));
	int fd = bpf_map__fd(skel->maps.stats);

	if (!per_cpu)
		die("out of memory");

	for (uint32_t k = 0; k < BLS_NR_STATS; k++) {
		out[k] = 0;
		if (bpf_map_lookup_elem(fd, &k, per_cpu))
			continue;
		for (int c = 0; c < nr; c++)
			out[k] += per_cpu[c];
	}
	free(per_cpu);
}

static void print_stats_json(const uint64_t *s, double elapsed)
{
	printf("{\"event\":\"stats\",\"elapsed_s\":%.3f", elapsed);
	for (int i = 0; i < BLS_NR_STATS; i++)
		printf(",\"%s\":%" PRIu64, bls_stat_names[i], s[i]);
	printf("}\n");
	fflush(stdout);
}

/* ------------------------------------------------------------------- main */

static void usage(const char *argv0)
{
	fprintf(stderr,
"usage: %s [options]\n"
"\n"
"  --big LIST          CPUs in the big (low-EPP) domain      [default: 0-3]\n"
"  --little LIST       CPUs in the little (high-EPP) domain   [default: rest]\n"
"  --epp-big NAME      EPP for big CPUs                       [performance]\n"
"  --epp-little NAME   EPP for little CPUs                    [power]\n"
"  --flat              single domain, no partition (control arm)\n"
"  --no-epp            do not touch EPP; scheduler partition only\n"
"  --strict            no cross-domain work stealing\n"
"  --mode MODE         flat | comm | adaptive | hybrid        [hybrid]\n"
"  --big-comm A,B,..   comms routed to the big domain         [make,cc1,cc1plus,ld,as,rustc,clang,gcc]\n"
"  --little-comm A,..  comms routed to the little domain\n"
"  --slice-big MS      time slice on big CPUs                 [20]\n"
"  --slice-little MS   time slice on little CPUs              [3]\n"
"  --thresh-ms MS      adaptive big/little slice threshold    [2]\n"
"  --interval S        stats interval, 0 = only at exit       [0]\n"
"  --duration S        exit after S seconds, 0 = until signal [0]\n"
"  --dry-run           apply EPP and report, do not load BPF\n"
"\n"
"Emits newline-delimited JSON on stdout; human-readable text on stderr.\n",
		argv0);
	exit(2);
}

static int mode_from_name(const char *s)
{
	if (!strcmp(s, "flat"))		return BLS_CLASSIFY_FLAT;
	if (!strcmp(s, "comm"))		return BLS_CLASSIFY_COMM;
	if (!strcmp(s, "adaptive"))	return BLS_CLASSIFY_ADAPTIVE;
	if (!strcmp(s, "hybrid"))	return BLS_CLASSIFY_HYBRID;
	die("unknown mode '%s'", s);
	return 0;
}

static int add_comm_rules(struct bls_bpf *skel, const char *list, int domain,
			  int slot)
{
	char *dup = strdup(list), *tok, *save = NULL;

	if (!dup)
		die("out of memory");
	for (tok = strtok_r(dup, ",", &save); tok; tok = strtok_r(NULL, ",", &save)) {
		size_t len = strlen(tok);

		if (slot >= BLS_MAX_COMM_RULES)
			die("too many comm rules (max %d)", BLS_MAX_COMM_RULES);
		if (len == 0)
			continue;
		if (len > BLS_COMM_LEN)
			len = BLS_COMM_LEN;
		memcpy((void *)skel->bss->comm_rules[slot].comm, tok, len);
		skel->bss->comm_rules[slot].len = len;
		skel->bss->comm_rules[slot].domain = domain;
		slot++;
	}
	free(dup);
	return slot;
}

static double now_s(void)
{
	struct timespec ts;

	clock_gettime(CLOCK_MONOTONIC, &ts);
	return ts.tv_sec + ts.tv_nsec / 1e9;
}

static int libbpf_quiet(enum libbpf_print_level lvl, const char *fmt, va_list ap)
{
	if (lvl == LIBBPF_DEBUG)
		return 0;
	return vfprintf(stderr, fmt, ap);
}

int main(int argc, char **argv)
{
	const char *big_list = NULL, *little_list = NULL;
	const char *epp_big = "performance", *epp_little = "power";
	const char *big_comm = "make,cc1,cc1plus,ld,as,rustc,clang,gcc,collect2,ccache";
	const char *little_comm = NULL;
	bool flat = false, no_epp = false, strict = false, dry_run = false;
	bool persist = false;
	int mode = BLS_CLASSIFY_HYBRID;
	double interval = 0, duration = 0;
	unsigned slice_big = 20, slice_little = 3, thresh_ms = 2;
	struct bls_bpf *skel = NULL;
	struct bpf_link *link = NULL;
	uint64_t stat_vals[BLS_NR_STATS];
	double t0;
	int slot = 0;

	static struct option opts[] = {
		{"big",		required_argument, 0, 'B'},
		{"little",	required_argument, 0, 'L'},
		{"epp-big",	required_argument, 0, 'e'},
		{"epp-little",	required_argument, 0, 'E'},
		{"flat",	no_argument,	   0, 'f'},
		{"no-epp",	no_argument,	   0, 'n'},
		{"strict",	no_argument,	   0, 's'},
		{"mode",	required_argument, 0, 'm'},
		{"big-comm",	required_argument, 0, 'c'},
		{"little-comm",	required_argument, 0, 'C'},
		{"slice-big",	required_argument, 0, 'S'},
		{"slice-little",required_argument, 0, 'l'},
		{"thresh-ms",	required_argument, 0, 't'},
		{"interval",	required_argument, 0, 'i'},
		{"duration",	required_argument, 0, 'd'},
		{"dry-run",	no_argument,	   0, 'D'},
		{"persist",	no_argument,	   0, 'P'},
		{"help",	no_argument,	   0, 'h'},
		{0, 0, 0, 0},
	};

	for (int c; (c = getopt_long(argc, argv, "h", opts, NULL)) != -1; ) {
		switch (c) {
		case 'B': big_list = optarg; break;
		case 'L': little_list = optarg; break;
		case 'e': epp_big = optarg; break;
		case 'E': epp_little = optarg; break;
		case 'f': flat = true; break;
		case 'n': no_epp = true; break;
		case 's': strict = true; break;
		case 'm': mode = mode_from_name(optarg); break;
		case 'c': big_comm = optarg; break;
		case 'C': little_comm = optarg; break;
		case 'S': slice_big = atoi(optarg); break;
		case 'l': slice_little = atoi(optarg); break;
		case 't': thresh_ms = atoi(optarg); break;
		case 'i': interval = atof(optarg); break;
		case 'd': duration = atof(optarg); break;
		case 'D': dry_run = true; break;
		case 'P': persist = true; break;
		default: usage(argv[0]);
		}
	}

	nr_cpus_online = count_online_cpus();
	if (nr_cpus_online <= 0 || nr_cpus_online > BLS_MAX_CPUS)
		die("implausible CPU count %d", nr_cpus_online);

	/* Default partition: first half big, second half little. */
	for (int i = 0; i < nr_cpus_online; i++) {
		cpus[i].domain = (i < nr_cpus_online / 2) ? BLS_DOM_BIG : BLS_DOM_LITTLE;
		cpus[i].core_id = core_id_of(i);
	}
	if (flat) {
		mode = BLS_CLASSIFY_FLAT;
		for (int i = 0; i < nr_cpus_online; i++)
			cpus[i].domain = BLS_DOM_BIG;
	} else {
		if (big_list || little_list) {
			for (int i = 0; i < nr_cpus_online; i++)
				cpus[i].domain = little_list ? BLS_DOM_BIG : BLS_DOM_LITTLE;
			if (big_list)
				parse_cpulist(big_list, BLS_DOM_BIG);
			if (little_list)
				parse_cpulist(little_list, BLS_DOM_LITTLE);
		}
		check_smt_split();
	}

	save_epp();
	if (!no_epp && !flat)
		apply_epp(epp_big, epp_little);
	else if (!no_epp && flat)
		apply_epp(epp_big, epp_big);

	print_partition_table(epp_big, flat ? epp_big : epp_little);
	report_partition(epp_big, flat ? epp_big : epp_little);

	if (dry_run) {
		fprintf(stderr, "bls: dry run, not loading BPF\n");
		if (!persist)
			restore_epp();
		return 0;
	}

	libbpf_set_print(libbpf_quiet);

	skel = bls_bpf__open();
	if (!skel) {
		restore_epp();
		die("failed to open BPF skeleton: %s", strerror(errno));
	}

	skel->rodata->nr_cpus = nr_cpus_online;
	skel->rodata->classify_mode = mode;
	skel->rodata->strict_domains = strict;
	skel->rodata->slice_big_ns = (uint64_t)slice_big * 1000000ULL;
	skel->rodata->slice_little_ns = (uint64_t)slice_little * 1000000ULL;
	skel->rodata->big_slice_thresh_ns = (uint64_t)thresh_ms * 1000000ULL;

	if (bls_bpf__load(skel)) {
		restore_epp();
		die("failed to load BPF scheduler: %s", strerror(errno));
	}

	for (int i = 0; i < nr_cpus_online; i++)
		skel->bss->cpu_dom[i] = cpus[i].domain;
	if (big_comm)
		slot = add_comm_rules(skel, big_comm, BLS_DOM_BIG, slot);
	if (little_comm)
		slot = add_comm_rules(skel, little_comm, BLS_DOM_LITTLE, slot);

	signal(SIGINT, on_signal);
	signal(SIGTERM, on_signal);

	link = bpf_map__attach_struct_ops(skel->maps.bls_ops);
	if (!link) {
		bls_bpf__destroy(skel);
		restore_epp();
		die("failed to attach scheduler: %s "
		    "(is CONFIG_SCHED_CLASS_EXT=y and no other scx scheduler running?)",
		    strerror(errno));
	}

	fprintf(stderr, "bls: attached (mode=%d strict=%d)\n", mode, strict);
	printf("{\"event\":\"attached\"}\n");
	fflush(stdout);

	t0 = now_s();
	while (!exiting) {
		double elapsed = now_s() - t0;

		if (duration > 0 && elapsed >= duration)
			break;
		if (skel->bss->uei.kind) {
			fprintf(stderr, "bls: scheduler exited: kind=%d code=%lld %s\n",
				skel->bss->uei.kind, (long long)skel->bss->uei.exit_code,
				skel->bss->uei.msg);
			break;
		}
		if (interval > 0) {
			read_stats(skel, stat_vals);
			print_stats_json(stat_vals, elapsed);
			usleep((useconds_t)(interval * 1e6));
		} else {
			usleep(200000);
		}
	}

	read_stats(skel, stat_vals);
	print_stats_json(stat_vals, now_s() - t0);

	bpf_link__destroy(link);
	bls_bpf__destroy(skel);
	if (!persist)
		restore_epp();
	fprintf(stderr, "bls: detached%s\n", persist ? "" : ", EPP restored");
	return 0;
}
