#!/usr/bin/env python3
"""Build results/train_summary.json + results/report.md from the files pulled into results/train and results/eval."""
import json, os, statistics as st, glob
os.chdir(os.path.dirname(os.path.abspath(__file__)))
T = "results/train"
mean = lambda x: sum(x) / len(x)
nodes = {}
for n in (1, 2, 3):
    steps = [json.loads(l) for l in open(f"{T}/steps_node{n}.jsonl")]
    summ = json.load(open(f"{T}/summary_node{n}.json"))
    t0, t1 = steps[0]["wall"] - steps[0]["t_step"], steps[-1]["wall"]
    gpu = {0: [], 1: []}; mem = {0: 0, 1: 0}
    for l in open(f"{T}/gpu_node{n}.csv"):
        p = l.strip().split(",")
        if len(p) != 4: continue
        ts, i, u, m = float(p[0]), int(p[1]), float(p[2]), float(p[3])
        if t0 <= ts <= t1: gpu[i].append(u); mem[i] = max(mem[i], m)
    def agg(sel):
        return {k: round(mean([s[k] for s in sel]), 4) for k in
                ("t_step", "t_compute", "t_comm", "t_fwd_bwd", "t_apply", "t_pack", "t_send", "t_wait", "t_recv", "t_unpack")}
    nodes[n] = dict(steps=len(steps), all=agg(steps),
                    per_epoch={e: agg([s for s in steps if s["epoch"] == e]) for e in (1, 2)},
                    median_step=round(st.median(s["t_step"] for s in steps), 4),
                    examples=sum(s["n"] for s in steps), wall_s=round(t1 - t0, 1),
                    gpu_util_mean={i: round(mean(gpu[i]), 1) for i in gpu}, smi_mem_max_mib=mem,
                    torch_vram=summ["vram"], epochs=summ["epochs"], info=summ["info"],
                    grad_bytes=steps[0]["grad_bytes"], lora_params=summ["lora_params"], shard=summ["shard_size"])
coord = [json.loads(l) for l in open(f"{T}/coordinator.jsonl")]
csteps = [c for c in coord if c["type"] == "step"]
checks = [c for c in coord if c["type"] == "epoch_check"]
wall = max(nodes[n]["wall_s"] for n in nodes)
total_ex = sum(nodes[n]["examples"] for n in nodes)
ep_loss = {e: round(mean([c["loss"] for c in csteps if (c["step"] // nodes[1]["epochs"][0]["steps"]) + 1 == e]), 5) for e in (1, 2)}
ev = {os.path.basename(f)[:-5]: {k: v for k, v in json.load(open(f)).items() if k != "items"} for f in glob.glob("results/eval/*.json")}
out = dict(nodes=nodes, coordinator=dict(steps=len(csteps), avg_ms_mean=round(mean([c["avg_ms"] for c in csteps]), 2),
           wait_spread_s_mean=round(mean([c["wait_spread_s"] for c in csteps]), 3), epoch_checks=checks,
           disconnects=[c for c in coord if c["type"] == "disconnect"]),
           wall_s=wall, total_examples=total_ex, examples_per_s=round(total_ex / wall, 2),
           train_loss_epoch_mean=ep_loss, first_step_loss=csteps[0]["loss"], last_step_loss=csteps[-1]["loss"], eval=ev)
json.dump(out, open("results/train_summary.json", "w"), indent=1)
print(json.dumps(out, indent=1))
