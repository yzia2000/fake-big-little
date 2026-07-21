# fake-big-little

A sched_ext BPF scheduler that partitions a homogeneous Intel laptop CPU into "big" and "little" core sets by per-core EPP, plus the measurement harness to find out whether that actually saves energy.

> **Preface.** This is a direct sequel to [**linux-laptop-power-audit**](https://github.com/yzia2000/linux-laptop-power-audit), which audited Linux power management on this same Lenovo YOGA 920 (i7-8550U, Kaby Lake-R) and found that after a decade of kernel progress exactly one knob still mattered: **EPP**, the 8-bit energy/performance hint in `IA32_HWP_REQUEST`, worth 43% performance and 43% energy under sustained load and nothing at all at idle.
>
> That result raises an obvious follow-up. EPP is a **per-logical-CPU** register. If one EPP value is worth 43%, can you set *different* EPP values on different cores, schedule throughput work onto the fast set and background work onto the slow set, and synthesise ARM's big.LITTLE on hardware that does not have it?
>
> This repo builds that scheduler and measures it. The short answer is no, and the interesting part is exactly *how much* of "no" is attributable to which physical mechanism.

---

## The hypothesis, stated so it can be killed

- **H1:** on a homogeneous Intel package, per-core EPP + QoS-aware task placement reproduces big.LITTLE's energy behaviour.
- **The mechanism H1 requires:** that a core set to EPP 255 actually runs slower *and cheaper* than a core set to EPP 0, at the same time, in the same package.
- **The reason to doubt it:** Skylake removed the on-package FIVR. Kaby Lake-R has **per-core clock domains but one shared VccCore rail**, so `V_rail = V(max active core frequency)`. Dynamic power is `C·V²·f`. A partition buys you the `f` term on the little cores. It does not buy you `V²`, because the big core is holding the rail up. Leakage, which scales worse than linearly in V, is not bought either. And the System Agent / ring / IMC floor is not under EPP control at all.
- **Prediction, therefore:** the partition is *physically real* (frequencies do diverge) but *economically thin* (the savings are a fraction of what a real cluster split would give), and on a 15 W part the PL1 package cap is already doing globally what big.LITTLE does per-cluster.

## Design of the experiment

Three experiments, ordered so that each one can invalidate the next:

| | Question | Kills the next stage if |
|---|---|---|
| **e1-rail** | Does per-core EPP produce divergent per-core clocks at all? | `little_MHz / big_MHz ≈ 1.0` — then the "partition" is a label with no physics behind it |
| **e2-coupling** | What does a light thread cost alone vs. alongside a turbo thread? | the two are equal — then there is no shared rail and the whole premise is wrong |
| **e3-ab** | Full 2×2: `{EEVDF, scx_bls} × {flat EPP, partitioned EPP}` on `make -j8` + a latency-sensitive task | — |

**The 2×2 is the load-bearing design choice.** A one-factor A/B ("my scheduler vs. the default") cannot distinguish an effect caused by the *placement policy* from one caused by the *EPP setting*, and the honest prior is that essentially all of it is the EPP setting. Crossing the factors is what makes the answer attributable.

Control arms are deliberate, not decorative:
- `eevdf-flat` — the machine as shipped.
- `scx-flat` — the same BPF scheduler with `--flat`, i.e. **identical code path, partitioning disabled**. Isolates "cost of running a custom scheduler" from "benefit of partitioning".
- `scx-partitioned-strict` — no cross-domain work stealing. Big.LITTLE-honest and deliberately worse for throughput; it is the arm that actually prices the partition.

## What is in here

**Scheduler** (C + BPF, no C++, therefore no package manager):
- `src/bls.bpf.c` — the sched_ext scheduler. Two DSQs, one per domain. Tasks classified by comm-prefix rule, by EWMA of continuous on-CPU slice length, or both. Hysteresis on reclassification. `--strict` disables work stealing so the partition is enforced rather than advisory.
- `src/bls.c` — loader. Applies EPP, and before anything else **checks the partition against the SMT topology** and **reads `IA32_HWP_REQUEST` back over `/dev/cpu/N/msr`** to confirm what the PCU was actually programmed with. sysfs accepting a write is not evidence the hardware took it.
- Written against the sched_ext ABI **dumped from the running kernel's BTF**, not against documentation. `make` regenerates `vmlinux.h` from `/sys/kernel/btf/vmlinux` on every clean build.

**Measurement** (C):
- `src/energy.c` — RAPL sampler wrapping a workload. Unwraps the 32-bit counters, reports `package-0`, `core`, `uncore`, `dram`, `psys` **and the residual** (`rest = package − core − uncore`, the part EPP cannot touch). Per-CPU frequency from APERF/MPERF/TSC, with `bzy_mhz` (aperf/mperf, clock *while running*) reported separately from `avg_mhz` (aperf/tsc) — only the former answers "did the little core actually clock down".
- `src/pinger.c` — the light task. Reports `wake_us` (scheduling latency) *and* `work_us` (service time for a fixed work quantum) separately, so "the interactive task got starved" and "the interactive task got a slow core" are not conflated. Calibrated at full clock after a 300 ms warm burn, so `work_us / target_work_us` is a direct clock ratio.
- `src/spin.c` — places a known load on exactly known CPUs, and reports an iteration rate that is an *independent* frequency estimate. If it disagrees with the MSR path, the run is void.

**Harness** (Python, stdlib only):
- `scripts/workload.py` — generates the compile workload. Hermetic: fixed seed, no network, no distro drift. 512 TUs so `-j8` stays fed to the end.
- `scripts/bench.py` — randomised interleaved run order, cooldown to a fixed package temperature before every run, EPP saved and restored in a `finally`, every tool's JSON stored verbatim.
- `scripts/analyze.py` — BCa bootstrap CIs, permutation tests, Hedges' g, and **minimum detectable effect**. Data-quality gates (thermal spread across arms, AC/battery consistency, throttling, run-order drift) and **placement sanity** gates. A failing gate turns an apparent win into "not admissible" rather than a headline.
- `sim/rail_model.py` — the shared-rail power model, run **before** touching hardware so the measurement has something falsifiable to hit.

## Model predictions (before measurement)

`python3 sim/rail_model.py` — every constant tagged `[ARK]` (published spec), `[PUB]` (derivable for the class) or `[ASSUME]` (calibrate me), and `--calibrate` fits the assumed ones against measured samples.

- **Rail tax.** With one core at 4.0 GHz the rail sits at 1.150 V. A "little" thread at 800 MHz that would cost **0.190 W** on its own 0.680 V rail costs **0.899 W** here — **4.7×**. Split: 2.9× on dynamic (V²), 8.1× on leakage (exp V).
- Across 1–7 light threads, EPP partitioning retains only **69–77%** of the energy saving a true LITTLE cluster would deliver.
- **Race-to-idle.** The energy-optimal frequency for fixed work is **0.85 GHz, not `f_min`**; running at 400 MHz costs **+20.5%** energy for the same work, because the uncore floor is 43% of package power down there.
- **Topology.** 8 logical CPUs, **4 tunable frequency domains**. An EPP=255 CPU is silently overridden whenever its SMT sibling goes busy — which is why the loader refuses to split a physical core across domains.
- The model does **not** predict that the shared rail collapses the optimum to an endpoint; on a compile-dominated mix with PL1 applied it still finds an interior optimum, for reasons that are *not* voltage. That is written up in the tool's own output rather than smoothed over.

## Status

Hardware measurements are not yet collected. `data/` is empty by design — no numbers are quoted in this README that did not come out of the model, and the model's numbers are labelled as such. Results, once taken, land in `data/results.csv` and `docs/results.md`, both generated.

## Reproducing

Requires: Linux ≥ 6.12 with `CONFIG_SCHED_CLASS_EXT=y` and `CONFIG_DEBUG_INFO_BTF=y`, `intel_pstate` in active mode with `hwp_epp`, clang, libbpf, bpftool, root.

```sh
make                                    # builds bls, energy, pinger, spin
python3 scripts/workload.py             # generate the compile workload
python3 sim/rail_model.py               # predictions, no hardware needed

sudo modprobe msr
sudo python3 scripts/bench.py all --reps 7
python3 scripts/analyze.py --mde
```

`bench.py` refuses to start on battery unless told otherwise, refuses to run if another sched_ext scheduler is loaded, and restores EPP even if it crashes.

## Scope

Single machine, single microarchitecture. The conclusion is about **Kaby Lake-R's power delivery topology**, not about sched_ext, not about big.LITTLE, and not about Intel generally. Parts with per-core FIVR, per-cluster rails, or genuinely heterogeneous cores (Alder Lake and later) will not behave like this — on those, the same scheduler is asking a real question.

## Licence

GPL-2.0 for the scheduler and tools (sched_ext BPF programs must be GPL-compatible to call the kfuncs). MIT for the Python.
