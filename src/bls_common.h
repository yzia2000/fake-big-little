/* SPDX-License-Identifier: GPL-2.0 */
/*
 * bls_common.h - types shared between the BPF scheduler and its userspace loader.
 *
 * Kept free of kernel and libbpf headers so both sides can include it.
 */
#ifndef __BLS_COMMON_H
#define __BLS_COMMON_H

#define BLS_MAX_CPUS		64
#define BLS_MAX_COMM_RULES	16
#define BLS_COMM_LEN		16	/* TASK_COMM_LEN */

/* Core domains. Index into per-domain arrays; also the DSQ id. */
enum bls_domain {
	BLS_DOM_BIG	= 0,	/* low-EPP cores: "performance" partition */
	BLS_DOM_LITTLE	= 1,	/* high-EPP cores: "efficiency" partition */
	BLS_NR_DOMS	= 2,
};

/* How a task's domain is chosen. */
enum bls_classify_mode {
	BLS_CLASSIFY_FLAT	= 0,	/* everything -> BIG. Control arm: same
					 * scheduler code path, no partitioning. */
	BLS_CLASSIFY_COMM	= 1,	/* match p->comm against comm_rules */
	BLS_CLASSIFY_ADAPTIVE	= 2,	/* EWMA of on-cpu slice length */
	BLS_CLASSIFY_HYBRID	= 3,	/* comm rules first, EWMA otherwise */
};

/* Indices into the global stats array. Keep in sync with bls_stat_names[]. */
enum bls_stat {
	BLS_STAT_ENQ,			/* enqueue() calls */
	BLS_STAT_DIRECT,		/* dispatched straight to a local DSQ */
	BLS_STAT_DSQ_BIG,		/* queued on the big DSQ */
	BLS_STAT_DSQ_LITTLE,		/* queued on the little DSQ */
	BLS_STAT_LOCAL_HIT,		/* consumed from own domain's DSQ */
	BLS_STAT_STEAL,			/* consumed from the other domain's DSQ */
	BLS_STAT_NO_IDLE_IN_DOM,	/* domain saturated at select_cpu time */
	BLS_STAT_RECLASSIFY,		/* adaptive classifier changed a domain */
	BLS_STAT_RUN_BIG_MS,		/* task-time on big cores, ms */
	BLS_STAT_RUN_LITTLE_MS,		/* task-time on little cores, ms */
	BLS_STAT_TASKS_BIG,		/* tasks classified big at init */
	BLS_STAT_TASKS_LITTLE,
	BLS_NR_STATS,
};

/* A userspace-supplied comm -> domain rule. */
struct bls_comm_rule {
	char	comm[BLS_COMM_LEN];
	unsigned int len;	/* prefix length to match; 0 disables the rule */
	unsigned int domain;
};

#endif /* __BLS_COMMON_H */
