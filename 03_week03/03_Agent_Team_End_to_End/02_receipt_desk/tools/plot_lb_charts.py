#!/usr/bin/env python3
"""
Generate 4 high-DPI Thai-labeled Matplotlib charts from REAL 2x RTX 4090 2× RTX 4090 benchmark JSONs
in results/lb/ -> results/images/ (and also build public/data/lb_summary.json for /telemetry).
"""
import json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
LB_DIR = ROOT / "results" / "lb"
IMG_DIR = ROOT / "results" / "images"
WEB_DATA = ROOT / "code_reference" / "app" / "web" / "public" / "data" / "lb_summary.json"

# Thai font setup on Windows
plt.rcParams["font.sans-serif"] = ["Leelawadee UI", "Tahoma", "Noto Sans Thai", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.dpi"] = 180

C_SLATE = "#334155"
C_RED = "#dc2626"
C_AMBER = "#d97706"
C_EMERALD = "#059669"
C_INDIGO = "#4338ca"
C_SKY = "#0284c7"


def jload(name: str):
    p = LB_DIR / name
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def get_levels(d):
    if not d:
        return []
    by_n = {}
    for lv in d.get("levels", []):
        if lv.get("discarded"):
            continue
        by_n[lv["users"]] = lv
    return [by_n[k] for k in sorted(by_n)]


def peak_tps(d):
    lvs = get_levels(d)
    return max((lv.get("throughput_tok_s") or 0 for lv in lvs), default=0)


def cap_users(d):
    if not d:
        return 0
    c = d.get("capacity") or {}
    if c.get("users") is not None:
        return int(c["users"])
    passing = [lv["users"] for lv in get_levels(d) if lv.get("verdict") or lv.get("pass")]
    return max(passing, default=0)


def at_cap_ttft(d):
    c = (d or {}).get("capacity") or {}
    ac = c.get("at_capacity") or {}
    if ac.get("ttft_p95_s") is not None:
        return float(ac["ttft_p95_s"])
    u = cap_users(d)
    for lv in get_levels(d):
        if lv["users"] == u and lv.get("ttft_p95_s") is not None:
            return float(lv["ttft_p95_s"])
    return 0.0


def main():
    IMG_DIR.mkdir(parents=True, exist_ok=True)
    WEB_DATA.parent.mkdir(parents=True, exist_ok=True)

    n1 = jload("dp1_n1_baseline.json")
    seq = jload("dp1_seq.json")
    dp1 = jload("dp1_cb.json")
    dp1_fast = jload("dp1_cb_fast.json")
    dp2 = jload("dp2_cb.json")
    dp2_fast = jload("dp2_cb_fast.json")
    cap32 = jload("cap_32.json")
    cap256 = jload("cap_256.json")
    mix_s = jload("mix_short.json")
    mix_l = jload("mix_long.json")
    fail = jload("fail_replica.json")
    fail_ev = jload("fail_event.json")
    ocr1 = jload("receipt_batch_dp1.json")
    ocr2 = jload("receipt_batch_dp2.json")
    meta = jload("instance_meta.json") or {}

    seq_u = cap_users(seq)
    dp1_u = cap_users(dp1)
    dp1_fu = cap_users(dp1_fast)
    dp2_u = cap_users(dp2)
    dp2_fu = cap_users(dp2_fast)

    seq_tps = round(peak_tps(seq))
    dp1_tps = round(peak_tps(dp1))
    dp2_tps = round(peak_tps(dp2))

    eff_users = round(100.0 * dp2_u / (2 * max(1, dp1_u)), 1)
    eff_tps = round(100.0 * dp2_tps / (2 * max(1, dp1_tps)), 1)
    ocr1_rpm = ocr1.get("receipts_per_minute", 0) if ocr1 else 0
    ocr2_rpm = ocr2.get("receipts_per_minute", 0) if ocr2 else 0
    ocr_speedup = round(ocr2_rpm / max(0.01, ocr1_rpm), 2) if ocr1 and ocr2 else 0

    # ── Chart 1: Capacity & Peak Throughput & OCR Batch Speedup ──
    fig, axes = plt.subplots(1, 3, figsize=(15.5, 5.0))
    fig.patch.set_facecolor("white")

    labels = ["1 GPU\nSequential\n(max_seqs=1)", "1 GPU\nContinuous Batching\n(max_seqs=256)", "2 GPUs Data Parallelism\n+ NGINX least_conn\n(max_seqs=256)"]
    x = np.arange(3)
    w = 0.36

    ax = axes[0]
    b1 = ax.bar(x - w/2, [seq_u, dp1_u, dp2_u], w, label="Standard SLO (≥15 tok/s)", color=[C_RED, C_SKY, C_EMERALD], edgecolor="white")
    b2 = ax.bar(x + w/2, [seq_u, dp1_fu, dp2_fu], w, label="Fast SLO (≥50% ของ 1 ผู้ใช้)", color=["#fca5a5", "#7dd3fc", "#6ee7b7"], edgecolor="white")
    ax.set_title("จำนวนผู้ใช้พร้อมกันสูงสุดตาม SLO (คน)", fontsize=11.5, fontweight="bold", pad=10)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=8.8)
    ax.set_ylabel("ผู้ใช้พร้อมกัน (คน)")
    ax.grid(axis="y", alpha=0.25)
    ax.legend(fontsize=8, loc="upper left")
    for bar in list(b1) + list(b2):
        h = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2, h + max(dp2_u, 10)*0.02, f"{int(h)}", ha="center", va="bottom", fontsize=9, fontweight="bold")
    ax.set_ylim(0, max(dp2_u, 10) * 1.22)

    ax = axes[1]
    bars = ax.bar(x, [seq_tps, dp1_tps, dp2_tps], width=0.52, color=[C_RED, C_SKY, C_INDIGO], edgecolor="white")
    ax.set_title(f"Peak Throughput รวม (Efficiency {eff_tps}%)", fontsize=11.5, fontweight="bold", pad=10)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=8.8)
    ax.set_ylabel("โทเคนต่อวินาที (tok/s)")
    ax.grid(axis="y", alpha=0.25)
    for bar in bars:
        h = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2, h + max(dp2_tps, 100)*0.02, f"{int(h):,}", ha="center", va="bottom", fontsize=9.5, fontweight="bold")
    ax.set_ylim(0, max(dp2_tps, 100) * 1.2)

    ax = axes[2]
    olabels = ["1× RTX 4090\n(1 Replica)", "2× RTX 4090\nData Parallelism\n+ NGINX least_conn"]
    obars = ax.bar([0, 1], [ocr1_rpm, ocr2_rpm], width=0.48, color=[C_SKY, C_EMERALD], edgecolor="white")
    ax.set_title(f"อ่านใบเสร็จ CORD-v2 จริง (Speedup {ocr_speedup}×)", fontsize=11.5, fontweight="bold", pad=10)
    ax.set_xticks([0, 1])
    ax.set_xticklabels(olabels, fontsize=9.2)
    ax.set_ylabel("ใบเสร็จต่อนาที")
    ax.grid(axis="y", alpha=0.25)
    for bar in obars:
        h = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2, h + max(ocr2_rpm, 10)*0.02, f"{h:.0f} ใบ/นาที", ha="center", va="bottom", fontsize=9.5, fontweight="bold")
    ax.set_ylim(0, max(ocr2_rpm, 10) * 1.22)

    fig.suptitle("ผลวัดจริงบน 1 โหนด × 2× RTX 4090 · Qwen3-VL-2B-Instruct + LoRA (ReceiptDesk)", fontsize=13.5, fontweight="bold", y=0.99)
    plt.tight_layout(rect=[0, 0, 1, 0.94])
    fig.savefig(IMG_DIR / "01_capacity_throughput_vllm.png")
    plt.close(fig)

    # ── Chart 2: TTFT p95, Per-User Speed p5 & System Throughput vs N Users ──
    fig, axes = plt.subplots(1, 3, figsize=(15.5, 4.9))
    fig.patch.set_facecolor("white")
    series = [
        ("1 GPU Sequential (cap=1)", get_levels(seq), C_RED, "s--"),
        ("1 GPU Continuous Batching (cap=256)", get_levels(dp1), C_SKY, "o-"),
        ("2 GPUs Data Parallelism (cap=256)", get_levels(dp2), C_EMERALD, "D-"),
    ]
    for title, key, ylab, slo, ax in [
        ("เวลารอโทเคนแรก TTFT p95 (ยิ่งต่ำยิ่งดี)", "ttft_p95_s", "วินาที", (2.0, "เพดาน SLO ≤ 2.0 วินาที"), axes[0]),
        ("ความเร็วต่อผู้ใช้ Speed p5 (ยิ่งสูงยิ่งดี)", "speed_p5_tok_s", "tok/s ต่อผู้ใช้", (15.0, "เกณฑ์ Standard SLO ≥ 15 tok/s"), axes[1]),
        ("กำลังผลิตรวมทั้งระบบ Throughput", "throughput_tok_s", "tok/s รวม", None, axes[2]),
    ]:
        for name, lvs, col, sty in series:
            xs = [lv["users"] for lv in lvs if lv.get(key) is not None]
            ys = [lv[key] for lv in lvs if lv.get(key) is not None]
            if xs:
                ax.plot(xs, ys, sty, label=name, color=col, linewidth=2.2, markersize=5.5)
        if slo:
            ax.axhline(slo[0], color=C_AMBER, linestyle=":", linewidth=1.8, label=slo[1])
        ax.set_title(title, fontsize=11, fontweight="bold")
        ax.set_xlabel("จำนวนผู้ใช้พร้อมกัน (คน)")
        ax.set_ylabel(ylab)
        ax.grid(alpha=0.25)
        ax.legend(fontsize=7.8)
    fig.suptitle("เส้นโค้งประสิทธิภาพเมื่อเพิ่มจำนวนผู้ใช้พร้อมกัน (2× RTX 4090)", fontsize=13.5, fontweight="bold", y=0.99)
    plt.tight_layout(rect=[0, 0, 1, 0.94])
    fig.savefig(IMG_DIR / "02_ttft_speed_curves.png")
    plt.close(fig)

    # ── Chart 3: Concurrency Cap Trade-off (cap=32 vs cap=256) + Short/Long Mix Balance ──
    fig, axes = plt.subplots(1, 2, figsize=(13.5, 4.9))
    fig.patch.set_facecolor("white")

    c32 = (cap32 or {}).get("levels", [{}])[0]
    c256 = (cap256 or {}).get("levels", [{}])[0]
    ax = axes[0]
    metrics_x = np.arange(2)
    t_vals = [c32.get("ttft_p95_s") or 0, c256.get("ttft_p95_s") or 0]
    s_vals = [c32.get("speed_p5_tok_s") or 0, c256.get("speed_p5_tok_s") or 0]
    ax2 = ax.twinx()
    b_t = ax.bar(metrics_x - 0.18, t_vals, 0.34, color=C_AMBER, label="TTFT p95 (วินาที)")
    b_s = ax2.bar(metrics_x + 0.18, s_vals, 0.34, color=C_INDIGO, label="Speed p5 (tok/s)")
    ax.set_xticks(metrics_x)
    ax.set_xticklabels([f"max-num-seqs = 32\n(N={c32.get('users','?')})", f"max-num-seqs = 256\n(N={c256.get('users','?')})"], fontsize=9.5)
    ax.set_ylabel("TTFT p95 (วินาที)", color=C_AMBER)
    ax2.set_ylabel("Speed p5 ต่อผู้ใช้ (tok/s)", color=C_INDIGO)
    ax.set_title("Trade-off ของเพดาน Concurrency (cap=32 vs cap=256) ภายใต้โหลดสูง", fontsize=10.8, fontweight="bold")
    ax.grid(axis="y", alpha=0.2)
    for bar in b_t:
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.05, f"{bar.get_height():.2f}s", ha="center", va="bottom", fontsize=9, fontweight="bold", color=C_AMBER)
    for bar in b_s:
        ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1.0, f"{bar.get_height():.1f}", ha="center", va="bottom", fontsize=9, fontweight="bold", color=C_INDIGO)
    ax.set_ylim(0, max(t_vals + [1.0]) * 1.28)
    ax2.set_ylim(0, max(s_vals + [20.0]) * 1.28)

    ax = axes[1]
    ms = (mix_s or {}).get("levels", [{}])[0].get("replicas", {})
    ml = (mix_l or {}).get("levels", [{}])[0].get("replicas", {})
    g0_s = ms.get("gpu0", {}).get("share_pct", 50.0)
    g1_s = ms.get("gpu1", {}).get("share_pct", 50.0)
    g0_l = ml.get("gpu0", {}).get("share_pct", 50.0)
    g1_l = ml.get("gpu1", {}).get("share_pct", 50.0)
    mx = np.arange(2)
    bs0 = ax.bar(mx - 0.18, [g0_s, g0_l], 0.34, color=C_EMERALD, label="gpu0 (:8001)")
    bs1 = ax.bar(mx + 0.18, [g1_s, g1_l], 0.34, color=C_SKY, label="gpu1 (:8002)")
    ax.axhline(50.0, color=C_SLATE, linestyle="--", linewidth=1.2, alpha=0.7, label="สมดุลสมบูรณ์ 50%")
    ax.set_xticks(mx)
    ax.set_xticklabels(["คำถามสั้นทั้งหมด\n(0% ยาว)", "คำถามสั้นผสมยาว\n(25% ยาว 600 โทเคน)"], fontsize=9.5)
    ax.set_ylabel("สัดส่วนคำขอที่แต่ละ GPU รับ (%)")
    ax.set_ylim(0, 72)
    ax.set_title("ความสมดุลของ NGINX least_conn ระหว่าง gpu0 และ gpu1", fontsize=10.8, fontweight="bold")
    ax.grid(axis="y", alpha=0.25)
    ax.legend(fontsize=8.5, loc="upper right")
    for bar in list(bs0) + list(bs1):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1.0, f"{bar.get_height():.1f}%", ha="center", va="bottom", fontsize=9, fontweight="bold")

    fig.suptitle("การคุม Concurrency Cap และความสมดุลของ NGINX least_conn บน 2× RTX 4090", fontsize=13, fontweight="bold", y=0.99)
    plt.tight_layout(rect=[0, 0, 1, 0.94])
    fig.savefig(IMG_DIR / "03_concurrency_and_mix.png")
    plt.close(fig)

    # ── Chart 4: Mid-Stream Failover Timeline (Kill gpu1 :8002) ──
    fig, axes = plt.subplots(2, 1, figsize=(13.5, 6.2), sharex=True)
    fig.patch.set_facecolor("white")
    ps = (fail or {}).get("per_second", [])
    ts = [r["t"] for r in ps]
    toks = [r["tokens"] for r in ps]
    errs = [r["errors"] for r in ps]
    r_g0 = [r.get("replicas", {}).get("gpu0", {}).get("running", 0) for r in ps]
    r_g1 = [r.get("replicas", {}).get("gpu1", {}).get("running", 0) for r in ps]

    # Estimate cut second from gpu1 dropping to 0 or errors spike
    cut_t = 20
    for r in ps:
        if r["t"] >= 10 and (r["errors"] > 0 or r.get("replicas", {}).get("gpu1", {}).get("running", 0) == 0):
            cut_t = r["t"]
            break

    errors_after_cut = sum(r["errors"] for r in ps if r["t"] >= cut_t + 3)

    ax = axes[0]
    ax.plot(ts, toks, color=C_EMERALD, linewidth=2.3, label="Throughput รวม (tok/s)")
    ax.axvline(cut_t, color=C_RED, linestyle="--", linewidth=2.0, label=f"ปิด gpu1 (:8002) กลางสตรีมที่ t={cut_t}s")
    ax.set_ylabel("tok/s")
    ax.set_title(f"ทดสอบ Failover: ปิด gpu1 กลางสตรีม -> NGINX ตัดไป gpu0 อัตโนมัติ (Error หลังฟื้นตัว = {errors_after_cut})", fontsize=11.5, fontweight="bold")
    ax.grid(alpha=0.25)
    ax.legend(loc="upper right", fontsize=9)

    ax = axes[1]
    ax.plot(ts, r_g0, color=C_SKY, linewidth=2.2, label="งานกำลังรันบน gpu0 (:8001)")
    ax.plot(ts, r_g1, color=C_AMBER, linewidth=2.2, label="งานกำลังรันบน gpu1 (:8002)")
    ax.bar(ts, errs, color=C_RED, alpha=0.55, width=0.6, label="Error ต่อวินาที (เฉพาะสตรีมที่ค้างตอนถูก kill)")
    ax.axvline(cut_t, color=C_RED, linestyle="--", linewidth=2.0)
    ax.set_xlabel("เวลาตั้งแต่เริ่มทดสอบ (วินาที)")
    ax.set_ylabel("จำนวนคำขอ / Error")
    ax.grid(alpha=0.25)
    ax.legend(loc="upper right", fontsize=9)

    plt.tight_layout()
    fig.savefig(IMG_DIR / "04_failover_timeline.png")
    plt.close(fig)

    # ── Export lb_summary.json for Next.js /telemetry page & README/Slides ──
    summary = {
        "measuredOn": f"Vast.ai 2× RTX 4090 ({meta.get('location', 'Spain, ES')}, {meta.get('inet_down_mbps', 6110)} Mbps)",
        "model": "Qwen/Qwen3-VL-2B-Instruct + LoRA (receipt-vlm)",
        "n1SpeedTps": n1.get("speed_mean_tps") if n1 else None,
        "n1TtftMs": round((n1.get("ttft_mean_s") or 0) * 1000, 1) if n1 else None,
        "fastSloMinTps": n1.get("fast_slo_speed_min_tps") if n1 else None,
        "scalingEfficiencyPct": eff_tps,
        "capacityScalingEfficiencyPct": eff_users,
        "ocrDp1Rpm": ocr1_rpm,
        "ocrDp2Rpm": ocr2_rpm,
        "ocrDp1P50s": ocr1.get("latency_p50_s") if ocr1 else None,
        "ocrDp2P50s": ocr2.get("latency_p50_s") if ocr2 else None,
        "ocrSpeedup": ocr_speedup,
        "cap32": {"users": c32.get("users"), "ttftP95": c32.get("ttft_p95_s"), "speedP5": c32.get("speed_p5_tok_s"), "tps": c32.get("throughput_tok_s")},
        "cap256": {"users": c256.get("users"), "ttftP95": c256.get("ttft_p95_s"), "speedP5": c256.get("speed_p5_tok_s"), "tps": c256.get("throughput_tok_s")},
        "mixBalance": {"gpu0Pct": round(g0_l, 1), "gpu1Pct": round(g1_l, 1), "shortGpu0Pct": round(g0_s, 1), "shortGpu1Pct": round(g1_s, 1)},
        "failoverCutSec": cut_t,
        "failoverErrorsAtCut": sum(r["errors"] for r in ps if cut_t <= r["t"] < cut_t + 3),
        "failoverErrorsAfterCut": errors_after_cut,
        "table": [
            {
                "config": "1 GPU · Sequential (max-num-seqs=1)",
                "gpus": 1,
                "cap": 1,
                "stdUsers": seq_u,
                "fastUsers": seq_u,
                "peakTps": f"{seq_tps:,}",
                "ttftP95": f"{at_cap_ttft(seq):.3f} s",
                "efficiency": "Baseline",
            },
            {
                "config": "1 GPU · Continuous Batching (max-num-seqs=256)",
                "gpus": 1,
                "cap": 256,
                "stdUsers": dp1_u,
                "fastUsers": dp1_fu,
                "peakTps": f"{dp1_tps:,}",
                "ttftP95": f"{at_cap_ttft(dp1):.3f} s",
                "efficiency": "100% (1 GPU ref)",
            },
            {
                "config": "2 GPUs · Data Parallelism + NGINX least_conn (NGINX least_conn)",
                "gpus": 2,
                "cap": 256,
                "stdUsers": dp2_u,
                "fastUsers": dp2_fu,
                "peakTps": f"{dp2_tps:,}",
                "ttftP95": f"{at_cap_ttft(dp2):.3f} s",
                "efficiency": f"{eff_tps}% (Throughput) / {eff_users}% (Users)",
            },
        ],
    }
    WEB_DATA.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    (LB_DIR / "lb_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print("GENERATED 4 CHARTS + lb_summary.json:", json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
