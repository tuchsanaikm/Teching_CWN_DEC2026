"""Build results/summary.md and results/summary.json from the probe, training and eval outputs."""
import json
import os

R = "/workspace/lab4_dp4/results"
probe = json.load(open(f"{R}/batch_probe.json"))
train = json.load(open(f"{R}/train_metrics.json"))
evals = {t: json.load(open(f"{R}/eval/eval_{t}.json")) for t in ["base", "epoch1", "epoch2", "epoch3"]
         if os.path.exists(f"{R}/eval/eval_{t}.json")}
n = probe["ngpu"]
gpus = list(range(n))
L = ["# Data Parallelism · Qwen3-8B + LoRA · 4 GPU (DDP)", ""]

L += ["## 1. batch ต่อ GPU เทียบ VRAM สูงสุด (3 step, ตัวอย่างยาวที่สุด 256 token)", "",
      "| batch ต่อ GPU | batch รวม | ผล | " + " | ".join(f"GPU{g} MiB" for g in gpus) + " | PyTorch allocated สูงสุด MiB | วินาที/step (step 2–3) |",
      "|---|---|---|" + "---|" * (n + 2)]
for r in probe["probes"]:
    if r["status"] == "ok":
        s = r["sec_per_step"][1:]
        L.append(f"| {r['batch_per_gpu']} | {r['global_batch']} | ผ่าน | " + " | ".join(f"{m:,}" for m in r["nvidia_smi_peak_mib"])
                 + f" | {max(r['torch_allocated_mib']):,} | {sum(s) / len(s):.2f} |")
    else:
        L.append(f"| {r['batch_per_gpu']} | {r.get('global_batch', '')} | Out of Memory | " + " | ".join(["OOM"] * n) + " | – | – |")
L += ["", f"batch ต่อ GPU ใหญ่สุดที่ผ่าน: **{probe['max_batch_per_gpu']}**", ""]

L += ["## 2. การเทรน", "",
      f"batch ต่อ GPU {train['batch_per_gpu']} · batch รวม {train['global_batch']} · {train['steps_per_epoch']} step ต่อ Epoch", "",
      "| Epoch | step | วินาที/step | ตัวอย่าง/วินาที | เวลา (วินาที) | " + " | ".join(f"util GPU{g} %" for g in gpus) + " | " + " | ".join(f"VRAM GPU{g} MiB" for g in gpus) + " |",
      "|---|---|---|---|---|" + "---|" * (2 * n)]
for e in train["epochs"]:
    L.append(f"| {e['epoch']} | {e['steps']} | {e['sec_per_step']:.3f} | {e['samples_per_sec']:.1f} | {e['epoch_sec']:.0f} | "
             + " | ".join(f"{u:.0f}" for u in e["gpu_util_mean"]) + " | " + " | ".join(f"{m:,}" for m in e["nvidia_smi_peak_mib"]) + " |")
tot_s = sum(e["epoch_sec"] for e in train["epochs"])
tot_n = sum(e["samples"] for e in train["epochs"])
tot_st = sum(e["steps"] for e in train["epochs"])
util = [sum(e["gpu_util_mean"][g] * e["epoch_sec"] for e in train["epochs"]) / tot_s for g in gpus]
L.append(f"| รวม | {tot_st} | {tot_s / tot_st:.3f} | {tot_n / tot_s:.1f} | {tot_s:.0f} | " + " | ".join(f"{u:.0f}" for u in util)
         + " | " + " | ".join(f"{max(e['nvidia_smi_peak_mib'][g] for e in train['epochs']):,}" for g in gpus) + " |")

L += ["", "## 3. loss และ Exact Match (Test Set 200 ตัวอย่าง)", "",
      "| โมเดล | train loss (เฉลี่ยทั้ง Epoch) | test loss | Exact Match | ถูก/ทั้งหมด | Exact Match แบบไม่สนตัวพิมพ์และชนิดเครื่องหมายคำพูด |",
      "|---|---|---|---|---|---|"]
tl = {f"epoch{e['epoch']}": e["train_loss_mean"] for e in train["epochs"]}
for t, ev in evals.items():
    name = "Base" if t == "base" else f"หลัง Epoch {t[-1]}"
    L.append(f"| {name} | {tl[t]:.4f} | {ev['test_loss']:.4f} | {ev['exact_match'] * 100:.1f}% | {ev['em_correct']}/{ev['n']} | {ev['exact_match_loose'] * 100:.1f}% |"
             if t in tl else
             f"| {name} | – | {ev['test_loss']:.4f} | {ev['exact_match'] * 100:.1f}% | {ev['em_correct']}/{ev['n']} | {ev['exact_match_loose'] * 100:.1f}% |")
open(f"{R}/summary.md", "w").write("\n".join(L) + "\n")
json.dump({"probe": probe, "train": {k: v for k, v in train.items() if k != "epochs"},
           "epochs": [{k: v for k, v in e.items() if k != "losses"} for e in train["epochs"]],
           "total": {"steps": tot_st, "sec": tot_s, "sec_per_step": tot_s / tot_st, "samples_per_sec": tot_n / tot_s,
                     "gpu_util_mean": util}, "eval": evals}, open(f"{R}/summary.json", "w"), indent=1)
print("\n".join(L))
