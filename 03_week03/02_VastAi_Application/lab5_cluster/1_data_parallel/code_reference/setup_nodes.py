#!/usr/bin/env python3
"""Runs on the control machine. Steps (pick with argv, default = all):
  prepare  copy scripts to both nodes, install deps, download model + dataset, split
  verify   pull reports, check both nodes hold the identical train/test files
  samples  build results/dataset_samples.md (6 examples)
  net      measure Node 2 -> Node 1 port reachability, RTT and throughput both ways
Secrets: HF_TOKEN is sent to the nodes over SSH stdin only; never printed or stored.
"""
import json, os, subprocess, sys
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, "results")
KEY = "/workspace/vastai_lab/Devtool_SSH/devtoolSSH"
SSH_OPTS = ["-i", KEY, "-o", "StrictHostKeyChecking=no", "-o", "UserKnownHostsFile=/dev/null",
            "-o", "LogLevel=ERROR", "-o", "ConnectTimeout=15", "-o", "ServerAliveInterval=30"]
NODES = json.load(open(os.path.join(HERE, "nodes.json")))["nodes"]
REMOTE = "/workspace/lab5_dp"


def ssh(node, cmd, stdin=None, timeout=3600):
    r = subprocess.run(["ssh", *SSH_OPTS, "-p", str(node["ssh_port"]), f"root@{node['public_ip']}",
                        cmd], input=stdin, capture_output=True, text=True, timeout=timeout)
    return r.returncode, r.stdout, r.stderr


def scp_to(node, files, dest):
    subprocess.run(["scp", *SSH_OPTS, "-P", str(node["ssh_port"]), *files,
                    f"root@{node['public_ip']}:{dest}"], check=True, capture_output=True)


def scp_from(node, path, dest):
    subprocess.run(["scp", *SSH_OPTS, "-P", str(node["ssh_port"]),
                    f"root@{node['public_ip']}:{path}", dest], check=True, capture_output=True)


def hf_token():
    for line in open("/workspace/vastapp_lab/.env"):
        if line.startswith("HF_TOKEN="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def prepare_one(node):
    tag = f"node{node['node']}"
    ssh(node, f"mkdir -p {REMOTE}")
    scp_to(node, [os.path.join(HERE, f) for f in ("prepare_node.py", "nettest.py")], REMOTE + "/")
    script = f"""set -e
touch ~/.no_auto_tmux
read -r HF_TOKEN
export HF_TOKEN HF_HUB_ENABLE_HF_TRANSFER=1 HF_HOME={REMOTE}/hf_cache
cd {REMOTE}
PY=$(command -v python || command -v python3)
$PY -m pip install -q --root-user-action=ignore datasets transformers huggingface_hub hf_transfer safetensors "brotli>=1.2" > pip.log 2>&1
(apt-get update -qq && apt-get install -y -qq iperf3 iputils-ping) > apt.log 2>&1 || true
$PY prepare_node.py > prepare.log 2> prepare.err
"""
    # send the script as the remote command and the token alone on stdin
    rc, out, err = ssh(node, f"bash -c {quote(script)}", stdin=hf_token() + "\n")
    _, tail, _ = ssh(node, f"tail -c 1500 {REMOTE}/prepare.err; tail -c 300 {REMOTE}/pip.log")
    print(f"[{tag}] prepare rc={rc}")
    if rc != 0:
        print(f"[{tag}] stderr tail:\n{tail}\n{err[-800:]}")
    return rc


def quote(s):
    return "'" + s.replace("'", "'\"'\"'") + "'"


def step_prepare():
    with ThreadPoolExecutor(2) as ex:
        rcs = list(ex.map(prepare_one, NODES))
    if any(rcs):
        sys.exit("prepare failed")


def step_verify():
    reps = []
    for n in NODES:
        dest = os.path.join(RES, f"prepare_report_node{n['node']}.json")
        scp_from(n, f"{REMOTE}/prepare_report.json", dest)
        reps.append(json.load(open(dest)))
    same = {k: reps[0][k] == reps[1][k] for k in
            ("train_sha256", "test_sha256", "train_count", "test_count", "model_revision",
             "dataset_revision", "model_params", "model_weight_bytes")}
    summary = {"node1": reps[0], "node2": reps[1], "identical": same,
               "all_identical": all(same.values())}
    json.dump(summary, open(os.path.join(RES, "prepare_summary.json"), "w"), indent=2)
    print(json.dumps({"identical": same, "train": reps[0]["train_count"],
                      "test": reps[0]["test_count"], "total": reps[0]["dataset_total"],
                      "params": reps[0]["model_params"], "gpus": [r["gpus"] for r in reps],
                      "torch": [(r["torch"], r["torch_cuda"]) for r in reps]}, indent=2))
    if not summary["all_identical"]:
        sys.exit("nodes differ!")


def cell(s):
    return s.replace("|", "\\|").replace("\n", " ")


def step_samples():
    os.makedirs(os.path.join(RES, "data_head"), exist_ok=True)
    local = os.path.join(RES, "data_head", "train_first6.jsonl")
    rc, out, _ = ssh(NODES[0], f"head -n 6 {REMOTE}/data/train.jsonl")
    rc2, out2, _ = ssh(NODES[1], f"head -n 6 {REMOTE}/data/train.jsonl")
    assert rc == 0 and out == out2, "first rows differ between nodes"
    open(local, "w", encoding="utf-8").write(out)
    rows = [json.loads(l) for l in out.splitlines()]
    md = ["# ตัวอย่างข้อมูล b-mc2/sql-create-context (6 รายการแรกของ Training Set)", "",
          "สับด้วย seed 0 · Training Set 4,000 ตัวอย่าง · Test Set 200 ตัวอย่าง · "
          "ทั้ง 2 Node ได้ไฟล์เดียวกัน (sha256 ตรงกัน)", "",
          "| # | คำถาม (question) | โครงสร้างตาราง (context) | SQL เฉลย (answer) |",
          "|---|---|---|---|"]
    for i, r in enumerate(rows, 1):
        md.append(f"| {i} | {cell(r['question'])} | `{cell(r['context'])}` | `{cell(r['answer'])}` |")
    open(os.path.join(RES, "dataset_samples.md"), "w", encoding="utf-8").write("\n".join(md) + "\n")
    print("\n".join(md))


def step_net():
    n1, n2 = NODES
    port_in, port_ext = n1["open_port_internal"], n1["open_port_external"]
    res = {"node1": f"{n1['public_ip']}:{port_ext} (container port {port_in})",
           "direction_note": "client = Node 2, server = Node 1; all traffic uses Node 1's one open port"}
    ssh(n1, f"cd {REMOTE}; [ -f nettest.pid ] && kill $(cat nettest.pid) 2>/dev/null; pkill iperf3; "
            f"sleep 0.5; nohup python nettest.py server {port_in} > nettest_server.log 2>&1 "
            f"< /dev/null & echo $! > nettest.pid; sleep 2", timeout=30)
    rc, out, err = ssh(n2, f"cd {REMOTE}; python nettest.py client {n1['public_ip']} {port_ext} "
                           f"--secs 10 --pings 60", timeout=180)
    try:
        res["tcp_test"] = json.loads(out)
    except Exception:
        res["tcp_test"] = {"connect_ok": False, "error": (out + err)[-400:]}
    ssh(n1, f"kill $(cat {REMOTE}/nettest.pid); sleep 1", timeout=30)
    # ICMP ping (may be filtered by hosts)
    rc, out, _ = ssh(n2, f"ping -c 10 -i 0.2 -q {n1['public_ip']} 2>&1 | tail -n 2", timeout=60)
    res["icmp_ping_node2_to_node1"] = out.strip()
    # iperf3 cross-check over the same port (4 parallel streams), both directions
    ssh(n1, f"nohup iperf3 -s -p {port_in} -D > /dev/null 2>&1; sleep 1", timeout=30)
    ip = {}
    for name, flag in (("node2_to_node1", ""), ("node1_to_node2", "-R")):
        rc, out, err = ssh(n2, f"iperf3 -c {n1['public_ip']} -p {port_ext} -t 10 -P 4 -J {flag}",
                           timeout=120)
        try:
            j = json.loads(out)
            ip[name] = {"mbps_received": round(j["end"]["sum_received"]["bits_per_second"] / 1e6, 1),
                        "mbps_sent": round(j["end"]["sum_sent"]["bits_per_second"] / 1e6, 1),
                        "retransmits": j["end"]["sum_sent"].get("retransmits")}
        except Exception:
            ip[name] = {"error": (out + err)[-300:]}
    ssh(n1, "pkill iperf3", timeout=30)
    res["iperf3_4streams"] = ip
    json.dump(res, open(os.path.join(RES, "network.json"), "w"), indent=2)
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    os.makedirs(RES, exist_ok=True)
    steps = sys.argv[1:] or ["prepare", "verify", "samples", "net"]
    for s in steps:
        print(f"=== {s} ===", flush=True)
        globals()[f"step_{s}"]()
