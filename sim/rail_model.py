#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
rail_model.py -- a first-principles power model of a shared-voltage-rail x86 client CPU,
used to predict (BEFORE any hardware measurement is taken) whether ARM big.LITTLE can be
usefully emulated on an Intel Core i7-8550U (Kaby Lake-R, 4C/8T, single package).

------------------------------------------------------------------------------------
HYPOTHESIS UNDER TEST (the repo's premise)
------------------------------------------------------------------------------------
  H1: By partitioning the 4 physical cores of an i7-8550U into a "big" set (EPP=0,
      high HWP max) and a "LITTLE" set (EPP=255, low HWP max), and doing QoS-aware
      placement with a sched_ext BPF scheduler, we can obtain the energy behaviour of
      a real big.LITTLE SoC.

------------------------------------------------------------------------------------
WHY THE MODEL SAYS NO (the physics)
------------------------------------------------------------------------------------
  Since Skylake, Intel client parts have:
    * PER-CORE clock domains          -> per-core frequency IS controllable (HWP/EPP works)
    * ONE SHARED core voltage rail    -> VccCore is supplied by an external VR; the
                                         on-package FIVR was removed in Skylake, so there
                                         is exactly ONE core voltage for the whole package.
  Consequently the rail voltage is dictated by the *highest* frequency any active core
  requests:

        V_rail = V(max_i f_i)

  A "LITTLE" core dropped to 800 MHz therefore still sits at the voltage demanded by
  the "big" core at 4.0 GHz. Its dynamic power keeps the full V^2 penalty, and its
  leakage keeps the full exp(V) penalty. Only the linear-in-f term is saved.

  A real big.LITTLE SoC has SEPARATE per-cluster rails, so V_little = V(f_little) is
  independent of the big cluster. That is the counterfactual this file computes.

  Additionally, on client Skylake/Kaby Lake the ring interconnect + LLC slices are
  themselves on VccCore and their clock tracks the fastest core, so one turbo core also
  drags the uncore voltage/frequency up. And the System Agent / memory controller floor
  is not under EPP control at all -- on a 15 W U-part it is a large fraction of package
  power at low-to-mid load, which sets a hard lower bound on any "LITTLE" core's cost.

------------------------------------------------------------------------------------
FALSIFIABLE PREDICTIONS (what the hardware run must show, or this model is wrong)
------------------------------------------------------------------------------------
  P1. With one core pinned at max turbo, adding a light background task on another core
      costs ~3-5x more package power than the same task would cost on a dedicated
      low-voltage rail. Equivalently: EPP-based "LITTLE" cores retain only ~50-70% of
      the energy saving a true LITTLE cluster would deliver, and the deficit grows as
      the light task's activity factor falls (because the deficit is leakage-dominated).
  P2. In a fixed-work partition sweep, the shared rail retains only a fraction of the
      energy benefit that partitioning delivers on a split rail, and at identical
      placement the shared rail costs several percent more energy for the same work.
      Whatever interior optimum the shared rail does show is produced by the linear-in-f
      dynamic term and by the PL1 power cap redistributing frequency -- NOT by voltage:
      V_rail never falls while any big core runs. Falsifier: if the measured
      energy-vs-partition curve is deeper than the shared-rail column predicts, or if
      per-core VID (MSR 0x198) is observed to differ across cores, this model is wrong.
  P3. Because of the uncore/SA floor there is a race-to-idle crossover frequency well
      above f_min: running a fixed amount of work at f_min costs MORE total energy than
      running it near the crossover. The model reports that crossover explicitly.
  P4. Per-core EPP cannot differentiate SMT siblings (cpu_i and cpu_i+4 share one core
      and therefore one clock domain). Any scheduler that treats the 8 logical CPUs as
      8 independently-tunable "cores" will observe its LITTLE setting silently
      overridden whenever a big thread lands on the sibling.

------------------------------------------------------------------------------------
STATUS OF THE NUMBERS
------------------------------------------------------------------------------------
  Every constant is in the CONSTANTS block below with a `# source:` line. They fall in
  three classes:
      [ARK]    published Intel spec for i7-8550U         -- hard numbers
      [PUB]    published/derivable for this class of part -- soft but grounded
      [ASSUME] an assumption, to be CALIBRATED against measurement (see --calibrate)
  The qualitative conclusions (P1-P4) depend on the SHAPE of V(f) and on the existence
  of the shared rail, not on the exact magnitude of C_eff / k_leak. --calibrate refits
  C_eff, k_leak and the uncore floor from measured RAPL data and reprints everything.

Usage:
    python3 sim/rail_model.py
    python3 sim/rail_model.py --json
    python3 sim/rail_model.py --calibrate data/rapl_samples.csv
    python3 sim/rail_model.py --plot out/figs
Stdlib + optional matplotlib only. No numpy/scipy.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import sys

# =====================================================================================
# CONSTANTS BLOCK
# Every printed claim in this file traces back to one of these.
# =====================================================================================

# ---- Part identity ------------------------------------------------------------------
PART_NAME = "Intel Core i7-8550U (Kaby Lake-R)"
N_PHYS_CORES = 4                 # source: [ARK] i7-8550U is 4 cores / 8 threads
N_LOGICAL_CPUS = 8               # source: [ARK] SMT2
SMT_SIBLING_STRIDE = 4           # source: [ASSUME] Linux enumerates cpu{i} and cpu{i+4}
                                 #   as siblings of physical core i on this topology.
                                 #   Verify with /sys/devices/system/cpu/cpu0/topology/
                                 #   thread_siblings_list before trusting placement code.

# ---- Frequency domain ---------------------------------------------------------------
F_MIN_HZ = 400e6                 # source: [ARK] minimum P-state (LFM) of this SKU family
F_BASE_HZ = 1800e6               # source: [ARK] i7-8550U base frequency 1.80 GHz
F_TURBO_MAX_HZ = 4000e6          # source: [ARK] max single-core turbo 4.00 GHz
# Turbo bins by number of simultaneously active physical cores.
TURBO_BINS_HZ = {                # source: [PUB] i7-8550U published turbo ratios
    1: 4000e6,
    2: 4000e6,
    3: 3900e6,
    4: 3700e6,
}
F_LITTLE_HZ = 800e6              # source: [ASSUME] the frequency an EPP=255 / low-HWP-max
                                 #   "LITTLE" core is expected to settle at under a light
                                 #   background task. Chosen as 2x LFM; calibrate.

# ---- Voltage-frequency curve V(f) ---------------------------------------------------
# Anchors for VccCore on a 15 W Kaby Lake-R U part, (MHz, volts).
# source: [PUB] typical VID/VccCore range for 14nm++ client U-parts is ~0.65 V at LFM to
#   ~1.15 V at max single-core turbo; intermediate points follow the usual
#   roughly-linear-then-steepening VF shape of Intel 14nm client silicon.
#   These are the single most load-bearing constants in the model -- if the real part's
#   VF curve is flatter, the rail tax shrinks; if steeper, it grows. Measure with
#   MSR 0x198 (IA32_PERF_STATUS) VID field to replace these.
VF_ANCHORS = [
    (400.0, 0.650),
    (800.0, 0.680),
    (1200.0, 0.725),
    (1800.0, 0.830),   # base clock
    (2400.0, 0.925),
    (3000.0, 1.020),
    (3400.0, 1.075),
    (3700.0, 1.115),   # all-core turbo
    (4000.0, 1.150),   # 1-core turbo
]

# ---- Dynamic power ------------------------------------------------------------------
# P_dyn(core) = activity * C_EFF * V_rail^2 * f_GHz     [W], with C_EFF in W/(V^2*GHz).
C_EFF_W_PER_V2_GHZ = 2.20        # source: [ASSUME, derived] chosen so that 4 cores at
                                 #   base 1.80 GHz / V=0.830 / activity 1.0 give
                                 #   4 * 2.20 * 0.830^2 * 1.8 = 10.9 W of core dynamic
                                 #   power, which together with leakage + uncore lands
                                 #   the package near the 15 W PL1 the part is specified
                                 #   to sustain at base clock. Primary --calibrate target.

# ---- Leakage ------------------------------------------------------------------------
# P_leak(core) = K_LEAK * V * exp(V / VT_EFF) * temp_factor(T)      [W]
# Rationale for the form: subthreshold leakage current is exponential in
# (V_gs - V_th)/nkT and V_th falls with V_body/DIBL, so I_leak grows super-linearly with
# supply; multiplying by V converts current to power. The exp() is the honest part --
# it is what makes a 1.15 V rail expensive for an idle-ish core. A purely linear-in-V
# leakage term was considered and rejected because it would understate exactly the
# effect under test (it would flatter the shared-rail case).
VT_EFF_V = 0.300                 # source: [ASSUME] effective thermal/DIBL scale voltage.
                                 #   0.30 V gives ~9x leakage growth from 0.65 V to
                                 #   1.15 V, consistent with the order of magnitude
                                 #   reported for 14nm class logic over that range.
K_LEAK = 0.01035                 # source: [ASSUME, derived] set so that a single core at
                                 #   V=1.15 V and 60 C leaks ~0.55 W, i.e. ~2.2 W across
                                 #   4 cores at full turbo, ~15% of a 15 W package.
                                 #   Second --calibrate target.
T_REF_C = 60.0                   # source: [ASSUME] reference junction temp for K_LEAK.
T_DEFAULT_C = 60.0               # source: [ASSUME] operating temp used by experiments.
LEAK_TEMP_DOUBLING_C = 25.0      # source: [PUB] leakage roughly doubles per ~20-30 C on
                                 #   this class of process; 25 C used as the midpoint.
C6_LEAK_RESIDUAL = 0.10          # source: [ASSUME] a core in C6 is power-gated, but the
                                 #   gate is imperfect and the core's share of always-on
                                 #   logic remains. 10% of active-state leakage.
ACTIVITY_C6_EPS = 1e-6           # activity below this is treated as "core in C6"

# ---- Uncore -------------------------------------------------------------------------
# The uncore is deliberately split into the part that IS on the shared core rail (ring +
# LLC slices) and the part that is not (System Agent / IMC / display, on VccSA/VccIO).
# This split is the reason a "LITTLE" core cannot escape the big core's voltage even
# indirectly: the fabric it talks to is also dragged up.
P_SA_FLOOR_W = 0.90              # source: [ASSUME] System Agent + IMC + PLLs + always-on
                                 #   package logic while the package is in C0. On a 15 W
                                 #   U part this is the dominant term at low load.
                                 #   Third --calibrate target.
P_PKG_C6_W = 0.15                # source: [ASSUME] package power when all cores are in
                                 #   C6 and the package is in a deep PC-state.
C_RING_W_PER_V2_GHZ = 0.55       # source: [ASSUME] effective switching capacitance of the
                                 #   ring + LLC slices, in the same units as C_EFF.
F_RING_MIN_HZ = 800e6            # source: [ASSUME] ring floor while package is in C0
F_RING_MAX_HZ = 3900e6           # source: [ASSUME] ring clock caps just under max core
                                 #   turbo on this generation; ring tracks the fastest
                                 #   active core.
K_UNCORE_TRAFFIC_W_PER_GHZ = 0.12  # source: [ASSUME] incremental LLC/memory traffic power
                                 #   per unit of aggregate active core-GHz. Stands in for
                                 #   a real MPKI-driven term; the experiments here use
                                 #   compile-like workloads so it is roughly constant.

# ---- Package power limits -----------------------------------------------------------
PL1_W = 15.0                     # source: [ARK] i7-8550U configurable TDP-up nominal 15 W
PL2_W = 25.0                     # source: [PUB] typical OEM PL2 for this SKU
TAU_S = 28.0                     # source: [PUB] typical OEM tau

# ---- Workload definition (Experiments B and C) --------------------------------------
W_COMPILE_GCYCLES = 120.0        # source: [ASSUME] total CPU work of the `make -j` job,
                                 #   in giga-core-cycles. Sized so that the all-core,
                                 #   PL1-limited configuration finishes comfortably
                                 #   inside the deadline while the 1-core one does not.
W_LIGHT_GCYCLES_PER_TASK = 15.0  # source: [ASSUME] work each background/QoS task must
                                 #   complete within the horizon (e.g. a compositor, an
                                 #   audio thread, a media decode). Deliberately large
                                 #   enough that the background is not a rounding error
                                 #   next to the compile -- otherwise the partition
                                 #   sweep degenerates into a plain frequency sweep.
N_LIGHT_TASKS = 3                # source: [ASSUME] number of background QoS tasks
HORIZON_S = 30.0                 # source: [ASSUME] deadline for BOTH the compile and the
                                 #   background work, and the minimum accounting window.
                                 #   Configurations that miss it are infeasible: without
                                 #   a deadline "run everything at f_min forever" wins
                                 #   trivially and the experiment says nothing.

# ---- Numerics -----------------------------------------------------------------------
FREQ_SWEEP_STEP_HZ = 25e6
POWER_CAP_TOL_W = 1e-4

CONSTANT_SOURCES = {
    "N_PHYS_CORES": "ARK", "F_MIN_HZ": "ARK", "F_BASE_HZ": "ARK",
    "F_TURBO_MAX_HZ": "ARK", "TURBO_BINS_HZ": "PUB", "PL1_W": "ARK", "PL2_W": "PUB",
    "VF_ANCHORS": "PUB", "C_EFF_W_PER_V2_GHZ": "ASSUME", "K_LEAK": "ASSUME",
    "VT_EFF_V": "ASSUME", "P_SA_FLOOR_W": "ASSUME", "C_RING_W_PER_V2_GHZ": "ASSUME",
    "K_UNCORE_TRAFFIC_W_PER_GHZ": "ASSUME", "F_LITTLE_HZ": "ASSUME",
    "C6_LEAK_RESIDUAL": "ASSUME", "SMT_SIBLING_STRIDE": "ASSUME",
}

# Mutable copies the calibrator overwrites. The physics functions read THESE, never the
# module-level constants, so --calibrate changes every downstream number consistently.
PARAMS = {
    "C_eff": C_EFF_W_PER_V2_GHZ,
    "k_leak": K_LEAK,
    "p_sa_floor": P_SA_FLOOR_W,
}


# =====================================================================================
# PHYSICS
# =====================================================================================

def v_of_f(f_hz: float) -> float:
    """Core supply voltage required to sustain frequency f, piecewise-linear on the
    VF_ANCHORS table, clamped outside the anchored range."""
    f_mhz = f_hz / 1e6
    if f_mhz <= VF_ANCHORS[0][0]:
        return VF_ANCHORS[0][1]
    if f_mhz >= VF_ANCHORS[-1][0]:
        return VF_ANCHORS[-1][1]
    for (f0, v0), (f1, v1) in zip(VF_ANCHORS, VF_ANCHORS[1:]):
        if f0 <= f_mhz <= f1:
            t = (f_mhz - f0) / (f1 - f0)
            return v0 + t * (v1 - v0)
    return VF_ANCHORS[-1][1]  # unreachable


def leak_shape(v: float) -> float:
    """Unit-less leakage shape g(V) = V * exp(V / VT_EFF). Multiplied by k_leak (W)."""
    return v * math.exp(v / VT_EFF_V)


def leak_temp_factor(temp_c: float) -> float:
    """Leakage doubles every LEAK_TEMP_DOUBLING_C above T_REF_C."""
    return 2.0 ** ((temp_c - T_REF_C) / LEAK_TEMP_DOUBLING_C)


def core_leakage_w(v: float, active: bool, temp_c: float = T_DEFAULT_C) -> float:
    g = PARAMS["k_leak"] * leak_shape(v) * leak_temp_factor(temp_c)
    return g if active else g * C6_LEAK_RESIDUAL


def package_power(core_states, shared_rail: bool = True, temp_c: float = T_DEFAULT_C):
    """Package power breakdown for a set of physical cores.

    core_states : list of (freq_hz, activity) tuples, one per PHYSICAL core.
                  activity is the 0..1 fraction of wall time the core is not
                  clock-gated (i.e. C0 residency of that core).
    shared_rail : True  -> single VccCore for the whole package (the real i7-8550U).
                  False -> per-core (per-cluster) rails, the big.LITTLE counterfactual.

    Returns dict with keys: dyn, leak, uncore, total, v_rail, f_max_active_hz,
    plus uncore sub-breakdown (uncore_sa, uncore_ring, uncore_traffic).
    """
    active = [(f, a) for (f, a) in core_states if a > ACTIVITY_C6_EPS]

    if not active:
        # Whole package idle: everything gated, deep PC-state.
        v_idle = v_of_f(F_MIN_HZ)
        leak = sum(core_leakage_w(v_idle, False, temp_c) for _ in core_states)
        return {
            "dyn": 0.0, "leak": leak,
            "uncore": P_PKG_C6_W, "uncore_sa": P_PKG_C6_W,
            "uncore_ring": 0.0, "uncore_traffic": 0.0,
            "total": leak + P_PKG_C6_W,
            "v_rail": v_idle, "f_max_active_hz": 0.0,
        }

    f_max_active = max(f for f, _ in active)
    v_rail = v_of_f(f_max_active)

    dyn = 0.0
    leak = 0.0
    for (f, a) in core_states:
        is_active = a > ACTIVITY_C6_EPS
        # THE crux: on a shared rail every core -- including the "LITTLE" one -- pays
        # V(f_max_active). On a split rail it pays V(its own f).
        v_core = v_rail if shared_rail else v_of_f(f if is_active else F_MIN_HZ)
        if is_active:
            dyn += a * PARAMS["C_eff"] * (v_core ** 2) * (f / 1e9)
        leak += core_leakage_w(v_core, is_active, temp_c)

    # Ring / LLC. On client Skylake+ the ring is on VccCore and its clock tracks the
    # fastest active core. In the split-rail counterfactual we CHARGE THE SAME RING COST
    # (the interconnect still has to serve the fast cluster) -- this is deliberately
    # conservative: it can only understate, never overstate, the shared-rail penalty.
    f_ring = min(max(f_max_active, F_RING_MIN_HZ), F_RING_MAX_HZ)
    v_ring = v_of_f(f_ring)
    uncore_ring = C_RING_W_PER_V2_GHZ * (v_ring ** 2) * (f_ring / 1e9)

    agg_active_ghz = sum(a * f / 1e9 for (f, a) in core_states if a > ACTIVITY_C6_EPS)
    uncore_traffic = K_UNCORE_TRAFFIC_W_PER_GHZ * agg_active_ghz

    uncore_sa = PARAMS["p_sa_floor"]
    uncore = uncore_sa + uncore_ring + uncore_traffic

    return {
        "dyn": dyn, "leak": leak, "uncore": uncore,
        "uncore_sa": uncore_sa, "uncore_ring": uncore_ring,
        "uncore_traffic": uncore_traffic,
        "total": dyn + leak + uncore,
        "v_rail": v_rail, "f_max_active_hz": f_max_active,
    }


def turbo_limit_hz(n_active_cores: int) -> float:
    """Published turbo ceiling for a given number of simultaneously active cores."""
    if n_active_cores <= 0:
        return F_MIN_HZ
    n = min(n_active_cores, max(TURBO_BINS_HZ))
    return TURBO_BINS_HZ[n]


def freq_under_power_cap(n_active, activity, f_ceiling_hz, cap_w=PL1_W,
                         shared_rail=True, temp_c=T_DEFAULT_C, others=None):
    """Highest common frequency for `n_active` cores at `activity` such that package
    power <= cap_w. `others` is an extra list of (f, a) core states held fixed.
    Bisection on frequency; returns f_hz (>= F_MIN_HZ even if the cap is violated there,
    in which case the cap is simply unachievable and the caller should note it)."""
    others = others or []

    def p_at(f):
        states = [(f, activity)] * n_active + list(others)
        return package_power(states, shared_rail=shared_rail, temp_c=temp_c)["total"]

    if p_at(F_MIN_HZ) >= cap_w:
        return F_MIN_HZ
    if p_at(f_ceiling_hz) <= cap_w:
        return f_ceiling_hz
    lo, hi = F_MIN_HZ, f_ceiling_hz
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        if p_at(mid) > cap_w:
            hi = mid
        else:
            lo = mid
        if hi - lo < 1e5:
            break
    return lo


# =====================================================================================
# PRINTING HELPERS
# =====================================================================================

def hr(title=None, char="=", width=92):
    if title:
        print("\n" + char * width)
        print(title)
        print(char * width)
    else:
        print(char * width)


def fmt_row(cols, widths, aligns=None):
    aligns = aligns or [">"] * len(cols)
    return "  ".join(("{:%s%d}" % (a, w)).format(c) for c, w, a in zip(cols, widths, aligns))


# =====================================================================================
# EXPERIMENT A -- "the rail tax"
# =====================================================================================

def experiment_a(light_activity=0.15, f_light_hz=F_LITTLE_HZ, temp_c=T_DEFAULT_C,
                 max_light_cores=7, verbose=True):
    """One core pinned at turbo (the `make -j` big core). Add N cores running a light
    background task at F_LITTLE. Report the MARGINAL package power of those light tasks
    under the real shared rail vs the big.LITTLE split-rail counterfactual.

    Note on N: the part has 4 physical cores, but per-core EPP is exposed on all 8
    LOGICAL cpus, and the repo's premise treats them as 8 independent knobs. We therefore
    sweep N=1..7 in *logical* terms and map onto physical cores: the first 3 land on
    distinct physical cores, N>3 lands on SMT siblings, which SHARE the big core's clock
    domain (prediction P4). Siblings of the turbo core cannot be slowed at all.
    """
    f_big = turbo_limit_hz(1)
    rows = []
    for n_light in range(1, max_light_cores + 1):
        # Map n_light logical light threads onto physical cores.
        # Physical core 0 hosts the big thread. Its sibling is logical cpu 4.
        # Light threads fill physical cores 1,2,3 first, then double up as siblings.
        n_free = N_PHYS_CORES - 1          # physical cores not hosting the big thread
        phys_light_activity = [0.0] * N_PHYS_CORES
        for k in range(n_light):
            # Threads 0..2 -> distinct physical cores 1,2,3.
            # Threads 3..5 -> the SMT siblings of those same cores (still 3 clock domains).
            # Thread 6      -> the SMT sibling of the BIG core, which cannot be slowed
            #                  down at all: it inherits the big core's 4.0 GHz clock.
            pc = 0 if k >= 2 * n_free else 1 + (k % n_free)
            phys_light_activity[pc] += light_activity

        n_siblings_on_big = max(0, n_light - 2 * n_free)

        def build(shared):
            states = []
            for pc in range(N_PHYS_CORES):
                a_light = min(phys_light_activity[pc], 1.0)
                if pc == 0:
                    # Big core: turbo, already at activity 1.0. A light thread landing on
                    # its SMT sibling adds no marginal POWER in this model (the core is
                    # already un-gated) -- it steals throughput from the compile instead.
                    # That is why the N=7 row shows a suspiciously cheap increment: the
                    # cost has moved from watts into wall-clock, which this experiment
                    # does not price. Experiment B does.
                    states.append((f_big, 1.0))
                else:
                    if a_light > ACTIVITY_C6_EPS:
                        states.append((f_light_hz, a_light))
                    else:
                        states.append((F_MIN_HZ, 0.0))
            return states

        base_states = [(f_big, 1.0)] + [(F_MIN_HZ, 0.0)] * (N_PHYS_CORES - 1)
        with_states = build(True)

        p_base_sh = package_power(base_states, shared_rail=True, temp_c=temp_c)["total"]
        p_with_sh = package_power(with_states, shared_rail=True, temp_c=temp_c)["total"]
        p_base_sp = package_power(base_states, shared_rail=False, temp_c=temp_c)["total"]
        p_with_sp = package_power(with_states, shared_rail=False, temp_c=temp_c)["total"]

        marg_sh = p_with_sh - p_base_sh
        marg_sp = p_with_sp - p_base_sp

        # Reference: no partitioning at all -- the light tasks run on cores that are
        # ALSO at turbo frequency (what you get with no EPP scheme whatsoever).
        naive_states = [(f_big, 1.0)]
        for pc in range(1, N_PHYS_CORES):
            a = min(phys_light_activity[pc], 1.0)
            naive_states.append((f_big, a) if a > ACTIVITY_C6_EPS else (F_MIN_HZ, 0.0))
        p_naive = package_power(naive_states, shared_rail=True, temp_c=temp_c)["total"]
        marg_naive = p_naive - p_base_sh

        save_sh = marg_naive - marg_sh          # saving EPP partitioning actually buys
        save_sp = marg_naive - marg_sp          # saving a true LITTLE cluster would buy
        retained = (save_sh / save_sp) if save_sp > 1e-9 else float("nan")
        rail_tax_w = marg_sh - marg_sp
        ratio = (marg_sh / marg_sp) if marg_sp > 1e-9 else float("inf")

        rows.append({
            "n_light": n_light,
            "n_light_on_big_sibling": n_siblings_on_big,
            "marginal_w_shared": marg_sh,
            "marginal_w_split": marg_sp,
            "marginal_w_no_partition": marg_naive,
            "rail_tax_w": rail_tax_w,
            "cost_ratio_shared_over_split": ratio,
            "saving_retained_frac": retained,
            "saving_destroyed_frac": 1.0 - retained,
            "pkg_w_shared": p_with_sh,
            "pkg_w_split": p_with_sp,
        })

    # Per-core micro-breakdown: one light core, the cleanest statement of the tax.
    v_big = v_of_f(f_big)
    v_lit = v_of_f(f_light_hz)
    one_light_shared = (light_activity * PARAMS["C_eff"] * v_big ** 2 * f_light_hz / 1e9,
                        core_leakage_w(v_big, True, temp_c))
    one_light_split = (light_activity * PARAMS["C_eff"] * v_lit ** 2 * f_light_hz / 1e9,
                       core_leakage_w(v_lit, True, temp_c))

    detail = {
        "f_big_ghz": f_big / 1e9, "v_rail_big_v": v_big,
        "f_light_ghz": f_light_hz / 1e9, "v_light_if_split_v": v_lit,
        "light_activity": light_activity,
        "one_light_core_shared_dyn_w": one_light_shared[0],
        "one_light_core_shared_leak_w": one_light_shared[1],
        "one_light_core_split_dyn_w": one_light_split[0],
        "one_light_core_split_leak_w": one_light_split[1],
        "one_light_core_shared_total_w": sum(one_light_shared),
        "one_light_core_split_total_w": sum(one_light_split),
        "one_light_core_cost_ratio": sum(one_light_shared) / sum(one_light_split),
        "v_squared_penalty": (v_big / v_lit) ** 2,
        "leak_penalty": leak_shape(v_big) / leak_shape(v_lit),
    }

    if verbose:
        hr("EXPERIMENT A -- THE RAIL TAX")
        print("Setup: physical core 0 pinned at %.2f GHz turbo, activity 1.00 (the `make -j`"
              % (f_big / 1e9))
        print("       big core). N light threads at %.2f GHz, activity %.2f each."
              % (f_light_hz / 1e9, light_activity))
        print("Rail voltage with the big core active: V = %.3f V  [VF_ANCHORS]" % v_big)
        print("Rail voltage a true LITTLE cluster would use: V = %.3f V  [VF_ANCHORS]" % v_lit)
        print()
        print("  Single light core, isolated cost:")
        print("    shared rail (real i7-8550U): dyn %.3f W + leak %.3f W = %.3f W"
              % (one_light_shared[0], one_light_shared[1], sum(one_light_shared)))
        print("    split rail  (true LITTLE)  : dyn %.3f W + leak %.3f W = %.3f W"
              % (one_light_split[0], one_light_split[1], sum(one_light_split)))
        print("    => the SAME task costs %.2fx more on the shared rail."
              % detail["one_light_core_cost_ratio"])
        print("       V^2 penalty  = %.2fx   (dynamic)   [C_EFF, VF_ANCHORS]"
              % detail["v_squared_penalty"])
        print("       exp(V) penalty = %.2fx (leakage)   [K_LEAK, VT_EFF_V]"
              % detail["leak_penalty"])
        print()
        w = [3, 6, 11, 11, 11, 10, 8, 11, 10]
        hdr = ["N", "on-SMT", "marg W", "marg W", "marg W", "rail tax",
               "cost", "saving", "saving"]
        hdr2 = ["", "sib", "no-part", "shared", "split", "W", "ratio",
                "retained", "destroyed"]
        print(fmt_row(hdr, w))
        print(fmt_row(hdr2, w))
        print("-" * 92)
        for r in rows:
            print(fmt_row([
                "%d" % r["n_light"],
                "%d" % r["n_light_on_big_sibling"],
                "%.3f" % r["marginal_w_no_partition"],
                "%.3f" % r["marginal_w_shared"],
                "%.3f" % r["marginal_w_split"],
                "%.3f" % r["rail_tax_w"],
                "%.2fx" % r["cost_ratio_shared_over_split"],
                "%.1f%%" % (100 * r["saving_retained_frac"]),
                "%.1f%%" % (100 * r["saving_destroyed_frac"]),
            ], w))
        print()
        print("Columns: 'no-part' = light tasks left at turbo frequency (no EPP scheme).")
        print("         'shared'  = EPP-partitioned LITTLE cores, real single-rail part.")
        print("         'split'   = same placement on a true per-cluster-rail big.LITTLE.")
        print("         'retained'= fraction of big.LITTLE's saving that EPP actually gets.")
        print("PREDICTION P1: the 'destroyed' column is large and roughly constant in N.")

    return {"rows": rows, "detail": detail}


# =====================================================================================
# EXPERIMENT B -- partition sweep at fixed total work
# =====================================================================================

def experiment_b(temp_c=T_DEFAULT_C, apply_pl1=True, verbose=True):
    """Fixed workload: W_COMPILE_GCYCLES of parallel compile work + N_LIGHT_TASKS
    background tasks of W_LIGHT_GCYCLES_PER_TASK each that must complete within
    HORIZON_S. Sweep n_big = 0..N_PHYS_CORES and compute energy-to-solution for the
    shared rail and the split-rail counterfactual.

    Accounting: phase 1 runs [0, T_compile] with big cores at activity 1.0 and little
    cores at whatever activity their background task needs. Phase 2 runs
    [T_compile, HORIZON_S] with big cores in C6 and the background still running.
    Energy = P1*T1 + P2*T2. This makes race-to-idle emerge naturally rather than being
    assumed.
    """
    results = []
    for n_big in range(0, N_PHYS_CORES + 1):
        n_little = N_PHYS_CORES - n_big

        for shared in (True, False):
            # Frequency the big cores actually get.
            f_big_ceiling = turbo_limit_hz(max(n_big, 1))
            if n_big == 0:
                # Degenerate: no big cores -> the compile runs on the little cores.
                f_work = F_LITTLE_HZ
                n_work = n_little
            else:
                f_work = f_big_ceiling
                n_work = n_big

            # Background tasks are spread over the little cores; if there are none,
            # they run on the big cores (at big frequency).
            if n_little > 0:
                f_bg = F_LITTLE_HZ
                n_bg_cores = min(n_little, N_LIGHT_TASKS)
            else:
                f_bg = f_work
                n_bg_cores = min(n_big, N_LIGHT_TASKS)
            bg_cycles_per_core = (N_LIGHT_TASKS * W_LIGHT_GCYCLES_PER_TASK) / max(n_bg_cores, 1)
            # activity needed to finish bg_cycles within the horizon at f_bg
            a_bg = min(1.0, bg_cycles_per_core * 1e9 / (f_bg * HORIZON_S))

            # Under PL1 the compile frequency is reduced until package power fits.
            if apply_pl1 and n_big > 0:
                bg_states_fixed = []
                for i in range(N_PHYS_CORES - n_work):
                    bg_states_fixed.append((f_bg, a_bg) if i < n_bg_cores else (F_MIN_HZ, 0.0))
                f_work = freq_under_power_cap(n_work, 1.0, f_work, cap_w=PL1_W,
                                              shared_rail=shared, temp_c=temp_c,
                                              others=bg_states_fixed)

            t_compile = (W_COMPILE_GCYCLES * 1e9) / (n_work * f_work) if n_work else float("inf")
            # Energy-to-solution must charge for ALL the work, otherwise "run slowly and
            # never finish" wins trivially. The accounting window therefore extends to
            # whichever is longer: the compile's completion, or the background deadline.
            t_end = max(t_compile, HORIZON_S)
            finished_in_horizon = t_compile <= HORIZON_S

            # --- phase 1 ---
            s1 = []
            for i in range(N_PHYS_CORES):
                if i < n_work:
                    s1.append((f_work, 1.0))
                elif i < n_work + n_bg_cores:
                    s1.append((f_bg, a_bg))
                else:
                    s1.append((F_MIN_HZ, 0.0))
            p1 = package_power(s1, shared_rail=shared, temp_c=temp_c)

            # --- phase 2 (compile done, background continues to its deadline) ---
            t2 = max(0.0, t_end - t_compile)
            s2 = []
            for i in range(N_PHYS_CORES):
                if i < n_work:
                    s2.append((F_MIN_HZ, 0.0))
                elif i < n_work + n_bg_cores:
                    s2.append((f_bg, a_bg))
                else:
                    s2.append((F_MIN_HZ, 0.0))
            # if bg was hosted on the work cores, keep it alive there in phase 2
            if n_bg_cores > 0 and n_little == 0:
                s2 = [(f_bg, a_bg)] * n_bg_cores + [(F_MIN_HZ, 0.0)] * (N_PHYS_CORES - n_bg_cores)
            p2 = package_power(s2, shared_rail=shared, temp_c=temp_c)

            t1 = t_compile
            energy = p1["total"] * t1 + p2["total"] * t2

            results.append({
                "n_big": n_big, "n_little": n_little, "shared_rail": shared,
                "f_work_ghz": f_work / 1e9, "f_bg_ghz": f_bg / 1e9,
                "bg_activity": a_bg,
                "t_compile_s": t_compile,
                "t_window_s": t_end,
                "finished_in_horizon": finished_in_horizon,
                "p_phase1_w": p1["total"], "p_phase2_w": p2["total"],
                "v_rail_phase1_v": p1["v_rail"],
                "energy_j": energy,
            })

    shared_rows = [r for r in results if r["shared_rail"]]
    split_rows = [r for r in results if not r["shared_rail"]]

    def best_of(rows):
        """Minimum energy among DEADLINE-FEASIBLE configurations."""
        feas = [r for r in rows if r["finished_in_horizon"]]
        return min(feas or rows, key=lambda r: r["energy_j"])

    best_shared = best_of(shared_rows)
    best_split = best_of(split_rows)

    def interior(rows):
        b = best_of(rows)
        return 0 < b["n_big"] < N_PHYS_CORES

    def all_big(rows):
        return [r for r in rows if r["n_big"] == N_PHYS_CORES][0]

    def spread(rows):
        """Flatness of the feasible energy curve: how much the partition choice can
        possibly matter, as a fraction of the best feasible energy."""
        feas = [r for r in rows if r["finished_in_horizon"]] or rows
        e = [r["energy_j"] for r in feas]
        return (max(e) - min(e)) / min(e)

    # How much is the big/LITTLE partition worth *at all*, on each rail? Measured
    # against the no-partition baseline (every core big, background time-shares them).
    ben_shared = all_big(shared_rows)["energy_j"] - best_shared["energy_j"]
    ben_split = all_big(split_rows)["energy_j"] - best_split["energy_j"]

    # Pure rail tax at each partition point: E(shared) - E(split) with everything else
    # identical. This is the part of big.LITTLE that a single-rail part CANNOT have.
    per_n = []
    for n in range(N_PHYS_CORES + 1):
        rs = [r for r in shared_rows if r["n_big"] == n][0]
        rp = [r for r in split_rows if r["n_big"] == n][0]
        per_n.append({
            "n_big": n,
            "energy_j_shared": rs["energy_j"], "energy_j_split": rp["energy_j"],
            "rail_tax_j": rs["energy_j"] - rp["energy_j"],
            "rail_tax_pct": 100.0 * (rs["energy_j"] - rp["energy_j"]) / rp["energy_j"],
            "feasible": rs["finished_in_horizon"] and rp["finished_in_horizon"],
        })

    summary = {
        "best_n_big_shared": best_shared["n_big"],
        "best_energy_j_shared": best_shared["energy_j"],
        "best_n_big_split": best_split["n_big"],
        "best_energy_j_split": best_split["energy_j"],
        "interior_optimum_shared": interior(shared_rows),
        "interior_optimum_split": interior(split_rows),
        "energy_gap_j": best_shared["energy_j"] - best_split["energy_j"],
        "energy_gap_pct": 100.0 * (best_shared["energy_j"] - best_split["energy_j"])
                          / best_split["energy_j"],
        "partition_benefit_j_shared": ben_shared,
        "partition_benefit_j_split": ben_split,
        "partition_benefit_retained_frac": (ben_shared / ben_split) if ben_split > 1e-9
                                            else float("nan"),
        "curve_spread_frac_shared": spread(shared_rows),
        "curve_spread_frac_split": spread(split_rows),
        "rail_tax_by_n_big": per_n,
        "pl1_applied": apply_pl1,
    }

    if verbose:
        hr("EXPERIMENT B -- PARTITION SWEEP AT FIXED WORK")
        print("Work: %.0f Gcycles of compile + %d background tasks x %.1f Gcycles,"
              % (W_COMPILE_GCYCLES, N_LIGHT_TASKS, W_LIGHT_GCYCLES_PER_TASK))
        print("      background deadline %.0f s. PL1 cap %s (%.1f W)."
              % (HORIZON_S, "APPLIED" if apply_pl1 else "IGNORED", PL1_W))
        print("Energy-to-solution = P1*t_compile + P2*(window - t_compile), where the")
        print("window is max(t_compile, deadline) so ALL the work is always charged for.")
        print()
        w = [5, 6, 8, 8, 7, 9, 8, 9, 11]
        for label, rows in (("SHARED RAIL (real i7-8550U)", shared_rows),
                            ("SPLIT RAIL  (true big.LITTLE counterfactual)", split_rows)):
            print("  " + label)
            print("  " + fmt_row(["nbig", "nlit", "f_work", "f_bg", "V_rail",
                                  "t_comp s", "win s", "P1 W", "Energy J"], w))
            print("  " + "-" * 78)
            best = best_of(rows)
            for r in rows:
                mark = " <-- min (feasible)" if r is best else ""
                nofin = "  INFEASIBLE: misses the %.0fs deadline" % HORIZON_S \
                    if not r["finished_in_horizon"] else ""
                print("  " + fmt_row([
                    "%d" % r["n_big"], "%d" % r["n_little"],
                    "%.2f" % r["f_work_ghz"], "%.2f" % r["f_bg_ghz"],
                    "%.3f" % r["v_rail_phase1_v"],
                    "%.2f" % r["t_compile_s"],
                    "%.1f" % r["t_window_s"],
                    "%.2f" % r["p_phase1_w"],
                    "%.1f" % r["energy_j"],
                ], w) + mark + nofin)
            print()
        print("  PURE RAIL TAX at identical placement (same n_big, same frequencies):")
        w2 = [6, 13, 13, 12, 10, 10]
        print("  " + fmt_row(["nbig", "E shared J", "E split J", "rail tax J",
                              "rail tax", "feasible"], w2))
        print("  " + "-" * 70)
        for r in summary["rail_tax_by_n_big"]:
            print("  " + fmt_row([
                "%d" % r["n_big"], "%.1f" % r["energy_j_shared"],
                "%.1f" % r["energy_j_split"], "%.1f" % r["rail_tax_j"],
                "%.1f%%" % r["rail_tax_pct"], "yes" if r["feasible"] else "no"], w2))
        print()
        print("  shared rail: optimum at n_big=%d, %.1f J  (interior optimum: %s)"
              % (summary["best_n_big_shared"], summary["best_energy_j_shared"],
                 summary["interior_optimum_shared"]))
        print("  split  rail: optimum at n_big=%d, %.1f J  (interior optimum: %s)"
              % (summary["best_n_big_split"], summary["best_energy_j_split"],
                 summary["interior_optimum_split"]))
        print("  energy penalty of the shared rail at its own optimum: %+.1f J (%+.1f%%)"
              % (summary["energy_gap_j"], summary["energy_gap_pct"]))
        print("  value of partitioning at all (vs all-big): shared %.1f J, split %.1f J"
              % (summary["partition_benefit_j_shared"], summary["partition_benefit_j_split"]))
        print("  => the shared rail retains %.0f%% of the partition's value; the missing"
              % (100 * summary["partition_benefit_retained_frac"]))
        print("     %.0f%% is exactly what a per-cluster rail would have bought."
              % (100 * (1 - summary["partition_benefit_retained_frac"])))
        print("  feasible-curve spread (max/min-1): shared %.1f%%, split %.1f%%"
              % (100 * summary["curve_spread_frac_shared"],
                 100 * summary["curve_spread_frac_split"]))
        print()
        print("PREDICTION P2 (as the model actually computes it -- note this is WEAKER than")
        print("  the naive 'shared rail collapses to an endpoint' claim, and the difference")
        print("  matters):")
        print("  * BOTH rails show an interior optimum here, but for different reasons.")
        print("    On the SPLIT rail the interior optimum is a genuine voltage effect: the")
        print("    LITTLE cores sit at %.3f V. On the SHARED rail the interior optimum is"
              % v_of_f(F_LITTLE_HZ))
        print("    produced ONLY by (a) the linear-in-f dynamic term and (b) the PL1 cap")
        print("    redistributing frequency -- V_rail stays pinned by the big core (see the")
        print("    V_rail column: it never falls below %.3f V for any n_big>0)."
              % min(r["v_rail_phase1_v"] for r in shared_rows if r["n_big"] > 0))
        print("  * The falsifiable content is the RAIL TAX table above and the retained")
        print("    fraction: if the measured energy-vs-partition curve on the i7-8550U is")
        print("    deeper than the shared-rail column predicts, this model is wrong.")
        print("  * Note also how strongly PL1 flattens the curve: on a %.0f W part the"
              % PL1_W)
        print("    package power cap is already doing globally what big.LITTLE would do")
        print("    per-cluster, which is a large part of why the partition adds so little.")

    return {"rows": results, "summary": summary}


# =====================================================================================
# EXPERIMENT C -- uncore floor and the race-to-idle crossover
# =====================================================================================

def experiment_c(n_cores=N_PHYS_CORES, work_gcycles=W_COMPILE_GCYCLES,
                 temp_c=T_DEFAULT_C, verbose=True):
    """Energy-to-solution for a fixed amount of work vs the frequency it is run at,
    with and without the fixed uncore/package floor. Reports the crossover (energy-
    optimal) frequency. Without a floor, energy falls monotonically toward f_min
    (V^2 scaling wins). With the floor, there is an interior optimum: below it, the
    floor paid over a longer runtime dominates. That optimum is the race-to-idle point.
    """
    f_ceiling = turbo_limit_hz(n_cores)
    curve = []
    f = F_MIN_HZ
    while f <= f_ceiling + 1:
        states = [(f, 1.0)] * n_cores + [(F_MIN_HZ, 0.0)] * (N_PHYS_CORES - n_cores)
        p = package_power(states, shared_rail=True, temp_c=temp_c)
        t = (work_gcycles * 1e9) / (n_cores * f)
        e_full = p["total"] * t
        # Same run with the *fixed* (non-frequency-scaling) floor removed. The
        # frequency-scaling uncore terms (ring, traffic) stay, since they are not a floor.
        e_nofloor = (p["total"] - p["uncore_sa"]) * t
        # Core-only (no uncore at all), for reference.
        e_coreonly = (p["dyn"] + p["leak"]) * t
        curve.append({
            "f_ghz": f / 1e9, "v_v": p["v_rail"], "t_s": t,
            "p_w": p["total"], "p_dyn_w": p["dyn"], "p_leak_w": p["leak"],
            "p_uncore_w": p["uncore"],
            "e_j": e_full, "e_j_no_fixed_floor": e_nofloor, "e_j_core_only": e_coreonly,
        })
        f += FREQ_SWEEP_STEP_HZ

    best = min(curve, key=lambda r: r["e_j"])
    best_nofloor = min(curve, key=lambda r: r["e_j_no_fixed_floor"])
    best_coreonly = min(curve, key=lambda r: r["e_j_core_only"])
    e_at_min = [r for r in curve if abs(r["f_ghz"] - F_MIN_HZ / 1e9) < 1e-6][0]

    summary = {
        "n_cores": n_cores,
        "work_gcycles": work_gcycles,
        "crossover_f_ghz": best["f_ghz"],
        "crossover_v_v": best["v_v"],
        "crossover_energy_j": best["e_j"],
        "crossover_runtime_s": best["t_s"],
        "f_opt_ghz_without_fixed_floor": best_nofloor["f_ghz"],
        "f_opt_ghz_core_only": best_coreonly["f_ghz"],
        "energy_at_f_min_j": e_at_min["e_j"],
        "energy_penalty_of_running_at_f_min_pct":
            100.0 * (e_at_min["e_j"] - best["e_j"]) / best["e_j"],
        "uncore_share_at_f_min_pct": 100.0 * e_at_min["p_uncore_w"] / e_at_min["p_w"],
        "uncore_share_at_crossover_pct": 100.0 * best["p_uncore_w"] / best["p_w"],
    }

    if verbose:
        hr("EXPERIMENT C -- THE UNCORE FLOOR AND THE RACE-TO-IDLE CROSSOVER")
        print("Fixed work %.0f Gcycles on %d cores, swept over frequency."
              % (work_gcycles, n_cores))
        print("Fixed floor = System Agent/IMC/always-on = %.2f W [P_SA_FLOOR_W], not under"
              % PARAMS["p_sa_floor"])
        print("EPP control. Ring and traffic terms scale with f and stay in all columns.")
        print()
        w = [7, 6, 7, 8, 8, 8, 8, 10, 12, 11]
        print(fmt_row(["f GHz", "V", "t s", "P dyn", "P leak", "P unc", "P tot",
                       "E J", "E J no-floor", "E J core"], w))
        print("-" * 92)
        step = max(1, len(curve) // 24)
        shown = set()
        for i, r in enumerate(curve):
            if i % step and r is not best and r is not curve[-1]:
                continue
            if r["f_ghz"] in shown:
                continue
            shown.add(r["f_ghz"])
            mark = "  <-- crossover" if r is best else ""
            print(fmt_row([
                "%.3f" % r["f_ghz"], "%.3f" % r["v_v"], "%.2f" % r["t_s"],
                "%.2f" % r["p_dyn_w"], "%.2f" % r["p_leak_w"],
                "%.2f" % r["p_uncore_w"], "%.2f" % r["p_w"],
                "%.1f" % r["e_j"], "%.1f" % r["e_j_no_fixed_floor"],
                "%.1f" % r["e_j_core_only"],
            ], w) + mark)
        print()
        print("  energy-optimal frequency WITH fixed uncore floor : %.3f GHz (V=%.3f, %.1f J)"
              % (summary["crossover_f_ghz"], summary["crossover_v_v"],
                 summary["crossover_energy_j"]))
        print("  energy-optimal frequency WITHOUT fixed floor      : %.3f GHz"
              % summary["f_opt_ghz_without_fixed_floor"])
        print("  energy-optimal frequency, cores only (no uncore)  : %.3f GHz"
              % summary["f_opt_ghz_core_only"])
        print("  running the same work at f_min (%.2f GHz) instead costs %+.1f%% energy"
              % (F_MIN_HZ / 1e9, summary["energy_penalty_of_running_at_f_min_pct"]))
        print("  uncore share of package power: %.1f%% at f_min, %.1f%% at the crossover"
              % (summary["uncore_share_at_f_min_pct"],
                 summary["uncore_share_at_crossover_pct"]))
        print()
        print("PREDICTION P3: the crossover is well above f_min, so a 'LITTLE' core parked")
        print("  at 400-800 MHz is energy-INEFFICIENT for throughput work even ignoring the")
        print("  shared rail. It only helps for latency-insensitive work that would")
        print("  otherwise keep the package out of a deep C-state anyway.")

    return {"curve": curve, "summary": summary}


# =====================================================================================
# CALIBRATION -- plain normal-equations least squares, stdlib only
# =====================================================================================

def _solve_linear(A, b):
    """Solve A x = b for a small dense square system via Gaussian elimination with
    partial pivoting. A is a list of rows, b a list. Returns x or None if singular."""
    n = len(b)
    M = [list(A[i]) + [b[i]] for i in range(n)]
    for col in range(n):
        piv = max(range(col, n), key=lambda r: abs(M[r][col]))
        if abs(M[piv][col]) < 1e-14:
            return None
        M[col], M[piv] = M[piv], M[col]
        pv = M[col][col]
        for r in range(col + 1, n):
            fac = M[r][col] / pv
            if fac == 0.0:
                continue
            for c in range(col, n + 1):
                M[r][c] -= fac * M[col][c]
    x = [0.0] * n
    for r in range(n - 1, -1, -1):
        s = M[r][n] - sum(M[r][c] * x[c] for c in range(r + 1, n))
        x[r] = s / M[r][r]
    return x


def _fnum(s):
    """Parse a CSV cell to float; return None for missing/NaN/blank/garbage."""
    if s is None:
        return None
    s = s.strip()
    if s == "" or s.lower() in ("nan", "na", "n/a", "null", "-", "none"):
        return None
    try:
        v = float(s)
    except ValueError:
        return None
    if math.isnan(v) or math.isinf(v):
        return None
    return v


def load_samples(path):
    """Read the repo's RAPL CSV. Expected columns:
       t_s,pkg_w,core_w,uncore_w,dram_w,psys_w,pkg_c,
       cpu0_mhz..cpu7_mhz,cpu0_busy..cpu7_busy
    Extra columns are ignored; missing ones are tolerated. Returns list of dicts with
    per-PHYSICAL-core (freq_hz, activity) already folded from SMT siblings."""
    samples = []
    skipped = 0
    with open(path, "r", newline="") as fh:
        rdr = csv.DictReader(fh)
        if not rdr.fieldnames:
            return samples, 0
        fields = [f.strip() for f in rdr.fieldnames]
        rdr.fieldnames = fields
        for row in rdr:
            pkg = _fnum(row.get("pkg_w"))
            if pkg is None or pkg <= 0:
                skipped += 1
                continue
            mhz = [_fnum(row.get("cpu%d_mhz" % i)) for i in range(N_LOGICAL_CPUS)]
            busy = [_fnum(row.get("cpu%d_busy" % i)) for i in range(N_LOGICAL_CPUS)]
            if all(m is None for m in mhz):
                skipped += 1
                continue
            # Fold SMT siblings onto physical cores: the pair shares one clock domain,
            # so freq = max(sibling freqs); activity = sum, capped at 1.0.
            phys = []
            ok = True
            for pc in range(N_PHYS_CORES):
                sibs = [pc, pc + SMT_SIBLING_STRIDE]
                fs = [mhz[i] for i in sibs if i < N_LOGICAL_CPUS and mhz[i] is not None]
                bs = [busy[i] for i in sibs if i < N_LOGICAL_CPUS and busy[i] is not None]
                if not fs:
                    ok = False
                    break
                f_hz = max(fs) * 1e6
                a = min(1.0, sum(bs)) if bs else 0.0
                phys.append((f_hz, a))
            if not ok:
                skipped += 1
                continue
            temp = _fnum(row.get("pkg_c"))
            samples.append({
                "t_s": _fnum(row.get("t_s")),
                "pkg_w": pkg,
                "core_w": _fnum(row.get("core_w")),
                "uncore_w": _fnum(row.get("uncore_w")),
                "dram_w": _fnum(row.get("dram_w")),
                "psys_w": _fnum(row.get("psys_w")),
                "temp_c": temp if temp is not None else T_DEFAULT_C,
                "phys": phys,
            })
    return samples, skipped


def calibrate(path, verbose=True):
    """Least-squares fit of (C_eff, k_leak, p_sa_floor) to measured package power.

    Model, linear in the three unknowns:
        pkg_w  ~  C_eff * X1 + k_leak * X2 + p_sa_floor * 1  + R
    where
        X1 = sum_i a_i * V_rail^2 * f_i[GHz]                      (core dynamic)
        X2 = sum_i g(V_i) * temp_factor * (1 or C6 residual)      (core leakage shape)
        R  = ring + traffic power at NOMINAL C_RING/K_UNCORE_TRAFFIC (held fixed, and
             subtracted from the target before fitting, so it does not contaminate the
             three parameters we care about).
    V_rail is taken from the measured max core frequency via VF_ANCHORS -- i.e. the
    shared-rail assumption is BAKED IN here. That is intentional: if the fit residual is
    large and structured, the shared-rail assumption itself is suspect and this model
    should be revisited.
    """
    samples, skipped = load_samples(path)
    if len(samples) < 4:
        raise SystemExit("calibrate: need >= 4 usable rows in %s (got %d, skipped %d)"
                         % (path, len(samples), skipped))

    rows_x, rows_y = [], []
    for s in samples:
        phys = s["phys"]
        temp = s["temp_c"]
        active = [(f, a) for (f, a) in phys if a > ACTIVITY_C6_EPS]
        f_max = max((f for f, _ in active), default=F_MIN_HZ)
        v = v_of_f(f_max)
        x1 = sum(a * (v ** 2) * (f / 1e9) for (f, a) in phys if a > ACTIVITY_C6_EPS)
        tf = leak_temp_factor(temp)
        x2 = sum(leak_shape(v) * tf * (1.0 if a > ACTIVITY_C6_EPS else C6_LEAK_RESIDUAL)
                 for (_, a) in phys)
        x3 = 1.0
        if active:
            f_ring = min(max(f_max, F_RING_MIN_HZ), F_RING_MAX_HZ)
            v_ring = v_of_f(f_ring)
            r = C_RING_W_PER_V2_GHZ * v_ring ** 2 * (f_ring / 1e9)
            r += K_UNCORE_TRAFFIC_W_PER_GHZ * sum(a * f / 1e9 for (f, a) in active)
        else:
            r = 0.0
        rows_x.append([x1, x2, x3])
        rows_y.append(s["pkg_w"] - r)

    # Normal equations: (X^T X) beta = X^T y
    n = 3
    XtX = [[sum(rx[i] * rx[j] for rx in rows_x) for j in range(n)] for i in range(n)]
    Xty = [sum(rx[i] * y for rx, y in zip(rows_x, rows_y)) for i in range(n)]
    # Tiny Tikhonov term guards against a rank-deficient design (e.g. all samples at one
    # frequency, which cannot separate C_eff from the floor).
    trace = sum(XtX[i][i] for i in range(n)) or 1.0
    lam = 1e-9 * trace
    for i in range(n):
        XtX[i][i] += lam
    beta = _solve_linear(XtX, Xty)
    if beta is None:
        raise SystemExit("calibrate: design matrix is singular; the samples do not vary "
                         "enough in frequency/activity to separate the parameters.")

    c_eff, k_leak, p_floor = beta
    clamped = []
    if c_eff <= 0:
        clamped.append("C_eff")
        c_eff = C_EFF_W_PER_V2_GHZ
    if k_leak < 0:
        clamped.append("k_leak")
        k_leak = 0.0
    if p_floor < 0:
        clamped.append("p_sa_floor")
        p_floor = 0.0

    resid = [y - sum(b * x for b, x in zip(beta, rx)) for rx, y in zip(rows_x, rows_y)]
    rms = math.sqrt(sum(r * r for r in resid) / len(resid))
    ybar = sum(rows_y) / len(rows_y)
    sstot = sum((y - ybar) ** 2 for y in rows_y)
    r2 = 1.0 - sum(r * r for r in resid) / sstot if sstot > 1e-12 else float("nan")
    max_abs = max(abs(r) for r in resid)

    old = dict(PARAMS)
    PARAMS["C_eff"] = c_eff
    PARAMS["k_leak"] = k_leak
    PARAMS["p_sa_floor"] = p_floor

    info = {
        "csv": os.path.abspath(path),
        "n_samples_used": len(samples),
        "n_rows_skipped": skipped,
        "fit": {"C_eff": c_eff, "k_leak": k_leak, "p_sa_floor": p_floor},
        "prior": {"C_eff": old["C_eff"], "k_leak": old["k_leak"],
                  "p_sa_floor": old["p_sa_floor"]},
        "clamped_to_prior": clamped,
        "residual_rms_w": rms,
        "residual_max_abs_w": max_abs,
        "r_squared": r2,
    }

    if verbose:
        hr("CALIBRATION -- least squares fit to measured RAPL package power")
        print("source CSV        : %s" % info["csv"])
        print("rows used/skipped : %d / %d" % (len(samples), skipped))
        print()
        w = [14, 14, 14, 10]
        print(fmt_row(["parameter", "prior", "fitted", "ratio"], w, ["<", ">", ">", ">"]))
        print("-" * 60)
        for k, unit in (("C_eff", "W/(V^2*GHz)"), ("k_leak", "W"),
                        ("p_sa_floor", "W")):
            pr, ft = old[k], PARAMS[k]
            print(fmt_row([k + " [" + unit + "]", "%.5g" % pr, "%.5g" % ft,
                           ("%.2fx" % (ft / pr)) if pr else "n/a"],
                          w, ["<", ">", ">", ">"]))
        if clamped:
            print("\n  NOTE: %s came out non-physical (<=0) and was reverted to the prior."
                  % ", ".join(clamped))
            print("        That usually means the samples do not span enough of the")
            print("        frequency/activity space to identify it.")
        print()
        print("residual RMS      : %.3f W   (max |resid| %.3f W)" % (rms, max_abs))
        print("R^2               : %.4f" % r2)
        if rms > 1.5:
            print("WARNING: residual RMS > 1.5 W. Either the VF_ANCHORS curve is wrong for")
            print("         this part, or package power contains a term this model omits")
            print("         (iGPU? PSys vs PKG domain mismatch?). Treat the refitted")
            print("         experiments below as indicative only.")
        print("\nRe-running all experiments with the fitted constants...")

    return info


# =====================================================================================
# PLOTS (optional)
# =====================================================================================

def make_plots(outdir, res_a, res_b, res_c):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as e:
        return {"written": [], "error": "matplotlib unavailable: %s" % e}

    os.makedirs(outdir, exist_ok=True)
    written = []

    # A: marginal power of light tasks, shared vs split
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ns = [r["n_light"] for r in res_a["rows"]]
    ax.plot(ns, [r["marginal_w_no_partition"] for r in res_a["rows"]],
            "o-", label="no partitioning (light tasks at turbo)")
    ax.plot(ns, [r["marginal_w_shared"] for r in res_a["rows"]],
            "s-", label="EPP LITTLE, shared rail (real i7-8550U)")
    ax.plot(ns, [r["marginal_w_split"] for r in res_a["rows"]],
            "^-", label="true big.LITTLE, split rail")
    ax.set_xlabel("number of light background threads")
    ax.set_ylabel("marginal package power [W]")
    ax.set_title("Experiment A: the rail tax (one core at %.1f GHz turbo)"
                 % res_a["detail"]["f_big_ghz"])
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8)
    p = os.path.join(outdir, "expA_rail_tax.png")
    fig.tight_layout(); fig.savefig(p, dpi=130); plt.close(fig); written.append(p)

    # B: energy vs partition
    fig, ax = plt.subplots(figsize=(7, 4.5))
    for shared, style, lbl in ((True, "s-", "shared rail (real)"),
                               (False, "^-", "split rail (counterfactual)")):
        rows = [r for r in res_b["rows"] if r["shared_rail"] == shared]
        rows.sort(key=lambda r: r["n_big"])
        ax.plot([r["n_big"] for r in rows], [r["energy_j"] for r in rows], style, label=lbl)
    ax.set_xlabel("number of cores designated 'big'")
    ax.set_ylabel("energy to solution [J]")
    ax.set_title("Experiment B: partition sweep at fixed work")
    ax.grid(alpha=0.3); ax.legend(fontsize=8)
    p = os.path.join(outdir, "expB_partition_sweep.png")
    fig.tight_layout(); fig.savefig(p, dpi=130); plt.close(fig); written.append(p)

    # C: energy vs frequency
    fig, ax = plt.subplots(figsize=(7, 4.5))
    c = res_c["curve"]
    ax.plot([r["f_ghz"] for r in c], [r["e_j"] for r in c], label="with fixed uncore floor")
    ax.plot([r["f_ghz"] for r in c], [r["e_j_no_fixed_floor"] for r in c],
            "--", label="fixed floor removed")
    ax.plot([r["f_ghz"] for r in c], [r["e_j_core_only"] for r in c],
            ":", label="cores only")
    xo = res_c["summary"]["crossover_f_ghz"]
    ax.axvline(xo, color="k", lw=0.8)
    ax.annotate("crossover %.2f GHz" % xo, xy=(xo, res_c["summary"]["crossover_energy_j"]),
                xytext=(6, 6), textcoords="offset points", fontsize=8)
    ax.set_xlabel("core frequency [GHz]")
    ax.set_ylabel("energy to solution [J]")
    ax.set_title("Experiment C: uncore floor and race-to-idle")
    ax.grid(alpha=0.3); ax.legend(fontsize=8)
    p = os.path.join(outdir, "expC_uncore_floor.png")
    fig.tight_layout(); fig.savefig(p, dpi=130); plt.close(fig); written.append(p)

    return {"written": written, "error": None}


# =====================================================================================
# TOP LEVEL
# =====================================================================================

def print_header():
    hr("rail_model.py -- can ARM big.LITTLE be faked on %s?" % PART_NAME)
    print("Hypothesis H1: per-core HWP/EPP partitioning + sched_ext placement reproduces")
    print("               big.LITTLE energy behaviour on a homogeneous 4C/8T Intel part.")
    print("Model's answer: NO -- and the three experiments below quantify why, before")
    print("               any hardware measurement is taken.")
    print()
    print("Key structural facts encoded in this model:")
    print("  * per-core CLOCK domains exist          -> EPP does change per-core frequency")
    print("  * ONE shared VccCore rail (no FIVR)     -> V_rail = V(max active core freq)")
    print("  * ring/LLC on VccCore, clock tracks max -> the fabric is dragged up too")
    print("  * System Agent floor %.2f W, EPP-immune -> a hard lower bound per unit time"
          % PARAMS["p_sa_floor"])
    print("  * SMT siblings share a clock domain     -> 8 logical CPUs, 4 tunable domains")
    print()
    print("Voltage-frequency curve in use [VF_ANCHORS]:")
    pts = [400e6, 800e6, 1200e6, 1800e6, 2400e6, 3000e6, 3700e6, 4000e6]
    print("   f [GHz] " + " ".join("%7.2f" % (f / 1e9) for f in pts))
    print("   V [V]   " + " ".join("%7.3f" % v_of_f(f) for f in pts))
    print("   V^2     " + " ".join("%7.3f" % (v_of_f(f) ** 2) for f in pts))
    print("   leak g  " + " ".join("%7.3f" % leak_shape(v_of_f(f)) for f in pts))


def print_constants():
    hr("CONSTANTS IN EFFECT")
    w = [30, 14, 8]
    print(fmt_row(["constant", "value", "class"], w, ["<", ">", ">"]))
    print("-" * 56)
    items = [
        ("N_PHYS_CORES", N_PHYS_CORES), ("F_MIN_HZ [GHz]", F_MIN_HZ / 1e9),
        ("F_BASE_HZ [GHz]", F_BASE_HZ / 1e9), ("F_TURBO_MAX_HZ [GHz]", F_TURBO_MAX_HZ / 1e9),
        ("F_LITTLE_HZ [GHz]", F_LITTLE_HZ / 1e9), ("PL1_W", PL1_W), ("PL2_W", PL2_W),
        ("C_eff [W/(V^2*GHz)]", PARAMS["C_eff"]), ("k_leak [W]", PARAMS["k_leak"]),
        ("VT_EFF_V", VT_EFF_V), ("p_sa_floor [W]", PARAMS["p_sa_floor"]),
        ("C_RING_W_PER_V2_GHZ", C_RING_W_PER_V2_GHZ),
        ("K_UNCORE_TRAFFIC_W_PER_GHZ", K_UNCORE_TRAFFIC_W_PER_GHZ),
        ("C6_LEAK_RESIDUAL", C6_LEAK_RESIDUAL),
        ("SMT_SIBLING_STRIDE", SMT_SIBLING_STRIDE),
    ]
    keymap = {"C_eff [W/(V^2*GHz)]": "C_EFF_W_PER_V2_GHZ", "k_leak [W]": "K_LEAK",
              "p_sa_floor [W]": "P_SA_FLOOR_W"}
    for name, val in items:
        base = keymap.get(name, name.split(" [")[0])
        cls = CONSTANT_SOURCES.get(base, "ASSUME")
        print(fmt_row([name, "%.5g" % float(val), cls], w, ["<", ">", ">"]))
    print("\n[ARK] published spec  [PUB] published/derivable for the class  "
          "[ASSUME] calibrate me")


def print_verdict(res_a, res_b, res_c):
    hr("VERDICT")
    d = res_a["detail"]
    a1 = res_a["rows"][0]
    bs = res_b["summary"]
    cs = res_c["summary"]
    print("H1 is REJECTED by the model. Quantitatively:")
    print()
    print("  1. RAIL TAX. With one core at %.2f GHz the rail sits at %.3f V. A 'LITTLE'"
          % (d["f_big_ghz"], d["v_rail_big_v"]))
    print("     thread at %.2f GHz that would cost %.3f W on its own %.3f V rail costs"
          % (d["f_light_ghz"], d["one_light_core_split_total_w"], d["v_light_if_split_v"]))
    print("     %.3f W here -- %.2fx more. Across N=1..%d light threads, EPP retains only"
          % (d["one_light_core_shared_total_w"], d["one_light_core_cost_ratio"],
             len(res_a["rows"])))
    print("     %.0f-%.0f%% of the energy saving a true LITTLE cluster would deliver."
          % (100 * min(r["saving_retained_frac"] for r in res_a["rows"]),
             100 * max(r["saving_retained_frac"] for r in res_a["rows"])))
    print()
    print("  2. PARTITIONING IS WORTH LESS. Shared-rail energy minimises at n_big=%d,"
          % bs["best_n_big_shared"])
    print("     split-rail at n_big=%d; at its own optimum the shared rail burns %+.1f%%"
          % (bs["best_n_big_split"], bs["energy_gap_pct"]))
    print("     more energy for identical work. Partitioning is worth %.1f J on the shared"
          % bs["partition_benefit_j_shared"])
    print("     rail vs %.1f J on a split rail: %.0f%% of its value retained. And the whole"
          % (bs["partition_benefit_j_split"],
             100 * bs["partition_benefit_retained_frac"]))
    print("     feasible curve spans only %.1f%%, so the placement decision the sched_ext"
          % (100 * bs["curve_spread_frac_shared"]))
    print("     scheduler agonises over is worth at most that much.")
    print("     CAVEAT, stated plainly: this workload is compile-dominated, so the rail")
    print("     tax is diluted and PL1 (%s here) flattens the curve further. The"
          % ("applied" if bs["pl1_applied"] else "ignored"))
    print("     background-dominated regime -- the one big.LITTLE actually targets -- is")
    print("     Experiment A, where the tax is %.1fx per LITTLE thread. Re-run with"
          % res_a["detail"]["one_light_core_cost_ratio"])
    print("     --no-pl1 to see the sweep with the cap removed.")
    print()
    print("  3. UNCORE FLOOR. Energy-optimal frequency is %.2f GHz, not f_min. Parking a"
          % cs["crossover_f_ghz"])
    print("     core at %.2f GHz costs %+.1f%% energy for the same work. Uncore is %.0f%%"
          % (F_MIN_HZ / 1e9, cs["energy_penalty_of_running_at_f_min_pct"],
             cs["uncore_share_at_f_min_pct"]))
    print("     of package power down there -- EPP cannot touch it.")
    print()
    print("  4. TOPOLOGY. Only %d frequency domains exist for %d logical CPUs; an EPP=255"
          % (N_PHYS_CORES, N_LOGICAL_CPUS))
    print("     'LITTLE' cpu is silently overridden whenever its SMT sibling goes busy.")
    print()
    print("What the scheme CAN still buy (and what the hardware run should look for):")
    print("  * the linear-in-f dynamic term is real and does save power;")
    print("  * keeping the max-frequency core count low keeps V_rail low, so the useful")
    print("    knob is the MAXIMUM across cores, not the partition -- i.e. a global")
    print("    frequency cap, not a big/LITTLE split;")
    print("  * consolidating work to fewer cores to let others reach C6 saves the C6")
    print("    leakage delta (%.0f%% of active leakage per core) and can let the package"
          % (100 * (1 - C6_LEAK_RESIDUAL)))
    print("    reach a deep PC-state, which is worth more than any EPP setting.")


def run_all(args, calib_info=None):
    if not args.json:
        print_header()
        print_constants()

    res_a = experiment_a(light_activity=args.light_activity,
                         f_light_hz=args.f_little * 1e6,
                         temp_c=args.temp_c, verbose=not args.json)
    res_b = experiment_b(temp_c=args.temp_c, apply_pl1=not args.no_pl1,
                         verbose=not args.json)
    res_c = experiment_c(n_cores=args.exp_c_cores, temp_c=args.temp_c,
                         verbose=not args.json)

    if not args.json:
        print_verdict(res_a, res_b, res_c)

    out = {
        "part": PART_NAME,
        "hypothesis": "per-core EPP partitioning emulates big.LITTLE on a shared-rail "
                      "homogeneous x86 client CPU",
        "verdict": "rejected",
        "params": dict(PARAMS),
        "constants": {
            "n_phys_cores": N_PHYS_CORES, "n_logical_cpus": N_LOGICAL_CPUS,
            "smt_sibling_stride": SMT_SIBLING_STRIDE,
            "f_min_hz": F_MIN_HZ, "f_base_hz": F_BASE_HZ,
            "f_turbo_max_hz": F_TURBO_MAX_HZ, "f_little_hz": args.f_little * 1e6,
            "turbo_bins_hz": {str(k): v for k, v in TURBO_BINS_HZ.items()},
            "vf_anchors_mhz_v": VF_ANCHORS,
            "vt_eff_v": VT_EFF_V, "c_ring_w_per_v2_ghz": C_RING_W_PER_V2_GHZ,
            "k_uncore_traffic_w_per_ghz": K_UNCORE_TRAFFIC_W_PER_GHZ,
            "c6_leak_residual": C6_LEAK_RESIDUAL,
            "pl1_w": PL1_W, "pl2_w": PL2_W, "tau_s": TAU_S,
            "temp_c": args.temp_c,
            "w_compile_gcycles": W_COMPILE_GCYCLES,
            "w_light_gcycles_per_task": W_LIGHT_GCYCLES_PER_TASK,
            "n_light_tasks": N_LIGHT_TASKS, "horizon_s": HORIZON_S,
            "source_class": CONSTANT_SOURCES,
        },
        "experiment_a_rail_tax": res_a,
        "experiment_b_partition_sweep": res_b,
        "experiment_c_uncore_floor": res_c,
        "predictions": {
            "P1_saving_retained_frac_range": [
                min(r["saving_retained_frac"] for r in res_a["rows"]),
                max(r["saving_retained_frac"] for r in res_a["rows"])],
            "P1_single_little_cost_ratio": res_a["detail"]["one_light_core_cost_ratio"],
            "P2_shared_rail_interior_optimum":
                res_b["summary"]["interior_optimum_shared"],
            "P2_split_rail_interior_optimum":
                res_b["summary"]["interior_optimum_split"],
            "P2_partition_benefit_retained_frac":
                res_b["summary"]["partition_benefit_retained_frac"],
            "P2_energy_penalty_at_optimum_pct":
                res_b["summary"]["energy_gap_pct"],
            "P2_feasible_curve_spread_frac_shared":
                res_b["summary"]["curve_spread_frac_shared"],
            "P3_race_to_idle_crossover_ghz":
                res_c["summary"]["crossover_f_ghz"],
            "P3_energy_penalty_at_f_min_pct":
                res_c["summary"]["energy_penalty_of_running_at_f_min_pct"],
            "P4_tunable_freq_domains": N_PHYS_CORES,
            "P4_logical_cpus": N_LOGICAL_CPUS,
        },
    }
    if calib_info:
        out["calibration"] = calib_info

    if args.plot:
        out["plots"] = make_plots(args.plot, res_a, res_b, res_c)
        if not args.json:
            hr("PLOTS")
            if out["plots"]["error"]:
                print("  skipped: %s" % out["plots"]["error"])
            else:
                for p in out["plots"]["written"]:
                    print("  wrote %s" % p)

    if args.json:
        json.dump(out, sys.stdout, indent=2, sort_keys=False, default=str)
        sys.stdout.write("\n")
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=("Shared-voltage-rail power model for %s: predicts whether per-core "
                     "EPP partitioning can emulate ARM big.LITTLE." % PART_NAME),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="All constants are in the CONSTANTS block of this file, each with a "
               "`# source:` comment marking it as [ARK]/[PUB]/[ASSUME].")
    ap.add_argument("--json", action="store_true",
                    help="emit all results as JSON on stdout (suppresses tables)")
    ap.add_argument("--calibrate", metavar="CSV",
                    help="fit C_eff, k_leak and the uncore floor to a measured RAPL CSV, "
                         "then rerun every experiment with the fitted constants")
    ap.add_argument("--plot", metavar="DIR",
                    help="write PNG figures to DIR (skipped if matplotlib is missing)")
    ap.add_argument("--light-activity", type=float, default=0.15,
                    help="activity factor of each light/background thread (default 0.15)")
    ap.add_argument("--f-little", type=float, default=F_LITTLE_HZ / 1e6, metavar="MHZ",
                    help="frequency of a 'LITTLE' core in MHz (default %d)"
                         % int(F_LITTLE_HZ / 1e6))
    ap.add_argument("--temp-c", type=float, default=T_DEFAULT_C,
                    help="junction temperature in C for the leakage model (default %.0f)"
                         % T_DEFAULT_C)
    ap.add_argument("--exp-c-cores", type=int, default=N_PHYS_CORES,
                    help="number of active cores in experiment C (default %d)"
                         % N_PHYS_CORES)
    ap.add_argument("--no-pl1", action="store_true",
                    help="ignore the PL1 package power cap in experiment B")
    args = ap.parse_args(argv)

    if args.exp_c_cores < 1 or args.exp_c_cores > N_PHYS_CORES:
        ap.error("--exp-c-cores must be 1..%d" % N_PHYS_CORES)
    if not (0.0 < args.light_activity <= 1.0):
        ap.error("--light-activity must be in (0, 1]")

    calib_info = None
    if args.calibrate:
        calib_info = calibrate(args.calibrate, verbose=not args.json)

    run_all(args, calib_info)
    return 0


if __name__ == "__main__":
    sys.exit(main())
