# fake-big-little

A sched_ext BPF scheduler that partitions a homogeneous Intel laptop CPU into "big" and "little" core sets by per-core EPP, plus the measurement harness to find out whether that saves energy. **It does not, and the reason is more fundamental than expected.**

> **Preface.** This is a direct sequel to [**linux-laptop-power-audit**](https://github.com/yzia2000/linux-laptop-power-audit), which audited Linux power management on this same Lenovo YOGA 920 (i7-8550U, Kaby Lake-R) and found that after a decade of kernel progress exactly one knob still mattered: **EPP**, the 8-bit energy/performance hint in `IA32_HWP_REQUEST`, worth 43% performance and 43% energy under sustained load and nothing at all at idle.
>
> That result raises an obvious follow-up. EPP is a **per-logical-CPU** register. If one EPP value is worth 43%, can you set *different* EPP values on different cores, schedule throughput work onto the fast set and background work onto the slow set, and synthesise ARM's big.LITTLE on hardware that does not have it?
>
> This repo builds that scheduler and measures it. The answer is no — and the interesting part is that it fails one level below where the theory said it would.

---

## Findings

**203 runs · 7 reps per arm · zero failed runs · all on AC · peak 74 °C against a 100 °C Tjmax.** Nothing throttled, nothing discarded.

- **The partition does not exist.** Two cores holding opposite ends of the 8-bit EPP range (0 and 255) ran at **3589 MHz and 3589 MHz** — a little/big frequency ratio of **1.000**, agreeing to 0.03% on two independent measurement paths.
- **A busy core's clock is set by the EPP of cores running nothing.** Holding one core at EPP 255 and changing *only the idle cores' EPP* moved it **1200 → 3598 MHz — a 3.00× swing** (95% CI [+2392, +2404] MHz). The busy core's own `HWP_REQUEST` never changed.
- **EPP is resolved package-wide, not per core.** The i7-8550U has four thermally distinct cores and **one frequency domain**. Per-core P-states are a Xeon feature; this is a client part.
- **EPP itself works fine** — all cores at 255 gives 951 MHz / 1.53 W versus 13.10 W, an **8.6× power swing**. It is simply a *package* control wearing a per-CPU register's clothing.
- **The scheme has a real cost and zero benefit:** **+44% idle power** for the partition, **+7.1% energy and +11% wall time** for enforcing it. No arm saved energy in any configuration.
- **The prediction was right for the wrong reason.** The pre-registered model blamed the shared voltage rail. The hardware fails *before* that argument applies. See [below](#the-model-was-right-for-the-wrong-reason).

**[Full analysis →](docs/findings.md)** · [generated statistics](docs/results.md) · [per-run data (203 runs)](data/results.csv)

---

## Evidence

### 1. The partition is not physically real — `e1-rail`

One spinner pinned to cpu0 ("big"), one to cpu2 ("little"), 20 s × 7 reps.

| arm | cpu0 EPP | cpu2 EPP | cpu0 MHz | cpu2 MHz | little/big | pkg W |
|---|---|---|---|---|---|---|
| both-performance | 0 | 0 | 3588 | 3588 | 1.000 | 13.11 |
| both-balance | 128 | 128 | 3586 | 3586 | 1.000 | 13.04 |
| **partitioned** | **0** | **255** | **3589** | **3589** | **1.000** | 13.10 |
| both-power | 255 | 255 | 951 | 951 | 1.000 | 1.53 |

- The partitioned arm holds EPP values at opposite extremes and the clocks agree to **0.03%**.
- `spin`'s iteration-rate check agrees independently (482.5 vs 483.9 Miter/s, 0.3% apart) — not an APERF/MPERF artefact.
- EPP 0 and EPP 128 are within 0.5% of each other under load. On this part the whole useful range of EPP sits at the `power` end.

### 2. Why — `e1b-poison`

The decisive experiment, added *after* e1 came back at 1.000. The probe (cpu2) is held at **EPP 255 in every arm**; only the other seven CPUs' EPP changes, and those run nothing (measured 0.1–1.0% busy).

| idle CPUs' EPP | probe MHz | sd | pkg W |
|---|---|---|---|
| `power` (255) | 1200 | 8.5 | 1.40 |
| `balance_power` | 2269 | 14.0 | 2.98 |
| `balance_performance` | 3596 | 0.5 | 8.31 |
| `performance` (0) | 3598 | 0.7 | 8.34 |

- **3.00×, driven entirely by cores executing nothing.**
- The obvious alternative — that the min/max window pinned the clock — is **excluded by the register dump**: the probe's `IA32_HWP_REQUEST` is `[min=4, max=40, desired=0, epp=255]` in *both* the 1200 MHz and 3598 MHz arms, against `HWP_CAPABILITIES [highest=40, guaranteed=18, most_efficient=13, lowest=1]`. The window did not move; only other cores' EPP did.

### 3. The cost of the scheme — `e2-coupling`

Under load, partitioned and flat EPP are indistinguishable (all deltas within noise), exactly as §1 requires:

| condition | partitioned W | flat W | delta |
|---|---|---|---|
| little1 | 8.34 | 8.36 | −0.02 |
| little4 | 15.41 | 15.43 | −0.02 |
| big1+little4 | 17.10 | 17.07 | +0.02 |

But at idle the partition is not free:

| | partitioned | flat | delta |
|---|---|---|---|
| idle package power | **0.860 W** | **0.596 W** | **+44%**, 95% CI [+0.194, +0.341] W |

### 4. End-to-end A/B — `e3-ab`

`make -j8` plus a 100 Hz latency-sensitive task. Control is `eevdf-flat` (the machine as shipped).

| arm | wall s | pkg J | vs control | wake p99 µs | work p50 µs |
|---|---|---|---|---|---|
| eevdf-flat *(control)* | 26.09 | 589.4 | — | 1679 | 660 |
| eevdf-partitioned | 26.01 | 593.2 | not detectable | 1773 | 669 |
| scx-flat | 26.44 | 594.6 | not detectable | 7300 | 670 |
| scx-partitioned | 26.29 | 600.7 | **+1.9%** | 7292 | 674 |
| scx-partitioned-strict | 28.92 | 631.1 | **+7.1%** | 2347 | 825 |

- **No arm saves energy.** With n=7 the minimum detectable effect is 1.7–2.0% of control energy — a big.LITTLE-scale saving (tens of percent) would have been unmissable.
- **Enforcing the partition costs 7.1% energy and 11% wall time.** `--strict` disables cross-domain stealing, which is the honest big.LITTLE behaviour; the cost is idle CPUs sitting next to a runnable queue for no thermodynamic gain.
- **`bls` is 4.3× worse than EEVDF at wake p99** (7300 vs 1679 µs). That is a property of *my scheduler*, not of the partition — `scx-flat` and `scx-partitioned` are identical on it. EEVDF has had a decade of tuning; a few hundred lines of BPF has not.

---

## Conclusions

- **Software cannot synthesise big.LITTLE on this hardware.** Not "inefficiently" — *at all*. The knob the scheme is built on is not per-core, so there is no partition to schedule against. Every downstream design decision (task classification, domain DSQs, strict placement) is scheduling against a distinction the silicon does not implement.
- **The only control that moved package power was the most performance-biased EPP anywhere in the package.** So the effective knob on this machine is **global** — lower EPP everywhere, or cap the package — not a partition. That is the same conclusion the [predecessor audit](https://github.com/yzia2000/linux-laptop-power-audit) reached from the opposite direction; this repo is the negative result that closes off the obvious next idea.
- **"Per-CPU register" does not imply "per-CPU effect."** `IA32_HWP_REQUEST` is architecturally per-logical-processor and *documented* as such. It is resolved package-wide on client silicon. Reading back the register you wrote confirms the write, not the behaviour — only a frequency measurement does.
- **The failure is in power delivery topology, not in sched_ext.** The scheduler works: verifier-clean, attaches, schedules real work, 0 rejected tasks. It is asking a question this CPU cannot answer.
- **Where the question is live again:** Alder Lake and later (real P/E cores), Xeon (per-core P-states), and anything with per-cluster rails. The scheduler in this repo runs there unmodified.

### The model was right for the wrong reason

`sim/rail_model.py` was written and run **before any hardware was touched**, and it predicted rejection — blaming the **shared voltage rail**: a 4.7× rail tax on each "little" thread, 69–77% of big.LITTLE's benefit destroyed.

The hardware fails one level earlier. The rail argument presupposes that per-core clock domains exist and that the shared rail then erases the benefit. There are no per-core clock domains here, so the argument never gets to apply. The model's assumption line — `per-core CLOCK domains exist -> EPP does change per-core frequency` — was tagged as structural fact. It is true of Xeon and false of this part.

**Predicted outcome: correct. Predicted mechanism: wrong.** `sim/rail_model.py` is left unedited so the two can be compared; retrofitting it to match the measurement would have destroyed the only evidence of what was actually believed beforehand.

### Limitations

- **Run-order drift — a quality gate is left FAILING rather than suppressed.** `core_j` rises ~1.1% monotonically across reps within an arm (Spearman rho up to +0.96) while `rest_j` falls ~12%; package total is stable to 0.3%. It is a redistribution *inside* the package, orders of magnitude below a 3.00× effect, but it is flagged in the generated report where a reader will hit it.
- **Single machine, single microarchitecture.** Everything here is about Kaby Lake-R client silicon.
- **n=7** — ample for the 3.00× and 8.6× effects, marginal for anything under 2%. The honest headline on energy is a *bound*, not a zero.
- **`bls` is a deliberately simple scheduler.** Its latency numbers bound this implementation, not sched_ext.

---

## Design of the experiment

Four experiments, ordered so each can invalidate the next. `e1b` was not in the original design — it exists because `e1` returned a result that needed explaining:

| | Question | Kills the next stage if |
|---|---|---|
| **e1-rail** | Does per-core EPP produce divergent per-core clocks at all? | ratio ≈ 1.0 — the "partition" is a label with no physics behind it. **This is what happened.** |
| **e1b-poison** | Whose EPP sets a busy core's clock — its own, or the package's? | added post-hoc to isolate the mechanism |
| **e2-coupling** | What does a light thread cost alone vs. alongside a turbo thread? | the two are equal — then there is no shared rail either |
| **e3-ab** | Full 2×2: `{EEVDF, scx_bls} × {flat EPP, partitioned EPP}` on `make -j8` + a latency-sensitive task | — |

**The 2×2 is the load-bearing design choice.** A one-factor A/B ("my scheduler vs. the default") cannot distinguish an effect caused by the *placement policy* from one caused by the *EPP setting*. Crossing the factors is what makes the answer attributable.

Control arms are deliberate, not decorative:
- `eevdf-flat` — the machine as shipped.
- `scx-flat` — the same BPF scheduler with `--flat`: **identical code path, partitioning disabled**. Isolates "cost of running a custom scheduler" from "benefit of partitioning".
- `scx-partitioned-strict` — no cross-domain work stealing. Big.LITTLE-honest and deliberately worse for throughput; the arm that actually prices the partition.

### The pre-registered hypothesis

*Left unedited. The third bullet's premise is the part the hardware refuted.*

- **H1:** on a homogeneous Intel package, per-core EPP + QoS-aware placement reproduces big.LITTLE's energy behaviour.
- **What H1 requires:** a core at EPP 255 runs slower *and cheaper* than a core at EPP 0, at the same time, in the same package.
- **The reason to doubt it:** Skylake removed the on-package FIVR. Kaby Lake-R has per-core clock domains but one shared VccCore rail, so `V_rail = V(max active core frequency)`. A partition buys the `f` term on the little cores but not `V²`, because the big core holds the rail up.
- **Prediction:** the partition is *physically real* but *economically thin*.

## What is in here

**Scheduler** (C + BPF — no C++, therefore no package manager):
- `src/bls.bpf.c` — the sched_ext scheduler. Two DSQs, one per domain. Tasks classified by comm-prefix rule, by EWMA of continuous on-CPU slice, or both. Hysteresis on reclassification. `--strict` enforces the partition rather than advising it.
- `src/bls.c` — loader. Applies EPP, **checks the partition against SMT topology** (siblings share a clock domain, so splitting a core across domains is meaningless) and **reads `IA32_HWP_REQUEST` back over `/dev/cpu/N/msr`**. sysfs accepting a write is not evidence the hardware took it.
- Built against the sched_ext ABI **dumped from the running kernel's BTF**, not from documentation. `make` regenerates `vmlinux.h` from `/sys/kernel/btf/vmlinux`.

**Measurement** (C):
- `src/energy.c` — RAPL sampler wrapping a workload. Unwraps the 32-bit counters; reports `package-0`, `core`, `uncore`, `dram`, `psys` **and the residual** (`rest = package − core − uncore`, the part EPP cannot touch), plus the full HWP request/capabilities per CPU. Frequency from APERF/MPERF/TSC, with `bzy_mhz` (clock *while running*) separate from `avg_mhz`.
- `src/pinger.c` — the light task. Reports `wake_us` (scheduling latency) and `work_us` (service time for fixed work) **separately**, so "starved" and "given a slow core" are not conflated.
- `src/spin.c` — places known load on exactly known CPUs; its iteration rate is an *independent* frequency estimate. If it disagrees with the MSR path, the run is void.

**Harness** (Python, stdlib only):
- `scripts/workload.py` — hermetic compile workload: fixed seed, no network, no distro drift, 512 TUs so `-j8` stays fed to the end.
- `scripts/bench.py` — randomised interleaved run order, cooldown calibrated to the machine's measured idle temperature floor, EPP restored in a `finally`, every tool's JSON stored verbatim.
- `scripts/analyze.py` — BCa bootstrap CIs, permutation tests, Hedges' g, **minimum detectable effect**, and quality gates (thermal spread, AC/battery consistency, throttling, run-order drift, placement sanity). A failing gate turns an apparent win into "not admissible" rather than a headline.
- `sim/rail_model.py` — the shared-rail power model, run **before** hardware so the measurement had something falsifiable to hit. Every constant tagged `[ARK]` (published spec), `[PUB]` (derivable) or `[ASSUME]` (calibrate me).

## Reproducing

Requires Linux ≥ 6.12 with `CONFIG_SCHED_CLASS_EXT=y` and `CONFIG_DEBUG_INFO_BTF=y`, `intel_pstate` in active mode with `hwp_epp`, clang, libbpf, bpftool, and root.

```sh
make                                    # builds bls, energy, pinger, spin
python3 scripts/workload.py             # generate the compile workload
python3 sim/rail_model.py               # predictions, no hardware needed

sudo modprobe msr
sudo ./scripts/selftest.sh              # verifier check: loads, runs, unloads
sudo python3 scripts/bench.py all --reps 7 --plan-only   # time estimate first
sudo python3 scripts/bench.py all --reps 7               # ~2 h, 203 runs
python3 scripts/analyze.py --mde
```

`bench.py` refuses to start on battery unless told otherwise, refuses to run if another sched_ext scheduler is loaded, and restores EPP even if it crashes.

## Scope

Single machine, single microarchitecture. The conclusion is about **Kaby Lake-R's frequency-domain topology** — not about sched_ext, not about big.LITTLE as a design, and not about Intel generally. Parts with per-core P-states, per-cluster rails, or genuinely heterogeneous cores will not behave like this.

## Licence

GPL-2.0 for the scheduler and tools (sched_ext BPF programs must be GPL-compatible to call the kfuncs). MIT for the Python.
