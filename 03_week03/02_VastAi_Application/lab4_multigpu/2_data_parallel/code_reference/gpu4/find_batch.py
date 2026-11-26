"""Find the largest batch per GPU: try 1, 2, 4, 8, ... (3 DDP steps each, longest sample) until Out of Memory.

Every size runs as a fresh torchrun job so that GPU memory starts clean.
"""
import glob
import json
import os
import subprocess
import sys

ROOT = "/workspace/lab4_dp4"
OUT = f"{ROOT}/results"
NGPU = int(sys.argv[1]) if len(sys.argv) > 1 else 4
os.makedirs(f"{OUT}/probe", exist_ok=True)
for f in glob.glob(f"{OUT}/probe/*"):
    os.remove(f)

rows, best, b = [], None, 1
while True:
    logf = f"{OUT}/probe/bs{b}.log"
    with open(logf, "w") as lf:
        rc = subprocess.run(["torchrun", "--nproc_per_node", str(NGPU), f"{ROOT}/code/train.py",
                             "--mode", "probe", "--batch-size", str(b)], stdout=lf, stderr=subprocess.STDOUT).returncode
    ok = f"{OUT}/probe/bs{b}.json"
    text = open(logf, errors="replace").read()
    if rc == 0 and os.path.exists(ok):
        rows.append(json.load(open(ok)))
        best = b
        print(f"batch_per_gpu={b}: ok {rows[-1]['nvidia_smi_peak_mib']} MiB", flush=True)
        b *= 2
        continue
    oom = sorted(glob.glob(f"{OUT}/probe/oom_bs{b}_rank*.json"))
    if oom or "out of memory" in text.lower():
        rows.append({"batch_per_gpu": b, "global_batch": b * NGPU, "status": "oom",
                     "oom_ranks": [json.load(open(f))["rank"] for f in oom]})
        print(f"batch_per_gpu={b}: Out of Memory on ranks {rows[-1]['oom_ranks']}", flush=True)
    else:
        rows.append({"batch_per_gpu": b, "status": f"error rc={rc}"})
        print(f"batch_per_gpu={b}: failed for another reason (rc={rc}), see {logf}", flush=True)
    break

json.dump({"ngpu": NGPU, "max_batch_per_gpu": best, "probes": rows}, open(f"{OUT}/batch_probe.json", "w"), indent=1)
print("PROBE_DONE max_batch_per_gpu =", best, flush=True)
sys.exit(0 if best and rows[-1]["status"] == "oom" else 1)
