/* SPDX-License-Identifier: GPL-2.0 */
/*
 * bls.bpf.c - "fake big.LITTLE" sched_ext scheduler.
 *
 * Partitions a homogeneous SMP package into two software domains:
 *
 *   BLS_DOM_BIG    - CPUs the loader has set to a low EPP (energy_performance_
 *                    preference = "performance"), i.e. the ones the hardware
 *                    P-state controller will push to turbo aggressively.
 *   BLS_DOM_LITTLE - CPUs the loader has set to a high EPP ("power"), i.e. the
 *                    ones the PCU will keep near the efficiency point.
 *
 * Tasks are classified into one of the two domains and are scheduled from a
 * per-domain DSQ onto that domain's CPUs. This is the software analogue of an
 * ARM big.LITTLE placement policy.
 *
 * The point of the exercise is measurement, not the scheduler: see README.md.
 * Everything here is therefore built so that the *placement policy* can be
 * turned off (BLS_CLASSIFY_FLAT) while every other code path stays identical,
 * which gives a clean control arm for the A/B.
 *
 * Written against the sched_ext ABI of Linux 7.1 (struct sched_ext_ops as
 * exported in /sys/kernel/btf/vmlinux on the test machine).
 */
#include "vmlinux.h"
#include <bpf/bpf_helpers.h>
#include <bpf/bpf_tracing.h>
#include <bpf/bpf_core_read.h>

#include "bls_common.h"

char _license[] SEC("license") = "GPL";

#define BPF_STRUCT_OPS(name, args...)	SEC("struct_ops/"#name) BPF_PROG(name, ##args)
#define BPF_STRUCT_OPS_SLEEPABLE(name, args...) \
					SEC("struct_ops.s/"#name) BPF_PROG(name, ##args)

#define NSEC_PER_MSEC 1000000ULL

/* vmlinux.h carries no uapi constants; only the few we return are needed. */
#define ENOMEM	12
#define EINVAL	22

/* ---- sched_ext kfuncs (signatures taken from the running kernel's BTF) ---- */
void scx_bpf_dsq_insert(struct task_struct *p, u64 dsq_id, u64 slice,
			u64 enq_flags) __ksym;
bool scx_bpf_dsq_move_to_local(u64 dsq_id) __ksym;
s32 scx_bpf_create_dsq(u64 dsq_id, s32 node) __ksym;
bool scx_bpf_test_and_clear_cpu_idle(s32 cpu) __ksym;
void scx_bpf_kick_cpu(s32 cpu, u64 flags) __ksym;
s32 scx_bpf_dsq_nr_queued(u64 dsq_id) __ksym;
u32 scx_bpf_nr_cpu_ids(void) __ksym;
u64 scx_bpf_now(void) __ksym;
bool bpf_cpumask_test_cpu(u32 cpu, const struct cpumask *cpumask) __ksym;

/* ---- configuration, written by the loader before attach ---- */
const volatile u32 nr_cpus		= 1;
const volatile u32 classify_mode	= BLS_CLASSIFY_FLAT;
const volatile bool strict_domains	= false;	/* forbid cross-domain steal */
const volatile u64 slice_big_ns		= 20ULL * NSEC_PER_MSEC;
const volatile u64 slice_little_ns	= 3ULL * NSEC_PER_MSEC;
/*
 * Adaptive classifier threshold: a task whose EWMA continuous on-CPU slice
 * exceeds this is treated as throughput-bound and sent to the big domain.
 */
const volatile u64 big_slice_thresh_ns	= 2ULL * NSEC_PER_MSEC;

/* Written by the loader before attach; read at runtime, hence volatile. */
volatile u8 cpu_dom[BLS_MAX_CPUS];
volatile struct bls_comm_rule comm_rules[BLS_MAX_COMM_RULES];

/* Filled in by ops.exit so the loader can report why the scheduler unloaded. */
struct {
	s32	kind;
	s64	exit_code;
	char	msg[128];
} uei;

struct {
	__uint(type, BPF_MAP_TYPE_PERCPU_ARRAY);
	__uint(max_entries, BLS_NR_STATS);
	__type(key, u32);
	__type(value, u64);
} stats SEC(".maps");

struct task_ctx {
	u64	exec_ewma_ns;	/* EWMA of continuous on-CPU slice length */
	u64	started_at;
	u64	ran_big_ns;
	u64	ran_little_ns;
	u32	domain;
	bool	comm_pinned;	/* domain came from a comm rule; do not adapt */
};

struct {
	__uint(type, BPF_MAP_TYPE_TASK_STORAGE);
	__uint(map_flags, BPF_F_NO_PREALLOC);
	__type(key, int);
	__type(value, struct task_ctx);
} task_ctxs SEC(".maps");

static __always_inline void stat_add(u32 idx, u64 delta)
{
	u64 *v = bpf_map_lookup_elem(&stats, &idx);

	if (v)
		*v += delta;
}

static __always_inline u64 dom_dsq(u32 dom)
{
	return dom == BLS_DOM_LITTLE ? BLS_DOM_LITTLE : BLS_DOM_BIG;
}

static __always_inline u64 dom_slice(u32 dom)
{
	return dom == BLS_DOM_LITTLE ? slice_little_ns : slice_big_ns;
}

static __always_inline u32 dom_of_cpu(s32 cpu)
{
	if (cpu < 0 || cpu >= BLS_MAX_CPUS)
		return BLS_DOM_BIG;
	return cpu_dom[cpu] == BLS_DOM_LITTLE ? BLS_DOM_LITTLE : BLS_DOM_BIG;
}

/*
 * Prefix-match p->comm against the loader-supplied rules. Prefix rather than
 * exact match because the interesting names are truncated or suffixed
 * ("cc1plus", "ld.lld", "make"). First match wins.
 */
static __always_inline int classify_by_comm(struct task_struct *p)
{
	char comm[BLS_COMM_LEN];
	int i, j;

	if (bpf_probe_read_kernel_str(comm, sizeof(comm), p->comm) < 0)
		return -1;

	for (i = 0; i < BLS_MAX_COMM_RULES; i++) {
		u32 len = comm_rules[i].len;
		bool match = true;

		if (!len || len > BLS_COMM_LEN)
			continue;

		for (j = 0; j < BLS_COMM_LEN; j++) {
			if (j >= len)
				break;
			if (comm[j] != comm_rules[i].comm[j]) {
				match = false;
				break;
			}
		}
		if (match)
			return comm_rules[i].domain == BLS_DOM_LITTLE ?
				BLS_DOM_LITTLE : BLS_DOM_BIG;
	}
	return -1;
}

static __always_inline u32 initial_domain(struct task_struct *p, bool *pinned)
{
	int by_comm;

	*pinned = false;

	switch (classify_mode) {
	case BLS_CLASSIFY_FLAT:
		return BLS_DOM_BIG;
	case BLS_CLASSIFY_COMM:
		by_comm = classify_by_comm(p);
		*pinned = by_comm >= 0;
		return by_comm >= 0 ? (u32)by_comm : BLS_DOM_LITTLE;
	case BLS_CLASSIFY_HYBRID:
		by_comm = classify_by_comm(p);
		if (by_comm >= 0) {
			*pinned = true;
			return (u32)by_comm;
		}
		/* fall through */
	default:
		/* Adaptive: assume light until proven otherwise. */
		return BLS_DOM_LITTLE;
	}
}

/*
 * Find an idle CPU inside `dom` that `p` is allowed to run on, claiming it.
 * Returns -1 if the domain has no usable idle CPU.
 */
static __always_inline s32 pick_idle_in_dom(struct task_struct *p, u32 dom,
					    s32 prev_cpu)
{
	const struct cpumask *allowed = p->cpus_ptr;
	u32 i;

	if (prev_cpu >= 0 && prev_cpu < BLS_MAX_CPUS &&
	    dom_of_cpu(prev_cpu) == dom &&
	    scx_bpf_test_and_clear_cpu_idle(prev_cpu))
		return prev_cpu;

	for (i = 0; i < BLS_MAX_CPUS; i++) {
		if (i >= nr_cpus)
			break;
		if (dom_of_cpu(i) != dom)
			continue;
		if (!bpf_cpumask_test_cpu(i, allowed))
			continue;
		if (scx_bpf_test_and_clear_cpu_idle(i))
			return i;
	}
	return -1;
}

/* Wake an idle CPU in `dom` so a freshly queued task is picked up promptly. */
static __always_inline void kick_idle_in_dom(struct task_struct *p, u32 dom)
{
	const struct cpumask *allowed = p->cpus_ptr;
	u32 i;

	for (i = 0; i < BLS_MAX_CPUS; i++) {
		if (i >= nr_cpus)
			break;
		if (dom_of_cpu(i) != dom)
			continue;
		if (!bpf_cpumask_test_cpu(i, allowed))
			continue;
		if (scx_bpf_test_and_clear_cpu_idle(i)) {
			scx_bpf_kick_cpu(i, SCX_KICK_IDLE);
			return;
		}
	}
}

s32 BPF_STRUCT_OPS(bls_select_cpu, struct task_struct *p, s32 prev_cpu,
		   u64 wake_flags)
{
	struct task_ctx *tc = bpf_task_storage_get(&task_ctxs, p, 0, 0);
	u32 dom = tc ? tc->domain : BLS_DOM_BIG;
	s32 cpu;

	cpu = pick_idle_in_dom(p, dom, prev_cpu);
	if (cpu >= 0) {
		/* Straight to the CPU's local DSQ; ops.enqueue is skipped. */
		scx_bpf_dsq_insert(p, SCX_DSQ_LOCAL, dom_slice(dom), 0);
		stat_add(BLS_STAT_DIRECT, 1);
		return cpu;
	}

	stat_add(BLS_STAT_NO_IDLE_IN_DOM, 1);

	/*
	 * Domain is busy. In non-strict mode a task may spill to the other
	 * domain rather than queue behind its own; this is the escape valve
	 * that keeps throughput from collapsing when the partition is a bad
	 * fit for the offered load.
	 */
	if (!strict_domains) {
		cpu = pick_idle_in_dom(p, dom ^ 1, -1);
		if (cpu >= 0) {
			scx_bpf_dsq_insert(p, SCX_DSQ_LOCAL, dom_slice(dom), 0);
			stat_add(BLS_STAT_DIRECT, 1);
			stat_add(BLS_STAT_STEAL, 1);
			return cpu;
		}
	}

	return prev_cpu;
}

void BPF_STRUCT_OPS(bls_enqueue, struct task_struct *p, u64 enq_flags)
{
	struct task_ctx *tc = bpf_task_storage_get(&task_ctxs, p, 0, 0);
	u32 dom = tc ? tc->domain : BLS_DOM_BIG;

	stat_add(BLS_STAT_ENQ, 1);
	stat_add(dom == BLS_DOM_LITTLE ? BLS_STAT_DSQ_LITTLE : BLS_STAT_DSQ_BIG, 1);

	scx_bpf_dsq_insert(p, dom_dsq(dom), dom_slice(dom), enq_flags);
	kick_idle_in_dom(p, dom);
}

void BPF_STRUCT_OPS(bls_dispatch, s32 cpu, struct task_struct *prev)
{
	u32 dom = dom_of_cpu(cpu);

	if (scx_bpf_dsq_move_to_local(dom_dsq(dom))) {
		stat_add(BLS_STAT_LOCAL_HIT, 1);
		return;
	}

	/*
	 * Work conservation. With --strict this is skipped, so an idle little
	 * CPU will sit idle while the big DSQ has runnable tasks. That is the
	 * honest big.LITTLE-style behaviour and it is what actually exposes the
	 * cost of the partition, so it is a measured arm rather than a bug.
	 */
	if (strict_domains)
		return;

	if (scx_bpf_dsq_move_to_local(dom_dsq(dom ^ 1)))
		stat_add(BLS_STAT_STEAL, 1);
}

void BPF_STRUCT_OPS(bls_running, struct task_struct *p)
{
	struct task_ctx *tc = bpf_task_storage_get(&task_ctxs, p, 0, 0);

	if (tc)
		tc->started_at = scx_bpf_now();
}

void BPF_STRUCT_OPS(bls_stopping, struct task_struct *p, bool runnable)
{
	struct task_ctx *tc = bpf_task_storage_get(&task_ctxs, p, 0, 0);
	u64 now = scx_bpf_now();
	u64 delta;
	u32 cpu;

	if (!tc || !tc->started_at)
		return;

	delta = now - tc->started_at;
	tc->started_at = 0;

	cpu = bpf_get_smp_processor_id();
	if (dom_of_cpu(cpu) == BLS_DOM_LITTLE) {
		tc->ran_little_ns += delta;
		stat_add(BLS_STAT_RUN_LITTLE_MS, delta / NSEC_PER_MSEC);
	} else {
		tc->ran_big_ns += delta;
		stat_add(BLS_STAT_RUN_BIG_MS, delta / NSEC_PER_MSEC);
	}

	/* EWMA, alpha = 1/4. */
	tc->exec_ewma_ns = (tc->exec_ewma_ns * 3 + delta) / 4;

	if (tc->comm_pinned ||
	    (classify_mode != BLS_CLASSIFY_ADAPTIVE &&
	     classify_mode != BLS_CLASSIFY_HYBRID))
		return;

	/*
	 * Reclassify with hysteresis: promote at the threshold, demote only at
	 * half of it, so a task oscillating around the boundary does not
	 * ping-pong across domains (each migration costs an LLC-warm cache).
	 */
	if (tc->domain == BLS_DOM_LITTLE &&
	    tc->exec_ewma_ns > big_slice_thresh_ns) {
		tc->domain = BLS_DOM_BIG;
		stat_add(BLS_STAT_RECLASSIFY, 1);
	} else if (tc->domain == BLS_DOM_BIG &&
		   tc->exec_ewma_ns < big_slice_thresh_ns / 2) {
		tc->domain = BLS_DOM_LITTLE;
		stat_add(BLS_STAT_RECLASSIFY, 1);
	}
}

s32 BPF_STRUCT_OPS(bls_init_task, struct task_struct *p,
		   struct scx_init_task_args *args)
{
	struct task_ctx *tc;
	bool pinned;

	tc = bpf_task_storage_get(&task_ctxs, p, 0, BPF_LOCAL_STORAGE_GET_F_CREATE);
	if (!tc)
		return -ENOMEM;

	tc->domain = initial_domain(p, &pinned);
	tc->comm_pinned = pinned;
	tc->exec_ewma_ns = 0;
	tc->started_at = 0;

	stat_add(tc->domain == BLS_DOM_LITTLE ? BLS_STAT_TASKS_LITTLE :
						BLS_STAT_TASKS_BIG, 1);
	return 0;
}

s32 BPF_STRUCT_OPS_SLEEPABLE(bls_init)
{
	s32 ret;

	ret = scx_bpf_create_dsq(BLS_DOM_BIG, -1);
	if (ret)
		return ret;
	return scx_bpf_create_dsq(BLS_DOM_LITTLE, -1);
}

void BPF_STRUCT_OPS(bls_exit, struct scx_exit_info *ei)
{
	uei.kind = ei->kind;
	uei.exit_code = ei->exit_code;
	bpf_probe_read_kernel_str(uei.msg, sizeof(uei.msg), ei->msg);
}

SEC(".struct_ops.link")
struct sched_ext_ops bls_ops = {
	.select_cpu	= (void *)bls_select_cpu,
	.enqueue	= (void *)bls_enqueue,
	.dispatch	= (void *)bls_dispatch,
	.running	= (void *)bls_running,
	.stopping	= (void *)bls_stopping,
	.init_task	= (void *)bls_init_task,
	.init		= (void *)bls_init,
	.exit		= (void *)bls_exit,
	.flags		= SCX_OPS_ENQ_LAST,
	.timeout_ms	= 5000,
	.name		= "bls",
};
