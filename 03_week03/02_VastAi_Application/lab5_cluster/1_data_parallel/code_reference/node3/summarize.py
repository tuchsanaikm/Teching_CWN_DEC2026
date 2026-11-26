#!/usr/bin/env python3
"""Build results/train_summary.json + results/report.md from the logs pulled into results/raw/."""
import json, glob, os, statistics as st
R = "results/raw"
W = {r: [json.loads(l) for l in open(f"{R}/worker{r}_steps.jsonl")] for r in range(6)}
C = [json.loads(l) for l in open(f"{R}/coordinator_steps.jsonl")]
chk = [json.loads(l) for l in open(f"{R}/weight_check.jsonl")]
gpu = {}
for n in (1, 2, 3): gpu.update(json.load(open(f"{R}/gpu_summary_node{n}.json")))
ev = {k: json.load(open(f"{R}/eval_{k}.json"))["summary"] for k in ("base", "epoch1", "epoch2")
      if os.path.exists(f"{R}/eval_{k}.json")}
nsteps = len(C); m = st.mean
skip = 1                                   # step 0 includes CUDA warm-up + waiting for model loads
per_rank = {}
for r in range(6):
    w = W[r][skip:]
    per_rank[r] = {"compute_s": m(x["t_compute"] for x in w), "comm_s": m(x["t_comm"] for x in w),
                   "send_s": m(x["t_send"] for x in w), "wait_recv_s": m(x["t_wait_recv"] for x in w),
                   "vram_alloc_peak_mb": max(x["vram_alloc_peak_mb"] for x in W[r]),
                   "vram_reserved_peak_mb": max(x["vram_reserved_peak_mb"] for x in W[r]),
                   "up_bytes": W[r][-1]["up_bytes"], "down_bytes": W[r][-1]["down_bytes"],
                   "reconnects": W[r][-1]["reconnects"], "steps": len(W[r]),
                   "examples": sum(x["n"] for x in W[r]), **gpu[f"rank{r}"]}
wall = C[-1]["t"] - C[0]["t"]                      # first average -> last average
examples = sum(c["n_total"] for c in C[1:])
step_s = wall / (nsteps - 1)
ep = {}
for e in (1, 2):
    cs = [c for c, w in zip(C, W[0]) if w["epoch"] == e]
    ep[e] = {"steps": len(cs), "examples": sum(c["n_total"] for c in cs),
             "train_loss": sum(c["loss"] * c["n_total"] for c in cs) / sum(c["n_total"] for c in cs),
             "seconds": cs[-1]["t"] - cs[0]["t"]}
S = {"batch_per_gpu": 4, "gpus": 6, "batch_total": 24, "steps": nsteps, "steps_per_epoch": ep[1]["steps"],
     "wall_s_step1_to_end": wall, "sec_per_step": step_s,
     "sec_per_step_compute_mean": m(v["compute_s"] for v in per_rank.values()),
     "sec_per_step_comm_mean": m(v["comm_s"] for v in per_rank.values()),
     "examples_per_s": examples / wall,
     "grad_up_bytes_per_worker_step": per_rank[0]["up_bytes"], "grad_down_bytes_per_worker_step": per_rank[0]["down_bytes"],
     "sec_per_step_median": st.median(b["t"] - a["t"] for a, b in zip(C, C[1:])),
     "sec_per_step_p90": sorted(b["t"] - a["t"] for a, b in zip(C, C[1:]))[int(0.9 * (nsteps - 1))],
     "sec_per_step_max": max(b["t"] - a["t"] for a, b in zip(C, C[1:])),
     "comm_s_median": st.median(x["t_comm"] for r in range(6) for x in W[r][skip:]),
     "compute_s_median": st.median(x["t_compute"] for r in range(6) for x in W[r][skip:]),
     "steps_over_15s": sum(b["t"] - a["t"] > 15 for a, b in zip(C, C[1:])),
     "arrive_spread_s_mean": m(c["arrive_spread_s"] for c in C[1:]), "coordinator_avg_ms": m(c["avg_ms"] for c in C),
     "per_rank": per_rank, "epochs": ep, "weight_check": chk, "eval": ev}
json.dump(S, open("results/train_summary.json", "w"), indent=1)
o = ["# LAB 5 — Data Parallelism 3 Node (6 × RTX 3090), Qwen3-8B + LoRA → SQL", "",
     f"- batch ต่อ GPU = 4, รวม = 24 · {nsteps} step ({ep[1]['steps']} step/epoch × 2) · ตัวอย่าง/epoch = {ep[1]['examples']}",
     f"- วินาทีต่อ step (wall) = {step_s:.2f} · คำนวณบน GPU เฉลี่ย {S['sec_per_step_compute_mean']:.2f} s · ส่ง+รอ Gradient เฉลี่ย {S['sec_per_step_comm_mean']:.2f} s",
     f"- มัธยฐาน: {S['sec_per_step_median']:.2f} s/step (คำนวณ {S['compute_s_median']:.2f} · ส่ง+รอ {S['comm_s_median']:.2f}) · p90 {S['sec_per_step_p90']:.2f} s · ช้าสุด {S['sec_per_step_max']:.1f} s · step ที่เกิน 15 s = {S['steps_over_15s']}",
     f"- ตัวอย่างต่อวินาที = {S['examples_per_s']:.2f} · เวลาเทรนรวม {wall/60:.1f} นาที",
     f"- Gradient ต่อ step ต่อ worker: ส่งขึ้น {per_rank[0]['up_bytes']/1e6:.2f} MB (bf16) · รับค่าเฉลี่ย {per_rank[0]['down_bytes']/1e6:.2f} MB (fp32) · รวมทั้งคลัสเตอร์ {(per_rank[0]['up_bytes']+per_rank[0]['down_bytes'])*6/1e6:.1f} MB/step",
     "", "| rank | Node/GPU | VRAM สูงสุด torch reserved (MB) | VRAM สูงสุด nvidia-smi (MiB) | คำนวณ (s/step) | ส่ง+รอ (s/step) | ส่ง (s) | รอ+รับ (s) | GPU util เฉลี่ย % | reconnect |", "|---|---|---|---|---|---|---|---|---|---|"]
for r, v in per_rank.items():
    o.append(f"| {r} | N{v['node']}/GPU{v['gpu']} | {v['vram_reserved_peak_mb']} | {v['nvidia_smi_mem_max_mib']:.0f} | {v['compute_s']:.3f} | {v['comm_s']:.3f} | {v['send_s']:.3f} | {v['wait_recv_s']:.3f} | {v['util_mean']} | {v['reconnects']} |")
o += ["", "| จุดวัด | train loss (เฉลี่ยทั้ง epoch) | test loss | Exact Match (200 ข้อ) | น้ำหนัก LoRA 6 ตัวเท่ากัน |", "|---|---|---|---|---|"]
for k, e in (("base", None), ("epoch1", 1), ("epoch2", 2)):
    x = ev.get(k, {}); c = next((c for c in chk if c["tag"] == k), None)
    o.append(f"| {k} | {ep[e]['train_loss']:.4f} |" if e else f"| {k} | - |")
    o[-1] += f" {x.get('test_loss', float('nan')):.4f} | {x.get('exact_match_count','?')}/200 = {100*x.get('exact_match', float('nan')):.1f}% | {('ใช่ sha256 ' + c['sha_per_rank'][0][:12]) if c and c['equal'] else ('-' if not c else 'ไม่เท่า')} |"
open("results/report.md", "w", encoding="utf-8").write("\n".join(o) + "\n")
print("\n".join(o))
