#!/usr/bin/env python3
"""Save cost evidence of the rented machine into results/raw (never stores keys).

  collect_cost.py snapshot   -> results/raw/instance_final.json  (run BEFORE destroying)
  collect_cost.py billing    -> results/raw/billing.json         (charges billed to the instance)
"""
import json
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "results", "raw")
LABEL = "vapp-lab4-mp"
SECRET_WORDS = ("key", "token", "pass", "secret", "env", "onstart", "jupyter")
os.environ["PATH"] += os.pathsep + os.path.expanduser("~/.local/bin")


def vast(*args):
    p = subprocess.run(["vastai", *args, "--raw"], capture_output=True, text=True)
    if p.returncode != 0:
        sys.exit(f"vastai {args[0]} {args[1]} failed (rc={p.returncode})")
    return json.loads(p.stdout)


def scrub(o):
    if isinstance(o, dict):
        return {k: scrub(v) for k, v in o.items()
                if not any(w in k.lower() for w in SECRET_WORDS)}
    if isinstance(o, list):
        return [scrub(v) for v in o]
    return o


def instance_id():
    return json.load(open(os.path.join(ROOT, "results", "instance.json")))["instance_id"]


def snapshot():
    mine = [i for i in vast("show", "instances") if i.get("label") == LABEL]
    if len(mine) != 1:
        sys.exit(f"expected exactly 1 instance labelled {LABEL}, found {len(mine)}")
    inst = scrub(mine[0])
    inst["snapshot_unix"] = time.time()
    inst["age_sec_at_snapshot"] = inst["snapshot_unix"] - inst["start_date"]
    json.dump(inst, open(os.path.join(RAW, "instance_final.json"), "w"), indent=1)
    print(f"instance {inst['id']} label={inst['label']} status={inst['actual_status']} "
          f"age={inst['age_sec_at_snapshot'] / 60:.1f} min dph_total={inst['dph_total']:.4f}")


def billing():
    iid = instance_id()
    res = vast("show", "invoices-v1", "--charges", "-ct", "instance", "-l", "100",
               "--latest-first", "--verbose")
    rows = [scrub(r) for r in res.get("results", []) if r.get("source") == f"instance-{iid}"]
    out = {"instance_id": iid, "label": LABEL, "fetched_unix": time.time(),
           "total_charged_usd": round(sum(r["amount"] for r in rows), 4), "charges": rows}
    json.dump(out, open(os.path.join(RAW, "billing.json"), "w"), indent=1)
    print(f"instance {iid}: {len(rows)} charge row(s), total ${out['total_charged_usd']:.3f}")
    for r in rows:
        for it in r.get("items", []):
            print(f"  {it['type']:5s} ${it['amount']:.3f}  {it['description']}")


if __name__ == "__main__":
    {"snapshot": snapshot, "billing": billing}[sys.argv[1]]()
