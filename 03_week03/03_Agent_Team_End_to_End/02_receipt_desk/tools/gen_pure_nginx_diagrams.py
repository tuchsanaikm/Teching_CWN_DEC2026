#!/usr/bin/env python3
"""
Generate crisp, publication-grade Thai technical diagrams for ReceiptDesk (Pure LAB 7 NGINX + 2x vLLM).
Direct HTTP/SSE + NGINX least_conn + 2x vLLM Data Parallelism + PostgreSQL 16 state diagrams.
Outputs:
  - images/theory/arch-nginx-vllm.png
  - images/theory/state-flow.png
  - images/theory/trace-nginx.png
  - images/theory/lab6-vs-lab7.png
  - plan/dag.png
  - plan/gantt-plan.png
  - plan/compare.png
  - plan/whatif/gantt-receiptdesk-2.png
"""
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

ROOT = Path(__file__).resolve().parents[1]

# Configure clean Thai font on Windows
plt.rcParams["font.family"] = ["Tahoma", "Leelawadee UI", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

NAVY = "#0F172A"
SLATE = "#334155"
MUTED = "#64748B"
BG = "#F8FAFC"
WHITE = "#FFFFFF"
BLUE = "#0284C7"
BLUE_LT = "#E0F2FE"
TEAL = "#0D9488"
TEAL_LT = "#CCFBF1"
GREEN = "#15803D"
GREEN_LT = "#DCFCE7"
AMBER = "#D97706"
AMBER_LT = "#FEF3C7"
RED = "#DC2626"
RED_LT = "#FEE2E2"
PURPLE = "#7C3AED"
PURPLE_LT = "#EDE9FE"
BORDER = "#CBD5E1"


def box(ax, x, y, w, h, title, body="", fc=WHITE, ec=SLATE, title_color=NAVY, lw=1.6, r=0.18, ts=11, bs=9):
    p = FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0.04,rounding_size={r}",
                       facecolor=fc, edgecolor=ec, linewidth=lw, zorder=3)
    ax.add_patch(p)
    if body:
        ax.text(x + w / 2, y + h * 0.66, title, ha="center", va="center",
                fontsize=ts, fontweight="bold", color=title_color, zorder=4)
        ax.text(x + w / 2, y + h * 0.28, body, ha="center", va="center",
                fontsize=bs, color=SLATE, zorder=4, linespacing=1.32)
    else:
        ax.text(x + w / 2, y + h / 2, title, ha="center", va="center",
                fontsize=ts, fontweight="bold", color=title_color, zorder=4, linespacing=1.3)


def arrow(ax, x1, y1, x2, y2, label="", color=SLATE, rad=0.0, lw=1.8, lx_off=0.0, ly_off=0.22, ls="-"):
    a = FancyArrowPatch((x1, y1), (x2, y2),
                        connectionstyle=f"arc3,rad={rad}",
                        arrowstyle="-|>,head_length=7,head_width=4.5",
                        color=color, linewidth=lw, linestyle=ls, zorder=5)
    ax.add_patch(a)
    if label:
        mx, my = (x1 + x2) / 2 + lx_off, (y1 + y2) / 2 + ly_off
        ax.text(mx, my, label, ha="center", va="center", fontsize=8.5, fontweight="bold",
                color=color, bbox=dict(boxstyle="round,pad=0.18", fc=WHITE, ec="none", alpha=0.92), zorder=6)


def make_arch():
    fig, ax = plt.subplots(figsize=(14, 7.6), dpi=160)
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 7.6)
    ax.axis("off")

    ax.text(0.4, 7.22, "สถาปัตยกรรม ReceiptDesk · NGINX least_conn + 2× vLLM Data Parallelism",
            fontsize=15, fontweight="bold", color=NAVY)
    ax.text(0.4, 6.86, "สถาปัตยกรรมเรียบง่าย 2 ชั้น (Web + NGINX + 2× vLLM) · ฝั่งเว็บเก็บข้อมูลจริงใน PostgreSQL · ฝั่ง GPU ใช้ 1 โหนด × 2× RTX 4090 รองรับทั้ง Vision OCR และ SSE Copilot",
            fontsize=10, color=MUTED)

    # Zone 1: Users
    p_u = FancyBboxPatch((0.3, 1.0), 2.1, 5.4, boxstyle="round,pad=0.06,rounding_size=0.22",
                         fc="#F1F5F9", ec=BORDER, lw=1.4, zorder=1)
    ax.add_patch(p_u)
    ax.text(1.35, 6.12, "ผู้ใช้ 4 บทบาท", ha="center", fontsize=11, fontweight="bold", color=NAVY)
    box(ax, 0.48, 4.75, 1.74, 1.0, "พนักงานบัญชี", "อัปโหลด · ตรวจแก้\nยืนยัน · Copilot", fc=WHITE, ec=BLUE, ts=10, bs=8.5)
    box(ax, 0.48, 3.55, 1.74, 1.0, "หัวหน้าทีมบัญชี", "ตั้งงานด่วน (≤10 ใบ)\nดูงานค้าง · เปิดใบกลับ", fc=WHITE, ec=TEAL, ts=10, bs=8.5)
    box(ax, 0.48, 2.35, 1.74, 1.0, "เจ้าของสำนักงาน", "รายงานรายเดือน CSV\nTelemetry · Insights", fc=WHITE, ec=PURPLE, ts=10, bs=8.5)
    box(ax, 0.48, 1.15, 1.74, 1.0, "ลูกค้า (คุณสมชาย)", "พอร์ทัลเฉพาะร้านตน\nเห็นหลังยืนยันเท่านั้น", fc=WHITE, ec=AMBER, ts=10, bs=8.5)

    # Zone 2: Local Docker Compose
    p_w = FancyBboxPatch((2.85, 0.95), 4.65, 5.5, boxstyle="round,pad=0.06,rounding_size=0.22",
                         fc="#EFF6FF", ec="#93C5FD", lw=1.6, zorder=1)
    ax.add_patch(p_w)
    ax.text(5.17, 6.18, "เครื่องสำนักงาน · Docker Compose (receiptdesk-nginx)", ha="center",
            fontsize=10.0, fontweight="bold", color="#1D4ED8")
    box(ax, 3.05, 4.48, 4.25, 1.32, "Web App · Next.js 16 + Tailwind v4 (:3420)",
        "Upload · Split-Pane Review (BR-05 สด) · /copilot (SSE Proxy)\n/telemetry · /reports (CSV) · /portal · กติกา BR-01..14",
        fc=WHITE, ec=BLUE, title_color="#0369A1", ts=9.5, bs=8.0)
    box(ax, 3.05, 2.82, 4.25, 1.28, "Async Dispatcher (PostgreSQL Outbox)",
        "ดึงงานด้วย FOR UPDATE SKIP LOCKED · สลับด่วน:ปกติ = 4:1\nลองซ้ำสูงสุด 3 ครั้ง → ครบ 3 ย้ายสถานะ unreadable (ให้คนพิมพ์เอง)",
        fc=WHITE, ec=TEAL, title_color="#0F766E", ts=9.5, bs=7.9)
    box(ax, 3.05, 1.18, 2.02, 1.22, "PostgreSQL 16",
        "11 ตาราง · สถานะใบ\nเพดาน 400 · Audit Log", fc=BLUE_LT, ec=BLUE, ts=9.6, bs=8.0)
    box(ax, 5.28, 1.18, 2.02, 1.22, "Volume uploads",
        "รูปใบเสร็จต้นฉบับ\n(ไม่หายแม้ลบ GPU)", fc=AMBER_LT, ec=AMBER, ts=9.6, bs=8.0)

    # Zone 3: Vast.ai 2x RTX 4090
    p_g = FancyBboxPatch((8.05, 0.95), 5.65, 5.5, boxstyle="round,pad=0.06,rounding_size=0.22",
                         fc="#ECFDF5", ec="#6EE7B7", lw=1.8, zorder=1)
    ax.add_patch(p_g)
    ax.text(10.88, 6.18, "Vast.ai · 1 โหนด × 2× RTX 4090 (Data Parallelism 2×1)", ha="center",
            fontsize=10.2, fontweight="bold", color="#065F46")
    box(ax, 8.24, 2.22, 2.15, 3.55, "NGINX 1.27\nLoad Balancer\n(:8080)",
        "• least_conn\n• proxy_buffering off\n• Bearer API Key\n• X-Replica header\n• Passive Failover\n  (max_fails=1, 30s)",
        fc=GREEN_LT, ec=GREEN, title_color="#14532D", ts=10.0, bs=8.2)
    box(ax, 10.82, 4.12, 2.68, 1.65, "vLLM Replica 0 · GPU 0",
        "พอร์ต 127.0.0.1:8001\nQwen3-VL-2B + Merged LoRA\nContinuous Batching\n(--max-num-seqs 256)",
        fc=WHITE, ec=GREEN, title_color="#065F46", ts=9.5, bs=8.1)
    box(ax, 10.82, 2.22, 2.68, 1.65, "vLLM Replica 1 · GPU 1",
        "พอร์ต 127.0.0.1:8002\nQwen3-VL-2B + Merged LoRA\nContinuous Batching\n(--max-num-seqs 256)",
        fc=WHITE, ec=GREEN, title_color="#065F46", ts=9.5, bs=8.1)
    box(ax, 8.24, 1.15, 5.26, 0.80,
        "ผลวัดจริง: 640 ผู้ใช้ (Standard SLO) · 257 ผู้ใช้ (Fast SLO)\n28,541 tok/s · 2,643.9 ใบเสร็จ/นาที · Scaling 101.6%",
        fc="#064E3B", ec="#064E3B", title_color=WHITE, ts=8.5)

    # Arrows (clean non-overlapping paths)
    arrow(ax, 2.42, 5.05, 3.05, 5.12, "HTTP / SSE", color=BLUE, ly_off=0.28)
    arrow(ax, 5.17, 4.48, 5.17, 4.10, "รายการรอส่ง", color=TEAL, lw=1.5, lx_off=0.58, ly_off=0.0)
    arrow(ax, 4.06, 2.82, 4.06, 2.40, "", color=BLUE, lw=1.5)
    arrow(ax, 6.29, 2.82, 6.29, 2.40, "", color=AMBER, lw=1.5)
    arrow(ax, 7.30, 5.10, 8.24, 4.82, "SSE Stream\nCopilot", color=PURPLE, ly_off=0.35)
    arrow(ax, 7.30, 3.45, 8.24, 3.55, "Vision OCR\n(JSON)", color=TEAL, ly_off=-0.38)
    arrow(ax, 10.39, 4.55, 10.82, 4.92, "gpu0", color=GREEN, ly_off=0.22)
    arrow(ax, 10.39, 3.30, 10.82, 3.00, "gpu1", color=GREEN, ly_off=-0.24)

    # Bottom caption
    ax.text(7.0, 0.42, "ข้อมูลจริงและรูปต้นฉบับอยู่บนเครื่องสำนักงานเสมอ · คลัสเตอร์ 2× RTX 4090 เป็น Stateless ลบทิ้งหลังใช้งานได้โดยไม่สูญเสียข้อมูล",
            ha="center", fontsize=9.5, color=SLATE, style="italic")

    out = ROOT / "images" / "theory" / "arch-nginx-vllm.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=160, bbox_inches="tight", facecolor=BG)
    plt.close(fig)
    print("WROTE", out)


def make_state_flow():
    fig, ax = plt.subplots(figsize=(13.5, 5.8), dpi=160)
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)
    ax.set_xlim(0, 13.5)
    ax.set_ylim(0, 5.8)
    ax.axis("off")

    ax.text(0.4, 5.4, "วงจรสถานะของใบเสร็จ 5 สถานะใน PostgreSQL (จัดการสถานะใน PostgreSQL 16 โดยตรง)",
            fontsize=14, fontweight="bold", color=NAVY)
    ax.text(0.4, 5.05, "ทุกการเปลี่ยนสถานะบันทึกในตาราง receipt_events · ลองอ่านไม่สำเร็จครบ 3 ครั้งจะหยุดส่งซ้ำอัตโนมัติ (BR-07)",
            fontsize=9.8, color=MUTED)

    box(ax, 0.5, 2.55, 2.1, 1.35, "1. รออ่าน\n(queued)", "รับไฟล์ลง volume แล้ว\nผ่าน BR-01..03, BR-11", fc=BLUE_LT, ec=BLUE, ts=10.5, bs=8.5)
    box(ax, 3.6, 2.55, 2.35, 1.35, "2. กำลังอ่าน\n(processing)", "Dispatcher หยิบส่ง\nNGINX → vLLM (attempts+1)", fc=PURPLE_LT, ec=PURPLE, ts=10.5, bs=8.5)
    box(ax, 7.1, 3.45, 2.35, 1.35, "3. รอตรวจ\n(review)", "ได้ JSON 5 ช่องแล้ว\nคำนวณธง BR-04 / BR-05", fc=AMBER_LT, ec=AMBER, ts=10.5, bs=8.5)
    box(ax, 7.1, 1.05, 2.35, 1.35, "4. อ่านไม่ได้\n(unreadable)", "ล้มเหลวครบ 3 ครั้ง (BR-07)\nหยุดส่งซ้ำ · ไปหน้าพิมพ์เอง", fc=RED_LT, ec=RED, ts=10.5, bs=8.5)
    box(ax, 10.65, 2.25, 2.35, 1.45, "5. ยืนยันแล้ว\n(confirmed)", "ยอดรวม ≥ 0.01 บาท (BR-06)\nเข้าสรุปรายเดือน & พอร์ทัล", fc=GREEN_LT, ec=GREEN, ts=10.5, bs=8.5)

    arrow(ax, 2.6, 3.35, 3.6, 3.35, "หยิบงาน\n(ด่วน:ปกติ 4:1)", color=BLUE, ly_off=0.34)
    arrow(ax, 3.6, 2.75, 2.6, 2.75, "ล้มเหลวครั้ง 1–2\nลองใหม่", color=RED, rad=0.25, ly_off=-0.42)
    arrow(ax, 5.95, 3.55, 7.1, 4.1, "อ่านสำเร็จ", color=GREEN, ly_off=0.25)
    arrow(ax, 5.95, 2.85, 7.1, 1.85, "ล้มเหลวครบ 3 ครั้ง\n(BR-07)", color=RED, ly_off=-0.32)
    arrow(ax, 9.45, 4.05, 10.65, 3.3, "พนักงานยืนยัน", color=GREEN, ly_off=0.26)
    arrow(ax, 9.45, 1.75, 10.65, 2.6, "พนักงานพิมพ์ 5 ช่อง\nแล้วยืนยัน", color=TEAL, ly_off=-0.35)
    arrow(ax, 11.4, 3.7, 8.8, 4.8, "หัวหน้าทีมเปิดใบกลับ (reopen)", color=AMBER, rad=0.28, ly_off=0.35, ls="--")

    ax.text(6.75, 0.35, "หมายเหตุ: สถานะ unreadable ไม่มีเส้นกลับไป queued (FR-16) · การตั้งเป็นงานด่วนคือฟิลด์ priority ของชุด ไม่ใช่สถานะใหม่",
            ha="center", fontsize=9.2, color=SLATE, style="italic")

    out = ROOT / "images" / "theory" / "state-flow.png"
    fig.savefig(out, dpi=160, bbox_inches="tight", facecolor=BG)
    plt.close(fig)
    print("WROTE", out)


def make_trace():
    fig, ax = plt.subplots(figsize=(14, 6.4), dpi=160)
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 6.4)
    ax.axis("off")

    ax.text(0.35, 6.02, "เส้นทางสืบย้อนกลับ (Traceability): จากคำพูดลูกค้า → User Story → Requirement → System Design",
            fontsize=13.8, fontweight="bold", color=NAVY)
    ax.text(0.35, 5.68, "ทุกองค์ประกอบในสถาปัตยกรรมและทุก Test Case ผูกกลับไปยังคำพูดจริงของลูกค้า 4 บทบาทได้ 100%",
            fontsize=9.6, color=MUTED)

    cols = [
        (0.35, "1. คำพูดจากการสัมภาษณ์", BLUE, BLUE_LT),
        (3.8, "2. User Story", TEAL, TEAL_LT),
        (7.15, "3. Requirement & Rule", PURPLE, PURPLE_LT),
        (10.5, "4. System Design (NGINX + vLLM)", GREEN, GREEN_LT),
    ]
    for cx, label, ec, fc in cols:
        box(ax, cx, 5.02, 3.1, 0.48, label, fc=fc, ec=ec, title_color=ec, ts=10.2)

    rows = [
        (3.65,
         "คุณกิตติ (หัวหน้าทีม)", "“100 ใบ ยอดผิดได้ไม่เกิน 5 ใบ\nถ้าไม่แน่ใจต้องบอก อย่าเดา”",
         "US-07 · US-08", "ติดธงระบบไม่แน่ใจ\nและแสดงเหตุผลให้ตรวจ",
         "NFR-01 · BR-04 · BR-05", "M1 ≥ 95%, M2 ≤ 1%\nconf < 0.90 · diff > 1.00",
         "LoRA Qwen3-VL-2B\n+ BR-05 Live Recalc", "logprobs → conf\nแก้ยอดแล้วคำนวณธงสด"),
        (2.05,
         "คุณกิตติ + คุณอรทัย", "“งานเร่งด่วนไม่เกิน 5 นาทีต้องเห็นผล\nห้ามล่ม ถ้าเต็มให้บอกนาทีลองใหม่”",
         "US-10 · US-14", "งานเร่งด่วนได้ก่อนโดยงานปกติไม่ค้าง\nโหลดเต็มตอบนาทีลองใหม่",
         "NFR-02/03 · BR-08..12", "เร่งด่วน ≤10 ใบ, ≤5/วัน, 4:1\nเพดานรอประมวลผล 400 ใบ",
         "NGINX least_conn +\n2× vLLM Replicas", "Data Parallelism 2×1\n2,643.9 ใบ/นาที + Failover"),
        (0.45,
         "คุณสมชาย (ลูกค้า)", "“อยากอัปโหลดเอง เห็นสรุปรายเดือน\nและรู้ว่าใบส่งถึงแล้ว”",
         "US-22 · US-23 · US-24", "พอร์ทัลเฉพาะร้านตน\nไม่เห็นยอดก่อนยืนยัน",
         "FR-25..29 · BR-14", "กรอง client_id ฝั่ง server\nนับวันที่ 1 ถึงสิ้นเดือน",
         "Next.js /portal +\nSSE Copilot (/copilot)", "RBAC 4 บทบาทแยกขาด\nสตรีมสดผ่าน proxy_buffering off"),
    ]
    for ry, t1, b1, t2, b2, t3, b3, t4, b4 in rows:
        box(ax, 0.35, ry, 3.1, 1.3, t1, b1, fc=WHITE, ec=BLUE, ts=9.6, bs=8.3)
        box(ax, 3.8, ry, 3.1, 1.3, t2, b2, fc=WHITE, ec=TEAL, ts=9.6, bs=8.3)
        box(ax, 7.15, ry, 3.1, 1.3, t3, b3, fc=WHITE, ec=PURPLE, ts=9.6, bs=8.3)
        box(ax, 10.5, ry, 3.1, 1.3, t4, b4, fc=WHITE, ec=GREEN, ts=9.6, bs=8.3)
        arrow(ax, 3.45, ry + 0.65, 3.8, ry + 0.65, color=SLATE, lw=1.6)
        arrow(ax, 6.9, ry + 0.65, 7.15, ry + 0.65, color=SLATE, lw=1.6)
        arrow(ax, 10.25, ry + 0.65, 10.5, ry + 0.65, color=SLATE, lw=1.6)

    out = ROOT / "images" / "theory" / "trace-nginx.png"
    fig.savefig(out, dpi=160, bbox_inches="tight", facecolor=BG)
    plt.close(fig)
    print("WROTE", out)


def make_lab6_vs_lab7():
    fig, ax = plt.subplots(figsize=(13.5, 6.0), dpi=160)
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)
    ax.set_xlim(0, 13.5)
    ax.set_ylim(0, 6.0)
    ax.axis("off")

    ax.text(0.4, 5.62, "ทำไม ReceiptDesk เลือก Continuous Batching + Data Parallelism แทน Static Micro-batching",
            fontsize=13.5, fontweight="bold", color=NAVY)
    ax.text(0.4, 5.26, "Qwen3-VL-2B-Instruct สร้างคำตอบทีละโทเคน (JSON ใบเสร็จ + แชท Copilot สตรีมสด) ความยาวแต่ละคำขอไม่เท่ากัน",
            fontsize=9.6, color=MUTED)

    # Left: Static Micro-batching
    p1 = FancyBboxPatch((0.4, 0.55), 6.0, 4.4, boxstyle="round,pad=0.06,rounding_size=0.22",
                        fc="#F1F5F9", ec=BORDER, lw=1.6, zorder=1)
    ax.add_patch(p1)
    box(ax, 0.6, 4.2, 5.6, 0.6, "Static Micro-batching (เหมาะกับโมเดลภาพ 1 รอบ)", fc=BLUE, ec=BLUE, title_color=WHITE, ts=10.3)
    box(ax, 0.7, 2.95, 5.4, 1.0, "1. รวบรวมคำขอให้ครบชุดแล้วรันพร้อมกัน", "รัน Forward Pass 1 ครั้งเท่ากันทุกภาพ\nต้องรอให้ทั้งชุดเสร็จพร้อมกันก่อนส่งกลับ", fc=WHITE, ec=BLUE, ts=9.8, bs=8.5)
    box(ax, 0.7, 1.75, 5.4, 1.0, "2. จุดอ่อนเมื่อใช้กับ VLM / LLM", "คำตอบสั้นต้องรอคำตอบยาวจบทั้งชุด (Head-of-Line Blocking)\nและไม่รองรับการสตรีมทีละโทเคน (SSE)", fc=RED_LT, ec=RED, ts=9.8, bs=8.5)
    ax.text(3.4, 1.02, "ไม่เหมาะกับงาน VLM ที่ความยาวคำตอบต่างกันมาก", ha="center", fontsize=9.6, fontweight="bold", color=SLATE)

    # Right: Continuous Batching + Data Parallelism
    p2 = FancyBboxPatch((7.0, 0.55), 6.1, 4.4, boxstyle="round,pad=0.06,rounding_size=0.22",
                        fc="#ECFDF5", ec=GREEN, lw=2.0, zorder=1)
    ax.add_patch(p2)
    box(ax, 7.2, 4.2, 5.7, 0.6, "vLLM Continuous Batching + Data Parallelism 2×1", fc=GREEN, ec=GREEN, title_color=WHITE, ts=10.2)
    box(ax, 7.3, 2.95, 5.5, 1.0, "1. Iteration-Level Continuous Batching (max-num-seqs=256)", "แทรกคำขอใหม่ทุกรอบโทเคน · คำขอที่จบออกทันที\nThroughput พุ่งจาก 209 → 14,050 tok/s (67.2× บน 1 GPU)", fc=WHITE, ec=GREEN, ts=9.6, bs=8.5)
    box(ax, 7.3, 1.75, 5.5, 1.0, "2. NGINX least_conn + 2× RTX 4090 Data Parallelism", "ปิด proxy_buffering เพื่อ SSE สตรีมสด · เกลี่ยโหลด 49.4% / 50.6%\n28,541 tok/s · 640 ผู้ใช้ · 2,643.9 ใบเสร็จ/นาที · Failover 0 error", fc=GREEN_LT, ec=GREEN, ts=9.6, bs=8.5)
    ax.text(10.05, 1.02, "✓ สถาปัตยกรรมหลักของ ReceiptDesk (NGINX + 2× vLLM)", ha="center", fontsize=9.8, fontweight="bold", color="#065F46")

    out = ROOT / "images" / "theory" / "serving-architecture-choice.png"
    fig.savefig(out, dpi=160, bbox_inches="tight", facecolor=BG)
    plt.close(fig)
    print("WROTE", out)


def make_dag():
    fig, ax = plt.subplots(figsize=(14.5, 7.8), dpi=160)
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)
    ax.set_xlim(0, 14.5)
    ax.set_ylim(0, 7.8)
    ax.axis("off")

    ax.text(0.35, 7.42, "DAG 14 บล็อกของแผน receiptdesk · ครบ 6 สกิล (NGINX least_conn + 2× vLLM)",
            fontsize=14.5, fontweight="bold", color=NAVY)
    ax.text(0.35, 7.06, "สายวิกฤต (เส้นสีแดง): B01 → B02 → B04 → B11 → B14 · เวลารวมตามแผน 63.5 นาที (4 บัญชี · agent พร้อมกันสูงสุด 4)",
            fontsize=9.8, color=MUTED)

    nodes = {
        "B01": (0.4, 3.8, "B01 · โครงโปรเจกต์\n+ docker compose", "cyolo · S · cyolo1", True),
        "B13": (0.4, 1.1, "B13 · โลโก้ & ภาพ\nReceiptDesk", "image · S · cyolo1", False),
        "B02": (3.0, 5.2, "B02 · PostgreSQL\n11 ตาราง + Seed", "cyolo · M · cyolo1", True),
        "B03": (3.0, 3.6, "B03 · กติกา BR\n(rules.ts)", "review · M · yolo2+cyolo1", False),
        "B06": (3.0, 2.0, "B06 · กติกาเร่งด่วน\n4:1 + Overload 429", "debate · S · 3 agents", False),
        "B10": (3.0, 0.4, "B10 · เทรน LoRA\n1 vs 2 GPU + Eval", "yolo · L · yolo3", False),
        "B04": (5.8, 4.9, "B04 · RBAC 4 บทบาท\n+ API 35 เส้น", "yolo · L · yolo2", True),
        "B05": (5.8, 3.3, "B05 · Async Dispatcher\n(vLLM / Mock)", "cyolo · M · cyolo1", False),
        "B07": (5.8, 1.7, "B07 · จัดลำดับ 4:1\nเพดาน 400 · ลอง 3 ครั้ง", "cyolo · M · cyolo1", False),
        "B11": (8.8, 5.3, "B11 · หน้าเว็บตามบทบาท\n+ Portal + Reports", "yolo · L · yolo2", True),
        "B12": (8.8, 3.7, "B12 · Split-Pane\nReview Workbench", "best_of · M · 3 agents", False),
        "B08": (8.8, 2.1, "B08 · SSE Copilot\nProxy + Telemetry", "yolo · M · gyolo1", False),
        "B09": (8.8, 0.5, "B09 · AI Serving\nNGINX + 2× vLLM", "yolo · M · gyolo1", False),
        "B14": (11.9, 3.1, "B14 · รวมระบบ +\nทดสอบเบื้องต้น", "yolo · M · yolo2", True),
    }

    W, H = 2.15, 1.18
    for k, (x, y, t, sub, crit) in nodes.items():
        fc = "#FEF2F2" if crit else (PURPLE_LT if "debate" in sub or "best_of" in sub else (AMBER_LT if "review" in sub else WHITE))
        ec = RED if crit else (PURPLE if "debate" in sub or "best_of" in sub else (AMBER if "review" in sub else BLUE))
        lw = 2.3 if crit else 1.5
        box(ax, x, y, W, H, t, sub, fc=fc, ec=ec, lw=lw, ts=9.2, bs=8.0)

    edges = [
        ("B01", "B02", True), ("B01", "B03", False), ("B01", "B06", False), ("B01", "B10", False),
        ("B02", "B04", True), ("B02", "B05", False), ("B03", "B04", False), ("B06", "B07", False),
        ("B04", "B11", True), ("B04", "B12", False), ("B07", "B08", False), ("B07", "B09", False), ("B08", "B09", False),
        ("B11", "B14", True), ("B12", "B14", False), ("B05", "B14", False), ("B09", "B14", False), ("B10", "B14", False), ("B13", "B14", False),
    ]
    for u, v, crit in edges:
        x1, y1 = nodes[u][0] + W, nodes[u][1] + H / 2
        x2, y2 = nodes[v][0], nodes[v][1] + H / 2
        if u == "B08" and v == "B09":
            arrow(ax, nodes[u][0] + W / 2, nodes[u][1], nodes[v][0] + W / 2, nodes[v][1] + H, color=SLATE, lw=1.4)
        elif u in ("B13", "B10") and v == "B14":
            arrow(ax, x1, nodes[u][1] + 0.2, x2, nodes[v][1] + 0.15, color="#94A3B8", lw=1.1, rad=0.22, ls="--")
        else:
            arrow(ax, x1, y1, x2, y2, color=RED if crit else "#94A3B8", lw=2.3 if crit else 1.2)

    # Legend
    ax.text(0.4, 0.08, "สัญลักษณ์:  ■ ขอบแดง = สายวิกฤต (Critical Path)   ■ พื้นเหลือง = review (ผู้ตรวจต่าง CLI)   ■ พื้นม่วง = debate / best_of (3 agents)",
            fontsize=9.2, color=SLATE)

    out = ROOT / "plan" / "dag.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=160, bbox_inches="tight", facecolor=BG)
    plt.close(fig)
    print("WROTE", out)


def make_gantt_plan():
    tasks = [
        ("B01 โครงโปรเจกต์ (cyolo1)", 0.0, 2.3, BLUE, True),
        ("B13 โลโก้ & ภาพ (cyolo1)", 0.0, 0.5, TEAL, False),
        ("B02 ฐานข้อมูล 11 ตาราง (cyolo1)", 2.3, 7.9, BLUE, True),
        ("B06 กติกาเร่งด่วน 4:1 (debate)", 2.3, 6.8, PURPLE, False),
        ("B03 กติกา Business Rule (review)", 6.8, 17.7, AMBER, False),
        ("B07 จัดลำดับ 4:1 & เพดาน 400 (cyolo1)", 6.8, 12.5, BLUE, False),
        ("B05 Async Dispatcher (cyolo1)", 7.9, 13.6, BLUE, False),
        ("B10 เทรน LoRA 1/2 GPU (yolo3)", 12.5, 30.8, GREEN, False),
        ("B08 SSE Copilot + Telemetry (gyolo1)", 13.6, 22.8, GREEN, False),
        ("B04 RBAC + API 35 เส้น (yolo2)", 17.7, 36.0, RED, True),
        ("B09 NGINX least_conn + 2×vLLM (gyolo1)", 22.8, 31.9, GREEN, False),
        ("B11 หน้าเว็บตามบทบาท (yolo2)", 36.0, 54.4, RED, True),
        ("B12 Split-Pane Review (best_of)", 36.0, 47.4, PURPLE, False),
        ("B14 รวมระบบ + ทดสอบเบื้องต้น (yolo2)", 54.4, 63.5, RED, True),
    ]
    fig, ax = plt.subplots(figsize=(13.2, 6.8), dpi=160)
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(WHITE)
    y_pos = list(range(len(tasks) - 1, -1, -1))
    for i, (name, s, e, col, crit) in enumerate(tasks):
        y = y_pos[i]
        ax.barh(y, e - s, left=s, height=0.62, color=col, alpha=0.88, edgecolor=NAVY if crit else "none", linewidth=1.3)
        ax.text(e + 0.8, y, f"{s:.1f}–{e:.1f} นาที", va="center", fontsize=8.5, color=SLATE, fontweight="bold" if crit else "normal")
    ax.set_yticks(y_pos)
    ax.set_yticklabels([t[0] for t in tasks], fontsize=9.3, color=NAVY)
    ax.set_xlim(0, 74)
    ax.set_xlabel("เวลาตามแผน (นาที) · agent พร้อมกันสูงสุด 4 ตัว", fontsize=10, fontweight="bold", color=NAVY)
    ax.set_title("Gantt แผน receiptdesk · 14 บล็อกบน 4 บัญชี (เวลารวมตามแผน 63.5 นาที)", fontsize=13.2, fontweight="bold", color=NAVY, pad=12)
    ax.grid(axis="x", linestyle="--", alpha=0.4)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    out = ROOT / "plan" / "gantt-plan.png"
    fig.savefig(out, dpi=160, bbox_inches="tight", facecolor=BG)
    plt.close(fig)
    print("WROTE", out)


def make_compare():
    blocks = ["B01", "B02", "B03*", "B04", "B05", "B06", "B07", "B08", "B09", "B10", "B11", "B12", "B13", "B14"]
    plan_m = [2.27, 5.67, 10.84, 18.34, 5.67, 4.57, 5.67, 9.17, 9.17, 18.34, 18.34, 11.42, 0.55, 9.17]
    act_m  = [0.83, 3.38, 22.02, 15.42, 9.32, 11.45, 3.73, 9.03, 10.37, 13.62, 11.98, 14.82, 0.55, 8.63]

    fig, ax = plt.subplots(figsize=(13.2, 5.8), dpi=160)
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(WHITE)
    x = range(len(blocks))
    w = 0.38
    ax.bar([i - w / 2 for i in x], plan_m, width=w, color="#94A3B8", label="เวลาตามแผน (รวม 63.5 นาที)")
    bars = ax.bar([i + w / 2 for i in x], act_m, width=w, color=BLUE, label="เวลาจริง (รวม 92.0 นาที · ครบ 14/14 บล็อก)")
    bars[2].set_color(AMBER)  # Highlight B03 review scope decision

    for i, (p, a) in enumerate(zip(plan_m, act_m)):
        ax.text(i + w / 2, a + 0.45, f"{a:.1f}", ha="center", va="bottom", fontsize=8.2, fontweight="bold",
                color=AMBER if i == 2 else NAVY)

    ax.annotate("B03 (review): รอบ 1–2 ไม่จบ\nหลังกำหนดขอบเขตใหม่ ผ่านทันที", xy=(2.19, 22.02), xytext=(3.8, 21.5),
                arrowprops=dict(arrowstyle="->", color=AMBER, lw=1.6),
                fontsize=9.2, fontweight="bold", color="#B45309",
                bbox=dict(boxstyle="round,pad=0.35", fc=AMBER_LT, ec=AMBER))

    ax.set_xticks(list(x))
    ax.set_xticklabels(blocks, fontsize=9.8, fontweight="bold", color=NAVY)
    ax.set_ylabel("ระยะเวลาต่อบล็อก (นาที)", fontsize=10, fontweight="bold", color=NAVY)
    ax.set_ylim(0, 26.5)
    ax.set_title("เปรียบเทียบเวลาตามแผน vs เวลาจริงทั้ง 14 บล็อก (หลังกำหนดขอบเขตการตรวจ B03)", fontsize=13, fontweight="bold", color=NAVY, pad=12)
    ax.legend(frameon=True, facecolor=WHITE, edgecolor=BORDER, loc="upper right", fontsize=9.5)
    ax.grid(axis="y", linestyle="--", alpha=0.4)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    out = ROOT / "plan" / "compare.png"
    fig.savefig(out, dpi=160, bbox_inches="tight", facecolor=BG)
    plt.close(fig)
    print("WROTE", out)


def make_whatif():
    tasks = [
        ("B01 โครงโปรเจกต์", 0.0, 2.3, BLUE, "วางได้"),
        ("B13 โลโก้ & ภาพ", 0.0, 0.5, TEAL, "วางได้"),
        ("B02 ฐานข้อมูล 11 ตาราง", 2.3, 7.9, BLUE, "วางได้"),
        ("B03 กติกา BR (review)", 2.3, 13.2, AMBER, "วางได้"),
        ("B05 Async Dispatcher", 7.9, 13.6, BLUE, "วางได้"),
        ("B10 เทรน LoRA 1/2 GPU", 13.6, 31.9, GREEN, "วางได้"),
        ("B04 RBAC + API 35 เส้น", 13.6, 31.9, BLUE, "วางได้"),
        ("B11 หน้าเว็บตามบทบาท", 31.9, 68.1, BLUE, "วางได้"),
        ("B06 กติกาเร่งด่วน (debate · ต้องใช้ 3)", 0, 0, RED, "วางไม่ได้ (เกินเพดาน 2)"),
        ("B07–B09 ลำดับ/Copilot/NGINX (รอ B06)", 0, 0, RED, "ถูกบล็อกเพราะ B06"),
        ("B12 Review Workbench (best_of · ต้องใช้ 3)", 0, 0, RED, "วางไม่ได้ (เกินเพดาน 2)"),
        ("B14 รวมระบบ (รอ B09, B12)", 0, 0, RED, "ถูกบล็อก — สร้างไม่จบ!"),
    ]
    fig, ax = plt.subplots(figsize=(13.2, 6.2), dpi=160)
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(WHITE)
    y_pos = list(range(len(tasks) - 1, -1, -1))
    for i, (name, s, e, col, note) in enumerate(tasks):
        y = y_pos[i]
        if e > s:
            ax.barh(y, e - s, left=s, height=0.6, color=col, alpha=0.88)
            ax.text(e + 0.9, y, f"{s:.1f}–{e:.1f} นาที", va="center", fontsize=8.5, color=SLATE)
        else:
            ax.barh(y, 46, left=2.0, height=0.58, color=RED_LT, edgecolor=RED, linestyle="--", linewidth=1.2)
            ax.text(25.0, y, f"✗ {note}", ha="center", va="center", fontsize=9.0, fontweight="bold", color=RED)
    ax.set_yticks(y_pos)
    ax.set_yticklabels([t[0] for t in tasks], fontsize=9.2, color=NAVY)
    ax.set_xlim(0, 78)
    ax.set_xlabel("เวลาตามแผน (นาที) · What-if จำกัด agent พร้อมกันสูงสุด 2 ตัว", fontsize=10, fontweight="bold", color=NAVY)
    ax.set_title("What-if: แผน receiptdesk-2 (เพดาน 2 agent) วางได้เพียง 8/14 บล็อก — debate และ best_of ทำงานไม่ได้",
                 fontsize=12.4, fontweight="bold", color=RED, pad=12)
    ax.grid(axis="x", linestyle="--", alpha=0.4)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    out = ROOT / "plan" / "whatif" / "gantt-receiptdesk-2.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=160, bbox_inches="tight", facecolor=BG)
    plt.close(fig)
    print("WROTE", out)


if __name__ == "__main__":
    make_arch()
    make_state_flow()
    make_trace()
    make_lab6_vs_lab7()
    make_dag()
    make_gantt_plan()
    make_compare()
    make_whatif()
    print("ALL 8 PURE-NGINX DIAGRAMS GENERATED!")
