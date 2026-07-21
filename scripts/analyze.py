#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-2.0
"""
analyze.py -- statistics and reporting stage for the fake-big-little experiment.

------------------------------------------------------------------------------------
WHAT THIS ANSWERS
------------------------------------------------------------------------------------
The repo asks whether partitioning a HOMOGENEOUS Intel Kaby Lake-R part (i7-8550U,
4C/8T, one package, ONE shared VccCore rail) into "big" and "LITTLE" core sets via
per-core HWP EPP -- plus a sched_ext BPF scheduler that places tasks by QoS class --
saves energy relative to a flat EPP setting.

sim/rail_model.py predicts NO: per-core frequency is controllable but the voltage is
not, so a "LITTLE" core keeps the V^2 dynamic penalty and the exp(V) leakage penalty of
whatever the fastest active core demands. This file must be able to state that
conclusion honestly -- and must be equally capable of reporting a win if the hardware
disagrees with the model. Nothing here assumes the sign of the result.

------------------------------------------------------------------------------------
WHY THE STATISTICS ARE SHAPED THIS WAY
------------------------------------------------------------------------------------
  * MDE OVER p-VALUES. With ~10 reps per arm on a thermally noisy 15 W laptop, the
    interesting quantity is not "is p < 0.05" but "how large would an effect have to be
    before this design could see it at all". A non-significant result with a +-8 %
    minimum detectable effect is evidence of a small-or-absent effect; the same result
    with a +-40 % MDE is evidence of nothing. Every contrast is therefore reported
    alongside its MDE, and any contrast whose CI straddles zero is printed as
    "no detectable difference", never as a bare signed number.
  * BCa BOOTSTRAP. Energy-per-run distributions on a thermally-limited part are skewed
    (a run that trips a thermal event has a long right tail) and n is small. BCa
    corrects for both median bias (z0) and skew-induced non-constant variance (a), and
    unlike the percentile interval it is second-order accurate and transformation
    respecting. When BCa degenerates (all jackknife values equal, or z0 infinite,
    which happens with tiny n or ties) the code falls back to the plain percentile
    interval and SAYS SO in the `ci_method` field -- it is never silently mislabelled.
  * PERMUTATION TEST. Exchangeability under the null is the only assumption; no
    normality, and it matches how the runs were actually randomised.
  * GATES BEFORE EFFECTS. A partitioning experiment where the tasks did not stay
    partitioned, or where the arms ran at different starting temperatures, or where the
    package thermally throttled, proves nothing regardless of its p-value. Those checks
    are printed above the effects, and the verdict text refuses to claim a win when a
    gate failed.

------------------------------------------------------------------------------------
USAGE
------------------------------------------------------------------------------------
    python3 scripts/analyze.py
    python3 scripts/analyze.py --mde
    python3 scripts/analyze.py --json > analysis.json
    python3 scripts/analyze.py --raw data/raw --out-csv data/results.csv \
                               --out-md docs/results.md

Python 3, standard library only. No numpy, no scipy, no pandas: every statistic below
is implemented by hand so the numbers can be audited without a dependency tree.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import random
import sys
from datetime import datetime

# =====================================================================================
# CONFIGURATION
# =====================================================================================

N_BOOT = 10000            # bootstrap resamples for every CI
N_PERM = 10000            # permutations for every two-sample test
SEED = 0                  # random.Random(SEED); fixed so the report is reproducible
ALPHA = 0.05              # two-sided
POWER = 0.80              # for the minimum detectable effect

EPP_BIG_MAX = 128         # epp < 128 => "big" domain, epp >= 128 => "LITTLE" domain
N_CPUS = 8                # logical CPUs on an i7-8550U
SMT_STRIDE = 4            # cpu{i} and cpu{i+SMT_STRIDE} are siblings of one physical core

# Quality-gate thresholds.
MAX_START_TEMP_SPREAD_C = 5.0     # across arms, otherwise thermal state confounds arm
THROTTLE_MARGIN_C = 3.0           # pkg_c_max within this of 100 C => assume throttling
TJMAX_C = 100.0
MAX_CROSS_DOMAIN_FRAC = 0.20      # in a `strict` arm, cross-domain placement budget
DRIFT_RHO = 0.6                   # |Spearman rho| vs rep index above this => drift flag
FREQ_RATIO_REAL = 0.90            # little/big bzy ratio above this => partition not real

GENERATED_MARKER = "<!-- GENERATED FILE -- DO NOT EDIT BY HAND."

# Metrics carried through the full statistical machinery.
# (column, unit, lower_is_better, description); lower_is_better=None means "diagnostic,
# neither direction is a win".
METRICS = [
    ("energy_to_solution_j", "J",   True,  "package energy to complete the workload"),
    ("edp_js",               "J*s", True,  "energy-delay product (pkg_j * wall_s)"),
    ("pkg_j_per_s",          "W",   True,  "mean package power"),
    ("wall_s",               "s",   True,  "time to solution"),
    ("core_j",               "J",   True,  "core-domain energy (the part EPP can touch)"),
    ("rest_frac",            "-",   None,  "share of pkg energy EPP cannot touch"),
    ("wake_us_p99",          "us",  True,  "pinger p99 wake latency (QoS cost)"),
    ("wake_us_p50",          "us",  True,  "pinger median wake latency"),
    ("bzy_mhz_big_mean",     "MHz", None,  "mean busy MHz of the big domain"),
    ("bzy_mhz_little_mean",  "MHz", None,  "mean busy MHz of the LITTLE domain"),
]
METRIC_UNIT = {m[0]: m[1] for m in METRICS}
METRIC_LOWER_BETTER = {m[0]: m[2] for m in METRICS}
METRIC_DESC = {m[0]: m[3] for m in METRICS}
HEADLINE_METRIC = "energy_to_solution_j"

RAIL_EXPERIMENT = "e1-rail"       # the experiment that tests whether the split is real


# =====================================================================================
# NUMERIC PRIMITIVES
# =====================================================================================

def num(x):
    """Coerce to a finite float, or None. NaN/Inf/None/non-numeric all become None.

    Missing-ness is a first-class outcome here: a NaN in a RAPL counter means the
    counter wrapped or the domain is unsupported, not that the value is zero.
    """
    if x is None or isinstance(x, bool):
        return None
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    if math.isnan(v) or math.isinf(v):
        return None
    return v


def clean(xs):
    """Drop missing values from an iterable of maybe-numbers."""
    return [v for v in (num(x) for x in xs) if v is not None]


def mean(xs):
    return sum(xs) / len(xs) if xs else None


def median(xs):
    if not xs:
        return None
    s = sorted(xs)
    n = len(s)
    mid = n // 2
    return s[mid] if n % 2 else 0.5 * (s[mid - 1] + s[mid])


def sd(xs):
    """Sample standard deviation (n-1)."""
    n = len(xs)
    if n < 2:
        return None
    m = sum(xs) / n
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (n - 1))


def pooled_sd(a, b):
    na, nb = len(a), len(b)
    if na < 2 or nb < 2:
        return None
    sa, sb = sd(a), sd(b)
    return math.sqrt(((na - 1) * sa * sa + (nb - 1) * sb * sb) / (na + nb - 2))


def norm_cdf(z):
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def norm_ppf(p):
    """Inverse standard normal CDF (Acklam's rational approximation + one Halley step).

    Accurate to ~1e-15 after refinement; used for the BCa bias/acceleration algebra.
    """
    if p <= 0.0:
        return float("-inf")
    if p >= 1.0:
        return float("inf")
    a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02,
         1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00]
    b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02,
         6.680131188771972e+01, -1.328068155288572e+01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
         -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00]
    d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00,
         3.754408661907416e+00]
    plow, phigh = 0.02425, 1.0 - 0.02425
    if p < plow:
        q = math.sqrt(-2.0 * math.log(p))
        x = (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / \
            ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0)
    elif p > phigh:
        q = math.sqrt(-2.0 * math.log(1.0 - p))
        x = -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / \
            ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0)
    else:
        q = p - 0.5
        r = q * q
        x = (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q / \
            (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1.0)
    # Halley refinement against the true CDF.
    e = norm_cdf(x) - p
    u = e * math.sqrt(2.0 * math.pi) * math.exp(x * x / 2.0)
    return x - u / (1.0 + x * u / 2.0)


def _betacf(a, b, x):
    """Continued fraction for the incomplete beta function (Numerical Recipes form)."""
    MAXIT, EPS, FPMIN = 300, 3.0e-16, 1.0e-300
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < FPMIN:
        d = FPMIN
    d = 1.0 / d
    h = d
    for m in range(1, MAXIT + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < FPMIN:
            d = FPMIN
        c = 1.0 + aa / c
        if abs(c) < FPMIN:
            c = FPMIN
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < FPMIN:
            d = FPMIN
        c = 1.0 + aa / c
        if abs(c) < FPMIN:
            c = FPMIN
        d = 1.0 / d
        de = d * c
        h *= de
        if abs(de - 1.0) < EPS:
            break
    return h


def betainc(a, b, x):
    """Regularised incomplete beta I_x(a, b)."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    lbeta = (math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
             + a * math.log(x) + b * math.log1p(-x))
    front = math.exp(lbeta)
    if x < (a + 1.0) / (a + b + 2.0):
        return front * _betacf(a, b, x) / a
    return 1.0 - math.exp(math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
                          + b * math.log1p(-x) + a * math.log(x)) * _betacf(b, a, 1.0 - x) / b


def t_cdf(t, df):
    if df <= 0:
        return float("nan")
    x = df / (df + t * t)
    p = 0.5 * betainc(df / 2.0, 0.5, x)
    return p if t <= 0 else 1.0 - p


def t_ppf(p, df):
    """Student-t quantile by bisection on t_cdf. Small n makes this matter: at df=18 the
    two-sided 95 % critical value is 2.10, not 1.96, and the MDE scales with it."""
    if df <= 0:
        return float("nan")
    lo, hi = -1.0e3, 1.0e3
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if t_cdf(mid, df) < p:
            lo = mid
        else:
            hi = mid
        if hi - lo < 1e-10:
            break
    return 0.5 * (lo + hi)


def rankdata(xs):
    """Ranks with average ties (needed for Spearman)."""
    n = len(xs)
    order = sorted(range(n), key=lambda i: xs[i])
    ranks = [0.0] * n
    i = 0
    while i < n:
        j = i
        while j + 1 < n and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        avg = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            ranks[order[k]] = avg
        i = j + 1
    return ranks


def pearson(xs, ys):
    n = len(xs)
    if n < 3:
        return None
    mx, my = sum(xs) / n, sum(ys) / n
    sxy = sum((a - mx) * (b - my) for a, b in zip(xs, ys))
    sxx = sum((a - mx) ** 2 for a in xs)
    syy = sum((b - my) ** 2 for b in ys)
    if sxx <= 0 or syy <= 0:
        return None
    return sxy / math.sqrt(sxx * syy)


def spearman(xs, ys):
    """Spearman rho, by hand: Pearson correlation of average-tied ranks."""
    pairs = [(a, b) for a, b in zip(xs, ys) if a is not None and b is not None]
    if len(pairs) < 3:
        return None
    return pearson(rankdata([p[0] for p in pairs]), rankdata([p[1] for p in pairs]))


# =====================================================================================
# RESAMPLING
# =====================================================================================

def _percentile_of_sorted(s, q):
    """Linear-interpolated quantile of an already sorted list, q in [0, 1]."""
    if not s:
        return None
    if len(s) == 1:
        return s[0]
    idx = q * (len(s) - 1)
    lo = int(math.floor(idx))
    hi = min(lo + 1, len(s) - 1)
    frac = idx - lo
    return s[lo] * (1.0 - frac) + s[hi] * frac


def bootstrap_ci(groups, stat, n_boot=N_BOOT, alpha=ALPHA, seed=SEED):
    """BCa bootstrap CI for `stat(groups)`, with a labelled percentile fallback.

    `groups` is a list of independent samples (one group for a mean, two for a
    difference of means); each is resampled with replacement independently, which is the
    right null-free resampling scheme for a two-sample estimand.

    Returns dict(point, lo, hi, method, n_boot). `method` is "BCa" or "percentile" and is
    reported verbatim in the output so a percentile interval is never passed off as BCa.
    """
    out = {"point": None, "lo": None, "hi": None, "method": None, "n_boot": n_boot}
    if any(len(g) < 2 for g in groups) or not groups:
        return out
    try:
        theta = stat(groups)
    except (ZeroDivisionError, ValueError):
        return out
    out["point"] = theta

    rng = random.Random(seed)
    reps = []
    for _ in range(n_boot):
        rs = [rng.choices(g, k=len(g)) for g in groups]
        try:
            reps.append(stat(rs))
        except (ZeroDivisionError, ValueError):
            pass
    if len(reps) < 100:
        return out
    reps.sort()

    # --- bias correction z0: how far the bootstrap distribution's median sits from the
    # point estimate, in normal-deviate units.
    n_less = sum(1 for r in reps if r < theta)
    n_eq = sum(1 for r in reps if r == theta)
    prop = (n_less + 0.5 * n_eq) / len(reps)

    # --- acceleration a: jackknife skewness of the estimator.
    accel = None
    if 0.0 < prop < 1.0:
        jack = []
        ok = True
        for gi, g in enumerate(groups):
            if len(g) < 3:            # leaving one out would leave <2 for the sd/mean
                ok = False
                break
            for i in range(len(g)):
                red = list(groups)
                red[gi] = g[:i] + g[i + 1:]
                try:
                    jack.append(stat(red))
                except (ZeroDivisionError, ValueError):
                    ok = False
                    break
            if not ok:
                break
        if ok and len(jack) >= 3:
            jm = sum(jack) / len(jack)
            d2 = sum((jm - v) ** 2 for v in jack)
            d3 = sum((jm - v) ** 3 for v in jack)
            if d2 > 0:
                accel = d3 / (6.0 * (d2 ** 1.5))

    if accel is not None and 0.0 < prop < 1.0:
        z0 = norm_ppf(prop)
        za_lo, za_hi = norm_ppf(alpha / 2.0), norm_ppf(1.0 - alpha / 2.0)
        denom_lo = 1.0 - accel * (z0 + za_lo)
        denom_hi = 1.0 - accel * (z0 + za_hi)
        if denom_lo != 0.0 and denom_hi != 0.0:
            a1 = norm_cdf(z0 + (z0 + za_lo) / denom_lo)
            a2 = norm_cdf(z0 + (z0 + za_hi) / denom_hi)
            if 0.0 < a1 < a2 < 1.0:
                out["lo"] = _percentile_of_sorted(reps, a1)
                out["hi"] = _percentile_of_sorted(reps, a2)
                out["method"] = "BCa"
                return out

    # Fallback, explicitly labelled.
    out["lo"] = _percentile_of_sorted(reps, alpha / 2.0)
    out["hi"] = _percentile_of_sorted(reps, 1.0 - alpha / 2.0)
    out["method"] = "percentile"
    return out


def mean_ci(xs, seed=SEED):
    return bootstrap_ci([xs], lambda g: sum(g[0]) / len(g[0]), seed=seed)


def diff_ci(control, arm, seed=SEED):
    """CI for mean(arm) - mean(control)."""
    return bootstrap_ci([control, arm],
                        lambda g: sum(g[1]) / len(g[1]) - sum(g[0]) / len(g[0]),
                        seed=seed)


def permutation_p(control, arm, n_perm=N_PERM, seed=SEED):
    """Two-sided permutation test on the difference in means.

    p = (1 + #{|diff*| >= |diff_obs|}) / (n_perm + 1): the add-one keeps p strictly
    positive, which is the honest statement when the null was never actually observed.
    """
    if len(control) < 2 or len(arm) < 2:
        return None
    obs = abs(sum(arm) / len(arm) - sum(control) / len(control))
    pooled = list(control) + list(arm)
    n0 = len(control)
    rng = random.Random(seed)
    hits = 0
    for _ in range(n_perm):
        rng.shuffle(pooled)
        a = pooled[:n0]
        b = pooled[n0:]
        if abs(sum(b) / len(b) - sum(a) / len(a)) >= obs - 1e-15:
            hits += 1
    return (1.0 + hits) / (n_perm + 1.0)


def hedges_g(control, arm):
    """Bias-corrected Cohen's d. The correction matters at n~10: J ~ 0.96."""
    sp = pooled_sd(control, arm)
    if sp is None or sp == 0:
        return None
    d = (sum(arm) / len(arm) - sum(control) / len(control)) / sp
    n = len(control) + len(arm)
    j = 1.0 - 3.0 / (4.0 * n - 9.0)
    return j * d


def mde(control, arm, alpha=ALPHA, power=POWER):
    """Minimum detectable effect for a two-sample two-sided t-test.

        MDE = (t_{1-alpha/2, df} + t_{power, df}) * s_pooled * sqrt(1/n0 + 1/n1)

    This is the standard t-approximation to the noncentral-t power calculation; it is
    accurate to a percent or so for df >= 10 and is conservative-ish below that.
    Interpretation: with this pooled sd and these n, a true effect smaller than MDE would
    be missed more often than not. It is the number that makes a null result mean
    something.
    """
    if len(control) < 2 or len(arm) < 2:
        return None
    sp = pooled_sd(control, arm)
    if sp is None:
        return None
    df = len(control) + len(arm) - 2
    tcrit = t_ppf(1.0 - alpha / 2.0, df)
    tpow = t_ppf(power, df)
    return (tcrit + tpow) * sp * math.sqrt(1.0 / len(control) + 1.0 / len(arm))


# =====================================================================================
# LOADING
# =====================================================================================

def _parse_constant(name):
    """json.load hook: NaN/Infinity/-Infinity all become None (missing), not floats."""
    return None


def find_run_files(raw_dir):
    hits = []
    for dirpath, _dirnames, filenames in os.walk(raw_dir):
        for fn in sorted(filenames):
            if fn.endswith(".json"):
                hits.append(os.path.join(dirpath, fn))
    return sorted(hits)


def load_runs(raw_dir):
    """Read every data/raw/**/*.json. Returns (runs, load_errors)."""
    runs, errors = [], []
    for path in find_run_files(raw_dir):
        try:
            with open(path, "r", encoding="utf-8") as fh:
                obj = json.load(fh, parse_constant=_parse_constant)
        except (OSError, ValueError) as exc:
            errors.append({"file": path, "error": "%s: %s" % (type(exc).__name__, exc)})
            continue
        if not isinstance(obj, dict):
            errors.append({"file": path, "error": "top level is not an object"})
            continue
        obj["_file"] = path
        runs.append(obj)
    return runs, errors


def _get(d, *keys, default=None):
    """Nested dict get that tolerates None at any level."""
    cur = d
    for k in keys:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(k)
        if cur is None:
            return default
    return cur


def _arr(d, key, n=N_CPUS):
    """Fetch a per-CPU array, padded/truncated to n, missing entries as None."""
    v = d.get(key) if isinstance(d, dict) else None
    if not isinstance(v, list):
        return [None] * n
    out = [num(x) for x in v[:n]]
    return out + [None] * (n - len(out))


def split_domains(epp):
    """Derive the big/LITTLE CPU sets from the per-CPU EPP array.

    EPP < 128 => big, >= 128 => LITTLE. If every EPP is equal (the flat arm, or a run
    where the write silently failed) there is no partition and all CPUs are "big" --
    which is the honest description of a flat machine.
    """
    vals = [(i, int(e)) for i, e in enumerate(epp) if e is not None]
    if not vals:
        return list(range(N_CPUS)), [], False
    distinct = {e for _i, e in vals}
    if len(distinct) <= 1:
        return [i for i, _e in vals], [], False
    big = [i for i, e in vals if e < EPP_BIG_MAX]
    little = [i for i, e in vals if e >= EPP_BIG_MAX]
    return big, little, True


def flatten_run(run):
    """One raw run object -> one flat dict of tidy columns."""
    r = {}
    energy = run.get("energy") if isinstance(run.get("energy"), dict) else {}
    pinger = run.get("pinger") if isinstance(run.get("pinger"), dict) else {}
    spin = run.get("spin") if isinstance(run.get("spin"), dict) else {}
    bls = run.get("bls") if isinstance(run.get("bls"), dict) else {}
    factors = run.get("factors") if isinstance(run.get("factors"), dict) else {}
    env = run.get("env") if isinstance(run.get("env"), dict) else {}

    r["file"] = run.get("_file", "")
    r["experiment"] = run.get("experiment") or "(unknown)"
    r["arm"] = run.get("arm") or "(unknown)"
    r["sched"] = factors.get("sched")
    r["epp_mode"] = factors.get("epp")
    r["strict"] = factors.get("strict")
    r["rep"] = num(run.get("rep"))
    r["timestamp"] = run.get("timestamp")
    r["ok"] = run.get("ok")
    r["notes"] = run.get("notes")

    r["kernel"] = env.get("kernel")
    r["on_ac"] = env.get("on_ac")
    r["start_temp_c"] = num(env.get("start_temp_c"))
    r["governor"] = env.get("governor")

    for k in ("wall_s", "pkg_j", "core_j", "uncore_j", "dram_j", "psys_j", "rest_j",
              "avg_pkg_w", "pkg_c_mean", "pkg_c_max"):
        r[k] = num(energy.get(k))
    ec = energy.get("exit_code")
    r["exit_code"] = int(ec) if isinstance(ec, (int, float)) and not isinstance(ec, bool) else None

    # ---- derived energy metrics -----------------------------------------------------
    pkg, wall, rest = r["pkg_j"], r["wall_s"], r["rest_j"]
    r["energy_to_solution_j"] = pkg
    r["edp_js"] = pkg * wall if (pkg is not None and wall is not None) else None
    r["pkg_j_per_s"] = (pkg / wall) if (pkg is not None and wall not in (None, 0)) else None
    # rest_frac: the share of package energy that per-core EPP cannot touch at all
    # (uncore, System Agent, memory controller). A large rest_frac caps the best possible
    # saving from ANY core-frequency policy, so it is a headline diagnostic, not a footnote.
    r["rest_frac"] = (rest / pkg) if (rest is not None and pkg not in (None, 0)) else None

    # ---- per-CPU arrays and domain split --------------------------------------------
    avg_mhz = _arr(energy, "cpu_avg_mhz")
    bzy_mhz = _arr(energy, "cpu_bzy_mhz")
    busy = _arr(energy, "cpu_busy")
    epp = _arr(energy, "epp")
    big, little, partitioned = split_domains(epp)
    r["_big_cpus"], r["_little_cpus"] = big, little
    r["_bzy_mhz"] = bzy_mhz
    r["partitioned_epp"] = partitioned
    r["big_cpus"] = " ".join(str(i) for i in big)
    r["little_cpus"] = " ".join(str(i) for i in little)
    r["n_big_cpus"] = len(big)
    r["n_little_cpus"] = len(little)
    r["bzy_mhz_big_mean"] = mean(clean(bzy_mhz[i] for i in big))
    r["bzy_mhz_little_mean"] = mean(clean(bzy_mhz[i] for i in little))
    b, l = r["bzy_mhz_big_mean"], r["bzy_mhz_little_mean"]
    r["bzy_ratio_little_over_big"] = (l / b) if (b not in (None, 0) and l is not None) else None
    # cpu{i} and cpu{i+4} are SMT siblings sharing ONE clock domain; splitting a pair
    # across domains means one of the two EPP settings is silently ignored.
    sib_split = 0
    for i in range(SMT_STRIDE):
        j = i + SMT_STRIDE
        if epp[i] is not None and epp[j] is not None:
            if (epp[i] < EPP_BIG_MAX) != (epp[j] < EPP_BIG_MAX):
                sib_split += 1
    r["smt_pairs_split"] = sib_split
    for i in range(N_CPUS):
        r["cpu%d_avg_mhz" % i] = avg_mhz[i]
        r["cpu%d_bzy_mhz" % i] = bzy_mhz[i]
        r["cpu%d_busy" % i] = busy[i]
        r["cpu%d_epp" % i] = epp[i]

    # ---- pinger ---------------------------------------------------------------------
    r["pinger_present"] = isinstance(run.get("pinger"), dict)
    r["pinger_n"] = num(pinger.get("n"))
    for k in ("wake_us_p50", "wake_us_p99", "wake_us_p999", "wake_us_mean",
              "work_us_p50", "work_us_p99", "work_us_mean", "target_work_us"):
        r[k] = num(pinger.get(k))

    # ---- spin -----------------------------------------------------------------------
    threads = spin.get("threads") if isinstance(spin.get("threads"), list) else []
    rates = clean(t.get("miters_per_busy_s") for t in threads if isinstance(t, dict))
    r["spin_present"] = isinstance(run.get("spin"), dict)
    r["spin_threads"] = len(threads)
    r["spin_miters_total"] = sum(rates) if rates else None
    r["spin_miters_mean"] = mean(rates)

    # ---- bls (scheduler placement counters) -----------------------------------------
    r["bls_present"] = isinstance(run.get("bls"), dict)
    for k in ("enqueue", "dsq_big", "dsq_little", "cross_domain",
              "run_big_ms", "run_little_ms"):
        r["bls_" + k] = num(bls.get(k))
    enq = r["bls_enqueue"]
    r["bls_cross_frac"] = (r["bls_cross_domain"] / enq) if (
        enq not in (None, 0) and r["bls_cross_domain"] is not None) else None
    rb, rl = r["bls_run_big_ms"], r["bls_run_little_ms"]
    tot = (rb or 0.0) + (rl or 0.0)
    r["bls_run_big_frac"] = (rb / tot) if (rb is not None and tot > 0) else None
    r["bls_run_little_frac"] = (rl / tot) if (rl is not None and tot > 0) else None
    db, dl = r["bls_dsq_big"], r["bls_dsq_little"]
    dtot = (db or 0.0) + (dl or 0.0)
    r["bls_dsq_big_frac"] = (db / dtot) if (db is not None and dtot > 0) else None
    r["_bls_extra"] = {k: num(v) for k, v in bls.items()
                       if k not in ("enqueue", "dsq_big", "dsq_little", "cross_domain",
                                    "run_big_ms", "run_little_ms")}
    return r


# Fixed leading column order; anything discovered later (extra bls keys) is appended
# in sorted order so `git diff` on results.csv stays readable.
BASE_COLUMNS = (
    ["file", "experiment", "arm", "sched", "epp_mode", "strict", "rep", "timestamp",
     "ok", "exit_code", "kernel", "on_ac", "governor", "start_temp_c",
     "wall_s", "pkg_j", "core_j", "uncore_j", "dram_j", "psys_j", "rest_j",
     "avg_pkg_w", "pkg_c_mean", "pkg_c_max",
     "energy_to_solution_j", "edp_js", "pkg_j_per_s", "rest_frac",
     "partitioned_epp", "n_big_cpus", "n_little_cpus", "big_cpus", "little_cpus",
     "smt_pairs_split",
     "bzy_mhz_big_mean", "bzy_mhz_little_mean", "bzy_ratio_little_over_big"]
    + ["cpu%d_%s" % (i, s) for i in range(N_CPUS)
       for s in ("avg_mhz", "bzy_mhz", "busy", "epp")]
    + ["pinger_present", "pinger_n", "wake_us_p50", "wake_us_p99", "wake_us_p999",
       "wake_us_mean", "work_us_p50", "work_us_p99", "work_us_mean", "target_work_us",
       "spin_present", "spin_threads", "spin_miters_total", "spin_miters_mean",
       "bls_present", "bls_enqueue", "bls_dsq_big", "bls_dsq_little", "bls_cross_domain",
       "bls_run_big_ms", "bls_run_little_ms", "bls_cross_frac", "bls_run_big_frac",
       "bls_run_little_frac", "bls_dsq_big_frac",
       "notes"]
)


def write_csv(rows, path):
    extra = sorted({k for r in rows for k in r.get("_bls_extra", {})})
    cols = [c for c in BASE_COLUMNS if c != "notes"] + \
           ["bls_" + k for k in extra] + ["notes"]
    d = os.path.dirname(os.path.abspath(path))
    if d:
        os.makedirs(d, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(cols)
        for r in rows:
            out = []
            for c in cols:
                if c.startswith("bls_") and c[4:] in extra:
                    v = r.get("_bls_extra", {}).get(c[4:])
                else:
                    v = r.get(c)
                if v is None:
                    out.append("")
                elif isinstance(v, bool):
                    out.append("true" if v else "false")
                elif isinstance(v, float):
                    out.append(("%.6f" % v).rstrip("0").rstrip(".") if v == v else "")
                else:
                    out.append(v)
            w.writerow(out)
    return cols


# =====================================================================================
# GROUPING AND SUMMARY STATISTICS
# =====================================================================================

def group_runs(rows):
    """{experiment: {arm: [row, ...]}} with stable ordering."""
    exps = {}
    for r in rows:
        exps.setdefault(r["experiment"], {}).setdefault(r["arm"], []).append(r)
    for arms in exps.values():
        for rs in arms.values():
            rs.sort(key=lambda r: (r["rep"] if r["rep"] is not None else 0,
                                   r["timestamp"] or "", r["file"]))
    return exps


def pick_control(arms):
    """Control arm = (sched=eevdf, epp=flat); else an arm named "control"; else first
    alphabetically. Deterministic so the report does not silently re-baseline."""
    named = sorted(arms)
    for a in named:
        rows = arms[a]
        if rows and rows[0].get("sched") == "eevdf" and rows[0].get("epp_mode") == "flat":
            return a
    for a in named:
        if a.lower() == "control":
            return a
    return named[0] if named else None


def values(rows, metric):
    return clean(r.get(metric) for r in rows)


def summarize_arm(rows, metric, seed=SEED):
    xs = values(rows, metric)
    s = {"metric": metric, "unit": METRIC_UNIT.get(metric, ""),
         "n": len(xs), "n_runs": len(rows), "n_missing": len(rows) - len(xs),
         "mean": mean(xs), "median": median(xs), "sd": sd(xs),
         "min": min(xs) if xs else None, "max": max(xs) if xs else None,
         "ci_lo": None, "ci_hi": None, "ci_method": None}
    if len(xs) >= 2:
        ci = mean_ci(xs, seed=seed)
        s["ci_lo"], s["ci_hi"], s["ci_method"] = ci["lo"], ci["hi"], ci["method"]
    return s


def contrast(control_rows, arm_rows, metric, seed=SEED):
    """Full contrast of one arm against the control for one metric."""
    a = values(control_rows, metric)
    b = values(arm_rows, metric)
    c = {"metric": metric, "unit": METRIC_UNIT.get(metric, ""),
         "n_control": len(a), "n_arm": len(b),
         "mean_control": mean(a), "mean_arm": mean(b),
         "diff": None, "ci_lo": None, "ci_hi": None, "ci_method": None,
         "pct_change": None, "hedges_g": None, "p_perm": None,
         "mde_abs": None, "mde_pct": None,
         "detectable": None, "verdict": "insufficient data", "sentence": ""}
    if len(a) < 2 or len(b) < 2:
        c["sentence"] = ("%s: insufficient data (n_control=%d, n_arm=%d); "
                         "no contrast computed." % (metric, len(a), len(b)))
        return c

    mc, ma = mean(a), mean(b)
    c["diff"] = ma - mc
    ci = diff_ci(a, b, seed=seed)
    c["ci_lo"], c["ci_hi"], c["ci_method"] = ci["lo"], ci["hi"], ci["method"]
    c["pct_change"] = (100.0 * (ma - mc) / mc) if mc not in (None, 0) else None
    c["hedges_g"] = hedges_g(a, b)
    c["p_perm"] = permutation_p(a, b, seed=seed)
    m = mde(a, b)
    c["mde_abs"] = m
    c["mde_pct"] = (100.0 * m / abs(mc)) if (m is not None and mc not in (None, 0)) else None

    straddles = (c["ci_lo"] is None or c["ci_hi"] is None or
                 (c["ci_lo"] <= 0.0 <= c["ci_hi"]))
    c["detectable"] = not straddles
    unit = c["unit"]
    if straddles:
        # The classic error this guards against: reading a signed point estimate off a
        # CI that comfortably contains zero and calling it a saving.
        c["verdict"] = "no detectable difference"
        if m is not None and abs(c["diff"]) < m:
            c["sentence"] = ("%s: no detectable difference (|effect| < MDE = %s %s"
                             "%s)." % (metric, fmt(m), unit,
                                       "" if c["mde_pct"] is None
                                       else " = %.1f%% of control" % c["mde_pct"]))
        else:
            c["sentence"] = ("%s: no detectable difference (95%% CI [%s, %s] %s includes "
                             "zero; MDE = %s %s%s). The point estimate is not evidence."
                             % (metric, fmt(c["ci_lo"]), fmt(c["ci_hi"]), unit,
                                fmt(m), unit,
                                "" if c["mde_pct"] is None
                                else " = %.1f%% of control" % c["mde_pct"]))
    else:
        lower_better = METRIC_LOWER_BETTER.get(metric)
        direction = "lower" if c["diff"] < 0 else "higher"
        if lower_better is None:
            c["verdict"] = "%s (diagnostic)" % direction
        elif (c["diff"] < 0) == bool(lower_better):
            c["verdict"] = "%s (better)" % direction
        else:
            c["verdict"] = "%s (worse)" % direction
        c["sentence"] = ("%s: %s than control by %s %s (%s), 95%% CI [%s, %s] excludes "
                         "zero; Hedges g = %s, permutation p = %s; MDE = %s %s."
                         % (metric, direction, fmt(abs(c["diff"])), unit,
                            signed_pct(c["pct_change"]),
                            fmt(c["ci_lo"]), fmt(c["ci_hi"]),
                            fmt(c["hedges_g"], 3), fmt(c["p_perm"], 4),
                            fmt(m), unit))
    return c


def available_metrics(rows):
    return [m for m, _u, _lb, _d in METRICS
            if any(num(r.get(m)) is not None for r in rows)]


# =====================================================================================
# QUALITY GATES
# =====================================================================================

def gate(name, status, detail):
    return {"name": name, "status": status, "detail": detail}


def quality_gates(exp, arms, metrics):
    """PASS/FAIL/SKIP gates for one experiment. Each carries its numbers."""
    gates = []
    all_rows = [r for rs in arms.values() for r in rs]

    # --- G1: every run completed --------------------------------------------------
    bad_ok = [r for r in all_rows if r.get("ok") is not True]
    bad_exit = [r for r in all_rows if r.get("exit_code") not in (0,)]
    if bad_ok or bad_exit:
        gates.append(gate("run completion",
                          "FAIL",
                          "%d/%d runs with ok != true, %d/%d with exit_code != 0: %s"
                          % (len(bad_ok), len(all_rows), len(bad_exit), len(all_rows),
                             ", ".join(sorted({os.path.basename(r["file"])
                                               for r in bad_ok + bad_exit})[:8]) or "-")))
    else:
        gates.append(gate("run completion", "PASS",
                          "%d/%d runs have ok=true and exit_code=0" % (len(all_rows),
                                                                       len(all_rows))))

    # --- G2: starting temperature not confounded with arm -------------------------
    arm_temp = {a: mean(values(rs, "start_temp_c")) for a, rs in arms.items()}
    have = {a: v for a, v in arm_temp.items() if v is not None}
    if len(have) < 2:
        gates.append(gate("start temperature spread", "SKIP",
                          "start_temp_c present for %d/%d arms" % (len(have), len(arms))))
    else:
        spread = max(have.values()) - min(have.values())
        hot = max(have, key=lambda a: have[a])
        cold = min(have, key=lambda a: have[a])
        st = "PASS" if spread < MAX_START_TEMP_SPREAD_C else "FAIL"
        gates.append(gate("start temperature spread", st,
                          "max-min of per-arm mean start_temp_c = %.2f C "
                          "(limit %.1f); hottest %s %.1f C, coldest %s %.1f C"
                          % (spread, MAX_START_TEMP_SPREAD_C, hot, have[hot],
                             cold, have[cold])))

    # --- G3: AC power state identical --------------------------------------------
    ac = {}
    for a, rs in arms.items():
        for r in rs:
            ac.setdefault(repr(r.get("on_ac")), []).append(a)
    if len(ac) == 1:
        gates.append(gate("on_ac consistent", "PASS",
                          "all %d runs on_ac=%s" % (len(all_rows), list(ac)[0])))
    else:
        gates.append(gate("on_ac consistent", "FAIL",
                          "mixed AC state across runs: %s"
                          % "; ".join("%s in arms {%s}" % (k, ",".join(sorted(set(v))))
                                      for k, v in sorted(ac.items()))))

    # --- G4: no thermal throttling ------------------------------------------------
    cmax = [(r, r.get("pkg_c_max")) for r in all_rows if r.get("pkg_c_max") is not None]
    if not cmax:
        gates.append(gate("thermal headroom", "SKIP", "no pkg_c_max recorded"))
    else:
        worst_row, worst = max(cmax, key=lambda t: t[1])
        near = [r for r, v in cmax if v >= TJMAX_C - THROTTLE_MARGIN_C]
        st = "PASS" if not near else "FAIL"
        gates.append(gate("thermal headroom", st,
                          "max pkg_c_max = %.1f C in arm %s (limit %.1f C = Tjmax-%.0f); "
                          "%d/%d runs at or above the limit"
                          % (worst, worst_row["arm"], TJMAX_C - THROTTLE_MARGIN_C,
                             THROTTLE_MARGIN_C, len(near), len(cmax))))

    # --- G5: balanced design ------------------------------------------------------
    counts = {a: len(rs) for a, rs in sorted(arms.items())}
    st = "PASS" if len(set(counts.values())) <= 1 else "FAIL"
    gates.append(gate("balanced reps per arm", st,
                      ", ".join("%s=%d" % (a, n) for a, n in counts.items())))

    # --- G6: run-order drift ------------------------------------------------------
    drift = []
    for a, rs in sorted(arms.items()):
        for m in metrics:
            pairs = [(r.get("rep"), r.get(m)) for r in rs]
            xs = [p[0] for p in pairs]
            ys = [p[1] for p in pairs]
            rho = spearman(xs, ys)
            if rho is not None and abs(rho) > DRIFT_RHO:
                drift.append({"arm": a, "metric": m, "rho": rho, "n": len(rs)})
    if drift:
        # At n<8 per arm, |rho| > 0.6 happens by chance often enough that this gate is a
        # prompt to inspect the trace, not proof of a thermal/frequency ramp. Say so.
        min_n = min((len(rs) for rs in arms.values()), default=0)
        caveat = ("" if min_n >= 8 else
                  "  [n=%d per arm: rho is noisy at this size, treat as a prompt to "
                  "inspect the run order, not as proof of drift]" % min_n)
        gates.append(gate("run-order drift", "FAIL",
                          "%d arm/metric pairs with |Spearman rho vs rep| > %.1f: %s%s"
                          % (len(drift), DRIFT_RHO,
                             "; ".join("%s/%s rho=%+.2f" % (d["arm"], d["metric"], d["rho"])
                                       for d in drift[:6]), caveat)))
    else:
        gates.append(gate("run-order drift", "PASS",
                          "no arm/metric pair exceeds |Spearman rho vs rep| = %.1f"
                          % DRIFT_RHO))
    return gates, drift


# =====================================================================================
# PLACEMENT SANITY  (did the partition actually happen?)
# =====================================================================================

def placement_sanity(arms):
    """Per-arm scheduler placement summary + the hard gate on cross-domain traffic."""
    out = {"arms": [], "gates": []}
    any_bls = False
    for a, rs in sorted(arms.items()):
        with_bls = [r for r in rs if r.get("bls_present")]
        if not with_bls:
            out["arms"].append({"arm": a, "n": len(rs), "n_with_bls": 0, "strict": None,
                                "cross_frac_mean": None, "run_big_frac_mean": None,
                                "run_little_frac_mean": None, "dsq_big_frac_mean": None,
                                "enqueue_mean": None})
            continue
        any_bls = True
        strict = with_bls[0].get("strict")
        rec = {
            "arm": a, "n": len(rs), "n_with_bls": len(with_bls), "strict": strict,
            "enqueue_mean": mean(values(with_bls, "bls_enqueue")),
            "cross_frac_mean": mean(values(with_bls, "bls_cross_frac")),
            "cross_frac_max": max(values(with_bls, "bls_cross_frac"), default=None),
            "run_big_frac_mean": mean(values(with_bls, "bls_run_big_frac")),
            "run_little_frac_mean": mean(values(with_bls, "bls_run_little_frac")),
            "dsq_big_frac_mean": mean(values(with_bls, "bls_dsq_big_frac")),
        }
        out["arms"].append(rec)

        if rec["cross_frac_mean"] is not None:
            over = rec["cross_frac_mean"] > MAX_CROSS_DOMAIN_FRAC
            if strict is True:
                out["gates"].append(gate(
                    "placement: %s (strict)" % a,
                    "FAIL" if over else "PASS",
                    "cross_domain/enqueue = %.1f%% (max over runs %.1f%%), budget %.0f%%; "
                    "run time big/LITTLE = %s / %s"
                    % (100.0 * rec["cross_frac_mean"],
                       100.0 * (rec["cross_frac_max"] or 0.0),
                       100.0 * MAX_CROSS_DOMAIN_FRAC,
                       pct(rec["run_big_frac_mean"]), pct(rec["run_little_frac_mean"]))
                    + ("  -- the tasks did NOT stay partitioned, so this arm cannot "
                       "support any claim about partitioning." if over else "")))
            else:
                out["gates"].append(gate(
                    "placement: %s (non-strict)" % a, "INFO",
                    "cross_domain/enqueue = %.1f%%; run time big/LITTLE = %s / %s"
                    % (100.0 * rec["cross_frac_mean"],
                       pct(rec["run_big_frac_mean"]), pct(rec["run_little_frac_mean"]))))
    if not any_bls:
        out["gates"].append(gate("placement", "SKIP",
                                 "no arm reported bls scheduler counters"))
    out["ok"] = not any(g["status"] == "FAIL" for g in out["gates"])
    return out


# =====================================================================================
# FREQUENCY DIVERGENCE  (is the "partition" physically real?)
# =====================================================================================

def frequency_divergence(arms):
    """Per-CPU busy MHz by domain, and little/big ratio.

    This is the load-bearing check for the whole repo: if EPP did not actually pull the
    LITTLE cores' frequency down, there is no partition, and every downstream energy
    comparison is a comparison of a machine with itself.
    """
    out = {"arms": [], "note": None}
    for a, rs in sorted(arms.items()):
        percpu = []
        for i in range(N_CPUS):
            percpu.append({
                "cpu": i,
                "bzy_mhz": mean(values(rs, "cpu%d_bzy_mhz" % i)),
                "avg_mhz": mean(values(rs, "cpu%d_avg_mhz" % i)),
                "busy": mean(values(rs, "cpu%d_busy" % i)),
                "epp": median(values(rs, "cpu%d_epp" % i)),
            })
        big_v = values(rs, "bzy_mhz_big_mean")
        lit_v = values(rs, "bzy_mhz_little_mean")
        ratios = values(rs, "bzy_ratio_little_over_big")
        rec = {
            "arm": a, "n": len(rs),
            "partitioned_epp": any(r.get("partitioned_epp") for r in rs),
            "smt_pairs_split": max([r.get("smt_pairs_split") or 0 for r in rs], default=0),
            "per_cpu": percpu,
            "big_bzy_mhz": mean(big_v), "little_bzy_mhz": mean(lit_v),
            "ratio_little_over_big": mean(ratios),
            "ratio_ci_lo": None, "ratio_ci_hi": None, "ratio_ci_method": None,
            "verdict": None,
        }
        if len(ratios) >= 2:
            ci = mean_ci(ratios)
            rec["ratio_ci_lo"], rec["ratio_ci_hi"] = ci["lo"], ci["hi"]
            rec["ratio_ci_method"] = ci["method"]
        rr = rec["ratio_little_over_big"]
        if not rec["partitioned_epp"]:
            rec["verdict"] = ("flat EPP: no big/LITTLE split was requested in this arm "
                              "(all 8 CPUs report the same EPP)")
        elif rr is None:
            rec["verdict"] = "no per-CPU frequency data"
        elif rr >= FREQ_RATIO_REAL:
            rec["verdict"] = ("NOT PHYSICALLY REAL: LITTLE cores ran at %.0f%% of big-core "
                              "frequency (>= %.0f%%). The EPP write did not separate the "
                              "domains, so nothing downstream of this can be attributed "
                              "to partitioning." % (100.0 * rr, 100.0 * FREQ_RATIO_REAL))
        else:
            rec["verdict"] = ("frequency split is real: LITTLE cores ran at %.0f%% of "
                              "big-core frequency" % (100.0 * rr))
        if rec["smt_pairs_split"]:
            rec["verdict"] += ("  [WARNING: %d SMT sibling pair(s) split across domains; "
                               "siblings share one clock domain, so one of the two EPP "
                               "settings is silently ignored]" % rec["smt_pairs_split"])
        out["arms"].append(rec)

    real = [r for r in out["arms"] if r["partitioned_epp"] and
            r["ratio_little_over_big"] is not None]
    if not real:
        out["note"] = "no arm in this experiment requested a big/LITTLE EPP split."
    elif all(r["ratio_little_over_big"] >= FREQ_RATIO_REAL for r in real):
        out["note"] = ("The partition is NOT physically real in any arm: LITTLE-domain "
                       "frequency is within %.0f%% of big-domain frequency. Everything "
                       "downstream is moot -- the energy comparison is a comparison of "
                       "the machine against itself."
                       % (100.0 * (1.0 - FREQ_RATIO_REAL)))
    else:
        best = min(real, key=lambda r: r["ratio_little_over_big"])
        out["note"] = ("The frequency split is real (lowest little/big ratio %.2f in arm "
                       "%s), so the energy comparison is testing a genuine partition."
                       % (best["ratio_little_over_big"], best["arm"]))
    return out


# =====================================================================================
# COVERAGE
# =====================================================================================

def coverage(rows):
    n = len(rows)
    cov = {"n_runs": n, "fields": []}
    checks = [("energy.pkg_j", "pkg_j"), ("energy.wall_s", "wall_s"),
              ("energy.rest_j", "rest_j"), ("energy.cpu_bzy_mhz", "cpu0_bzy_mhz"),
              ("energy.epp", "cpu0_epp"), ("env.start_temp_c", "start_temp_c"),
              ("energy.pkg_c_max", "pkg_c_max")]
    for label, col in checks:
        have = sum(1 for r in rows if num(r.get(col)) is not None)
        cov["fields"].append({"field": label, "present": have, "missing": n - have,
                              "pct": (100.0 * have / n) if n else 0.0})
    for label, col in (("pinger", "pinger_present"), ("spin", "spin_present"),
                       ("bls", "bls_present")):
        have = sum(1 for r in rows if r.get(col))
        cov["fields"].append({"field": label, "present": have, "missing": n - have,
                              "pct": (100.0 * have / n) if n else 0.0})
    return cov


# =====================================================================================
# ANALYSIS DRIVER
# =====================================================================================

def analyze(rows, seed=SEED):
    exps = group_runs(rows)
    result = {"experiments": [], "coverage": coverage(rows), "n_runs": len(rows)}
    for exp in sorted(exps):
        arms = exps[exp]
        all_rows = [r for rs in arms.values() for r in rs]
        metrics = available_metrics(all_rows)
        control = pick_control(arms)
        ctrl_rows = arms.get(control, [])
        ctrl_reason = "factors sched=eevdf,epp=flat"
        if ctrl_rows and not (ctrl_rows[0].get("sched") == "eevdf"
                              and ctrl_rows[0].get("epp_mode") == "flat"):
            ctrl_reason = ("named 'control'" if (control or "").lower() == "control"
                           else "first arm alphabetically (no eevdf/flat arm present)")
        gates, drift = quality_gates(exp, arms, metrics)
        erec = {
            "experiment": exp,
            "n_runs": len(all_rows),
            "arms": sorted(arms),
            "n_per_arm": {a: len(rs) for a, rs in sorted(arms.items())},
            "control_arm": control,
            "control_selection": ctrl_reason,
            "metrics": metrics,
            "summary": [],
            "contrasts": [],
            "mde": [],
            "gates": gates,
            "drift": drift,
            "placement": placement_sanity(arms),
            "coverage": coverage(all_rows),
        }
        # Computed for every experiment because it gates the verdict; only rendered as a
        # full section for the experiment that exists to test it.
        erec["frequency"] = frequency_divergence(arms)
        erec["render_frequency"] = (exp == RAIL_EXPERIMENT)
        for rec in erec["frequency"]["arms"]:
            rr = rec["ratio_little_over_big"]
            if not rec["partitioned_epp"] or rr is None:
                continue
            erec["gates"].append(gate(
                "partition is physically real: %s" % rec["arm"],
                "FAIL" if rr >= FREQ_RATIO_REAL else "PASS",
                "little/big bzy MHz = %.3f (%s MHz / %s MHz over %d runs); a real split "
                "needs < %.2f" % (rr, fmt(rec["little_bzy_mhz"]), fmt(rec["big_bzy_mhz"]),
                                  rec["n"], FREQ_RATIO_REAL)
                + ("  -- EPP did not separate the frequency domains, so no downstream "
                   "energy difference can be attributed to partitioning."
                   if rr >= FREQ_RATIO_REAL else "")))

        for a in sorted(arms):
            for m in metrics:
                s = summarize_arm(arms[a], m, seed=seed)
                s["arm"] = a
                erec["summary"].append(s)

        for a in sorted(arms):
            if a == control:
                continue
            for m in metrics:
                c = contrast(ctrl_rows, arms[a], m, seed=seed)
                c["arm"] = a
                c["control_arm"] = control
                erec["contrasts"].append(c)
                erec["mde"].append({
                    "arm": a, "metric": m, "unit": METRIC_UNIT.get(m, ""),
                    "n_control": c["n_control"], "n_arm": c["n_arm"],
                    "pooled_sd": pooled_sd(values(ctrl_rows, m), values(arms[a], m)),
                    "control_mean": c["mean_control"],
                    "mde_abs": c["mde_abs"], "mde_pct": c["mde_pct"],
                    "alpha": ALPHA, "power": POWER,
                })
        erec["verdict"] = experiment_verdict(erec)
        result["experiments"].append(erec)
    result["headline"] = overall_headline(result)
    return result


def experiment_verdict(erec):
    """Plain-language verdict for one experiment, refusing to over-claim."""
    lines = []
    exp = erec["experiment"]
    ctrl = erec["control_arm"]
    failed = [g["name"] for g in erec["gates"] if g["status"] == "FAIL"]
    failed += [g["name"] for g in erec["placement"]["gates"] if g["status"] == "FAIL"]

    head = [c for c in erec["contrasts"] if c["metric"] == HEADLINE_METRIC]
    if not head:
        lines.append("No %s data in %s; no energy conclusion can be drawn."
                     % (HEADLINE_METRIC, exp))
    for c in head:
        if c["diff"] is None:
            lines.append("%s vs %s: insufficient data for an energy contrast."
                         % (c["arm"], ctrl))
        elif not c["detectable"]:
            lines.append(
                "%s vs %s: no detectable difference in energy-to-solution "
                "(|effect| < MDE = %s J = %s of the control mean, at %d%% power / "
                "alpha %.2f with n=%d vs %d). This design could not have seen a saving "
                "smaller than that; it is not evidence that the saving is exactly zero."
                % (c["arm"], ctrl, fmt(c["mde_abs"]),
                   "%.1f%%" % c["mde_pct"] if c["mde_pct"] is not None else "n/a",
                   int(POWER * 100), ALPHA, c["n_control"], c["n_arm"]))
        else:
            better = c["diff"] < 0
            lines.append(
                "%s vs %s: energy-to-solution is %s by %s J (%.1f%%), 95%% CI [%s, %s] "
                "excludes zero (Hedges g = %s, permutation p = %s)."
                % (c["arm"], ctrl, "LOWER" if better else "HIGHER",
                   fmt(abs(c["diff"])), c["pct_change"] or 0.0,
                   fmt(c["ci_lo"]), fmt(c["ci_hi"]),
                   fmt(c["hedges_g"], 3), fmt(c["p_perm"], 4)))
            if failed:
                lines.append(
                    "   CAUTION: this apparent %s is not admissible while these gates "
                    "fail: %s." % ("saving" if better else "regression",
                                   ", ".join(sorted(set(failed)))))

    freq = erec.get("frequency")
    if freq and freq.get("note"):
        lines.append(freq["note"])
    if failed:
        lines.append("Failing gates: %s." % ", ".join(sorted(set(failed))))
    return lines


def overall_headline(result):
    """Repo-level answer: did per-core-EPP partitioning save energy anywhere?"""
    wins, nulls, blocked = [], [], []
    for e in result["experiments"]:
        gate_fail = any(g["status"] == "FAIL" for g in e["gates"]) or \
                    any(g["status"] == "FAIL" for g in e["placement"]["gates"])
        for c in e["contrasts"]:
            if c["metric"] != HEADLINE_METRIC or c["diff"] is None:
                continue
            tag = "%s/%s" % (e["experiment"], c["arm"])
            if c["detectable"] and c["diff"] < 0:
                (blocked if gate_fail else wins).append((tag, c))
            elif not c["detectable"]:
                nulls.append((tag, c))
    lines = []
    if wins:
        lines.append("A detectable energy saving was found in: %s."
                     % ", ".join("%s (%.1f%%)" % (t, c["pct_change"] or 0.0)
                                 for t, c in wins))
        lines.append("Before believing it, confirm the frequency split was real and that "
                     "placement stayed inside its domain -- a saving from an arm that did "
                     "not actually partition is a saving from something else.")
    if blocked:
        lines.append("Apparent savings in %s are NOT admissible: quality gates failed for "
                     "those experiments."
                     % ", ".join(t for t, _c in blocked))
    if nulls and not wins:
        worst = max((c["mde_pct"] for _t, c in nulls if c["mde_pct"] is not None),
                    default=None)
        best = min((c["mde_pct"] for _t, c in nulls if c["mde_pct"] is not None),
                   default=None)
        lines.append("No detectable energy saving in any arm (%d contrast%s on %s, all "
                     "95%% CIs straddle zero)."
                     % (len(nulls), "" if len(nulls) == 1 else "s", HEADLINE_METRIC))
        if best is not None:
            lines.append("The honest headline is bounded, not zero: with this many reps "
                         "no effect smaller than %.1f%%-%.1f%% of control energy is "
                         "detectable at %d%% power. A real big.LITTLE-scale saving "
                         "(tens of percent) would have been visible; it was not."
                         % (best, worst, int(POWER * 100)))
    if not result["experiments"]:
        lines.append("No experiments to report.")
    elif not lines:
        lines.append("No usable %s contrast could be computed from these runs (every "
                     "experiment lacked either a control arm or the metric itself); see "
                     "the Coverage tables." % HEADLINE_METRIC)
    return lines


# =====================================================================================
# FORMATTING
# =====================================================================================

def fmt(x, prec=3):
    if x is None:
        return "n/a"
    if isinstance(x, bool):
        return "true" if x else "false"
    if isinstance(x, str):
        return x
    try:
        v = float(x)
    except (TypeError, ValueError):
        return str(x)
    if math.isnan(v) or math.isinf(v):
        return "n/a"
    if v != 0 and (abs(v) < 1e-3 or abs(v) >= 1e7):
        return "%.*e" % (prec, v)
    av = abs(v)
    if av >= 1000:
        return "%.1f" % v
    if av >= 10:
        return "%.2f" % v
    return "%.*f" % (prec, v)


def pct(x, prec=1):
    return "n/a" if x is None else "%.*f%%" % (prec, 100.0 * x)


def signed_pct(x, prec=1):
    return "n/a" if x is None else "%+.*f%%" % (prec, x)


def busy_fmt(v):
    """cpu_busy is reported as a fraction by some collectors and as a percent by others;
    accept both rather than printing a 5500 % duty cycle."""
    if v is None:
        return "n/a"
    return "%.1f%%" % (100.0 * v if v <= 1.5 else v)


def md_table(headers, rows, aligns=None):
    """Markdown table with padded cells, so the raw file is readable and diffs cleanly."""
    cols = len(headers)
    aligns = aligns or (["l"] + ["r"] * (cols - 1))
    # Escape cell pipes before measuring, or a value like |rho| silently splits the row.
    def esc(v):
        return str(v).replace("|", "\\|")

    cells = [[esc(h) for h in headers]] + [[esc(c) for c in r] for r in rows]
    widths = [max(len(row[i]) for row in cells) for i in range(cols)]
    widths = [max(w, 3) for w in widths]

    def line(vals):
        out = []
        for i, v in enumerate(vals):
            out.append(v.ljust(widths[i]) if aligns[i] == "l" else v.rjust(widths[i]))
        return "| " + " | ".join(out) + " |"

    sep = []
    for i in range(cols):
        sep.append(":" + "-" * (widths[i] - 1) if aligns[i] == "l"
                   else "-" * (widths[i] - 1) + ":")
    return [line(cells[0]), "| " + " | ".join(sep) + " |"] + [line(r) for r in cells[1:]]


def status_mark(status):
    return {"PASS": "PASS", "FAIL": "FAIL", "SKIP": "SKIP", "INFO": "INFO"}.get(status,
                                                                                status)


# =====================================================================================
# MARKDOWN REPORT
# =====================================================================================

def render_markdown(result, args, raw_dir, csv_path, now):
    L = []
    a = L.append
    a(GENERATED_MARKER)
    a("     Produced by scripts/analyze.py from %s" % raw_dir)
    a("     Generated: %s" % now)
    a("     Every number below carries the run count it was computed from.")
    a("     Edits will be lost on the next `make analyze`; change the script instead. -->")
    a("")
    a("# fake-big-little: measured results")
    a("")
    a("- Generated: `%s`" % now)
    a("- Raw runs read: **%d** from `%s`" % (result["n_runs"], raw_dir))
    a("- Tidy per-run data: `%s`" % csv_path)
    a("- Resampling: %d bootstrap resamples, %d permutations, seed `random.Random(%d)` "
      "(the report is reproducible byte-for-byte)." % (N_BOOT, N_PERM, SEED))
    a("- CI method is stated per row: `BCa` (bias-corrected and accelerated) where the "
      "jackknife acceleration is well defined, `percentile` where it degenerates. It is "
      "never mislabelled.")
    a("")

    # ---- headline ------------------------------------------------------------------
    a("## Headline")
    a("")
    for line in result["headline"]:
        a("- %s" % line)
    a("")

    for e in result["experiments"]:
        a("---")
        a("")
        a("# Experiment `%s`" % e["experiment"])
        a("")
        a("- Runs: **%d** across %d arms (%s)"
          % (e["n_runs"], len(e["arms"]),
             ", ".join("%s n=%d" % (k, v) for k, v in e["n_per_arm"].items())))
        a("- Control arm: **`%s`** (%s)" % (e["control_arm"], e["control_selection"]))
        a("")

        a("## Verdict")
        a("")
        for line in e["verdict"]:
            a("- %s" % line)
        a("")

        # ---- data quality ----------------------------------------------------------
        a("## Data quality")
        a("")
        rows = [[status_mark(g["status"]), g["name"], g["detail"]] for g in e["gates"]]
        L.extend(md_table(["status", "gate", "numbers"], rows, ["l", "l", "l"]))
        a("")
        nfail = sum(1 for g in e["gates"] if g["status"] == "FAIL")
        if nfail:
            a("**%d gate(s) FAILED.** A failed gate means the arms are not comparable; "
              "effect sizes below are reported for completeness but must not be quoted "
              "as results until the gate is fixed." % nfail)
        else:
            a("All gates pass: the arms are comparable on completion, thermal state, "
              "power source, balance and run order.")
        a("")

        # ---- placement -------------------------------------------------------------
        a("## Placement sanity")
        a("")
        a("A partitioning experiment where the tasks did not stay partitioned proves "
          "nothing, so this comes before the effect sizes.")
        a("")
        prows = []
        for p in e["placement"]["arms"]:
            prows.append([
                p["arm"],
                "%d/%d" % (p["n_with_bls"], p["n"]),
                fmt(p["strict"]),
                fmt(p["enqueue_mean"]),
                pct(p["cross_frac_mean"]),
                pct(p["run_big_frac_mean"]),
                pct(p["run_little_frac_mean"]),
                pct(p["dsq_big_frac_mean"]),
            ])
        L.extend(md_table(
            ["arm", "runs w/ bls", "strict", "enqueues (mean)", "cross-domain / enqueue",
             "run time in big", "run time in LITTLE", "dispatch to big"],
            prows))
        a("")
        for g in e["placement"]["gates"]:
            a("- **%s** -- %s: %s" % (status_mark(g["status"]), g["name"], g["detail"]))
        a("")

        # ---- frequency divergence --------------------------------------------------
        if e.get("render_frequency"):
            a("## Frequency divergence")
            a("")
            a("Per-CPU busy MHz averaged over runs. If little/big is near 1.0 the "
              "partition is not physically real and everything downstream is moot.")
            a("")
            for rec in e["frequency"]["arms"]:
                a("### `%s` (n=%d)" % (rec["arm"], rec["n"]))
                a("")
                frows = []
                for c in rec["per_cpu"]:
                    dom = "-"
                    if c["epp"] is not None:
                        dom = "big" if c["epp"] < EPP_BIG_MAX else "LITTLE"
                    if not rec["partitioned_epp"]:
                        dom = "flat"
                    frows.append([
                        "cpu%d" % c["cpu"], dom,
                        "%d" % int(c["epp"]) if c["epp"] is not None else "n/a",
                        fmt(c["bzy_mhz"]), fmt(c["avg_mhz"]), busy_fmt(c["busy"]),
                        "cpu%d" % ((c["cpu"] + SMT_STRIDE) % N_CPUS),
                    ])
                L.extend(md_table(
                    ["cpu", "domain", "epp", "bzy MHz", "avg MHz", "busy", "SMT sibling"],
                    frows))
                a("")
                a("- big domain bzy: **%s MHz**, LITTLE domain bzy: **%s MHz**"
                  % (fmt(rec["big_bzy_mhz"]), fmt(rec["little_bzy_mhz"])))
                ci = ""
                if rec["ratio_ci_lo"] is not None:
                    ci = " (95%% CI [%s, %s], %s)" % (fmt(rec["ratio_ci_lo"], 3),
                                                      fmt(rec["ratio_ci_hi"], 3),
                                                      rec["ratio_ci_method"])
                a("- **little_bzy_mhz / big_bzy_mhz = %s**%s"
                  % (fmt(rec["ratio_little_over_big"], 3), ci))
                a("- %s" % rec["verdict"])
                a("")
            a("**%s**" % e["frequency"]["note"])
            a("")

        # ---- per-arm summary -------------------------------------------------------
        a("## Per-arm summary")
        a("")
        a("Mean with a 95%% bootstrap CI (%d resamples). `n` is the number of runs that "
          "actually carried the metric." % N_BOOT)
        a("")
        for m in e["metrics"]:
            a("### `%s` (%s) -- %s" % (m, METRIC_UNIT.get(m, ""), METRIC_DESC.get(m, "")))
            a("")
            srows = []
            for s in e["summary"]:
                if s["metric"] != m:
                    continue
                srows.append([
                    s["arm"] + ("  [control]" if s["arm"] == e["control_arm"] else ""),
                    "%d" % s["n"],
                    "%d" % s["n_missing"],
                    fmt(s["mean"]), fmt(s["median"]), fmt(s["sd"]),
                    "[%s, %s]" % (fmt(s["ci_lo"]), fmt(s["ci_hi"])),
                    s["ci_method"] or "n/a",
                ])
            L.extend(md_table(["arm", "n", "missing", "mean", "median", "sd",
                               "95% CI of mean", "CI method"], srows))
            a("")

        # ---- contrasts -------------------------------------------------------------
        a("## Contrasts vs control (`%s`)" % e["control_arm"])
        a("")
        a("Difference in means (arm - control). A contrast whose CI straddles zero is "
          "reported as *no detectable difference*, never as a signed saving.")
        a("")
        for arm in e["arms"]:
            if arm == e["control_arm"]:
                continue
            cs = [c for c in e["contrasts"] if c["arm"] == arm]
            if not cs:
                continue
            a("### `%s` vs `%s`" % (arm, e["control_arm"]))
            a("")
            crows = []
            for c in cs:
                crows.append([
                    c["metric"],
                    "%d/%d" % (c["n_control"], c["n_arm"]),
                    fmt(c["mean_control"]), fmt(c["mean_arm"]),
                    fmt(c["diff"]),
                    "[%s, %s]" % (fmt(c["ci_lo"]), fmt(c["ci_hi"])),
                    signed_pct(c["pct_change"]),
                    fmt(c["hedges_g"], 3),
                    fmt(c["p_perm"], 4),
                    fmt(c["mde_abs"]),
                    "%.1f%%" % c["mde_pct"] if c["mde_pct"] is not None else "n/a",
                    c["verdict"],
                ])
            L.extend(md_table(
                ["metric", "n ctl/arm", "control mean", "arm mean", "diff",
                 "95% CI of diff", "% change", "Hedges g", "p (perm)",
                 "MDE (abs)", "MDE (%)", "result"], crows))
            a("")
            for c in cs:
                a("- %s" % c["sentence"])
            a("")

        # ---- MDE section -----------------------------------------------------------
        if args.mde:
            a("## Minimum detectable effect")
            a("")
            a("At %d%% power, alpha %.2f, two-sided, from the observed pooled sd and n. "
              "This matters more than any p-value here: it is the smallest true effect "
              "this design could have caught. Effects below it are invisible to the "
              "experiment, not absent from the machine."
              % (int(POWER * 100), ALPHA))
            a("")
            mrows = []
            for r in e["mde"]:
                mrows.append([
                    r["arm"], r["metric"], r["unit"],
                    "%d/%d" % (r["n_control"], r["n_arm"]),
                    fmt(r["pooled_sd"]), fmt(r["control_mean"]),
                    fmt(r["mde_abs"]),
                    "%.1f%%" % r["mde_pct"] if r["mde_pct"] is not None else "n/a",
                ])
            L.extend(md_table(
                ["arm", "metric", "unit", "n ctl/arm", "pooled sd", "control mean",
                 "MDE (abs)", "MDE (% of control)"], mrows))
            a("")
            head = [r for r in e["mde"]
                    if r["metric"] == HEADLINE_METRIC and r["mde_pct"] is not None]
            if head:
                worst = max(head, key=lambda r: r["mde_pct"])
                a("Reading: on `%s`, the weakest arm comparison (`%s`) can only detect "
                  "effects of **%.1f%% or larger**. To halve that, quadruple the reps."
                  % (HEADLINE_METRIC, worst["arm"], worst["mde_pct"]))
                a("")

        # ---- coverage --------------------------------------------------------------
        a("## Coverage")
        a("")
        crows = [[f["field"], "%d" % f["present"], "%d" % f["missing"], "%.0f%%" % f["pct"]]
                 for f in e["coverage"]["fields"]]
        L.extend(md_table(["field", "present", "missing", "coverage"], crows))
        a("")

    a("---")
    a("")
    a("Generated by `scripts/analyze.py` on %s. %d runs. Do not edit by hand."
      % (now, result["n_runs"]))
    a("")
    return "\n".join(L)


def write_markdown(text, path):
    """Write the report, refusing to clobber a hand-written file at the same path."""
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as fh:
                head = fh.read(4096)
        except OSError:
            head = ""
        if GENERATED_MARKER not in head:
            raise SystemExit(
                "refusing to overwrite %s: it does not start with the generated-file "
                "marker, so it may be hand-written. Move it aside or pass --out-md."
                % path)
    d = os.path.dirname(os.path.abspath(path))
    if d:
        os.makedirs(d, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


# =====================================================================================
# CONSOLE SUMMARY
# =====================================================================================

def print_console(result, args, csv_path, md_path):
    print("=" * 92)
    print("fake-big-little analysis -- %d runs" % result["n_runs"])
    print("=" * 92)
    for e in result["experiments"]:
        print("\n%s  (%d runs, control=%s)"
              % (e["experiment"], e["n_runs"], e["control_arm"]))
        for g in e["gates"] + e["placement"]["gates"]:
            if g["status"] in ("FAIL",):
                print("  [FAIL] %s: %s" % (g["name"], g["detail"]))
        for line in e["verdict"]:
            print("  %s" % line)
        if args.mde:
            for r in e["mde"]:
                if r["metric"] == HEADLINE_METRIC and r["mde_pct"] is not None:
                    print("  MDE %s vs control on %s: %s %s (%.1f%% of control), n=%d/%d"
                          % (r["arm"], r["metric"], fmt(r["mde_abs"]), r["unit"],
                             r["mde_pct"], r["n_control"], r["n_arm"]))
    print("\nHEADLINE")
    for line in result["headline"]:
        print("  %s" % line)
    print("\nwrote %s" % csv_path)
    print("wrote %s" % md_path)


# =====================================================================================
# JSON
# =====================================================================================

def sanitize(obj):
    """Make the structure JSON-safe: no NaN/Inf, no private keys, no sets."""
    if isinstance(obj, dict):
        return {k: sanitize(v) for k, v in obj.items() if not str(k).startswith("_")}
    if isinstance(obj, (list, tuple)):
        return [sanitize(v) for v in obj]
    if isinstance(obj, float):
        return None if (math.isnan(obj) or math.isinf(obj)) else obj
    return obj


# =====================================================================================
# MAIN
# =====================================================================================

def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Statistics and report generator for the fake-big-little experiment.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Stdlib only. Bootstrap/permutation seeds are fixed, so re-running on the "
               "same data reproduces the report exactly.")
    ap.add_argument("--raw", default=os.path.join("data", "raw"), metavar="DIR",
                    help="directory of raw run JSON, searched recursively "
                         "(default: data/raw)")
    ap.add_argument("--out-csv", default=os.path.join("data", "results.csv"),
                    metavar="PATH", help="tidy per-run CSV (default: data/results.csv)")
    ap.add_argument("--out-md", default=os.path.join("docs", "results.md"),
                    metavar="PATH", help="generated Markdown report "
                                         "(default: docs/results.md)")
    ap.add_argument("--mde", action="store_true",
                    help="include the full minimum-detectable-effect section: the "
                         "smallest true effect this many reps could have caught")
    ap.add_argument("--json", action="store_true",
                    help="dump the whole computed structure to stdout as JSON")
    args = ap.parse_args(argv)

    if not os.path.isdir(args.raw):
        print("no runs found (no such directory: %s)" % args.raw)
        return 0

    runs, load_errors = load_runs(args.raw)
    for err in load_errors:
        print("warning: skipping %s -- %s" % (err["file"], err["error"]),
              file=sys.stderr)
    if not runs:
        print("no runs found (searched %s for **/*.json)" % args.raw)
        return 0

    rows = [flatten_run(r) for r in runs]
    now = datetime.now().replace(microsecond=0).isoformat()

    write_csv(rows, args.out_csv)
    result = analyze(rows)
    result["generated"] = now
    result["raw_dir"] = args.raw
    result["load_errors"] = load_errors
    result["config"] = {"n_boot": N_BOOT, "n_perm": N_PERM, "seed": SEED,
                        "alpha": ALPHA, "power": POWER,
                        "epp_big_max": EPP_BIG_MAX,
                        "max_start_temp_spread_c": MAX_START_TEMP_SPREAD_C,
                        "max_cross_domain_frac": MAX_CROSS_DOMAIN_FRAC,
                        "drift_rho": DRIFT_RHO,
                        "freq_ratio_real": FREQ_RATIO_REAL}

    write_markdown(render_markdown(result, args, args.raw, args.out_csv, now),
                   args.out_md)

    if args.json:
        json.dump(sanitize(result), sys.stdout, indent=2, allow_nan=False)
        sys.stdout.write("\n")
    else:
        print_console(result, args, args.out_csv, args.out_md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
