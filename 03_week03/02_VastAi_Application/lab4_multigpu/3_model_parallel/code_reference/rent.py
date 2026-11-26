#!/usr/bin/env python3
"""เช่าเครื่อง RTX 3090 x2 ที่ถูกที่สุดตามเงื่อนไข (ป้าย vapp-lab4-mp)

ถ้าเกิน 10 นาทีเครื่องยังไม่พร้อม (SSH เข้าไม่ได้) จะลบแล้วเช่าเครื่องถัดไป
ผลลัพธ์เขียนลง results/instance.json (ไม่มีค่า key ใด ๆ)
"""
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
SSH_KEY = "/workspace/vastai_lab/Devtool_SSH/devtoolSSH"
LABEL = "vapp-lab4-mp"
IMAGE = "vastai/pytorch:2.8.0-cuda-12.8.1-py312-24.04-2026-10-23"
DISK = 60
MAX_PRICE = 0.60
READY_TIMEOUT = 600  # 10 นาที
QUERY = (
    "gpu_name=RTX_3090 num_gpus=2 verified=true rentable=true "
    "reliability>=0.95 inet_down>=700 inet_down_cost<=0.01 "
    "cpu_cores_effective>=16 cuda_max_good>=12.8 "
    f"disk_space>={DISK} geolocation notin [CN]"
)


def vast(*args, raw=True):
    cmd = ["vastai", *args] + (["--raw"] if raw else [])
    p = subprocess.run(cmd, capture_output=True, text=True)
    out = p.stdout.strip()
    if raw:
        try:
            return json.loads(out)
        except json.JSONDecodeError:
            return {"_error": (out or p.stderr)[:500]}
    return out


def ssh_ok(host, port):
    p = subprocess.run(
        ["ssh", "-i", SSH_KEY, "-p", str(port), "-o", "StrictHostKeyChecking=no",
         "-o", "UserKnownHostsFile=/dev/null", "-o", "ConnectTimeout=10",
         "-o", "BatchMode=yes", "-o", "LogLevel=ERROR", f"root@{host}",
         "nvidia-smi --query-gpu=name --format=csv,noheader | wc -l"],
        capture_output=True, text=True)
    return p.returncode == 0 and p.stdout.strip() == "2"


def offers():
    res = vast("search", "offers", QUERY, "--storage", str(DISK), "-o", "dph_total")
    if isinstance(res, dict):
        sys.exit(f"search failed: {res}")
    # dph_total รวมค่า disk 60 GB แล้ว
    return [o for o in res if o["dph_total"] <= MAX_PRICE]


def try_offer(o):
    print(f"[rent] offer {o['id']} machine {o['machine_id']} "
          f"${o['dph_total']:.4f}/hr {o['geolocation']}", flush=True)
    res = vast("create", "instance", str(o["id"]), "--image", IMAGE,
               "--disk", str(DISK), "--ssh", "--direct", "--label", LABEL,
               "--cancel-unavail")
    iid = res.get("new_contract") if isinstance(res, dict) else None
    if not iid:
        print(f"[rent] create failed: {res}", flush=True)
        return None
    pub = open(SSH_KEY + ".pub").read().strip()
    vast("attach", "ssh", str(iid), pub, raw=False)
    t0 = time.time()
    while time.time() - t0 < READY_TIMEOUT:
        time.sleep(15)
        info = vast("show", "instance", str(iid))
        st = info.get("actual_status")
        print(f"[rent] {iid} {int(time.time() - t0)}s status={st} "
              f"msg={str(info.get('status_msg'))[:80]!r}", flush=True)
        if st in ("exited", "unknown", "offline"):
            break
        if st == "running":
            # direct ก่อน ถ้าไม่ได้ใช้ proxy
            cands = []
            ports = (info.get("ports") or {}).get("22/tcp")
            if ports and info.get("public_ipaddr"):
                cands.append((info["public_ipaddr"].strip(), int(ports[0]["HostPort"])))
            if info.get("ssh_host"):
                cands.append((info["ssh_host"], int(info["ssh_port"])))
            for host, port in cands:
                if ssh_ok(host, port):
                    return {
                        "instance_id": iid, "offer_id": o["id"],
                        "machine_id": o["machine_id"], "host_id": o["host_id"],
                        "label": LABEL, "image": IMAGE, "disk_gb": DISK,
                        "ssh_host": host, "ssh_port": port,
                        "dph_total": info.get("dph_total", o["dph_total"]),
                        "gpu_name": o["gpu_name"], "num_gpus": o["num_gpus"],
                        "geolocation": o["geolocation"],
                        "cpu_cores_effective": o["cpu_cores_effective"],
                        "cpu_name": o.get("cpu_name"),
                        "inet_down": o["inet_down"],
                        "inet_down_cost": o["inet_down_cost"],
                        "reliability": o["reliability2"],
                        "pci_gen": o.get("pci_gen"), "gpu_lanes": o.get("gpu_lanes"),
                        "ready_seconds": int(time.time() - t0),
                    }
    print(f"[rent] {iid} not ready in time -> destroy", flush=True)
    vast("destroy", "instance", str(iid), "-y", raw=False)
    return None


def main():
    tried = set()
    for _ in range(5):
        cands = [o for o in offers() if o["machine_id"] not in tried]
        if not cands:
            sys.exit("no offers left")
        o = cands[0]
        tried.add(o["machine_id"])
        info = try_offer(o)
        if info:
            os.makedirs(os.path.join(HERE, "results"), exist_ok=True)
            with open(os.path.join(HERE, "results", "instance.json"), "w") as f:
                json.dump(info, f, indent=2)
            print("[rent] READY", json.dumps(info), flush=True)
            return
    sys.exit("gave up after 5 offers")


if __name__ == "__main__":
    main()
