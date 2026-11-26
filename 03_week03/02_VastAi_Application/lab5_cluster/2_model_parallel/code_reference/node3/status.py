#!/usr/bin/env python3
"""Print status of the 3 nodes and write state/n<N>.json (ssh host/port, public ip, mapped ports)."""
import json, subprocess, os, time, sys
os.chdir(os.path.dirname(os.path.abspath(__file__)))
os.environ["PATH"] += ":" + os.path.expanduser("~/.local/bin")
for n in (1, 2, 3):
    f = f"state/n{n}.id"
    if not os.path.exists(f): continue
    iid = open(f).read().strip()
    d = json.loads(subprocess.check_output(["vastai", "show", "instance", iid, "--raw"]))
    ports = d.get("ports") or {}
    def hp(k):
        v = ports.get(k); return int(v[0]["HostPort"]) if v else None
    info = dict(node=n, id=int(iid), label=d.get("label"), status=d.get("actual_status"),
                msg=(d.get("status_msg") or "")[:80].strip(), ip=d.get("public_ipaddr"),
                ssh_port=hp("22/tcp"), port9000=hp("9000/tcp"), geo=d.get("geolocation"),
                dph=round(d.get("dph_total") or 0, 4), gpu=f'{d.get("num_gpus")}x {d.get("gpu_name")}',
                cpu_eff=d.get("cpu_cores_effective"), machine=d.get("machine_id"), host=d.get("host_id"),
                inet_down=d.get("inet_down"), inet_up=d.get("inet_up"),
                age_s=int(time.time() - int(open(f"state/n{n}.created").read())))
    json.dump(info, open(f"state/n{n}.json", "w"), indent=1)
    print(json.dumps(info))
