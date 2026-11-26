"""Build SiteSafe_Inspect_Slides.html from scratch using slides_engine.py + README.md + real JSON evidence."""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
os.chdir(ROOT)
sys.path.insert(0, HERE)

import slides_engine as E
from slides_figures import SLIDE_ART, STORY_ART, THEORY_DIAGRAMS

# Load README.md and verified result files
E.load('README.md')
LB = json.load(open('results/lb/summary.json', encoding='utf-8'))
M_BEFORE = json.load(open('results/model/metrics_before.json', encoding='utf-8'))
M_AFTER = json.load(open('results/model/metrics_after.json', encoding='utf-8'))
E2E = json.load(open('test/evidence/e2e_results.json', encoding='utf-8'))
BH = json.load(open('test/evidence/bughunt_results.json', encoding='utf-8'))
ALL_TCS = E2E + BH

# Helper CSS for clean editorial media grids & terminal console cards (zero AI-card patterns)
EXTRA_CSS = """
<style>
.editorial-row { display:grid; gap:20px; align-items:start; }
.editorial-row.c2 { grid-template-columns:1fr 1fr; }
.editorial-row.c3 { grid-template-columns:1fr 1fr 1fr; }
.editorial-row.c4 { grid-template-columns:1fr 1fr 1fr 1fr; }
.media-item { display:flex; flex-direction:column; gap:8px; }
.media-item img { width:100%; height:auto; max-height:460px; object-fit:contain; border-radius:8px; border:1px solid #CBD5E1; background:#0F172A; cursor:zoom-in; }
.media-item.tall img { max-height:520px; }
.media-item.compact img { max-height:230px; }
.media-cap { font-size:0.84em; color:#334155; line-height:1.35; }
.media-cap strong { color:#0F172A; }
.persona-img { width:100%; height:220px; object-fit:cover; border-radius:8px; border:1px solid #CBD5E1; }
.persona-role { font-weight:800; color:#0F766E; font-size:0.95em; margin-top:4px; }
.persona-desc { font-size:0.86em; color:#334155; line-height:1.4; }
.console-box { background:#0F172A; color:#E2E8F0; border-radius:10px; padding:18px 22px; font-family:ui-monospace,Consolas,monospace; font-size:0.84em; line-height:1.55; border-left:5px solid #0EA5E9; }
.console-box.destroyed { border-left-color:#16A34A; }
.console-hdr { display:flex; justify-content:space-between; align-items:center; padding-bottom:10px; margin-bottom:12px; border-bottom:1px solid #334155; font-family:system-ui,"Leelawadee UI",sans-serif; color:#F8FAFC !important; }
.console-hdr strong { color:#F8FAFC !important; font-size:1.05em; }
.status-run { background:#15803D; color:#FFF; padding:3px 10px; border-radius:4px; font-weight:800; font-size:0.85em; }
.status-del { background:#475569; color:#FFF; padding:3px 10px; border-radius:4px; font-weight:800; font-size:0.85em; }
.compact-tbl table { font-size:0.74em !important; }
.compact-tbl td, .compact-tbl th { padding:5px 8px !important; }
.step-list { list-style:none; padding:0; margin:0; display:flex; flex-direction:column; gap:16px; }
.step-list li { display:grid; grid-template-columns:48px 1fr; gap:16px; padding-bottom:12px; border-bottom:1px solid #E2E8F0; align-items:start; }
.step-list li:last-child { border-bottom:none; }
.step-num { font-size:1.35em; font-weight:800; color:#0F766E; line-height:1.1; }
.badge-ok { color:#15803D; font-weight:800; }
.badge-bug { color:#DC2626; font-weight:800; }
</style>
"""

def add_prompt(heading_prefix, prompt_idx, label):
    """Extract verbatim prompt alert from README.md by index (0-based across README) and add slides."""
    alerts = [b for s in E.SECS for b in E.walk(s['blocks']) if b.get('t') == 'alert' and b.get('kind') == 'IMPORTANT']
    alert = alerts[prompt_idx]
    for s in E.prompt_slides(alert, E.CTX['kicker'], label):
        E.add(s)

def gif_grid(title, items, cols=2, tag='Playwright GIF Evidence', post=''):
    """Render 2, 3, or 4 animated .gif items cleanly for side-by-side visual verification."""
    cls = 'compact' if len(items) == 4 else ''
    html_items = []
    for src, head, sub in items:
        html_items.append(
            f'<div class="media-item {cls}">'
            f'<img src="{E.esc(src)}" alt="{E.esc(head)}">'
            f'<div class="media-cap"><strong>{E.esc(head)}</strong> — {E.esc(sub)}</div>'
            f'</div>'
        )
    grid_cls = f'c{cols}'
    body = f'<div class="editorial-row {grid_cls}">' + ''.join(html_items) + '</div>'
    if post:
        body += E.note(post)
    E.add(E.slide(title, body, tag=tag))

def img_pair(title, left_src, left_cap, right_src, right_cap, tag='', post=''):
    body = (
        '<div class="editorial-row c2">'
        f'<div class="media-item tall"><img src="{E.esc(left_src)}" alt="{E.esc(left_cap)}"><div class="media-cap">{E.inline(left_cap)}</div></div>'
        f'<div class="media-item tall"><img src="{E.esc(right_src)}" alt="{E.esc(right_cap)}"><div class="media-cap">{E.inline(right_cap)}</div></div>'
        '</div>'
    )
    if post:
        body += E.note(post)
    E.add(E.slide(title, body, tag=tag))

def build():
    # ==================== SLIDES 1–4: OPENING (REORGANIZED & CRYSTAL CLEAR) ====================
    E.CTX.update(kicker='SiteSafe Inspect', group='1 · ภาพรวมโครงการ')

    # Slide 1: Cover (Brand-new cyolo1 16:9 artwork)
    E.add(E.cover(
        'SiteSafe Inspect',
        'สร้างระบบตรวจอุปกรณ์นิรภัยหน้างานก่อสร้างครบวงจร · 1 โหนด × 2× RTX 4090 · NGINX least_conn + 8× FastAPI Micro-batching',
        SLIDE_ART['cover'],
        small='กรณีศึกษา บริษัท ไทยมั่นคงก่อสร้าง จำกัด · ภาพจำลอง',
    ))

    # Slide 2: Headline Outcome Hero
    d4 = LB['designs'][3]
    E.add(E.hero(
        'ผลลัพธ์จริงของโครงการ · 1 โหนด × 2× RTX 4090',
        'เพิ่มความจุ 8.0 เท่า ป้องกันเครื่องล่ม 0.00% และผ่านชุดทดสอบครบ 27 ข้อ',
        SLIDE_ART['hero_outcome'],
        [
            ('ความจุพร้อมกัน (Design #4)', f"{d4['capacity']} ผู้ใช้", f"เพิ่มขึ้น 8.0 เท่า · p95 = {d4['p95_at_cap_ms']} มิลลิวินาที", 'good'),
            ('ปริมาณงานสูงสุด (คำขอต่อวินาที)', f"{d4['max_rps']}", 'NGINX least_conn + 8× FastAPI Micro-batching', ''),
            ('ความผิดพลาดเมื่อ GPU ล่ม', '0.00%', 'Failover ON ย้ายคำขอไป Process ที่รอดอัตโนมัติ', 'good'),
            ('Playwright + Bug Hunt', '24/24 + 3/3', 'บันทึกวิดีโอ .gif หลักฐานครบทุก Test Case', ''),
        ],
        post='ตัวเลขทั้งหมดวัดจริงจาก 1 โหนด × 2× RTX 4090 และชุดทดสอบ Playwright อัตโนมัติ · ภาพจำลอง',
        tag='results/lb/summary.json · test/evidence/',
    ))

    # Slide 3: Customer Problem & Core Question
    E.add(E.explain(
        'ปัญหาลูกค้า: ตรวจรูป 300+ ใบต่อวันด้วยตา หลุดคนไม่ใส่หมวกและทำรายงานไม่ทัน 18:00 น.',
        STORY_ART['overload'],
        [
            '**3 ไซต์งานพร้อมกัน:** หัวหน้างานถ่ายรูปหน้างานวันละ 3 รอบ รวมกว่า 300 รูปต่อวัน และช่วงเร่งด่วนอัปโหลดพร้อมกันถึง 150 รูป',
            '**ความเสี่ยงด้านความปลอดภัย:** เมื่อตรวจด้วยตาไม่ทัน ทำให้หลุดภาพคนงานไม่ใส่หมวกนิรภัยและไม่ใส่เสื้อสะท้อนแสง',
            '**โจทย์ของระบบ:** ต้องตรวจจับแม่นยำ ตอบกลับเร็วช่วงเร่งด่วน รูปห้ามหาย แยกสิทธิ์ 3 บทบาท และออกรายงานก่อน 18:00 น.',
        ],
        post='ภาพจำลองจากสถานการณ์หน้างานของบริษัท ไทยมั่นคงก่อสร้าง จำกัด',
    ))

    # Slide 4: End-to-End 4-Phase Roadmap & Design #4 Overview
    E.add(E.explain(
        'เส้นทางวิศวกรรม 4 ระยะ: จากบทสัมภาษณ์สู่ระบบจริงบน 2× RTX 4090 และ Playwright 27 ข้อ',
        SLIDE_ART['diag_phases'],
        [
            '**ระยะ A · วิเคราะห์โจทย์และออกแบบ:** แปลงบทสัมภาษณ์เป็น User Stories, กติกา 7 ข้อ และสถาปัตยกรรม Design #4',
            '**ระยะ B · วางแผน DAG 10 บล็อก:** จัดสายวิกฤตและกระจายงานขนานให้ทีม Agent (`yolo2`, `yolo3`, `cyolo1`)',
            '**ระยะ C · สร้างและวัดผลบน 2× RTX 4090:** เว็บ Next.js 15 + PostgreSQL เชื่อมตรง NGINX `least_conn` + 8× FastAPI',
            '**ระยะ D · ทดสอบ 27 ข้อ + Bug Hunt:** รัน Playwright บันทึก `.gif` ทุกข้อ ยืนยันจับบัก 3/3 แล้วลบเครื่อง GPU ทันที',
        ],
    ))

    # ==================== CUSTOMER STORY & INTERVIEW ====================
    E.CTX.update(kicker='เรื่องราวลูกค้า · บริษัท ไทยมั่นคงก่อสร้าง จำกัด', group='2 · เรื่องราวและบทสัมภาษณ์')

    # Slide 5: 3 Personas
    personas_html = (
        '<div class="editorial-row c3">'
        f'<div><img class="persona-img" src="{STORY_ART["wichai"]}" alt="วิชัย"><div class="persona-role">วิชัย · หัวหน้างานไซต์ (Supervisor)</div><div class="persona-desc">เดินตรวจหน้างานวันละ 3 รอบ ต้องการอัปโหลดรูปเป็นชุดไม่เกิน 50 รูป ดูเฉพาะไซต์ตัวเอง และแก้ผลได้เมื่อโมเดลทักผิด</div></div>'
        f'<div><img class="persona-img" src="{STORY_ART["napa"]}" alt="นภา"><div class="persona-role">นภา · ผู้จัดการความปลอดภัย (Manager)</div><div class="persona-desc">ดูแลครบ 3 ไซต์ ต้องการดูเฉพาะรูปที่มีปัญหา (ไม่ผ่าน/เตือน) ตรวจสอบประวัติการแก้ผล และสรุปรายงานก่อน 18:00 น.</div></div>'
        f'<div><img class="persona-img" src="{STORY_ART["thana"]}" alt="ธนา"><div class="persona-role">ธนา · ผู้บริหาร (Executive)</div><div class="persona-desc">ต้องการดูรายงานเปรียบเทียบอัตราผ่านทั้ง 3 ไซต์ (ต่ำกว่า 90% ขึ้นสีแดง) และสถานะเครื่อง GPU โดยไม่เปิดดูรูปหน้างาน</div></div>'
        '</div>'
        + E.note('ภาพจำลอง · บทบาททั้ง 3 กลุ่มถูกบังคับสิทธิ์ที่ฝั่งเซิร์ฟเวอร์ทุก API (NFR-06)')
    )
    E.add(E.slide('ผู้ใช้ทั้ง 3 บทบาทมีขอบเขตสิทธิ์และหน้าจอที่ต่างกันชัดเจน', personas_html, tag='INTERVIEW.md'))

    # Slide 6: Real Field Pain Points
    img_pair(
        'หน้างานจริงมีทั้งมุมกล้องซับซ้อนและช่วงเร่งด่วนที่รูปเข้าพร้อมกันจำนวนมาก',
        STORY_ART['walk'], '**1 · เดินตรวจหน้างาน:** หัวหน้างานถ่ายรูปด้วยมือถือ 100+ รูปต่อไซต์ต่อวัน (ภาพจำลอง)',
        STORY_ART['miss'], '**2 · จุดพลาดที่ยอมรับไม่ได้:** คนงานไม่ใส่หมวกนิรภัยเพียง 1 คนในภาพต้องแจ้งเตือนทันที (ภาพจำลอง)',
        tag='INTERVIEW.md',
    )

    # Slide 7: Interview & Scope
    E.add(E.explain(
        'บทสัมภาษณ์กำหนดเส้นแบ่งชัดเจนว่าอะไรต้องทำในรุ่นแรกและอะไรตัดออกก่อน',
        STORY_ART['interview'],
        [
            '**ต้องมีในรุ่นแรก:** อัปโหลดเป็นชุด, ตรวจจับ `NO_HARDHAT` / `NO_VEST` พร้อมวาดกรอบ, แก้ผลแบบเก็บประวัติลบไม่ได้, รายงานรายวัน และ `/telemetry`',
            '**นอกขอบเขตรุ่นแรก:** แจ้งเตือนผ่าน LINE, การตรวจจับจากกล้องวิดีโอสด และการสร้างบัญชีผู้ใช้ด้วยตนเอง',
            '**จุดยืนด้านความโปร่งใส:** ทุกข้อสมมติถูกระบุชัดในเอกสารเพื่อให้ลูกค้าตรวจสอบก่อนลงมือเขียนโค้ด',
        ],
        post='ภาพจำลอง · รายละเอียดบทสัมภาษณ์ฉบับเต็มอยู่ใน INTERVIEW.md',
    ))

    # ==================== PHASE A: REQUIREMENTS & SYSTEM DESIGN ====================
    E.CTX.update(kicker='ระยะ A · วิเคราะห์โจทย์และออกแบบสถาปัตยกรรม', group='3 · ระยะ A: โจทย์และการออกแบบ')
    E.add(E.divider('ระยะ A', 'วิเคราะห์โจทย์ กติกา 7 ข้อ และสถาปัตยกรรม Design #4',
                    'แปลงบทสัมภาษณ์เป็น User Stories · Requirements · Test Data · System Design · ภาพจำลอง',
                    SLIDE_ART['div_a']))

    # Prompt 1
    add_prompt('A.1', 0, 'พรอมต์ที่ 1 · แปลงบทสัมภาษณ์เป็น docs/USER-STORIES.md')

    # Business Rules Table (Main Table from README)
    E.add(E.tbl(
        'กติกาธุรกิจทั้ง 7 ข้อกระชับ ชัดเจน และรวมศูนย์ไว้ที่ web/lib/rules.ts ไฟล์เดียว',
        E.table('A.1', 'รหัสกติกา'),
        post='การรวมศูนย์กติกาและสวิตช์ BUG_MODE ไว้ที่ไฟล์เดียวทำให้เปลี่ยนเกณฑ์และทดสอบกรณีขอบเขตได้แม่นยำ',
        tag='docs/REQUIREMENTS.md',
    ))

    # Prompt 2
    add_prompt('A.1', 1, 'พรอมต์ที่ 2 · สร้าง docs/REQUIREMENTS.md และ docs/TEST-DATA.md')

    # Engineering First Principles: Why Design #4?
    E.add(E.explain(
        'เหตุผลเชิงวิศวกรรม: โมเดล 19 MB ติดคอขวด CPU/GIL จึงต้องใช้ 4 Processes ต่อ GPU + Micro-batching',
        SLIDE_ART['diag_microbatch'],
        [
            '**ปัญหาแบบ 1 Process ทีละ 1 รูป:** โมเดล YOLO11s ขนาดเพียง 19 MB จึงใช้การ์ดจอแค่ 8% ขณะที่ Python GIL รอถอดรหัสภาพทีละใบ',
            '**ทางออก 1 · 4 Processes ต่อ GPU:** แยก Process อิสระ 4 ตัวต่อการ์ดจอ (รวม 8 ตัวบน `2× RTX 4090`) เพื่อถอดรหัสภาพขนานบน 48 vCPU',
            '**ทางออก 2 · Dynamic Micro-batching:** รวมภาพที่เข้ามาในช่วง `5 ms` สูงสุด `32` รูปส่งเข้า GPU คราวเดียว ลดโอเวอร์เฮดต่อภาพ',
            '**ทางออก 3 · NGINX `least_conn` + Failover ON:** ส่งงานให้ Process ที่ว่างที่สุดและย้ายคำขออัตโนมัติเมื่อ Process ล่ม',
        ],
    ))

    # Full System Architecture Diagram
    E.add(E.fig(
        'สถาปัตยกรรม Design #4: Next.js 15 ส่ง HTTP ขนาน 16 รูปตรงสู่ NGINX + 8× FastAPI บน 2× RTX 4090',
        THEORY_DIAGRAMS['arch'],
        'ฝั่งเว็บเก็บต้นฉบับลง Volume และ PostgreSQL ก่อนตอบรับ 201 แล้ว Async HTTP Dispatcher ส่งตรงไปยัง NGINX โดยไม่ต้องใช้โบรกเกอร์ข้อความภายนอก',
        tag='docs/DESIGN.md',
    ))

    # State Flow & End-to-End Trace
    E.add(E.fig(
        'วงจรสถานะ 4 ค่าของงานตรวจรูป: ปลายทาง DONE และ FAILED เปลี่ยนสถานะซ้ำไม่ได้',
        THEORY_DIAGRAMS['state'],
        'รูปที่ระบบรับแล้วทุกรูปต้องจบที่ DONE หรือ FAILED พร้อมเหตุผลชัดเจน และไม่หายแม้เบราว์เซอร์ปิดหรือ Process ล่มกลางทาง',
        tag='docs/DESIGN.md',
    ))

    E.add(E.fig(
        'ลำดับการไหลของคำขอ End-to-End ตั้งแต่หน้าอัปโหลดจนถึงรายงานประจำวัน',
        THEORY_DIAGRAMS['trace'],
        'NGINX แนบ Header X-Upstream กลับมาพร้อมค่า batch_size, queue_ms (เวลารอรวมชุด) และ model_ms เพื่อบันทึกลง PostgreSQL ทุกรูป',
        tag='docs/DESIGN.md',
    ))

    # Prompt 3
    add_prompt('A.2', 2, 'พรอมต์ที่ 3 · ออกแบบ docs/DESIGN.md สถาปัตยกรรม 2 ฝั่ง')

    # ==================== PHASE B: DAG PLANNING ====================
    E.CTX.update(kicker='ระยะ B · วางแผนการทำงานแบบ DAG', group='4 · ระยะ B: วางแผน DAG')
    E.add(E.divider('ระยะ B', 'วางแผนงานขนาน 10 บล็อกด้วย DAG และเกณฑ์ Review ชัดเจน',
                    'จัดสายวิกฤตและกระจายงานให้ทีม Agent (yolo2 · yolo3 · cyolo1) · ภาพจำลอง',
                    SLIDE_ART['div_b']))

    E.add(E.fig(
        'แผนงาน DAG 10 บล็อก: สายวิกฤตคือ B01 → B02 → B03 → B08 → B10 ทำงานขนานสูงสุด 3 งาน',
        'plan/dag.png',
        'แยกงานฝั่งเว็บ (PostgreSQL, Business Rules, หน้าเว็บ 8 หน้า) ขนานกับฝั่ง AI (NGINX least_conn, 8× FastAPI Micro-batching, Evaluation)',
        tag='plan/PLAN.md',
    ))

    E.add(E.fig(
        'Gantt แผนเวลา: ประมาณการรวม 112.5 นาที และคุมบล็อก B03 (Review) ให้จบภายใน 3 รอบ',
        'plan/gantt-plan.png',
        'กำหนดขอบเขตการตรวจของบล็อก B03 ให้ผ่านทันทีเมื่อกรณีขอบเขตใน docs/TEST-DATA.md ผ่านครบโดยไม่ขยายขอบเขตเกิน Requirement',
        tag='plan/PLAN.md',
    ))

    E.add(E.fig(
        'Gantt เวลาทำงานจริง: เสร็จสมบูรณ์ครบ 10/10 บล็อก ใช้โทเคนรวม 2,499,966 โทเคน',
        'plan/gantt-actual.png',
        'การทำงานขนานช่วยย่นเวลาสร้างจริงลงอย่างชัดเจน และได้ซอร์สโค้ดครบทั้งฝั่งเว็บ Docker Compose และฝั่ง AI บน 2× RTX 4090',
        tag='plan/REPORT.md',
    ))

    # Prompt 4
    add_prompt('ระยะ B', 3, 'พรอมต์ที่ 4 · วางแผนงาน DAG 10 บล็อกใน plan/PLAN.md')

    # ==================== PHASE C: BUILD, MODEL, 2x RTX 4090 & WEB DEMO ====================
    E.CTX.update(kicker='ระยะ C · สร้างระบบ เตรียมโมเดล และวัดผลบน 2× RTX 4090', group='5 · ระยะ C: สร้างและเปิดใช้จริง')
    E.add(E.divider('ระยะ C', 'สร้างแอป เทรนโมเดล YOLO11s และพิสูจน์สมรรถนะบน 2× RTX 4090',
                    'โค้ด 10 บล็อก · ประเมินโมเดล · วัดสมรรถนะ 4 รูปแบบ · ทดสอบ GPU ช้าและ Failover · ภาพจำลอง',
                    SLIDE_ART['div_c']))

    # Prompt 5
    add_prompt('C.1', 4, 'พรอมต์ที่ 5 · สั่งทีม Agent สร้างซอร์สโค้ดครบ 10 บล็อก')

    # Build & Unit Test Verification Summary
    build_html = E.tiles([
        ('Web Unit Tests (Vitest)', '119 / 119', 'ผ่านครบ typecheck, Next.js 15 build และ rules.ts', 'good'),
        ('AI Evaluation Tests', '30 / 30', 'ผ่านครบการตรวจ Recall, Precision และ threshold', 'good'),
        ('Single Source of Truth', '1 ไฟล์', 'อ่าน BUG_MODE และกติกา BR-01..07 ที่ lib/rules.ts ที่เดียว', ''),
    ]) + E.note('ยืนยันสิทธิ์ฐานข้อมูล Append-only (NFR-07): บัญชี runtime sitesafe_app ถูกปฏิเสธ UPDATE และ DELETE บนตาราง result_overrides')
    E.add(E.slide('ซอร์สโค้ดทั้งฝั่งเว็บและฝั่ง AI ผ่าน Build และ Unit Test ครบก่อนเช่าเครื่อง GPU', build_html, tag='code_reference/app/TEST.md'))

    # Prompt 6
    add_prompt('C.2', 5, 'พรอมต์ที่ 6 · เช่าเครื่อง 2× RTX 4090 และวัดความแม่นยำโมเดล YOLO11s')

    # Vast.ai RUNNING Console Card (NO PRICES!)
    running_console = """
<div class="console-box">
  <div class="console-hdr">
    <strong>Vast.ai Cloud Console · 1 โหนด × 2× RTX 4090 (label: e2e-sitesafe-nginx)</strong>
    <span class="status-run">● RUNNING</span>
  </div>
  <div>Instance ID : 62729107 &nbsp;·&nbsp; Location : Illinois, US &nbsp;·&nbsp; Verification : verified</div>
  <div>Hardware    : 2× NVIDIA GeForce RTX 4090 (24 GB VRAM × 2) · 48 vCPU · 125.6 GB RAM · 60 GB Disk</div>
  <div>Image       : pytorch/pytorch:2.4.1-cuda12.4-cudnn9-runtime · Open Port : 8080/tcp</div>
  <div>Loaded      : /workspace/lab6/best.pt (19.2 MB) · server.py · nginx.conf · cluster.sh</div>
  <div style="margin-top:10px;color:#4ADE80;">[cluster] READY in 36s: nginx :8080 -&gt; 8 server(s) [8101..8104, 8201..8204] mode=micro lb=lc failover=on</div>
  <div style="color:#38BDF8;">GET /lb/health -&gt; 200 {"status":"ok","service":"nginx"} &nbsp;|&nbsp; GET /health -&gt; 200 {"status":"ready","mode":"micro","max_batch":32}</div>
</div>
""" + E.note('คั่นจังหวะชัดเจนระหว่างขั้นสร้างเครื่อง GPU กับขั้นรันโมเดลและวัดผล · ยืนยันว่าทั้ง 8 Processes และ NGINX พร้อมรับงานจริง')
    E.add(E.slide('สถานะเครื่อง Vast.ai พร้อมใช้งาน (RUNNING): 8 Processes + NGINX เปิดพอร์ต 8080 ครบ', running_console, tag='Vast.ai Console · 2× RTX 4090'))

    # Dataset & Training Results
    E.add(E.fig(
        'ตัวอย่างภาพชุดข้อมูล PPE ที่ใช้เทรนและทดสอบโมเดล YOLO11s',
        'results/dataset_samples.jpg',
        'ครอบคลุมมุมกล้องหน้างานก่อสร้างหลากหลายระยะ ทั้งคนงานสวมอุปกรณ์ครบและไม่สวมหมวก/เสื้อสะท้อนแสง',
        tag='results/dataset_samples.jpg',
    ))

    E.add(E.fig(
        'กราฟผลการเทรน YOLO11s ครบ 30 Epochs (534.7 วินาที): Loss ลดลงสม่ำเสมอและ mAP สูงขึ้นต่อเนื่อง',
        'results/model/results.png',
        'น้ำหนักโมเดลที่บันทึกไว้ (results/model/best.pt ขนาด 19.2 MB) ถูกนำไปใช้งานจริงบนทั้ง 8 Processes ของ 2× RTX 4090',
        tag='results/model/train_time.json',
    ))

    E.add(E.tbl(
        'ผลประเมินโมเดล YOLO11s ที่ threshold 0.32: ค่าที่วัดได้ถึงเกณฑ์ ≥ 0.80 ครบทั้ง 2 คลาส',
        E.table('C.2', 'รุ่นโมเดล'),
        post='ความโปร่งใส: ชุดทดสอบสาธารณะมีภาพกลุ่มบวก 25 รูป (ต่ำกว่าเกณฑ์กลุ่มละ 100 รูปของ NFR-01) จึงแจ้งลูกค้าให้เก็บภาพหน้างานจริงเพิ่มเพื่อยืนยันซ้ำ',
        tag='results/model/metrics_after.json',
    ))

    E.add(E.fig(
        'ตัวอย่างกรอบทำนายจริงของโมเดล ppe-yolo-v1 (best.pt) บนภาพชุดทดสอบ',
        'results/model/examples_test_predictions.jpg',
        'โมเดลตีกรอบแยกคนงานที่สวมอุปกรณ์และไม่สวมอุปกรณ์ (NO-Hardhat, NO-Safety Vest) ได้แม่นยำพร้อมคะแนนความมั่นใจ',
        tag='results/model/examples_test_predictions.jpg',
    ))

    # Prompt 7
    add_prompt('C.3', 6, 'พรอมต์ที่ 7 · วัดสมรรถนะ 4 รูปแบบ, ทดสอบ GPU ช้า & Failover และเปิด Design #4')

    # Benchmark Results (Table + 4 Charts)
    E.add(E.tbl(
        'ผลวัดจริงบน 1 โหนด × 2× RTX 4090: Design #4 รองรับ 88 ผู้ใช้พร้อมกัน (8.0×) และ 444.55 คำขอต่อวินาที',
        E.table('C.3', 'รูปแบบสถาปัตยกรรม'),
        post='ทุกการวัดใช้เกณฑ์เดียวกันคือความหน่วง p95 ไม่เกิน 500 มิลลิวินาที · Design #4 ใช้ทั้ง GPU 0 (54%) และ GPU 1 (49%) อย่างสมดุล',
        tag='results/lb/summary.json',
    ))

    E.add(E.fig(
        'เทียบความจุ 4 รูปแบบ: จาก 11 → 32 → 64 → 88 ผู้ใช้พร้อมกัน (เพิ่มขึ้น 8.0 เท่า)',
        'images/lab/01_capacity_4designs.png',
        'ดูการกระโดดของความจุทุกขั้น: Micro-batching (2.9×) → เพิ่มเป็น 4 Processes/GPU (5.8×) → ขยาย 2× RTX 4090 + NGINX least_conn (8.0×)',
        tag='results/lb/summary.json',
    ))

    E.add(E.fig(
        'เส้นโค้งความหน่วงและปริมาณงาน: Design #4 คง p95 ต่ำกว่า 500 ms ได้จนถึง 88 ผู้ใช้พร้อมกัน',
        'images/lab/04_latency_throughput_curves.png',
        'เมื่อเพิ่มจำนวนผู้ใช้พร้อมกัน Design #4 ทำปริมาณงานได้สูงสุด 444.55 คำขอต่อวินาทีโดยความหน่วงยังผ่านเกณฑ์ SLO',
        tag='results/lb/gpu2_lc.json',
    ))

    E.add(E.fig(
        'เมื่อ GPU 1 ช้าลง 3 เท่า: NGINX least_conn รักษาความจุได้ 76 ผู้ใช้ สูงกว่า Round Robin +76.7%',
        'images/lab/02_rr_vs_lc_slow.png',
        'Round Robin แจกงาน 50%/50% ทำให้ค้างที่การ์ดจอช้า (43 ผู้ใช้) ส่วน least_conn โยกโหลดไป GPU 0 ทันทีเป็น 68%/32% (76 ผู้ใช้)',
        tag='results/lb/lc_slow.json · rr_slow.json',
    ))

    E.add(E.fig(
        'เมื่อปิด GPU 1 กะทันหันกลางโหลด 80 ผู้ใช้: Failover ON ลดความผิดพลาดจาก 67.18% เหลือ 0.00%',
        'images/lab/03_failover_comparison.png',
        'Failover OFF เกิด 502 จำนวน 14,098 คำขอ (67.18%) ขณะที่ Failover ON ใช้ proxy_next_upstream ย้ายไป GPU 0 ได้ครบโดยผิดพลาด 0 คำขอ',
        tag='results/lb/fail_on.json · fail_off.json',
    ))

    # Dedicated Web Demo Login Accounts Table Slide (User Requirement!)
    E.add(E.tbl(
        'บัญชีทดลองใช้งานหน้าเว็บ (Demo Login Accounts): ทดลองสลับครบทั้ง 3 บทบาทได้ทันที',
        E.table('C.4', 'บทบาท (Role)'),
        post='รหัสผ่านทั้งหมดเก็บด้วย argon2id ใน PostgreSQL · หลังเปิดเว็บที่ http://localhost:3410 สามารถล็อกอินด้วยบัญชีเหล่านี้เพื่อทดสอบสิทธิ์ได้ทันที',
        tag='docs/TEST-DATA.md',
    ))

    # Web Demo GIF #1 (Starts right from /login!)
    E.add(E.fig(
        'เดโมใช้งานจริง 1: เริ่มจากหน้า /login → อัปโหลด 6 รูป → กรอบ PPE บน 2× RTX 4090 → รายงาน',
        'images/lab/sitesafe_e2e_flow.gif',
        'แสดงการพิมพ์อีเมลและรหัสผ่านจริงบนหน้า /login, อัปโหลดภาพหน้างานจริง, แสดงกรอบตรวจจับพร้อมป้าย GPU/model_ms และเปิดรายงานประจำวัน',
        tag='Live 2× RTX 4090 Demo GIF',
    ))

    # Web Demo GIF #2 (20-photo batch + Telemetry!)
    E.add(E.fig(
        'เดโมใช้งานจริง 2: อัปโหลด 20 รูปพร้อมกัน → หน้ารูปมีปัญหา → รายงาน <90% แดง → /telemetry',
        'images/lab/sitesafe_lb_telemetry.gif',
        'สลับบทบาทจากหัวหน้างานเป็นผู้จัดการความปลอดภัย ตรวจหน้ารูปมีปัญหา รายงานไซต์ ก สีแดง (89.67%) และแดชบอร์ด /telemetry สถานะ ONLINE',
        tag='Live 2× RTX 4090 Demo GIF',
    ))

    # Live Web Screenshots (2 clean pairs)
    img_pair(
        'หน้าจอใช้งานจริงฝั่งหัวหน้างาน: หน้าอัปโหลดผูกไซต์อัตโนมัติ และหน้าดูกรอบ PPE พร้อม GPU Telemetry',
        'images/lab/web-home.png', '**หน้า `/upload`:** ผูก `SITE-A` อัตโนมัติ ไม่มีช่องเลือกไซต์อื่น',
        'images/lab/web-detect-boxes.png', '**หน้า `/photos/[id]`:** วาดกรอบ PPE ทับภาพต้นฉบับพร้อม `X-Upstream` และ `model_ms`',
        tag='Live Web UI',
    )

    img_pair(
        'หน้าจอใช้งานจริงฝั่งผู้จัดการและผู้บริหาร: รายงานเส้นแบ่ง 90% และแดชบอร์ด /telemetry',
        'images/lab/web-report-daily.png', '**หน้า `/reports/daily`:** SITE-A `89.67%` ขึ้นสีแดง · SITE-B `90.00%` ปกติ',
        'images/lab/web-telemetry.png', '**หน้า `/telemetry`:** แสดงสถานะ Upstream `ONLINE` และสัดส่วนการกระจายงาน 2× RTX 4090',
        tag='Live Web UI',
    )

    # ==================== PHASE D: PLAYWRIGHT 27 TCs + GIFs + BUG HUNT + DESTROY ====================
    E.CTX.update(kicker='ระยะ D · ทดสอบอัตโนมัติ Playwright 27 ข้อและ Bug Hunt', group='6 · ระยะ D: ทดสอบและส่งมอบ')
    E.add(E.divider('ระยะ D', 'ทดสอบอัตโนมัติ Playwright 27 ข้อพร้อม `.gif` ทุกข้อ และ Bug Hunt 3/3',
                    'พิสูจน์ทุกกติกาบน 2× RTX 4090 จริง · จับบักซ่อนครบ 3/3 · ลบเครื่อง GPU ทันที · ภาพจำลอง',
                    SLIDE_ART['div_d']))

    # Prompt 8
    add_prompt('D.1', 7, 'พรอมต์ที่ 8 · รัน Playwright 24 Core Test Cases พร้อมบันทึก .gif ทุกข้อ')

    # Verification Overview KPIs
    ver_html = E.tiles([
        ('Core Test Cases ผ่าน 100%', '24 / 24', 'ทดสอบจริงบน 2× RTX 4090 (22 ข้อ) + Mock (2 ข้อ)', 'good'),
        ('Bug Hunt จับบักครบ 100%', '3 / 3', 'พิสูจน์ในโหมด BUG_MODE=1 แล้วคืนค่า BUG_MODE=0', 'good'),
        ('p95 ชุด 20 รูปจริง (TC-16)', '2.23 วิ', 'เร็วกว่าเกณฑ์ 30 วิ ถึง 13.5× · กระจาย gpu0=7, gpu1=13', ''),
    ]) + E.note('ทุก Test Case ทั้ง 27 ข้อมีไฟล์วิดีโอ .gif ของตัวเองใน images/tests/TC-01.gif ถึง TC-27.gif และเปิดกรองดูได้ใน test/index.html')
    E.add(E.slide('สรุปผลทดสอบ Playwright: ผ่านครบ 24/24 ข้อ จับบัก Bug Hunt ครบ 3/3 และบันทึก .gif ครบ 27 ไฟล์', ver_html, tag='test/TEST-REPORT.md'))

    # Complete Playwright Test Case Table split cleanly across 2 slides (12 rows each)
    def tc_table_slide(title, subset, tag):
        rows_md = [['TC ID', 'ชื่อ Test Case', 'กติกา', 'โหมด', 'ผลจริง', 'สถานะ']]
        for tc in subset:
            st = '✓ ผ่าน' if tc['status'] == 'PASS' else '✗ จับบักได้'
            rows_md.append([f"**{tc['id']}**", tc['name'], f"`{tc['rule']}`", tc['mode'], tc['actual'], st])
        tbl_html = '<div class="compact-tbl">' + E.table_html({'t': 'table', 'head': rows_md[0], 'rows': rows_md[1:]}) + '</div>'
        E.add(E.slide(title, tbl_html, tag=tag))

    tc_table_slide('ตารางผลทดสอบ Playwright (ชุดที่ 1 · TC-01 ถึง TC-12): Upload, Rules และ Live YOLO11s', E2E[:12], 'test/evidence/e2e_results.json')
    tc_table_slide('ตารางผลทดสอบ Playwright (ชุดที่ 2 · TC-13 ถึง TC-24): Reliability, 2× GPU LB, Reports และ RBAC', E2E[12:24], 'test/evidence/e2e_results.json')

    # 6 Rich Per-TC GIF Showcase Slides (Core TCs)
    gif_grid(
        'หลักฐาน GIF กลุ่ม A · การรับไฟล์และตรวจขอบเขต (BR-05, FR-02, BR-06)',
        [
            ('images/tests/TC-01.gif', 'TC-01 · รับ 14.9 & 15.0 MB พอดี', 'HTTP 201 ทั้งสองไฟล์ (BR-05)'),
            ('images/tests/TC-02.gif', 'TC-02 · ปฏิเสธ 15 MB + 1 B', 'HTTP 413 พร้อมข้อความ 15 MB'),
            ('images/tests/TC-04.gif', 'TC-04 · ปฏิเสธ GIF/PDF/fake.jpg', 'HTTP 415 ตรวจจาก Magic Bytes'),
            ('images/tests/TC-05.gif', 'TC-05 · ขอบเขต 0 / 50 / 51 รูป', '422 · 201 · 422 ตรงตาม BR-06'),
        ],
        cols=2,
        tag='TC-01 · TC-02 · TC-04 · TC-05',
        post='คลิกที่วิดีโอ GIF ใดก็ได้เพื่อขยายเต็มจอ · ดูครบทุกข้อที่ test/index.html',
    )

    gif_grid(
        'หลักฐาน GIF กลุ่ม B · ตารางตัดสิน BR-01..03 และ YOLO11s จริงบน 2× RTX 4090',
        [
            ('images/tests/TC-07.gif', 'TC-07 · Decision Table 8/8', 'ครบ R-1..R-8 รวม H=0, V=2 → FAIL'),
            ('images/tests/TC-08.gif', 'TC-08 · กรอบ Bounding Boxes', 'h1_v1.jpg วาดครบ 2 กรอบ SVG'),
            ('images/tests/TC-09.gif', 'TC-09 · Live 2× RTX 4090 (6 รูป)', '6/6 DONE · gpu0-8103 · 26.38 ms'),
        ],
        cols=3,
        tag='TC-07 · TC-08 · TC-09',
        post='ยืนยันทั้งกติกาเชิงขอบเขตแบบกำหนดค่าได้ (Mock) และผลตรวจภาพหน้างานจริงด้วย YOLO11s บน 2× RTX 4090',
    )

    gif_grid(
        'หลักฐาน GIF กลุ่ม C · ความทนทาน รูปห้ามหาย และการกระจายงานข้าม 2× RTX 4090',
        [
            ('images/tests/TC-13.gif', 'TC-13 · ปิดเบราว์เซอร์กลางทาง', 'เปิดกลับมาตรวจจบครบ 10/10 รูป'),
            ('images/tests/TC-14.gif', 'TC-14 · ไฟล์ใหญ่ 14.9 & 15.0 MB', 'ผ่าน NGINX 20 MB จบ 2/2 ใน 2.5 วิ'),
            ('images/tests/TC-15.gif', 'TC-15 · ไฟล์เสีย corrupt_half.jpg', 'จบ FAILED โดยไม่ขวางภาพปกติ 2/2'),
            ('images/tests/TC-16.gif', 'TC-16 · ชุด 20 รูปพร้อมกัน', '20/20 ใน 2.69 วิ · p95=2.23 วิ · gpu0=7, gpu1=13'),
        ],
        cols=2,
        tag='TC-13 · TC-14 · TC-15 · TC-16',
        post='TC-16 พิสูจน์จริงว่า NGINX least_conn กระจายโหลดข้ามทั้ง GPU 0 และ GPU 1 พร้อมทำความเร็วเร็วกว่าเกณฑ์ 30 วินาทีถึง 13.5 เท่า',
    )

    gif_grid(
        'หลักฐาน GIF กลุ่ม D1 · เส้นแบ่งรายงาน 90.00% และป้ายเวลาความพร้อม 18:00 น.',
        [
            ('images/tests/TC-18.gif', 'TC-18 · เส้นแบ่งสีแดง BR-04', '89.67% แดง · 90.00% และ 90.33% ปกติ'),
            ('images/tests/TC-19.gif', 'TC-19 · ขอบเขตพิเศษวันที่ 2', 'ไม่มีข้อมูล / 9÷10=90% / ตัด FAILED ออก'),
            ('images/tests/TC-20.gif', 'TC-20 · เวลาความพร้อม BR-07', '17:59 น. ระหว่างวัน → 18:00 น. พร้อมแล้ว'),
        ],
        cols=3,
        tag='TC-18 · TC-19 · TC-20',
    )

    gif_grid(
        'หลักฐาน GIF กลุ่ม D2 · หน้ารูปมีปัญหา การแก้ผลพร้อม Audit Trail และการเลื่อนวัน',
        [
            ('images/tests/TC-10.gif', 'TC-10 · หน้า /photos/problems', 'แสดงเฉพาะ FAIL 20 + WARN 11 = 31 รูป'),
            ('images/tests/TC-21.gif', 'TC-21 · แก้ผล FAIL → PASS', 'ไซต์ ก เปลี่ยนจาก 89.67% แดงเป็น 90.00% ปกติ'),
            ('images/tests/TC-22.gif', 'TC-22 · ปฏิเสธเหตุผลว่าง + Audit', 'เหตุผลว่าง 422 · มีเหตุผล 201 · เลื่อนวันได้'),
        ],
        cols=3,
        tag='TC-10 · TC-21 · TC-22',
    )

    gif_grid(
        'หลักฐาน GIF กลุ่ม E · การแยกสิทธิ์ RBAC 3 บทบาท และแดชบอร์ด /telemetry ปลอด API Key',
        [
            ('images/tests/TC-23.gif', 'TC-23 · RBAC 3 บทบาท (401/403/404)', 'ไม่ล็อกอิน→401 · ข้ามไซต์→404 · Manager/Exec→403'),
            ('images/tests/TC-24.gif', 'TC-24 · /telemetry ONLINE + Security', 'แสดงสถานะ ONLINE (gpu0-8103) · 0 API Key รั่วไหล'),
        ],
        cols=2,
        tag='TC-23 · TC-24',
        post='ทุกบทบาทเข้าดู /telemetry ได้ แต่ไม่มีการส่งผ่าน API Key ไปยังฝั่งเบราว์เซอร์หรือ HTML เลยแม้แต่ตัวเดียว',
    )

    # Bug Hunt Section
    E.add(E.explain(
        'Bug Hunt (BUG_MODE=1): พิสูจน์ว่าชุดทดสอบจับบักที่ซ่อนอยู่ในกติกาได้จริงครบ 3/3',
        SLIDE_ART['diag_bughunt'],
        [
            '**เปิดโหมด `BUG_MODE=1`:** สวิตช์ที่อ่านเฉพาะใน `web/lib/rules.ts` ทำให้กติกา 3 ข้อ (`BR-02`, `BR-04`, `BR-06`) ทำงานผิดที่จุดขอบเขต',
            '**รัน Playwright ตรวจซ้ำ (`TC-25`–`TC-27`):** ชุดทดสอบต้องตรวจพบความผิดพลาดครบทั้ง 3 ข้อ ไม่ใช่ปล่อยผ่านไปเงียบ ๆ',
            '**คืนค่า `BUG_MODE=0` ทันที:** หลังเก็บหลักฐาน `.gif` และภาพหน้าจอครบจึงปิดโหมดบักกลับสู่สถานะปกติ',
        ],
    ))

    # Prompt 9
    add_prompt('D.2', 8, 'พรอมต์ที่ 9 · รัน Bug Hunt (TC-25..TC-27) ในโหมด BUG_MODE=1')

    # Bug Hunt 3-GIF Showcase
    gif_grid(
        'หลักฐาน GIF Bug Hunt (BUG_MODE=1): จับบักซ่อนได้ครบทั้ง 3 กติกา (3/3 · 100%)',
        [
            ('images/tests/TC-25.gif', 'TC-25 · จับบัก #1 (BR-02)', 'h0_v2.jpg ตอบ WARN แทน FAIL'),
            ('images/tests/TC-26.gif', 'TC-26 · จับบัก #2 (BR-04)', 'SITE-B 90.00% พอดีถูกไฮไลต์สีแดง'),
            ('images/tests/TC-27.gif', 'TC-27 · จับบัก #3 (BR-06)', 'ส่งชุด 51 รูปตอบ 201 แทน 422'),
        ],
        cols=3,
        tag='TC-25 · TC-26 · TC-27 (BUG_MODE=1)',
        post='ยืนยันคุณภาพของชุดทดสอบ: เมื่อโค้ดผิดเงื่อนไขเพียง 1 เครื่องหมาย (> แทน ≥ หรือ ≤ แทน <) Playwright จับได้ทันทีทุกข้อ',
    )

    E.add(E.fig(
        'ภาพหน้าจอหลักฐาน Bug #2 (BR-04): เมื่อ BUG_MODE=1 ไซต์ ข ที่ได้ 90.00% พอดีกลายเป็นสีแดงผิดกติกา',
        'images/lab/web-bug-9000.png',
        'เปรียบเทียบกับภาพปกติ (BUG_MODE=0) ที่ SITE-B 90.00% ต้องไม่แดง · การทดสอบจุดขอบเขต 90.00% พอดีช่วยจับบักลักษณะนี้ได้ทันที',
        tag='test/BUG-HUNT.md',
    ))

    # Prompt 10 (Destroy GPU & Delivery)
    add_prompt('D.3', 9, 'พรอมต์ที่ 10 · ลบเครื่อง GPU บน Vast.ai และออกเอกสารส่งมอบงาน')

    # Vast.ai DESTROYED Console Card (NO PRICES!)
    destroyed_console = """
<div class="console-box destroyed">
  <div class="console-hdr">
    <strong>Vast.ai Cloud Console · คืนทรัพยากรหลังจบการทดสอบ (label: e2e-sitesafe-nginx)</strong>
    <span class="status-del">● DESTROYED (0 REMAINING)</span>
  </div>
  <div>$ vastai destroy instance 62729107 -y</div>
  <div style="color:#4ADE80;">destroying instance 62729107.</div>
  <div style="margin-top:8px;">$ vastai show instances --filter label=e2e-sitesafe-nginx</div>
  <div style="color:#38BDF8;">Total: 0 instances (e2e-sitesafe-nginx)</div>
  <div style="margin-top:8px;">$ docker compose -p sitesafe-nginx down -v &amp;&amp; docker compose -p sitesafe-mock down -v</div>
  <div style="color:#4ADE80;">All local test containers, volumes, and temporary keys removed cleanly.</div>
</div>
""" + E.note('วินัยสำคัญของงาน GPU บนคลาวด์: ลบเครื่องทันทีหลังบันทึกหลักฐานครบทุกไฟล์ และตรวจยืนยันด้วย vastai show instances เสมอ')
    E.add(E.slide('ยืนยันลบเครื่อง Vast.ai (DESTROYED): เหลือ 0 เครื่องและปิดคอนเทนเนอร์ทดสอบครบถ้วน', destroyed_console, tag='Vast.ai Cleanup Verified'))

    # ==================== SUMMARY & DELIVERY ====================
    E.CTX.update(kicker='สรุปและส่งมอบงาน', group='7 · สรุปและส่งมอบ')

    # Delivery Verdict
    verdict_html = E.tiles([
        ('คำตัดสินส่งมอบงาน', 'พร้อมส่งมอบ', 'ผ่านครบทั้ง 4 ระยะ · 24/24 Core + 3/3 Bug Hunt', 'good'),
        ('ความจุ Design #4 จริง', '88 ผู้ใช้', '444.55 คำขอต่อวินาที · Failover Error 0.00%', 'good'),
        ('ข้อสังเกตโปร่งใส Test Set', '82 รูป', 'ค่าที่วัดได้ ≥ 0.80 ทุกคลาส · แนะนำเก็บภาพจริงเพิ่มให้ครบ 100/กลุ่ม', ''),
    ]) + E.note('การส่งมอบงานวิศวกรรมที่ดีไม่ได้ซ่อนข้อจำกัด: เราแจ้งลูกค้าชัดเจนเรื่องขนาด Test Set สาธารณะ 82 รูปควบคู่กับผลวัดจริงทั้งหมดใน DELIVERY.md')
    E.add(E.slide('คำตัดสินส่งมอบงาน: พร้อมส่งมอบพร้อมหลักฐานจริงและข้อสังเกตโปร่งใสครบถ้วน', verdict_html, tag='DELIVERY.md'))

    # Key Engineering Takeaways (editorial numbered list, zero AI cards)
    lessons_html = """
<ul class="step-list">
  <li><div class="step-num">01</div><div><strong>เริ่มจากกติกาและกรณีขอบเขตก่อนเขียนโค้ด:</strong> การเขียน <code>docs/TEST-DATA.md</code> ล่วงหน้าและรวมกติกาไว้ที่ <code>web/lib/rules.ts</code> ไฟล์เดียวทำให้การตรวจและแก้บักแม่นยำ</div></li>
  <li><div class="step-num">02</div><div><strong>แก้คอขวดให้ตรงจุดด้วย Design #4:</strong> โมเดลขนาดเล็ก (19 MB) ติดคอขวด CPU/GIL การใช้ 4 Processes ต่อ GPU + Micro-batching + NGINX <code>least_conn</code> เพิ่มความจุได้ 8.0 เท่าโดยไม่ต้องเพิ่มโบรกเกอร์ซับซ้อน</div></li>
  <li><div class="step-num">03</div><div><strong>วัดความทนทานด้วยสถานการณ์เสียจริง:</strong> ทดสอบทั้ง GPU ช้าลง 3 เท่า (<code>least_conn</code> ชนะ +76.7%) และปิด GPU 1 กะทันหัน (<code>Failover ON</code> ผิดพลาด 0.00%)</div></li>
  <li><div class="step-num">04</div><div><strong>พิสูจน์คุณภาพชุดทดสอบด้วย Bug Hunt:</strong> ชุดทดสอบที่ดีต้องทั้งผ่าน 24/24 เมื่อโค้ดถูก และจับบักได้ 3/3 เมื่อเปิด <code>BUG_MODE=1</code> พร้อมวิดีโอ <code>.gif</code> หลักฐานทุกข้อ</div></li>
</ul>
"""
    E.add(E.slide('บทเรียนวิศวกรรม 4 ข้อจากการสร้าง SiteSafe Inspect ตั้งแต่โจทย์จนถึงส่งมอบ', lessons_html, tag='Key Takeaways'))

    # Closing Divider
    E.add(E.divider(
        'จบการนำเสนอ',
        'SiteSafe Inspect พร้อมใช้งานและตรวจสอบย้อนกลับได้ทุกตัวเลข',
        'คู่มือฉบับเต็ม: README.md · ดูวิดีโอทดสอบทั้ง 27 ข้อ: test/index.html · รวมพรอมต์: PROMPTS.md · คำตัดสินส่งมอบ: DELIVERY.md · ภาพจำลอง',
        SLIDE_ART['div_summary'],
    ))

    out_path = 'SiteSafe_Inspect_Slides.html'
    E.write(E.SL, out_path, 'SiteSafe Inspect · 2× RTX 4090 · NGINX least_conn + 8× FastAPI Micro-batching')

    # Inject our clean extra editorial CSS right before </head>
    raw = open(out_path, encoding='utf-8').read()
    raw = raw.replace('</head>', EXTRA_CSS + '\n</head>', 1)
    open(out_path, 'w', encoding='utf-8').write(raw)
    print(f'BUILT {out_path}: {len(E.SL)} slides')

if __name__ == '__main__':
    build()
