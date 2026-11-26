#!/usr/bin/env python3
"""Rent 2 nodes (2x RTX 3090 each) on Vast.ai for the data-parallel lab.

Selection rule: among offers meeting every condition, pick the pair of machines
with different public IPs that is nearest (same country > same continent > other)
and, inside that tier, has the lowest total price.
A node that is not usable (running + SSH answers) within 10 minutes is destroyed
and replaced by the next best offer near the surviving node.
The API key is only ever read by the vastai CLI itself; it is never printed.
"""
import json, os, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
VASTAI = os.environ.get("VASTAI", "/root/.local/bin/vastai")
SSH_KEY = "/workspace/vastai_lab/Devtool_SSH/devtoolSSH"
IMAGE = "pytorch/pytorch:2.8.0-cuda12.8-cudnn9-runtime"
DISK = 60
MAX_DPH = 0.60
NODE1_PORT = 5201          # the one port Node 1 exposes to the outside
LABELS = ["vapp-lab5-dp-1", "vapp-lab5-dp-2"]
READY_TIMEOUT = 600        # 10 minutes
QUERY = ("gpu_name=RTX_3090 num_gpus=2 verified=true rentable=true reliability>=0.95 "
         "inet_down>=700 inet_down_cost<=0.01 cpu_cores_effective>=16 "
         f"dph_total<={MAX_DPH} cuda_max_good>=12.8 direct_port_count>=2 "
         f"disk_space>={DISK} geolocation notin [CN]")
CONTINENT = {}
for cont, ccs in {
    "EU": "FR DE CZ RO BG PL NL BE ES PT IT SE NO FI DK EE LV LT UA GB IE AT CH HU SK SI HR RS GR IS LU MD",
    "NA": "US CA MX", "SA": "CL BR AR CO PE",
    "AS": "TH TW JP KR SG MY VN IN ID PH HK KZ AE IL TR SA",
    "OC": "AU NZ", "AF": "ZA EG NG KE MA",
}.items():
    for cc in ccs.split():
        CONTINENT[cc] = cont


def vast(*args, raw=True):
    cmd = [VASTAI, *args] + (["--raw"] if raw else [])
    out = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if not raw:
        return out.stdout + out.stderr
    try:
        return json.loads(out.stdout)
    except json.JSONDecodeError:
        raise RuntimeError(f"vastai {args[0]} {args[1] if len(args) > 1 else ''} failed: "
                           f"{(out.stdout + out.stderr)[:300]}")


def cc(o):
    return (o.get("geolocation") or "??").split(",")[-1].strip()


def tier(a, b):
    if cc(a) == cc(b):
        return 0
    if CONTINENT.get(cc(a)) and CONTINENT.get(cc(a)) == CONTINENT.get(cc(b)):
        return 1
    return 2


def search(exclude_machines=()):
    offers = vast("search", "offers", QUERY, "--storage", str(DISK), "-o", "dph_total")
    good = []
    for o in offers:
        if o["machine_id"] in exclude_machines:
            continue
        # re-check every condition locally (dph_total here already includes 60 GB disk)
        if (o["dph_total"] <= MAX_DPH and o["num_gpus"] == 2 and "3090" in o["gpu_name"]
                and o["reliability2"] >= 0.95 and o["inet_down"] >= 700
                and o["inet_down_cost"] <= 0.01 and o["cpu_cores_effective"] >= 16
                and cc(o) != "CN" and o["cuda_max_good"] >= 12.8):
            good.append(o)
    return good


def best_pair(offers):
    best = None
    for i, a in enumerate(offers):
        for b in offers[i + 1:]:
            if a["public_ipaddr"] == b["public_ipaddr"] or a["machine_id"] == b["machine_id"]:
                continue
            key = (tier(a, b), a["dph_total"] + b["dph_total"])
            if best is None or key < best[0]:
                best = (key, a, b)
    if best is None:
        raise RuntimeError("no pair of offers satisfies the conditions")
    return best[1], best[2]


def best_partner(offers, other_ip, other_offer):
    cands = [o for o in offers if o["public_ipaddr"] != other_ip]
    if not cands:
        raise RuntimeError("no replacement offer available")
    return min(cands, key=lambda o: (tier(o, other_offer), o["dph_total"]))


def create(offer, idx):
    args = ["create", "instance", str(offer["id"]), "--image", IMAGE, "--disk", str(DISK),
            "--ssh", "--direct", "--label", LABELS[idx], "--cancel-unavail"]
    if idx == 0:
        args += ["--env", f"-p {NODE1_PORT}:{NODE1_PORT}"]
    r = vast(*args)
    if not r.get("success"):
        raise RuntimeError(f"create failed: {r}")
    print(f"[{LABELS[idx]}] created instance {r['new_contract']} from offer {offer['id']} "
          f"({offer['geolocation']}, ${offer['dph_total']:.4f}/h)", flush=True)
    return r["new_contract"]


def ssh_ok(host, port):
    r = subprocess.run(["ssh", "-i", SSH_KEY, "-p", str(port), "-o", "StrictHostKeyChecking=no",
                        "-o", "UserKnownHostsFile=/dev/null", "-o", "ConnectTimeout=8",
                        "-o", "BatchMode=yes", "-o", "LogLevel=ERROR", f"root@{host}",
                        "nvidia-smi -L | wc -l"], capture_output=True, text=True, timeout=40)
    return r.returncode == 0 and r.stdout.strip() == "2"


def node_info(inst, idx, offer):
    ports = inst.get("ports") or {}
    ssh_port = int(ports["22/tcp"][0]["HostPort"])
    info = {
        "node": idx + 1, "label": LABELS[idx], "instance_id": inst["id"],
        "offer_id": offer["id"], "machine_id": inst["machine_id"], "host_id": inst["host_id"],
        "public_ip": inst["public_ipaddr"].strip(), "ssh_port": ssh_port,
        "geolocation": inst.get("geolocation"), "gpu": f'{inst["num_gpus"]}x {inst["gpu_name"]}',
        "dph_total": inst["dph_total"], "cpu_cores": inst.get("cpu_cores"),
        "cpu_cores_effective": inst.get("cpu_cores_effective"),
        "reliability": offer["reliability2"], "inet_down": offer["inet_down"],
        "inet_up": offer["inet_up"], "inet_down_cost": offer["inet_down_cost"],
        "cuda_max_good": offer["cuda_max_good"], "image": IMAGE, "disk_gb": DISK,
    }
    if idx == 0:
        info["open_port_internal"] = NODE1_PORT
        info["open_port_external"] = int(ports[f"{NODE1_PORT}/tcp"][0]["HostPort"])
    return info


def wait_ready(iid, idx, offer, t0):
    """Return node info when usable, or None on timeout / dead state."""
    while time.time() - t0 < READY_TIMEOUT:
        try:
            inst = vast("show", "instance", str(iid))
        except Exception as e:  # transient API problem
            print(f"[{LABELS[idx]}] poll error: {e}", flush=True)
            time.sleep(10)
            continue
        st = inst.get("actual_status")
        print(f"[{LABELS[idx]}] {int(time.time() - t0)}s status={st} "
              f"msg={(inst.get('status_msg') or '')[:70].strip()}", flush=True)
        if st in ("exited", "unknown", "offline"):
            return None
        if st == "running" and (inst.get("ports") or {}).get("22/tcp"):
            try:
                info = node_info(inst, idx, offer)
                if ssh_ok(info["public_ip"], info["ssh_port"]):
                    info["ready_seconds"] = int(time.time() - t0)
                    return info
            except Exception as e:
                print(f"[{LABELS[idx]}] not usable yet: {e}", flush=True)
        time.sleep(15)
    return None


def main():
    log = {"query": QUERY, "events": []}
    offers = search()
    log["offers_at_start"] = [
        {k: o[k] for k in ("id", "machine_id", "host_id", "public_ipaddr", "geolocation",
                            "dph_total", "reliability2", "inet_down", "inet_up",
                            "inet_down_cost", "cpu_cores", "cpu_cores_effective",
                            "cuda_max_good")} for o in offers]
    used, dead = set(), set()   # machines already tried / offers that refused to create
    ids, t0s, infos = [None, None], [None, None], [None, None]
    pair = None
    for _ in range(8):
        offers = [o for o in search() if o["id"] not in dead]
        pair = list(best_pair(offers))
        msg = (f"picked pair offers {pair[0]['id']} + {pair[1]['id']} (tier {tier(*pair)}, "
               f"total ${pair[0]['dph_total'] + pair[1]['dph_total']:.4f}/h)")
        log["events"].append(msg)
        print(msg, flush=True)
        try:
            ids[0] = create(pair[0], 0)
        except RuntimeError as e:
            dead.add(pair[0]["id"])
            log["events"].append(f"offer {pair[0]['id']} could not be created: {str(e)[:120]}")
            print(log["events"][-1], flush=True)
            continue
        t0s[0] = time.time()
        try:
            ids[1] = create(pair[1], 1)
        except RuntimeError as e:
            dead.add(pair[1]["id"])
            log["events"].append(f"offer {pair[1]['id']} could not be created: {str(e)[:120]}; "
                                 f"destroying {ids[0]} and re-picking the pair")
            print(log["events"][-1], flush=True)
            vast("destroy", "instance", str(ids[0]), "-y", raw=False)
            ids[0] = None
            continue
        t0s[1] = time.time()
        break
    else:
        raise RuntimeError("could not create a pair")
    used.update(o["machine_id"] for o in pair)
    for attempt in range(6):
        for i in (0, 1):
            if infos[i] is None:
                infos[i] = wait_ready(ids[i], i, pair[i], t0s[i])
        bad = [i for i in (0, 1) if infos[i] is None]
        if not bad:
            break
        for i in bad:
            msg = f"{LABELS[i]} instance {ids[i]} not ready in 10 min -> destroyed"
            vast("destroy", "instance", str(ids[i]), "-y", raw=False)
            log["events"].append(msg)
            print(msg, flush=True)
            other = 1 - i
            while True:
                cands = [o for o in search(used) if o["id"] not in dead]
                new = best_partner(cands, pair[other]["public_ipaddr"], pair[other])
                try:
                    ids[i] = create(new, i)
                    break
                except RuntimeError:
                    dead.add(new["id"])
            pair[i] = new
            used.add(new["machine_id"])
            t0s[i] = time.time()
            infos[i] = None
            log["events"].append(f"{LABELS[i]} replaced by offer {new['id']} ({new['geolocation']})")
    else:
        raise RuntimeError("could not get 2 ready nodes")
    assert infos[0]["public_ip"] != infos[1]["public_ip"]
    os.makedirs(os.path.join(HERE, "results"), exist_ok=True)
    json.dump({"nodes": infos}, open(os.path.join(HERE, "nodes.json"), "w"), indent=2)
    json.dump(log, open(os.path.join(HERE, "results", "rent_log.json"), "w"), indent=2)
    print("READY", json.dumps(infos, indent=2))


if __name__ == "__main__":
    sys.exit(main())
