#!/usr/bin/env python3
"""Experiment driver for fake-big-little.

Runs the three experiments, in increasing order of how much they assume:

  e1-rail      Does per-core EPP actually produce divergent per-core clocks?
               If it does not, the "partition" is a label with no physics
               behind it and e3 cannot mean anything.

  e2-coupling  Given that the package has one core voltage rail, what does a
               light thread cost when it runs alone versus alongside a thread
               at turbo? On a true big.LITTLE SoC these are the same number.
               The gap between them is the rail tax.

  e3-ab        The 2x2: {EEVDF, scx_bls} x {flat EPP, partitioned EPP}, on a
               `make -j8` plus a concurrent latency-sensitive task. Crossing
               the two factors is the point: a one-factor A/B cannot tell you
               whether an observed effect came from the placement policy or
               from the EPP setting, and the honest prior is that all of it
               comes from the EPP setting.

Design decisions that exist to stop the harness lying to itself:

  * Randomised, interleaved run order. Arms are not run in blocks, because
    package temperature and fan state drift monotonically over a session and
    would be perfectly confounded with the arm.
  * Cooldown to a fixed package temperature before every run, with the achieved
    starting temperature recorded so the analysis can check it.
  * The workload tree is built once as a warm-up before measurement starts, so
    no arm pays for cold page cache.
  * Every tool's raw JSON is stored verbatim. Nothing is aggregated at capture
    time; all reduction happens later in analyze.py against the stored files.
  * EPP is saved once at startup and restored in a finally block, including on
    crash, so a failed session cannot leave the machine misconfigured.
"""
import argparse
import glob
import json
import os
import random
import shutil
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD = os.path.join(ROOT, "build")
RAW = os.path.join(ROOT, "data", "raw")

CPU_SYS = "/sys/devices/system/cpu"
EPP_PATH = CPU_SYS + "/cpu{}/cpufreq/energy_performance_preference"

# EPP names. "performance" is EPP 0, "power" is EPP 255. balance_performance
# (EPP 128) is the kernel default on this machine and is the flat baseline that
# the previous audit (linux-laptop-power-audit) landed on.
EPP_BIG = "performance"
EPP_LITTLE = "power"
EPP_FLAT = "balance_performance"


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ------------------------------------------------------------------ system --

def nr_cpus():
    return len(glob.glob(CPU_SYS + "/cpu[0-9]*/topology"))


def topology():
    """cpu -> physical core id."""
    out = {}
    for c in range(nr_cpus()):
        with open(f"{CPU_SYS}/cpu{c}/topology/core_id") as f:
            out[c] = int(f.read())
    return out


def default_partition():
    """Split by *physical core*, keeping SMT siblings together.

    Splitting a core across domains is meaningless: the two hyperthreads share
    one clock domain and the PCU resolves their HWP requests to the more
    performance-biased of the pair. The lower-numbered half of the cores becomes
    big, the rest little.
    """
    topo = topology()
    cores = sorted(set(topo.values()))
    big_cores = set(cores[: max(1, len(cores) // 2)])
    big = [c for c, core in topo.items() if core in big_cores]
    little = [c for c, core in topo.items() if core not in big_cores]
    return sorted(big), sorted(little)


def cpulist(cpus):
    """Render [0,1,4,5] as '0-1,4-5'."""
    if not cpus:
        return ""
    parts, start, prev = [], cpus[0], cpus[0]
    for c in cpus[1:] + [None]:
        if c is not None and c == prev + 1:
            prev = c
            continue
        parts.append(str(start) if start == prev else f"{start}-{prev}")
        start = prev = c
    return ",".join(parts)


def pkg_temp_c():
    """Package temperature from hwmon; None if coretemp is not loaded."""
    for hw in sorted(glob.glob("/sys/class/hwmon/hwmon*")):
        try:
            with open(os.path.join(hw, "name")) as f:
                if f.read().strip() != "coretemp":
                    continue
            for lbl in sorted(glob.glob(os.path.join(hw, "temp*_label"))):
                with open(lbl) as f:
                    if not f.read().strip().lower().startswith("package"):
                        continue
                inp = lbl.replace("_label", "_input")
                with open(inp) as f:
                    return int(f.read()) / 1000.0
        except OSError:
            continue
    return None


def on_ac():
    for p in glob.glob("/sys/class/power_supply/A*/online"):
        try:
            with open(p) as f:
                return f.read().strip() == "1"
        except OSError:
            pass
    return None


def read_epp_all():
    return {c: open(EPP_PATH.format(c)).read().strip() for c in range(nr_cpus())}


def write_epp(cpu, value):
    with open(EPP_PATH.format(cpu), "w") as f:
        f.write(value)


def apply_epp(mapping):
    for cpu, value in mapping.items():
        write_epp(cpu, value)


def current_scx():
    try:
        with open("/sys/kernel/sched_ext/state") as f:
            return f.read().strip()
    except OSError:
        return None


# ------------------------------------------------------------- run helpers --

def collect_json(text):
    """Pull every complete JSON object printed on its own line.

    Each tool in this repo prints exactly one JSON object per line on stdout,
    which lets several of them share a pipe without an IPC protocol.
    """
    out = []
    for line in text.splitlines():
        line = line.strip()
        if not (line.startswith("{") and line.endswith("}")):
            continue
        try:
            out.append(json.loads(line, parse_constant=lambda c: None))
        except json.JSONDecodeError:
            pass
    return out


def classify_json(objs):
    """Route each tool's JSON to a named slot by its distinguishing keys."""
    slots = {"energy": None, "pinger": None, "spin": None, "bls": None,
             "partition": None}
    for o in objs:
        if "pkg_j" in o:
            slots["energy"] = o
        elif "wake_us_p50" in o:
            slots["pinger"] = o
        elif "threads" in o:
            slots["spin"] = o
        elif o.get("event") == "stats":
            slots["bls"] = o
        elif o.get("event") == "partition":
            slots["partition"] = o
    return slots


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


# ------------------------------------------------------------------- bench --

class Bench:
    def __init__(self, args):
        self.args = args
        self.big, self.little = default_partition()
        if args.big:
            self.big = parse_cpulist(args.big)
            self.little = [c for c in range(nr_cpus()) if c not in self.big]
        self.saved_epp = read_epp_all()
        self.idle_floor = None
        self.env = {}
        self.energy = os.path.join(BUILD, "energy")
        self.pinger = os.path.join(BUILD, "pinger")
        self.spin = os.path.join(BUILD, "spin")
        self.bls = os.path.join(BUILD, "bls")
        self.genproj = os.path.join(BUILD, "genproj")

    # -- preflight ---------------------------------------------------------

    def preflight(self):
        problems = []
        if os.geteuid() != 0:
            problems.append("must run as root (RAPL energy_uj and MSRs are privileged)")
        for tool in (self.energy, self.pinger, self.spin):
            if not os.path.exists(tool):
                problems.append(f"missing {tool}: run `make`")
        if self.args.experiment in ("e3-ab", "all") and not os.path.exists(self.bls):
            problems.append(f"missing {self.bls}: run `make` (needs bpftool + libbpf)")
        if not os.path.exists(os.path.join(self.genproj, "Makefile")):
            problems.append("missing workload: run `python3 scripts/workload.py`")
        if not os.path.exists("/dev/cpu/0/msr"):
            problems.append("no /dev/cpu/0/msr: run `modprobe msr`")
        try:
            driver = open(f"{CPU_SYS}/cpu0/cpufreq/scaling_driver").read().strip()
        except OSError:
            driver = None
        if driver != "intel_pstate":
            problems.append(f"scaling_driver is {driver!r}, expected intel_pstate "
                            "(EPP is only settable in intel_pstate active mode)")
        state = current_scx()
        if state and state not in ("disabled", "none"):
            problems.append(f"a sched_ext scheduler is already loaded (state={state})")

        ac = on_ac()
        if ac is False and not self.args.allow_battery:
            problems.append("running on battery: package power and turbo budget "
                            "differ from AC. Pass --allow-battery to override, "
                            "but do not mix AC and battery runs in one dataset.")

        self.env = {
            "kernel": os.uname().release,
            "cpu_model": self._cpu_model(),
            "nr_cpus": nr_cpus(),
            "big_cpus": self.big,
            "little_cpus": self.little,
            "scaling_driver": driver,
            "governor": self._read(f"{CPU_SYS}/cpu0/cpufreq/scaling_governor"),
            "on_ac": ac,
            "epp_at_start": self.saved_epp,
        }
        return problems

    @staticmethod
    def _read(path):
        try:
            with open(path) as f:
                return f.read().strip()
        except OSError:
            return None

    @staticmethod
    def _cpu_model():
        try:
            for line in open("/proc/cpuinfo"):
                if line.startswith("model name"):
                    return line.split(":", 1)[1].strip()
        except OSError:
            pass
        return None

    # -- environment control ----------------------------------------------

    def set_partitioned_epp(self):
        apply_epp({**{c: EPP_BIG for c in self.big},
                   **{c: EPP_LITTLE for c in self.little}})

    def set_flat_epp(self, value=EPP_FLAT):
        apply_epp({c: value for c in range(nr_cpus())})

    def restore_epp(self):
        for cpu, value in self.saved_epp.items():
            try:
                write_epp(cpu, value)
            except OSError:
                pass

    def measure_idle_floor(self):
        """Find the temperature this machine actually settles at when idle.

        A fixed cooldown target is a trap: this laptop idles at 52 C, so a
        hard-coded 50 C target means every single cooldown runs to its timeout
        and never fires, silently turning a 40 minute session into a six hour
        one while looking like it is working. Measure the floor instead and
        aim a small margin above it.
        """
        samples = []
        end = time.time() + self.args.floor_probe
        while time.time() < end:
            t = pkg_temp_c()
            if t is not None:
                samples.append(t)
            time.sleep(1)
        return min(samples) if samples else None

    def cool_target(self):
        if self.idle_floor is None:
            return self.args.cool_to
        return max(self.args.cool_to, self.idle_floor + self.args.cool_margin)

    def cooldown(self):
        """Idle until the package is at or below the target temperature.

        Returns the temperature actually reached. A run that could not cool in
        time is still recorded, with its real starting temperature, so the
        analysis can flag it rather than the harness quietly dropping it.
        """
        target, deadline = self.cool_target(), time.time() + self.args.cool_max
        t = pkg_temp_c()
        while t is not None and t > target and time.time() < deadline:
            time.sleep(2)
            t = pkg_temp_c()
        time.sleep(self.args.settle)
        return pkg_temp_c()

    # -- record ------------------------------------------------------------

    def record(self, experiment, arm, factors, rep, slots, ok, notes="",
               start_temp=None, extra=None):
        rec = {
            "experiment": experiment,
            "arm": arm,
            "factors": factors,
            "rep": rep,
            "timestamp": now_iso(),
            "ok": ok,
            "env": dict(self.env, start_temp_c=start_temp),
            "energy": slots.get("energy"),
            "pinger": slots.get("pinger"),
            "spin": slots.get("spin"),
            "bls": slots.get("bls"),
            "partition": slots.get("partition"),
            "notes": notes,
        }
        if extra:
            rec.update(extra)
        d = os.path.join(RAW, experiment)
        os.makedirs(d, exist_ok=True)
        path = os.path.join(d, f"{arm}.rep{rep:02d}.json")
        with open(path, "w") as f:
            json.dump(rec, f, indent=1)
        status = "ok " if ok else "FAIL"
        e = slots.get("energy") or {}
        print(f"  [{status}] {experiment}/{arm} rep{rep} "
              f"wall={e.get('wall_s', float('nan')):.2f}s "
              f"pkg={e.get('pkg_j', float('nan')):.1f}J "
              f"start={start_temp}C", flush=True)
        return rec

    def csv_path(self, experiment, arm, rep):
        d = os.path.join(RAW, experiment)
        os.makedirs(d, exist_ok=True)
        return os.path.join(d, f"{arm}.rep{rep:02d}.csv")

    # -- e1: is the partition physically real? -----------------------------

    def e1_rail(self, rep):
        """One thread on a big CPU, one on a little CPU, under three EPP configs.

        The measurement that matters is the ratio of the two CPUs' busy
        frequencies. If EPP "performance" and EPP "power" produce the same
        clock, there is no partition.
        """
        probe_big, probe_little = self.big[0], self.little[0]
        arms = [
            ("both-performance", {c: EPP_BIG for c in range(nr_cpus())}),
            ("both-power", {c: EPP_LITTLE for c in range(nr_cpus())}),
            ("both-balance", {c: EPP_FLAT for c in range(nr_cpus())}),
            ("partitioned", {**{c: EPP_BIG for c in self.big},
                             **{c: EPP_LITTLE for c in self.little}}),
        ]
        for name, mapping in arms:
            apply_epp(mapping)
            t = self.cooldown()
            csv = self.csv_path("e1-rail", name, rep)
            p = run([self.energy, "-i", "200", "-o", csv, "--label", name, "--",
                     self.spin, "--cpus", f"{probe_big},{probe_little}",
                     "--dur", str(self.args.dur), "--label", name])
            slots = classify_json(collect_json(p.stdout))
            ok = p.returncode == 0 and slots["energy"] is not None
            self.record("e1-rail", name,
                        {"epp": name, "probe_big": probe_big,
                         "probe_little": probe_little},
                        rep, slots, ok, start_temp=t,
                        notes="one spinner pinned to one CPU of each domain")

    # -- e2: what does the shared rail cost? -------------------------------

    def e2_conditions(self):
        """The placements e2 compares.

        Shared with the run planner rather than duplicated, because the first
        version of this had the planner reporting 22 arms while the experiment
        actually ran 16 - a run-length estimate that disagrees with the run is
        worse than no estimate.
        """
        conditions = [("idle", None)]
        for k in sorted({1, 2, len(self.little)}):
            if k <= len(self.little):
                conditions.append((f"little{k}", cpulist(self.little[:k])))
                conditions.append((f"big1+little{k}",
                                   cpulist(sorted(self.big[:1] + self.little[:k]))))
        conditions.append(("big1", cpulist(self.big[:1])))
        return conditions

    def e2_coupling(self, rep):
        """Marginal cost of light threads, with and without a turbo thread.

        Each condition is a fixed placement, so the difference between
        `littleN` and `big1+littleN` isolates the incremental package power of
        the same little threads under two different rail voltages.
        """
        conditions = self.e2_conditions()

        for epp_name, mapping in (
            ("partitioned", {**{c: EPP_BIG for c in self.big},
                             **{c: EPP_LITTLE for c in self.little}}),
            ("flat", {c: EPP_FLAT for c in range(nr_cpus())}),
        ):
            apply_epp(mapping)
            for cond, cpus in conditions:
                arm = f"{epp_name}.{cond}"
                t = self.cooldown()
                csv = self.csv_path("e2-coupling", arm, rep)
                if cpus is None:
                    cmd = [self.energy, "-i", "200", "-o", csv, "--label", arm,
                           "-t", str(self.args.dur)]
                else:
                    cmd = [self.energy, "-i", "200", "-o", csv, "--label", arm,
                           "--", self.spin, "--cpus", cpus,
                           "--dur", str(self.args.dur), "--label", arm]
                p = run(cmd)
                slots = classify_json(collect_json(p.stdout))
                ok = p.returncode == 0 and slots["energy"] is not None
                self.record("e2-coupling", arm,
                            {"epp": epp_name, "condition": cond, "cpus": cpus},
                            rep, slots, ok, start_temp=t)

    # -- e3: the actual A/B ------------------------------------------------

    E3_ARMS = [
        ("eevdf-flat", {"sched": "eevdf", "epp": "flat", "strict": False}),
        ("eevdf-partitioned", {"sched": "eevdf", "epp": "partitioned", "strict": False}),
        ("scx-flat", {"sched": "scx", "epp": "flat", "strict": False}),
        ("scx-partitioned", {"sched": "scx", "epp": "partitioned", "strict": False}),
        ("scx-partitioned-strict", {"sched": "scx", "epp": "partitioned", "strict": True}),
    ]

    def e3_one(self, arm, factors, rep):
        if factors["epp"] == "partitioned":
            self.set_partitioned_epp()
        else:
            self.set_flat_epp()

        run(["make", "-C", self.genproj, "-s", "clean"])
        t = self.cooldown()

        bls_proc = None
        if factors["sched"] == "scx":
            cmd = [self.bls, "--persist", "--no-epp",
                   "--big", cpulist(self.big), "--little", cpulist(self.little),
                   "--mode", "hybrid"]
            if factors["strict"]:
                cmd.append("--strict")
            bls_proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE, text=True)
            # Wait for the struct_ops to actually attach; loading is not
            # instantaneous and a build started too early would run partly
            # under EEVDF and partly under scx.
            if not self._wait_attached(bls_proc, timeout=10):
                self._kill(bls_proc)
                return self.record("e3-ab", arm, factors, rep,
                                   {"bls": None}, False, start_temp=t,
                                   notes="scheduler failed to attach")

        ping = subprocess.Popen(
            [self.pinger, "--hz", str(self.args.ping_hz), "--dur", "3600",
             "--work-us", str(self.args.ping_work_us), "--warmup", "1",
             "--label", arm],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)

        csv = self.csv_path("e3-ab", arm, rep)
        p = run([self.energy, "-i", "200", "-o", csv, "--label", arm, "--",
                 "make", "-C", self.genproj, "-s", f"-j{nr_cpus()}"])

        ping.send_signal(signal.SIGTERM)
        ping_out, _ = ping.communicate(timeout=30)

        bls_out = ""
        if bls_proc:
            bls_proc.send_signal(signal.SIGTERM)
            try:
                bls_out, bls_err = bls_proc.communicate(timeout=30)
            except subprocess.TimeoutExpired:
                self._kill(bls_proc)
                bls_out, bls_err = "", ""

        slots = classify_json(collect_json(p.stdout + "\n" + ping_out +
                                           "\n" + bls_out))
        ok = (p.returncode == 0 and slots["energy"] is not None
              and slots["energy"].get("exit_code") == 0
              and slots["pinger"] is not None)
        return self.record("e3-ab", arm, factors, rep, slots, ok, start_temp=t)

    @staticmethod
    def _wait_attached(proc, timeout):
        """Block until bls prints its `attached` event, or give up."""
        end = time.time() + timeout
        while time.time() < end:
            if proc.poll() is not None:
                return False
            state = current_scx()
            if state and state not in ("disabled", "none"):
                time.sleep(0.5)
                return True
            time.sleep(0.2)
        return False

    @staticmethod
    def _kill(proc):
        try:
            proc.kill()
            proc.wait(timeout=5)
        except Exception:
            pass

    # -- driver ------------------------------------------------------------

    def plan(self):
        """(experiment, nr_arms, seconds_of_measured_work_per_run)."""
        out = []
        if self.args.experiment in ("e1-rail", "all"):
            out.append(("e1-rail", 4, self.args.dur))
        if self.args.experiment in ("e2-coupling", "all"):
            out.append(("e2-coupling", 2 * len(self.e2_conditions()),
                        self.args.dur))
        if self.args.experiment in ("e3-ab", "all"):
            out.append(("e3-ab", len(self.E3_ARMS), 30.0))
        return out

    def print_plan(self):
        """Say up front how long this will take.

        The cooldown is the dominant term and it is invisible in the arm count,
        which is how a session that looks like "175 short runs" turns into an
        afternoon. Both bounds are printed: the lower assumes cooldown is
        instant, the upper assumes it always times out.
        """
        total_runs = lo = hi = 0
        print("\nplan:")
        for name, arms, secs in self.plan():
            runs = arms * self.args.reps
            per_lo = secs + self.args.settle
            per_hi = secs + self.args.settle + self.args.cool_max
            total_runs += runs
            lo += runs * per_lo
            hi += runs * per_hi
            print(f"  {name:<12} {arms} arms x {self.args.reps} reps = "
                  f"{runs:>3} runs   {runs * per_lo / 60:5.1f}-"
                  f"{runs * per_hi / 60:5.1f} min")
        print(f"  {'total':<12} {'':>16} {total_runs:>3} runs   "
              f"{lo / 60:5.1f}-{hi / 60:5.1f} min\n", flush=True)

    def warmup(self):
        print("warmup: building the workload once to fill page cache", flush=True)
        run(["make", "-C", self.genproj, "-s", "clean"])
        run(["make", "-C", self.genproj, "-s", f"-j{nr_cpus()}"])
        run(["make", "-C", self.genproj, "-s", "clean"])

    def go(self):
        problems = self.preflight()
        if problems:
            for p in problems:
                # --plan-only answers "how long will this take", which is
                # worth answering without root and without a built tree.
                label = "warning" if self.args.plan_only else "preflight"
                print(f"{label}: {p}", file=sys.stderr)
            if not self.args.plan_only:
                return 1

        print(f"machine : {self.env['cpu_model']}")
        print(f"kernel  : {self.env['kernel']}")
        print(f"big     : {cpulist(self.big)}  (EPP {EPP_BIG})")
        print(f"little  : {cpulist(self.little)}  (EPP {EPP_LITTLE})")
        print(f"flat    : all CPUs EPP {EPP_FLAT}")
        print(f"reps    : {self.args.reps}")

        print(f"probing idle temperature floor for "
              f"{self.args.floor_probe:.0f}s ...", flush=True)
        self.idle_floor = self.measure_idle_floor()
        self.env["idle_floor_c"] = self.idle_floor
        self.env["cool_target_c"] = self.cool_target()
        print(f"idle floor : {self.idle_floor} C")
        print(f"cool to    : {self.cool_target():.1f} C "
              f"(max {self.args.cool_max:.0f}s per run)")

        self.print_plan()
        if self.args.plan_only:
            return 0

        self.warmup()

        rng = random.Random(self.args.seed)
        try:
            if self.args.experiment in ("e1-rail", "all"):
                for rep in range(self.args.reps):
                    self.e1_rail(rep)
            if self.args.experiment in ("e2-coupling", "all"):
                for rep in range(self.args.reps):
                    self.e2_coupling(rep)
            if self.args.experiment in ("e3-ab", "all"):
                # Interleave: every rep runs every arm, in a fresh random order.
                for rep in range(self.args.reps):
                    arms = list(self.E3_ARMS)
                    rng.shuffle(arms)
                    for arm, factors in arms:
                        self.e3_one(arm, factors, rep)
        finally:
            self.restore_epp()
            print("\nEPP restored to the values found at startup.")
        return 0


def parse_cpulist(s):
    out = []
    for part in s.split(","):
        if "-" in part:
            a, b = part.split("-")
            out.extend(range(int(a), int(b) + 1))
        else:
            out.append(int(part))
    return sorted(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog=__doc__)
    ap.add_argument("experiment", nargs="?", default="all",
                    choices=["all", "e1-rail", "e2-coupling", "e3-ab"])
    ap.add_argument("--reps", type=int, default=7,
                    help="repetitions per arm; 7 is the floor for a usable "
                         "bootstrap CI on this much run-to-run noise")
    ap.add_argument("--dur", type=float, default=20,
                    help="seconds per fixed-duration run (e1, e2)")
    ap.add_argument("--big", help="override the big CPU list, e.g. 0-1,4-5")
    ap.add_argument("--cool-to", type=float, default=50.0,
                    help="cool the package to this many degrees C before a run")
    ap.add_argument("--cool-max", type=float, default=120.0,
                    help="give up cooling after this many seconds")
    ap.add_argument("--cool-margin", type=float, default=3.0,
                    help="cool to (measured idle floor + this), if that is "
                         "higher than --cool-to")
    ap.add_argument("--floor-probe", type=float, default=10.0,
                    help="seconds spent measuring the idle temperature floor")
    ap.add_argument("--plan-only", action="store_true",
                    help="print the run plan and time estimate, then exit")
    ap.add_argument("--settle", type=float, default=3.0,
                    help="extra idle seconds after cooldown")
    ap.add_argument("--ping-hz", type=float, default=100)
    ap.add_argument("--ping-work-us", type=float, default=500)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--allow-battery", action="store_true")
    args = ap.parse_args()

    return Bench(args).go()


if __name__ == "__main__":
    sys.exit(main())
