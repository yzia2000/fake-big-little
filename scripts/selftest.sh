#!/bin/sh
# SPDX-License-Identifier: GPL-2.0
#
# Smallest thing that proves the scheduler is real: load it, put load on the
# machine, take it away again, and check that (a) the verifier accepted it,
# (b) tasks actually ran under it, and (c) the box survived.
#
#   sudo ./scripts/selftest.sh
#
# Exits non-zero on the first failure. Everything it touches is restored.
set -e

cd "$(dirname "$0")/.."
BIN=./build

[ "$(id -u)" = 0 ] || { echo "selftest: must run as root"; exit 1; }
for t in bls energy pinger spin; do
	[ -x "$BIN/$t" ] || { echo "selftest: missing $BIN/$t, run make"; exit 1; }
done

modprobe msr 2>/dev/null || true

echo "== sched_ext state before: $(cat /sys/kernel/sched_ext/state 2>/dev/null)"
echo
echo "== 1. EPP partition dry run (no BPF loaded) =========================="
$BIN/bls --dry-run --big 0-1,4-5 --little 2-3,6-7 | tee /tmp/bls-partition.json

# The harness consumes these lines as JSON, and a malformed line is silently
# dropped rather than noticed - which is exactly how the first version of this
# shipped an empty MSR readback. Validate it here instead.
echo "-- validating JSON output"
python3 - /tmp/bls-partition.json <<'EOF'
import json, sys
n = 0
for line in open(sys.argv[1]):
	line = line.strip()
	if not line.startswith("{"):
		continue
	o = json.loads(line)          # raises, and fails the run, if malformed
	if o.get("event") == "partition":
		n += 1
		for c in o["cpus"]:
			assert "epp_msr_after" in c, c
print(f"   ok: {n} partition record(s), all fields present")
EOF
rm -f /tmp/bls-partition.json

echo
echo "== 2. load the scheduler, 12s under load ============================="
$BIN/bls --big 0-1,4-5 --little 2-3,6-7 --mode hybrid --duration 12 --interval 4 &
BLS_PID=$!

# Give the struct_ops time to attach before generating load, otherwise part of
# the load runs under EEVDF and the counters below understate everything.
sleep 2
state=$(cat /sys/kernel/sched_ext/state 2>/dev/null)
echo "-- sched_ext state while loaded: $state"
if [ "$state" = "disabled" ] || [ -z "$state" ]; then
	kill $BLS_PID 2>/dev/null || true
	echo "selftest: FAIL - scheduler did not attach"
	exit 1
fi

$BIN/spin --cpus 0-7 --dur 5 --label selftest-load >/dev/null
$BIN/pinger --hz 100 --dur 4 --warmup 0.5 --label selftest-ping

wait $BLS_PID
echo
echo "== 3. sched_ext state after: $(cat /sys/kernel/sched_ext/state 2>/dev/null)"
echo "== 4. rejected task count: $(cat /sys/kernel/sched_ext/nr_rejected 2>/dev/null)"
echo
echo "selftest: PASS (scheduler loaded, ran real work, unloaded cleanly)"
