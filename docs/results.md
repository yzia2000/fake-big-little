<!-- GENERATED FILE -- DO NOT EDIT BY HAND.
     Produced by scripts/analyze.py from data/raw
     Generated: 2026-07-22T22:14:08
     Every number below carries the run count it was computed from.
     Edits will be lost on the next `make analyze`; change the script instead. -->

# fake-big-little: measured results

- Generated: `2026-07-22T22:14:08`
- Raw runs read: **203** from `data/raw`
- Tidy per-run data: `data/results.csv`
- Resampling: 10000 bootstrap resamples, 10000 permutations, seed `random.Random(0)` (the report is reproducible byte-for-byte).
- CI method is stated per row: `BCa` (bias-corrected and accelerated) where the jackknife acceleration is well defined, `percentile` where it degenerates. It is never mislabelled.

## Headline

- Apparent savings in e1-rail/both-power, e1b-poison/others-balance-power, e1b-poison/others-power, e2-coupling/flat.idle, e2-coupling/partitioned.idle, e2-coupling/partitioned.little1 are NOT admissible: quality gates failed for those experiments.
- No detectable energy saving in any arm (4 contrasts on energy_to_solution_j, all 95% CIs straddle zero).
- The honest headline is bounded, not zero: with this many reps no effect smaller than 1.0%-2.0% of control energy is detectable at 80% power. A real big.LITTLE-scale saving (tens of percent) would have been visible; it was not.

---

# Experiment `e1-rail`

- Runs: **28** across 4 arms (both-balance n=7, both-performance n=7, both-power n=7, partitioned n=7)
- Control arm: **`both-balance`** (first arm alphabetically (no eevdf/flat arm present))

## Verdict

- both-performance vs both-balance: energy-to-solution is HIGHER by 1.369 J (0.5%), 95% CI [0.778, 2.031] excludes zero (Hedges g = 1.979, permutation p = 0.0025).
-    CAUTION: this apparent regression is not admissible while these gates fail: partition is physically real: partitioned, run-order drift.
- both-power vs both-balance: energy-to-solution is LOWER by 230.28 J (-88.3%), 95% CI [-230.78, -229.36] excludes zero (Hedges g = -313.56, permutation p = 8.9991e-04).
-    CAUTION: this apparent saving is not admissible while these gates fail: partition is physically real: partitioned, run-order drift.
- partitioned vs both-balance: energy-to-solution is HIGHER by 1.189 J (0.5%), 95% CI [0.723, 1.655] excludes zero (Hedges g = 2.309, permutation p = 8.9991e-04).
-    CAUTION: this apparent regression is not admissible while these gates fail: partition is physically real: partitioned, run-order drift.
- The partition is NOT physically real in any arm: LITTLE-domain frequency is within 10% of big-domain frequency. Everything downstream is moot -- the energy comparison is a comparison of the machine against itself.
- Failing gates: partition is physically real: partitioned, run-order drift.

## Data quality

| status | gate                                      | numbers                                                                                                                                                                                                                                                                                                                                                                                           |
| :----- | :---------------------------------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| PASS   | run completion                            | 28/28 runs have ok=true and exit_code=0                                                                                                                                                                                                                                                                                                                                                           |
| PASS   | start temperature spread                  | max-min of per-arm mean start_temp_c = 2.29 C (limit 5.0); hottest both-power 49.4 C, coldest both-balance 47.1 C                                                                                                                                                                                                                                                                                 |
| PASS   | on_ac consistent                          | all 28 runs on_ac=True                                                                                                                                                                                                                                                                                                                                                                            |
| PASS   | thermal headroom                          | max pkg_c_max = 74.0 C in arm both-performance (limit 97.0 C = Tjmax-3); 0/28 runs at or above the limit                                                                                                                                                                                                                                                                                          |
| PASS   | balanced reps per arm                     | both-balance=7, both-performance=7, both-power=7, partitioned=7                                                                                                                                                                                                                                                                                                                                   |
| FAIL   | run-order drift                           | 15 arm/metric pairs with \|Spearman rho vs rep\| > 0.6: both-balance/core_j rho=+0.96; both-balance/rest_frac rho=-0.86; both-balance/bzy_mhz_big_mean rho=+0.61; both-performance/core_j rho=+0.93; both-performance/rest_frac rho=-0.93; both-power/energy_to_solution_j rho=-0.61  [n=7 per arm: rho is noisy at this size, treat as a prompt to inspect the run order, not as proof of drift] |
| FAIL   | partition is physically real: partitioned | little/big bzy MHz = 0.998 (3420.5 MHz / 3426.6 MHz over 7 runs); a real split needs < 0.90  -- EPP did not separate the frequency domains, so no downstream energy difference can be attributed to partitioning.                                                                                                                                                                                 |

**2 gate(s) FAILED.** A failed gate means the arms are not comparable; effect sizes below are reported for completeness but must not be quoted as results until the gate is fixed.

## Placement sanity

A partitioning experiment where the tasks did not stay partitioned proves nothing, so this comes before the effect sizes.

| arm              | runs w/ bls | strict | enqueues (mean) | cross-domain / enqueue | run time in big | run time in LITTLE | dispatch to big |
| :--------------- | ----------: | -----: | --------------: | ---------------------: | --------------: | -----------------: | --------------: |
| both-balance     |         0/7 |    n/a |             n/a |                    n/a |             n/a |                n/a |             n/a |
| both-performance |         0/7 |    n/a |             n/a |                    n/a |             n/a |                n/a |             n/a |
| both-power       |         0/7 |    n/a |             n/a |                    n/a |             n/a |                n/a |             n/a |
| partitioned      |         0/7 |    n/a |             n/a |                    n/a |             n/a |                n/a |             n/a |

- **SKIP** -- placement: no arm reported bls scheduler counters

## Frequency divergence

Per-CPU busy MHz averaged over runs. If little/big is near 1.0 the partition is not physically real and everything downstream is moot.

### `both-balance` (n=7)

| cpu  | domain | epp | bzy MHz | avg MHz |  busy | SMT sibling |
| :--- | -----: | --: | ------: | ------: | ----: | ----------: |
| cpu0 |   flat | 128 |  3586.4 |  3510.5 | 97.9% |        cpu4 |
| cpu1 |   flat | 128 |  3323.6 |   27.23 |  0.8% |        cpu5 |
| cpu2 |   flat | 128 |  3586.4 |  3510.0 | 97.9% |        cpu6 |
| cpu3 |   flat | 128 |  3321.6 |   6.114 |  0.2% |        cpu7 |
| cpu4 |   flat | 128 |  3441.2 |   4.557 |  0.1% |        cpu0 |
| cpu5 |   flat | 128 |  3323.1 |   5.314 |  0.2% |        cpu1 |
| cpu6 |   flat | 128 |  3413.3 |   2.871 |  0.1% |        cpu2 |
| cpu7 |   flat | 128 |  3316.3 |   5.929 |  0.2% |        cpu3 |

- big domain bzy: **3414.0 MHz**, LITTLE domain bzy: **n/a MHz**
- **little_bzy_mhz / big_bzy_mhz = n/a**
- flat EPP: no big/LITTLE split was requested in this arm (all 8 CPUs report the same EPP)

### `both-performance` (n=7)

| cpu  | domain | epp | bzy MHz | avg MHz |  busy | SMT sibling |
| :--- | -----: | --: | ------: | ------: | ----: | ----------: |
| cpu0 |   flat |   0 |  3587.5 |  3512.4 | 97.9% |        cpu4 |
| cpu1 |   flat |   0 |  3330.9 |   29.71 |  0.9% |        cpu5 |
| cpu2 |   flat |   0 |  3587.5 |  3511.8 | 97.9% |        cpu6 |
| cpu3 |   flat |   0 |  3340.5 |   8.000 |  0.2% |        cpu7 |
| cpu4 |   flat |   0 |  3422.0 |   4.457 |  0.1% |        cpu0 |
| cpu5 |   flat |   0 |  3329.5 |   6.357 |  0.2% |        cpu1 |
| cpu6 |   flat |   0 |  3425.3 |   3.743 |  0.1% |        cpu2 |
| cpu7 |   flat |   0 |  3329.3 |   6.686 |  0.2% |        cpu3 |

- big domain bzy: **3419.1 MHz**, LITTLE domain bzy: **n/a MHz**
- **little_bzy_mhz / big_bzy_mhz = n/a**
- flat EPP: no big/LITTLE split was requested in this arm (all 8 CPUs report the same EPP)

### `both-power` (n=7)

| cpu  | domain | epp | bzy MHz | avg MHz |   busy | SMT sibling |
| :--- | -----: | --: | ------: | ------: | -----: | ----------: |
| cpu0 |   flat | 255 |  950.57 |  951.34 | 100.1% |        cpu4 |
| cpu1 |   flat | 255 |  947.31 |   28.33 |   3.0% |        cpu5 |
| cpu2 |   flat | 255 |  950.57 |  951.27 | 100.1% |        cpu6 |
| cpu3 |   flat | 255 |  943.97 |   6.443 |   0.7% |        cpu7 |
| cpu4 |   flat | 255 |  941.31 |   3.529 |   0.4% |        cpu0 |
| cpu5 |   flat | 255 |  944.14 |   5.100 |   0.6% |        cpu1 |
| cpu6 |   flat | 255 |  945.83 |   4.900 |   0.5% |        cpu2 |
| cpu7 |   flat | 255 |  942.90 |   6.671 |   0.7% |        cpu3 |

- big domain bzy: **945.83 MHz**, LITTLE domain bzy: **n/a MHz**
- **little_bzy_mhz / big_bzy_mhz = n/a**
- flat EPP: no big/LITTLE split was requested in this arm (all 8 CPUs report the same EPP)

### `partitioned` (n=7)

| cpu  | domain | epp | bzy MHz | avg MHz |  busy | SMT sibling |
| :--- | -----: | --: | ------: | ------: | ----: | ----------: |
| cpu0 |    big |   0 |  3588.7 |  3514.3 | 97.9% |        cpu4 |
| cpu1 |    big |   0 |  3330.8 |   25.57 |  0.8% |        cpu5 |
| cpu2 | LITTLE | 255 |  3588.7 |  3513.9 | 97.9% |        cpu6 |
| cpu3 | LITTLE | 255 |  3335.9 |   6.271 |  0.2% |        cpu7 |
| cpu4 |    big |   0 |  3455.5 |   3.114 |  0.1% |        cpu0 |
| cpu5 |    big |   0 |  3331.4 |   5.929 |  0.2% |        cpu1 |
| cpu6 | LITTLE | 255 |  3429.9 |   3.400 |  0.1% |        cpu2 |
| cpu7 | LITTLE | 255 |  3327.8 |   6.414 |  0.2% |        cpu3 |

- big domain bzy: **3426.6 MHz**, LITTLE domain bzy: **3420.5 MHz**
- **little_bzy_mhz / big_bzy_mhz = 0.998** (95% CI [0.995, 1.001], BCa)
- NOT PHYSICALLY REAL: LITTLE cores ran at 100% of big-core frequency (>= 90%). The EPP write did not separate the domains, so nothing downstream of this can be attributed to partitioning.

**The partition is NOT physically real in any arm: LITTLE-domain frequency is within 10% of big-domain frequency. Everything downstream is moot -- the energy comparison is a comparison of the machine against itself.**

## Per-arm summary

Mean with a 95% bootstrap CI (10000 resamples). `n` is the number of runs that actually carried the metric.

### `energy_to_solution_j` (J) -- package energy to complete the workload

| arm                     |   n | missing |   mean | median |    sd |   95% CI of mean | CI method |
| :---------------------- | --: | ------: | -----: | -----: | ----: | ---------------: | --------: |
| both-balance  [control] |   7 |       0 | 260.90 | 260.94 | 0.317 | [260.70, 261.14] |       BCa |
| both-performance        |   7 |       0 | 262.27 | 262.21 | 0.859 | [261.73, 262.90] |       BCa |
| both-power              |   7 |       0 |  30.62 |  30.49 | 0.919 |   [30.18, 31.59] |       BCa |
| partitioned             |   7 |       0 | 262.09 | 261.95 | 0.603 | [261.69, 262.51] |       BCa |

### `edp_js` (J*s) -- energy-delay product (pkg_j * wall_s)

| arm                     |   n | missing |   mean | median |    sd |   95% CI of mean | CI method |
| :---------------------- | --: | ------: | -----: | -----: | ----: | ---------------: | --------: |
| both-balance  [control] |   7 |       0 | 5218.8 | 5219.6 | 6.313 | [5214.7, 5223.5] |       BCa |
| both-performance        |   7 |       0 | 5245.8 | 5244.5 | 17.16 | [5235.0, 5258.2] |       BCa |
| both-power              |   7 |       0 | 612.61 | 609.98 | 18.38 | [603.74, 631.84] |       BCa |
| partitioned             |   7 |       0 | 5242.2 | 5239.4 | 12.07 | [5234.2, 5250.6] |       BCa |

### `pkg_j_per_s` (W) -- mean package power

| arm                     |   n | missing |  mean | median |    sd | 95% CI of mean | CI method |
| :---------------------- | --: | ------: | ----: | -----: | ----: | -------------: | --------: |
| both-balance  [control] |   7 |       0 | 13.04 |  13.05 | 0.016 | [13.03, 13.06] |       BCa |
| both-performance        |   7 |       0 | 13.11 |  13.11 | 0.043 | [13.09, 13.14] |       BCa |
| both-power              |   7 |       0 | 1.531 |  1.524 | 0.046 | [1.509, 1.579] |       BCa |
| partitioned             |   7 |       0 | 13.10 |  13.10 | 0.030 | [13.08, 13.12] |       BCa |

### `wall_s` (s) -- time to solution

| arm                     |   n | missing |  mean | median |        sd | 95% CI of mean | CI method |
| :---------------------- | --: | ------: | ----: | -----: | --------: | -------------: | --------: |
| both-balance  [control] |   7 |       0 | 20.00 |  20.00 | 2.309e-04 | [20.00, 20.00] |       BCa |
| both-performance        |   7 |       0 | 20.00 |  20.00 | 1.704e-04 | [20.00, 20.00] |       BCa |
| both-power              |   7 |       0 | 20.00 |  20.00 | 2.870e-04 | [20.00, 20.00] |       BCa |
| partitioned             |   7 |       0 | 20.00 |  20.00 | 1.272e-04 | [20.00, 20.00] |       BCa |

### `core_j` (J) -- core-domain energy (the part EPP can touch)

| arm                     |   n | missing |   mean | median |    sd |   95% CI of mean | CI method |
| :---------------------- | --: | ------: | -----: | -----: | ----: | ---------------: | --------: |
| both-balance  [control] |   7 |       0 | 245.83 | 246.22 | 1.026 | [244.95, 246.41] |       BCa |
| both-performance        |   7 |       0 | 246.88 | 247.10 | 1.060 | [245.97, 247.46] |       BCa |
| both-power              |   7 |       0 |  15.68 |  16.01 | 0.640 |   [15.16, 16.05] |       BCa |
| partitioned             |   7 |       0 | 247.00 | 247.04 | 0.610 | [246.55, 247.39] |       BCa |

### `rest_frac` (-) -- share of pkg energy EPP cannot touch

| arm                     |   n | missing |  mean | median |    sd | 95% CI of mean | CI method |
| :---------------------- | --: | ------: | ----: | -----: | ----: | -------------: | --------: |
| both-balance  [control] |   7 |       0 | 0.058 |  0.056 | 0.004 | [0.056, 0.061] |       BCa |
| both-performance        |   7 |       0 | 0.059 |  0.056 | 0.004 | [0.056, 0.062] |       BCa |
| both-power              |   7 |       0 | 0.487 |  0.480 | 0.021 | [0.474, 0.504] |       BCa |
| partitioned             |   7 |       0 | 0.058 |  0.056 | 0.004 | [0.055, 0.061] |       BCa |

### `bzy_mhz_big_mean` (MHz) -- mean busy MHz of the big domain

| arm                     |   n | missing |   mean | median |    sd |   95% CI of mean | CI method |
| :---------------------- | --: | ------: | -----: | -----: | ----: | ---------------: | --------: |
| both-balance  [control] |   7 |       0 | 3414.0 | 3417.3 | 10.33 | [3405.9, 3420.2] |       BCa |
| both-performance        |   7 |       0 | 3419.1 | 3420.7 | 9.968 | [3411.0, 3424.8] |       BCa |
| both-power              |   7 |       0 | 945.83 | 947.15 | 13.33 | [935.21, 953.75] |       BCa |
| partitioned             |   7 |       0 | 3426.6 | 3428.4 | 9.630 | [3418.9, 3432.3] |       BCa |

### `bzy_mhz_little_mean` (MHz) -- mean busy MHz of the LITTLE domain

| arm                     |   n | missing |   mean | median |    sd |   95% CI of mean | CI method |
| :---------------------- | --: | ------: | -----: | -----: | ----: | ---------------: | --------: |
| both-balance  [control] |   0 |       7 |    n/a |    n/a |   n/a |       [n/a, n/a] |       n/a |
| both-performance        |   0 |       7 |    n/a |    n/a |   n/a |       [n/a, n/a] |       n/a |
| both-power              |   0 |       7 |    n/a |    n/a |   n/a |       [n/a, n/a] |       n/a |
| partitioned             |   7 |       0 | 3420.5 | 3421.4 | 7.963 | [3415.2, 3426.1] |       BCa |

## Contrasts vs control (`both-balance`)

Difference in means (arm - control). A contrast whose CI straddles zero is reported as *no detectable difference*, never as a signed saving.

### `both-performance` vs `both-balance`

| metric               | n ctl/arm | control mean | arm mean |      diff |   95% CI of diff | % change | Hedges g |   p (perm) | MDE (abs) | MDE (%) |                   result |
| :------------------- | --------: | -----------: | -------: | --------: | ---------------: | -------: | -------: | ---------: | --------: | ------: | -----------------------: |
| energy_to_solution_j |       7/7 |       260.90 |   262.27 |     1.369 |   [0.778, 2.031] |    +0.5% |    1.979 |     0.0025 |     1.057 |    0.4% |           higher (worse) |
| edp_js               |       7/7 |       5218.8 |   5245.8 |     27.00 |   [15.21, 40.24] |    +0.5% |    1.955 |     0.0025 |     21.09 |    0.4% |           higher (worse) |
| pkg_j_per_s          |       7/7 |        13.04 |    13.11 |     0.069 |   [0.040, 0.103] |    +0.5% |    2.003 |     0.0025 |     0.053 |    0.4% |           higher (worse) |
| wall_s               |       7/7 |        20.00 |    20.00 |    -0.001 | [-0.002, -0.001] |    -0.0% |   -6.787 | 8.9991e-04 | 3.310e-04 |    0.0% |           lower (better) |
| core_j               |       7/7 |       245.83 |   246.88 |     1.049 |   [0.017, 2.046] |    +0.4% |    0.941 |     0.0883 |     1.701 |    0.7% |           higher (worse) |
| rest_frac            |       7/7 |        0.058 |    0.059 | 8.886e-04 |  [-0.003, 0.004] |    +1.5% |    0.224 |     0.7718 |     0.006 |   10.5% | no detectable difference |
| bzy_mhz_big_mean     |       7/7 |       3414.0 |   3419.1 |     5.066 |  [-4.617, 14.94] |    +0.1% |    0.467 |     0.3615 |     16.55 |    0.5% | no detectable difference |
| bzy_mhz_little_mean  |       0/0 |          n/a |      n/a |       n/a |       [n/a, n/a] |      n/a |      n/a |        n/a |       n/a |     n/a |        insufficient data |

- energy_to_solution_j: higher than control by 1.369 J (+0.5%), 95% CI [0.778, 2.031] excludes zero; Hedges g = 1.979, permutation p = 0.0025; MDE = 1.057 J.
- edp_js: higher than control by 27.00 J*s (+0.5%), 95% CI [15.21, 40.24] excludes zero; Hedges g = 1.955, permutation p = 0.0025; MDE = 21.09 J*s.
- pkg_j_per_s: higher than control by 0.069 W (+0.5%), 95% CI [0.040, 0.103] excludes zero; Hedges g = 2.003, permutation p = 0.0025; MDE = 0.053 W.
- wall_s: lower than control by 0.001 s (-0.0%), 95% CI [-0.002, -0.001] excludes zero; Hedges g = -6.787, permutation p = 8.9991e-04; MDE = 3.310e-04 s.
- core_j: higher than control by 1.049 J (+0.4%), 95% CI [0.017, 2.046] excludes zero; Hedges g = 0.941, permutation p = 0.0883; MDE = 1.701 J.
- rest_frac: no detectable difference (|effect| < MDE = 0.006 - = 10.5% of control).
- bzy_mhz_big_mean: no detectable difference (|effect| < MDE = 16.55 MHz = 0.5% of control).
- bzy_mhz_little_mean: insufficient data (n_control=0, n_arm=0); no contrast computed.

### `both-power` vs `both-balance`

| metric               | n ctl/arm | control mean | arm mean |      diff |     95% CI of diff | % change | Hedges g |   p (perm) | MDE (abs) | MDE (%) |              result |
| :------------------- | --------: | -----------: | -------: | --------: | -----------------: | -------: | -------: | ---------: | --------: | ------: | ------------------: |
| energy_to_solution_j |       7/7 |       260.90 |    30.62 |   -230.28 | [-230.78, -229.36] |   -88.3% |  -313.56 | 8.9991e-04 |     1.121 |    0.4% |      lower (better) |
| edp_js               |       7/7 |       5218.8 |   612.61 |   -4606.2 | [-4616.2, -4587.8] |   -88.3% |  -313.83 | 8.9991e-04 |     22.41 |    0.4% |      lower (better) |
| pkg_j_per_s          |       7/7 |        13.04 |    1.531 |    -11.51 |   [-11.54, -11.47] |   -88.3% |  -313.29 | 8.9991e-04 |     0.056 |    0.4% |      lower (better) |
| wall_s               |       7/7 |        20.00 |    20.00 | 9.286e-04 | [6.571e-04, 0.001] |    +0.0% |    3.337 | 8.9991e-04 | 4.249e-04 |    0.0% |      higher (worse) |
| core_j               |       7/7 |       245.83 |    15.68 |   -230.15 | [-230.90, -229.22] |   -93.6% |  -251.96 | 8.9991e-04 |     1.395 |    0.6% |      lower (better) |
| rest_frac            |       7/7 |        0.058 |    0.487 |     0.429 |     [0.416, 0.446] |  +743.5% |    26.14 | 8.9991e-04 |     0.025 |   43.4% | higher (diagnostic) |
| bzy_mhz_big_mean     |       7/7 |       3414.0 |   945.83 |   -2468.2 | [-2480.2, -2457.1] |   -72.3% |  -193.80 | 8.9991e-04 |     19.45 |    0.6% |  lower (diagnostic) |
| bzy_mhz_little_mean  |       0/0 |          n/a |      n/a |       n/a |         [n/a, n/a] |      n/a |      n/a |        n/a |       n/a |     n/a |   insufficient data |

- energy_to_solution_j: lower than control by 230.28 J (-88.3%), 95% CI [-230.78, -229.36] excludes zero; Hedges g = -313.56, permutation p = 8.9991e-04; MDE = 1.121 J.
- edp_js: lower than control by 4606.2 J*s (-88.3%), 95% CI [-4616.2, -4587.8] excludes zero; Hedges g = -313.83, permutation p = 8.9991e-04; MDE = 22.41 J*s.
- pkg_j_per_s: lower than control by 11.51 W (-88.3%), 95% CI [-11.54, -11.47] excludes zero; Hedges g = -313.29, permutation p = 8.9991e-04; MDE = 0.056 W.
- wall_s: higher than control by 9.286e-04 s (+0.0%), 95% CI [6.571e-04, 0.001] excludes zero; Hedges g = 3.337, permutation p = 8.9991e-04; MDE = 4.249e-04 s.
- core_j: lower than control by 230.15 J (-93.6%), 95% CI [-230.90, -229.22] excludes zero; Hedges g = -251.96, permutation p = 8.9991e-04; MDE = 1.395 J.
- rest_frac: higher than control by 0.429 - (+743.5%), 95% CI [0.416, 0.446] excludes zero; Hedges g = 26.14, permutation p = 8.9991e-04; MDE = 0.025 -.
- bzy_mhz_big_mean: lower than control by 2468.2 MHz (-72.3%), 95% CI [-2480.2, -2457.1] excludes zero; Hedges g = -193.80, permutation p = 8.9991e-04; MDE = 19.45 MHz.
- bzy_mhz_little_mean: insufficient data (n_control=0, n_arm=0); no contrast computed.

### `partitioned` vs `both-balance`

| metric               | n ctl/arm | control mean | arm mean |       diff |   95% CI of diff | % change | Hedges g |   p (perm) | MDE (abs) | MDE (%) |                   result |
| :------------------- | --------: | -----------: | -------: | ---------: | ---------------: | -------: | -------: | ---------: | --------: | ------: | -----------------------: |
| energy_to_solution_j |       7/7 |       260.90 |   262.09 |      1.189 |   [0.723, 1.655] |    +0.5% |    2.309 | 8.9991e-04 |     0.786 |    0.3% |           higher (worse) |
| edp_js               |       7/7 |       5218.8 |   5242.2 |      23.41 |   [14.12, 32.72] |    +0.4% |    2.276 | 8.9991e-04 |     15.71 |    0.3% |           higher (worse) |
| pkg_j_per_s          |       7/7 |        13.04 |    13.10 |      0.060 |   [0.037, 0.084] |    +0.5% |    2.342 | 8.9991e-04 |     0.039 |    0.3% |           higher (worse) |
| wall_s               |       7/7 |        20.00 |    20.00 |     -0.001 | [-0.002, -0.001] |    -0.0% |   -7.245 | 8.9991e-04 | 3.041e-04 |    0.0% |           lower (better) |
| core_j               |       7/7 |       245.83 |   247.00 |      1.169 |   [0.458, 2.097] |    +0.5% |    1.297 |     0.0176 |     1.377 |    0.6% |           higher (worse) |
| rest_frac            |       7/7 |        0.058 |    0.058 | -1.775e-04 |  [-0.004, 0.003] |    -0.3% |   -0.045 |     0.7758 |     0.006 |   10.4% | no detectable difference |
| bzy_mhz_big_mean     |       7/7 |       3414.0 |   3426.6 |      12.59 |   [3.278, 22.39] |    +0.4% |    1.181 |     0.0399 |     16.29 |    0.5% |      higher (diagnostic) |
| bzy_mhz_little_mean  |       0/7 |          n/a |   3420.5 |        n/a |       [n/a, n/a] |      n/a |      n/a |        n/a |       n/a |     n/a |        insufficient data |

- energy_to_solution_j: higher than control by 1.189 J (+0.5%), 95% CI [0.723, 1.655] excludes zero; Hedges g = 2.309, permutation p = 8.9991e-04; MDE = 0.786 J.
- edp_js: higher than control by 23.41 J*s (+0.4%), 95% CI [14.12, 32.72] excludes zero; Hedges g = 2.276, permutation p = 8.9991e-04; MDE = 15.71 J*s.
- pkg_j_per_s: higher than control by 0.060 W (+0.5%), 95% CI [0.037, 0.084] excludes zero; Hedges g = 2.342, permutation p = 8.9991e-04; MDE = 0.039 W.
- wall_s: lower than control by 0.001 s (-0.0%), 95% CI [-0.002, -0.001] excludes zero; Hedges g = -7.245, permutation p = 8.9991e-04; MDE = 3.041e-04 s.
- core_j: higher than control by 1.169 J (+0.5%), 95% CI [0.458, 2.097] excludes zero; Hedges g = 1.297, permutation p = 0.0176; MDE = 1.377 J.
- rest_frac: no detectable difference (|effect| < MDE = 0.006 - = 10.4% of control).
- bzy_mhz_big_mean: higher than control by 12.59 MHz (+0.4%), 95% CI [3.278, 22.39] excludes zero; Hedges g = 1.181, permutation p = 0.0399; MDE = 16.29 MHz.
- bzy_mhz_little_mean: insufficient data (n_control=0, n_arm=7); no contrast computed.

## Minimum detectable effect

At 80% power, alpha 0.05, two-sided, from the observed pooled sd and n. This matters more than any p-value here: it is the smallest true effect this design could have caught. Effects below it are invisible to the experiment, not absent from the machine.

| arm              |               metric | unit | n ctl/arm | pooled sd | control mean | MDE (abs) | MDE (% of control) |
| :--------------- | -------------------: | ---: | --------: | --------: | -----------: | --------: | -----------------: |
| both-performance | energy_to_solution_j |    J |       7/7 |     0.648 |       260.90 |     1.057 |               0.4% |
| both-performance |               edp_js |  J*s |       7/7 |     12.93 |       5218.8 |     21.09 |               0.4% |
| both-performance |          pkg_j_per_s |    W |       7/7 |     0.032 |        13.04 |     0.053 |               0.4% |
| both-performance |               wall_s |    s |       7/7 | 2.030e-04 |        20.00 | 3.310e-04 |               0.0% |
| both-performance |               core_j |    J |       7/7 |     1.043 |       245.83 |     1.701 |               0.7% |
| both-performance |            rest_frac |    - |       7/7 |     0.004 |        0.058 |     0.006 |              10.5% |
| both-performance |     bzy_mhz_big_mean |  MHz |       7/7 |     10.15 |       3414.0 |     16.55 |               0.5% |
| both-performance |  bzy_mhz_little_mean |  MHz |       0/0 |       n/a |          n/a |       n/a |                n/a |
| both-power       | energy_to_solution_j |    J |       7/7 |     0.688 |       260.90 |     1.121 |               0.4% |
| both-power       |               edp_js |  J*s |       7/7 |     13.74 |       5218.8 |     22.41 |               0.4% |
| both-power       |          pkg_j_per_s |    W |       7/7 |     0.034 |        13.04 |     0.056 |               0.4% |
| both-power       |               wall_s |    s |       7/7 | 2.605e-04 |        20.00 | 4.249e-04 |               0.0% |
| both-power       |               core_j |    J |       7/7 |     0.855 |       245.83 |     1.395 |               0.6% |
| both-power       |            rest_frac |    - |       7/7 |     0.015 |        0.058 |     0.025 |              43.4% |
| both-power       |     bzy_mhz_big_mean |  MHz |       7/7 |     11.92 |       3414.0 |     19.45 |               0.6% |
| both-power       |  bzy_mhz_little_mean |  MHz |       0/0 |       n/a |          n/a |       n/a |                n/a |
| partitioned      | energy_to_solution_j |    J |       7/7 |     0.482 |       260.90 |     0.786 |               0.3% |
| partitioned      |               edp_js |  J*s |       7/7 |     9.629 |       5218.8 |     15.71 |               0.3% |
| partitioned      |          pkg_j_per_s |    W |       7/7 |     0.024 |        13.04 |     0.039 |               0.3% |
| partitioned      |               wall_s |    s |       7/7 | 1.864e-04 |        20.00 | 3.041e-04 |               0.0% |
| partitioned      |               core_j |    J |       7/7 |     0.844 |       245.83 |     1.377 |               0.6% |
| partitioned      |            rest_frac |    - |       7/7 |     0.004 |        0.058 |     0.006 |              10.4% |
| partitioned      |     bzy_mhz_big_mean |  MHz |       7/7 |     9.985 |       3414.0 |     16.29 |               0.5% |
| partitioned      |  bzy_mhz_little_mean |  MHz |       0/7 |       n/a |          n/a |       n/a |                n/a |

Reading: on `energy_to_solution_j`, the weakest arm comparison (`both-power`) can only detect effects of **0.4% or larger**. To halve that, quadruple the reps.

## Coverage

| field              | present | missing | coverage |
| :----------------- | ------: | ------: | -------: |
| energy.pkg_j       |      28 |       0 |     100% |
| energy.wall_s      |      28 |       0 |     100% |
| energy.rest_j      |      28 |       0 |     100% |
| energy.cpu_bzy_mhz |      28 |       0 |     100% |
| energy.epp         |      28 |       0 |     100% |
| env.start_temp_c   |      28 |       0 |     100% |
| energy.pkg_c_max   |      28 |       0 |     100% |
| pinger             |       0 |      28 |       0% |
| spin               |      28 |       0 |     100% |
| bls                |       0 |      28 |       0% |

---

# Experiment `e1b-poison`

- Runs: **28** across 4 arms (others-balance n=7, others-balance-power n=7, others-performance n=7, others-power n=7)
- Control arm: **`others-balance`** (first arm alphabetically (no eevdf/flat arm present))

## Verdict

- others-balance-power vs others-balance: energy-to-solution is LOWER by 106.59 J (-64.1%), 95% CI [-107.25, -106.04] excludes zero (Hedges g = -159.22, permutation p = 8.9991e-04).
-    CAUTION: this apparent saving is not admissible while these gates fail: partition is physically real: others-performance, run-order drift.
- others-performance vs others-balance: energy-to-solution is HIGHER by 0.592 J (0.4%), 95% CI [0.319, 0.943] excludes zero (Hedges g = 1.726, permutation p = 0.0033).
-    CAUTION: this apparent regression is not admissible while these gates fail: partition is physically real: others-performance, run-order drift.
- others-power vs others-balance: energy-to-solution is LOWER by 138.33 J (-83.2%), 95% CI [-138.50, -138.22] excludes zero (Hedges g = -925.12, permutation p = 8.9991e-04).
-    CAUTION: this apparent saving is not admissible while these gates fail: partition is physically real: others-performance, run-order drift.
- The partition is NOT physically real in any arm: LITTLE-domain frequency is within 10% of big-domain frequency. Everything downstream is moot -- the energy comparison is a comparison of the machine against itself.
- Failing gates: partition is physically real: others-performance, run-order drift.

## Data quality

| status | gate                                             | numbers                                                                                                                                                                                                                                                                                                                                                                                                                       |
| :----- | :----------------------------------------------- | :---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| PASS   | run completion                                   | 28/28 runs have ok=true and exit_code=0                                                                                                                                                                                                                                                                                                                                                                                       |
| PASS   | start temperature spread                         | max-min of per-arm mean start_temp_c = 2.00 C (limit 5.0); hottest others-performance 49.6 C, coldest others-balance 47.6 C                                                                                                                                                                                                                                                                                                   |
| PASS   | on_ac consistent                                 | all 28 runs on_ac=True                                                                                                                                                                                                                                                                                                                                                                                                        |
| PASS   | thermal headroom                                 | max pkg_c_max = 66.0 C in arm others-performance (limit 97.0 C = Tjmax-3); 0/28 runs at or above the limit                                                                                                                                                                                                                                                                                                                    |
| PASS   | balanced reps per arm                            | others-balance=7, others-balance-power=7, others-performance=7, others-power=7                                                                                                                                                                                                                                                                                                                                                |
| FAIL   | run-order drift                                  | 7 arm/metric pairs with \|Spearman rho vs rep\| > 0.6: others-balance-power/energy_to_solution_j rho=-0.79; others-balance-power/edp_js rho=-0.79; others-balance-power/pkg_j_per_s rho=-0.79; others-balance-power/wall_s rho=+0.84; others-power/energy_to_solution_j rho=+0.79; others-power/edp_js rho=+0.79  [n=7 per arm: rho is noisy at this size, treat as a prompt to inspect the run order, not as proof of drift] |
| FAIL   | partition is physically real: others-performance | little/big bzy MHz = 1.038 (3597.7 MHz / 3467.0 MHz over 7 runs); a real split needs < 0.90  -- EPP did not separate the frequency domains, so no downstream energy difference can be attributed to partitioning.                                                                                                                                                                                                             |

**2 gate(s) FAILED.** A failed gate means the arms are not comparable; effect sizes below are reported for completeness but must not be quoted as results until the gate is fixed.

## Placement sanity

A partitioning experiment where the tasks did not stay partitioned proves nothing, so this comes before the effect sizes.

| arm                  | runs w/ bls | strict | enqueues (mean) | cross-domain / enqueue | run time in big | run time in LITTLE | dispatch to big |
| :------------------- | ----------: | -----: | --------------: | ---------------------: | --------------: | -----------------: | --------------: |
| others-balance       |         0/7 |    n/a |             n/a |                    n/a |             n/a |                n/a |             n/a |
| others-balance-power |         0/7 |    n/a |             n/a |                    n/a |             n/a |                n/a |             n/a |
| others-performance   |         0/7 |    n/a |             n/a |                    n/a |             n/a |                n/a |             n/a |
| others-power         |         0/7 |    n/a |             n/a |                    n/a |             n/a |                n/a |             n/a |

- **SKIP** -- placement: no arm reported bls scheduler counters

## Per-arm summary

Mean with a 95% bootstrap CI (10000 resamples). `n` is the number of runs that actually carried the metric.

### `energy_to_solution_j` (J) -- package energy to complete the workload

| arm                       |   n | missing |   mean | median |    sd |   95% CI of mean | CI method |
| :------------------------ | --: | ------: | -----: | -----: | ----: | ---------------: | --------: |
| others-balance  [control] |   7 |       0 | 166.26 | 166.19 | 0.191 | [166.15, 166.42] |       BCa |
| others-balance-power      |   7 |       0 |  59.67 |  60.06 | 0.865 |   [59.03, 60.20] |       BCa |
| others-performance        |   7 |       0 | 166.85 | 166.79 | 0.412 | [166.62, 167.19] |       BCa |
| others-power              |   7 |       0 |  27.92 |  27.93 | 0.051 |   [27.89, 27.96] |       BCa |

### `edp_js` (J*s) -- energy-delay product (pkg_j * wall_s)

| arm                       |   n | missing |   mean | median |    sd |   95% CI of mean | CI method |
| :------------------------ | --: | ------: | -----: | -----: | ----: | ---------------: | --------: |
| others-balance  [control] |   7 |       0 | 3325.6 | 3324.3 | 3.834 | [3323.4, 3328.9] |       BCa |
| others-balance-power      |   7 |       0 | 1193.6 | 1201.4 | 17.31 | [1180.8, 1204.1] |       BCa |
| others-performance        |   7 |       0 | 3337.2 | 3336.0 | 8.237 | [3332.6, 3344.0] |       BCa |
| others-power              |   7 |       0 | 558.58 | 558.73 | 1.027 | [557.86, 559.26] |       BCa |

### `pkg_j_per_s` (W) -- mean package power

| arm                       |   n | missing |  mean | median |    sd | 95% CI of mean | CI method |
| :------------------------ | --: | ------: | ----: | -----: | ----: | -------------: | --------: |
| others-balance  [control] |   7 |       0 | 8.312 |  8.309 | 0.010 | [8.306, 8.320] |       BCa |
| others-balance-power      |   7 |       0 | 2.983 |  3.003 | 0.043 | [2.951, 3.009] |       BCa |
| others-performance        |   7 |       0 | 8.342 |  8.339 | 0.021 | [8.330, 8.359] |       BCa |
| others-power              |   7 |       0 | 1.396 |  1.396 | 0.003 | [1.394, 1.398] |       BCa |

### `wall_s` (s) -- time to solution

| arm                       |   n | missing |  mean | median |        sd | 95% CI of mean | CI method |
| :------------------------ | --: | ------: | ----: | -----: | --------: | -------------: | --------: |
| others-balance  [control] |   7 |       0 | 20.00 |  20.00 | 1.952e-04 | [20.00, 20.00] |       BCa |
| others-balance-power      |   7 |       0 | 20.00 |  20.00 | 9.759e-05 | [20.00, 20.00] |       BCa |
| others-performance        |   7 |       0 | 20.00 |  20.00 | 1.215e-04 | [20.00, 20.00] |       BCa |
| others-power              |   7 |       0 | 20.00 |  20.00 | 1.272e-04 | [20.00, 20.00] |       BCa |

### `core_j` (J) -- core-domain energy (the part EPP can touch)

| arm                       |   n | missing |   mean | median |    sd |   95% CI of mean | CI method |
| :------------------------ | --: | ------: | -----: | -----: | ----: | ---------------: | --------: |
| others-balance  [control] |   7 |       0 | 152.02 | 151.99 | 0.107 | [151.96, 152.11] |       BCa |
| others-balance-power      |   7 |       0 |  45.27 |  44.94 | 0.841 |   [44.71, 45.84] |       BCa |
| others-performance        |   7 |       0 | 152.42 | 152.31 | 0.221 | [152.29, 152.61] |       BCa |
| others-power              |   7 |       0 |  13.87 |  13.84 | 0.086 |   [13.83, 13.96] |       BCa |

### `rest_frac` (-) -- share of pkg energy EPP cannot touch

| arm                       |   n | missing |  mean | median |        sd | 95% CI of mean | CI method |
| :------------------------ | --: | ------: | ----: | -----: | --------: | -------------: | --------: |
| others-balance  [control] |   7 |       0 | 0.086 |  0.086 | 4.919e-04 | [0.085, 0.086] |       BCa |
| others-balance-power      |   7 |       0 | 0.241 |  0.240 |     0.009 | [0.237, 0.251] |       BCa |
| others-performance        |   7 |       0 | 0.086 |  0.087 |     0.001 | [0.086, 0.087] |       BCa |
| others-power              |   7 |       0 | 0.503 |  0.504 |     0.002 | [0.501, 0.505] |       BCa |

### `bzy_mhz_big_mean` (MHz) -- mean busy MHz of the big domain

| arm                       |   n | missing |   mean | median |    sd |   95% CI of mean | CI method |
| :------------------------ | --: | ------: | -----: | -----: | ----: | ---------------: | --------: |
| others-balance  [control] |   0 |       7 |    n/a |    n/a |   n/a |       [n/a, n/a] |       n/a |
| others-balance-power      |   0 |       7 |    n/a |    n/a |   n/a |       [n/a, n/a] |       n/a |
| others-performance        |   7 |       0 | 3467.0 | 3466.9 | 8.920 | [3460.1, 3472.6] |       BCa |
| others-power              |   7 |       0 | 1181.4 | 1186.5 | 8.747 | [1174.2, 1186.5] |       BCa |

### `bzy_mhz_little_mean` (MHz) -- mean busy MHz of the LITTLE domain

| arm                       |   n | missing |   mean | median |    sd |   95% CI of mean | CI method |
| :------------------------ | --: | ------: | -----: | -----: | ----: | ---------------: | --------: |
| others-balance  [control] |   7 |       0 | 3463.1 | 3466.0 | 7.954 | [3457.1, 3468.0] |       BCa |
| others-balance-power      |   7 |       0 | 2254.0 | 2254.4 | 11.69 | [2245.6, 2261.6] |       BCa |
| others-performance        |   7 |       0 | 3597.7 | 3597.6 | 0.752 | [3597.1, 3598.2] |       BCa |
| others-power              |   0 |       7 |    n/a |    n/a |   n/a |       [n/a, n/a] |       n/a |

## Contrasts vs control (`others-balance`)

Difference in means (arm - control). A contrast whose CI straddles zero is reported as *no detectable difference*, never as a signed saving.

### `others-balance-power` vs `others-balance`

| metric               | n ctl/arm | control mean | arm mean |      diff |         95% CI of diff | % change | Hedges g |   p (perm) | MDE (abs) | MDE (%) |              result |
| :------------------- | --------: | -----------: | -------: | --------: | ---------------------: | -------: | -------: | ---------: | --------: | ------: | ------------------: |
| energy_to_solution_j |       7/7 |       166.26 |    59.67 |   -106.59 |     [-107.25, -106.04] |   -64.1% |  -159.22 | 8.9991e-04 |     1.022 |    0.6% |      lower (better) |
| edp_js               |       7/7 |       3325.6 |   1193.6 |   -2132.0 |     [-2145.3, -2121.0] |   -64.1% |  -159.23 | 8.9991e-04 |     20.44 |    0.6% |      lower (better) |
| pkg_j_per_s          |       7/7 |        8.312 |    2.983 |    -5.329 |       [-5.362, -5.301] |   -64.1% |  -159.20 | 8.9991e-04 |     0.051 |    0.6% |      lower (better) |
| wall_s               |       7/7 |        20.00 |    20.00 | 1.714e-04 | [5.714e-05, 3.714e-04] |    +0.0% |    1.040 |     0.0756 | 2.517e-04 |    0.0% |      higher (worse) |
| core_j               |       7/7 |       152.02 |    45.27 |   -106.75 |     [-107.32, -106.18] |   -70.2% |  -166.66 | 8.9991e-04 |     0.978 |    0.6% |      lower (better) |
| rest_frac            |       7/7 |        0.086 |    0.241 |     0.156 |         [0.151, 0.166] |  +181.9% |    22.24 | 8.9991e-04 |     0.011 |   12.5% | higher (diagnostic) |
| bzy_mhz_big_mean     |       0/0 |          n/a |      n/a |       n/a |             [n/a, n/a] |      n/a |      n/a |        n/a |       n/a |     n/a |   insufficient data |
| bzy_mhz_little_mean  |       7/7 |       3463.1 |   2254.0 |   -1209.2 |     [-1219.1, -1199.6] |   -34.9% |  -113.23 | 8.9991e-04 |     16.31 |    0.5% |  lower (diagnostic) |

- energy_to_solution_j: lower than control by 106.59 J (-64.1%), 95% CI [-107.25, -106.04] excludes zero; Hedges g = -159.22, permutation p = 8.9991e-04; MDE = 1.022 J.
- edp_js: lower than control by 2132.0 J*s (-64.1%), 95% CI [-2145.3, -2121.0] excludes zero; Hedges g = -159.23, permutation p = 8.9991e-04; MDE = 20.44 J*s.
- pkg_j_per_s: lower than control by 5.329 W (-64.1%), 95% CI [-5.362, -5.301] excludes zero; Hedges g = -159.20, permutation p = 8.9991e-04; MDE = 0.051 W.
- wall_s: higher than control by 1.714e-04 s (+0.0%), 95% CI [5.714e-05, 3.714e-04] excludes zero; Hedges g = 1.040, permutation p = 0.0756; MDE = 2.517e-04 s.
- core_j: lower than control by 106.75 J (-70.2%), 95% CI [-107.32, -106.18] excludes zero; Hedges g = -166.66, permutation p = 8.9991e-04; MDE = 0.978 J.
- rest_frac: higher than control by 0.156 - (+181.9%), 95% CI [0.151, 0.166] excludes zero; Hedges g = 22.24, permutation p = 8.9991e-04; MDE = 0.011 -.
- bzy_mhz_big_mean: insufficient data (n_control=0, n_arm=0); no contrast computed.
- bzy_mhz_little_mean: lower than control by 1209.2 MHz (-34.9%), 95% CI [-1219.1, -1199.6] excludes zero; Hedges g = -113.23, permutation p = 8.9991e-04; MDE = 16.31 MHz.

### `others-performance` vs `others-balance`

| metric               | n ctl/arm | control mean | arm mean |      diff |     95% CI of diff | % change | Hedges g |   p (perm) | MDE (abs) | MDE (%) |              result |
| :------------------- | --------: | -----------: | -------: | --------: | -----------------: | -------: | -------: | ---------: | --------: | ------: | ------------------: |
| energy_to_solution_j |       7/7 |       166.26 |   166.85 |     0.592 |     [0.319, 0.943] |    +0.4% |    1.726 |     0.0033 |     0.524 |    0.3% |      higher (worse) |
| edp_js               |       7/7 |       3325.6 |   3337.2 |     11.63 |     [6.179, 18.66] |    +0.3% |    1.695 |     0.0039 |     10.48 |    0.3% |      higher (worse) |
| pkg_j_per_s          |       7/7 |        8.312 |    8.342 |     0.030 |     [0.016, 0.048] |    +0.4% |    1.758 |     0.0033 |     0.026 |    0.3% |      higher (worse) |
| wall_s               |       7/7 |        20.00 |    20.00 |    -0.001 |   [-0.001, -0.001] |    -0.0% |   -7.322 | 8.9991e-04 | 2.652e-04 |    0.0% |      lower (better) |
| core_j               |       7/7 |       152.02 |   152.42 |     0.393 |     [0.252, 0.593] |    +0.3% |    2.124 | 8.9991e-04 |     0.283 |    0.2% |      higher (worse) |
| rest_frac            |       7/7 |        0.086 |    0.086 | 8.822e-04 | [1.281e-04, 0.002] |    +1.0% |    1.037 |     0.0605 |     0.001 |    1.5% | higher (diagnostic) |
| bzy_mhz_big_mean     |       0/7 |          n/a |   3467.0 |       n/a |         [n/a, n/a] |      n/a |      n/a |        n/a |       n/a |     n/a |   insufficient data |
| bzy_mhz_little_mean  |       7/7 |       3463.1 |   3597.7 |    134.55 |   [129.54, 140.50] |    +3.9% |    22.30 | 8.9991e-04 |     9.214 |    0.3% | higher (diagnostic) |

- energy_to_solution_j: higher than control by 0.592 J (+0.4%), 95% CI [0.319, 0.943] excludes zero; Hedges g = 1.726, permutation p = 0.0033; MDE = 0.524 J.
- edp_js: higher than control by 11.63 J*s (+0.3%), 95% CI [6.179, 18.66] excludes zero; Hedges g = 1.695, permutation p = 0.0039; MDE = 10.48 J*s.
- pkg_j_per_s: higher than control by 0.030 W (+0.4%), 95% CI [0.016, 0.048] excludes zero; Hedges g = 1.758, permutation p = 0.0033; MDE = 0.026 W.
- wall_s: lower than control by 0.001 s (-0.0%), 95% CI [-0.001, -0.001] excludes zero; Hedges g = -7.322, permutation p = 8.9991e-04; MDE = 2.652e-04 s.
- core_j: higher than control by 0.393 J (+0.3%), 95% CI [0.252, 0.593] excludes zero; Hedges g = 2.124, permutation p = 8.9991e-04; MDE = 0.283 J.
- rest_frac: higher than control by 8.822e-04 - (+1.0%), 95% CI [1.281e-04, 0.002] excludes zero; Hedges g = 1.037, permutation p = 0.0605; MDE = 0.001 -.
- bzy_mhz_big_mean: insufficient data (n_control=0, n_arm=7); no contrast computed.
- bzy_mhz_little_mean: higher than control by 134.55 MHz (+3.9%), 95% CI [129.54, 140.50] excludes zero; Hedges g = 22.30, permutation p = 8.9991e-04; MDE = 9.214 MHz.

### `others-power` vs `others-balance`

| metric               | n ctl/arm | control mean | arm mean |      diff |         95% CI of diff | % change | Hedges g |   p (perm) | MDE (abs) | MDE (%) |              result |
| :------------------- | --------: | -----------: | -------: | --------: | ---------------------: | -------: | -------: | ---------: | --------: | ------: | ------------------: |
| energy_to_solution_j |       7/7 |       166.26 |    27.92 |   -138.33 |     [-138.50, -138.22] |   -83.2% |  -925.12 | 8.9991e-04 |     0.228 |    0.1% |      lower (better) |
| edp_js               |       7/7 |       3325.6 |   558.58 |   -2767.0 |     [-2770.4, -2764.7] |   -83.2% |  -922.95 | 8.9991e-04 |     4.578 |    0.1% |      lower (better) |
| pkg_j_per_s          |       7/7 |        8.312 |    1.396 |    -6.916 |       [-6.924, -6.910] |   -83.2% |  -927.23 | 8.9991e-04 |     0.011 |    0.1% |      lower (better) |
| wall_s               |       7/7 |        20.00 |    20.00 | 7.714e-04 | [6.429e-04, 9.571e-04] |    +0.0% |    4.384 | 8.9991e-04 | 2.687e-04 |    0.0% |      higher (worse) |
| core_j               |       7/7 |       152.02 |    13.87 |   -138.15 |     [-138.25, -138.06] |   -90.9% |  -1335.0 | 8.9991e-04 |     0.158 |    0.1% |      lower (better) |
| rest_frac            |       7/7 |        0.086 |    0.503 |     0.418 |         [0.415, 0.419] |  +487.9% |   220.13 | 8.9991e-04 |     0.003 |    3.4% | higher (diagnostic) |
| bzy_mhz_big_mean     |       0/7 |          n/a |   1181.4 |       n/a |             [n/a, n/a] |      n/a |      n/a |        n/a |       n/a |     n/a |   insufficient data |
| bzy_mhz_little_mean  |       7/0 |       3463.1 |      n/a |       n/a |             [n/a, n/a] |      n/a |      n/a |        n/a |       n/a |     n/a |   insufficient data |

- energy_to_solution_j: lower than control by 138.33 J (-83.2%), 95% CI [-138.50, -138.22] excludes zero; Hedges g = -925.12, permutation p = 8.9991e-04; MDE = 0.228 J.
- edp_js: lower than control by 2767.0 J*s (-83.2%), 95% CI [-2770.4, -2764.7] excludes zero; Hedges g = -922.95, permutation p = 8.9991e-04; MDE = 4.578 J*s.
- pkg_j_per_s: lower than control by 6.916 W (-83.2%), 95% CI [-6.924, -6.910] excludes zero; Hedges g = -927.23, permutation p = 8.9991e-04; MDE = 0.011 W.
- wall_s: higher than control by 7.714e-04 s (+0.0%), 95% CI [6.429e-04, 9.571e-04] excludes zero; Hedges g = 4.384, permutation p = 8.9991e-04; MDE = 2.687e-04 s.
- core_j: lower than control by 138.15 J (-90.9%), 95% CI [-138.25, -138.06] excludes zero; Hedges g = -1335.0, permutation p = 8.9991e-04; MDE = 0.158 J.
- rest_frac: higher than control by 0.418 - (+487.9%), 95% CI [0.415, 0.419] excludes zero; Hedges g = 220.13, permutation p = 8.9991e-04; MDE = 0.003 -.
- bzy_mhz_big_mean: insufficient data (n_control=0, n_arm=7); no contrast computed.
- bzy_mhz_little_mean: insufficient data (n_control=7, n_arm=0); no contrast computed.

## Minimum detectable effect

At 80% power, alpha 0.05, two-sided, from the observed pooled sd and n. This matters more than any p-value here: it is the smallest true effect this design could have caught. Effects below it are invisible to the experiment, not absent from the machine.

| arm                  |               metric | unit | n ctl/arm | pooled sd | control mean | MDE (abs) | MDE (% of control) |
| :------------------- | -------------------: | ---: | --------: | --------: | -----------: | --------: | -----------------: |
| others-balance-power | energy_to_solution_j |    J |       7/7 |     0.627 |       166.26 |     1.022 |               0.6% |
| others-balance-power |               edp_js |  J*s |       7/7 |     12.53 |       3325.6 |     20.44 |               0.6% |
| others-balance-power |          pkg_j_per_s |    W |       7/7 |     0.031 |        8.312 |     0.051 |               0.6% |
| others-balance-power |               wall_s |    s |       7/7 | 1.543e-04 |        20.00 | 2.517e-04 |               0.0% |
| others-balance-power |               core_j |    J |       7/7 |     0.600 |       152.02 |     0.978 |               0.6% |
| others-balance-power |            rest_frac |    - |       7/7 |     0.007 |        0.086 |     0.011 |              12.5% |
| others-balance-power |     bzy_mhz_big_mean |  MHz |       0/0 |       n/a |          n/a |       n/a |                n/a |
| others-balance-power |  bzy_mhz_little_mean |  MHz |       7/7 |     9.998 |       3463.1 |     16.31 |               0.5% |
| others-performance   | energy_to_solution_j |    J |       7/7 |     0.321 |       166.26 |     0.524 |               0.3% |
| others-performance   |               edp_js |  J*s |       7/7 |     6.424 |       3325.6 |     10.48 |               0.3% |
| others-performance   |          pkg_j_per_s |    W |       7/7 |     0.016 |        8.312 |     0.026 |               0.3% |
| others-performance   |               wall_s |    s |       7/7 | 1.626e-04 |        20.00 | 2.652e-04 |               0.0% |
| others-performance   |               core_j |    J |       7/7 |     0.173 |       152.02 |     0.283 |               0.2% |
| others-performance   |            rest_frac |    - |       7/7 | 7.962e-04 |        0.086 |     0.001 |               1.5% |
| others-performance   |     bzy_mhz_big_mean |  MHz |       0/7 |       n/a |          n/a |       n/a |                n/a |
| others-performance   |  bzy_mhz_little_mean |  MHz |       7/7 |     5.649 |       3463.1 |     9.214 |               0.3% |
| others-power         | energy_to_solution_j |    J |       7/7 |     0.140 |       166.26 |     0.228 |               0.1% |
| others-power         |               edp_js |  J*s |       7/7 |     2.807 |       3325.6 |     4.578 |               0.1% |
| others-power         |          pkg_j_per_s |    W |       7/7 |     0.007 |        8.312 |     0.011 |               0.1% |
| others-power         |               wall_s |    s |       7/7 | 1.648e-04 |        20.00 | 2.687e-04 |               0.0% |
| others-power         |               core_j |    J |       7/7 |     0.097 |       152.02 |     0.158 |               0.1% |
| others-power         |            rest_frac |    - |       7/7 |     0.002 |        0.086 |     0.003 |               3.4% |
| others-power         |     bzy_mhz_big_mean |  MHz |       0/7 |       n/a |          n/a |       n/a |                n/a |
| others-power         |  bzy_mhz_little_mean |  MHz |       7/0 |       n/a |       3463.1 |       n/a |                n/a |

Reading: on `energy_to_solution_j`, the weakest arm comparison (`others-balance-power`) can only detect effects of **0.6% or larger**. To halve that, quadruple the reps.

## Coverage

| field              | present | missing | coverage |
| :----------------- | ------: | ------: | -------: |
| energy.pkg_j       |      28 |       0 |     100% |
| energy.wall_s      |      28 |       0 |     100% |
| energy.rest_j      |      28 |       0 |     100% |
| energy.cpu_bzy_mhz |      28 |       0 |     100% |
| energy.epp         |      28 |       0 |     100% |
| env.start_temp_c   |      28 |       0 |     100% |
| energy.pkg_c_max   |      28 |       0 |     100% |
| pinger             |       0 |      28 |       0% |
| spin               |      28 |       0 |     100% |
| bls                |       0 |      28 |       0% |

---

# Experiment `e2-coupling`

- Runs: **112** across 16 arms (flat.big1 n=7, flat.big1+little1 n=7, flat.big1+little2 n=7, flat.big1+little4 n=7, flat.idle n=7, flat.little1 n=7, flat.little2 n=7, flat.little4 n=7, partitioned.big1 n=7, partitioned.big1+little1 n=7, partitioned.big1+little2 n=7, partitioned.big1+little4 n=7, partitioned.idle n=7, partitioned.little1 n=7, partitioned.little2 n=7, partitioned.little4 n=7)
- Control arm: **`flat.big1`** (first arm alphabetically (no eevdf/flat arm present))

## Verdict

- flat.big1+little1 vs flat.big1: energy-to-solution is HIGHER by 94.71 J (56.4%), 95% CI [93.62, 95.96] excludes zero (Hedges g = 74.33, permutation p = 8.9991e-04).
-    CAUTION: this apparent regression is not admissible while these gates fail: partition is physically real: partitioned.big1, partition is physically real: partitioned.big1+little1, partition is physically real: partitioned.big1+little2, partition is physically real: partitioned.big1+little4, partition is physically real: partitioned.idle, partition is physically real: partitioned.little1, partition is physically real: partitioned.little2, partition is physically real: partitioned.little4, run-order drift.
- flat.big1+little2 vs flat.big1: energy-to-solution is HIGHER by 135.55 J (80.7%), 95% CI [134.17, 137.36] excludes zero (Hedges g = 78.41, permutation p = 8.9991e-04).
-    CAUTION: this apparent regression is not admissible while these gates fail: partition is physically real: partitioned.big1, partition is physically real: partitioned.big1+little1, partition is physically real: partitioned.big1+little2, partition is physically real: partitioned.big1+little4, partition is physically real: partitioned.idle, partition is physically real: partitioned.little1, partition is physically real: partitioned.little2, partition is physically real: partitioned.little4, run-order drift.
- flat.big1+little4 vs flat.big1: energy-to-solution is HIGHER by 173.49 J (103.2%), 95% CI [171.87, 174.94] excludes zero (Hedges g = 103.03, permutation p = 8.9991e-04).
-    CAUTION: this apparent regression is not admissible while these gates fail: partition is physically real: partitioned.big1, partition is physically real: partitioned.big1+little1, partition is physically real: partitioned.big1+little2, partition is physically real: partitioned.big1+little4, partition is physically real: partitioned.idle, partition is physically real: partitioned.little1, partition is physically real: partitioned.little2, partition is physically real: partitioned.little4, run-order drift.
- flat.idle vs flat.big1: energy-to-solution is LOWER by 156.07 J (-92.9%), 95% CI [-157.20, -154.71] excludes zero (Hedges g = -113.99, permutation p = 8.9991e-04).
-    CAUTION: this apparent saving is not admissible while these gates fail: partition is physically real: partitioned.big1, partition is physically real: partitioned.big1+little1, partition is physically real: partitioned.big1+little2, partition is physically real: partitioned.big1+little4, partition is physically real: partitioned.idle, partition is physically real: partitioned.little1, partition is physically real: partitioned.little2, partition is physically real: partitioned.little4, run-order drift.
- flat.little1 vs flat.big1: no detectable difference in energy-to-solution (|effect| < MDE = 3.197 J = 1.9% of the control mean, at 80% power / alpha 0.05 with n=7 vs 7). This design could not have seen a saving smaller than that; it is not evidence that the saving is exactly zero.
- flat.little2 vs flat.big1: energy-to-solution is HIGHER by 94.32 J (56.1%), 95% CI [93.32, 95.45] excludes zero (Hedges g = 81.08, permutation p = 8.9991e-04).
-    CAUTION: this apparent regression is not admissible while these gates fail: partition is physically real: partitioned.big1, partition is physically real: partitioned.big1+little1, partition is physically real: partitioned.big1+little2, partition is physically real: partitioned.big1+little4, partition is physically real: partitioned.idle, partition is physically real: partitioned.little1, partition is physically real: partitioned.little2, partition is physically real: partitioned.little4, run-order drift.
- flat.little4 vs flat.big1: energy-to-solution is HIGHER by 140.59 J (83.7%), 95% CI [139.43, 141.71] excludes zero (Hedges g = 113.39, permutation p = 8.9991e-04).
-    CAUTION: this apparent regression is not admissible while these gates fail: partition is physically real: partitioned.big1, partition is physically real: partitioned.big1+little1, partition is physically real: partitioned.big1+little2, partition is physically real: partitioned.big1+little4, partition is physically real: partitioned.idle, partition is physically real: partitioned.little1, partition is physically real: partitioned.little2, partition is physically real: partitioned.little4, run-order drift.
- partitioned.big1 vs flat.big1: no detectable difference in energy-to-solution (|effect| < MDE = 1.756 J = 1.0% of the control mean, at 80% power / alpha 0.05 with n=7 vs 7). This design could not have seen a saving smaller than that; it is not evidence that the saving is exactly zero.
- partitioned.big1+little1 vs flat.big1: energy-to-solution is HIGHER by 94.51 J (56.2%), 95% CI [93.44, 95.64] excludes zero (Hedges g = 78.33, permutation p = 8.9991e-04).
-    CAUTION: this apparent regression is not admissible while these gates fail: partition is physically real: partitioned.big1, partition is physically real: partitioned.big1+little1, partition is physically real: partitioned.big1+little2, partition is physically real: partitioned.big1+little4, partition is physically real: partitioned.idle, partition is physically real: partitioned.little1, partition is physically real: partitioned.little2, partition is physically real: partitioned.little4, run-order drift.
- partitioned.big1+little2 vs flat.big1: energy-to-solution is HIGHER by 135.68 J (80.7%), 95% CI [133.73, 140.60] excludes zero (Hedges g = 41.66, permutation p = 8.9991e-04).
-    CAUTION: this apparent regression is not admissible while these gates fail: partition is physically real: partitioned.big1, partition is physically real: partitioned.big1+little1, partition is physically real: partitioned.big1+little2, partition is physically real: partitioned.big1+little4, partition is physically real: partitioned.idle, partition is physically real: partitioned.little1, partition is physically real: partitioned.little2, partition is physically real: partitioned.little4, run-order drift.
- partitioned.big1+little4 vs flat.big1: energy-to-solution is HIGHER by 173.94 J (103.5%), 95% CI [172.69, 175.56] excludes zero (Hedges g = 112.70, permutation p = 8.9991e-04).
-    CAUTION: this apparent regression is not admissible while these gates fail: partition is physically real: partitioned.big1, partition is physically real: partitioned.big1+little1, partition is physically real: partitioned.big1+little2, partition is physically real: partitioned.big1+little4, partition is physically real: partitioned.idle, partition is physically real: partitioned.little1, partition is physically real: partitioned.little2, partition is physically real: partitioned.little4, run-order drift.
- partitioned.idle vs flat.big1: energy-to-solution is LOWER by 150.78 J (-89.7%), 95% CI [-152.13, -149.08] excludes zero (Hedges g = -91.04, permutation p = 8.9991e-04).
-    CAUTION: this apparent saving is not admissible while these gates fail: partition is physically real: partitioned.big1, partition is physically real: partitioned.big1+little1, partition is physically real: partitioned.big1+little2, partition is physically real: partitioned.big1+little4, partition is physically real: partitioned.idle, partition is physically real: partitioned.little1, partition is physically real: partitioned.little2, partition is physically real: partitioned.little4, run-order drift.
- partitioned.little1 vs flat.big1: energy-to-solution is LOWER by 1.213 J (-0.7%), 95% CI [-2.242, -0.035] excludes zero (Hedges g = -1.005, permutation p = 0.0690).
-    CAUTION: this apparent saving is not admissible while these gates fail: partition is physically real: partitioned.big1, partition is physically real: partitioned.big1+little1, partition is physically real: partitioned.big1+little2, partition is physically real: partitioned.big1+little4, partition is physically real: partitioned.idle, partition is physically real: partitioned.little1, partition is physically real: partitioned.little2, partition is physically real: partitioned.little4, run-order drift.
- partitioned.little2 vs flat.big1: energy-to-solution is HIGHER by 93.91 J (55.9%), 95% CI [92.94, 94.88] excludes zero (Hedges g = 87.77, permutation p = 8.9991e-04).
-    CAUTION: this apparent regression is not admissible while these gates fail: partition is physically real: partitioned.big1, partition is physically real: partitioned.big1+little1, partition is physically real: partitioned.big1+little2, partition is physically real: partitioned.big1+little4, partition is physically real: partitioned.idle, partition is physically real: partitioned.little1, partition is physically real: partitioned.little2, partition is physically real: partitioned.little4, run-order drift.
- partitioned.little4 vs flat.big1: energy-to-solution is HIGHER by 140.21 J (83.4%), 95% CI [139.02, 141.34] excludes zero (Hedges g = 109.96, permutation p = 8.9991e-04).
-    CAUTION: this apparent regression is not admissible while these gates fail: partition is physically real: partitioned.big1, partition is physically real: partitioned.big1+little1, partition is physically real: partitioned.big1+little2, partition is physically real: partitioned.big1+little4, partition is physically real: partitioned.idle, partition is physically real: partitioned.little1, partition is physically real: partitioned.little2, partition is physically real: partitioned.little4, run-order drift.
- The partition is NOT physically real in any arm: LITTLE-domain frequency is within 10% of big-domain frequency. Everything downstream is moot -- the energy comparison is a comparison of the machine against itself.
- Failing gates: partition is physically real: partitioned.big1, partition is physically real: partitioned.big1+little1, partition is physically real: partitioned.big1+little2, partition is physically real: partitioned.big1+little4, partition is physically real: partitioned.idle, partition is physically real: partitioned.little1, partition is physically real: partitioned.little2, partition is physically real: partitioned.little4, run-order drift.

## Data quality

| status | gate                                                   | numbers                                                                                                                                                                                                                                                                                                                                                                              |
| :----- | :----------------------------------------------------- | :----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| PASS   | run completion                                         | 112/112 runs have ok=true and exit_code=0                                                                                                                                                                                                                                                                                                                                            |
| PASS   | start temperature spread                               | max-min of per-arm mean start_temp_c = 2.29 C (limit 5.0); hottest flat.big1+little4 49.9 C, coldest flat.little1 47.6 C                                                                                                                                                                                                                                                             |
| PASS   | on_ac consistent                                       | all 112 runs on_ac=True                                                                                                                                                                                                                                                                                                                                                              |
| PASS   | thermal headroom                                       | max pkg_c_max = 80.0 C in arm flat.little4 (limit 97.0 C = Tjmax-3); 0/112 runs at or above the limit                                                                                                                                                                                                                                                                                |
| PASS   | balanced reps per arm                                  | flat.big1=7, flat.big1+little1=7, flat.big1+little2=7, flat.big1+little4=7, flat.idle=7, flat.little1=7, flat.little2=7, flat.little4=7, partitioned.big1=7, partitioned.big1+little1=7, partitioned.big1+little2=7, partitioned.big1+little4=7, partitioned.idle=7, partitioned.little1=7, partitioned.little2=7, partitioned.little4=7                                             |
| FAIL   | run-order drift                                        | 24 arm/metric pairs with \|Spearman rho vs rep\| > 0.6: flat.big1/energy_to_solution_j rho=-0.64; flat.big1/edp_js rho=-0.64; flat.big1/pkg_j_per_s rho=-0.64; flat.big1/wall_s rho=+0.65; flat.big1/core_j rho=-0.86; flat.big1+little1/energy_to_solution_j rho=-0.68  [n=7 per arm: rho is noisy at this size, treat as a prompt to inspect the run order, not as proof of drift] |
| FAIL   | partition is physically real: partitioned.big1         | little/big bzy MHz = 0.968 (3431.8 MHz / 3544.1 MHz over 7 runs); a real split needs < 0.90  -- EPP did not separate the frequency domains, so no downstream energy difference can be attributed to partitioning.                                                                                                                                                                    |
| FAIL   | partition is physically real: partitioned.big1+little1 | little/big bzy MHz = 1.001 (3430.2 MHz / 3427.4 MHz over 7 runs); a real split needs < 0.90  -- EPP did not separate the frequency domains, so no downstream energy difference can be attributed to partitioning.                                                                                                                                                                    |
| FAIL   | partition is physically real: partitioned.big1+little2 | little/big bzy MHz = 1.000 (3331.8 MHz / 3331.8 MHz over 7 runs); a real split needs < 0.90  -- EPP did not separate the frequency domains, so no downstream energy difference can be attributed to partitioning.                                                                                                                                                                    |
| FAIL   | partition is physically real: partitioned.big1+little4 | little/big bzy MHz = 1.000 (3330.0 MHz / 3329.6 MHz over 7 runs); a real split needs < 0.90  -- EPP did not separate the frequency domains, so no downstream energy difference can be attributed to partitioning.                                                                                                                                                                    |
| FAIL   | partition is physically real: partitioned.idle         | little/big bzy MHz = 0.999 (3435.8 MHz / 3440.8 MHz over 7 runs); a real split needs < 0.90  -- EPP did not separate the frequency domains, so no downstream energy difference can be attributed to partitioning.                                                                                                                                                                    |
| FAIL   | partition is physically real: partitioned.little1      | little/big bzy MHz = 1.000 (3482.3 MHz / 3481.8 MHz over 7 runs); a real split needs < 0.90  -- EPP did not separate the frequency domains, so no downstream energy difference can be attributed to partitioning.                                                                                                                                                                    |
| FAIL   | partition is physically real: partitioned.little2      | little/big bzy MHz = 1.052 (3505.2 MHz / 3330.6 MHz over 7 runs); a real split needs < 0.90  -- EPP did not separate the frequency domains, so no downstream energy difference can be attributed to partitioning.                                                                                                                                                                    |
| FAIL   | partition is physically real: partitioned.little4      | little/big bzy MHz = 1.076 (3583.2 MHz / 3330.6 MHz over 7 runs); a real split needs < 0.90  -- EPP did not separate the frequency domains, so no downstream energy difference can be attributed to partitioning.                                                                                                                                                                    |

**9 gate(s) FAILED.** A failed gate means the arms are not comparable; effect sizes below are reported for completeness but must not be quoted as results until the gate is fixed.

## Placement sanity

A partitioning experiment where the tasks did not stay partitioned proves nothing, so this comes before the effect sizes.

| arm                      | runs w/ bls | strict | enqueues (mean) | cross-domain / enqueue | run time in big | run time in LITTLE | dispatch to big |
| :----------------------- | ----------: | -----: | --------------: | ---------------------: | --------------: | -----------------: | --------------: |
| flat.big1                |         0/7 |    n/a |             n/a |                    n/a |             n/a |                n/a |             n/a |
| flat.big1+little1        |         0/7 |    n/a |             n/a |                    n/a |             n/a |                n/a |             n/a |
| flat.big1+little2        |         0/7 |    n/a |             n/a |                    n/a |             n/a |                n/a |             n/a |
| flat.big1+little4        |         0/7 |    n/a |             n/a |                    n/a |             n/a |                n/a |             n/a |
| flat.idle                |         0/7 |    n/a |             n/a |                    n/a |             n/a |                n/a |             n/a |
| flat.little1             |         0/7 |    n/a |             n/a |                    n/a |             n/a |                n/a |             n/a |
| flat.little2             |         0/7 |    n/a |             n/a |                    n/a |             n/a |                n/a |             n/a |
| flat.little4             |         0/7 |    n/a |             n/a |                    n/a |             n/a |                n/a |             n/a |
| partitioned.big1         |         0/7 |    n/a |             n/a |                    n/a |             n/a |                n/a |             n/a |
| partitioned.big1+little1 |         0/7 |    n/a |             n/a |                    n/a |             n/a |                n/a |             n/a |
| partitioned.big1+little2 |         0/7 |    n/a |             n/a |                    n/a |             n/a |                n/a |             n/a |
| partitioned.big1+little4 |         0/7 |    n/a |             n/a |                    n/a |             n/a |                n/a |             n/a |
| partitioned.idle         |         0/7 |    n/a |             n/a |                    n/a |             n/a |                n/a |             n/a |
| partitioned.little1      |         0/7 |    n/a |             n/a |                    n/a |             n/a |                n/a |             n/a |
| partitioned.little2      |         0/7 |    n/a |             n/a |                    n/a |             n/a |                n/a |             n/a |
| partitioned.little4      |         0/7 |    n/a |             n/a |                    n/a |             n/a |                n/a |             n/a |

- **SKIP** -- placement: no arm reported bls scheduler counters

## Per-arm summary

Mean with a 95% bootstrap CI (10000 resamples). `n` is the number of runs that actually carried the metric.

### `energy_to_solution_j` (J) -- package energy to complete the workload

| arm                      |   n | missing |   mean | median |    sd |   95% CI of mean | CI method |
| :----------------------- | --: | ------: | -----: | -----: | ----: | ---------------: | --------: |
| flat.big1  [control]     |   7 |       0 | 168.05 | 167.98 | 1.257 | [167.22, 168.91] |       BCa |
| flat.big1+little1        |   7 |       0 | 262.76 | 262.15 | 1.124 | [262.15, 263.80] |       BCa |
| flat.big1+little2        |   7 |       0 | 303.60 | 303.40 | 1.912 | [302.57, 305.27] |       BCa |
| flat.big1+little4        |   7 |       0 | 341.54 | 341.72 | 1.841 | [340.15, 342.66] |       BCa |
| flat.idle                |   7 |       0 |  11.98 |  11.27 | 1.306 |   [11.21, 13.13] |       BCa |
| flat.little1             |   7 |       0 | 167.29 | 166.34 | 2.470 | [166.27, 170.15] |       BCa |
| flat.little2             |   7 |       0 | 262.37 | 262.23 | 0.889 | [261.97, 263.37] |       BCa |
| flat.little4             |   7 |       0 | 308.64 | 308.68 | 1.055 | [307.90, 309.35] |       BCa |
| partitioned.big1         |   7 |       0 | 168.03 | 167.81 | 0.858 | [167.54, 168.74] |       BCa |
| partitioned.big1+little1 |   7 |       0 | 262.56 | 262.48 | 0.985 | [261.98, 263.38] |       BCa |
| partitioned.big1+little2 |   7 |       0 | 303.73 | 302.47 | 4.125 | [302.00, 308.53] |       BCa |
| partitioned.big1+little4 |   7 |       0 | 341.99 | 341.78 | 1.611 | [341.13, 343.41] |       BCa |
| partitioned.idle         |   7 |       0 |  17.27 |  16.65 | 1.796 |   [16.25, 18.84] |       BCa |
| partitioned.little1      |   7 |       0 | 166.84 | 166.64 | 0.987 | [166.35, 167.90] |       BCa |
| partitioned.little2      |   7 |       0 | 261.96 | 261.71 | 0.652 | [261.64, 262.65] |       BCa |
| partitioned.little4      |   7 |       0 | 308.26 | 308.25 | 1.126 | [307.43, 309.00] |       BCa |

### `edp_js` (J*s) -- energy-delay product (pkg_j * wall_s)

| arm                      |   n | missing |   mean | median |    sd |   95% CI of mean | CI method |
| :----------------------- | --: | ------: | -----: | -----: | ----: | ---------------: | --------: |
| flat.big1  [control]     |   7 |       0 | 3361.4 | 3360.0 | 25.15 | [3344.9, 3378.6] |       BCa |
| flat.big1+little1        |   7 |       0 | 5255.9 | 5243.6 | 22.51 | [5243.8, 5276.7] |       BCa |
| flat.big1+little2        |   7 |       0 | 6072.8 | 6068.9 | 38.25 | [6052.1, 6106.3] |       BCa |
| flat.big1+little4        |   7 |       0 | 6831.8 | 6835.5 | 36.84 | [6803.9, 6854.3] |       BCa |
| flat.idle                |   7 |       0 | 240.82 | 226.06 | 27.05 | [224.99, 264.63] |       BCa |
| flat.little1             |   7 |       0 | 3346.3 | 3327.2 | 49.42 | [3325.8, 3403.5] |       BCa |
| flat.little2             |   7 |       0 | 5248.1 | 5245.5 | 17.78 | [5240.1, 5268.1] |       BCa |
| flat.little4             |   7 |       0 | 6173.6 | 6174.5 | 21.19 | [6158.8, 6187.8] |       BCa |
| partitioned.big1         |   7 |       0 | 3360.9 | 3356.5 | 17.18 | [3351.1, 3375.1] |       BCa |
| partitioned.big1+little1 |   7 |       0 | 5251.5 | 5250.0 | 19.73 | [5240.0, 5267.9] |       BCa |
| partitioned.big1+little2 |   7 |       0 | 6075.1 | 6049.9 | 82.48 | [6040.4, 6171.0] |       BCa |
| partitioned.big1+little4 |   7 |       0 | 6840.4 | 6836.0 | 32.14 | [6823.3, 6868.7] |       BCa |
| partitioned.idle         |   7 |       0 | 346.77 | 333.63 | 37.30 | [325.61, 379.88] |       BCa |
| partitioned.little1      |   7 |       0 | 3336.9 | 3333.0 | 19.76 | [3327.3, 3358.1] |       BCa |
| partitioned.little2      |   7 |       0 | 5239.5 | 5234.6 | 13.04 | [5233.2, 5253.4] |       BCa |
| partitioned.little4      |   7 |       0 | 6165.6 | 6165.4 | 22.51 | [6149.1, 6180.5] |       BCa |

### `pkg_j_per_s` (W) -- mean package power

| arm                      |   n | missing |  mean | median |    sd | 95% CI of mean | CI method |
| :----------------------- | --: | ------: | ----: | -----: | ----: | -------------: | --------: |
| flat.big1  [control]     |   7 |       0 | 8.401 |  8.398 | 0.063 | [8.360, 8.444] |       BCa |
| flat.big1+little1        |   7 |       0 | 13.14 |  13.11 | 0.056 | [13.11, 13.19] |       BCa |
| flat.big1+little2        |   7 |       0 | 15.18 |  15.17 | 0.096 | [15.13, 15.26] |       BCa |
| flat.big1+little4        |   7 |       0 | 17.07 |  17.08 | 0.092 | [17.00, 17.13] |       BCa |
| flat.idle                |   7 |       0 | 0.596 |  0.562 | 0.063 | [0.559, 0.651] |       BCa |
| flat.little1             |   7 |       0 | 8.363 |  8.316 | 0.123 | [8.312, 8.506] |       BCa |
| flat.little2             |   7 |       0 | 13.12 |  13.11 | 0.044 | [13.10, 13.17] |       BCa |
| flat.little4             |   7 |       0 | 15.43 |  15.43 | 0.053 | [15.39, 15.47] |       BCa |
| partitioned.big1         |   7 |       0 | 8.401 |  8.390 | 0.043 | [8.377, 8.437] |       BCa |
| partitioned.big1+little1 |   7 |       0 | 13.13 |  13.12 | 0.049 | [13.10, 13.17] |       BCa |
| partitioned.big1+little2 |   7 |       0 | 15.19 |  15.12 | 0.206 | [15.10, 15.43] |       BCa |
| partitioned.big1+little4 |   7 |       0 | 17.10 |  17.09 | 0.081 | [17.06, 17.17] |       BCa |
| partitioned.idle         |   7 |       0 | 0.860 |  0.831 | 0.086 | [0.811, 0.936] |       BCa |
| partitioned.little1      |   7 |       0 | 8.341 |  8.331 | 0.049 | [8.317, 8.394] |       BCa |
| partitioned.little2      |   7 |       0 | 13.10 |  13.08 | 0.033 | [13.08, 13.13] |       BCa |
| partitioned.little4      |   7 |       0 | 15.41 |  15.41 | 0.056 | [15.37, 15.45] |       BCa |

### `wall_s` (s) -- time to solution

| arm                      |   n | missing |  mean | median |        sd | 95% CI of mean | CI method |
| :----------------------- | --: | ------: | ----: | -----: | --------: | -------------: | --------: |
| flat.big1  [control]     |   7 |       0 | 20.00 |  20.00 | 6.630e-04 | [20.00, 20.00] |       BCa |
| flat.big1+little1        |   7 |       0 | 20.00 |  20.00 | 1.345e-04 | [20.00, 20.00] |       BCa |
| flat.big1+little2        |   7 |       0 | 20.00 |  20.00 | 1.604e-04 | [20.00, 20.00] |       BCa |
| flat.big1+little4        |   7 |       0 | 20.00 |  20.00 | 5.460e-04 | [20.00, 20.00] |       BCa |
| flat.idle                |   7 |       0 | 20.10 |  20.07 |     0.063 | [20.06, 20.16] |       BCa |
| flat.little1             |   7 |       0 | 20.00 |  20.00 | 2.236e-04 | [20.00, 20.00] |       BCa |
| flat.little2             |   7 |       0 | 20.00 |  20.00 | 1.618e-04 | [20.00, 20.00] |       BCa |
| flat.little4             |   7 |       0 | 20.00 |  20.00 | 4.786e-04 | [20.00, 20.00] |       BCa |
| partitioned.big1         |   7 |       0 | 20.00 |  20.00 | 1.272e-04 | [20.00, 20.00] |       BCa |
| partitioned.big1+little1 |   7 |       0 | 20.00 |  20.00 | 1.826e-04 | [20.00, 20.00] |       BCa |
| partitioned.big1+little2 |   7 |       0 | 20.00 |  20.00 | 1.113e-04 | [20.00, 20.00] |       BCa |
| partitioned.big1+little4 |   7 |       0 | 20.00 |  20.00 | 5.648e-04 | [20.00, 20.00] |       BCa |
| partitioned.idle         |   7 |       0 | 20.08 |  20.04 |     0.073 | [20.04, 20.14] |       BCa |
| partitioned.little1      |   7 |       0 | 20.00 |  20.00 | 1.604e-04 | [20.00, 20.00] |       BCa |
| partitioned.little2      |   7 |       0 | 20.00 |  20.00 | 1.113e-04 | [20.00, 20.00] |       BCa |
| partitioned.little4      |   7 |       0 | 20.00 |  20.00 | 1.272e-04 | [20.00, 20.00] |       BCa |

### `core_j` (J) -- core-domain energy (the part EPP can touch)

| arm                      |   n | missing |   mean | median |    sd |   95% CI of mean | CI method |
| :----------------------- | --: | ------: | -----: | -----: | ----: | ---------------: | --------: |
| flat.big1  [control]     |   7 |       0 | 153.38 | 153.43 | 0.901 | [152.82, 154.07] |       BCa |
| flat.big1+little1        |   7 |       0 | 247.71 | 247.61 | 0.626 | [247.32, 248.18] |       BCa |
| flat.big1+little2        |   7 |       0 | 288.50 | 287.89 | 1.984 | [287.58, 290.66] |       BCa |
| flat.big1+little4        |   7 |       0 | 326.44 | 327.01 | 1.252 | [325.25, 327.11] |       BCa |
| flat.idle                |   7 |       0 |  1.727 |  1.831 | 0.310 |   [1.481, 1.911] |       BCa |
| flat.little1             |   7 |       0 | 152.37 | 152.18 | 1.457 | [151.66, 153.92] |       BCa |
| flat.little2             |   7 |       0 | 247.43 | 247.50 | 0.636 | [246.81, 247.75] |       BCa |
| flat.little4             |   7 |       0 | 293.46 | 293.68 | 0.776 | [292.99, 294.05] |       BCa |
| partitioned.big1         |   7 |       0 | 153.29 | 153.38 | 1.333 | [152.25, 154.10] |       BCa |
| partitioned.big1+little1 |   7 |       0 | 248.06 | 247.99 | 0.818 | [247.58, 248.74] |       BCa |
| partitioned.big1+little2 |   7 |       0 | 289.09 | 287.30 | 4.226 | [287.31, 294.01] |       BCa |
| partitioned.big1+little4 |   7 |       0 | 327.10 | 326.16 | 1.733 | [326.14, 328.56] |       BCa |
| partitioned.idle         |   7 |       0 |  7.224 |  7.211 | 0.360 |   [7.009, 7.525] |       BCa |
| partitioned.little1      |   7 |       0 | 152.30 | 152.32 | 0.219 | [152.10, 152.42] |       BCa |
| partitioned.little2      |   7 |       0 | 247.46 | 247.33 | 0.642 | [247.15, 248.14] |       BCa |
| partitioned.little4      |   7 |       0 | 293.61 | 293.68 | 1.033 | [292.84, 294.26] |       BCa |

### `rest_frac` (-) -- share of pkg energy EPP cannot touch

| arm                      |   n | missing |  mean | median |        sd | 95% CI of mean | CI method |
| :----------------------- | --: | ------: | ----: | -----: | --------: | -------------: | --------: |
| flat.big1  [control]     |   7 |       0 | 0.087 |  0.086 |     0.004 | [0.086, 0.091] |       BCa |
| flat.big1+little1        |   7 |       0 | 0.057 |  0.056 |     0.003 | [0.055, 0.060] |       BCa |
| flat.big1+little2        |   7 |       0 | 0.050 |  0.049 |     0.003 | [0.048, 0.052] |       BCa |
| flat.big1+little4        |   7 |       0 | 0.044 |  0.043 |     0.002 | [0.043, 0.046] |       BCa |
| flat.idle                |   7 |       0 | 0.852 |  0.835 |     0.038 | [0.831, 0.884] |       BCa |
| flat.little1             |   7 |       0 | 0.089 |  0.086 |     0.006 | [0.085, 0.094] |       BCa |
| flat.little2             |   7 |       0 | 0.057 |  0.055 |     0.003 | [0.055, 0.060] |       BCa |
| flat.little4             |   7 |       0 | 0.049 |  0.048 |     0.003 | [0.048, 0.051] |       BCa |
| partitioned.big1         |   7 |       0 | 0.088 |  0.086 |     0.005 | [0.086, 0.093] |       BCa |
| partitioned.big1+little1 |   7 |       0 | 0.055 |  0.055 | 4.386e-04 | [0.055, 0.056] |       BCa |
| partitioned.big1+little2 |   7 |       0 | 0.048 |  0.048 |     0.001 | [0.047, 0.049] |       BCa |
| partitioned.big1+little4 |   7 |       0 | 0.044 |  0.043 |     0.002 | [0.043, 0.046] |       BCa |
| partitioned.idle         |   7 |       0 | 0.578 |  0.570 |     0.022 | [0.567, 0.601] |       BCa |
| partitioned.little1      |   7 |       0 | 0.087 |  0.086 |     0.004 | [0.085, 0.092] |       BCa |
| partitioned.little2      |   7 |       0 | 0.055 |  0.055 | 6.082e-04 | [0.055, 0.056] |       BCa |
| partitioned.little4      |   7 |       0 | 0.048 |  0.047 | 8.869e-04 | [0.047, 0.048] |       BCa |

### `bzy_mhz_big_mean` (MHz) -- mean busy MHz of the big domain

| arm                      |   n | missing |   mean | median |    sd |   95% CI of mean | CI method |
| :----------------------- | --: | ------: | -----: | -----: | ----: | ---------------: | --------: |
| flat.big1  [control]     |   7 |       0 | 3473.6 | 3474.1 | 11.89 | [3466.2, 3482.6] |       BCa |
| flat.big1+little1        |   7 |       0 | 3414.9 | 3414.6 | 5.685 | [3411.4, 3419.3] |       BCa |
| flat.big1+little2        |   7 |       0 | 3323.5 | 3323.8 | 3.124 | [3321.6, 3325.9] |       BCa |
| flat.big1+little4        |   7 |       0 | 3325.2 | 3324.9 | 2.654 | [3323.1, 3326.8] |       BCa |
| flat.idle                |   7 |       0 | 918.48 | 936.95 | 55.55 | [872.13, 950.33] |       BCa |
| flat.little1             |   7 |       0 | 3464.8 | 3463.1 | 7.843 | [3459.6, 3470.3] |       BCa |
| flat.little2             |   7 |       0 | 3409.3 | 3409.0 | 6.817 | [3405.6, 3415.4] |       BCa |
| flat.little4             |   7 |       0 | 3451.0 | 3450.2 | 3.994 | [3448.3, 3453.7] |       BCa |
| partitioned.big1         |   7 |       0 | 3544.1 | 3544.9 | 12.83 | [3535.8, 3553.2] |       BCa |
| partitioned.big1+little1 |   7 |       0 | 3427.4 | 3430.8 | 13.99 | [3412.2, 3434.0] |       BCa |
| partitioned.big1+little2 |   7 |       0 | 3331.8 | 3331.4 | 3.802 | [3329.4, 3334.7] |       BCa |
| partitioned.big1+little4 |   7 |       0 | 3329.6 | 3330.7 | 1.941 | [3328.0, 3330.7] |       BCa |
| partitioned.idle         |   7 |       0 | 3440.8 | 3441.2 | 22.94 | [3425.8, 3457.1] |       BCa |
| partitioned.little1      |   7 |       0 | 3481.8 | 3478.7 | 8.338 | [3477.3, 3489.4] |       BCa |
| partitioned.little2      |   7 |       0 | 3330.6 | 3331.2 | 2.542 | [3329.1, 3332.5] |       BCa |
| partitioned.little4      |   7 |       0 | 3330.6 | 3331.3 | 2.364 | [3328.6, 3331.9] |       BCa |

### `bzy_mhz_little_mean` (MHz) -- mean busy MHz of the LITTLE domain

| arm                      |   n | missing |   mean | median |    sd |   95% CI of mean |  CI method |
| :----------------------- | --: | ------: | -----: | -----: | ----: | ---------------: | ---------: |
| flat.big1  [control]     |   0 |       7 |    n/a |    n/a |   n/a |       [n/a, n/a] |        n/a |
| flat.big1+little1        |   0 |       7 |    n/a |    n/a |   n/a |       [n/a, n/a] |        n/a |
| flat.big1+little2        |   0 |       7 |    n/a |    n/a |   n/a |       [n/a, n/a] |        n/a |
| flat.big1+little4        |   0 |       7 |    n/a |    n/a |   n/a |       [n/a, n/a] |        n/a |
| flat.idle                |   0 |       7 |    n/a |    n/a |   n/a |       [n/a, n/a] |        n/a |
| flat.little1             |   0 |       7 |    n/a |    n/a |   n/a |       [n/a, n/a] |        n/a |
| flat.little2             |   0 |       7 |    n/a |    n/a |   n/a |       [n/a, n/a] |        n/a |
| flat.little4             |   0 |       7 |    n/a |    n/a |   n/a |       [n/a, n/a] |        n/a |
| partitioned.big1         |   7 |       0 | 3431.8 | 3438.9 | 22.50 | [3414.7, 3446.1] |        BCa |
| partitioned.big1+little1 |   7 |       0 | 3430.2 | 3429.4 | 2.654 | [3428.5, 3432.2] |        BCa |
| partitioned.big1+little2 |   7 |       0 | 3331.8 | 3331.7 | 1.211 | [3330.9, 3332.6] |        BCa |
| partitioned.big1+little4 |   7 |       0 | 3330.0 | 3330.0 | 0.000 | [3330.0, 3330.0] | percentile |
| partitioned.idle         |   7 |       0 | 3435.8 | 3437.6 | 15.17 | [3425.2, 3446.2] |        BCa |
| partitioned.little1      |   7 |       0 | 3482.3 | 3477.6 | 13.58 | [3475.2, 3495.3] |        BCa |
| partitioned.little2      |   7 |       0 | 3505.2 | 3501.8 | 9.308 | [3499.3, 3512.0] |        BCa |
| partitioned.little4      |   7 |       0 | 3583.2 | 3582.8 | 1.539 | [3582.4, 3584.6] |        BCa |

## Contrasts vs control (`flat.big1`)

Difference in means (arm - control). A contrast whose CI straddles zero is reported as *no detectable difference*, never as a signed saving.

### `flat.big1+little1` vs `flat.big1`

| metric               | n ctl/arm | control mean | arm mean |      diff |     95% CI of diff | % change | Hedges g |   p (perm) | MDE (abs) | MDE (%) |             result |
| :------------------- | --------: | -----------: | -------: | --------: | -----------------: | -------: | -------: | ---------: | --------: | ------: | -----------------: |
| energy_to_solution_j |       7/7 |       168.05 |   262.76 |     94.71 |     [93.62, 95.96] |   +56.4% |    74.33 | 8.9991e-04 |     1.946 |    1.2% |     higher (worse) |
| edp_js               |       7/7 |       3361.4 |   5255.9 |    1894.5 |   [1872.8, 1919.5] |   +56.4% |    74.30 | 8.9991e-04 |     38.93 |    1.2% |     higher (worse) |
| pkg_j_per_s          |       7/7 |        8.401 |    13.14 |     4.735 |     [4.680, 4.797] |   +56.4% |    74.36 | 8.9991e-04 |     0.097 |    1.2% |     higher (worse) |
| wall_s               |       7/7 |        20.00 |    20.00 | 3.571e-04 | [5.714e-05, 0.001] |    +0.0% |    0.699 |     0.1502 | 7.802e-04 |    0.0% |     higher (worse) |
| core_j               |       7/7 |       153.38 |   247.71 |     94.32 |     [93.54, 95.05] |   +61.5% |   113.83 | 8.9991e-04 |     1.265 |    0.8% |     higher (worse) |
| rest_frac            |       7/7 |        0.087 |    0.057 |    -0.030 |   [-0.034, -0.027] |   -34.4% |   -8.450 | 8.9991e-04 |     0.005 |    6.2% | lower (diagnostic) |
| bzy_mhz_big_mean     |       7/7 |       3473.6 |   3414.9 |    -58.68 |   [-68.39, -50.22] |    -1.7% |   -5.895 | 8.9991e-04 |     15.20 |    0.4% | lower (diagnostic) |
| bzy_mhz_little_mean  |       0/0 |          n/a |      n/a |       n/a |         [n/a, n/a] |      n/a |      n/a |        n/a |       n/a |     n/a |  insufficient data |

- energy_to_solution_j: higher than control by 94.71 J (+56.4%), 95% CI [93.62, 95.96] excludes zero; Hedges g = 74.33, permutation p = 8.9991e-04; MDE = 1.946 J.
- edp_js: higher than control by 1894.5 J*s (+56.4%), 95% CI [1872.8, 1919.5] excludes zero; Hedges g = 74.30, permutation p = 8.9991e-04; MDE = 38.93 J*s.
- pkg_j_per_s: higher than control by 4.735 W (+56.4%), 95% CI [4.680, 4.797] excludes zero; Hedges g = 74.36, permutation p = 8.9991e-04; MDE = 0.097 W.
- wall_s: higher than control by 3.571e-04 s (+0.0%), 95% CI [5.714e-05, 0.001] excludes zero; Hedges g = 0.699, permutation p = 0.1502; MDE = 7.802e-04 s.
- core_j: higher than control by 94.32 J (+61.5%), 95% CI [93.54, 95.05] excludes zero; Hedges g = 113.83, permutation p = 8.9991e-04; MDE = 1.265 J.
- rest_frac: lower than control by 0.030 - (-34.4%), 95% CI [-0.034, -0.027] excludes zero; Hedges g = -8.450, permutation p = 8.9991e-04; MDE = 0.005 -.
- bzy_mhz_big_mean: lower than control by 58.68 MHz (-1.7%), 95% CI [-68.39, -50.22] excludes zero; Hedges g = -5.895, permutation p = 8.9991e-04; MDE = 15.20 MHz.
- bzy_mhz_little_mean: insufficient data (n_control=0, n_arm=0); no contrast computed.

### `flat.big1+little2` vs `flat.big1`

| metric               | n ctl/arm | control mean | arm mean |      diff |          95% CI of diff | % change | Hedges g |   p (perm) | MDE (abs) | MDE (%) |                   result |
| :------------------- | --------: | -----------: | -------: | --------: | ----------------------: | -------: | -------: | ---------: | --------: | ------: | -----------------------: |
| energy_to_solution_j |       7/7 |       168.05 |   303.60 |    135.55 |        [134.17, 137.36] |   +80.7% |    78.41 | 8.9991e-04 |     2.640 |    1.6% |           higher (worse) |
| edp_js               |       7/7 |       3361.4 |   6072.8 |    2711.4 |        [2683.8, 2747.6] |   +80.7% |    78.41 | 8.9991e-04 |     52.80 |    1.6% |           higher (worse) |
| pkg_j_per_s          |       7/7 |        8.401 |    15.18 |     6.776 |          [6.707, 6.867] |   +80.7% |    78.41 | 8.9991e-04 |     0.132 |    1.6% |           higher (worse) |
| wall_s               |       7/7 |        20.00 |    20.00 | 1.714e-04 | [-1.286e-04, 9.682e-04] |    +0.0% |    0.333 |     0.8189 | 7.867e-04 |    0.0% | no detectable difference |
| core_j               |       7/7 |       153.38 |   288.50 |    135.12 |        [134.02, 137.23] |   +88.1% |    82.11 | 8.9991e-04 |     2.513 |    1.6% |           higher (worse) |
| rest_frac            |       7/7 |        0.087 |    0.050 |    -0.037 |        [-0.041, -0.035] |   -43.0% |   -11.13 | 8.9991e-04 |     0.005 |    5.9% |       lower (diagnostic) |
| bzy_mhz_big_mean     |       7/7 |       3473.6 |   3323.5 |   -150.03 |      [-159.33, -142.33] |    -4.3% |   -16.16 | 8.9991e-04 |     14.18 |    0.4% |       lower (diagnostic) |
| bzy_mhz_little_mean  |       0/0 |          n/a |      n/a |       n/a |              [n/a, n/a] |      n/a |      n/a |        n/a |       n/a |     n/a |        insufficient data |

- energy_to_solution_j: higher than control by 135.55 J (+80.7%), 95% CI [134.17, 137.36] excludes zero; Hedges g = 78.41, permutation p = 8.9991e-04; MDE = 2.640 J.
- edp_js: higher than control by 2711.4 J*s (+80.7%), 95% CI [2683.8, 2747.6] excludes zero; Hedges g = 78.41, permutation p = 8.9991e-04; MDE = 52.80 J*s.
- pkg_j_per_s: higher than control by 6.776 W (+80.7%), 95% CI [6.707, 6.867] excludes zero; Hedges g = 78.41, permutation p = 8.9991e-04; MDE = 0.132 W.
- wall_s: no detectable difference (|effect| < MDE = 7.867e-04 s = 0.0% of control).
- core_j: higher than control by 135.12 J (+88.1%), 95% CI [134.02, 137.23] excludes zero; Hedges g = 82.11, permutation p = 8.9991e-04; MDE = 2.513 J.
- rest_frac: lower than control by 0.037 - (-43.0%), 95% CI [-0.041, -0.035] excludes zero; Hedges g = -11.13, permutation p = 8.9991e-04; MDE = 0.005 -.
- bzy_mhz_big_mean: lower than control by 150.03 MHz (-4.3%), 95% CI [-159.33, -142.33] excludes zero; Hedges g = -16.16, permutation p = 8.9991e-04; MDE = 14.18 MHz.
- bzy_mhz_little_mean: insufficient data (n_control=0, n_arm=0); no contrast computed.

### `flat.big1+little4` vs `flat.big1`

| metric               | n ctl/arm | control mean | arm mean |      diff |     95% CI of diff | % change | Hedges g |   p (perm) | MDE (abs) | MDE (%) |             result |
| :------------------- | --------: | -----------: | -------: | --------: | -----------------: | -------: | -------: | ---------: | --------: | ------: | -----------------: |
| energy_to_solution_j |       7/7 |       168.05 |   341.54 |    173.49 |   [171.87, 174.94] |  +103.2% |   103.03 | 8.9991e-04 |     2.571 |    1.5% |     higher (worse) |
| edp_js               |       7/7 |       3361.4 |   6831.8 |    3470.4 |   [3437.8, 3499.3] |  +103.2% |   103.01 | 8.9991e-04 |     51.44 |    1.5% |     higher (worse) |
| pkg_j_per_s          |       7/7 |        8.401 |    17.07 |     8.673 |     [8.592, 8.745] |  +103.2% |   103.05 | 8.9991e-04 |     0.129 |    1.5% |     higher (worse) |
| wall_s               |       7/7 |        20.00 |    20.00 | 5.286e-04 | [8.571e-05, 0.001] |    +0.0% |    0.815 |     0.1279 | 9.905e-04 |    0.0% |     higher (worse) |
| core_j               |       7/7 |       153.38 |   326.44 |    173.05 |   [171.75, 173.96] |  +112.8% |   148.54 | 8.9991e-04 |     1.779 |    1.2% |     higher (worse) |
| rest_frac            |       7/7 |        0.087 |    0.044 |    -0.043 |   [-0.047, -0.041] |   -49.4% |   -13.67 | 8.9991e-04 |     0.005 |    5.5% | lower (diagnostic) |
| bzy_mhz_big_mean     |       7/7 |       3473.6 |   3325.2 |   -148.34 | [-157.56, -140.60] |    -4.3% |   -16.12 | 8.9991e-04 |     14.05 |    0.4% | lower (diagnostic) |
| bzy_mhz_little_mean  |       0/0 |          n/a |      n/a |       n/a |         [n/a, n/a] |      n/a |      n/a |        n/a |       n/a |     n/a |  insufficient data |

- energy_to_solution_j: higher than control by 173.49 J (+103.2%), 95% CI [171.87, 174.94] excludes zero; Hedges g = 103.03, permutation p = 8.9991e-04; MDE = 2.571 J.
- edp_js: higher than control by 3470.4 J*s (+103.2%), 95% CI [3437.8, 3499.3] excludes zero; Hedges g = 103.01, permutation p = 8.9991e-04; MDE = 51.44 J*s.
- pkg_j_per_s: higher than control by 8.673 W (+103.2%), 95% CI [8.592, 8.745] excludes zero; Hedges g = 103.05, permutation p = 8.9991e-04; MDE = 0.129 W.
- wall_s: higher than control by 5.286e-04 s (+0.0%), 95% CI [8.571e-05, 0.001] excludes zero; Hedges g = 0.815, permutation p = 0.1279; MDE = 9.905e-04 s.
- core_j: higher than control by 173.05 J (+112.8%), 95% CI [171.75, 173.96] excludes zero; Hedges g = 148.54, permutation p = 8.9991e-04; MDE = 1.779 J.
- rest_frac: lower than control by 0.043 - (-49.4%), 95% CI [-0.047, -0.041] excludes zero; Hedges g = -13.67, permutation p = 8.9991e-04; MDE = 0.005 -.
- bzy_mhz_big_mean: lower than control by 148.34 MHz (-4.3%), 95% CI [-157.56, -140.60] excludes zero; Hedges g = -16.12, permutation p = 8.9991e-04; MDE = 14.05 MHz.
- bzy_mhz_little_mean: insufficient data (n_control=0, n_arm=0); no contrast computed.

### `flat.idle` vs `flat.big1`

| metric               | n ctl/arm | control mean | arm mean |    diff |     95% CI of diff | % change | Hedges g |   p (perm) | MDE (abs) | MDE (%) |              result |
| :------------------- | --------: | -----------: | -------: | ------: | -----------------: | -------: | -------: | ---------: | --------: | ------: | ------------------: |
| energy_to_solution_j |       7/7 |       168.05 |    11.98 | -156.07 | [-157.20, -154.71] |   -92.9% |  -113.99 | 8.9991e-04 |     2.091 |    1.2% |      lower (better) |
| edp_js               |       7/7 |       3361.4 |   240.82 | -3120.6 | [-3143.6, -3092.7] |   -92.8% |  -111.85 | 8.9991e-04 |     42.60 |    1.3% |      lower (better) |
| pkg_j_per_s          |       7/7 |        8.401 |    0.596 |  -7.806 |   [-7.862, -7.740] |   -92.9% |  -116.15 | 8.9991e-04 |     0.103 |    1.2% |      lower (better) |
| wall_s               |       7/7 |        20.00 |    20.10 |   0.097 |     [0.061, 0.154] |    +0.5% |    2.028 | 8.9991e-04 |     0.073 |    0.4% |      higher (worse) |
| core_j               |       7/7 |       153.38 |    1.727 | -151.66 | [-152.37, -151.06] |   -98.9% |  -210.75 | 8.9991e-04 |     1.099 |    0.7% |      lower (better) |
| rest_frac            |       7/7 |        0.087 |    0.852 |   0.765 |     [0.743, 0.798] |  +878.5% |    26.80 | 8.9991e-04 |     0.044 |   50.1% | higher (diagnostic) |
| bzy_mhz_big_mean     |       7/7 |       3473.6 |   918.48 | -2555.1 | [-2602.4, -2522.4] |   -73.6% |   -59.55 | 8.9991e-04 |     65.52 |    1.9% |  lower (diagnostic) |
| bzy_mhz_little_mean  |       0/0 |          n/a |      n/a |     n/a |         [n/a, n/a] |      n/a |      n/a |        n/a |       n/a |     n/a |   insufficient data |

- energy_to_solution_j: lower than control by 156.07 J (-92.9%), 95% CI [-157.20, -154.71] excludes zero; Hedges g = -113.99, permutation p = 8.9991e-04; MDE = 2.091 J.
- edp_js: lower than control by 3120.6 J*s (-92.8%), 95% CI [-3143.6, -3092.7] excludes zero; Hedges g = -111.85, permutation p = 8.9991e-04; MDE = 42.60 J*s.
- pkg_j_per_s: lower than control by 7.806 W (-92.9%), 95% CI [-7.862, -7.740] excludes zero; Hedges g = -116.15, permutation p = 8.9991e-04; MDE = 0.103 W.
- wall_s: higher than control by 0.097 s (+0.5%), 95% CI [0.061, 0.154] excludes zero; Hedges g = 2.028, permutation p = 8.9991e-04; MDE = 0.073 s.
- core_j: lower than control by 151.66 J (-98.9%), 95% CI [-152.37, -151.06] excludes zero; Hedges g = -210.75, permutation p = 8.9991e-04; MDE = 1.099 J.
- rest_frac: higher than control by 0.765 - (+878.5%), 95% CI [0.743, 0.798] excludes zero; Hedges g = 26.80, permutation p = 8.9991e-04; MDE = 0.044 -.
- bzy_mhz_big_mean: lower than control by 2555.1 MHz (-73.6%), 95% CI [-2602.4, -2522.4] excludes zero; Hedges g = -59.55, permutation p = 8.9991e-04; MDE = 65.52 MHz.
- bzy_mhz_little_mean: insufficient data (n_control=0, n_arm=0); no contrast computed.

### `flat.little1` vs `flat.big1`

| metric               | n ctl/arm | control mean | arm mean |      diff |      95% CI of diff | % change | Hedges g | p (perm) | MDE (abs) | MDE (%) |                   result |
| :------------------- | --------: | -----------: | -------: | --------: | ------------------: | -------: | -------: | -------: | --------: | ------: | -----------------------: |
| energy_to_solution_j |       7/7 |       168.05 |   167.29 |    -0.758 |     [-2.104, 2.093] |    -0.5% |   -0.362 |   0.5299 |     3.197 |    1.9% | no detectable difference |
| edp_js               |       7/7 |       3361.4 |   3346.3 |    -15.12 |     [-42.04, 42.06] |    -0.4% |   -0.361 |   0.5317 |     63.96 |    1.9% | no detectable difference |
| pkg_j_per_s          |       7/7 |        8.401 |    8.363 |    -0.038 |     [-0.105, 0.104] |    -0.5% |   -0.363 |   0.5290 |     0.160 |    1.9% | no detectable difference |
| wall_s               |       7/7 |        20.00 |    20.00 | 2.429e-04 | [-8.571e-05, 0.001] |    +0.0% |    0.460 |   0.5564 | 8.069e-04 |    0.0% | no detectable difference |
| core_j               |       7/7 |       153.38 |   152.37 |    -1.016 |     [-1.940, 0.534] |    -0.7% |   -0.785 |   0.1485 |     1.976 |    1.3% | no detectable difference |
| rest_frac            |       7/7 |        0.087 |    0.089 |     0.001 |     [-0.003, 0.007] |    +1.7% |    0.288 |   0.6270 |     0.008 |    9.0% | no detectable difference |
| bzy_mhz_big_mean     |       7/7 |       3473.6 |   3464.8 |    -8.762 |     [-19.25, 0.684] |    -0.3% |   -0.815 |   0.1349 |     16.43 |    0.5% | no detectable difference |
| bzy_mhz_little_mean  |       0/0 |          n/a |      n/a |       n/a |          [n/a, n/a] |      n/a |      n/a |      n/a |       n/a |     n/a |        insufficient data |

- energy_to_solution_j: no detectable difference (|effect| < MDE = 3.197 J = 1.9% of control).
- edp_js: no detectable difference (|effect| < MDE = 63.96 J*s = 1.9% of control).
- pkg_j_per_s: no detectable difference (|effect| < MDE = 0.160 W = 1.9% of control).
- wall_s: no detectable difference (|effect| < MDE = 8.069e-04 s = 0.0% of control).
- core_j: no detectable difference (|effect| < MDE = 1.976 J = 1.3% of control).
- rest_frac: no detectable difference (|effect| < MDE = 0.008 - = 9.0% of control).
- bzy_mhz_big_mean: no detectable difference (|effect| < MDE = 16.43 MHz = 0.5% of control).
- bzy_mhz_little_mean: insufficient data (n_control=0, n_arm=0); no contrast computed.

### `flat.little2` vs `flat.big1`

| metric               | n ctl/arm | control mean | arm mean |      diff |     95% CI of diff | % change | Hedges g |   p (perm) | MDE (abs) | MDE (%) |             result |
| :------------------- | --------: | -----------: | -------: | --------: | -----------------: | -------: | -------: | ---------: | --------: | ------: | -----------------: |
| energy_to_solution_j |       7/7 |       168.05 |   262.37 |     94.32 |     [93.32, 95.45] |   +56.1% |    81.08 | 8.9991e-04 |     1.776 |    1.1% |     higher (worse) |
| edp_js               |       7/7 |       3361.4 |   5248.1 |    1886.7 |   [1866.7, 1909.3] |   +56.1% |    81.10 | 8.9991e-04 |     35.52 |    1.1% |     higher (worse) |
| pkg_j_per_s          |       7/7 |        8.401 |    13.12 |     4.715 |     [4.665, 4.772] |   +56.1% |    81.05 | 8.9991e-04 |     0.089 |    1.1% |     higher (worse) |
| wall_s               |       7/7 |        20.00 |    20.00 | 3.857e-04 | [7.143e-05, 0.001] |    +0.0% |    0.748 |     0.1147 | 7.871e-04 |    0.0% |     higher (worse) |
| core_j               |       7/7 |       153.38 |   247.43 |     94.05 |     [93.21, 94.72] |   +61.3% |   112.93 | 8.9991e-04 |     1.272 |    0.8% |     higher (worse) |
| rest_frac            |       7/7 |        0.087 |    0.057 |    -0.030 |   [-0.034, -0.027] |   -34.8% |   -8.406 | 8.9991e-04 |     0.005 |    6.3% | lower (diagnostic) |
| bzy_mhz_big_mean     |       7/7 |       3473.6 |   3409.3 |    -64.26 |   [-73.90, -55.29] |    -1.9% |   -6.209 | 8.9991e-04 |     15.81 |    0.5% | lower (diagnostic) |
| bzy_mhz_little_mean  |       0/0 |          n/a |      n/a |       n/a |         [n/a, n/a] |      n/a |      n/a |        n/a |       n/a |     n/a |  insufficient data |

- energy_to_solution_j: higher than control by 94.32 J (+56.1%), 95% CI [93.32, 95.45] excludes zero; Hedges g = 81.08, permutation p = 8.9991e-04; MDE = 1.776 J.
- edp_js: higher than control by 1886.7 J*s (+56.1%), 95% CI [1866.7, 1909.3] excludes zero; Hedges g = 81.10, permutation p = 8.9991e-04; MDE = 35.52 J*s.
- pkg_j_per_s: higher than control by 4.715 W (+56.1%), 95% CI [4.665, 4.772] excludes zero; Hedges g = 81.05, permutation p = 8.9991e-04; MDE = 0.089 W.
- wall_s: higher than control by 3.857e-04 s (+0.0%), 95% CI [7.143e-05, 0.001] excludes zero; Hedges g = 0.748, permutation p = 0.1147; MDE = 7.871e-04 s.
- core_j: higher than control by 94.05 J (+61.3%), 95% CI [93.21, 94.72] excludes zero; Hedges g = 112.93, permutation p = 8.9991e-04; MDE = 1.272 J.
- rest_frac: lower than control by 0.030 - (-34.8%), 95% CI [-0.034, -0.027] excludes zero; Hedges g = -8.406, permutation p = 8.9991e-04; MDE = 0.005 -.
- bzy_mhz_big_mean: lower than control by 64.26 MHz (-1.9%), 95% CI [-73.90, -55.29] excludes zero; Hedges g = -6.209, permutation p = 8.9991e-04; MDE = 15.81 MHz.
- bzy_mhz_little_mean: insufficient data (n_control=0, n_arm=0); no contrast computed.

### `flat.little4` vs `flat.big1`

| metric               | n ctl/arm | control mean | arm mean |      diff |          95% CI of diff | % change | Hedges g |   p (perm) | MDE (abs) | MDE (%) |                   result |
| :------------------- | --------: | -----------: | -------: | --------: | ----------------------: | -------: | -------: | ---------: | --------: | ------: | -----------------------: |
| energy_to_solution_j |       7/7 |       168.05 |   308.64 |    140.59 |        [139.43, 141.71] |   +83.7% |   113.39 | 8.9991e-04 |     1.893 |    1.1% |           higher (worse) |
| edp_js               |       7/7 |       3361.4 |   6173.6 |    2812.2 |        [2788.8, 2834.7] |   +83.7% |   113.20 | 8.9991e-04 |     37.93 |    1.1% |           higher (worse) |
| pkg_j_per_s          |       7/7 |        8.401 |    15.43 |     7.028 |          [6.971, 7.085] |   +83.7% |   113.57 | 8.9991e-04 |     0.094 |    1.1% |           higher (worse) |
| wall_s               |       7/7 |        20.00 |    20.00 | 7.143e-05 | [-4.000e-04, 7.714e-04] |    +0.0% |    0.116 |     0.8037 | 9.430e-04 |    0.0% | no detectable difference |
| core_j               |       7/7 |       153.38 |   293.46 |    140.07 |        [139.26, 140.89] |   +91.3% |   155.94 | 8.9991e-04 |     1.372 |    0.9% |           higher (worse) |
| rest_frac            |       7/7 |        0.087 |    0.049 |    -0.038 |        [-0.042, -0.036] |   -43.6% |   -11.54 | 8.9991e-04 |     0.005 |    5.8% |       lower (diagnostic) |
| bzy_mhz_big_mean     |       7/7 |       3473.6 |   3451.0 |    -22.57 |        [-32.00, -14.64] |    -0.6% |   -2.383 | 8.9991e-04 |     14.46 |    0.4% |       lower (diagnostic) |
| bzy_mhz_little_mean  |       0/0 |          n/a |      n/a |       n/a |              [n/a, n/a] |      n/a |      n/a |        n/a |       n/a |     n/a |        insufficient data |

- energy_to_solution_j: higher than control by 140.59 J (+83.7%), 95% CI [139.43, 141.71] excludes zero; Hedges g = 113.39, permutation p = 8.9991e-04; MDE = 1.893 J.
- edp_js: higher than control by 2812.2 J*s (+83.7%), 95% CI [2788.8, 2834.7] excludes zero; Hedges g = 113.20, permutation p = 8.9991e-04; MDE = 37.93 J*s.
- pkg_j_per_s: higher than control by 7.028 W (+83.7%), 95% CI [6.971, 7.085] excludes zero; Hedges g = 113.57, permutation p = 8.9991e-04; MDE = 0.094 W.
- wall_s: no detectable difference (|effect| < MDE = 9.430e-04 s = 0.0% of control).
- core_j: higher than control by 140.07 J (+91.3%), 95% CI [139.26, 140.89] excludes zero; Hedges g = 155.94, permutation p = 8.9991e-04; MDE = 1.372 J.
- rest_frac: lower than control by 0.038 - (-43.6%), 95% CI [-0.042, -0.036] excludes zero; Hedges g = -11.54, permutation p = 8.9991e-04; MDE = 0.005 -.
- bzy_mhz_big_mean: lower than control by 22.57 MHz (-0.6%), 95% CI [-32.00, -14.64] excludes zero; Hedges g = -2.383, permutation p = 8.9991e-04; MDE = 14.46 MHz.
- bzy_mhz_little_mean: insufficient data (n_control=0, n_arm=0); no contrast computed.

### `partitioned.big1` vs `flat.big1`

| metric               | n ctl/arm | control mean | arm mean |       diff |       95% CI of diff | % change | Hedges g |   p (perm) | MDE (abs) | MDE (%) |                   result |
| :------------------- | --------: | -----------: | -------: | ---------: | -------------------: | -------: | -------: | ---------: | --------: | ------: | -----------------------: |
| energy_to_solution_j |       7/7 |       168.05 |   168.03 |     -0.014 |      [-1.067, 1.051] |    -0.0% |   -0.012 |     0.9862 |     1.756 |    1.0% | no detectable difference |
| edp_js               |       7/7 |       3361.4 |   3360.9 |     -0.470 |      [-21.53, 20.82] |    -0.0% |   -0.020 |     0.9736 |     35.13 |    1.0% | no detectable difference |
| pkg_j_per_s          |       7/7 |        8.401 |    8.401 | -2.393e-04 |      [-0.053, 0.053] |    -0.0% |   -0.004 |     0.9939 |     0.088 |    1.0% | no detectable difference |
| wall_s               |       7/7 |        20.00 |    20.00 |     -0.001 | [-0.001, -3.571e-04] |    -0.0% |   -2.185 |     0.0048 | 7.786e-04 |    0.0% |           lower (better) |
| core_j               |       7/7 |       153.38 |   153.29 |     -0.091 |      [-1.283, 0.936] |    -0.1% |   -0.075 |     0.8910 |     1.856 |    1.2% | no detectable difference |
| rest_frac            |       7/7 |        0.087 |    0.088 |  6.323e-04 |      [-0.003, 0.005] |    +0.7% |    0.146 |     0.6508 |     0.007 |    7.6% | no detectable difference |
| bzy_mhz_big_mean     |       7/7 |       3473.6 |   3544.1 |      70.53 |       [58.14, 82.43] |    +2.0% |    5.339 | 8.9991e-04 |     20.17 |    0.6% |      higher (diagnostic) |
| bzy_mhz_little_mean  |       0/7 |          n/a |   3431.8 |        n/a |           [n/a, n/a] |      n/a |      n/a |        n/a |       n/a |     n/a |        insufficient data |

- energy_to_solution_j: no detectable difference (|effect| < MDE = 1.756 J = 1.0% of control).
- edp_js: no detectable difference (|effect| < MDE = 35.13 J*s = 1.0% of control).
- pkg_j_per_s: no detectable difference (|effect| < MDE = 0.088 W = 1.0% of control).
- wall_s: lower than control by 0.001 s (-0.0%), 95% CI [-0.001, -3.571e-04] excludes zero; Hedges g = -2.185, permutation p = 0.0048; MDE = 7.786e-04 s.
- core_j: no detectable difference (|effect| < MDE = 1.856 J = 1.2% of control).
- rest_frac: no detectable difference (|effect| < MDE = 0.007 - = 7.6% of control).
- bzy_mhz_big_mean: higher than control by 70.53 MHz (+2.0%), 95% CI [58.14, 82.43] excludes zero; Hedges g = 5.339, permutation p = 8.9991e-04; MDE = 20.17 MHz.
- bzy_mhz_little_mean: insufficient data (n_control=0, n_arm=7); no contrast computed.

### `partitioned.big1+little1` vs `flat.big1`

| metric               | n ctl/arm | control mean | arm mean |   diff |       95% CI of diff | % change | Hedges g |   p (perm) | MDE (abs) | MDE (%) |             result |
| :------------------- | --------: | -----------: | -------: | -----: | -------------------: | -------: | -------: | ---------: | --------: | ------: | -----------------: |
| energy_to_solution_j |       7/7 |       168.05 |   262.56 |  94.51 |       [93.44, 95.64] |   +56.2% |    78.33 | 8.9991e-04 |     1.842 |    1.1% |     higher (worse) |
| edp_js               |       7/7 |       3361.4 |   5251.5 | 1890.1 |     [1868.6, 1912.7] |   +56.2% |    78.29 | 8.9991e-04 |     36.87 |    1.1% |     higher (worse) |
| pkg_j_per_s          |       7/7 |        8.401 |    13.13 |  4.726 |       [4.672, 4.782] |   +56.2% |    78.36 | 8.9991e-04 |     0.092 |    1.1% |     higher (worse) |
| wall_s               |       7/7 |        20.00 |    20.00 | -0.001 | [-0.001, -3.714e-04] |    -0.0% |   -2.228 |     0.0048 | 7.931e-04 |    0.0% |     lower (better) |
| core_j               |       7/7 |       153.38 |   248.06 |  94.67 |       [93.86, 95.56] |   +61.7% |   102.98 | 8.9991e-04 |     1.404 |    0.9% |     higher (worse) |
| rest_frac            |       7/7 |        0.087 |    0.055 | -0.032 |     [-0.036, -0.030] |   -36.6% |   -11.88 | 8.9991e-04 |     0.004 |    4.7% | lower (diagnostic) |
| bzy_mhz_big_mean     |       7/7 |       3473.6 |   3427.4 | -46.22 |     [-62.38, -35.82] |    -1.3% |   -3.333 | 8.9991e-04 |     21.17 |    0.6% | lower (diagnostic) |
| bzy_mhz_little_mean  |       0/7 |          n/a |   3430.2 |    n/a |           [n/a, n/a] |      n/a |      n/a |        n/a |       n/a |     n/a |  insufficient data |

- energy_to_solution_j: higher than control by 94.51 J (+56.2%), 95% CI [93.44, 95.64] excludes zero; Hedges g = 78.33, permutation p = 8.9991e-04; MDE = 1.842 J.
- edp_js: higher than control by 1890.1 J*s (+56.2%), 95% CI [1868.6, 1912.7] excludes zero; Hedges g = 78.29, permutation p = 8.9991e-04; MDE = 36.87 J*s.
- pkg_j_per_s: higher than control by 4.726 W (+56.2%), 95% CI [4.672, 4.782] excludes zero; Hedges g = 78.36, permutation p = 8.9991e-04; MDE = 0.092 W.
- wall_s: lower than control by 0.001 s (-0.0%), 95% CI [-0.001, -3.714e-04] excludes zero; Hedges g = -2.228, permutation p = 0.0048; MDE = 7.931e-04 s.
- core_j: higher than control by 94.67 J (+61.7%), 95% CI [93.86, 95.56] excludes zero; Hedges g = 102.98, permutation p = 8.9991e-04; MDE = 1.404 J.
- rest_frac: lower than control by 0.032 - (-36.6%), 95% CI [-0.036, -0.030] excludes zero; Hedges g = -11.88, permutation p = 8.9991e-04; MDE = 0.004 -.
- bzy_mhz_big_mean: lower than control by 46.22 MHz (-1.3%), 95% CI [-62.38, -35.82] excludes zero; Hedges g = -3.333, permutation p = 8.9991e-04; MDE = 21.17 MHz.
- bzy_mhz_little_mean: insufficient data (n_control=0, n_arm=7); no contrast computed.

### `partitioned.big1+little2` vs `flat.big1`

| metric               | n ctl/arm | control mean | arm mean |    diff |       95% CI of diff | % change | Hedges g |   p (perm) | MDE (abs) | MDE (%) |             result |
| :------------------- | --------: | -----------: | -------: | ------: | -------------------: | -------: | -------: | ---------: | --------: | ------: | -----------------: |
| energy_to_solution_j |       7/7 |       168.05 |   303.73 |  135.68 |     [133.73, 140.60] |   +80.7% |    41.66 | 8.9991e-04 |     4.973 |    3.0% |     higher (worse) |
| edp_js               |       7/7 |       3361.4 |   6075.1 |  2713.7 |     [2674.6, 2811.9] |   +80.7% |    41.67 | 8.9991e-04 |     99.45 |    3.0% |     higher (worse) |
| pkg_j_per_s          |       7/7 |        8.401 |    15.19 |   6.784 |       [6.686, 7.030] |   +80.8% |    41.65 | 8.9991e-04 |     0.249 |    3.0% |     higher (worse) |
| wall_s               |       7/7 |        20.00 |    20.00 |  -0.001 | [-0.001, -4.098e-04] |    -0.0% |   -2.335 |     0.0048 | 7.753e-04 |    0.0% |     lower (better) |
| core_j               |       7/7 |       153.38 |   289.09 |  135.70 |     [133.82, 140.70] |   +88.5% |    41.58 | 8.9991e-04 |     4.984 |    3.2% |     higher (worse) |
| rest_frac            |       7/7 |        0.087 |    0.048 |  -0.039 |     [-0.043, -0.037] |   -44.6% |   -13.80 | 8.9991e-04 |     0.004 |    4.9% | lower (diagnostic) |
| bzy_mhz_big_mean     |       7/7 |       3473.6 |   3331.8 | -141.72 |   [-151.08, -133.80] |    -4.1% |   -15.03 | 8.9991e-04 |     14.40 |    0.4% | lower (diagnostic) |
| bzy_mhz_little_mean  |       0/7 |          n/a |   3331.8 |     n/a |           [n/a, n/a] |      n/a |      n/a |        n/a |       n/a |     n/a |  insufficient data |

- energy_to_solution_j: higher than control by 135.68 J (+80.7%), 95% CI [133.73, 140.60] excludes zero; Hedges g = 41.66, permutation p = 8.9991e-04; MDE = 4.973 J.
- edp_js: higher than control by 2713.7 J*s (+80.7%), 95% CI [2674.6, 2811.9] excludes zero; Hedges g = 41.67, permutation p = 8.9991e-04; MDE = 99.45 J*s.
- pkg_j_per_s: higher than control by 6.784 W (+80.8%), 95% CI [6.686, 7.030] excludes zero; Hedges g = 41.65, permutation p = 8.9991e-04; MDE = 0.249 W.
- wall_s: lower than control by 0.001 s (-0.0%), 95% CI [-0.001, -4.098e-04] excludes zero; Hedges g = -2.335, permutation p = 0.0048; MDE = 7.753e-04 s.
- core_j: higher than control by 135.70 J (+88.5%), 95% CI [133.82, 140.70] excludes zero; Hedges g = 41.58, permutation p = 8.9991e-04; MDE = 4.984 J.
- rest_frac: lower than control by 0.039 - (-44.6%), 95% CI [-0.043, -0.037] excludes zero; Hedges g = -13.80, permutation p = 8.9991e-04; MDE = 0.004 -.
- bzy_mhz_big_mean: lower than control by 141.72 MHz (-4.1%), 95% CI [-151.08, -133.80] excludes zero; Hedges g = -15.03, permutation p = 8.9991e-04; MDE = 14.40 MHz.
- bzy_mhz_little_mean: insufficient data (n_control=0, n_arm=7); no contrast computed.

### `partitioned.big1+little4` vs `flat.big1`

| metric               | n ctl/arm | control mean | arm mean |       diff |       95% CI of diff | % change | Hedges g |   p (perm) | MDE (abs) | MDE (%) |             result |
| :------------------- | --------: | -----------: | -------: | ---------: | -------------------: | -------: | -------: | ---------: | --------: | ------: | -----------------: |
| energy_to_solution_j |       7/7 |       168.05 |   341.99 |     173.94 |     [172.69, 175.56] |  +103.5% |   112.70 | 8.9991e-04 |     2.357 |    1.4% |     higher (worse) |
| edp_js               |       7/7 |       3361.4 |   6840.4 |     3479.0 |     [3453.9, 3511.2] |  +103.5% |   112.86 | 8.9991e-04 |     47.07 |    1.4% |     higher (worse) |
| pkg_j_per_s          |       7/7 |        8.401 |    17.10 |      8.697 |       [8.634, 8.778] |  +103.5% |   112.53 | 8.9991e-04 |     0.118 |    1.4% |     higher (worse) |
| wall_s               |       7/7 |        20.00 |    20.00 | -9.286e-04 | [-0.001, -5.714e-05] |    -0.0% |   -1.412 |     0.0255 |     0.001 |    0.0% |     lower (better) |
| core_j               |       7/7 |       153.38 |   327.10 |     173.71 |     [172.57, 175.30] |  +113.3% |   117.73 | 8.9991e-04 |     2.253 |    1.5% |     higher (worse) |
| rest_frac            |       7/7 |        0.087 |    0.044 |     -0.044 |     [-0.047, -0.041] |   -50.0% |   -13.95 | 8.9991e-04 |     0.005 |    5.5% | lower (diagnostic) |
| bzy_mhz_big_mean     |       7/7 |       3473.6 |   3329.6 |    -143.94 |   [-153.10, -136.33] |    -4.1% |   -15.82 | 8.9991e-04 |     13.89 |    0.4% | lower (diagnostic) |
| bzy_mhz_little_mean  |       0/7 |          n/a |   3330.0 |        n/a |           [n/a, n/a] |      n/a |      n/a |        n/a |       n/a |     n/a |  insufficient data |

- energy_to_solution_j: higher than control by 173.94 J (+103.5%), 95% CI [172.69, 175.56] excludes zero; Hedges g = 112.70, permutation p = 8.9991e-04; MDE = 2.357 J.
- edp_js: higher than control by 3479.0 J*s (+103.5%), 95% CI [3453.9, 3511.2] excludes zero; Hedges g = 112.86, permutation p = 8.9991e-04; MDE = 47.07 J*s.
- pkg_j_per_s: higher than control by 8.697 W (+103.5%), 95% CI [8.634, 8.778] excludes zero; Hedges g = 112.53, permutation p = 8.9991e-04; MDE = 0.118 W.
- wall_s: lower than control by 9.286e-04 s (-0.0%), 95% CI [-0.001, -5.714e-05] excludes zero; Hedges g = -1.412, permutation p = 0.0255; MDE = 0.001 s.
- core_j: higher than control by 173.71 J (+113.3%), 95% CI [172.57, 175.30] excludes zero; Hedges g = 117.73, permutation p = 8.9991e-04; MDE = 2.253 J.
- rest_frac: lower than control by 0.044 - (-50.0%), 95% CI [-0.047, -0.041] excludes zero; Hedges g = -13.95, permutation p = 8.9991e-04; MDE = 0.005 -.
- bzy_mhz_big_mean: lower than control by 143.94 MHz (-4.1%), 95% CI [-153.10, -136.33] excludes zero; Hedges g = -15.82, permutation p = 8.9991e-04; MDE = 13.89 MHz.
- bzy_mhz_little_mean: insufficient data (n_control=0, n_arm=7); no contrast computed.

### `partitioned.idle` vs `flat.big1`

| metric               | n ctl/arm | control mean | arm mean |    diff |     95% CI of diff | % change | Hedges g |   p (perm) | MDE (abs) | MDE (%) |              result |
| :------------------- | --------: | -----------: | -------: | ------: | -----------------: | -------: | -------: | ---------: | --------: | ------: | ------------------: |
| energy_to_solution_j |       7/7 |       168.05 |    17.27 | -150.78 | [-152.13, -149.08] |   -89.7% |   -91.04 | 8.9991e-04 |     2.529 |    1.5% |      lower (better) |
| edp_js               |       7/7 |       3361.4 |   346.77 | -3014.6 | [-3042.2, -2979.3] |   -89.7% |   -88.72 | 8.9991e-04 |     51.88 |    1.5% |      lower (better) |
| pkg_j_per_s          |       7/7 |        8.401 |    0.860 |  -7.542 |   [-7.608, -7.460] |   -89.8% |   -93.40 | 8.9991e-04 |     0.123 |    1.5% |      lower (better) |
| wall_s               |       7/7 |        20.00 |    20.08 |   0.075 |     [0.034, 0.142] |    +0.4% |    1.358 | 8.9991e-04 |     0.084 |    0.4% |      higher (worse) |
| core_j               |       7/7 |       153.38 |    7.224 | -146.16 | [-146.88, -145.54] |   -95.3% |  -199.42 | 8.9991e-04 |     1.119 |    0.7% |      lower (better) |
| rest_frac            |       7/7 |        0.087 |    0.578 |   0.491 |     [0.480, 0.513] |  +563.8% |    29.57 | 8.9991e-04 |     0.025 |   29.1% | higher (diagnostic) |
| bzy_mhz_big_mean     |       7/7 |       3473.6 |   3440.8 |  -32.81 |   [-50.44, -14.83] |    -0.9% |   -1.681 |     0.0080 |     29.80 |    0.9% |  lower (diagnostic) |
| bzy_mhz_little_mean  |       0/7 |          n/a |   3435.8 |     n/a |         [n/a, n/a] |      n/a |      n/a |        n/a |       n/a |     n/a |   insufficient data |

- energy_to_solution_j: lower than control by 150.78 J (-89.7%), 95% CI [-152.13, -149.08] excludes zero; Hedges g = -91.04, permutation p = 8.9991e-04; MDE = 2.529 J.
- edp_js: lower than control by 3014.6 J*s (-89.7%), 95% CI [-3042.2, -2979.3] excludes zero; Hedges g = -88.72, permutation p = 8.9991e-04; MDE = 51.88 J*s.
- pkg_j_per_s: lower than control by 7.542 W (-89.8%), 95% CI [-7.608, -7.460] excludes zero; Hedges g = -93.40, permutation p = 8.9991e-04; MDE = 0.123 W.
- wall_s: higher than control by 0.075 s (+0.4%), 95% CI [0.034, 0.142] excludes zero; Hedges g = 1.358, permutation p = 8.9991e-04; MDE = 0.084 s.
- core_j: lower than control by 146.16 J (-95.3%), 95% CI [-146.88, -145.54] excludes zero; Hedges g = -199.42, permutation p = 8.9991e-04; MDE = 1.119 J.
- rest_frac: higher than control by 0.491 - (+563.8%), 95% CI [0.480, 0.513] excludes zero; Hedges g = 29.57, permutation p = 8.9991e-04; MDE = 0.025 -.
- bzy_mhz_big_mean: lower than control by 32.81 MHz (-0.9%), 95% CI [-50.44, -14.83] excludes zero; Hedges g = -1.681, permutation p = 0.0080; MDE = 29.80 MHz.
- bzy_mhz_little_mean: insufficient data (n_control=0, n_arm=7); no contrast computed.

### `partitioned.little1` vs `flat.big1`

| metric               | n ctl/arm | control mean | arm mean |       diff |       95% CI of diff | % change | Hedges g | p (perm) | MDE (abs) | MDE (%) |                   result |
| :------------------- | --------: | -----------: | -------: | ---------: | -------------------: | -------: | -------: | -------: | --------: | ------: | -----------------------: |
| energy_to_solution_j |       7/7 |       168.05 |   166.84 |     -1.213 |     [-2.242, -0.035] |    -0.7% |   -1.005 |   0.0690 |     1.844 |    1.1% |           lower (better) |
| edp_js               |       7/7 |       3361.4 |   3336.9 |     -24.47 |     [-45.04, -0.924] |    -0.7% |   -1.013 |   0.0654 |     36.89 |    1.1% |           lower (better) |
| pkg_j_per_s          |       7/7 |        8.401 |    8.341 |     -0.060 |     [-0.112, -0.001] |    -0.7% |   -0.997 |   0.0717 |     0.092 |    1.1% |           lower (better) |
| wall_s               |       7/7 |        20.00 |    20.00 |     -0.001 | [-0.002, -4.143e-04] |    -0.0% |   -2.302 |   0.0048 | 7.867e-04 |    0.0% |           lower (better) |
| core_j               |       7/7 |       153.38 |   152.30 |     -1.086 |     [-1.785, -0.503] |    -0.7% |   -1.550 |   0.0062 |     1.069 |    0.7% |           lower (better) |
| rest_frac            |       7/7 |        0.087 |    0.087 | -1.349e-04 |      [-0.004, 0.004] |    -0.2% |   -0.033 |   0.8736 |     0.006 |    7.1% | no detectable difference |
| bzy_mhz_big_mean     |       7/7 |       3473.6 |   3481.8 |      8.198 |      [-1.752, 18.11] |    +0.2% |    0.747 |   0.1648 |     16.75 |    0.5% | no detectable difference |
| bzy_mhz_little_mean  |       0/7 |          n/a |   3482.3 |        n/a |           [n/a, n/a] |      n/a |      n/a |      n/a |       n/a |     n/a |        insufficient data |

- energy_to_solution_j: lower than control by 1.213 J (-0.7%), 95% CI [-2.242, -0.035] excludes zero; Hedges g = -1.005, permutation p = 0.0690; MDE = 1.844 J.
- edp_js: lower than control by 24.47 J*s (-0.7%), 95% CI [-45.04, -0.924] excludes zero; Hedges g = -1.013, permutation p = 0.0654; MDE = 36.89 J*s.
- pkg_j_per_s: lower than control by 0.060 W (-0.7%), 95% CI [-0.112, -0.001] excludes zero; Hedges g = -0.997, permutation p = 0.0717; MDE = 0.092 W.
- wall_s: lower than control by 0.001 s (-0.0%), 95% CI [-0.002, -4.143e-04] excludes zero; Hedges g = -2.302, permutation p = 0.0048; MDE = 7.867e-04 s.
- core_j: lower than control by 1.086 J (-0.7%), 95% CI [-1.785, -0.503] excludes zero; Hedges g = -1.550, permutation p = 0.0062; MDE = 1.069 J.
- rest_frac: no detectable difference (|effect| < MDE = 0.006 - = 7.1% of control).
- bzy_mhz_big_mean: no detectable difference (|effect| < MDE = 16.75 MHz = 0.5% of control).
- bzy_mhz_little_mean: insufficient data (n_control=0, n_arm=7); no contrast computed.

### `partitioned.little2` vs `flat.big1`

| metric               | n ctl/arm | control mean | arm mean |    diff |       95% CI of diff | % change | Hedges g |   p (perm) | MDE (abs) | MDE (%) |             result |
| :------------------- | --------: | -----------: | -------: | ------: | -------------------: | -------: | -------: | ---------: | --------: | ------: | -----------------: |
| energy_to_solution_j |       7/7 |       168.05 |   261.96 |   93.91 |       [92.94, 94.88] |   +55.9% |    87.77 | 8.9991e-04 |     1.634 |    1.0% |     higher (worse) |
| edp_js               |       7/7 |       3361.4 |   5239.5 |  1878.1 |     [1858.7, 1897.4] |   +55.9% |    87.77 | 8.9991e-04 |     32.67 |    1.0% |     higher (worse) |
| pkg_j_per_s          |       7/7 |        8.401 |    13.10 |   4.695 |       [4.647, 4.744] |   +55.9% |    87.77 | 8.9991e-04 |     0.082 |    1.0% |     higher (worse) |
| wall_s               |       7/7 |        20.00 |    20.00 |  -0.001 | [-0.001, -3.714e-04] |    -0.0% |   -2.223 |     0.0048 | 7.753e-04 |    0.0% |     lower (better) |
| core_j               |       7/7 |       153.38 |   247.46 |   94.07 |       [93.33, 94.84] |   +61.3% |   112.61 | 8.9991e-04 |     1.276 |    0.8% |     higher (worse) |
| rest_frac            |       7/7 |        0.087 |    0.055 |  -0.032 |     [-0.036, -0.030] |   -36.5% |   -11.75 | 8.9991e-04 |     0.004 |    4.7% | lower (diagnostic) |
| bzy_mhz_big_mean     |       7/7 |       3473.6 |   3330.6 | -142.94 |   [-152.23, -135.24] |    -4.1% |   -15.57 | 8.9991e-04 |     14.02 |    0.4% | lower (diagnostic) |
| bzy_mhz_little_mean  |       0/7 |          n/a |   3505.2 |     n/a |           [n/a, n/a] |      n/a |      n/a |        n/a |       n/a |     n/a |  insufficient data |

- energy_to_solution_j: higher than control by 93.91 J (+55.9%), 95% CI [92.94, 94.88] excludes zero; Hedges g = 87.77, permutation p = 8.9991e-04; MDE = 1.634 J.
- edp_js: higher than control by 1878.1 J*s (+55.9%), 95% CI [1858.7, 1897.4] excludes zero; Hedges g = 87.77, permutation p = 8.9991e-04; MDE = 32.67 J*s.
- pkg_j_per_s: higher than control by 4.695 W (+55.9%), 95% CI [4.647, 4.744] excludes zero; Hedges g = 87.77, permutation p = 8.9991e-04; MDE = 0.082 W.
- wall_s: lower than control by 0.001 s (-0.0%), 95% CI [-0.001, -3.714e-04] excludes zero; Hedges g = -2.223, permutation p = 0.0048; MDE = 7.753e-04 s.
- core_j: higher than control by 94.07 J (+61.3%), 95% CI [93.33, 94.84] excludes zero; Hedges g = 112.61, permutation p = 8.9991e-04; MDE = 1.276 J.
- rest_frac: lower than control by 0.032 - (-36.5%), 95% CI [-0.036, -0.030] excludes zero; Hedges g = -11.75, permutation p = 8.9991e-04; MDE = 0.004 -.
- bzy_mhz_big_mean: lower than control by 142.94 MHz (-4.1%), 95% CI [-152.23, -135.24] excludes zero; Hedges g = -15.57, permutation p = 8.9991e-04; MDE = 14.02 MHz.
- bzy_mhz_little_mean: insufficient data (n_control=0, n_arm=7); no contrast computed.

### `partitioned.little4` vs `flat.big1`

| metric               | n ctl/arm | control mean | arm mean |    diff |       95% CI of diff | % change | Hedges g |   p (perm) | MDE (abs) | MDE (%) |             result |
| :------------------- | --------: | -----------: | -------: | ------: | -------------------: | -------: | -------: | ---------: | --------: | ------: | -----------------: |
| energy_to_solution_j |       7/7 |       168.05 |   308.26 |  140.21 |     [139.02, 141.34] |   +83.4% |   109.96 | 8.9991e-04 |     1.947 |    1.2% |     higher (worse) |
| edp_js               |       7/7 |       3361.4 |   6165.6 |  2804.2 |     [2780.3, 2826.8] |   +83.4% |   110.00 | 8.9991e-04 |     38.93 |    1.2% |     higher (worse) |
| pkg_j_per_s          |       7/7 |        8.401 |    15.41 |   7.011 |       [6.951, 7.067] |   +83.4% |   109.92 | 8.9991e-04 |     0.097 |    1.2% |     higher (worse) |
| wall_s               |       7/7 |        20.00 |    20.00 |  -0.001 | [-0.002, -4.363e-04] |    -0.0% |   -2.381 |     0.0048 | 7.786e-04 |    0.0% |     lower (better) |
| core_j               |       7/7 |       153.38 |   293.61 |  140.22 |     [139.23, 141.13] |   +91.4% |   135.43 | 8.9991e-04 |     1.581 |    1.0% |     higher (worse) |
| rest_frac            |       7/7 |        0.087 |    0.048 |  -0.040 |     [-0.044, -0.038] |   -45.4% |   -14.41 | 8.9991e-04 |     0.004 |    4.8% | lower (diagnostic) |
| bzy_mhz_big_mean     |       7/7 |       3473.6 |   3330.6 | -143.02 |   [-152.35, -135.34] |    -4.1% |   -15.62 | 8.9991e-04 |     13.98 |    0.4% | lower (diagnostic) |
| bzy_mhz_little_mean  |       0/7 |          n/a |   3583.2 |     n/a |           [n/a, n/a] |      n/a |      n/a |        n/a |       n/a |     n/a |  insufficient data |

- energy_to_solution_j: higher than control by 140.21 J (+83.4%), 95% CI [139.02, 141.34] excludes zero; Hedges g = 109.96, permutation p = 8.9991e-04; MDE = 1.947 J.
- edp_js: higher than control by 2804.2 J*s (+83.4%), 95% CI [2780.3, 2826.8] excludes zero; Hedges g = 110.00, permutation p = 8.9991e-04; MDE = 38.93 J*s.
- pkg_j_per_s: higher than control by 7.011 W (+83.4%), 95% CI [6.951, 7.067] excludes zero; Hedges g = 109.92, permutation p = 8.9991e-04; MDE = 0.097 W.
- wall_s: lower than control by 0.001 s (-0.0%), 95% CI [-0.002, -4.363e-04] excludes zero; Hedges g = -2.381, permutation p = 0.0048; MDE = 7.786e-04 s.
- core_j: higher than control by 140.22 J (+91.4%), 95% CI [139.23, 141.13] excludes zero; Hedges g = 135.43, permutation p = 8.9991e-04; MDE = 1.581 J.
- rest_frac: lower than control by 0.040 - (-45.4%), 95% CI [-0.044, -0.038] excludes zero; Hedges g = -14.41, permutation p = 8.9991e-04; MDE = 0.004 -.
- bzy_mhz_big_mean: lower than control by 143.02 MHz (-4.1%), 95% CI [-152.35, -135.34] excludes zero; Hedges g = -15.62, permutation p = 8.9991e-04; MDE = 13.98 MHz.
- bzy_mhz_little_mean: insufficient data (n_control=0, n_arm=7); no contrast computed.

## Minimum detectable effect

At 80% power, alpha 0.05, two-sided, from the observed pooled sd and n. This matters more than any p-value here: it is the smallest true effect this design could have caught. Effects below it are invisible to the experiment, not absent from the machine.

| arm                      |               metric | unit | n ctl/arm | pooled sd | control mean | MDE (abs) | MDE (% of control) |
| :----------------------- | -------------------: | ---: | --------: | --------: | -----------: | --------: | -----------------: |
| flat.big1+little1        | energy_to_solution_j |    J |       7/7 |     1.193 |       168.05 |     1.946 |               1.2% |
| flat.big1+little1        |               edp_js |  J*s |       7/7 |     23.87 |       3361.4 |     38.93 |               1.2% |
| flat.big1+little1        |          pkg_j_per_s |    W |       7/7 |     0.060 |        8.401 |     0.097 |               1.2% |
| flat.big1+little1        |               wall_s |    s |       7/7 | 4.783e-04 |        20.00 | 7.802e-04 |               0.0% |
| flat.big1+little1        |               core_j |    J |       7/7 |     0.776 |       153.38 |     1.265 |               0.8% |
| flat.big1+little1        |            rest_frac |    - |       7/7 |     0.003 |        0.087 |     0.005 |               6.2% |
| flat.big1+little1        |     bzy_mhz_big_mean |  MHz |       7/7 |     9.318 |       3473.6 |     15.20 |               0.4% |
| flat.big1+little1        |  bzy_mhz_little_mean |  MHz |       0/0 |       n/a |          n/a |       n/a |                n/a |
| flat.big1+little2        | energy_to_solution_j |    J |       7/7 |     1.618 |       168.05 |     2.640 |               1.6% |
| flat.big1+little2        |               edp_js |  J*s |       7/7 |     32.37 |       3361.4 |     52.80 |               1.6% |
| flat.big1+little2        |          pkg_j_per_s |    W |       7/7 |     0.081 |        8.401 |     0.132 |               1.6% |
| flat.big1+little2        |               wall_s |    s |       7/7 | 4.823e-04 |        20.00 | 7.867e-04 |               0.0% |
| flat.big1+little2        |               core_j |    J |       7/7 |     1.541 |       153.38 |     2.513 |               1.6% |
| flat.big1+little2        |            rest_frac |    - |       7/7 |     0.003 |        0.087 |     0.005 |               5.9% |
| flat.big1+little2        |     bzy_mhz_big_mean |  MHz |       7/7 |     8.692 |       3473.6 |     14.18 |               0.4% |
| flat.big1+little2        |  bzy_mhz_little_mean |  MHz |       0/0 |       n/a |          n/a |       n/a |                n/a |
| flat.big1+little4        | energy_to_solution_j |    J |       7/7 |     1.576 |       168.05 |     2.571 |               1.5% |
| flat.big1+little4        |               edp_js |  J*s |       7/7 |     31.54 |       3361.4 |     51.44 |               1.5% |
| flat.big1+little4        |          pkg_j_per_s |    W |       7/7 |     0.079 |        8.401 |     0.129 |               1.5% |
| flat.big1+little4        |               wall_s |    s |       7/7 | 6.073e-04 |        20.00 | 9.905e-04 |               0.0% |
| flat.big1+little4        |               core_j |    J |       7/7 |     1.091 |       153.38 |     1.779 |               1.2% |
| flat.big1+little4        |            rest_frac |    - |       7/7 |     0.003 |        0.087 |     0.005 |               5.5% |
| flat.big1+little4        |     bzy_mhz_big_mean |  MHz |       7/7 |     8.613 |       3473.6 |     14.05 |               0.4% |
| flat.big1+little4        |  bzy_mhz_little_mean |  MHz |       0/0 |       n/a |          n/a |       n/a |                n/a |
| flat.idle                | energy_to_solution_j |    J |       7/7 |     1.282 |       168.05 |     2.091 |               1.2% |
| flat.idle                |               edp_js |  J*s |       7/7 |     26.12 |       3361.4 |     42.60 |               1.3% |
| flat.idle                |          pkg_j_per_s |    W |       7/7 |     0.063 |        8.401 |     0.103 |               1.2% |
| flat.idle                |               wall_s |    s |       7/7 |     0.045 |        20.00 |     0.073 |               0.4% |
| flat.idle                |               core_j |    J |       7/7 |     0.674 |       153.38 |     1.099 |               0.7% |
| flat.idle                |            rest_frac |    - |       7/7 |     0.027 |        0.087 |     0.044 |              50.1% |
| flat.idle                |     bzy_mhz_big_mean |  MHz |       7/7 |     40.17 |       3473.6 |     65.52 |               1.9% |
| flat.idle                |  bzy_mhz_little_mean |  MHz |       0/0 |       n/a |          n/a |       n/a |                n/a |
| flat.little1             | energy_to_solution_j |    J |       7/7 |     1.960 |       168.05 |     3.197 |               1.9% |
| flat.little1             |               edp_js |  J*s |       7/7 |     39.21 |       3361.4 |     63.96 |               1.9% |
| flat.little1             |          pkg_j_per_s |    W |       7/7 |     0.098 |        8.401 |     0.160 |               1.9% |
| flat.little1             |               wall_s |    s |       7/7 | 4.947e-04 |        20.00 | 8.069e-04 |               0.0% |
| flat.little1             |               core_j |    J |       7/7 |     1.211 |       153.38 |     1.976 |               1.3% |
| flat.little1             |            rest_frac |    - |       7/7 |     0.005 |        0.087 |     0.008 |               9.0% |
| flat.little1             |     bzy_mhz_big_mean |  MHz |       7/7 |     10.07 |       3473.6 |     16.43 |               0.5% |
| flat.little1             |  bzy_mhz_little_mean |  MHz |       0/0 |       n/a |          n/a |       n/a |                n/a |
| flat.little2             | energy_to_solution_j |    J |       7/7 |     1.089 |       168.05 |     1.776 |               1.1% |
| flat.little2             |               edp_js |  J*s |       7/7 |     21.78 |       3361.4 |     35.52 |               1.1% |
| flat.little2             |          pkg_j_per_s |    W |       7/7 |     0.054 |        8.401 |     0.089 |               1.1% |
| flat.little2             |               wall_s |    s |       7/7 | 4.826e-04 |        20.00 | 7.871e-04 |               0.0% |
| flat.little2             |               core_j |    J |       7/7 |     0.780 |       153.38 |     1.272 |               0.8% |
| flat.little2             |            rest_frac |    - |       7/7 |     0.003 |        0.087 |     0.005 |               6.3% |
| flat.little2             |     bzy_mhz_big_mean |  MHz |       7/7 |     9.690 |       3473.6 |     15.81 |               0.5% |
| flat.little2             |  bzy_mhz_little_mean |  MHz |       0/0 |       n/a |          n/a |       n/a |                n/a |
| flat.little4             | energy_to_solution_j |    J |       7/7 |     1.161 |       168.05 |     1.893 |               1.1% |
| flat.little4             |               edp_js |  J*s |       7/7 |     23.26 |       3361.4 |     37.93 |               1.1% |
| flat.little4             |          pkg_j_per_s |    W |       7/7 |     0.058 |        8.401 |     0.094 |               1.1% |
| flat.little4             |               wall_s |    s |       7/7 | 5.782e-04 |        20.00 | 9.430e-04 |               0.0% |
| flat.little4             |               core_j |    J |       7/7 |     0.841 |       153.38 |     1.372 |               0.9% |
| flat.little4             |            rest_frac |    - |       7/7 |     0.003 |        0.087 |     0.005 |               5.8% |
| flat.little4             |     bzy_mhz_big_mean |  MHz |       7/7 |     8.868 |       3473.6 |     14.46 |               0.4% |
| flat.little4             |  bzy_mhz_little_mean |  MHz |       0/0 |       n/a |          n/a |       n/a |                n/a |
| partitioned.big1         | energy_to_solution_j |    J |       7/7 |     1.076 |       168.05 |     1.756 |               1.0% |
| partitioned.big1         |               edp_js |  J*s |       7/7 |     21.54 |       3361.4 |     35.13 |               1.0% |
| partitioned.big1         |          pkg_j_per_s |    W |       7/7 |     0.054 |        8.401 |     0.088 |               1.0% |
| partitioned.big1         |               wall_s |    s |       7/7 | 4.773e-04 |        20.00 | 7.786e-04 |               0.0% |
| partitioned.big1         |               core_j |    J |       7/7 |     1.138 |       153.38 |     1.856 |               1.2% |
| partitioned.big1         |            rest_frac |    - |       7/7 |     0.004 |        0.087 |     0.007 |               7.6% |
| partitioned.big1         |     bzy_mhz_big_mean |  MHz |       7/7 |     12.37 |       3473.6 |     20.17 |               0.6% |
| partitioned.big1         |  bzy_mhz_little_mean |  MHz |       0/7 |       n/a |          n/a |       n/a |                n/a |
| partitioned.big1+little1 | energy_to_solution_j |    J |       7/7 |     1.130 |       168.05 |     1.842 |               1.1% |
| partitioned.big1+little1 |               edp_js |  J*s |       7/7 |     22.60 |       3361.4 |     36.87 |               1.1% |
| partitioned.big1+little1 |          pkg_j_per_s |    W |       7/7 |     0.056 |        8.401 |     0.092 |               1.1% |
| partitioned.big1+little1 |               wall_s |    s |       7/7 | 4.862e-04 |        20.00 | 7.931e-04 |               0.0% |
| partitioned.big1+little1 |               core_j |    J |       7/7 |     0.861 |       153.38 |     1.404 |               0.9% |
| partitioned.big1+little1 |            rest_frac |    - |       7/7 |     0.003 |        0.087 |     0.004 |               4.7% |
| partitioned.big1+little1 |     bzy_mhz_big_mean |  MHz |       7/7 |     12.98 |       3473.6 |     21.17 |               0.6% |
| partitioned.big1+little1 |  bzy_mhz_little_mean |  MHz |       0/7 |       n/a |          n/a |       n/a |                n/a |
| partitioned.big1+little2 | energy_to_solution_j |    J |       7/7 |     3.049 |       168.05 |     4.973 |               3.0% |
| partitioned.big1+little2 |               edp_js |  J*s |       7/7 |     60.97 |       3361.4 |     99.45 |               3.0% |
| partitioned.big1+little2 |          pkg_j_per_s |    W |       7/7 |     0.152 |        8.401 |     0.249 |               3.0% |
| partitioned.big1+little2 |               wall_s |    s |       7/7 | 4.753e-04 |        20.00 | 7.753e-04 |               0.0% |
| partitioned.big1+little2 |               core_j |    J |       7/7 |     3.056 |       153.38 |     4.984 |               3.2% |
| partitioned.big1+little2 |            rest_frac |    - |       7/7 |     0.003 |        0.087 |     0.004 |               4.9% |
| partitioned.big1+little2 |     bzy_mhz_big_mean |  MHz |       7/7 |     8.826 |       3473.6 |     14.40 |               0.4% |
| partitioned.big1+little2 |  bzy_mhz_little_mean |  MHz |       0/7 |       n/a |          n/a |       n/a |                n/a |
| partitioned.big1+little4 | energy_to_solution_j |    J |       7/7 |     1.445 |       168.05 |     2.357 |               1.4% |
| partitioned.big1+little4 |               edp_js |  J*s |       7/7 |     28.86 |       3361.4 |     47.07 |               1.4% |
| partitioned.big1+little4 |          pkg_j_per_s |    W |       7/7 |     0.072 |        8.401 |     0.118 |               1.4% |
| partitioned.big1+little4 |               wall_s |    s |       7/7 | 6.159e-04 |        20.00 |     0.001 |               0.0% |
| partitioned.big1+little4 |               core_j |    J |       7/7 |     1.381 |       153.38 |     2.253 |               1.5% |
| partitioned.big1+little4 |            rest_frac |    - |       7/7 |     0.003 |        0.087 |     0.005 |               5.5% |
| partitioned.big1+little4 |     bzy_mhz_big_mean |  MHz |       7/7 |     8.518 |       3473.6 |     13.89 |               0.4% |
| partitioned.big1+little4 |  bzy_mhz_little_mean |  MHz |       0/7 |       n/a |          n/a |       n/a |                n/a |
| partitioned.idle         | energy_to_solution_j |    J |       7/7 |     1.551 |       168.05 |     2.529 |               1.5% |
| partitioned.idle         |               edp_js |  J*s |       7/7 |     31.81 |       3361.4 |     51.88 |               1.5% |
| partitioned.idle         |          pkg_j_per_s |    W |       7/7 |     0.076 |        8.401 |     0.123 |               1.5% |
| partitioned.idle         |               wall_s |    s |       7/7 |     0.052 |        20.00 |     0.084 |               0.4% |
| partitioned.idle         |               core_j |    J |       7/7 |     0.686 |       153.38 |     1.119 |               0.7% |
| partitioned.idle         |            rest_frac |    - |       7/7 |     0.016 |        0.087 |     0.025 |              29.1% |
| partitioned.idle         |     bzy_mhz_big_mean |  MHz |       7/7 |     18.27 |       3473.6 |     29.80 |               0.9% |
| partitioned.idle         |  bzy_mhz_little_mean |  MHz |       0/7 |       n/a |          n/a |       n/a |                n/a |
| partitioned.little1      | energy_to_solution_j |    J |       7/7 |     1.130 |       168.05 |     1.844 |               1.1% |
| partitioned.little1      |               edp_js |  J*s |       7/7 |     22.62 |       3361.4 |     36.89 |               1.1% |
| partitioned.little1      |          pkg_j_per_s |    W |       7/7 |     0.057 |        8.401 |     0.092 |               1.1% |
| partitioned.little1      |               wall_s |    s |       7/7 | 4.823e-04 |        20.00 | 7.867e-04 |               0.0% |
| partitioned.little1      |               core_j |    J |       7/7 |     0.656 |       153.38 |     1.069 |               0.7% |
| partitioned.little1      |            rest_frac |    - |       7/7 |     0.004 |        0.087 |     0.006 |               7.1% |
| partitioned.little1      |     bzy_mhz_big_mean |  MHz |       7/7 |     10.27 |       3473.6 |     16.75 |               0.5% |
| partitioned.little1      |  bzy_mhz_little_mean |  MHz |       0/7 |       n/a |          n/a |       n/a |                n/a |
| partitioned.little2      | energy_to_solution_j |    J |       7/7 |     1.002 |       168.05 |     1.634 |               1.0% |
| partitioned.little2      |               edp_js |  J*s |       7/7 |     20.03 |       3361.4 |     32.67 |               1.0% |
| partitioned.little2      |          pkg_j_per_s |    W |       7/7 |     0.050 |        8.401 |     0.082 |               1.0% |
| partitioned.little2      |               wall_s |    s |       7/7 | 4.753e-04 |        20.00 | 7.753e-04 |               0.0% |
| partitioned.little2      |               core_j |    J |       7/7 |     0.782 |       153.38 |     1.276 |               0.8% |
| partitioned.little2      |            rest_frac |    - |       7/7 |     0.003 |        0.087 |     0.004 |               4.7% |
| partitioned.little2      |     bzy_mhz_big_mean |  MHz |       7/7 |     8.596 |       3473.6 |     14.02 |               0.4% |
| partitioned.little2      |  bzy_mhz_little_mean |  MHz |       0/7 |       n/a |          n/a |       n/a |                n/a |
| partitioned.little4      | energy_to_solution_j |    J |       7/7 |     1.194 |       168.05 |     1.947 |               1.2% |
| partitioned.little4      |               edp_js |  J*s |       7/7 |     23.87 |       3361.4 |     38.93 |               1.2% |
| partitioned.little4      |          pkg_j_per_s |    W |       7/7 |     0.060 |        8.401 |     0.097 |               1.2% |
| partitioned.little4      |               wall_s |    s |       7/7 | 4.773e-04 |        20.00 | 7.786e-04 |               0.0% |
| partitioned.little4      |               core_j |    J |       7/7 |     0.969 |       153.38 |     1.581 |               1.0% |
| partitioned.little4      |            rest_frac |    - |       7/7 |     0.003 |        0.087 |     0.004 |               4.8% |
| partitioned.little4      |     bzy_mhz_big_mean |  MHz |       7/7 |     8.571 |       3473.6 |     13.98 |               0.4% |
| partitioned.little4      |  bzy_mhz_little_mean |  MHz |       0/7 |       n/a |          n/a |       n/a |                n/a |

Reading: on `energy_to_solution_j`, the weakest arm comparison (`partitioned.big1+little2`) can only detect effects of **3.0% or larger**. To halve that, quadruple the reps.

## Coverage

| field              | present | missing | coverage |
| :----------------- | ------: | ------: | -------: |
| energy.pkg_j       |     112 |       0 |     100% |
| energy.wall_s      |     112 |       0 |     100% |
| energy.rest_j      |     112 |       0 |     100% |
| energy.cpu_bzy_mhz |     112 |       0 |     100% |
| energy.epp         |     112 |       0 |     100% |
| env.start_temp_c   |     112 |       0 |     100% |
| energy.pkg_c_max   |     112 |       0 |     100% |
| pinger             |       0 |     112 |       0% |
| spin               |      98 |      14 |      88% |
| bls                |       0 |     112 |       0% |

---

# Experiment `e3-ab`

- Runs: **35** across 5 arms (eevdf-flat n=7, eevdf-partitioned n=7, scx-flat n=7, scx-partitioned n=7, scx-partitioned-strict n=7)
- Control arm: **`eevdf-flat`** (factors sched=eevdf,epp=flat)

## Verdict

- eevdf-partitioned vs eevdf-flat: no detectable difference in energy-to-solution (|effect| < MDE = 10.85 J = 1.8% of the control mean, at 80% power / alpha 0.05 with n=7 vs 7). This design could not have seen a saving smaller than that; it is not evidence that the saving is exactly zero.
- scx-flat vs eevdf-flat: no detectable difference in energy-to-solution (|effect| < MDE = 12.08 J = 2.0% of the control mean, at 80% power / alpha 0.05 with n=7 vs 7). This design could not have seen a saving smaller than that; it is not evidence that the saving is exactly zero.
- scx-partitioned vs eevdf-flat: energy-to-solution is HIGHER by 11.33 J (1.9%), 95% CI [5.749, 17.84] excludes zero (Hedges g = 1.715, permutation p = 0.0066).
-    CAUTION: this apparent regression is not admissible while these gates fail: partition is physically real: eevdf-partitioned, partition is physically real: scx-partitioned, partition is physically real: scx-partitioned-strict, run-order drift.
- scx-partitioned-strict vs eevdf-flat: energy-to-solution is HIGHER by 41.71 J (7.1%), 95% CI [35.71, 48.36] excludes zero (Hedges g = 5.950, permutation p = 8.9991e-04).
-    CAUTION: this apparent regression is not admissible while these gates fail: partition is physically real: eevdf-partitioned, partition is physically real: scx-partitioned, partition is physically real: scx-partitioned-strict, run-order drift.
- The partition is NOT physically real in any arm: LITTLE-domain frequency is within 10% of big-domain frequency. Everything downstream is moot -- the energy comparison is a comparison of the machine against itself.
- Failing gates: partition is physically real: eevdf-partitioned, partition is physically real: scx-partitioned, partition is physically real: scx-partitioned-strict, run-order drift.

## Data quality

| status | gate                                                 | numbers                                                                                                                                                                                                                                                                                                                                                                             |
| :----- | :--------------------------------------------------- | :---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| PASS   | run completion                                       | 35/35 runs have ok=true and exit_code=0                                                                                                                                                                                                                                                                                                                                             |
| PASS   | start temperature spread                             | max-min of per-arm mean start_temp_c = 0.57 C (limit 5.0); hottest scx-partitioned-strict 49.9 C, coldest scx-partitioned 49.3 C                                                                                                                                                                                                                                                    |
| PASS   | on_ac consistent                                     | all 35 runs on_ac=True                                                                                                                                                                                                                                                                                                                                                              |
| PASS   | thermal headroom                                     | max pkg_c_max = 94.0 C in arm eevdf-partitioned (limit 97.0 C = Tjmax-3); 0/35 runs at or above the limit                                                                                                                                                                                                                                                                           |
| PASS   | balanced reps per arm                                | eevdf-flat=7, eevdf-partitioned=7, scx-flat=7, scx-partitioned=7, scx-partitioned-strict=7                                                                                                                                                                                                                                                                                          |
| FAIL   | run-order drift                                      | 17 arm/metric pairs with \|Spearman rho vs rep\| > 0.6: eevdf-flat/energy_to_solution_j rho=+0.64; eevdf-flat/pkg_j_per_s rho=+0.82; eevdf-flat/wall_s rho=-0.93; eevdf-flat/core_j rho=+0.71; eevdf-flat/wake_us_p50 rho=+0.61; eevdf-flat/bzy_mhz_big_mean rho=+0.75  [n=7 per arm: rho is noisy at this size, treat as a prompt to inspect the run order, not as proof of drift] |
| FAIL   | partition is physically real: eevdf-partitioned      | little/big bzy MHz = 1.000 (2471.4 MHz / 2471.0 MHz over 7 runs); a real split needs < 0.90  -- EPP did not separate the frequency domains, so no downstream energy difference can be attributed to partitioning.                                                                                                                                                                   |
| FAIL   | partition is physically real: scx-partitioned        | little/big bzy MHz = 1.000 (2491.4 MHz / 2491.6 MHz over 7 runs); a real split needs < 0.90  -- EPP did not separate the frequency domains, so no downstream energy difference can be attributed to partitioning.                                                                                                                                                                   |
| FAIL   | partition is physically real: scx-partitioned-strict | little/big bzy MHz = 0.976 (2522.1 MHz / 2584.1 MHz over 7 runs); a real split needs < 0.90  -- EPP did not separate the frequency domains, so no downstream energy difference can be attributed to partitioning.                                                                                                                                                                   |

**4 gate(s) FAILED.** A failed gate means the arms are not comparable; effect sizes below are reported for completeness but must not be quoted as results until the gate is fixed.

## Placement sanity

A partitioning experiment where the tasks did not stay partitioned proves nothing, so this comes before the effect sizes.

| arm                    | runs w/ bls | strict | enqueues (mean) | cross-domain / enqueue | run time in big | run time in LITTLE | dispatch to big |
| :--------------------- | ----------: | -----: | --------------: | ---------------------: | --------------: | -----------------: | --------------: |
| eevdf-flat             |         0/7 |    n/a |             n/a |                    n/a |             n/a |                n/a |             n/a |
| eevdf-partitioned      |         0/7 |    n/a |             n/a |                    n/a |             n/a |                n/a |             n/a |
| scx-flat               |         7/7 |  false |         29517.0 |                  34.8% |           51.2% |              48.8% |           38.4% |
| scx-partitioned        |         7/7 |  false |         29351.1 |                  34.6% |           51.2% |              48.8% |           38.4% |
| scx-partitioned-strict |         7/7 |   true |          2952.4 |                   0.0% |           81.1% |              18.9% |           56.5% |

- **INFO** -- placement: scx-flat (non-strict): cross_domain/enqueue = 34.8%; run time big/LITTLE = 51.2% / 48.8%
- **INFO** -- placement: scx-partitioned (non-strict): cross_domain/enqueue = 34.6%; run time big/LITTLE = 51.2% / 48.8%
- **PASS** -- placement: scx-partitioned-strict (strict): cross_domain/enqueue = 0.0% (max over runs 0.0%), budget 20%; run time big/LITTLE = 81.1% / 18.9%

## Per-arm summary

Mean with a 95% bootstrap CI (10000 resamples). `n` is the number of runs that actually carried the metric.

### `energy_to_solution_j` (J) -- package energy to complete the workload

| arm                    |   n | missing |   mean | median |    sd |   95% CI of mean | CI method |
| :--------------------- | --: | ------: | -----: | -----: | ----: | ---------------: | --------: |
| eevdf-flat  [control]  |   7 |       0 | 589.41 | 589.58 | 6.487 | [584.02, 593.40] |       BCa |
| eevdf-partitioned      |   7 |       0 | 593.24 | 594.24 | 6.811 | [588.28, 597.58] |       BCa |
| scx-flat               |   7 |       0 | 594.57 | 594.90 | 8.218 | [588.92, 600.18] |       BCa |
| scx-partitioned        |   7 |       0 | 600.74 | 599.64 | 5.867 | [596.78, 604.80] |       BCa |
| scx-partitioned-strict |   7 |       0 | 631.12 | 630.51 | 6.638 | [626.46, 635.54] |       BCa |

### `edp_js` (J*s) -- energy-delay product (pkg_j * wall_s)

| arm                    |   n | missing |    mean |  median |     sd |     95% CI of mean | CI method |
| :--------------------- | --: | ------: | ------: | ------: | -----: | -----------------: | --------: |
| eevdf-flat  [control]  |   7 |       0 | 15374.0 | 15391.9 | 114.37 | [15292.6, 15447.8] |       BCa |
| eevdf-partitioned      |   7 |       0 | 15428.6 | 15407.6 | 164.10 | [15328.5, 15555.4] |       BCa |
| scx-flat               |   7 |       0 | 15718.3 | 15711.4 | 144.92 | [15620.5, 15820.9] |       BCa |
| scx-partitioned        |   7 |       0 | 15794.2 | 15758.6 | 125.22 | [15712.5, 15881.4] |       BCa |
| scx-partitioned-strict |   7 |       0 | 18254.1 | 18370.5 | 448.67 | [17744.0, 18458.6] |       BCa |

### `pkg_j_per_s` (W) -- mean package power

| arm                    |   n | missing |  mean | median |    sd | 95% CI of mean | CI method |
| :--------------------- | --: | ------: | ----: | -----: | ----: | -------------: | --------: |
| eevdf-flat  [control]  |   7 |       0 | 22.60 |  22.73 | 0.465 | [22.26, 22.89] |       BCa |
| eevdf-partitioned      |   7 |       0 | 22.81 |  22.87 | 0.326 | [22.57, 23.02] |       BCa |
| scx-flat               |   7 |       0 | 22.49 |  22.35 | 0.493 | [22.17, 22.86] |       BCa |
| scx-partitioned        |   7 |       0 | 22.85 |  22.89 | 0.421 | [22.54, 23.12] |       BCa |
| scx-partitioned-strict |   7 |       0 | 21.83 |  21.98 | 0.396 | [21.53, 22.07] |       BCa |

### `wall_s` (s) -- time to solution

| arm                    |   n | missing |  mean | median |    sd | 95% CI of mean | CI method |
| :--------------------- | --: | ------: | ----: | -----: | ----: | -------------: | --------: |
| eevdf-flat  [control]  |   7 |       0 | 26.09 |  25.94 | 0.284 | [25.91, 26.30] |       BCa |
| eevdf-partitioned      |   7 |       0 | 26.01 |  26.00 | 0.134 | [25.90, 26.09] |       BCa |
| scx-flat               |   7 |       0 | 26.44 |  26.55 | 0.252 | [26.26, 26.60] |       BCa |
| scx-partitioned        |   7 |       0 | 26.29 |  26.27 | 0.272 | [26.13, 26.50] |       BCa |
| scx-partitioned-strict |   7 |       0 | 28.92 |  28.92 | 0.550 | [28.35, 29.19] |       BCa |

### `core_j` (J) -- core-domain energy (the part EPP can touch)

| arm                    |   n | missing |   mean | median |    sd |   95% CI of mean | CI method |
| :--------------------- | --: | ------: | -----: | -----: | ----: | ---------------: | --------: |
| eevdf-flat  [control]  |   7 |       0 | 557.95 | 558.80 | 6.032 | [552.93, 561.43] |       BCa |
| eevdf-partitioned      |   7 |       0 | 562.14 | 562.81 | 6.644 | [557.42, 566.67] |       BCa |
| scx-flat               |   7 |       0 | 563.23 | 563.97 | 8.283 | [557.50, 568.88] |       BCa |
| scx-partitioned        |   7 |       0 | 569.56 | 568.13 | 5.856 | [565.65, 573.66] |       BCa |
| scx-partitioned-strict |   7 |       0 | 598.96 | 598.96 | 6.430 | [594.39, 603.27] |       BCa |

### `rest_frac` (-) -- share of pkg energy EPP cannot touch

| arm                    |   n | missing |  mean | median |        sd | 95% CI of mean | CI method |
| :--------------------- | --: | ------: | ----: | -----: | --------: | -------------: | --------: |
| eevdf-flat  [control]  |   7 |       0 | 0.053 |  0.053 |     0.001 | [0.053, 0.055] |       BCa |
| eevdf-partitioned      |   7 |       0 | 0.052 |  0.052 | 5.164e-04 | [0.052, 0.053] |       BCa |
| scx-flat               |   7 |       0 | 0.053 |  0.053 |     0.001 | [0.052, 0.054] |       BCa |
| scx-partitioned        |   7 |       0 | 0.052 |  0.052 | 5.979e-04 | [0.051, 0.052] |       BCa |
| scx-partitioned-strict |   7 |       0 | 0.051 |  0.051 | 5.235e-04 | [0.051, 0.051] |       BCa |

### `wake_us_p99` (us) -- pinger p99 wake latency (QoS cost)

| arm                    |   n | missing |   mean | median |     sd |   95% CI of mean | CI method |
| :--------------------- | --: | ------: | -----: | -----: | -----: | ---------------: | --------: |
| eevdf-flat  [control]  |   7 |       0 | 1678.5 | 1895.8 | 379.32 | [1400.6, 1909.8] |       BCa |
| eevdf-partitioned      |   7 |       0 | 1773.1 | 1828.8 | 333.12 | [1555.6, 2007.9] |       BCa |
| scx-flat               |   7 |       0 | 7300.1 | 7366.4 | 939.64 | [6737.6, 8044.4] |       BCa |
| scx-partitioned        |   7 |       0 | 7292.2 | 7350.9 | 489.13 | [6958.0, 7621.4] |       BCa |
| scx-partitioned-strict |   7 |       0 | 2346.8 | 2004.1 | 955.84 | [1862.2, 3275.9] |       BCa |

### `wake_us_p50` (us) -- pinger median wake latency

| arm                    |   n | missing |   mean | median |     sd |   95% CI of mean | CI method |
| :--------------------- | --: | ------: | -----: | -----: | -----: | ---------------: | --------: |
| eevdf-flat  [control]  |   7 |       0 | 326.49 | 274.88 | 281.04 | [154.72, 539.19] |       BCa |
| eevdf-partitioned      |   7 |       0 | 346.51 | 389.95 | 211.01 | [191.93, 476.74] |       BCa |
| scx-flat               |   7 |       0 | 500.94 | 410.15 | 255.18 | [349.54, 715.26] |       BCa |
| scx-partitioned        |   7 |       0 | 588.70 | 573.62 | 273.20 | [399.41, 776.58] |       BCa |
| scx-partitioned-strict |   7 |       0 | 361.82 | 240.97 | 232.82 | [221.41, 540.56] |       BCa |

### `bzy_mhz_big_mean` (MHz) -- mean busy MHz of the big domain

| arm                    |   n | missing |   mean | median |    sd |   95% CI of mean | CI method |
| :--------------------- | --: | ------: | -----: | -----: | ----: | ---------------: | --------: |
| eevdf-flat  [control]  |   7 |       0 | 2460.7 | 2468.1 | 18.37 | [2446.7, 2472.0] |       BCa |
| eevdf-partitioned      |   7 |       0 | 2471.0 | 2472.6 | 14.42 | [2460.8, 2480.5] |       BCa |
| scx-flat               |   7 |       0 | 2476.2 | 2473.3 | 21.92 | [2461.9, 2491.7] |       BCa |
| scx-partitioned        |   7 |       0 | 2491.6 | 2489.7 | 15.99 | [2480.9, 2502.8] |       BCa |
| scx-partitioned-strict |   7 |       0 | 2584.1 | 2591.3 | 16.14 | [2571.7, 2594.1] |       BCa |

### `bzy_mhz_little_mean` (MHz) -- mean busy MHz of the LITTLE domain

| arm                    |   n | missing |   mean | median |    sd |   95% CI of mean | CI method |
| :--------------------- | --: | ------: | -----: | -----: | ----: | ---------------: | --------: |
| eevdf-flat  [control]  |   0 |       7 |    n/a |    n/a |   n/a |       [n/a, n/a] |       n/a |
| eevdf-partitioned      |   7 |       0 | 2471.4 | 2472.9 | 13.99 | [2461.6, 2480.7] |       BCa |
| scx-flat               |   0 |       7 |    n/a |    n/a |   n/a |       [n/a, n/a] |       n/a |
| scx-partitioned        |   7 |       0 | 2491.4 | 2490.3 | 15.99 | [2480.5, 2502.4] |       BCa |
| scx-partitioned-strict |   7 |       0 | 2522.1 | 2525.2 | 12.86 | [2512.0, 2529.9] |       BCa |

## Contrasts vs control (`eevdf-flat`)

Difference in means (arm - control). A contrast whose CI straddles zero is reported as *no detectable difference*, never as a signed saving.

### `eevdf-partitioned` vs `eevdf-flat`

| metric               | n ctl/arm | control mean | arm mean |       diff |       95% CI of diff | % change | Hedges g | p (perm) | MDE (abs) | MDE (%) |                   result |
| :------------------- | --------: | -----------: | -------: | ---------: | -------------------: | -------: | -------: | -------: | --------: | ------: | -----------------------: |
| energy_to_solution_j |       7/7 |       589.41 |   593.24 |      3.833 |      [-2.329, 10.42] |    +0.7% |    0.540 |   0.2873 |     10.85 |    1.8% | no detectable difference |
| edp_js               |       7/7 |      15374.0 |  15428.6 |      54.63 |     [-72.56, 197.95] |    +0.4% |    0.362 |   0.4818 |    230.69 |    1.5% | no detectable difference |
| pkg_j_per_s          |       7/7 |        22.60 |    22.81 |      0.212 |      [-0.165, 0.609] |    +0.9% |    0.495 |   0.3356 |     0.654 |    2.9% | no detectable difference |
| wall_s               |       7/7 |        26.09 |    26.01 |     -0.078 |      [-0.315, 0.117] |    -0.3% |   -0.329 |   0.5165 |     0.362 |    1.4% | no detectable difference |
| core_j               |       7/7 |       557.95 |   562.14 |      4.190 |      [-1.783, 10.40] |    +0.8% |    0.618 |   0.2340 |     10.35 |    1.9% | no detectable difference |
| rest_frac            |       7/7 |        0.053 |    0.052 | -9.452e-04 | [-0.002, -2.237e-04] |    -1.8% |   -0.852 |   0.0646 |     0.002 |    3.2% |       lower (diagnostic) |
| wake_us_p99          |       7/7 |       1678.5 |   1773.1 |      94.60 |    [-230.71, 458.51] |    +5.6% |    0.248 |   0.6127 |    582.23 |   34.7% | no detectable difference |
| wake_us_p50          |       7/7 |       326.49 |   346.51 |      20.02 |    [-237.88, 238.41] |    +6.1% |    0.075 |   0.8789 |    405.32 |  124.1% | no detectable difference |
| bzy_mhz_big_mean     |       7/7 |       2460.7 |   2471.0 |      10.31 |      [-4.879, 26.97] |    +0.4% |    0.584 |   0.2558 |     26.94 |    1.1% | no detectable difference |
| bzy_mhz_little_mean  |       0/7 |          n/a |   2471.4 |        n/a |           [n/a, n/a] |      n/a |      n/a |      n/a |       n/a |     n/a |        insufficient data |

- energy_to_solution_j: no detectable difference (|effect| < MDE = 10.85 J = 1.8% of control).
- edp_js: no detectable difference (|effect| < MDE = 230.69 J*s = 1.5% of control).
- pkg_j_per_s: no detectable difference (|effect| < MDE = 0.654 W = 2.9% of control).
- wall_s: no detectable difference (|effect| < MDE = 0.362 s = 1.4% of control).
- core_j: no detectable difference (|effect| < MDE = 10.35 J = 1.9% of control).
- rest_frac: lower than control by 9.452e-04 - (-1.8%), 95% CI [-0.002, -2.237e-04] excludes zero; Hedges g = -0.852, permutation p = 0.0646; MDE = 0.002 -.
- wake_us_p99: no detectable difference (|effect| < MDE = 582.23 us = 34.7% of control).
- wake_us_p50: no detectable difference (|effect| < MDE = 405.32 us = 124.1% of control).
- bzy_mhz_big_mean: no detectable difference (|effect| < MDE = 26.94 MHz = 1.1% of control).
- bzy_mhz_little_mean: insufficient data (n_control=0, n_arm=7); no contrast computed.

### `scx-flat` vs `eevdf-flat`

| metric               | n ctl/arm | control mean | arm mean |       diff |      95% CI of diff | % change | Hedges g |   p (perm) | MDE (abs) | MDE (%) |                   result |
| :------------------- | --------: | -----------: | -------: | ---------: | ------------------: | -------: | -------: | ---------: | --------: | ------: | -----------------------: |
| energy_to_solution_j |       7/7 |       589.41 |   594.57 |      5.160 |     [-1.838, 12.51] |    +0.9% |    0.652 |     0.2041 |     12.08 |    2.0% | no detectable difference |
| edp_js               |       7/7 |      15374.0 |  15718.3 |     344.29 |    [221.17, 474.05] |    +2.2% |    2.469 |     0.0013 |    212.92 |    1.4% |           higher (worse) |
| pkg_j_per_s          |       7/7 |        22.60 |    22.49 |     -0.107 |     [-0.552, 0.374] |    -0.5% |   -0.209 |     0.6551 |     0.782 |    3.5% | no detectable difference |
| wall_s               |       7/7 |        26.09 |    26.44 |      0.353 |      [0.078, 0.593] |    +1.4% |    1.229 |     0.0341 |     0.439 |    1.7% |           higher (worse) |
| core_j               |       7/7 |       557.95 |   563.23 |      5.278 |     [-1.544, 12.49] |    +0.9% |    0.682 |     0.1878 |     11.82 |    2.1% | no detectable difference |
| rest_frac            |       7/7 |        0.053 |    0.053 | -6.559e-04 | [-0.002, 3.653e-04] |    -1.2% |   -0.496 |     0.3761 |     0.002 |    3.8% | no detectable difference |
| wake_us_p99          |       7/7 |       1678.5 |   7300.1 |     5621.6 |    [5005.6, 6398.8] |  +334.9% |    7.345 | 8.9991e-04 |    1168.7 |   69.6% |           higher (worse) |
| wake_us_p50          |       7/7 |       326.49 |   500.94 |     174.44 |    [-83.99, 441.60] |   +53.4% |    0.608 |     0.2514 |    437.81 |  134.1% | no detectable difference |
| bzy_mhz_big_mean     |       7/7 |       2460.7 |   2476.2 |      15.49 |     [-3.214, 35.99] |    +0.6% |    0.717 |     0.1746 |     32.99 |    1.3% | no detectable difference |
| bzy_mhz_little_mean  |       0/0 |          n/a |      n/a |        n/a |          [n/a, n/a] |      n/a |      n/a |        n/a |       n/a |     n/a |        insufficient data |

- energy_to_solution_j: no detectable difference (|effect| < MDE = 12.08 J = 2.0% of control).
- edp_js: higher than control by 344.29 J*s (+2.2%), 95% CI [221.17, 474.05] excludes zero; Hedges g = 2.469, permutation p = 0.0013; MDE = 212.92 J*s.
- pkg_j_per_s: no detectable difference (|effect| < MDE = 0.782 W = 3.5% of control).
- wall_s: higher than control by 0.353 s (+1.4%), 95% CI [0.078, 0.593] excludes zero; Hedges g = 1.229, permutation p = 0.0341; MDE = 0.439 s.
- core_j: no detectable difference (|effect| < MDE = 11.82 J = 2.1% of control).
- rest_frac: no detectable difference (|effect| < MDE = 0.002 - = 3.8% of control).
- wake_us_p99: higher than control by 5621.6 us (+334.9%), 95% CI [5005.6, 6398.8] excludes zero; Hedges g = 7.345, permutation p = 8.9991e-04; MDE = 1168.7 us.
- wake_us_p50: no detectable difference (|effect| < MDE = 437.81 us = 134.1% of control).
- bzy_mhz_big_mean: no detectable difference (|effect| < MDE = 32.99 MHz = 1.3% of control).
- bzy_mhz_little_mean: insufficient data (n_control=0, n_arm=0); no contrast computed.

### `scx-partitioned` vs `eevdf-flat`

| metric               | n ctl/arm | control mean | arm mean |   diff |       95% CI of diff | % change | Hedges g |   p (perm) | MDE (abs) | MDE (%) |                   result |
| :------------------- | --------: | -----------: | -------: | -----: | -------------------: | -------: | -------: | ---------: | --------: | ------: | -----------------------: |
| energy_to_solution_j |       7/7 |       589.41 |   600.74 |  11.33 |       [5.749, 17.84] |    +1.9% |    1.715 |     0.0066 |     10.09 |    1.7% |           higher (worse) |
| edp_js               |       7/7 |      15374.0 |  15794.2 | 420.20 |     [308.44, 537.79] |    +2.7% |    3.280 | 8.9991e-04 |    195.59 |    1.3% |           higher (worse) |
| pkg_j_per_s          |       7/7 |        22.60 |    22.85 |  0.252 |      [-0.172, 0.686] |    +1.1% |    0.533 |     0.3042 |     0.723 |    3.2% | no detectable difference |
| wall_s               |       7/7 |        26.09 |    26.29 |  0.207 |      [-0.059, 0.474] |    +0.8% |    0.697 |     0.1920 |     0.454 |    1.7% | no detectable difference |
| core_j               |       7/7 |       557.95 |   569.56 |  11.60 |       [6.309, 17.84] |    +2.1% |    1.827 |     0.0038 |     9.696 |    1.7% |           higher (worse) |
| rest_frac            |       7/7 |        0.053 |    0.052 | -0.001 | [-0.003, -7.081e-04] |    -2.7% |   -1.281 |     0.0047 |     0.002 |    3.2% |       lower (diagnostic) |
| wake_us_p99          |       7/7 |       1678.5 |   7292.2 | 5613.6 |     [5194.5, 6033.9] |  +334.4% |    12.01 | 8.9991e-04 |    713.89 |   42.5% |           higher (worse) |
| wake_us_p50          |       7/7 |       326.49 |   588.70 | 262.20 |     [-17.04, 515.94] |   +80.3% |    0.886 |     0.0976 |    452.05 |  138.5% | no detectable difference |
| bzy_mhz_big_mean     |       7/7 |       2460.7 |   2491.6 |  30.94 |       [15.03, 48.40] |    +1.3% |    1.682 |     0.0074 |     28.09 |    1.1% |      higher (diagnostic) |
| bzy_mhz_little_mean  |       0/7 |          n/a |   2491.4 |    n/a |           [n/a, n/a] |      n/a |      n/a |        n/a |       n/a |     n/a |        insufficient data |

- energy_to_solution_j: higher than control by 11.33 J (+1.9%), 95% CI [5.749, 17.84] excludes zero; Hedges g = 1.715, permutation p = 0.0066; MDE = 10.09 J.
- edp_js: higher than control by 420.20 J*s (+2.7%), 95% CI [308.44, 537.79] excludes zero; Hedges g = 3.280, permutation p = 8.9991e-04; MDE = 195.59 J*s.
- pkg_j_per_s: no detectable difference (|effect| < MDE = 0.723 W = 3.2% of control).
- wall_s: no detectable difference (|effect| < MDE = 0.454 s = 1.7% of control).
- core_j: higher than control by 11.60 J (+2.1%), 95% CI [6.309, 17.84] excludes zero; Hedges g = 1.827, permutation p = 0.0038; MDE = 9.696 J.
- rest_frac: lower than control by 0.001 - (-2.7%), 95% CI [-0.003, -7.081e-04] excludes zero; Hedges g = -1.281, permutation p = 0.0047; MDE = 0.002 -.
- wake_us_p99: higher than control by 5613.6 us (+334.4%), 95% CI [5194.5, 6033.9] excludes zero; Hedges g = 12.01, permutation p = 8.9991e-04; MDE = 713.89 us.
- wake_us_p50: no detectable difference (|effect| < MDE = 452.05 us = 138.5% of control).
- bzy_mhz_big_mean: higher than control by 30.94 MHz (+1.3%), 95% CI [15.03, 48.40] excludes zero; Hedges g = 1.682, permutation p = 0.0074; MDE = 28.09 MHz.
- bzy_mhz_little_mean: insufficient data (n_control=0, n_arm=7); no contrast computed.

### `scx-partitioned-strict` vs `eevdf-flat`

| metric               | n ctl/arm | control mean | arm mean |   diff |    95% CI of diff | % change | Hedges g |   p (perm) | MDE (abs) | MDE (%) |                   result |
| :------------------- | --------: | -----------: | -------: | -----: | ----------------: | -------: | -------: | ---------: | --------: | ------: | -----------------------: |
| energy_to_solution_j |       7/7 |       589.41 |   631.12 |  41.71 |    [35.71, 48.36] |    +7.1% |    5.950 | 8.9991e-04 |     10.70 |    1.8% |           higher (worse) |
| edp_js               |       7/7 |      15374.0 |  18254.1 | 2880.1 |  [2370.6, 3098.2] |   +18.7% |    8.235 | 8.9991e-04 |    534.02 |    3.5% |           higher (worse) |
| pkg_j_per_s          |       7/7 |        22.60 |    21.83 | -0.772 |  [-1.187, -0.351] |    -3.4% |   -1.673 |     0.0086 |     0.704 |    3.1% |           lower (better) |
| wall_s               |       7/7 |        26.09 |    28.92 |  2.836 |    [2.267, 3.169] |   +10.9% |    6.068 | 8.9991e-04 |     0.714 |    2.7% |           higher (worse) |
| core_j               |       7/7 |       557.95 |   598.96 |  41.01 |    [35.17, 47.26] |    +7.3% |    6.158 | 8.9991e-04 |     10.17 |    1.8% |           higher (worse) |
| rest_frac            |       7/7 |        0.053 |    0.051 | -0.002 |  [-0.004, -0.002] |    -4.5% |   -2.164 | 8.9991e-04 |     0.002 |    3.2% |       lower (diagnostic) |
| wake_us_p99          |       7/7 |       1678.5 |   2346.8 | 668.27 |  [119.25, 1634.2] |   +39.8% |    0.860 |     0.0859 |    1186.0 |   70.7% |           higher (worse) |
| wake_us_p50          |       7/7 |       326.49 |   361.82 |  35.32 | [-225.32, 280.45] |   +10.8% |    0.128 |     0.7924 |    420.91 |  128.9% | no detectable difference |
| bzy_mhz_big_mean     |       7/7 |       2460.7 |   2584.1 | 123.42 |  [106.64, 140.07] |    +5.0% |    6.682 | 8.9991e-04 |     28.20 |    1.1% |      higher (diagnostic) |
| bzy_mhz_little_mean  |       0/7 |          n/a |   2522.1 |    n/a |        [n/a, n/a] |      n/a |      n/a |        n/a |       n/a |     n/a |        insufficient data |

- energy_to_solution_j: higher than control by 41.71 J (+7.1%), 95% CI [35.71, 48.36] excludes zero; Hedges g = 5.950, permutation p = 8.9991e-04; MDE = 10.70 J.
- edp_js: higher than control by 2880.1 J*s (+18.7%), 95% CI [2370.6, 3098.2] excludes zero; Hedges g = 8.235, permutation p = 8.9991e-04; MDE = 534.02 J*s.
- pkg_j_per_s: lower than control by 0.772 W (-3.4%), 95% CI [-1.187, -0.351] excludes zero; Hedges g = -1.673, permutation p = 0.0086; MDE = 0.704 W.
- wall_s: higher than control by 2.836 s (+10.9%), 95% CI [2.267, 3.169] excludes zero; Hedges g = 6.068, permutation p = 8.9991e-04; MDE = 0.714 s.
- core_j: higher than control by 41.01 J (+7.3%), 95% CI [35.17, 47.26] excludes zero; Hedges g = 6.158, permutation p = 8.9991e-04; MDE = 10.17 J.
- rest_frac: lower than control by 0.002 - (-4.5%), 95% CI [-0.004, -0.002] excludes zero; Hedges g = -2.164, permutation p = 8.9991e-04; MDE = 0.002 -.
- wake_us_p99: higher than control by 668.27 us (+39.8%), 95% CI [119.25, 1634.2] excludes zero; Hedges g = 0.860, permutation p = 0.0859; MDE = 1186.0 us.
- wake_us_p50: no detectable difference (|effect| < MDE = 420.91 us = 128.9% of control).
- bzy_mhz_big_mean: higher than control by 123.42 MHz (+5.0%), 95% CI [106.64, 140.07] excludes zero; Hedges g = 6.682, permutation p = 8.9991e-04; MDE = 28.20 MHz.
- bzy_mhz_little_mean: insufficient data (n_control=0, n_arm=7); no contrast computed.

## Minimum detectable effect

At 80% power, alpha 0.05, two-sided, from the observed pooled sd and n. This matters more than any p-value here: it is the smallest true effect this design could have caught. Effects below it are invisible to the experiment, not absent from the machine.

| arm                    |               metric | unit | n ctl/arm | pooled sd | control mean | MDE (abs) | MDE (% of control) |
| :--------------------- | -------------------: | ---: | --------: | --------: | -----------: | --------: | -----------------: |
| eevdf-partitioned      | energy_to_solution_j |    J |       7/7 |     6.651 |       589.41 |     10.85 |               1.8% |
| eevdf-partitioned      |               edp_js |  J*s |       7/7 |    141.43 |      15374.0 |    230.69 |               1.5% |
| eevdf-partitioned      |          pkg_j_per_s |    W |       7/7 |     0.401 |        22.60 |     0.654 |               2.9% |
| eevdf-partitioned      |               wall_s |    s |       7/7 |     0.222 |        26.09 |     0.362 |               1.4% |
| eevdf-partitioned      |               core_j |    J |       7/7 |     6.345 |       557.95 |     10.35 |               1.9% |
| eevdf-partitioned      |            rest_frac |    - |       7/7 |     0.001 |        0.053 |     0.002 |               3.2% |
| eevdf-partitioned      |          wake_us_p99 |   us |       7/7 |    356.97 |       1678.5 |    582.23 |              34.7% |
| eevdf-partitioned      |          wake_us_p50 |   us |       7/7 |    248.50 |       326.49 |    405.32 |             124.1% |
| eevdf-partitioned      |     bzy_mhz_big_mean |  MHz |       7/7 |     16.51 |       2460.7 |     26.94 |               1.1% |
| eevdf-partitioned      |  bzy_mhz_little_mean |  MHz |       0/7 |       n/a |          n/a |       n/a |                n/a |
| scx-flat               | energy_to_solution_j |    J |       7/7 |     7.403 |       589.41 |     12.08 |               2.0% |
| scx-flat               |               edp_js |  J*s |       7/7 |    130.54 |      15374.0 |    212.92 |               1.4% |
| scx-flat               |          pkg_j_per_s |    W |       7/7 |     0.479 |        22.60 |     0.782 |               3.5% |
| scx-flat               |               wall_s |    s |       7/7 |     0.269 |        26.09 |     0.439 |               1.7% |
| scx-flat               |               core_j |    J |       7/7 |     7.245 |       557.95 |     11.82 |               2.1% |
| scx-flat               |            rest_frac |    - |       7/7 |     0.001 |        0.053 |     0.002 |               3.8% |
| scx-flat               |          wake_us_p99 |   us |       7/7 |    716.52 |       1678.5 |    1168.7 |              69.6% |
| scx-flat               |          wake_us_p50 |   us |       7/7 |    268.42 |       326.49 |    437.81 |             134.1% |
| scx-flat               |     bzy_mhz_big_mean |  MHz |       7/7 |     20.22 |       2460.7 |     32.99 |               1.3% |
| scx-flat               |  bzy_mhz_little_mean |  MHz |       0/0 |       n/a |          n/a |       n/a |                n/a |
| scx-partitioned        | energy_to_solution_j |    J |       7/7 |     6.185 |       589.41 |     10.09 |               1.7% |
| scx-partitioned        |               edp_js |  J*s |       7/7 |    119.92 |      15374.0 |    195.59 |               1.3% |
| scx-partitioned        |          pkg_j_per_s |    W |       7/7 |     0.443 |        22.60 |     0.723 |               3.2% |
| scx-partitioned        |               wall_s |    s |       7/7 |     0.278 |        26.09 |     0.454 |               1.7% |
| scx-partitioned        |               core_j |    J |       7/7 |     5.944 |       557.95 |     9.696 |               1.7% |
| scx-partitioned        |            rest_frac |    - |       7/7 |     0.001 |        0.053 |     0.002 |               3.2% |
| scx-partitioned        |          wake_us_p99 |   us |       7/7 |    437.68 |       1678.5 |    713.89 |              42.5% |
| scx-partitioned        |          wake_us_p50 |   us |       7/7 |    277.15 |       326.49 |    452.05 |             138.5% |
| scx-partitioned        |     bzy_mhz_big_mean |  MHz |       7/7 |     17.22 |       2460.7 |     28.09 |               1.1% |
| scx-partitioned        |  bzy_mhz_little_mean |  MHz |       0/7 |       n/a |          n/a |       n/a |                n/a |
| scx-partitioned-strict | energy_to_solution_j |    J |       7/7 |     6.563 |       589.41 |     10.70 |               1.8% |
| scx-partitioned-strict |               edp_js |  J*s |       7/7 |    327.41 |      15374.0 |    534.02 |               3.5% |
| scx-partitioned-strict |          pkg_j_per_s |    W |       7/7 |     0.432 |        22.60 |     0.704 |               3.1% |
| scx-partitioned-strict |               wall_s |    s |       7/7 |     0.437 |        26.09 |     0.714 |               2.7% |
| scx-partitioned-strict |               core_j |    J |       7/7 |     6.234 |       557.95 |     10.17 |               1.8% |
| scx-partitioned-strict |            rest_frac |    - |       7/7 |     0.001 |        0.053 |     0.002 |               3.2% |
| scx-partitioned-strict |          wake_us_p99 |   us |       7/7 |    727.16 |       1678.5 |    1186.0 |              70.7% |
| scx-partitioned-strict |          wake_us_p50 |   us |       7/7 |    258.06 |       326.49 |    420.91 |             128.9% |
| scx-partitioned-strict |     bzy_mhz_big_mean |  MHz |       7/7 |     17.29 |       2460.7 |     28.20 |               1.1% |
| scx-partitioned-strict |  bzy_mhz_little_mean |  MHz |       0/7 |       n/a |          n/a |       n/a |                n/a |

Reading: on `energy_to_solution_j`, the weakest arm comparison (`scx-flat`) can only detect effects of **2.0% or larger**. To halve that, quadruple the reps.

## Coverage

| field              | present | missing | coverage |
| :----------------- | ------: | ------: | -------: |
| energy.pkg_j       |      35 |       0 |     100% |
| energy.wall_s      |      35 |       0 |     100% |
| energy.rest_j      |      35 |       0 |     100% |
| energy.cpu_bzy_mhz |      35 |       0 |     100% |
| energy.epp         |      35 |       0 |     100% |
| env.start_temp_c   |      35 |       0 |     100% |
| energy.pkg_c_max   |      35 |       0 |     100% |
| pinger             |      35 |       0 |     100% |
| spin               |       0 |      35 |       0% |
| bls                |      21 |      14 |      60% |

---

Generated by `scripts/analyze.py` on 2026-07-22T22:14:08. 203 runs. Do not edit by hand.
