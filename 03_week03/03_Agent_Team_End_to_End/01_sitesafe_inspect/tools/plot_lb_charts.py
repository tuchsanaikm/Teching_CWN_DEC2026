#!/usr/bin/env python3
"""Generate high-DPI Thai-labeled LAB 6 benchmark charts on 2x RTX 4090 for SiteSafe Inspect
and export public/data/lab6-benchmarks.json for the Next.js /telemetry dashboard."""
import json
import os
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
LB_DIR = ROOT / "results" / "lb"
IMG_DIR = ROOT / "results" / "images"
WEB_JSON = ROOT / "code_reference" / "app" / "web" / "public" / "data" / "lab6-benchmarks.json"

IMG_DIR.mkdir(parents=True, exist_ok=True)
WEB_JSON.parent.mkdir(parents=True, exist_ok=True)

# Pick a Thai-capable font on Windows/Linux
THAI_FONTS = ["Leelawadee UI", "Tahoma", "Sarabun", "Noto Sans Thai", "DejaVu Sans"]
avail = {f.name for f in fm.fontManager.ttflist}
chosen_font = next((f for f in THAI_FONTS if f in avail), "DejaVu Sans")
plt.rcParams.update({
    "font.family": chosen_font,
    "axes.edgecolor": "#cbd5e1",
    "axes.linewidth": 1.0,
    "axes.grid": True,
    "grid.color": "#e2e8f0",
    "grid.linestyle": "--",
    "grid.alpha": 0.7,
    "figure.facecolor": "#ffffff",
    "axes.facecolor": "#f8fafc",
    "savefig.dpi": 200,
})


def load_json(name: str):
    p = LB_DIR / f"{name}.json"
    if not p.exists():
        raise FileNotFoundError(f"Missing {p}")
    return json.loads(p.read_text(encoding="utf-8"))


def level_at_cap(doc):
    cap = doc.get("capacity") or 0
    levels = doc.get("levels") or []
    matches = [lv for lv in levels if lv.get("users") == cap and lv.get("pass")]
    if matches:
        return matches[-1]
    passing = [lv for lv in levels if lv.get("pass")]
    return passing[-1] if passing else (levels[0] if levels else {})


def best_per_user(doc):
    by_n = {}
    for lv in doc.get("levels") or []:
        n = lv["users"]
        p95 = lv["latency_ms"]["p95"]
        if p95 is None:
            continue
        prev = by_n.get(n)
        if prev is None or (lv["pass"] and not prev["pass"]) or (lv["pass"] == prev["pass"] and p95 < prev["latency_ms"]["p95"]):
            by_n[n] = lv
    return [by_n[k] for k in sorted(by_n)]


def gpu_str(lv):
    u = lv.get("gpu_util_pct") or []
    if not u:
        return "-"
    return " / ".join(f"{x:.0f}%" for x in u)


def main():
    base = load_json("base")
    batch = load_json("batch")
    multi = load_json("multi")
    gpu2_lc = load_json("gpu2_lc")
    rr_slow = load_json("rr_slow")
    lc_slow = load_json("lc_slow")
    fail_off = load_json("fail_off")
    fail_on = load_json("fail_on")
    meta = load_json("instance_meta")

    designs = [
        ("base", "1. ฐานเดิม\n1 GPU · 1 Process\nSingle", "1 GPU · 1 Process · Single", base, "#64748b"),
        ("batch", "2. Micro-batch\n1 GPU · 1 Process\nMicro-batch", "1 GPU · 1 Process · Micro-batch", batch, "#0284c7"),
        ("multi", "3. 4 Processes/GPU\n1 GPU · 4 Processes\nMicro-batch", "1 GPU · 4 Processes · Micro-batch", multi, "#7c3aed"),
        ("gpu2_lc", "4. Design #4 เต็มระบบ\n2× RTX 4090 · 8 Processes\nNGINX least_conn", "2× RTX 4090 · 8 Processes · NGINX least_conn", gpu2_lc, "#059669"),
    ]

    # ---------- Chart 1: 4 Designs Capacity & Throughput ----------
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.5, 5.6))
    labels = [d[1] for d in designs]
    caps = [d[3].get("capacity") or 0 for d in designs]
    rpss = [d[3].get("max_throughput_rps") or 0 for d in designs]
    colors = [d[4] for d in designs]
    x = np.arange(len(designs))

    b1 = ax1.bar(x, caps, color=colors, width=0.58, edgecolor="#0f172a", linewidth=0.8)
    ax1.set_title("จำนวนผู้ใช้พร้อมกันสูงสุดที่ผ่านเกณฑ์ (p95 ≤ 500 ms)", fontsize=12.5, fontweight="bold", pad=12)
    ax1.set_ylabel("จำนวนผู้ใช้พร้อมกัน (Users)", fontsize=11, fontweight="bold")
    ax1.set_xticks(x)
    ax1.set_xticklabels(labels, fontsize=9.2)
    ax1.set_ylim(0, max(caps) * 1.24)
    base_cap = max(1, caps[0])
    for bar, c in zip(b1, caps):
        mult = c / base_cap
        ax1.text(bar.get_x() + bar.get_width() / 2, c + max(caps) * 0.025,
                 f"{c} users\n({mult:.1f}×)", ha="center", va="bottom", fontsize=10, fontweight="bold", color="#0f172a")

    b2 = ax2.bar(x, rpss, color=colors, width=0.58, edgecolor="#0f172a", linewidth=0.8)
    ax2.set_title("อัตราการตรวจภาพสูงสุด (Max Throughput)", fontsize=12.5, fontweight="bold", pad=12)
    ax2.set_ylabel("ภาพต่อวินาที (Requests / Second)", fontsize=11, fontweight="bold")
    ax2.set_xticks(x)
    ax2.set_xticklabels(labels, fontsize=9.2)
    ax2.set_ylim(0, max(rpss) * 1.24)
    base_rps = max(1.0, rpss[0])
    for bar, r in zip(b2, rpss):
        mult = r / base_rps
        ax2.text(bar.get_x() + bar.get_width() / 2, r + max(rpss) * 0.025,
                 f"{r:.1f} req/s\n({mult:.1f}×)", ha="center", va="bottom", fontsize=10, fontweight="bold", color="#0f172a")

    fig.suptitle(f"SiteSafe Inspect (YOLO11s) บน 1 โหนด × 2× RTX 4090 — เปรียบเทียบ 4 รูปแบบสถาปัตยกรรม",
                 fontsize=14, fontweight="bold", y=0.99)
    fig.tight_layout(rect=[0, 0, 1, 0.94])
    fig.savefig(IMG_DIR / "01_capacity_4designs.png")
    plt.close(fig)

    # ---------- Chart 2: Round Robin vs Least Connections (GPU 1 3x slower) ----------
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5.2))
    rr_cap = rr_slow.get("capacity") or 0
    lc_cap = lc_slow.get("capacity") or 0
    rr_rps = rr_slow.get("max_throughput_rps") or 0
    lc_rps = lc_slow.get("max_throughput_rps") or 0

    bars = ax1.bar(["Round Robin\n(วนแจกเท่ากัน)", "Least Connections\n(เลือก Process ที่ว่างกว่า)"], [rr_cap, lc_cap],
                   color=["#dc2626", "#059669"], width=0.5, edgecolor="#0f172a")
    ax1.set_title("ความจุผู้ใช้เมื่อ GPU 1 ช้าลง 3 เท่า", fontsize=12.5, fontweight="bold", pad=10)
    ax1.set_ylabel("จำนวนผู้ใช้พร้อมกัน (Users)", fontsize=11, fontweight="bold")
    ax1.set_ylim(0, max(rr_cap, lc_cap, 1) * 1.28)
    for bar, val, rps in zip(bars, [rr_cap, lc_cap], [rr_rps, lc_rps]):
        ax1.text(bar.get_x() + bar.get_width() / 2, val + max(rr_cap, lc_cap, 1) * 0.03,
                 f"{val} users\n({rps:.1f} req/s)", ha="center", va="bottom", fontsize=10.5, fontweight="bold")

    # GPU share at capacity
    rr_lv = level_at_cap(rr_slow)
    lc_lv = level_at_cap(lc_slow)
    def gpu_shares(lv):
        srvs = lv.get("servers") or {}
        g0 = sum(v.get("share_pct", 0) for k, v in srvs.items() if k.startswith("gpu0"))
        g1 = sum(v.get("share_pct", 0) for k, v in srvs.items() if k.startswith("gpu1"))
        return g0, g1

    rr_g0, rr_g1 = gpu_shares(rr_lv)
    lc_g0, lc_g1 = gpu_shares(lc_lv)
    x2 = np.arange(2)
    w = 0.34
    ax2.bar(x2 - w / 2, [rr_g0, lc_g0], width=w, label="GPU 0 (ความเร็วปกติ)", color="#0284c7", edgecolor="#0f172a")
    ax2.bar(x2 + w / 2, [rr_g1, lc_g1], width=w, label="GPU 1 (ช้ากว่า 3 เท่า)", color="#f59e0b", edgecolor="#0f172a")
    ax2.set_title("สัดส่วนงานที่ถูกส่งไปแต่ละ GPU ณ จุดความจุ", fontsize=12.5, fontweight="bold", pad=10)
    ax2.set_ylabel("สัดส่วนคำขอ (%)", fontsize=11, fontweight="bold")
    ax2.set_xticks(x2)
    ax2.set_xticklabels(["Round Robin", "Least Connections"], fontsize=10.5)
    ax2.set_ylim(0, 100)
    ax2.legend(loc="upper right", frameon=True)
    for i, (g0, g1) in enumerate([(rr_g0, rr_g1), (lc_g0, lc_g1)]):
        ax2.text(i - w / 2, g0 + 2, f"{g0:.1f}%", ha="center", va="bottom", fontsize=10, fontweight="bold")
        ax2.text(i + w / 2, g1 + 2, f"{g1:.1f}%", ha="center", va="bottom", fontsize=10, fontweight="bold")

    gain_pct = ((lc_cap - rr_cap) / max(1, rr_cap)) * 100
    fig.suptitle(f"ผลจริงบน 2× RTX 4090: NGINX least_conn รับผู้ใช้เพิ่ม +{gain_pct:.0f}% เมื่อการ์ดหนึ่งช้าลง",
                 fontsize=13.5, fontweight="bold", y=0.99)
    fig.tight_layout(rect=[0, 0, 1, 0.93])
    fig.savefig(IMG_DIR / "02_rr_vs_lc_slow.png")
    plt.close(fig)

    # ---------- Chart 3: Failover OFF vs ON timeline ----------
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(13, 6.8), sharex=True)
    for ax, doc, title, col_ok in [
        (ax1, fail_off, "Failover OFF (ไม่มี proxy_next_upstream / max_fails=0) — ฆ่า GPU 1 ที่วินาทีที่ 15", "#64748b"),
        (ax2, fail_on, "Failover ON (proxy_next_upstream error timeout non_idempotent + max_fails=1) — ฆ่า GPU 1 ที่วินาทีที่ 15", "#059669"),
    ]:
        lv = doc["levels"][0]
        ps = lv.get("per_second") or []
        secs = [r["second"] for r in ps]
        oks = [r["ok"] for r in ps]
        errs = [r["errors"] for r in ps]
        ax.plot(secs, oks, color=col_ok, linewidth=2.4, marker="o", markersize=4, label="คำขอสำเร็จ (req/s)")
        ax.bar(secs, errs, color="#dc2626", alpha=0.8, width=0.6, label="คำขอผิดพลาด (Errors/s)")
        ax.axvline(15, color="#b91c1c", linestyle="--", linewidth=2, label="SIGKILL GPU 1 (วินาทีที่ 15)")
        ax.set_title(title, fontsize=11.5, fontweight="bold", loc="left")
        ax.set_ylabel("คำขอต่อวินาที", fontsize=10.5, fontweight="bold")
        ax.legend(loc="upper right", ncol=3, fontsize=9, frameon=True)
        tot_err = lv.get("errors", 0)
        err_pct = lv.get("error_pct", 0.0)
        badge_col = "#dc2626" if tot_err > 0 else "#059669"
        ax.text(0.015, 0.84, f"รวมผิดพลาดในหน้าต่างวัด: {tot_err} คำขอ ({err_pct:.2f}%)",
                transform=ax.transAxes, fontsize=10.5, fontweight="bold", color="#ffffff",
                bbox=dict(boxstyle="round,pad=0.35", facecolor=badge_col, edgecolor="none"))
    ax2.set_xlabel("เวลาของการทดสอบ (วินาที · ผู้ใช้พร้อมกัน 80 คน)", fontsize=11, fontweight="bold")
    fig.suptitle("ทดสอบความทนทานเมื่อ GPU 1 ล่มกะทันหัน (SIGKILL) — Failover OFF vs ON",
                 fontsize=14, fontweight="bold", y=0.99)
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    fig.savefig(IMG_DIR / "03_failover_comparison.png")
    plt.close(fig)

    # ---------- Chart 4: Latency p95 & Throughput vs N Users ----------
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.5, 5.5))
    for _, _, short_lbl, doc, color in designs:
        pts = best_per_user(doc)
        ns = [p["users"] for p in pts]
        p95s = [p["latency_ms"]["p95"] for p in pts]
        rpss_pts = [p["throughput_rps"] for p in pts]
        ax1.plot(ns, p95s, marker="o", linewidth=2.3, color=color, label=short_lbl)
        ax2.plot(ns, rpss_pts, marker="s", linewidth=2.3, color=color, label=short_lbl)

    ax1.axhline(500, color="#dc2626", linestyle="--", linewidth=1.8, label="เส้นเกณฑ์ SLO (p95 = 500 ms)")
    ax1.set_xscale("log", base=2)
    ax1.set_title("ความหน่วง p95 เทียบจำนวนผู้ใช้พร้อมกัน (N)", fontsize=12, fontweight="bold")
    ax1.set_xlabel("จำนวนผู้ใช้พร้อมกัน (N · สเกลลอการิทึมฐาน 2)", fontsize=10.5, fontweight="bold")
    ax1.set_ylabel("p95 Latency (มิลลิวินาที)", fontsize=10.5, fontweight="bold")
    ax1.set_ylim(0, min(2000, max(650, max(p["latency_ms"]["p95"] for _, _, _, d, _ in designs for p in best_per_user(d) if p["latency_ms"]["p95"] < 2500) * 1.1)))
    ax1.legend(loc="upper left", fontsize=8.5, frameon=True)

    ax2.set_xscale("log", base=2)
    ax2.set_title("อัตราการตรวจภาพ (Throughput) เทียบจำนวนผู้ใช้พร้อมกัน (N)", fontsize=12, fontweight="bold")
    ax2.set_xlabel("จำนวนผู้ใช้พร้อมกัน (N · สเกลลอการิทึมฐาน 2)", fontsize=10.5, fontweight="bold")
    ax2.set_ylabel("Throughput (ภาพต่อวินาที)", fontsize=10.5, fontweight="bold")
    ax2.legend(loc="upper left", fontsize=8.5, frameon=True)

    fig.suptitle("กราฟ Latency p95 และ Throughput ของ YOLO11s บน 2× RTX 4090", fontsize=14, fontweight="bold", y=0.99)
    fig.tight_layout(rect=[0, 0, 1, 0.94])
    fig.savefig(IMG_DIR / "04_latency_throughput_curves.png")
    plt.close(fig)

    # ---------- Export summary JSON for Next.js /telemetry & Slides ----------
    fail_off_lv = fail_off["levels"][0]
    fail_on_lv = fail_on["levels"][0]
    summary = {
        "machine": f"{meta.get('num_gpus', 2)}× {meta.get('gpu_name', 'RTX 4090')} ({meta.get('geolocation', '')}, {int(meta.get('vcpus', 48))} vCPU)",
        "instance_meta": meta,
        "designs": [
            {
                "id": did,
                "label": short_lbl,
                "capacity": doc.get("capacity") or 0,
                "max_rps": doc.get("max_throughput_rps") or 0,
                "p95_at_cap_ms": level_at_cap(doc).get("latency_ms", {}).get("p95") or 0,
                "gpu_util_pct": gpu_str(level_at_cap(doc)),
                "batch_mean": level_at_cap(doc).get("model", {}).get("batch_mean_per_call") or 1.0,
                "model_ms_mean": level_at_cap(doc).get("model", {}).get("model_ms_mean") or 0.0,
            }
            for did, _, short_lbl, doc, _ in designs
        ],
        "slow_gpu": {
            "rr_capacity": rr_cap,
            "lc_capacity": lc_cap,
            "rr_rps": rr_rps,
            "lc_rps": lc_rps,
            "rr_gpu0_pct": round(rr_g0, 1),
            "rr_gpu1_pct": round(rr_g1, 1),
            "lc_gpu0_pct": round(lc_g0, 1),
            "lc_gpu1_pct": round(lc_g1, 1),
        },
        "failover": {
            "users": fail_off_lv.get("users", 80),
            "off_errors": fail_off_lv.get("errors", 0),
            "off_error_pct": fail_off_lv.get("error_pct", 0.0),
            "off_after_errors": fail_off_lv.get("after", {}).get("errors", 0),
            "on_errors": fail_on_lv.get("errors", 0),
            "on_error_pct": fail_on_lv.get("error_pct", 0.0),
            "on_after_errors": fail_on_lv.get("after", {}).get("errors", 0),
            "on_in_flight_errors": fail_on_lv.get("in_flight_at_event", {}).get("errors", 0),
        },
    }
    WEB_JSON.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    (LB_DIR / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print("Generated 4 charts in", IMG_DIR, "and exported", WEB_JSON)
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
