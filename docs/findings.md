# Findings

Hand-written analysis. The generated statistics live in [`results.md`](results.md) and the tidy per-run data in [`../data/results.csv`](../data/results.csv).

**203 runs, 7 reps per arm, all `ok`, all on AC, peak package temperature 74 °C against a 100 °C Tjmax — nothing was thermally throttled and no run was discarded.**

---

## The result in one line

The hypothesis does not fail because the partition is *expensive*. It fails because **the partition does not exist**: on this CPU, EPP is resolved package-wide, so a core set to EPP 255 runs at exactly the same frequency as a core set to EPP 0.

## 1. The partition is not physically real (`e1-rail`)

One spinner pinned to cpu0 ("big"), one to cpu2 ("little"), 20 s, 7 reps.

| arm | cpu0 EPP | cpu2 EPP | cpu0 MHz | cpu2 MHz | little/big | pkg W |
|---|---|---|---|---|---|---|
| both-performance | 0 | 0 | 3588 | 3588 | **1.000** | 13.11 |
| both-balance | 128 | 128 | 3586 | 3586 | **1.000** | 13.04 |
| **partitioned** | **0** | **255** | **3589** | **3589** | **1.000** | 13.10 |
| both-power | 255 | 255 | 951 | 951 | 1.000 | 1.53 |

In the partitioned arm the two cores hold EPP values at opposite ends of the 8-bit range and their busy frequencies agree to **0.03%**. The independent iteration-rate check in `spin` agrees (482.5 vs 483.9 Miter/s, 0.3% apart), so this is not an artefact of the APERF/MPERF path.

EPP itself works: all-255 gives 951 MHz and 1.53 W against 13.10 W, a **8.6× power difference**. It simply is not a per-core control.

Note also that EPP 0 and EPP 128 are within 0.5% of each other under saturating load. On this part the entire useful range of EPP is at the `power` end.

## 2. Why: EPP is resolved package-wide (`e1b-poison`)

The decisive experiment. The probe (cpu2) is held at **EPP 255 in every arm**; only the EPP of the *other seven CPUs* changes, and those CPUs run nothing (measured 0.1–1.0% busy).

| idle CPUs' EPP | probe MHz | sd | pkg W |
|---|---|---|---|
| `power` (255) | 1200 | 8.5 | 1.40 |
| `balance_power` (192) | 2269 | 14.0 | 2.98 |
| `balance_performance` (128) | 3596 | 0.5 | 8.31 |
| `performance` (0) | 3598 | 0.7 | 8.34 |

**+2398 MHz, 95% CI [+2392, +2404], a 3.00× swing** — driven entirely by the EPP of cores that are executing nothing at all.

The obvious alternative explanation is excluded by the register dump. The probe's `IA32_HWP_REQUEST` is `[min=4, max=40, desired=0, epp=255]` in **both** the 1200 MHz and the 3598 MHz arms — an identical min/max window against `HWP_CAPABILITIES [highest=40, guaranteed=18, most_efficient=13, lowest=1]`. The window did not move. Only other cores' EPP did.

This is the documented behaviour of Intel **client** parts: per-core P-states are a server (Xeon) feature, and client SKUs run all cores from one clock domain, with the PCU resolving every logical processor's HWP request to a single package-wide operating point biased toward the most performance-hungry requester. The i7-8550U has four *thermally* distinct cores and one *frequency* domain.

## 3. The scheme has a real cost (`e2-coupling`)

Under load, partitioned and flat EPP are indistinguishable — as they must be, given §1:

| condition | partitioned W | flat W | delta |
|---|---|---|---|
| little1 | 8.34 | 8.36 | −0.02 |
| little4 | 15.41 | 15.43 | −0.02 |
| big1+little4 | 17.10 | 17.07 | +0.02 |

All deltas are within run-to-run noise. But at idle the partition is not free:

| | partitioned | flat |
|---|---|---|
| idle package power | **0.860 W** | **0.596 W** |

**+0.264 W, 95% CI [+0.194, +0.341], +44%.** Setting half the CPUs to `performance` raises idle package power by nearly half, and buys nothing, because the frequency of a busy core is set by the package anyway.

## 4. The A/B confirms it end-to-end (`e3-ab`)

`make -j8` plus a 100 Hz latency-sensitive task.

| arm | wall s | pkg J | vs control | wake p99 µs | work p50 µs |
|---|---|---|---|---|---|
| eevdf-flat (control) | 26.09 | 589.4 | — | 1679 | 660 |
| eevdf-partitioned | 26.01 | 593.2 | not detectable | 1773 | 669 |
| scx-flat | 26.44 | 594.6 | not detectable | 7300 | 670 |
| scx-partitioned | 26.29 | 600.7 | **+1.9%** | 7292 | 674 |
| scx-partitioned-strict | 28.92 | 631.1 | **+7.1%** | 2347 | 825 |

- **No arm saves energy.** With n=7 the minimum detectable effect is 1.7–2.0% of control energy, so a big.LITTLE-scale saving (tens of percent) would have been unmissable. The honest statement is a bound, not a zero: *no effect larger than ~2% exists, and nothing smaller was resolvable here.*
- **Enforcing the partition costs 7.1% energy and 11% wall time.** `--strict` disables cross-domain stealing, which is the honest big.LITTLE behaviour; the cost is idle CPUs sitting next to a runnable queue for no thermodynamic gain.
- **My scheduler is worse at latency than EEVDF**, by 4.3× at p99 (7300 vs 1679 µs), and that is a property of `bls`, not of the partition — `scx-flat` and `scx-partitioned` are identical on it. EEVDF has had a decade of tuning on exactly this; a few hundred lines of BPF has not.

## What this says about the model

`sim/rail_model.py` predicted rejection, and rejection is what happened — but **the model's stated mechanism was wrong**, and it was wrong in a way worth recording.

The model assumed per-core clock domains existed and that the *shared voltage rail* was what destroyed the saving (predicting a 4.7× rail tax, 69–77% of the benefit retained). The hardware fails one level earlier than that: there are no per-core clock domains to begin with, so the rail argument never gets a chance to apply. The measured ratio is 1.000, not the 0.2-ish the model implied.

The model's line `per-core CLOCK domains exist -> EPP does change per-core frequency` is the assumption that broke. It was tagged as structural fact; it is true of Xeon and false of this part.

The prediction was right for the wrong reason. That is a weaker result than being right for the right reason, and pretending otherwise would be the most tempting error available here.

## Threats to validity

- **Run-order drift (gate FAILED).** `core_j` rises monotonically ~1.1% across reps within an arm (Spearman rho up to +0.96) while `rest_j` falls ~12%. Package total is stable to 0.3%, so this is a redistribution *within* the package rather than drift in the headline metric, and it is far below the effects being claimed (1.000 vs 0.33 frequency ratios). It is left flagged rather than suppressed. The likely cause is fan/SA state settling over a session; a longer settle or randomised rep order within arm would test that.
- **Single machine, single microarchitecture.** Everything here is about Kaby Lake-R client silicon.
- **n=7.** Adequate for the 3× and 8.6× effects; marginal for anything under 2%.
- **`--strict` and latency**: `bls` is a deliberately simple scheduler, so its latency numbers should not be read as a limit on what sched_ext can do.

## What would actually save energy here

The data points at the answer directly: the only knob that moved package power was the **most performance-biased EPP anywhere in the package** (§2). So the effective control on this hardware is a **global** one — lower EPP everywhere, or cap the package — not a partition. That is exactly the conclusion the [predecessor audit](https://github.com/yzia2000/linux-laptop-power-audit) reached from the other direction, and this repo is the negative result that closes off the obvious next idea.

Hardware where the question is live again: Alder Lake and later (real P/E cores), Xeon (per-core P-states), and anything with per-cluster rails. The scheduler in this repo runs there unmodified.
