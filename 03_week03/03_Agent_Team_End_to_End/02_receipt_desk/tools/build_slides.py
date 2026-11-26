#!/usr/bin/env python3
"""
Build ReceiptDesk_Slides.html cleanly from README.md and real JSON result files.
- 100% standalone product engineering narrative (direct HTTP/SSE architecture, no external broker, no prices)
- Centerpiece: 1 Node x 2x RTX 4090 · 2x vLLM Replicas (Data Parallelism 2x1 + Continuous Batching) behind NGINX least_conn (proxy_buffering off SSE + Failover ON)
- Every prompt pulled verbatim from README.md via E.prompt_code() + E.prompt_slides()
- Embeds 10 playable .gif slides (2 signature 6.5s live demos starting from /login + 8 per-TC comparison slides covering 15 distinct TC GIFs!)
- Target ~74-80 slides, zero AI card spam, editorial print aesthetic.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import slides_engine as E
import slides_figures as F

ROOT = E.ROOT


def load_json(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
        return json.load(fh)


def gif_pair(items, caption=""):
    """Render 2 or 3 crisp playable .gif panels side-by-side uncropped (16:9 contain)."""
    cols = len(items)
    cells = []
    for label, src, sub in items:
        cells.append(
            '<div style="display:flex;flex-direction:column;gap:8px;min-width:0">'
            f'<div style="font-size:.82em;font-weight:700;color:var(--navy);white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{E.md(label)}</div>'
            f'<div style="border:1px solid var(--line);border-radius:8px;overflow:hidden;background:#0f172a;aspect-ratio:16/9;width:100%">'
            f'<img src="{src}" alt="{E.esc(E.plain(label))}" style="width:100%;height:100%;display:block;object-fit:contain"></div>'
            f'<div style="font-size:.76em;color:var(--muted);line-height:1.38">{E.md(sub)}</div>'
            '</div>'
        )
    grid = f'<div style="display:grid;grid-template-columns:repeat({cols},1fr);gap:18px;align-items:start">{"".join(cells)}</div>'
    if caption:
        grid += f'<p class="cap" style="margin-top:8px">{E.md(caption)}</p>'
    return grid


def img_pair(items, caption=""):
    cols = len(items)
    cells = []
    for label, src, sub in items:
        cells.append(
            '<div style="display:flex;flex-direction:column;gap:8px;min-width:0">'
            f'<div style="font-size:.84em;font-weight:700;color:var(--navy);white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{E.md(label)}</div>'
            f'<div style="border:1px solid var(--line);border-radius:8px;overflow:hidden;background:#fff;aspect-ratio:16/9;width:100%">'
            f'<img src="{src}" alt="{E.esc(E.plain(label))}" style="width:100%;height:100%;display:block;object-fit:contain"></div>'
            f'<div style="font-size:.78em;color:var(--muted);line-height:1.38">{E.md(sub)}</div>'
            '</div>'
        )
    grid = f'<div style="display:grid;grid-template-columns:repeat({cols},1fr);gap:18px;align-items:start">{"".join(cells)}</div>'
    if caption:
        grid += f'<p class="cap" style="margin-top:8px">{E.md(caption)}</p>'
    return grid


def vast_console(status_badge, status_color, title_line, rows, footer_note):
    """Editorial Vast.ai console status panel (NO prices or rental fees!)."""
    trs = "".join(
        f'<tr><td style="width:34%;color:#94a3b8;border-bottom:1px solid #1e293b;padding:10px 14px;background:transparent">{E.md(k)}</td>'
        f'<td style="color:#f8fafc;border-bottom:1px solid #1e293b;padding:10px 14px;font-family:var(--mono);font-size:.9em;background:transparent">{E.md(v)}</td></tr>'
        for k, v in rows
    )
    return (
        '<div style="background:#0b1324;color:#f8fafc;border-radius:12px;padding:22px 26px;border:1px solid #1e293b">'
        '<div style="display:flex;justify-content:space-between;align-items:center;padding-bottom:14px;margin-bottom:12px;border-bottom:1px solid #1e293b">'
        f'<div style="font-family:var(--mono);font-size:.95em;font-weight:700;color:#e2e8f0">{E.esc(title_line)}</div>'
        f'<div style="font-family:var(--mono);font-size:.88em;font-weight:700;color:{status_color}">● {E.esc(status_badge)}</div>'
        '</div>'
        f'<table style="width:100%;border-collapse:collapse;background:transparent;border:0;border-radius:0">{trs}</table>'
        '</div>'
        + E.note(footer_note, "eye", "สรุปสถานะเครื่อง")
    )


def set_ctx(kicker, group):
    E.CTX["kicker"] = kicker
    E.CTX["group"] = group


def add_prompt(step_prefix, kicker, title):
    E.add(E.prompt_slides(E.prompt_code(step_prefix), kicker, title))


def build():
    del E.SL[:]
    del E.PROMPTS[:]
    E.load("README.md", latex=True)

    lb = load_json("results/lb/lb_summary.json")
    ts = load_json("results/model/train_speed.json")
    e2e = load_json("test/evidence/e2e_results.json")
    live = load_json("test/evidence/e2e_live.json")

    # =====================================================================
    # OPENING (Slides 1-7: Cover -> Hero -> Problem -> Roadmap -> Arch -> Story -> Interview)
    # =====================================================================
    set_ctx("", "บทนำ")
    E.add(E.cover(
        "ReceiptDesk",
        "ระบบอ่านใบเสร็จและผู้ช่วยบัญชี AI แบบสตรีมสดสำหรับสำนักงานบัญชี · 1 โหนด × 2× RTX 4090 (NGINX least_conn + 2× vLLM Data Parallelism)",
        F.HERO_AND_DIVIDERS["cover"],
        small="End-to-End AI Product Engineering · หัวข้อที่ 2",
    ))

    # Slide 2: Headline Outcome Hero
    E.add(E.hero(
        "ภาพรวมผลลัพธ์จริงบน 1 โหนด × 2× RTX 4090",
        "ระบบพร้อมใช้งานจริง: รองรับ 640 ผู้ใช้พร้อมกัน และผ่าน Playwright 28/28 ข้อ",
        F.HERO_AND_DIVIDERS["hero_results"],
        [
            ("ผู้ใช้งานพร้อมกัน (Standard SLO)", "640 คน", "TTFT p95 1.547 วินาที · Fast SLO 257 คน", "ok"),
            ("กำลังผลิตรวม (Data Parallelism 2×1)", "28,541 tok/s", "Scaling Efficiency 101.6% เทียบ GPU 1 ใบ", "ok"),
            ("อ่านใบเสร็จจริง (CORD-v2)", "2,643.9 ใบ/นาที", "Speedup 1.91× · ชุด 100 ใบเสร็จใน 2.3 วินาที", "ok"),
            ("Playwright E2E + Bug Hunt", f"{e2e['passed']} / {e2e['total']} ผ่าน", f"บันทึก .gif ครบ {e2e['gifs_recorded']} ข้อ · จับบั๊กซ่อน 3/3", "ok"),
        ],
        post=E.note("ตัวเลขทั้งหมดวัดจริงบน 1 โหนด × 2× RTX 4090 (results/lb/ และ test/evidence/)", "eye", "ที่มาของข้อมูล"),
        tag="ผลจริง 100%",
    ))

    # Slide 3: Customer Problem & Core Question
    set_ctx("บริบทลูกค้า · สำนักงานบัญชี ใส่ใจการบัญชี", "บทนำ")
    E.add(E.explain(
        "สิ้นเดือนใบเสร็จเข้าวันละ 800 ใบ: พิมพ์มือถึงสามทุ่มและยอดเริ่มผิด",
        "images/story/r3-monthend.jpg",
        [
            "**ลูกค้า 60 ร้านค้า** ส่งรูปใบเสร็จผ่าน LINE และอีเมลรวมเดือนละประมาณ **6,000 ใบ**",
            "**พนักงาน 4 คน** พิมพ์ชื่อร้าน วันที่ รายการ ราคา และยอดรวมด้วยมือเฉลี่ย **ใบละ 2 นาที**",
            "**คอขวดช่วงสิ้นเดือน** ใบเสร็จทะลักเข้าวันละ **800 ใบ** พร้อมคำถามด้านบัญชีจากทีมและลูกค้า",
            "**โจทย์วิศวกรรม** ออกแบบ สร้าง เปิดบริการบน `1 โหนด × 2× RTX 4090` และพิสูจน์ด้วยหลักฐานจริงทุกข้อ",
        ],
    ))

    # Slide 4: 4-Phase Engineering Roadmap
    E.add(E.fig(
        "เส้นทางสร้างระบบ ReceiptDesk ครบทั้ง 4 ระยะ (15 ขั้นตอน)",
        F.EXPLAINERS["roadmap"],
        "เริ่มจากคำพูดลูกค้า 4 บทบาท → วางแผนทีม AI 14 บล็อก → เทรน LoRA และเปิด NGINX + 2× vLLM → พิสูจน์ด้วย Playwright 28 ข้อพร้อม .gif ทุกข้อ",
        tag="แผนที่ทั้งบท",
    ))

    # Slide 5: Pure NGINX + 2x vLLM Architecture at a Glance
    E.add(E.fig(
        "สถาปัตยกรรมหลัก: เว็บ Next.js เชื่อมตรง NGINX least_conn → 2× vLLM Replicas",
        F.EXPLAINERS["arch_clean"],
        "1 โหนด × 2× RTX 4090 แยก 1 vLLM Replica ต่อ 1 GPU (**Data Parallelism 2×1**) ปิด buffering เพื่อรองรับทั้ง **Vision OCR** และ **SSE Copilot สตรีมสด**",
        tag="สถาปัตยกรรมหลัก",
    ))

    # Slide 6: Customer workflow before AI
    E.add(E.slide(
        "ภาพการทำงานเดิม: ถ่ายรูปส่งแยกช่องทาง แล้วพนักงานคีย์ทีละใบ",
        img_pair([
            ("1. ร้านค้าถ่ายรูปใบเสร็จส่งมา", "images/story/r1-send.jpg", "ใบเสร็จปนกันหลายแบบ ทั้งใบเสร็จความร้อน เบลอ และถ่ายไม่ตรงมุม"),
            ("2. พนักงานพิมพ์ 5 ช่องลงตารางทีละใบ", "images/story/r2-typing.jpg", "ใช้เวลาใบละ 2 นาที — 6,000 ใบต่อเดือนกินแรงงานกว่า 200 ชั่วโมง"),
        ]),
        tag="ภาพจำลอง",
    ))

    # Slide 7: 4 Stakeholders Interviewed
    people_html = (
        '<div style="display:grid;grid-template-columns:1.15fr 1fr;gap:22px;align-items:center">'
        '<div class="fig" style="border-radius:10px;overflow:hidden;border:1px solid var(--line)">'
        '<img src="images/story/r4-interview.jpg" alt="การสัมภาษณ์ลูกค้า 4 บทบาท" style="width:100%;height:auto;display:block"></div>'
        '<div style="display:flex;flex-direction:column;gap:12px">'
        + "".join(
            '<div style="display:flex;gap:12px;align-items:center;padding-bottom:10px;border-bottom:1px solid var(--line)">'
            f'<img src="{img}" alt="{name}" style="width:58px;height:58px;border-radius:50%;object-fit:cover;flex:none">'
            f'<div style="font-size:.82em;line-height:1.38"><b>{name}</b> ({role}) — {quote}</div></div>'
            for img, name, role, quote in [
                ("images/story/q-orathai.jpg", "คุณอรทัย", "เจ้าของสำนักงาน", "ห้ามล่ม ห้ามหาย ถ้าโหลดเต็มให้บอกนาทีลองใหม่ และไม่ต้องตรวจทุกช่องทุกใบ"),
                ("images/story/q-pim.jpg", "คุณพิมพ์", "พนักงานบัญชี", "ขออัปโหลดทีละชุดถึง 100 ใบ รอครึ่งชั่วโมงได้ ขอแค่ใบเสร็จไม่หาย"),
                ("images/story/q-kitti.jpg", "คุณกิตติ", "หัวหน้าทีมบัญชี", "100 ใบยอดรวมผิดได้ไม่เกิน 5 ใบ ถ้าไม่แน่ใจต้องบอก และงานเร่งด่วนต้องจบใน 5 นาที"),
                ("images/story/q-somchai.jpg", "คุณสมชาย", "ลูกค้าร้านอาหาร", "อยากอัปโหลดเอง เห็นสรุปรายเดือนเฉพาะร้านตน และรู้ว่าใบส่งถึงแล้ว"),
            ]
        )
        + '</div></div>'
    )
    E.add(E.slide("การสัมภาษณ์ 4 บทบาทเผยทั้งเป้าหมายหลักและจุดที่ต้องการขัดกัน", people_html, tag="INTERVIEW.md"))

    # =====================================================================
    # PHASE A · REQUIREMENT & ARCHITECTURE (Steps 1-3)
    # =====================================================================
    set_ctx("ระยะ A · จากคำพูดเป็น Requirement", "ระยะ A · Requirement")
    E.add(E.divider(
        "ระยะ A",
        "จากคำพูดลูกค้าเป็น Requirement และสถาปัตยกรรม",
        "ขั้นที่ 1–3 · User Story 24 ข้อ · Business Rule 14 ข้อ · ออกแบบ NGINX least_conn + 2× vLLM Data Parallelism",
        img=F.HERO_AND_DIVIDERS["phase_a"],
        small="ขั้นที่ 1–3 จาก 15",
    ))

    E.add(E.fig(
        "สืบย้อนกลับได้ทุกข้อ: จากคำพูดลูกค้า → User Story → Requirement → System Design",
        F.EXPLAINERS["trace"],
        "ทุกฟีเจอร์ กติกาเส้นแบ่ง และสถาปัตยกรรม `NGINX + 2× vLLM` ผูกกลับไปยังคำพูดจริงของลูกค้า 4 บทบาท",
        tag="Traceability",
    ))

    # Step 1
    add_prompt("ขั้นที่ 1", "ระยะ A · ขั้นที่ 1 จาก 15", "User Story จากบันทึกการสัมภาษณ์")
    E.add(E.slide(
        "ผลขั้นที่ 1: แยกได้ 24 User Story ครบ 4 บทบาท และพบจุดขัดกัน 6 จุด",
        E.tiles([
            ("ระดับ Must", "16 ข้อ", "ความสามารถหลักที่ขาดไม่ได้", "ok"),
            ("ระดับ Should / Could", "8 ข้อ", "Should 7 ข้อ · Could 1 ข้อ", ""),
            ("จุดที่ลูกค้าพูดขัดกัน", "6 จุด", "ต้องตัดสินใจด้วยข้อสมมติในขั้นที่ 2", "warn"),
            ("คำถามที่ต้องถามเพิ่ม", "14 ข้อ", "รวม US-24 ที่ไม่มีใครตอบในห้องประชุม", ""),
        ]) + E.note("พนักงานบัญชี 7 ข้อ · หัวหน้าทีม 6 ข้อ · เจ้าของสำนักงาน 8 ข้อ · ลูกค้า 3 ข้อ — ไม่เพิ่มสิ่งที่ลูกค้าไม่ได้พูด", "eye", "อ่านผล"),
        tag="docs/USER-STORIES.md",
    ))

    # Step 2
    add_prompt("ขั้นที่ 2", "ระยะ A · ขั้นที่ 2 จาก 15", "Requirement และ Business Rule ที่เรียบง่ายชัดเจน")
    E.add(E.tbl(
        "กติกา Business Rule เรียบง่าย ชัดเจน และตรวจได้ด้วยเส้นแบ่ง 3 ค่า",
        E.table("ขั้นที่ 2", "รหัส"),
        post=E.note("ทุกกติกาตรวจได้ด้วยค่า ต่ำกว่า / เท่ากับ / สูงกว่า เส้นแบ่ง เพื่อใช้สร้างชุดทดสอบอัตโนมัติในระยะ D", "eye", "หลักการ"),
        tag="docs/REQUIREMENTS.md",
    ))

    E.add(E.fig(
        "เกณฑ์ตัดสินโมเดล (Acceptance Gate): แปลงคำพูดลูกค้าเป็น 4 ตัวชี้วัดบน Test Set",
        F.EXPLAINERS["gate"],
        "**M1** วัดความแม่นยำยอดรวม ส่วน **M2–M4** วัดว่าโมเดลรู้ตัวว่าไม่แน่ใจได้ดีแค่ไหนโดยไม่ติดธงพร่ำเพรื่อ",
        tag="NFR-01",
    ))

    E.add(E.tbl(
        "SLO ของระบบ: ครอบคลุมทั้งชุดใบเสร็จปกติ ชุดเร่งด่วน และ Copilot สตรีมสด",
        E.table("ขั้นที่ 2", "เรื่อง"),
        post=E.note("เพิ่ม GPU เป็น 2 ใบถือว่าคุ้มเมื่อ Speedup ≥ 1.6 เท่า หรือ GPU 2 ใบผ่าน SLO ที่ 1 ใบทำไม่ได้", "eye", "เกณฑ์ความคุ้ม GPU"),
        tag="NFR-02..10",
    ))

    # Architecture rationale BEFORE Step 3 prompt
    E.add(E.fig(
        "เหตุผลทางวิศวกรรม: ทำไมต้อง Continuous Batching + Data Parallelism 2×1",
        F.EXPLAINERS["serving_choice"],
        "งาน VLM และแชท Copilot สร้างคำตอบทีละโทเคนความยาวต่างกัน จึงเลือก **vLLM Continuous Batching** แทน Static Micro-batching",
        tag="หลักการออกแบบ",
    ))

    # Step 3
    add_prompt("ขั้นที่ 3", "ระยะ A · ขั้นที่ 3 จาก 15", "System Design (NGINX least_conn + 2× vLLM) และข้อมูลทดสอบ")
    E.add(E.fig(
        "สถาปัตยกรรมเต็มระบบ: ฝั่งเว็บเก็บความจริง · ฝั่ง 2× RTX 4090 เป็น Stateless",
        F.EXPLAINERS["arch_detail"],
        "Next.js 16 + PostgreSQL 16 ส่ง Vision OCR และ SSE Copilot ตรงไป **NGINX 1.27 (`least_conn`, `proxy_buffering off`)** → **2× vLLM Replicas**",
        tag="docs/DESIGN.md",
    ))

    E.add(E.fig(
        "วงจรสถานะ 5 สถานะใน PostgreSQL: ล้มเหลวครบ 3 ครั้งย้ายไปให้คนพิมพ์เอง",
        F.EXPLAINERS["state_flow"],
        "จัดการสถานะใบเสร็จ ลำดับงานเร่งด่วน 4:1 เพดาน 400 ใบ (`HTTP 429`) และสถานะ `unreadable` ใน PostgreSQL 16 โดยตรง",
        tag="BR-07 · FR-16",
    ))

    # =====================================================================
    # PHASE B · PLANNING & WHAT-IF (Steps 4-5)
    # =====================================================================
    set_ctx("ระยะ B · วางแผนงานให้ทีม AI", "ระยะ B · วางแผน")
    E.add(E.divider(
        "ระยะ B",
        "วางแผนงานให้ทีม AI 4 บัญชีด้วย DAG และ What-if",
        "ขั้นที่ 4–5 · แตกงาน 14 บล็อกครบ 6 สกิลบนบัญชี yolo2, yolo3, cyolo1, gyolo1 · จำลอง What-if ก่อนรันจริง",
        img=F.HERO_AND_DIVIDERS["phase_b"],
        small="ขั้นที่ 4–5 จาก 15",
    ))

    add_prompt("ขั้นที่ 4", "ระยะ B · ขั้นที่ 4 จาก 15", "แตกงาน 14 บล็อก วาด DAG และ Gantt")
    E.add(E.fig(
        "DAG 14 บล็อกครบ 6 สกิล: สายวิกฤตคือ B01 → B02 → B04 → B11 → B14",
        "plan/dag.png",
        "ใช้ `review` กับกติกา Business Rule (กำหนดขอบเขตชัดให้จบใน ≤ 3 รอบ) · ใช้ `debate` กับกติกาเร่งด่วน · ใช้ `best_of` กับหน้า Split-Pane Review",
        tag="plan/PLAN.md",
    ))

    E.add(E.fig(
        "Gantt ตามแผน: รันพร้อมกันสูงสุด 4 agent จบใน 63.5 นาที",
        "plan/gantt-plan.png",
        "จัดสรรงานบน 4 บัญชี (`yolo2, yolo3, cyolo1, gyolo1`) แยกสายงานเว็บและสาย AI Serving ให้เดินขนานกัน",
        tag="plan/gantt-plan.png",
    ))

    add_prompt("ขั้นที่ 5", "ระยะ B · ขั้นที่ 5 จาก 15", "What-if ก่อนตัดสินใจรัน")
    E.add(E.fig(
        "What-if เพดาน 2 agent (receiptdesk-2): วางได้เพียง 8/14 บล็อก สร้างไม่จบ",
        "plan/whatif/gantt-receiptdesk-2.png",
        "สกิล `debate` (B06) และ `best_of` (B12) ต้องใช้ 3 agent พร้อมกัน จึงติดเพดาน 2 และบล็อกปลายน้ำจนถึง B14",
        tag="What-if Analysis",
    ))

    E.add(E.tbl(
        "เทียบ 3 แผนก่อนรันจริง: ควรเลือกแผน receiptdesk (4 agent · 4 บัญชี)",
        E.table("ขั้นที่ 5", "แผน"),
        post=E.note("What-if ใช้เวลา 2 นาทีโดยไม่เสียโทเคนของทีม ช่วยยืนยันข้อจำกัดของเพดาน agent ก่อนเริ่มสร้างจริง", "eye", "ข้อสรุป"),
        tag="ตารางหลัก",
    ))

    # =====================================================================
    # PHASE C · BUILD, TRAIN LoRA & SERVE ON 1 NODE x 2x RTX 4090 (Steps 6-10)
    # =====================================================================
    set_ctx("ระยะ C · สร้างระบบ เทรน และเปิดบริการ", "ระยะ C · สร้างและเปิดบริการ")
    E.add(E.divider(
        "ระยะ C",
        "สร้างระบบ เทรน LoRA และเปิดบริการบน 1 โหนด × 2× RTX 4090",
        "ขั้นที่ 6–10 · Agent Team 14/14 บล็อก · เทรน 1 vs 2 GPU · เปิด NGINX least_conn + 2× vLLM · วัดความจุจริง",
        img=F.HERO_AND_DIVIDERS["phase_c"],
        small="ขั้นที่ 6–10 จาก 15",
    ))

    # Step 6: Agent Team Build
    add_prompt("ขั้นที่ 6", "ระยะ C · ขั้นที่ 6 จาก 15", "Agent Team สร้างระบบตามแผน")
    E.add(E.fig(
        "ผลสร้างระบบจริง: เสร็จครบทั้ง 14/14 บล็อก และผ่านตรวจไขว้ B03 ครบ 89/89 เคส",
        "plan/compare.png",
        "ทีม AI 4 บัญชี (`yolo2, yolo3, cyolo1, gyolo1`) สร้างระบบครบทุกบล็อกตามแผน · บล็อก Business Rule (`B03`) ผ่านการตรวจไขว้ต่าง CLI ภายใน 2 รอบ",
        tag="plan/REPORT.md",
    ))

    # Step 7: Rent 1 node x 2x RTX 4090 & Dataset
    add_prompt("ขั้นที่ 7", "ระยะ C · ขั้นที่ 7 จาก 15", "เช่าเครื่อง 1 โหนด × 2× RTX 4090 และเตรียม Dataset CORD-v2")

    # Dedicated Vast.ai RUNNING console slide (NO prices!)
    E.add(E.slide(
        "สถานะเครื่องบน Vast.ai: 1 โหนด × 2× RTX 4090 พร้อมใช้งานแล้ว (RUNNING)",
        vast_console(
            "RUNNING", "#22c55e",
            "vastai show instances  ·  Instance ID: 62729069",
            [
                ("ป้ายเครื่อง (Label)", "e2e-receipt-nginx"),
                ("โครงสร้างเครื่อง", "1 โหนด × 2× NVIDIA GeForce RTX 4090 (24 GB VRAM ต่อใบ)"),
                ("สเปกและเครือข่าย", "Ireland, IE (Verified) · เน็ตขาเข้า 13,978 Mbps · RAM 206 GB · Disk 80 GB"),
                ("พอร์ตที่เปิด", "8080/tcp (NGINX least_conn + Bearer API Key Auth)"),
                ("โมเดลและ Dataset ที่โหลดเสร็จ", "Qwen/Qwen3-VL-2B-Instruct + naver-clova-ix/cord-v2 (Train 800 / Val 100 / Test 100)"),
            ],
            "เครื่องสร้างเสร็จและโหลดโมเดลพร้อมชุดข้อมูล CORD-v2 เรียบร้อยแล้ว — ขั้นถัดไปคือการเทรน LoRA เปรียบเทียบ 1 GPU กับ 2 GPU",
        ),
        tag="Vast.ai Console",
    ))

    E.add(E.fig(
        "ชุดข้อมูล CORD-v2: ตัวอย่างภาพใบเสร็จจริง 6 ใบคู่กับ JSON เฉลย 5 ช่อง",
        "results/dataset_samples.jpg",
        "Training 800 ใบ (ใช้ 400 ใบเทรน 1 Epoch) · Validation 100 ใบ · Test 100 ใบ — ตัดสินด้วยช่อง `total` ตาม Requirement",
        tag="Dataset",
    ))

    # Step 8: Train LoRA 1 GPU vs 2 GPU + Acceptance Gate
    add_prompt("ขั้นที่ 8", "ระยะ C · ขั้นที่ 8 จาก 15", "เทรน LoRA 1 GPU เทียบ 2 GPU (Data Parallelism) และตัดสินด้วย Acceptance Gate")

    r1, r2 = ts["rows"][0], ts["rows"][1]
    E.add(E.explain(
        f"เทรนด้วย Data Parallelism 2 GPU เร็วขึ้น {r2['speedup']:.2f} เท่า (Efficiency {r2['efficiency']*100:.1f}%)",
        "results/model/train_speed_loss.png",
        [
            f"**1× RTX 4090**: เวลาต่อ Epoch `{r1['epoch_s']:.1f} วินาที` · ความเร็ว `{r1['samples_per_s']:.2f} ตัวอย่างต่อวินาที` · Loss `{r1['train_loss']:.4f}`",
            f"**2× RTX 4090 (Data Parallelism)**: เวลาลดเหลือ **`{r2['epoch_s']:.1f} วินาที`** · ความเร็ว **`{r2['samples_per_s']:.2f} ตัวอย่างต่อวินาที`** · Loss `{r2['train_loss']:.4f}`",
            f"**ผ่านเกณฑ์ความคุ้ม GPU**: Speedup **`{r2['speedup']:.2f}×`** สูงกว่าเกณฑ์ขั้นต่ำ `1.6×` ใน Requirement อย่างชัดเจน",
            "**บันทึกน้ำหนัก LoRA**: เก็บไว้ที่ `results/model/lora_g2/` พร้อมนำไปรวมเข้ากับโมเดลฐานก่อนเปิดบริการ",
        ],
    ))

    E.add(E.explain(
        "ผลวัดบน Test Set 100 ใบ: ผ่าน Acceptance Gate ครบทั้ง 4 ข้อ (Silent Error = 0.0%)",
        "results/model/metrics_before_after.png",
        [
            "**M1 Total Accuracy**: เพิ่มจาก `72.0%` → **`96.0%`** (ผ่านเกณฑ์ `≥ 95.0%`)",
            "**M2 Silent Error Rate**: ลดจาก `18.0%` → **`0.0%`** (ผ่านเกณฑ์ `≤ 1.0%` ไม่มีใบผิดที่หลุดไม่เตือน)",
            "**M3 Flag Recall**: พุ่งจาก `35.7%` → **`100.0%`** (ผ่านเกณฑ์ `≥ 80.0%` จับใบผิดได้ทุกใบ)",
            "**M4 Flag Rate**: อยู่ที่ **`12.0%`** (ผ่านเกณฑ์ `≤ 20.0%` พนักงานไม่ต้องตรวจทุกช่องทุกใบ)",
        ],
    ))

    # Step 9: Deploy NGINX least_conn + 2x vLLM + Web Demo
    add_prompt("ขั้นที่ 9", "ระยะ C · ขั้นที่ 9 จาก 15", "เปิดบริการด้วย NGINX least_conn + 2× vLLM และเชื่อมเว็บ ReceiptDesk")

    E.add(E.tbl(
        "ผลเปิดบริการจริง: รวม LoRA 19.6 วินาที · vLLM 2/2 พร้อมทำงานใน 84.5 วินาที",
        E.table("ขั้นที่ 9", "ส่วนของระบบ"),
        post=E.note("NGINX ปิด `proxy_buffering off` ทำให้ `/copilot` สตรีมสดได้ `TTFT 488–547 ms` และความเร็ว `210.6–217.8 tok/s` ทันที", "eye", "ผลตรวจเส้นทาง"),
        tag="Live Cluster",
    ))

    # Dedicated Demo Login Accounts Slide (EXPLICITLY REQUESTED BY USER!)
    E.add(E.tbl(
        "บัญชีทดสอบสำหรับทดลองใช้งานเว็บ ReceiptDesk ครบทั้ง 4 บทบาท",
        E.table("บัญชีทดสอบสำหรับทดลองใช้งานเว็บ ReceiptDesk", "บทบาท"),
        post=E.note("เปิดใช้งานที่ `http://localhost:3420/login` (เชื่อม `2× RTX 4090`) หรือ `http://localhost:3421/login` (โหมดจำลอง) แล้วล็อกอินด้วยบัญชีด้านบน", "eye", "วิธีทดลองใช้"),
        tag="Web Demo Accounts",
    ))

    # Live Web UI Screenshots (2 slides cleanly paired + 1 full)
    E.add(E.slide(
        "หน้าจอเว็บจริง: อัปโหลดเป็นชุดพร้อมเพดาน 400 ใบ และ Split-Pane OCR Review",
        img_pair([
            ("หน้าอัปโหลดชุดใบเสร็จ (/upload)", "images/lab/web-home.png", "เลือกชื่อลูกค้า อัปโหลด 1–100 ใบ แสดงโควตางานเร่งด่วนและเพดาน 400 ใบ"),
            ("หน้า Split-Pane OCR Review (/receipts/[id])", "images/lab/web-review.png", "เทียบภาพใบเสร็จ CORD-v2 จริงคู่ช่องแก้ไข พร้อมคำนวณธง BR-05 ทันทีเมื่อแก้ยอด"),
        ]),
        tag="Live UI (:3420)",
    ))

    E.add(E.slide(
        "หน้าจอเว็บจริง: ผู้ช่วยบัญชี AI สตรีมสด (/copilot) และสุขภาพคลัสเตอร์ (/telemetry)",
        img_pair([
            ("Live SSE Accounting Copilot (/copilot)", "images/lab/web-copilot-stream.png", "สตรีมสดจาก 2× RTX 4090: TTFT 488 ms · 217.8 tok/s · X-Replica: gpu1"),
            ("Cluster Serving Telemetry (/telemetry)", "images/lab/web-telemetry.png", "แสดงสถานะคลัสเตอร์ ONLINE, gpu0/gpu1, Scaling 101.6% และ Failover 0 error"),
        ]),
        tag="Live UI (:3420)",
    ))

    E.add(E.fig(
        "หน้ารายงานสรุปรายเดือน (/reports): นับเฉพาะใบที่ยืนยันแล้วตั้งแต่วันที่ 1 ถึงสิ้นเดือน",
        "images/lab/web-report.png",
        "แสดงยอดรวม `1,340.00 บาท` ครบ 4 ใบของร้าน `CL-01` เดือน พ.ย. 2026 พร้อมปุ่มส่งออกไฟล์ CSV ที่ตรงยอด 100%",
        tag="Live UI (:3420)",
    ))

    # Step 10: Capacity, Streaming & Failover Benchmarks
    add_prompt("ขั้นที่ 10", "ระยะ C · ขั้นที่ 10 จาก 15", "วัดความจุคลัสเตอร์ 2× RTX 4090 (Continuous Batching · Data Parallelism · Failover)")

    E.add(E.fig(
        "ผลวัดจริง: Continuous Batching + Data Parallelism 2×1 เพิ่มความจุจาก 4 เป็น 640 ผู้ใช้",
        "images/lab/01_capacity_throughput_vllm.png",
        "กำลังผลิตรวมพุ่งจาก `209` → `14,050` → **`28,541 tok/s`** · อ่านใบเสร็จจริง CORD-v2 ได้ **`2,643.9 ใบเสร็จต่อนาที`** (Speedup `1.91×`)",
        tag="results/lb/",
    ))

    bench_tbl = {
        "head": ["การตั้งค่า (1 โหนด × 2× RTX 4090)", "GPU", "Standard SLO", "Fast SLO", "Peak tok/s", "TTFT p95"],
        "rows": [
            ["1 GPU · Sequential (`cap=1`)", "1", "**4** คน", "**4** คน", "**209**", "1.750 s"],
            ["1 GPU · Continuous Batching (`cap=256`)", "1", "**320** คน", "**128** คน", "**14,050**", "1.298 s"],
            ["**2 GPUs · Data Parallelism + NGINX `least_conn`**", "**2**", "**640** คน", "**257** คน", "**28,541**", "**1.547 s**"],
        ],
    }
    eq_html = E.eqbox(
        [
            r"\text{Scaling Efficiency} = \frac{28{,}541}{2 \times 14{,}050} = 101.6\%",
            r"\text{OCR Speedup} = \frac{2{,}643.9}{1{,}383.3} = 1.91\times",
        ],
        sub="1-User Baseline = 219.41 tok/s (TTFT 19.6 ms) · เกณฑ์ Fast SLO = 109.7 tok/s",
    )
    E.add(E.tbl(
        "ตารางสรุปผลวัดจริงบน 1 โหนด × 2× RTX 4090 เทียบทั้ง 3 การตั้งค่า",
        bench_tbl,
        post=eq_html,
        tag="ตารางหลัก",
    ))

    E.add(E.fig(
        "เส้นโค้ง TTFT p95 และความเร็วต่อผู้ใช้: 2 GPU ขยายเส้นความจุไปทางขวาครบ 2 เท่า",
        "images/lab/02_ttft_speed_curves.png",
        "ที่ 640 ผู้ใช้พร้อมกัน `2× RTX 4090` ยังคุม `TTFT p95 = 1.547 วินาที` (ต่ำกว่าเกณฑ์ 2.0 วินาที) และ `Speed p5` ผ่าน SLO",
        tag="results/lb/",
    ))

    E.add(E.fig(
        "Concurrency Cap (32 vs 256) และความสมดุลของ NGINX least_conn (49.4% / 50.6%)",
        "images/lab/03_concurrency_and_mix.png",
        "`--max-num-seqs 256` ให้ Throughput สูงกว่า `cap=32` ถึง **2.68 เท่า** · `least_conn` เกลี่ยคำถามสั้นผสมยาวลง `gpu0`/`gpu1` เกือบ 50/50",
        tag="results/lb/",
    ))

    E.add(E.fig(
        "ทดสอบ Failover กลางสตรีม: ปิด gpu1 (:8002) ที่ t=14s แล้ว Error หลังฟื้นตัว = 0 ครั้ง",
        "images/lab/04_failover_timeline.png",
        "NGINX Passive Health Check (`max_fails=1 fail_timeout=30s`) ตัด `gpu1` ออกอัตโนมัติและโอนโหลดทั้งหมดไป `gpu0` (~13,800 tok/s) โดยไม่ล่ม",
        tag="NFR-06",
    ))

    # =====================================================================
    # PHASE D · PLAYWRIGHT VERIFICATION (28 TCs + PER-TC GIFs + BUG HUNT) (Steps 11-15)
    # =====================================================================
    set_ctx("ระยะ D · พิสูจน์ระบบก่อนส่งมอบ", "ระยะ D · พิสูจน์และส่งมอบ")
    E.add(E.divider(
        "ระยะ D",
        "พิสูจน์ระบบด้วย Playwright 28 ข้อ พร้อม .gif ทุกข้อและ Bug Hunt",
        "ขั้นที่ 11–15 · Exploration 6 Charter · Test Plan ตรวจไขว้ · Playwright 28/28 ผ่านพร้อม .gif รายข้อ · Bug Hunt 3/3 · ลบ GPU",
        img=F.HERO_AND_DIVIDERS["phase_d"],
        small="ขั้นที่ 11–15 จาก 15",
    ))

    # Step 11: Exploration
    add_prompt("ขั้นที่ 11", "ระยะ D · ขั้นที่ 11 จาก 15", "Test Charter และ Exploration พร้อมกัน")
    E.add(E.slide(
        "ผล Exploration 6 Charter พร้อมกัน: พบจุดเสี่ยง BR-05 ก่อนเขียน Automated Test",
        E.tiles([
            ("Test Charter", "6 ชุด", "รันขนานกัน 6 session แยกตามบทบาท", ""),
            ("รายการที่สำรวจจริง", "72 ข้อ", "ผ่าน ✅ 64 · ข้อสังเกต ⚠️ 8 · ล้ม ❌ 0", "ok"),
            ("จุดเสี่ยงสำคัญที่พบ", "BR-05", "แก้ยอดในหน้า Review แล้วธงยอดไม่ตรงต้องคำนวณใหม่สด", "warn"),
        ]) + E.note("จุดเสี่ยง BR-05 ถูกแก้ไขในฝั่งเว็บและยืนยันผ่านอัตโนมัติใน `TC-09` พร้อมวิดีโอ `.gif` หลักฐาน", "eye", "คุณค่าของ Exploration"),
        tag="test/EXPLORATION.md",
    ))

    # Step 12: Test Plan & Review
    add_prompt("ขั้นที่ 12", "ระยะ D · ขั้นที่ 12 จาก 15", "Test Plan และการตรวจไขว้ต่างบัญชี")
    strat_tbl = {
        "head": ["โหมดการทดสอบ", "พอร์ต", "จำนวน TC", "เป้าหมายการพิสูจน์", "ผลจริง"],
        "rows": [
            ["Mock Deterministic (`BUG_MODE=0`)", "`3421`", "**22 ข้อ** (`TC-01..22`)", "เส้นแบ่ง 0.01 บาท, 0.01 ความมั่นใจ, 10 MB+1B, เพดาน 400, RBAC 4 บทบาท", "✅ 22/22 ผ่าน"],
            ["Live `2× RTX 4090` (`AI_MODE=vllm`)", "`3420`", "**3 ข้อ** (`TC-23..25`)", "อ่าน CORD-v2 จริง, สตรีมสด SSE Copilot (`TTFT/tok/s/X-Replica`), Telemetry", "✅ 3/3 ผ่าน"],
            ["Bug Hunt (`BUG_MODE=1`)", "`3421`", "**3 ข้อ** (`TC-26..28`)", "พิสูจน์ว่าชุดทดสอบจับบั๊กซ่อน 3 ตัว (`BR-05`, `BR-09`, `BR-14`) ได้จริง", "✅ จับครบ 3/3"],
        ],
    }
    E.add(E.tbl(
        "กลยุทธ์ทดสอบ 3 ชั้น: แยกเส้นแบ่งแน่นอนออกจากชุดทดสอบสดบน 2× RTX 4090",
        strat_tbl,
        post=E.note("แผนทดสอบผ่านการตรวจไขว้ต่างบัญชีโดย `cyolo1` (`test/PLAN-REVIEW.md`) และแก้ข้อรุนแรงสูงครบ 30/30 ข้อ", "eye", "การตรวจไขว้"),
        tag="test/TEST-PLAN.md",
    ))

    # Step 13: Playwright 28 TCs + Per-TC GIFs
    add_prompt("ขั้นที่ 13", "ระยะ D · ขั้นที่ 13 จาก 15", "Playwright E2E 28 ข้อพร้อมบันทึก .gif รายข้อ และวิดีโอสาธิตเริ่มจาก /login")

    # Summary Table by Group (28/28 PASS + 28/28 GIFs)
    grp_counts = {}
    for r in e2e["results"]:
        g = r["group"]
        grp_counts.setdefault(g, [0, 0, []])
        grp_counts[g][0] += 1
        if r["status"] == "PASS":
            grp_counts[g][1] += 1
        grp_counts[g][2].append(r["id"])
    grp_tbl = {
        "head": ["กลุ่มการทดสอบ", "รหัส Test Case", "ผ่าน / ทั้งหมด", "ไฟล์ .gif หลักฐาน"],
        "rows": [
            [g, f"`{ids[0]}..{ids[-1]}`" if len(ids) > 1 else f"`{ids[0]}`", f"✅ **{p}/{t}**", f"ครบ {t} ไฟล์"]
            for g, (t, p, ids) in grp_counts.items()
        ] + [
            ["**รวมทั้งหมด**", "`TC-01..TC-28`", f"✅ **{e2e['passed']}/{e2e['total']} (100.0%)**", f"**ครบ {e2e['gifs_recorded']} ไฟล์** (`test/index.html`)"]
        ],
    }
    E.add(E.tbl(
        "ผลทดสอบ Playwright E2E ครบทั้ง 9 กลุ่ม: ผ่าน 28/28 ข้อ พร้อม .gif รายข้อครบทุกข้อ",
        grp_tbl,
        post=E.note("เปิดดูและเล่น `.gif` ครบทั้ง 28 ข้อแบบโต้ตอบได้ที่ [test/index.html](test/index.html) และตารางเต็มใน [test/TEST-REPORT.md](test/TEST-REPORT.md)", "eye", "หลักฐานครบ 100%"),
        tag="ตารางหลัก",
    ))

    # LIVE SIGNATURE DEMO GIF #1 (Starts at /login!)
    E.add(E.fig(
        "วิดีโอสาธิตสด #1 (6.50 วินาที): เริ่มจากหน้า /login → อัปโหลด CORD-v2 → Review → รายงาน",
        F.LIVE_DEMOS["review_flow"],
        "เริ่มจากการพิมพ์ `kitti@receiptdesk.test` บนหน้า `/login` → อัปโหลดใบเสร็จจริงไป `2× RTX 4090` → ตรวจยืนยันบน Split-Pane → ตรวจรายงานรายเดือน",
        tag="Live Demo .gif (:3420)",
    ))

    # LIVE SIGNATURE DEMO GIF #2 (Live SSE Copilot + Telemetry)
    E.add(E.fig(
        "วิดีโอสาธิตสด #2 (6.50 วินาที): สตรีมสด AI Copilot (2× RTX 4090) + หน้า Telemetry",
        F.LIVE_DEMOS["streaming_copilot"],
        "เห็นคำตอบภาษาไทยไหลสดทีละโทเคนผ่าน NGINX `proxy_buffering off` พร้อมค่า `TTFT 488 ms`, `217.8 tok/s`, `X-Replica: gpu1` และสถานะ `ONLINE`",
        tag="Live Demo .gif (:3420)",
    ))

    # 8 PER-TC GIF COMPARISON SLIDES (15 distinct TC GIFs directly playable on slides!)
    E.add(E.slide(
        "หลักฐาน .gif รายข้อ (1/8) · การรับชุดไฟล์และเส้นแบ่งขนาด 10.00 MB",
        gif_pair([
            ("TC-01 · รับครบ 3 ชนิดไฟล์ (JPG, PNG, PDF 1 หน้า)", "images/tests/TC-01.gif", "ล็อกอินคุณพิมพ์ → อัปโหลด 3 ไฟล์ถูกต้อง → accepted = 3 (BR-01..03)"),
            ("TC-04 · เส้นแบ่งขนาดไฟล์ 10.00 MB vs +1 ไบต์", "images/tests/TC-04.gif", "10.00 MB พอดีรับได้ (1) · 10.00 MB + 1 ไบต์ถูกปฏิเสธทั้งชุด (0) (BR-02)"),
        ]),
        tag="Playwright .gif",
    ))

    E.add(E.slide(
        "หลักฐาน .gif รายข้อ (2/8) · ธงความมั่นใจ 0.89 และคำนวณธง BR-05 สดเมื่อแก้ยอด",
        gif_pair([
            ("TC-06 · เส้นแบ่งความมั่นใจ 0.89 / 0.90 / 0.91", "images/tests/TC-06.gif", "0.89 ติดธงสีส้มไม่แน่ใจยอดรวม · 0.90 และ 0.91 ไม่ติดธง (BR-04)"),
            ("TC-09 · แก้ยอดรวมแล้วธงยอดไม่ตรงคำนวณใหม่ทันที", "images/tests/TC-09.gif", "แก้เป็น 120.00 → ธงขึ้นทันที · แก้กลับ 100.00 → ธงหายทันที (BR-05 Live)"),
        ]),
        tag="Playwright .gif",
    ))

    E.add(E.slide(
        "หลักฐาน .gif รายข้อ (3/8) · ยืนยันผ่าน Split-Pane และประวัติแก้ไข (Audit + Reopen)",
        gif_pair([
            ("TC-11 · ตรวจแก้ เลือกหมวด ติ๊กตรวจยอด และกดยืนยัน", "images/tests/TC-11.gif", "พนักงานยืนยันใบเสร็จครบขั้นตอน → แสดงชื่อผู้ยืนยันและเวลา (FR-12)"),
            ("TC-12 · Audit Trail ค่า AI เดิม + หัวหน้าทีมเปิดใบกลับ", "images/tests/TC-12.gif", "เก็บประวัติแก้ไขครบทุกช่อง และคุณกิตติเปิดใบที่ยืนยันแล้วกลับได้ (FR-13)"),
        ]),
        tag="Playwright .gif",
    ))

    E.add(E.slide(
        "หลักฐาน .gif รายข้อ (4/8) · ชุดเร่งด่วน 10 vs 11 ใบ และเพดาน 400 ใบ (HTTP 429)",
        gif_pair([
            ("TC-13 · เส้นแบ่งชุดเร่งด่วน 10 ใบ vs 11 ใบ", "images/tests/TC-13.gif", "คุณกิตติตั้งชุดเร่งด่วน 10 ใบผ่าน · 11 ใบถูกปฏิเสธทันที (BR-08)"),
            ("TC-16 · เพดานใบค้าง 400 ใบและแจ้งนาทีลองใหม่", "images/tests/TC-16.gif", "ใบที่ 400 รับได้ · ใบที่ 401 ตอบ HTTP 429 พร้อมระบุนาทีลองใหม่ (BR-11..12)"),
        ]),
        tag="Playwright .gif",
    ))

    E.add(E.slide(
        "หลักฐาน .gif รายข้อ (5/8) · ลองอ่านครบ 3 ครั้งย้าย /unreadable และพิมพ์เองจนยืนยัน",
        gif_pair([
            ("TC-17 · fail2 ผ่านครั้งที่ 3 vs fail3 ย้ายหน้าอ่านไม่ได้", "images/tests/TC-17.gif", "หยุดส่งซ้ำอัตโนมัติใน PostgreSQL เมื่อครบ 3 ครั้ง (BR-07)"),
            ("TC-18 · พนักงานเปิดใบ unreadable พิมพ์ 5 ช่องเอง", "images/tests/TC-18.gif", "พิมพ์ชื่อร้าน วันที่ และยอด 185.00 บาทเองแล้วยืนยันเข้าบัญชีสำเร็จ (FR-17)"),
        ]),
        tag="Playwright .gif",
    ))

    E.add(E.slide(
        "หลักฐาน .gif รายข้อ (6/8) · รายงานรายเดือน CSV และพอร์ทัลส่วนตัวคุณสมชาย",
        gif_pair([
            ("TC-19 · สรุปรายเดือนนับวันที่ 1–30 และออก CSV", "images/tests/TC-19.gif", "ร้าน CL-01 เดือน พ.ย. 2026 = 1,340.00 บาท ครบ 4 ใบตรง CSV (BR-14)"),
            ("TC-22 · พอร์ทัลลูกค้าคุณสมชายแยกขาดข้อมูลร้านอื่น", "images/tests/TC-22.gif", "เห็นเฉพาะร้านตน 1,340.00 บาท ไม่เห็นร้าน CL-02 หรือใบที่ยังไม่ยืนยัน (FR-25..29)"),
        ]),
        tag="Playwright .gif",
    ))

    live_ocr_act = live["results"][0]["actual"]
    live_sse_act = live["results"][1]["actual"]
    E.add(E.slide(
        "หลักฐาน .gif รายข้อ (7/8) · ทดสอบสดกับ 2× RTX 4090 (CORD-v2 OCR + SSE Copilot)",
        gif_pair([
            ("TC-23 · อ่านใบเสร็จ CORD-v2 สด 3 ใบ (2× vLLM)", "images/tests/TC-23.gif", live_ocr_act),
            ("TC-24 · สตรีมสด /copilot (proxy_buffering off)", "images/tests/TC-24.gif", live_sse_act),
        ]),
        tag="Live 2× RTX 4090 .gif",
    ))

    # Step 14: Bug Hunt
    add_prompt("ขั้นที่ 14", "ระยะ D · ขั้นที่ 14 จาก 15", "Bug Hunt (BUG_MODE=1) พร้อม .gif และรายงานส่งมอบ")

    bug_tbl = {
        "head": ["บั๊กที่ซ่อนใน BUG_MODE=1", "TC ที่จับได้", "ความผิดพลาดที่ตรวจพบจริง", "ความรุนแรง"],
        "rows": [
            ["`BR-05` ผลต่าง `1.01–1.49` ไม่ติดธง", "`TC-26`", "ปัดผลต่างลงเป็นบาทเต็มทำให้ `mismatch = false`", "วิกฤต"],
            ["`BR-09` โควตาครบ 5 แล้วยังตั้งงานที่ 6 ได้", "`TC-27`", "เทียบ `> 5` แทน `>= 5` จึงรับงานที่ 6 ได้ (`accepted = 1`)", "สูง"],
            ["`BR-14` รายงานตัดใบเสร็จวันที่ 1 ทิ้ง", "`TC-28`", "ยอด CL-01 เหลือ `1,139.50` (3 ใบ) แทน `1,340.00` (4 ใบ)", "วิกฤต"],
        ],
    }
    E.add(E.tbl(
        "ผล Bug Hunt (BUG_MODE=1): ชุดทดสอบเส้นแบ่งจับบั๊กซ่อนได้ครบ 3 จาก 3 ตัว (100%)",
        bug_tbl,
        post=E.note("หลังบันทึกหลักฐาน `.gif` ครบทั้ง 3 บั๊ก ระบบถูกคืนค่า `BUG_MODE=0` และสรุปส่งมอบไว้ที่ [DELIVERY.md](DELIVERY.md)", "eye", "สรุป Bug Hunt"),
        tag="test/BUG-HUNT.md",
    ))

    E.add(E.slide(
        "หลักฐาน .gif รายข้อ (8/8) · Bug Hunt จับบั๊กซ่อนครบทั้ง 3 ตัวแบบเห็นคาตา",
        gif_pair([
            ("TC-26 · จับบั๊ก BR-05", "images/tests/TC-26.gif", "ผลต่าง 1.01–1.49 บาทไม่ติดธง"),
            ("TC-27 · จับบั๊ก BR-09", "images/tests/TC-27.gif", "งานเร่งด่วนที่ 6 หลุดผ่านได้"),
            ("TC-28 · จับบั๊ก BR-14", "images/tests/TC-28.gif", "ยอดเหลือ 1,139.50 ตัดวันที่ 1 ทิ้ง"),
        ]),
        tag="Bug Hunt 3/3 .gif",
    ))

    # Step 15: Destroy GPU
    add_prompt("ขั้นที่ 15", "ระยะ D · ขั้นที่ 15 จาก 15", "ลบเครื่อง GPU (e2e-receipt-nginx) และปิดระบบ")

    E.add(E.slide(
        "ยืนยันการลบเครื่อง GPU (DESTROYED): คงเหลือ 0 เครื่อง และล้าง API key แล้ว",
        vast_console(
            "DESTROYED · 0 INSTANCES", "#ef4444",
            "vastai destroy instance 62729069  &&  vastai show instances",
            [
                ("เครื่องที่ลบ", "Instance ID 62729069 · 1 โหนด × 2× RTX 4090 (ป้าย e2e-receipt-nginx)"),
                ("ระยะเวลาเปิดใช้งานรอบ Live", "~17 นาที (รวม LoRA, เปิด 2× vLLM + NGINX, รัน Live E2E และบันทึก .gif)"),
                ("ผลตรวจ vastai show instances", "Total: 0 instances (ไม่มีเครื่องป้าย e2e-receipt-nginx ค้างอยู่)"),
                ("สถานะ Docker Compose ในเครื่อง", "หยุด receiptdesk-nginx (:3420) และ receiptdesk-mock (:3421) เรียบร้อย"),
                ("ความปลอดภัย API Key", "ล้าง VLLM_API_KEY จริงออกจาก .env และลบไฟล์คีย์ชั่วคราวแล้ว"),
            ],
            "ข้อมูลบัญชี รูปใบเสร็จ ผลวัด JSON และหลักฐาน .gif ทั้งหมดถูกจัดเก็บถาวรไว้บนเครื่องสำนักงานครบ 100%",
        ),
        tag="Vast.ai Console",
    ))

    # =====================================================================
    # SUMMARY & CLOSING
    # =====================================================================
    set_ctx("สรุปผลการส่งมอบ · ReceiptDesk", "สรุปและส่งมอบ")
    verdict_tbl = {
        "head": ["มิติการประเมิน", "เป้าหมายจาก Requirement", "ผลที่วัดได้จริง", "สถานะ"],
        "rows": [
            ["โมเดล OCR (Acceptance Gate)", "M1 ≥ 95%, M2 ≤ 1%, M3 ≥ 80%, M4 ≤ 20%", "M1 `96.0%` · M2 `0.0%` · M3 `100.0%` · M4 `12.0%`", "✅ ผ่าน"],
            ["เทรน 2 GPU (Data Parallelism)", "Speedup ≥ 1.6×", "**1.89×** (205.9s → 108.8s · Efficiency `94.6%`)", "✅ ผ่าน"],
            ["กำลังผลิต OCR & Copilot (2× 4090)", "100 ใบ ≤ 30 นาที · TTFT p95 ≤ 2.0s", "**2,643.9 ใบ/นาที** · **640 ผู้ใช้** · **28,541 tok/s**", "✅ ผ่าน"],
            ["NGINX `least_conn` & Failover", "สมดุลโหลด · ปิด 1 GPU ต้องไม่ล่ม", "สมดุล `49.4% / 50.6%` · **Error หลังฟื้นตัว = 0 ครั้ง**", "✅ ผ่าน"],
            ["Playwright E2E + Bug Hunt", "ผ่าน 100% + จับบั๊กซ่อน 3/3", "**28/28 ผ่าน (100.0%)** · **28/28 `.gif`** · จับบั๊ก **3/3**", "✅ ผ่าน"],
        ],
    }
    E.add(E.tbl(
        "สรุปผลการส่งมอบ ReceiptDesk: ผ่านเกณฑ์วิศวกรรมและธุรกิจครบทุกมิติ",
        verdict_tbl,
        tag="READY FOR DELIVERY",
    ))

    takeaways = (
        '<div style="display:flex;flex-direction:column;gap:18px;margin-top:8px">'
        + "".join(
            '<div style="display:flex;gap:18px;align-items:baseline;padding-bottom:14px;border-bottom:1px solid var(--line)">'
            f'<span style="font-size:1.7em;font-weight:800;color:var(--teal);min-width:36px">{n}</span>'
            f'<div><div style="font-weight:700;color:var(--navy);font-size:1.06em;margin-bottom:4px">{E.md(h)}</div>'
            f'<div style="color:var(--ink);font-size:.92em;line-height:1.45">{E.md(b)}</div></div></div>'
            for n, h, b in [
                ("1", "เลือกสถาปัตยกรรม AI Serving ให้ตรงชนิดงานตั้งแต่ต้น",
                 "โมเดล VLM ขนาด 2B พอดี VRAM 1 ใบ จึงใช้ 1 vLLM Replica ต่อ 1 GPU (Data Parallelism 2×1) + Continuous Batching (`--max-num-seqs 256`) หลัง NGINX `least_conn` ปิด buffering — เรียบง่าย ไม่ต้องมีบริการตัวกลางซับซ้อน แต่ได้ Scaling Efficiency 101.6% และ Failover 0 error"),
                ("2", "ให้ฝั่งเว็บเป็นเจ้าของความจริง เพื่อให้ Cloud GPU ลบทิ้งได้ทุกเมื่อ",
                 "รูปต้นฉบับ สถานะใบเสร็จ 5 สถานะ ประวัติแก้ไข และกติกา Business Rule อยู่ใน PostgreSQL 16 บนเครื่องสำนักงาน ทำให้เปิดเครื่อง `2× RTX 4090` เฉพาะช่วงใช้งานและลบทิ้งทันทีโดยข้อมูลไม่หาย"),
                ("3", "พิสูจน์เส้นแบ่งทุกข้อด้วย Playwright และบันทึก .gif หลักฐานรายข้อ",
                 "แยกชุดทดสอบเส้นแบ่ง 22 ข้อ (`3421`) ออกจากชุดสด `2× RTX 4090` 3 ข้อ (`3420`) และ Bug Hunt 3 ข้อ พร้อม `.gif` ครบทั้ง 28 ข้อ ทำให้ผู้ตรวจและลูกค้ามองเห็นพฤติกรรมจริงทุกกรณี"),
            ]
        )
        + '</div>'
    )
    E.add(E.slide("บทเรียนสำคัญ 3 ข้อจากการสร้าง ReceiptDesk ครบวงจร", takeaways, tag="Key Takeaways"))

    E.add(E.divider(
        "จบหัวข้อที่ 2",
        "ReceiptDesk พร้อมส่งมอบให้สำนักงานบัญชี",
        '<span style="display:inline-flex;gap:20px;flex-wrap:wrap;align-items:center">'
        '<a href="README.md" style="display:inline;color:#7dd3fc;border-bottom:1px solid rgba(125,211,252,.5)">README.md</a>'
        '<a href="PROMPTS.md" style="display:inline;color:#7dd3fc;border-bottom:1px solid rgba(125,211,252,.5)">PROMPTS.md</a>'
        '<a href="test/index.html" style="display:inline;color:#7dd3fc;border-bottom:1px solid rgba(125,211,252,.5)">ศูนย์รวม .gif 28 ข้อ</a>'
        '<a href="DELIVERY.md" style="display:inline;color:#7dd3fc;border-bottom:1px solid rgba(125,211,252,.5)">DELIVERY.md</a>'
        '</span>',
        img=F.HERO_AND_DIVIDERS["cover"],
        small="ReceiptDesk · 1 โหนด × 2× RTX 4090",
    ))

    return E.write(E.SL, out="ReceiptDesk_Slides.html", title="ReceiptDesk · สไลด์ประกอบการสอน (1 โหนด × 2× RTX 4090)")


if __name__ == "__main__":
    build()
