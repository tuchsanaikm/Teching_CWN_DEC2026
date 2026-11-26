#!/usr/bin/env python3
"""สร้างสไลด์ LAB4_MultiGPU_Slides.html ของ LAB 4 (Multi-GPU ในเครื่องเดียว: Single GPU · Data Parallelism · Model Parallelism)

  python tools/build_slides.py            (รันจากโฟลเดอร์ lab4_multigpu)

LAB 4 มี 4 README (หน้ารวม · 1_single_gpu · 2_data_parallel · 3_model_parallel)
ลำดับการนำเสนอ:
  1. เริ่มต้น: ปก · แผนที่เส้นทาง · แผนที่โฟลเดอร์ (3 LAB ย่อย · 1 เครื่อง) · ตารางจำนวนเครื่อง vs GPU ในเครื่อง · ตัวแปรควบคุม
  2. พื้นฐานร่วม: Dataset sql-create-context · โมเดล Qwen3-8B · Attention Q/K/V · LoRA
  3. LAB 4.1 · Single GPU (`1_single_gpu/`, 1 เครื่อง × 1 ใบ · 3 ขั้น): สร้างเครื่อง (Vast.ai READY) → เทรน (ผลหลังเทรนเสร็จ) → กราฟ & บทเรียน → ลบเครื่อง
  4. LAB 4.2 · Data Parallelism (`2_data_parallel/` และ `gpu4/`, 1 เครื่อง × 2 และ 4 ใบ · 6 ขั้น): สร้างเครื่อง → เทรน → ผลหลังเทรนเสร็จ → กราฟ → ลบเครื่อง (ทั้ง 2 และ 4 ใบ)
  5. LAB 4.3 · Model Parallelism (`3_model_parallel/` และ `gpu4/`, 1 เครื่อง × 2 และ 4 ใบ · 6 ขั้น): สร้างเครื่อง → เทรน → ผลหลังเทรนเสร็จ → กราฟ → ลบเครื่อง (ทั้ง 2 และ 4 ใบ)
  6. บทสรุปทั้ง 3 แล็บ: เทียบผล 5 กรณี (ความเร็ว / VRAM & Batch / คุณภาพ) · แนวทางเลือกใช้ · ข้อจำกัด · จบ LAB 4

ข้อกำหนด:
- ทั้งเด็คอยู่ในกรอบ 80–100 หน้า (99 หน้า)
- ใช้คำเต็มตลอดทั้งเด็ค (Data Parallelism · Model Parallelism · Out of Memory · GPU utilization · ตัวอย่างต่อวินาที)
- มีหน้าคั่นแสดงสถานะเครื่อง Vast.ai พร้อมใช้งาน (RUNNING) หลังพรอมต์เช่าเครื่อง และหน้าค่าผลลัพธ์จริงหลังพรอมต์เทรนครบทุก 5 รอบ
- ไม่แสดงราคา ค่าเช่า หรือยอดที่ถูกคิดของเครื่องในหน้าผลและหน้าสรุป (พรอมต์คัดลอกตรงตัวอักษรจาก README)
- ตัวเลขผลทุกตัวอ่านจาก README และไฟล์ results/summary.json ของทั้ง 5 รอบตอนสร้างไฟล์
"""
import json, os, posixpath, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import slides_engine as E
from slides_engine import md, CTX, add, note, fig, explain, tbl, plain
from slides_figures import FIGS

S = E.slide
FIG = {f["img"]: f for f in FIGS}
OUT, TITLE = "LAB4_MultiGPU_Slides.html", "LAB 4 · Multi-GPU ในเครื่องเดียว (Single GPU · Data Parallelism · Model Parallelism)"

P1, P2, P3 = "1_single_gpu/", "2_data_parallel/", "3_model_parallel/"
IMG_S, IMG_1, IMG_2, IMG_3, IMG_SL = (
    "images/shared/",
    "images/single_gpu/",
    "images/data_parallel/",
    "images/model_parallel/",
    "images/slides/",
)

# ------------------------------------------------------------------ layout เพิ่มของเด็คนี้ (ไม่แก้ engine)
E.CSS += r"""
.ex.big .fig{flex:2.25 1 0}
.ex.mid2 .fig{flex:1.95 1 0}
.slide.stmt{padding:0;color:#fff}
.stmt img.bg{position:absolute;inset:0;width:100%;height:100%;object-fit:cover}
.stmt .shade{position:absolute;inset:0;background:linear-gradient(90deg,rgba(6,13,26,.95) 0%,rgba(6,13,26,.82) 52%,rgba(6,13,26,.18) 88%)}
.stmt .inner{justify-content:center;max-width:1060px}
.stmt .q{font-size:50px;font-weight:700;line-height:1.32;color:#fff}
.stmt .sub2{margin-top:28px;font-size:25px;line-height:1.6;color:#d6e4fb}
.stmt .sub2 b{color:#ffd28a}
.stmt .links{margin-top:26px;font-size:21px;line-height:1.7;color:#b9d2f5}
.stmt .links a{color:#8fe0dc;border-bottom-color:rgba(143,224,220,.45);margin-right:18px;white-space:nowrap}
.stmt .imgnote{bottom:60px}
.inner .dim{color:#9fb6dd;font-size:.9em}
.divider .inner .small{margin-bottom:22px}
.inner h1{line-height:1.32}
.slide.hero .tag{color:#ffd28a;text-shadow:0 1px 6px rgba(0,0,0,.95),0 0 3px #000}
.slide.hero code{background:rgba(255,255,255,.16);color:#fff}
.slide.hero .tiles.hl .num{font-size:2.15em}
.slide th a{color:#fff}

/* Vast.ai Web Console Status Mockup (ช่วงสร้างเครื่องเสร็จพร้อมเทรน) */
.vweb{background:#0f172a;color:#e2e8f0;border-radius:14px;overflow:hidden;border:1px solid #1e293b;margin-top:6px;box-shadow:0 10px 28px rgba(15,23,42,.18)}
.vweb-bar{display:flex;align-items:center;justify-content:space-between;background:#1e293b;padding:11px 20px;border-bottom:1px solid #334155;font-family:ui-monospace,Consolas,monospace;font-size:.82em;color:#94a3b8}
.vweb-dots{display:flex;gap:7px;align-items:center}
.vweb-dot{width:11px;height:11px;border-radius:50%;display:inline-block}
.vweb-url{background:#0f172a;padding:4px 16px;border-radius:6px;color:#cbd5e1;border:1px solid #334155}
.vweb-status{display:inline-flex;align-items:center;gap:7px;background:rgba(16,185,129,.18);color:#34d399;border:1px solid rgba(52,211,153,.45);padding:3px 13px;border-radius:999px;font-weight:700;font-size:.86em}
.vweb-body{padding:20px 26px}
.vweb-head{display:flex;align-items:center;justify-content:space-between;gap:16px;padding-bottom:14px;border-bottom:1px solid #334155;margin-bottom:16px;flex-wrap:wrap}
.vweb-gpu{font-size:1.35em;font-weight:700;color:#38bdf8}
.vweb-lbl{font-family:ui-monospace,Consolas,monospace;background:#1e293b;color:#fde68a;padding:4px 12px;border-radius:6px;border:1px solid #475569;font-size:.88em}
.vweb-grid{display:grid;grid-template-columns:1.15fr 1fr;gap:22px}
.vweb-kv{display:grid;grid-template-columns:auto 1fr;gap:8px 18px;font-size:.9em;line-height:1.45}
.vweb-k{color:#94a3b8;font-weight:600;white-space:nowrap}
.vweb-v{color:#f8fafc}
.vweb-chk{border-left:1px solid #334155;padding-left:22px;display:flex;flex-direction:column;gap:10px;justify-content:center}
.vweb-chkh{color:#94a3b8;font-size:.82em;font-weight:700;letter-spacing:.03em;text-transform:uppercase}
.vweb-item{display:flex;gap:10px;align-items:flex-start;font-size:.9em;line-height:1.45;color:#e2e8f0}
.vweb-ok{color:#34d399;font-weight:700;flex-shrink:0}
.vweb-next{margin-top:4px;padding-top:10px;border-top:1px dashed #334155;color:#7dd3fc;font-weight:700;font-size:.92em}
.vweb b{color:#7dd3fc}
.vweb .vweb-next b{color:#fde68a}
.vweb code{background:#1e293b;color:#fde68a;border:1px solid #334155}

/* Training Completion Readout (ช่วงหลังเทรนเสร็จ 3 Epoch) */
.tdone{background:#0b1220;color:#e2e8f0;border-radius:14px;overflow:hidden;border:1px solid #1e293b;margin-top:6px;box-shadow:0 10px 28px rgba(15,23,42,.16)}
.tdone-bar{display:flex;align-items:center;justify-content:space-between;gap:14px;background:#172033;padding:10px 20px;border-bottom:1px solid #334155;font-family:ui-monospace,Consolas,monospace;font-size:.82em;color:#cbd5e1}
.tdone-ok{background:rgba(56,189,248,.16);color:#38bdf8;border:1px solid rgba(56,189,248,.4);padding:3px 14px;border-radius:999px;font-weight:700;white-space:nowrap;flex-shrink:0}
.tdone-body{padding:18px 24px;display:grid;grid-template-columns:1.05fr 1fr;gap:22px;align-items:start}
.tdone-list{display:flex;flex-direction:column;gap:9px}
.tdone-row{display:flex;justify-content:space-between;gap:14px;padding-bottom:7px;border-bottom:1px solid #1e293b;font-size:.88em}
.tdone-row:last-child{border-bottom:none;padding-bottom:0}
.tdone-k{color:#94a3b8}
.tdone-v{color:#f8fafc;font-weight:700;text-align:right}
.tdone-v.hi{color:#34d399}
.tdone b{color:#fde68a}
.tdone-tbl{width:100%;border-collapse:collapse;font-size:.86em;margin:0;background:#111c33!important;border:1px solid #334155;border-radius:10px;overflow:hidden}
.tdone-tbl th{background:#1e293b!important;color:#cbd5e1!important;padding:8px 11px;text-align:left;font-weight:700;border-bottom:1px solid #334155}
.tdone-tbl td{background:#111c33!important;padding:8px 11px;border-bottom:1px solid #1e293b;color:#f1f5f9!important}
.tdone-tbl tr:nth-child(even) td{background:#16233d!important}
.tdone-tbl tr:last-child td{border-bottom:none}
.tdone-tbl td.em{color:#34d399!important;font-weight:700}
"""


# ------------------------------------------------------------------ อ่าน README 4 ไฟล์
def relink(folder):
    """แปลงเป้าหมายของลิงก์และภาพให้นับจากโฟลเดอร์ของสไลด์ (ไม่แตะข้อความใน code fence)"""
    def one(m):
        t = m.group(2)
        if t.startswith(("http", "#", "mailto:")):
            return m.group(0)
        path, _, frag = t.partition("#")
        new = posixpath.normpath(posixpath.join(folder, path))
        return "%s(%s%s)" % (m.group(1), new, "#" + frag if frag else "")

    def tr(text):
        out, fence = [], False
        for ln in text.split("\n"):
            if ln.strip().startswith("```"):
                fence = not fence
            elif not fence and folder:
                ln = re.sub(r"(\])\(([^)\s]+)\)", one, ln)
            out.append(ln)
        return "\n".join(out)
    return tr


DOC = {
    "ov": list(E.load("README.md", relink(""))),
    "s1": list(E.load("1_single_gpu/README.md", relink("1_single_gpu"))),
    "dp": list(E.load("2_data_parallel/README.md", relink("2_data_parallel"))),
    "mp": list(E.load("3_model_parallel/README.md", relink("3_model_parallel"))),
}

S1 = json.loads(E.read("1_single_gpu/results/summary.json"))
DP2 = json.loads(E.read("2_data_parallel/results/summary.json"))
DP4 = json.loads(E.read("2_data_parallel/gpu4/results/summary.json"))
MP2 = json.loads(E.read("3_model_parallel/results/summary.json"))
MP4 = json.loads(E.read("3_model_parallel/gpu4/results/summary.json"))


def use(doc):
    E.SECS[:] = DOC[doc]


def blocks(doc, prefix):
    use(doc)
    return E.sec(prefix)


def T(doc, prefix, head0, k=0):
    out = [b for b in E.walk(blocks(doc, prefix)) if b["t"] == "table" and plain(b["head"][0]).startswith(head0)]
    if k >= len(out):
        raise KeyError("ไม่พบตาราง %r ลำดับ %d ในหัวข้อ %r ของ %s" % (head0, k, prefix, doc))
    return out[k]


def filter_table(t, drop_starts=(), keep_starts=None):
    rows = []
    for r in t["rows"]:
        c0 = plain(r[0])
        if keep_starts is not None and not any(c0.startswith(p) for p in keep_starts):
            continue
        if any(c0.startswith(p) for p in drop_starts):
            continue
        rows.append(r)
    return {"t": "table", "head": list(t["head"]), "rows": rows}


def pslides(doc, prefix, title, how="คัดลอกแล้ววางใน Claude Code ที่โฟลเดอร์ 02_VastAi_Application"):
    use(doc)
    return E.prompt_slides(E.prompt_code(prefix, 0, how), CTX["kicker"], title)


# ------------------------------------------------------------------ ชิ้นส่วนช่วย
def big(title, src, points, post="", cls="big"):
    """ภาพใหญ่ด้านซ้าย + ข้อพูดเรียงเลข 3-4 ข้อด้านขวา"""
    s = explain(title, src, points, post)
    s["body"] = s["body"].replace('<div class="ex">', '<div class="ex %s">' % cls, 1)
    return s


def nfig(key, post=""):
    f = FIG[key]
    return big(f["title"], IMG_SL + "%s.jpg" % key, f["steps"], post=post, cls="mid2")


def vastai_ready(title, label, gpu_badge, specs, checks, next_text, post_note, tag="ช่วงสร้างเครื่องเสร็จ"):
    """สไลด์คั่นแสดงหน้าเว็บ Vast.ai ว่าเครื่องถูกสร้างและพร้อมใช้งาน (RUNNING) ก่อนเข้าสู่ช่วงเทรน"""
    kv_html = "".join(
        '<div class="vweb-k">%s</div><div class="vweb-v">%s</div>' % (E.esc(k), md(v))
        for k, v in specs
    )
    chk_html = "".join(
        '<div class="vweb-item"><span class="vweb-ok">✓</span><span>%s</span></div>' % md(c)
        for c in checks
    )
    body = (
        '<div class="vweb">'
        '<div class="vweb-bar">'
        '<div class="vweb-dots"><span class="vweb-dot" style="background:#f87171"></span>'
        '<span class="vweb-dot" style="background:#fbbf24"></span>'
        '<span class="vweb-dot" style="background:#34d399"></span></div>'
        '<div class="vweb-url">cloud.vast.ai/instances/</div>'
        '<div class="vweb-status">● RUNNING</div>'
        '</div>'
        '<div class="vweb-body">'
        '<div class="vweb-head">'
        '<div class="vweb-gpu">%s</div>'
        '<div class="vweb-lbl">ป้ายเครื่อง: %s</div>'
        '</div>'
        '<div class="vweb-grid">'
        '<div class="vweb-kv">%s</div>'
        '<div class="vweb-chk">'
        '<div class="vweb-chkh">ของที่เตรียมไว้บนเครื่องเสร็จแล้ว</div>'
        '%s'
        '<div class="vweb-next">➜ %s</div>'
        '</div></div></div></div>%s'
    ) % (E.esc(gpu_badge), E.esc(label), kv_html, chk_html, md(next_text), post_note)
    return S(title, body, tag=tag)


def train_done(title, bar_title, metrics, epoch_rows, post_note, tag="ช่วงเทรนเสร็จ"):
    """สไลด์คั่นแสดงค่าผลลัพธ์จริงที่ขึ้นมาหลังเทรนครบ 3 Epoch ก่อนดูกราฟเจาะลึก"""
    m_html = "".join(
        '<div class="tdone-row"><span class="tdone-k">%s</span><span class="tdone-v%s">%s</span></div>' % (
            E.esc(k), " hi" if hi else "", md(v))
        for k, v, hi in metrics
    )
    e_html = "".join(
        '<tr><td>%s</td><td>%s</td><td>%s</td><td class="em">%s</td></tr>' % (
            E.esc(ep), E.esc(tl), E.esc(vl), E.esc(em))
        for ep, tl, vl, em in epoch_rows
    )
    body = (
        '<div class="tdone">'
        '<div class="tdone-bar">'
        '<span>%s</span>'
        '<span class="tdone-ok">✓ เทรนครบ 3 Epoch · เครื่องยังเปิดอยู่</span>'
        '</div>'
        '<div class="tdone-body">'
        '<div class="tdone-list">%s</div>'
        '<div>'
        '<table class="tdone-tbl"><thead><tr><th>จุดวัด</th><th>train loss</th><th>test loss</th><th>Exact Match</th></tr></thead>'
        '<tbody>%s</tbody></table>'
        '</div>'
        '</div></div>%s'
    ) % (E.esc(bar_title), m_html, e_html, post_note)
    return S(title, body, tag=tag)


def statement(title, photo, q, sub, links_html=""):
    """ประโยคปิดบนภาพถ่ายเต็มหน้า"""
    lk = '<div class="links">%s</div>' % links_html if links_html else ""
    raw = ('<img class="bg" src="%s" alt="%s"><div class="shade"></div><div class="inner">'
           '<div class="q">%s</div><div class="sub2">%s</div>%s</div>'
           '<div class="imgnote">ภาพจำลอง</div>') % (photo, E.esc(title), md(q), md(sub), lk)
    return {"raw": raw, "cls": "stmt", "style": "", "title": title, "kicker": "", "tag": "", "lead": ""}


def build():
    E.SL[:] = []
    E.PROMPTS[:] = []

    # =========================================================================
    # 1 · เริ่มต้น: เส้นทางของ LAB 4 · โฟลเดอร์และความต่างทั้ง 3 แล็บย่อย
    # =========================================================================
    CTX.update(kicker="", group="เริ่มต้น · ภาพรวมและแผนที่โฟลเดอร์")
    add(E.cover(
        "LAB 4 · Multi-GPU ใน 1 เครื่อง",
        "Single GPU · Data Parallelism · Model Parallelism (เครื่องเดียว · 1, 2 และ 4 ใบ)",
        IMG_SL + "s01-cover.jpg",
        small="02_VastAi_Application / lab4_multigpu",
    ))

    CTX["kicker"] = "ภาพรวมของ LAB 4"
    add(fig(
        "เส้นทางของทั้งบท: ใช้เครื่องเดียวแต่เพิ่มหลาย GPU เพื่อแก้คอขวดคนละด้าน",
        IMG_SL + "s07-lab4-journey.jpg",
        "ทุกการทดลองใช้ **1 เครื่องต่อรอบ** (Multi-GPU ในเครื่องเดียว): เริ่มจาก **Single GPU** (1 ใบ ชนเพดานทั้งความเร็วและ VRAM) → แยกเป็น **Data Parallelism** (2 และ 4 ใบ เน้นความเร็ว) และ **Model Parallelism** (2 และ 4 ใบ ขยาย VRAM และ batch)",
        tag="ภาพจำลอง",
    ))

    add(nfig("n01-lab4-folders"))

    t_labs = T("ov", "ขอบเขตของบทนี้", "LAB ย่อย")
    add(tbl(
        "3 LAB ย่อยอยู่ที่โฟลเดอร์ไหน: เช่ากี่เครื่อง และเครื่องนั้นมี GPU กี่ใบ",
        t_labs,
        post=note("บทนี้ใช้ **เครื่องเช่าเพียง 1 เครื่องต่อรอบ** (GPU ทุกใบเสียบอยู่ในเครื่องเดียวกัน ไม่ใช่คลัสเตอร์หลายเครื่อง) · ใน `2_data_parallel/` และ `3_model_parallel/` ผลรอบ 2 ใบอยู่ที่รากโฟลเดอร์ ส่วนรอบ 4 ใบแยกเก็บใน `gpu4/`", "info"),
        tag="ตารางหลัก · โฟลเดอร์",
    ))

    add(big(
        "เมื่อในเครื่องเดียวมีหลาย GPU เลือกใช้ได้ 2 แบบ ซึ่งแก้ปัญหาคนละด้าน",
        IMG_S + "r-choose.png",
        [
            "**Data Parallelism (`2_data_parallel/`)** ให้ GPU ทุกใบในเครื่องถือโมเดลครบชุด แล้วแบ่งข้อมูลกันเทรน เหมาะเมื่ออยากให้ **เสร็จเร็วขึ้น**",
            "**Model Parallelism (`3_model_parallel/`)** แบ่ง Layer ของโมเดลชุดเดียวลงหลายใบในเครื่องเดียวกัน เหมาะเมื่อ **VRAM ไม่พอ** สำหรับโมเดลหรือ batch ที่ต้องการ",
            "**Single GPU (`1_single_gpu/`)** เป็นจุดตั้งต้น (1 เครื่อง × 1 ใบ) ไว้เทียบว่าเมื่อเพิ่มเป็น 2 ใบและ 4 ใบในเครื่องเดียว แต่ละแบบให้อะไรกลับมาจริง",
        ],
    ))

    t_diff = filter_table(T("ov", "3 แบบต่างกันอย่างไร", ""), drop_starts=("ภาพ",))
    add(tbl(
        "3 วิธีต่างกันอย่างไรในเชิงสถาปัตยกรรม: สิ่งที่ถูกแบ่ง และจังหวะการทำงานของ GPU",
        t_diff,
        post=note("ข้อต่างหัวใจ: Data Parallelism ให้ทุกใบทำงาน **พร้อมกัน** ส่วน Model Parallelism ให้แต่ละใบ **ผลัดกัน** ทำทีละช่วง"),
        tag="ตารางหลัก",
    ))

    t_same = T("ov", "สิ่งที่เหมือนกันทั้ง 3 LAB ย่อย", "หัวข้อ")
    add(tbl(
        "ตัวแปรควบคุมที่ตรึงเหมือนกันทั้ง 3 LAB เพื่อให้เทียบผลกันได้ตรงไปตรงมา",
        t_same,
        post=note("ทุกรอบแบ่งเป็น 3 ช่วงชัดเจน: **สร้างเครื่องบน Vast.ai → เทรนโมเดล 3 Epoch → สรุปผลและลบเครื่อง** (ห้ามลืมลบเครื่องในขั้นสุดท้าย)", "info"),
        tag="ค่าที่ตรึง",
    ))

    # =========================================================================
    # 2 · พื้นฐานร่วม: Dataset · โมเดล Qwen3-8B · LoRA
    # =========================================================================
    CTX.update(kicker="", group="พื้นฐานร่วม · ข้อมูล โมเดล และ LoRA")
    add(E.divider(
        "พื้นฐานร่วม",
        "Dataset · โมเดล Qwen3-8B · และ LoRA",
        "<p>ของชุดเดียวกันที่ทุก LAB ย่อย (<code>1_single_gpu</code> · <code>2_data_parallel</code> · <code>3_model_parallel</code>) ใช้ก่อนเริ่มจัดวางบน GPU</p>",
        img=IMG_SL + "s02-foundations.jpg",
        small="ใช้ร่วมกันทั้ง 3 LAB ย่อย",
    ))

    CTX["kicker"] = "พื้นฐานร่วม · Dataset"
    add(big(
        "Dataset `sql-create-context` สอนโมเดลแปลงคำถามภาษาอังกฤษเป็น SQL",
        IMG_S + "d-example.png",
        [
            "ข้อมูลมาจาก **WikiSQL และ Spider** รวมทั้งหมด **78,577 ตัวอย่าง** สัญญาอนุญาต CC BY 4.0",
            "1 ตัวอย่างมี 3 ช่อง คือ คำถาม (`question`), โครงสร้างตาราง (`context`) และ SQL เฉลย (`answer`)",
            "โมเดลรับ 2 ช่องแรกเป็น Input แล้วต้องสร้างคำสั่ง SQL ในช่องที่ 3 ให้ตรงเฉลย",
        ],
    ))

    t_row1 = T("s1", "รู้จัก Dataset", "ช่อง")
    add(tbl(
        "ตัวอย่างแถวที่ 1 ของ Training Set: แต่ละช่องทำหน้าที่ต่างกันอย่างไร",
        t_row1,
        post=note("ดูตัวอย่างจริงครบ 6 แถวแรกใน [1_single_gpu/results/dataset_samples.md](1_single_gpu/results/dataset_samples.md) ซึ่งทุก LAB ย่อยได้ชุดเดียวกันเพราะสับด้วย `seed 0`", "info"),
        tag="ตัวอย่างจริง",
    ))

    add(fig(
        "สับ 78,577 ตัวอย่างด้วย seed 0 แบ่งเป็น Train 4,000 และ Test 200 ชุดเดียวกันทุก LAB",
        IMG_S + "d-split.png",
        "**Test Set 200 ข้อ** ใช้สอบวัด Exact Match เท่านั้น ห้ามนำเข้าเทรน · 1 ข้อที่ตอบถูกเท่ากับ **0.5 จุดเปอร์เซ็นต์**",
    ))

    CTX["kicker"] = "พื้นฐานร่วม · โมเดลและ LoRA"
    add(big(
        "โมเดล `Qwen3-8B` มี 36 Layer และใช้ VRAM ราว 15.3 GiB ตั้งแต่ยังไม่เริ่มเทรน",
        IMG_S + "m-qwen3-8b.png",
        [
            "ขนาด **8.19 พันล้าน parameter** (`bf16`) ใช้พื้นที่บน disk **16.4 GB** และกิน VRAM **15.27 GiB** บน GPU ใบเดียว",
            "ในการทดลองนี้ **ปิดโหมด thinking** เพื่อให้ตอบเป็นคำสั่ง SQL โดยตรง และไม่ใช้ Gradient Checkpointing",
            "วัดผลเทียบระหว่าง **Base** (โมเดลเดิมก่อนเทรน) กับ **Fine-tuned** หลังจบ Epoch 1, 2 และ 3",
        ],
    ))

    add(big(
        "กลไก Attention ในแต่ละ Layer แปลงทุกคำเป็น Query, Key และ Value",
        IMG_S + "t-qkv.png",
        [
            "**Query (`q_proj`)** คือคำค้นที่ถือไว้ว่ากำลังต้องการข้อมูลอะไร",
            "**Key (`k_proj`)** คือป้ายกำกับที่บอกว่าคำนี้เกี่ยวกับอะไร ใช้เทียบกับ Query",
            "**Value (`v_proj`)** คือเนื้อหาที่จะหยิบไปใช้ต่อเมื่อเลือกได้แล้ว",
        ],
    ))

    add(big(
        "LoRA ล็อกน้ำหนักเดิมทั้งหมด แล้วเทรนเฉพาะตารางเล็ก 3.83 ล้านค่า (0.047%)",
        IMG_S + "t-lora-qv.png",
        [
            "แปะ LoRA (`r=8`, `alpha=16`) เฉพาะที่ **`q_proj` และ `v_proj`** ใน 36 Layer รวม **72 จุด**",
            "เทรนเพียง **3,833,856 parameter** จาก 8.19 พันล้าน ทำให้ส่วน Optimizer และ Gradient มีขนาดเล็กมาก",
            "Gradient ของ LoRA ขนาดเพียงราว **15 MB ต่อ step** จึงเหมาะกับการส่งข้าม GPU ใน Data Parallelism",
        ],
    ))

    # =========================================================================
    # 3 · LAB 4.1 · Single GPU (`1_single_gpu/`, 1 เครื่อง × 1 ใบ)
    # =========================================================================
    CTX.update(kicker="", group="LAB 4.1 · Single GPU (1_single_gpu/)")
    add(E.divider(
        "LAB 4.1",
        "Single GPU · เทรนด้วย GPU ใบเดียวและหาขีดจำกัด",
        "<p>คำถาม: เครื่องที่มี GPU 1 ใบ เทรนโมเดล 8 พันล้าน parameter ได้ batch ใหญ่แค่ไหน และเร็วเท่าไร</p>"
        "<p class=\"dim\">โฟลเดอร์: <code>1_single_gpu/</code> · 1 เครื่อง (RTX 3090 24 GB × 1 ใบ) · 3 ขั้นตอน</p>",
        img=IMG_SL + "s03-single.jpg",
        small="ส่วนที่ 1 จาก 3 ของภาค LAB · โฟลเดอร์ 1_single_gpu/",
    ))

    CTX["kicker"] = "LAB 4.1 (1_single_gpu/) · ช่วงสร้างเครื่อง (ขั้นที่ 1)"
    add(big(
        "Single GPU: โมเดลทั้งชุดและ batch ทั้งก้อนอยู่บน GPU 0 ใบเดียว",
        IMG_1 + "c-single.png",
        [
            "1 step ทำ **Forward → Backward → Update** ต่อเนื่องบนการ์ดใบเดียว ไม่มีการส่งข้อมูลข้าม GPU",
            "เขียนโค้ดง่ายที่สุด แต่รับ batch ได้จำกัดเท่าที่ VRAM ของการ์ดใบนี้เหลืออยู่",
            "ใช้เป็น **Baseline** เพื่อวัดว่าการเพิ่มเป็น 2 ใบและ 4 ใบในเครื่องเดียว (LAB 4.2 และ 4.3) ช่วยได้จริงแค่ไหน",
        ],
    ))

    add(big(
        "ขั้นที่ 1: เช่าเครื่อง RTX 3090 1 ใบ โหลด Qwen3-8B และแบ่ง Dataset",
        IMG_1 + "s1-one.png",
        [
            "เช่าเครื่อง 1 เครื่องผ่านเงื่อนไข (verified, PyTorch 2.8, CUDA 12.8, เน็ต ≥ 700 Mbps, disk 60 GB) ป้าย `vapp-lab4-single`",
            "โหลด `Qwen/Qwen3-8B` (16.4 GB) และ `b-mc2/sql-create-context` ลงเครื่องเช่า",
            "แบ่ง Training Set 4,000 และ Test Set 200 ด้วย `seed 0` แล้วสรุปตัวอย่าง 6 แถวลง `results/dataset_samples.md`",
        ],
    ))

    add(pslides("s1", "ขั้นที่ 1 ·", "LAB 4.1 ขั้นที่ 1 · เช่าเครื่อง 1 GPU และเตรียมของ"))

    add(vastai_ready(
        "หลังรันขั้นที่ 1: เครื่องบน Vast.ai ถูกสร้างและพร้อมใช้งานแล้ว (1 เครื่อง × 1 GPU)",
        "vapp-lab4-single",
        "1 เครื่อง · RTX 3090 24 GB × 1 ใบ",
        [
            ("ตำแหน่งเครื่อง", "Ontario, แคนาดา · สถานะ **RUNNING** (พร้อมในไม่ถึง 1 นาที)"),
            ("ระบบซอฟต์แวร์", "PyTorch 2.8.0+cu128 · CUDA 12.8 · disk 60 GB"),
            ("การเชื่อม GPU", "การ์ดใบเดียว (GPU 0) ไม่มีการส่งข้อมูลข้ามการ์ด"),
            ("ไฟล์ผลที่สร้าง", "`prepare_data.py` · `results/dataset_samples.md`"),
        ],
        [
            "โหลดโมเดล **Qwen/Qwen3-8B (16.4 GB)** ลงเครื่องเช่าครบแล้ว",
            "แบ่ง **Training Set 4,000** และ **Test Set 200** (seed 0) เรียบร้อย",
            "ผูกกุญแจ SSH (`devtoolSSH`) และตรวจว่าเครื่องตอบสนองพร้อมรันโค้ด",
        ],
        "ช่วงสร้างเครื่องเสร็จแล้ว · ขั้นถัดไปคือ **ช่วงเทรนโมเดล (ขั้นที่ 2)**",
        note("รอให้หน้าเว็บ Vast.ai แสดงสถานะ **RUNNING** และโหลดโมเดลกับข้อมูลครบก่อน จึงค่อยวางพรอมต์ขั้นที่ 2 เพื่อเริ่มเทรน", "info"),
    ))

    CTX["kicker"] = "LAB 4.1 (1_single_gpu/) · ช่วงเทรนโมเดล (ขั้นที่ 2)"
    add(big(
        "VRAM บนการ์ด 24 GB: Weights กินไป 15.3 GiB เหลือให้ Activation ราว 8.5 GiB",
        IMG_1 + "vram-single.png",
        [
            "**Weights คงที่ 15.27 GiB** (ราว 2 ใน 3 ของการ์ด) ส่วน LoRA + Optimizer ใช้เพียงราว 61 MB",
            "**Activation โตตามขนาด batch** เมื่อเพิ่ม batch เป็น 1 → 2 → 4 VRAM พุ่งเป็น 17.24 → 19.15 → **22.98 GiB**",
            "การ์ดใบนี้ใช้ได้จริง **23.80 GiB** ที่ batch 4 จึงเหลือที่ว่างไม่ถึง 1 GiB และ **batch 8 เกิด Out of Memory**",
        ],
    ))

    add(big(
        "ทำไมต้องวัด VRAM (Probe) ด้วยตัวอย่างที่ยาวที่สุดก่อนเทรนจริง",
        IMG_S + "s-why-probe.png",
        [
            "ลองรัน batch 1, 2, 4, 8 … อย่างละ **3 step** เพื่อหาเพดานก่อนเริ่มงานยาว แทนที่จะเดาแล้วล้มกลางทาง",
            "ต้องใช้ **ตัวอย่างที่ยาวที่สุด (256 token)** เพราะ batch ที่ยาวผิดปกติเพียงครั้งเดียวกลางทางก็ทำให้งานหยุดได้",
            "พรอมต์สั่งให้ AI ประมาณจากอัตราการเพิ่มของ VRAM แล้วลองค่าระหว่างตัวที่ผ่านกับตัวที่ล้มเพื่อยืนยัน",
        ],
    ))

    add(big(
        "ขั้นที่ 2: หา batch ใหญ่สุด เทรน 3 Epoch และวัด Exact Match หลังทุก Epoch",
        IMG_S + "s2-flow3.png",
        [
            "AI เขียน `train.py` และ `eval.py` แล้วรันต่อเนื่องใน `tmux` พร้อมระบบต่อจาก checkpoint เมื่อการเชื่อมต่อหลุด",
            "วัดโมเดล **Base** ก่อนเทรน แล้วใช้ **batch ใหญ่สุดที่ผ่านจากขั้น probe** เทรน 3 Epoch",
            "หลังจบทุก Epoch วัด test loss และ Exact Match บน Test Set 200 ข้อ",
        ],
    ))

    add(pslides("s1", "ขั้นที่ 2 ·", "LAB 4.1 ขั้นที่ 2 · เทรนด้วย GPU 1 ใบ"))

    CTX["kicker"] = "LAB 4.1 (1_single_gpu/) · ผลหลังเทรนเสร็จและบทเรียน"
    add(train_done(
        "หลังเทรน Single GPU ครบ 3 Epoch: ค่าผลลัพธ์จริงที่แสดงเมื่อจบขั้นที่ 2",
        "LAB 4.1 · Single GPU (1 เครื่อง × RTX 3090 1 ใบ · vapp-lab4-single)",
        [
            ("batch ใหญ่สุดที่เทรนได้", "4 (batch 8 เกิด Out of Memory)", True),
            ("จำนวน step ต่อ Epoch", "1,000 step (รวม 3,000 step ใน 23.6 นาที)", False),
            ("ความเร็วเฉลี่ย", "%.2f ตัวอย่างต่อวินาที (%.3f วินาทีต่อ step)" % (S1["examples_per_sec"], S1["sec_per_step"]), True),
            ("GPU utilization เฉลี่ย", "%.1f%% (การ์ดใบเดียวทำงานเต็มที่)" % S1["gpu_util_pct"], False),
            ("VRAM สูงสุดตอนเทรน", "%.2f GiB (เหลือไม่ถึง 1 GiB)" % S1["peak_vram_training_gib"], False),
        ],
        [
            ("Base (ก่อนเทรน)", "–", "%.4f" % S1["test_loss_base"], "%.1f%%" % S1["exact_match_pct"]["base"]),
            ("หลัง Epoch 1", "%.4f" % S1["train_loss_per_epoch"][0], "%.4f" % S1["test_loss_per_epoch"][0], "%.1f%%" % S1["exact_match_pct"]["epoch1"]),
            ("หลัง Epoch 2", "%.4f" % S1["train_loss_per_epoch"][1], "%.4f" % S1["test_loss_per_epoch"][1], "%.1f%%" % S1["exact_match_pct"]["epoch2"]),
            ("หลัง Epoch 3", "%.4f" % S1["train_loss_per_epoch"][2], "%.4f" % S1["test_loss_per_epoch"][2], "%.1f%%" % S1["exact_match_pct"]["epoch3"]),
        ],
        note("รอบแรกล้มด้วย Out of Memory หลัง step 740 เพราะ `attention_mask` หลัง AI แก้แล้วรันใหม่จึงเทรนจบครบ 3 Epoch — ดูรายละเอียดและกราฟในหน้าถัดไป"),
    ))

    add(fig(
        "ผลวัด VRAM บน GPU 1 ใบ: batch 4 ใช้ 22.98 GiB และ batch 8 เกิด Out of Memory",
        P1 + "results/images/vram_vs_batch.png",
        "วัดด้วยข้อความยาว 256 token อย่างละ 3 step · อัตราโตของ VRAM ราว **1.9 GiB ต่อ 1 ตัวอย่าง** ที่ batch 4 เหลือที่ว่างเพียง 0.82 GiB",
        tag="1_single_gpu/results/probe.json",
    ))

    add(nfig("n02-oom-padding", post=note("ในรอบจริง LAB 4.1 เกิด Out of Memory หลัง **step 740 จาก 1,000** ของ Epoch 1 ทั้งที่เปิด `expandable_segments` แล้ว พอหยุดส่ง `attention_mask` ก็เทรนจบครบ 3 Epoch ที่ VRAM สูงสุด 22.98 GiB เท่าตอนวัด")))

    add(E.hero(
        CTX["kicker"],
        "ผล Single GPU: batch สูงสุด %d · ความเร็ว %.2f ตัวอย่างต่อวินาที · GPU utilization %.1f%%" % (
            S1["batch_used"], S1["examples_per_sec"], S1["gpu_util_pct"]),
        IMG_SL + "h01-single.jpg",
        [
            ("batch ใหญ่สุดที่เทรนได้", "%d" % S1["batch_used"],
             "1,000 step ต่อ Epoch · batch 8 เกิด Out of Memory", ""),
            ("ความเร็วเฉลี่ย 3 Epoch", "%.2f" % S1["examples_per_sec"] + "<small>ตัวอย่างต่อวินาที</small>",
             "%.3f วินาทีต่อ step · ใช้เวลาเทรน %.1f นาที" % (S1["sec_per_step"], S1["train_minutes"]), "ok"),
            ("GPU utilization เฉลี่ย", "%.1f%%" % S1["gpu_util_pct"],
             "GPU ใบเดียวเป็นคอขวดเต็มที่แล้ว (VRAM %.2f GiB)" % S1["peak_vram_training_gib"], "warn"),
        ],
        post=note("ความเร็วตอนเทรนจริง (%.2f ตัวอย่างต่อวินาที) เร็วกว่าตอน probe เพราะข้อความเฉลี่ยยาว 112.2 token สั้นกว่า 256 token" % S1["examples_per_sec"]),
        tag="1_single_gpu/results/summary.json",
    ))

    add(fig(
        "Loss ตลอด 3 Epoch: train loss ลดเร็วและ test loss ลดลงต่อเนื่อง ยังไม่ overfit",
        P1 + "results/images/loss_3_epochs.png",
        "train loss เฉลี่ยลดจาก **%.4f → %.4f → %.4f** · จุดสีส้มคือ test loss ท้ายแต่ละ Epoch ลดจาก **%.4f → %.4f → %.4f**" % (
            S1["train_loss_per_epoch"][0], S1["train_loss_per_epoch"][1], S1["train_loss_per_epoch"][2],
            S1["test_loss_per_epoch"][0], S1["test_loss_per_epoch"][1], S1["test_loss_per_epoch"][2]),
        tag="1_single_gpu/results/train_metrics.json",
    ))

    add(fig(
        "Exact Match บน Test Set 200 ข้อ: พุ่งจาก %.1f%% เป็น %.1f%% ตั้งแต่ Epoch แรก" % (
            S1["exact_match_pct"]["base"], S1["exact_match_pct"]["epoch1"]),
        P1 + "results/images/exact_match_per_epoch.png",
        "หลัง Epoch 1 / 2 / 3 ได้ **%.1f%% · %.1f%% · %.1f%%** · Epoch 2 กับ 3 ต่างกันเพียง 3 ข้อจาก 200 จึงถือว่าทรงตัว" % (
            S1["exact_match_pct"]["epoch1"], S1["exact_match_pct"]["epoch2"], S1["exact_match_pct"]["epoch3"]),
        tag="1_single_gpu/results/summary.json",
    ))

    add(E.hero(
        CTX["kicker"],
        "ทำไม Base ได้ Exact Match แค่ %.1f%%: ส่วนใหญ่ผิดที่สไตล์ ไม่ใช่ตรรกะ SQL" % S1["exact_match_pct"]["base"],
        IMG_SL + "h05-base-style.jpg",
        [
            ("Base · แบบเข้มงวด", "%.1f%%" % S1["exact_match_pct"]["base"],
             "ตรงเพียง 3/200 ข้อ เพราะตอบ `'Ray Allen (20)'` แทน `\"ray allen (20)\"`", "bad"),
            ("Base · แบบผ่อนปรน", "%.1f%%" % S1["exact_match_relaxed_pct"]["base"],
             "ตรงถึง 105/200 ข้อ เมื่อไม่สนตัวพิมพ์เล็กใหญ่และชนิดเครื่องหมายคำพูด", "warn"),
            ("หลัง Fine-tune 3 Epoch", "%.1f%%" % S1["exact_match_pct"]["epoch3"],
             "แบบเข้มงวดพุ่งเป็น 155/200 ข้อ (ดีสุดที่ Epoch 2: %.1f%%)" % S1["exact_match_pct"]["epoch2"], "ok"),
        ],
        post=note("ตัวอย่างข้อแรก: เฉลยใช้ `\"ray allen (20)\"` · โมเดล Base ตอบ `'Ray Allen (20)'` · หลัง Epoch 3 ตอบตรงเฉลยทุกตัวอักษร"),
        tag="1_single_gpu/results/eval_base.json",
    ))

    CTX["kicker"] = "LAB 4.1 (1_single_gpu/) · ช่วงลบเครื่อง (ขั้นที่ 3) และจุดเปลี่ยนสู่ Multi-GPU"
    add(pslides("s1", "ขั้นที่ 3 ·", "LAB 4.1 ขั้นที่ 3 · สรุปผลเป็นกราฟและลบเครื่อง (ห้ามข้าม)"))

    add(E.hero(
        CTX["kicker"],
        "ขีดจำกัดของ GPU ใบเดียว: ทำงานเต็ม 97% และ VRAM เหลือไม่ถึง 1 GiB พร้อมกัน",
        IMG_SL + "h11-single-limit.jpg",
        [
            ("เพดานด้านความเร็ว", "%.1f%%" % S1["gpu_util_pct"],
             "การ์ดใบนี้คำนวณเต็มกำลังแล้ว อยากเร็วกว่านี้ต้องไป **LAB 4.2 Data Parallelism**", "warn"),
            ("เพดานด้าน VRAM", "%.2f GiB" % S1["peak_vram_training_gib"],
             "เหลือที่ว่างเพียง 0.82 GiB (batch 8 เกิด Out of Memory) อยากได้ batch ใหญ่ขึ้นต้องไป **LAB 4.3 Model Parallelism**", "bad"),
            ("Baseline ที่ได้", "%.2f" % S1["examples_per_sec"] + "<small>ตัวอย่างต่อวินาที</small>",
             "batch 4 · Exact Match หลัง Epoch 3 = %.1f%% · เตรียมเทียบกับเครื่องเดียว 2 และ 4 ใบ" % S1["exact_match_pct"]["epoch3"], ""),
        ],
        post=note("GPU 1 ใบชนเพดานพร้อมกันทั้งสองด้าน จึงเป็นเหตุผลให้ LAB 4.2 และ LAB 4.3 ทดลองแก้ปัญหาคนละด้านด้วยหลาย GPU ในเครื่องเดียว"),
        tag="สรุป LAB 4.1",
    ))

    # =========================================================================
    # 4 · LAB 4.2 · Data Parallelism (`2_data_parallel/` และ `gpu4/`, 1 เครื่อง × 2 และ 4 ใบ)
    # =========================================================================
    CTX.update(kicker="", group="LAB 4.2 · Data Parallelism (2_data_parallel/)")
    add(E.divider(
        "LAB 4.2",
        "Data Parallelism · ถือโมเดลคนละชุด แบ่งข้อมูลกันเทรน",
        "<p>คำถาม: ให้ GPU 2 ใบและ 4 ใบในเครื่องเดียวกันถือโมเดลครบชุดแล้วแบ่งข้อมูลกันเทรน จะเร็วขึ้นกี่เท่า และ batch ต่อใบเปลี่ยนไหม</p>"
        "<p class=\"dim\">โฟลเดอร์: <code>2_data_parallel/</code> (ขั้น 1–3 · 1 เครื่อง × 2 ใบ) และ <code>2_data_parallel/gpu4/</code> (ขั้น 4–6 · 1 เครื่อง × 4 ใบ)</p>",
        img=IMG_SL + "s04-dp.jpg",
        small="ส่วนที่ 2 จาก 3 ของภาค LAB · โฟลเดอร์ 2_data_parallel/",
    ))

    CTX["kicker"] = "LAB 4.2 (2_data_parallel/) · แนวคิด Data Parallelism"
    add(big(
        "Data Parallelism: GPU ทุกใบถือโมเดลครบชุด แล้วแบ่งข้อมูลกันทำคนละครึ่ง",
        IMG_2 + "c-dp.png",
        [
            "เปิดโปรแกรมเทรน 1 process ต่อ GPU โดยแต่ละใบถือสำเนาโมเดล (**replica**) ครบทั้ง 36 Layer",
            "ข้อมูล 1 batch รวมถูกแบ่งให้แต่ละใบไม่ซ้ำกัน (2 ใบได้ใบละ 2,000 ตัวอย่างต่อ Epoch)",
            "หลังคำนวณ Gradient เสร็จ นำมาเฉลี่ยให้เท่ากันแล้ว Update เหมือนกัน น้ำหนักทุกใบจึงตรงกันทุก step",
        ],
    ))

    add(big(
        "1 step ของ DistributedDataParallel: ทำ Forward + Backward พร้อมกัน รอกันแค่ช่วง All-reduce ราว 15 MB",
        IMG_2 + "c-dp-step.png",
        [
            "**Forward + Backward** ทุกใบคำนวณบนข้อมูลส่วนของตัวเองพร้อมกันโดยไม่ต้องรออีกใบ",
            "**All-reduce** เฉลี่ยเฉพาะ Gradient ของ LoRA (3.83 ล้านค่า × 4 byte ≈ **15 MB**) แล้วทุกใบ **Update** ด้วยค่าเดียวกัน",
            "เพราะข้อมูลที่ส่งมีแค่ ~15 MB แม้เครื่อง 2 ใบไม่มี NVLink (ผ่าน PCIe ข้าม NUMA) ช่วงรอกันก็ยังสั้นมาก",
        ],
    ))

    add(big(
        "ข้อจำกัดของ Data Parallelism: เพิ่ม GPU ไม่ได้ที่ว่าง VRAM ต่อใบเพิ่ม",
        IMG_2 + "vram-dp.png",
        [
            "ทุกใบยังต้องถือ **Weights 15.29 GiB** เหมือนตอนมี GPU ใบเดียว ที่ว่างสำหรับ Activation ต่อใบจึงเท่าเดิม",
            "batch ใหญ่สุดต่อ GPU ยังเป็น **4** (batch 8 ต่อใบเกิด Out of Memory ทั้งสองใบ) แต่ **batch รวม** เพิ่มเป็น 8",
            "สรุป: Data Parallelism แก้ปัญหาความเร็ว ไม่ได้แก้ปัญหาโมเดลใส่การ์ดใบเดียวไม่ลง",
        ],
    ))

    CTX["kicker"] = "LAB 4.2 (2_data_parallel/) · รอบ 2 ใบ · ช่วงสร้างเครื่อง (ขั้นที่ 1)"
    add(big(
        "ขั้นที่ 1: เช่าเครื่อง RTX 3090 2 ใบในเครื่องเดียว แล้วเตรียมโมเดลกับ Dataset",
        IMG_S + "s1-two.png",
        [
            "ระบุเงื่อนไข **RTX 3090 2 ใบในเครื่องเดียว** และ CPU ≥ 16 cores ป้าย `vapp-lab4-dp`",
            "ถ้าเครื่องดึง image เกิน 10 นาทีให้ลบและเปลี่ยนทันที (ในรอบจริงเครื่องแรกค้างเกิน 10 นาที AI จึงเปลี่ยนเครื่องเอง)",
            "โหลด `Qwen3-8B` และแบ่ง Dataset ชุดเดิม (4,000 / 200 ด้วย `seed 0`) พร้อมตรวจการเชื่อมต่อระหว่าง GPU (`nvidia-smi topo`)",
        ],
    ))

    add(pslides("dp", "ขั้นที่ 1 ·", "LAB 4.2 ขั้นที่ 1 · เช่าเครื่อง 2 GPU และเตรียมของ"))

    add(vastai_ready(
        "หลังรันขั้นที่ 1: เครื่องบน Vast.ai ถูกสร้างและพร้อมใช้งานแล้ว (1 เครื่อง × 2 GPU)",
        "vapp-lab4-dp",
        "1 เครื่อง · RTX 3090 24 GB × 2 ใบ",
        [
            ("ตำแหน่งเครื่อง", "Quebec, แคนาดา · สถานะ **RUNNING**"),
            ("สเปก CPU / ระบบ", "AMD EPYC 7551P · PyTorch 2.8.0+cu128 · CUDA 12.8 · disk 60 GB"),
            ("การเชื่อมระหว่าง GPU", "PCIe ข้าม NUMA node (`SYS`) ไม่มี NVLink (GPU 0 x4 · GPU 1 x16)"),
            ("หมายเหตุรอบจริง", "เครื่องแรกดึง image เกิน 10 นาที AI ลบและเปลี่ยนเครื่องให้เอง"),
        ],
        [
            "โหลดโมเดล **Qwen/Qwen3-8B (16.4 GB)** ลงเครื่องเช่าครบแล้ว",
            "แบ่ง **Training Set 4,000** และ **Test Set 200** (seed 0) เรียบร้อย",
            "บันทึกโครงสร้างการเชื่อม GPU ลง `results/gpu_topology.txt`",
        ],
        "ช่วงสร้างเครื่องเสร็จแล้ว · ขั้นถัดไปคือ **ช่วงเทรน Data Parallelism 2 ใบ (ขั้นที่ 2)**",
        note("สังเกตว่าเครื่องที่เช่ามีเพียง 1 เครื่องแต่เห็นการ์ด GPU 0 และ GPU 1 ครบทั้ง 2 ใบ เมื่อสถานะเป็น RUNNING แล้วจึงเริ่มขั้นที่ 2", "info"),
    ))

    CTX["kicker"] = "LAB 4.2 (2_data_parallel/) · รอบ 2 ใบ · ช่วงเทรนและผลหลังเทรนเสร็จ (ขั้นที่ 2)"
    add(pslides("dp", "ขั้นที่ 2 ·", "LAB 4.2 ขั้นที่ 2 · เทรนแบบ Data Parallelism (2 GPU)"))

    add(train_done(
        "หลังเทรน Data Parallelism 2 ใบครบ 3 Epoch: ค่าผลลัพธ์จริงที่แสดงเมื่อจบขั้นที่ 2",
        "LAB 4.2 · Data Parallelism (1 เครื่อง × RTX 3090 2 ใบ · vapp-lab4-dp)",
        [
            ("batch ต่อ GPU / batch รวม", "4 ต่อใบ / รวม 8 (batch 8 ต่อใบเกิด Out of Memory)", True),
            ("จำนวน step ต่อ Epoch", "500 step (รวม 1,500 step ใน %.1f นาที)" % DP2["train_minutes"], False),
            ("ความเร็วเฉลี่ย", "%.2f ตัวอย่างต่อวินาที (%.3f วินาทีต่อ step)" % (DP2["examples_per_sec"], DP2["sec_per_step"]), True),
            ("GPU utilization ต่อใบ", "%.1f%% / %.1f%% (ทำงานพร้อมกันทั้งสองใบ)" % (DP2["gpu_util_pct"][0], DP2["gpu_util_pct"][1]), False),
            ("VRAM สูงสุดตอนเทรน", "%.2f / %.2f GiB (PyTorch)" % (DP2["peak_vram_training_torch_gib"][0], DP2["peak_vram_training_torch_gib"][1]), False),
        ],
        [
            ("Base (ก่อนเทรน)", "–", "%.4f" % DP2["test_loss_base"], "1.5%*"),
            ("หลัง Epoch 1", "%.4f" % DP2["train_loss_per_epoch"][0], "%.4f" % DP2["test_loss_per_epoch"][0], "%.1f%%" % DP2["exact_match"]["strict_pct"]["epoch1"]),
            ("หลัง Epoch 2", "%.4f" % DP2["train_loss_per_epoch"][1], "%.4f" % DP2["test_loss_per_epoch"][1], "%.1f%%" % DP2["exact_match"]["strict_pct"]["epoch2"]),
            ("หลัง Epoch 3", "%.4f" % DP2["train_loss_per_epoch"][2], "%.4f" % DP2["test_loss_per_epoch"][2], "%.1f%%" % DP2["exact_match"]["strict_pct"]["epoch3"]),
        ],
        note("รอบแรกล้มด้วย Out of Memory ที่ step 59 เพราะ `attention_mask` หลังแก้แล้วเทรนจบและตรวจยืนยันว่าน้ำหนัก LoRA สองใบเท่ากันทุก Epoch · `*` ไม่นับ `;` ท้ายคำสั่ง"),
    ))

    add(E.hero(
        CTX["kicker"],
        "ผล Data Parallelism 2 ใบ: เร็ว %.2f ตัวอย่างต่อวินาที · GPU utilization %.1f%% / %.1f%% แต่ batch ต่อใบยังเป็น %d" % (
            DP2["examples_per_sec"], DP2["gpu_util_pct"][0], DP2["gpu_util_pct"][1], DP2["batch_used"]["per_gpu"]),
        IMG_SL + "h02-dp2.jpg",
        [
            ("ความเร็วเฉลี่ย 3 Epoch", "%.2f" % DP2["examples_per_sec"] + "<small>ตัวอย่างต่อวินาที</small>",
             "%.3f วินาทีต่อ step ละ %d ตัวอย่าง · เทรนจบใน %.1f นาที" % (
                 DP2["sec_per_step"], DP2["batch_used"]["total"], DP2["train_minutes"]), "ok"),
            ("batch ต่อใบ / รวม", "%d / %d" % (DP2["batch_used"]["per_gpu"], DP2["batch_used"]["total"]),
             "500 step ต่อ Epoch · batch 8 ต่อใบเกิด Out of Memory ทั้งสองใบ", ""),
            ("GPU utilization เฉลี่ย", "%.1f%% / %.1f%%" % (DP2["gpu_util_pct"][0], DP2["gpu_util_pct"][1]),
             "ทำงานพร้อมกันเกือบตลอด แม้ต่อผ่าน PCIe ข้าม NUMA (SYS)", "ok"),
        ],
        post=note("ได้ความเร็วเพิ่มขึ้นชัดเจน แต่ไม่ได้พื้นที่ VRAM ต่อใบเพิ่มเพราะทั้งสองใบต้องถือ Weights 15.29 GiB ครบชุด"),
        tag="2_data_parallel/results/summary.json",
    ))

    add(fig(
        "Data Parallelism 2 ใบ · VRAM ของสองใบเท่ากันเป๊ะทุกขนาด batch และเกิด Out of Memory ที่ batch 8 ต่อใบทั้งคู่",
        P2 + "results/images/vram_vs_batch.png",
        "แท่งของ GPU 0 และ GPU 1 สูงเท่ากันทุกขนาด batch เพราะทั้งสองใบถือโมเดลครบชุด 15.29 GiB และรับข้อมูลเท่ากัน",
        tag="2_data_parallel/results/probe/",
    ))

    add(fig(
        "Data Parallelism 2 ใบ · GPU 0 และ GPU 1 ทำงานพร้อมกัน 97–99% ตลอด 3 Epoch",
        P2 + "results/images/gpu_util.png",
        "GPU 0 เฉลี่ย **%.1f%%** และ GPU 1 เฉลี่ย **%.1f%%** · ช่วงรอ All-reduce ของ LoRA 15 MB สั้นจนแทบไม่ทำให้การ์ดว่าง" % (
            DP2["gpu_util_pct"][0], DP2["gpu_util_pct"][1]),
        tag="2_data_parallel/results/train_summary.json",
    ))

    add(fig(
        "Data Parallelism 2 ใบ · test loss ต่ำสุดที่ Epoch 2 (%.4f) แล้วเริ่มขยับขึ้นที่ Epoch 3 (%.4f)" % (
            DP2["test_loss_per_epoch"][1], DP2["test_loss_per_epoch"][2]),
        P2 + "results/images/loss_3_epochs.png",
        "train loss ลดต่อเนื่อง (**%.4f → %.4f → %.4f**) แต่ test loss เริ่มขยับขึ้นใน Epoch 3 ซึ่งเป็นสัญญาณเริ่มต้นของ overfitting" % (
            DP2["train_loss_per_epoch"][0], DP2["train_loss_per_epoch"][1], DP2["train_loss_per_epoch"][2]),
        tag="2_data_parallel/results/train_summary.json",
    ))

    add(fig(
        "Data Parallelism 2 ใบ · Exact Match เพิ่มขึ้นทุก Epoch ถึง %.1f%% หลัง Epoch 3" % DP2["exact_match"]["strict_pct"]["epoch3"],
        P2 + "results/images/exact_match.png",
        "Base %.1f%% (1.5%% เมื่อไม่นับ `;` ท้าย) → Epoch 1: **%.1f%%** → Epoch 2: **%.1f%%** → Epoch 3: **%.1f%%** (แบบผ่อนปรนสูงสุด %.1f%%)" % (
            DP2["exact_match"]["strict_pct"]["base"],
            DP2["exact_match"]["strict_pct"]["epoch1"],
            DP2["exact_match"]["strict_pct"]["epoch2"],
            DP2["exact_match"]["strict_pct"]["epoch3"],
            DP2["exact_match"]["relaxed_pct"]["epoch3"]),
        tag="2_data_parallel/results/eval_summary.json",
    ))

    CTX["kicker"] = "LAB 4.2 (2_data_parallel/) · รอบ 2 ใบ · ช่วงลบเครื่อง (ขั้นที่ 3)"
    add(pslides("dp", "ขั้นที่ 3 ·", "LAB 4.2 ขั้นที่ 3 · สรุปผลและลบเครื่อง 2 GPU (ห้ามข้าม)"))

    CTX["kicker"] = "LAB 4.2 (2_data_parallel/gpu4/) · รอบ 4 ใบ · ช่วงสร้างเครื่อง (ขั้นที่ 4)"
    add(big(
        "ขยาย Data Parallelism เป็น 4 ใบในเครื่องเดียว: คาดว่าเร็วขึ้นเกือบ 2 เท่า แต่ batch ต่อใบเท่าเดิม",
        IMG_2 + "c-dp4.png",
        [
            "มีโมเดล 4 ชุดบน GPU 4 ใบในเครื่องเดียวกัน แต่ละใบได้ข้อมูลเพียง **1 ใน 4** (1,000 ตัวอย่างต่อ Epoch)",
            "คาดว่า **batch ต่อใบเท่าเดิม (4)** แต่ batch รวมเพิ่มเป็น 16 ทำให้จำนวน step ต่อ Epoch ลดลงครึ่งหนึ่งเหลือ **250 step**",
            "ความเร็วควรใกล้ 2 เท่าของ 2 ใบ แต่ไม่ถึง 2 เท่าพอดี เพราะต้องรอกันตอน All-reduce ข้าม 4 ใบและรอใบที่ช้าที่สุด",
        ],
    ))

    add(big(
        "ขั้นที่ 4: เช่าเครื่อง RTX 3090 4 ใบในเครื่องเดียว เก็บงานใน `2_data_parallel/gpu4/`",
        IMG_2 + "s1-four.png",
        [
            "เช่าเครื่องใหม่ 1 เครื่องที่มี **RTX 3090 4 ใบในเครื่องเดียว** ป้าย `vapp-lab4-dp4` และเก็บโค้ดกับผลแยกใน `2_data_parallel/gpu4/`",
            "ต้องตรวจให้ driver รองรับ CUDA 12.8 ด้วย ไม่ใช่ดูแค่รุ่น GPU (รอบจริงข้ามเครื่องที่รองรับแค่ CUDA 12.2)",
            "ใช้ `seed 0` แบ่ง 4,000 / 200 เพื่อให้ได้ Dataset ชุดเดียวกับส่วน 2 ใบสำหรับเทียบผล",
        ],
    ))

    add(pslides("dp", "ขั้นที่ 4 ·", "LAB 4.2 ขั้นที่ 4 · เช่าเครื่อง 4 GPU และเตรียมของ"))

    add(vastai_ready(
        "หลังรันขั้นที่ 4: เครื่องบน Vast.ai ถูกสร้างและพร้อมใช้งานแล้ว (1 เครื่อง × 4 GPU)",
        "vapp-lab4-dp4",
        "1 เครื่อง · RTX 3090 24 GB × 4 ใบ",
        [
            ("ตำแหน่งเครื่อง", "ชิลี · สถานะ **RUNNING** (พร้อมใน 436 วินาที)"),
            ("สเปก CPU / ระบบ", "2× Xeon E5-2680 v4 (56 cores) · PyTorch 2.8.0+cu128 · CUDA 12.8"),
            ("การเชื่อมระหว่าง GPU", "PCIe 3.0 x16 ไม่มี NVLink (GPU 0–1 และ GPU 2–3 อยู่ใต้ CPU เดียวกัน)"),
            ("หมายเหตุรอบจริง", "เครื่องแรกค้าง loading เกิน 10 นาที AI ลบและเปลี่ยนเครื่องให้เอง"),
        ],
        [
            "มองเห็น **RTX 3090 ครบทั้ง 4 ใบในเครื่องเดียว** (GPU 0 ถึง GPU 3)",
            "โหลดโมเดล **Qwen/Qwen3-8B (16.4 GB)** และแบ่งข้อมูล 4,000 / 200 เสร็จแล้ว",
            "บันทึกข้อมูลเครื่องและ topology ลง `gpu4/results/gpu_topology.txt`",
        ],
        "ช่วงสร้างเครื่องเสร็จแล้ว · ขั้นถัดไปคือ **ช่วงเทรน Data Parallelism 4 ใบ (ขั้นที่ 5)**",
        note("ตรวจให้แน่ใจว่าเครื่องป้าย `vapp-lab4-dp4` ขึ้นสถานะ **RUNNING** และโหลดของครบแล้ว จึงค่อยวางพรอมต์ขั้นที่ 5", "info"),
    ))

    CTX["kicker"] = "LAB 4.2 (2_data_parallel/gpu4/) · รอบ 4 ใบ · ช่วงเทรนและผลหลังเทรนเสร็จ (ขั้นที่ 5)"
    add(pslides("dp", "ขั้นที่ 5 ·", "LAB 4.2 ขั้นที่ 5 · เทรนแบบ Data Parallelism (4 GPU)"))

    add(nfig("n03-answer-loss", post=note("Data Parallelism 4 ใบเกิด Out of Memory สองรอบแรกที่ step 20–25 แม้เปิด `expandable_segments` แล้ว เพราะขอเพิ่ม 594 MiB ไม่ได้ การแก้ด้วย `AnswerLoss` ลดจุดพีคลงกว่า 1.4 GiB")))

    add(train_done(
        "หลังเทรน Data Parallelism 4 ใบครบ 3 Epoch: ค่าผลลัพธ์จริงที่แสดงเมื่อจบขั้นที่ 5",
        "LAB 4.2 · Data Parallelism (1 เครื่อง × RTX 3090 4 ใบ · vapp-lab4-dp4)",
        [
            ("batch ต่อ GPU / batch รวม", "4 ต่อใบ / รวม 16 (batch 8 ต่อใบเกิด Out of Memory ทั้ง 4 ใบ)", True),
            ("จำนวน step ต่อ Epoch", "250 step (รวม 750 step ใน %.1f นาที)" % DP4["train_minutes"], False),
            ("ความเร็วเฉลี่ย", "%.2f ตัวอย่างต่อวินาที (เร็วกว่า 2 ใบ %.2f เท่า)" % (DP4["examples_per_sec"], DP4["vs_2gpu"]["speedup"]), True),
            ("GPU utilization ทั้ง 4 ใบ", "%.1f / %.1f / %.1f / %.1f%%" % tuple(DP4["gpu_util_pct"]), False),
            ("VRAM สูงสุดตอนเทรน", "%.2f / %.2f / %.2f / %.2f GiB (หลังแก้ด้วย AnswerLoss)" % tuple(DP4["peak_vram_training_torch_gib"]), False),
        ],
        [
            ("Base (ก่อนเทรน)", "–", "%.4f" % DP4["test_loss_base"], "%.1f%%" % DP4["exact_match"]["strict_pct"]["base"]),
            ("หลัง Epoch 1", "%.4f" % DP4["train_loss_per_epoch"][0], "%.4f" % DP4["test_loss_per_epoch"][0], "%.1f%%" % DP4["exact_match"]["strict_pct"]["epoch1"]),
            ("หลัง Epoch 2", "%.4f" % DP4["train_loss_per_epoch"][1], "%.4f" % DP4["test_loss_per_epoch"][1], "%.1f%%" % DP4["exact_match"]["strict_pct"]["epoch2"]),
            ("หลัง Epoch 3", "%.4f" % DP4["train_loss_per_epoch"][2], "%.4f" % DP4["test_loss_per_epoch"][2], "%.1f%%" % DP4["exact_match"]["strict_pct"]["epoch3"]),
        ],
        note("เทรน 3 Epoch ใช้เวลาเพียง **5.6 นาที** (ลดลงจาก 10.5 นาทีในรอบ 2 ใบ) และ test loss ยังลดลงต่อเนื่องทุก Epoch"),
    ))

    add(E.hero(
        CTX["kicker"],
        "ผล Data Parallelism 4 ใบ: เร็วขึ้น %.2f ตัวอย่างต่อวินาที (%.2f× ของ 2 ใบ) · GPU utilization 97%% ทุกใบ" % (
            DP4["examples_per_sec"], DP4["vs_2gpu"]["speedup"]),
        IMG_SL + "h03-dp4.jpg",
        [
            ("ความเร็วเฉลี่ย 3 Epoch", "%.2f" % DP4["examples_per_sec"] + "<small>ตัวอย่างต่อวินาที</small>",
             "เร็วกว่า 2 ใบ %.2f เท่า (ประสิทธิภาพต่อใบ %.1f%%) · เทรน 3 Epoch ใน %.1f นาที" % (
                 DP4["vs_2gpu"]["speedup"], DP4["vs_2gpu"]["per_gpu_efficiency_pct"], DP4["train_minutes"]), "ok"),
            ("batch ต่อใบ / รวม", "%d / %d" % (DP4["batch_used"]["per_gpu"], DP4["batch_used"]["total"]),
             "250 step ต่อ Epoch · batch 8 ต่อใบยังเกิด Out of Memory ทั้ง 4 ใบ", ""),
            ("GPU utilization ทั้ง 4 ใบ", "%.1f–%.1f%%" % (min(DP4["gpu_util_pct"]), max(DP4["gpu_util_pct"])),
             "%.1f / %.1f / %.1f / %.1f%% · ทุกใบเร็วพอ ๆ กัน" % tuple(DP4["gpu_util_pct"]), "ok"),
        ],
        post=note("Exact Match เพิ่มขึ้นทุก Epoch (%.1f%% → %.1f%% → %.1f%%) และ test loss ยังลดลงต่อเนื่อง เพราะ batch รวม 16 ปรับน้ำหนักเพียง 250 ครั้งต่อ Epoch" % (
            DP4["exact_match"]["strict_pct"]["epoch1"],
            DP4["exact_match"]["strict_pct"]["epoch2"],
            DP4["exact_match"]["strict_pct"]["epoch3"])),
        tag="2_data_parallel/gpu4/results/summary.json",
    ))

    add(fig(
        "Data Parallelism 4 ใบ · หลังแก้ด้วย AnswerLoss VRAM ที่ batch 4 ลดลง แต่ batch 8 ยังเกิด Out of Memory ทั้ง 4 ใบ",
        P2 + "gpu4/results/images/vram_vs_batch.png",
        "ตอน probe หลังแก้ batch 4 ใช้ **21.25 GiB** ต่อใบ (PyTorch) และตอนเทรนจริงสูงสุด **20.61–21.63 GiB** ส่วน batch 8 ล้มทั้ง 4 ใบ",
        tag="2_data_parallel/gpu4/results/batch_probe.json",
    ))

    add(fig(
        "Data Parallelism 4 ใบ · GPU ทั้ง 4 ใบทำงานสม่ำเสมอ 96–98% ทุก Epoch",
        P2 + "gpu4/results/images/gpu_util.png",
        "แม้ GPU 0–1 และ GPU 2–3 อยู่คนละ CPU (เชื่อมข้ามคู่แบบ SYS ไม่มี NVLink) แต่ไม่มีใบใดช้ากว่าใบอื่นจนดึงทั้งระบบลง",
        tag="2_data_parallel/gpu4/results/train_metrics.json",
    ))

    add(fig(
        "Data Parallelism 4 ใบ · Exact Match เพิ่มขึ้นทุก Epoch ถึง %.1f%% (test loss ยังลดลงต่อ)" % DP4["exact_match"]["strict_pct"]["epoch3"],
        P2 + "gpu4/results/images/exact_match.png",
        "batch รวม 16 มีจำนวน Update น้อยกว่า 2 ใบครึ่งหนึ่งต่อ Epoch โมเดลจึงเรียนรู้ช้ากว่าต่อ Epoch แต่ยังไม่มีสัญญาณ overfit",
        tag="2_data_parallel/gpu4/results/summary.json",
    ))

    CTX["kicker"] = "LAB 4.2 (2_data_parallel/gpu4/) · รอบ 4 ใบ · ช่วงลบเครื่อง (ขั้นที่ 6) และสรุปเทียบ"
    add(pslides("dp", "ขั้นที่ 6 ·", "LAB 4.2 ขั้นที่ 6 · สรุปผลและลบเครื่อง 4 GPU (ห้ามข้าม)"))

    t_dp_cmp = filter_table(
        T("dp", "2 ใบเทียบ 4 ใบ", "สิ่งที่วัด"),
        drop_starts=("ราคาเครื่อง", "$ ต่อ", "ใบคิดเงิน", "VRAM สูงสุด", "test loss"),
    )
    add(tbl(
        "Data Parallelism 2 ใบเทียบ 4 ใบ (1 เครื่องต่อรอบ): เร็วขึ้น 1.87 เท่า และ batch ต่อใบยังเท่าเดิม",
        t_dp_cmp,
        post=note("สองส่วนเช่าเครื่องคนละโฮสต์และส่วน 4 ใบใช้ `AnswerLoss` ตัวเลข 1.87 เท่าจึงรวมความต่างของเครื่องไว้ด้วย · `*` 1.5% เมื่อตัด `;` ท้ายคำสั่งตามกติกาเดียวกับรอบ 4 ใบ"),
        tag="ตารางหลัก · LAB 4.2",
    ))

    # =========================================================================
    # 5 · LAB 4.3 · Model Parallelism (`3_model_parallel/` และ `gpu4/`, 1 เครื่อง × 2 และ 4 ใบ)
    # =========================================================================
    CTX.update(kicker="", group="LAB 4.3 · Model Parallelism (3_model_parallel/)")
    add(E.divider(
        "LAB 4.3",
        "Model Parallelism · โมเดลชุดเดียว แบ่ง Layer ลงหลายใบ",
        "<p>คำถาม: แบ่งโมเดล 1 ชุดลง GPU 2 ใบและ 4 ใบในเครื่องเดียวกัน จะรับ batch ได้ใหญ่แค่ไหน และความเร็วเปลี่ยนหรือไม่</p>"
        "<p class=\"dim\">โฟลเดอร์: <code>3_model_parallel/</code> (ขั้น 1–3 · 1 เครื่อง × 2 ใบ · 18+18 Layer) และ <code>3_model_parallel/gpu4/</code> (ขั้น 4–6 · 1 เครื่อง × 4 ใบ · ใบละ 9 Layer)</p>",
        img=IMG_SL + "s05-mp.jpg",
        small="ส่วนที่ 3 จาก 3 ของภาค LAB · โฟลเดอร์ 3_model_parallel/",
    ))

    CTX["kicker"] = "LAB 4.3 (3_model_parallel/) · แนวคิด Model Parallelism"
    add(big(
        "Model Parallelism: โมเดลชุดเดียวแบ่ง Layer ครึ่งแรกไว้ GPU 0 ครึ่งหลังไว้ GPU 1",
        IMG_3 + "c-mp.png",
        [
            "กำหนด `device_map` ให้ **GPU 0 ถือ embedding + Layer 0–17** และ **GPU 1 ถือ Layer 18–35 + norm + `lm_head`**",
            "ข้อมูลทุก batch เข้าที่ GPU 0 ส่งผลกลางทางผ่าน PCIe ไป GPU 1 แล้วคำนวณ loss ที่ GPU 1",
            "Weights ไม่ถูกทำซ้ำ แต่ละใบจึงถือแค่ครึ่งโมเดล (**7.64 GiB**) เหลือที่ว่าง VRAM มากขึ้น",
        ],
    ))

    add(big(
        "1 step ของ Model Parallelism: GPU ผลัดกันทำงาน มีเพียง 1 ใบที่คำนวณในแต่ละขณะ",
        IMG_3 + "c-mp-turns.png",
        [
            "**Forward** GPU 0 ทำครึ่งแรก (GPU 1 รอ) → ส่งผลกลางทางให้ GPU 1 ทำครึ่งหลัง + loss (GPU 0 รอ)",
            "**Backward** GPU 1 หา Gradient ครึ่งหลัง (GPU 0 รอ) → ส่งกลับให้ GPU 0 หา Gradient ครึ่งแรกแล้ว Update",
            "LAB นี้ไม่ได้ทำ Pipeline Parallelism จึงไม่มีการซ้อนงาน ความเร็วจะไม่เพิ่มขึ้นตามจำนวน GPU",
        ],
    ))

    add(big(
        "VRAM ของ Model Parallelism: Weights เท่ากันสองใบ แต่ GPU 1 ที่ถือ `lm_head` เต็มก่อน",
        IMG_3 + "vram-mp.png",
        [
            "Weights ก่อนเทรนเท่ากันใบละ **7.64 GiB** แต่ Activation ของ GPU 1 สูงกว่า GPU 0 ทุกขนาด batch และห่างขึ้นเป็นเท่าตัว",
            "เหตุผลคือ GPU 1 ถือ **`lm_head`** ที่ต้องสร้างตารางคะแนนของคำศัพท์ **151,936 คำ** สำหรับทุก token แล้วคิด loss",
            "ที่ batch 16 GPU 1 ขอจองเพิ่ม **2.32 GiB** (`16 × 256 × 151,936 × 4 byte`) ไม่ได้จึงเกิด Out of Memory ขณะที่ GPU 0 ยังว่าง",
        ],
    ))

    CTX["kicker"] = "LAB 4.3 (3_model_parallel/) · รอบ 2 ใบ · ช่วงสร้างเครื่อง (ขั้นที่ 1)"
    add(pslides("mp", "ขั้นที่ 1 ·", "LAB 4.3 ขั้นที่ 1 · เช่าเครื่อง 2 GPU และเตรียมของ"))

    add(vastai_ready(
        "หลังรันขั้นที่ 1: เครื่องบน Vast.ai ถูกสร้างและพร้อมใช้งานแล้ว (1 เครื่อง × 2 GPU)",
        "vapp-lab4-mp",
        "1 เครื่อง · RTX 3090 24 GB × 2 ใบ",
        [
            ("ตำแหน่งเครื่อง", "สหรัฐอเมริกา · สถานะ **RUNNING** (พร้อมใน 542 วินาที)"),
            ("สเปก CPU / ระบบ", "CPU Xeon (20 cores) · PyTorch 2.8.0+cu128 · CUDA 12.8 · disk 60 GB"),
            ("การเชื่อมระหว่าง GPU", "PCIe Gen3 x16 (`PHB` ใต้ CPU เดียวกัน) ไม่มี NVLink"),
            ("ไฟล์ผลที่สร้าง", "`rent.py` · `prepare.py` · `results/gpu_topology.txt`"),
        ],
        [
            "มองเห็น **RTX 3090 ครบทั้ง 2 ใบในเครื่องเดียว** (GPU 0 และ GPU 1)",
            "โหลดโมเดล **Qwen/Qwen3-8B (16.4 GB)** และแบ่งข้อมูล 4,000 / 200 เสร็จแล้ว",
            "พร้อมวางแผนแบ่ง Layer 0–17 ลง GPU 0 และ Layer 18–35 ลง GPU 1",
        ],
        "ช่วงสร้างเครื่องเสร็จแล้ว · ขั้นถัดไปคือ **ช่วงเทรน Model Parallelism 2 ใบ (ขั้นที่ 2)**",
        note("รอให้สถานะบน Vast.ai เป็น **RUNNING** และโหลดโมเดลเสร็จก่อน จึงค่อยวางพรอมต์ขั้นที่ 2 เพื่อเริ่มแบ่ง Layer และเทรน", "info"),
    ))

    CTX["kicker"] = "LAB 4.3 (3_model_parallel/) · รอบ 2 ใบ · ช่วงเทรนและผลหลังเทรนเสร็จ (ขั้นที่ 2)"
    add(pslides("mp", "ขั้นที่ 2 ·", "LAB 4.3 ขั้นที่ 2 · เทรนแบบ Model Parallelism (2 GPU)"))

    add(train_done(
        "หลังเทรน Model Parallelism 2 ใบครบ 3 Epoch: ค่าผลลัพธ์จริงที่แสดงเมื่อจบขั้นที่ 2",
        "LAB 4.3 · Model Parallelism (1 เครื่อง × RTX 3090 2 ใบ · vapp-lab4-mp)",
        [
            ("batch ใหญ่สุดที่เทรนได้", "%d (batch 16 เกิด Out of Memory ที่ GPU 1)" % MP2["batch_used"], True),
            ("จำนวน step ต่อ Epoch", "%d step (รวม 1,500 step ใน %.1f นาที)" % (MP2["steps_per_epoch"], MP2["train_minutes"]), False),
            ("ความเร็วเฉลี่ย", "%.2f ตัวอย่างต่อวินาที (%.3f วินาทีต่อ step)" % (MP2["examples_per_sec"], MP2["sec_per_step"]), True),
            ("GPU utilization ต่อใบ", "%.1f%% / %.1f%% (รวม %.1f%% · ผลัดกันทำงาน)" % (MP2["gpu_util_pct"][0], MP2["gpu_util_pct"][1], sum(MP2["gpu_util_pct"])), False),
            ("VRAM สูงสุดตอนเทรน", "%.2f / %.2f GiB (GPU 1 สูงกว่าเพราะ lm_head)" % (MP2["train_peak_allocated_gib"][0], MP2["train_peak_allocated_gib"][1]), False),
        ],
        [
            ("Base (ก่อนเทรน)", "–", "%.4f" % MP2["test_loss_base"], "1.5%*"),
            ("หลัง Epoch 1", "%.4f" % MP2["train_loss_per_epoch"][0], "%.4f" % MP2["test_loss_per_epoch"][0], "%.1f%%" % MP2["exact_match"]["strict"]["epoch1"]),
            ("หลัง Epoch 2", "%.4f" % MP2["train_loss_per_epoch"][1], "%.4f" % MP2["test_loss_per_epoch"][1], "%.1f%%" % MP2["exact_match"]["strict"]["epoch2"]),
            ("หลัง Epoch 3", "%.4f" % MP2["train_loss_per_epoch"][2], "%.4f" % MP2["test_loss_per_epoch"][2], "%.1f%%" % MP2["exact_match"]["strict"]["epoch3"]),
        ],
        note("รอบนี้ผ่าน batch 8 ได้ทันทีโดยไม่เกิด Out of Memory กลางทาง เพราะแต่ละใบถือ Weights เพียง 7.64 GiB · `*` ไม่นับ `;` ท้ายคำสั่ง"),
    ))

    add(E.hero(
        CTX["kicker"],
        "ผล Model Parallelism 2 ใบ: batch เพิ่มเป็น %d แต่ความเร็ว %.2f ตัวอย่างต่อวินาที เพราะผลัดกันทำ" % (
            MP2["batch_used"], MP2["examples_per_sec"]),
        IMG_SL + "h06-mp2.jpg",
        [
            ("batch ใหญ่สุดที่เทรนได้", "%d" % MP2["batch_used"],
             "2 เท่าของ Single GPU · batch 16 เกิด Out of Memory ที่ GPU 1 (ถือ `lm_head`)", "ok"),
            ("ความเร็วเฉลี่ย 3 Epoch", "%.2f" % MP2["examples_per_sec"] + "<small>ตัวอย่างต่อวินาที</small>",
             "%.3f วินาทีต่อ step ละ 8 ตัวอย่าง · เทรนรวม %.1f นาที" % (MP2["sec_per_step"], MP2["train_minutes"]), "warn"),
            ("GPU utilization ต่อใบ", "%.1f%% / %.1f%%" % (MP2["gpu_util_pct"][0], MP2["gpu_util_pct"][1]),
             "รวมกัน %.1f%% เท่ากับมี GPU ทำงาน 1 ใบตลอดเวลา · Exact Match สูงสุด %.1f%%" % (
                 sum(MP2["gpu_util_pct"]), MP2["exact_match"]["strict"]["epoch2"]), "bad"),
        ],
        post=note("ได้พื้นที่ VRAM เพิ่มขึ้นจริง (Weights เหลือใบละ 7.64 GiB) แต่ความเร็วไม่เพิ่มขึ้นตามจำนวนการ์ด เพราะสองใบผลัดกันคำนวณ"),
        tag="3_model_parallel/results/summary.json",
    ))

    add(fig(
        "Model Parallelism 2 ใบ · GPU 1 ใช้ VRAM มากกว่า GPU 0 ทุกขนาด batch และเกิด Out of Memory ก่อนที่ batch 16",
        P3 + "results/images/vram_vs_batch.png",
        "แบ่ง Layer 18/18 เท่ากันไม่ได้แปลว่า VRAM เท่ากัน · ตอนเทรนจริงที่ batch 8 PyTorch ใช้ **%.2f / %.2f GiB**" % (
            MP2["train_peak_allocated_gib"][0], MP2["train_peak_allocated_gib"][1]),
        tag="3_model_parallel/results/summary.json",
    ))

    add(fig(
        "Model Parallelism 2 ใบ · GPU utilization เฉลี่ย %.1f%% และ %.1f%% ยืนยันว่าทั้งสองใบผลัดกันทำงาน" % (
            MP2["gpu_util_pct"][0], MP2["gpu_util_pct"][1]),
        P3 + "results/images/gpu_util.png",
        "ผลรวม GPU utilization ทั้งสองใบได้ **%.1f%%** ตลอด 3 Epoch · ใช้เวลาเทรนรวม %.1f นาที (0.789 วินาทีต่อ step ละ 8 ตัวอย่าง)" % (
            sum(MP2["gpu_util_pct"]), MP2["train_minutes"]),
        tag="3_model_parallel/results/train_summary.json",
    ))

    add(fig(
        "Model Parallelism 2 ใบ · test loss ต่ำสุดที่ Epoch 2 (%.4f) และเริ่มขยับขึ้นที่ Epoch 3 (%.4f)" % (
            MP2["test_loss_per_epoch"][1], MP2["test_loss_per_epoch"][2]),
        P3 + "results/images/loss.png",
        "train loss ลดจาก **%.4f → %.4f → %.4f** ขณะที่ test loss นิ่งหลัง Epoch 2 แสดงว่าเริ่มอิ่มตัวแล้ว" % (
            MP2["train_loss_per_epoch"][0], MP2["train_loss_per_epoch"][1], MP2["train_loss_per_epoch"][2]),
        tag="3_model_parallel/results/train_summary.json",
    ))

    add(fig(
        "Model Parallelism 2 ใบ · Exact Match ดีที่สุดที่ Epoch 2 (%.1f%%) และทรงตัวที่ %.1f%% ใน Epoch 3" % (
            MP2["exact_match"]["strict"]["epoch2"], MP2["exact_match"]["strict"]["epoch3"]),
        P3 + "results/images/exact_match.png",
        "Base %.1f%% (1.5%% เมื่อไม่นับ `;` ท้าย · แบบผ่อนปรน %.1f%%) → หลัง Fine-tune ได้ **%.1f%% / %.1f%% / %.1f%%**" % (
            MP2["exact_match"]["strict"]["base"],
            MP2["exact_match"]["relaxed"]["base"],
            MP2["exact_match"]["strict"]["epoch1"],
            MP2["exact_match"]["strict"]["epoch2"],
            MP2["exact_match"]["strict"]["epoch3"]),
        tag="3_model_parallel/results/summary.json",
    ))

    CTX["kicker"] = "LAB 4.3 (3_model_parallel/) · รอบ 2 ใบ · ช่วงลบเครื่อง (ขั้นที่ 3)"
    add(pslides("mp", "ขั้นที่ 3 ·", "LAB 4.3 ขั้นที่ 3 · สรุปผลและลบเครื่อง 2 GPU (ห้ามข้าม)"))

    CTX["kicker"] = "LAB 4.3 (3_model_parallel/gpu4/) · รอบ 4 ใบ · ช่วงสร้างเครื่อง (ขั้นที่ 4)"
    add(big(
        "ขยาย Model Parallelism เป็น 4 ใบในเครื่องเดียว: แบ่ง 36 Layer เป็นใบละ 9 Layer เรียงจาก GPU 0 ถึง 3",
        IMG_3 + "c-mp4.png",
        [
            "GPU 0 ถือ `embed` + Layer 0–8 · GPU 1 ถือ 9–17 · GPU 2 ถือ 18–26 · **GPU 3 ถือ 27–35 + norm + `lm_head`**",
            "ข้อมูลส่งต่อเป็นสายพาน 4 สถานี (ข้าม PCIe 3 ครั้ง) ทำให้ยังมีเพียง **1 ใบ** ที่คำนวณในแต่ละขณะ",
            "คาดว่า GPU utilization ต่อใบจะลดเหลือราว **25%** ความเร็วเท่าเดิมหรือช้าลงเล็กน้อย และใบที่ช้าที่สุดจะกำหนดความเร็วทั้งสาย",
        ],
    ))

    add(big(
        "VRAM แบบ 4 ใบ: Weights เหลือ 3.2–4.4 GiB ต่อใบ แต่ GPU 3 ที่ถือ `lm_head` ยังเต็มก่อน",
        IMG_3 + "vram-mp4.png",
        [
            "Weights ต่อใบลดลงเกือบครึ่ง ทำให้รับ **batch ใหญ่สุดเพิ่มเป็น 16** (2 เท่าของแบบ 2 ใบ)",
            "GPU 1 และ GPU 2 ใช้ VRAM เพียง **9.7 GiB** ตอนเทรน batch 16 เหลือที่ว่างอีกราว 14 GiB",
            "แต่ **GPU 3** พุ่งไป 17.5 GiB และที่ batch 32 ขอเพิ่ม **4.64 GiB** (`32 × 256 × 151,936 × 4 byte`) จนเกิด Out of Memory",
        ],
    ))

    add(big(
        "ขั้นที่ 4: เช่าเครื่อง 4 GPU ในเครื่องเดียว เก็บงานใน `3_model_parallel/gpu4/` และวัดความเร็วทีละใบ",
        IMG_3 + "s1-four.png",
        [
            "เช่าเครื่อง RTX 3090 4 ใบในเครื่องเดียว ป้าย `vapp-lab4-mp4` เก็บโค้ดและผลใน `3_model_parallel/gpu4/`",
            "เพิ่ม **ขั้นที่ 5 ในพรอมต์**: วัดความเร็ว GPU ทีละใบด้วยงานเดียวกัน เพราะใน Model Parallelism ใบที่ช้าสุดจะถ่วงทั้งสาย",
            "ตั้งเกณฑ์ชัด: ถ้ามีใบไหนช้ากว่าใบที่เร็วที่สุด **เกิน 20%** ให้ลบและเปลี่ยนเครื่องทันที",
        ],
    ))

    add(pslides("mp", "ขั้นที่ 4 ·", "LAB 4.3 ขั้นที่ 4 · เช่าเครื่อง 4 GPU และวัดความเร็วทีละใบ"))

    add(vastai_ready(
        "หลังรันขั้นที่ 4: เครื่องบน Vast.ai ถูกสร้างและผ่านเกณฑ์ความเร็วแล้ว (1 เครื่อง × 4 GPU)",
        "vapp-lab4-mp4",
        "1 เครื่อง · RTX 3090 24 GB × 4 ใบ",
        [
            ("ตำแหน่งเครื่อง", "ชิลี · สถานะ **RUNNING**"),
            ("สเปก CPU / ระบบ", "2× Xeon E5-2680 v4 (56 cores) · PyTorch 2.8.0+cu128 · CUDA 12.8"),
            ("การเชื่อมระหว่าง GPU", "PCIe Gen3 x16 ไม่มี NVLink (GPU 0–1 และ GPU 2–3 อยู่คนละ CPU)"),
            ("ผลเช็กความเร็ว GPU", "ใบช้าสุด (GPU 2) ช้ากว่าใบเร็วสุดเพียง **%.1f%%** (ผ่านเกณฑ์ ≤ 20%%)" % MP4["gpu_speed_check"]["worst_slower_pct"]),
        ],
        [
            "มองเห็น **RTX 3090 ครบทั้ง 4 ใบในเครื่องเดียว** และผ่านการทดสอบความเร็วทีละใบ",
            "โหลดโมเดล **Qwen/Qwen3-8B (16.4 GB)** และแบ่งข้อมูล 4,000 / 200 เสร็จแล้ว",
            "บันทึกผลทดสอบความเร็วและ topology ลง `gpu4/results/gpu_bench.json`",
        ],
        "ช่วงสร้างเครื่องและตรวจความเร็วเสร็จแล้ว · ขั้นถัดไปคือ **ช่วงเทรน Model Parallelism 4 ใบ (ขั้นที่ 5)**",
        note("ดูรายละเอียดคะแนนความเร็วของ GPU ทั้ง 4 ใบในหน้าถัดไป ก่อนเข้าสู่พรอมต์ขั้นที่ 5 เพื่อเริ่มเทรน", "info"),
    ))

    t_bench = T("mp", "ขั้นที่ 4 ·", "GPU")
    add(tbl(
        "ผลวัดความเร็ว GPU ทีละใบ: GPU 2 ช้ากว่า GPU 3 อยู่ %.1f%% ผ่านเกณฑ์ไม่เกิน 20%%" % MP4["gpu_speed_check"]["worst_slower_pct"],
        t_bench,
        post=note("ทดสอบทั้งการคูณเมทริกซ์ FP16 (8192×8192) และ train step ของ Transformer 1 ชั้น (ช้าสุดต่างเพียง 5.9%) จึงใช้เครื่องนี้เทรนต่อได้", "ok"),
        tag="3_model_parallel/gpu4/results/gpu_bench.json",
    ))

    CTX["kicker"] = "LAB 4.3 (3_model_parallel/gpu4/) · รอบ 4 ใบ · ช่วงเทรนและผลหลังเทรนเสร็จ (ขั้นที่ 5)"
    add(pslides("mp", "ขั้นที่ 5 ·", "LAB 4.3 ขั้นที่ 5 · เทรนแบบ Model Parallelism (4 GPU)"))

    add(train_done(
        "หลังเทรน Model Parallelism 4 ใบครบ 3 Epoch: ค่าผลลัพธ์จริงที่แสดงเมื่อจบขั้นที่ 5",
        "LAB 4.3 · Model Parallelism (1 เครื่อง × RTX 3090 4 ใบ · vapp-lab4-mp4)",
        [
            ("batch ใหญ่สุดที่เทรนได้", "%d (batch 32 เกิด Out of Memory ที่ GPU 3)" % MP4["batch_used"], True),
            ("จำนวน step ต่อ Epoch", "%d step (รวม 750 step ใน %.1f นาที)" % (MP4["steps_per_epoch"], MP4["train_minutes"]), False),
            ("ความเร็วเฉลี่ย", "%.2f ตัวอย่างต่อวินาที (%.3f วินาทีต่อ step)" % (MP4["examples_per_sec"], MP4["sec_per_step"]), True),
            ("GPU utilization ทั้ง 4 ใบ", "%.1f / %.1f / %.1f / %.1f%% (รวม %.1f%%)" % (
                MP4["gpu_util_pct"][0], MP4["gpu_util_pct"][1], MP4["gpu_util_pct"][2], MP4["gpu_util_pct"][3], sum(MP4["gpu_util_pct"])), False),
            ("VRAM สูงสุดตอนเทรน", "%.2f / %.2f / %.2f / %.2f GiB (GPU 3 สูงสุด)" % tuple(MP4["train_peak_allocated_gib"]), False),
        ],
        [
            ("Base (ก่อนเทรน)", "–", "%.4f" % MP4["test_loss_base"], "%.1f%%" % MP4["exact_match"]["strict"]["base"]),
            ("หลัง Epoch 1", "%.4f" % MP4["train_loss_per_epoch"][0], "%.4f" % MP4["test_loss_per_epoch"][0], "%.1f%%" % MP4["exact_match"]["strict"]["epoch1"]),
            ("หลัง Epoch 2", "%.4f" % MP4["train_loss_per_epoch"][1], "%.4f" % MP4["test_loss_per_epoch"][1], "%.1f%%" % MP4["exact_match"]["strict"]["epoch2"]),
            ("หลัง Epoch 3", "%.4f" % MP4["train_loss_per_epoch"][2], "%.4f" % MP4["test_loss_per_epoch"][2], "%.1f%%" % MP4["exact_match"]["strict"]["epoch3"]),
        ],
        note("ขยาย batch ได้เป็น **16** (4 เท่าของ GPU ใบเดียว) แต่ความเร็วยังอยู่ที่ **9.91 ตัวอย่างต่อวินาที** เพราะทั้ง 4 ใบผลัดกันทำงานทีละใบ"),
    ))

    add(E.hero(
        CTX["kicker"],
        "ผล Model Parallelism 4 ใบ: batch ใหญ่ขึ้นเป็น %d แต่ความเร็วยังเท่าเดิมที่ %.2f ตัวอย่างต่อวินาที" % (
            MP4["batch_used"], MP4["examples_per_sec"]),
        IMG_SL + "h04-mp4.jpg",
        [
            ("batch ใหญ่สุดที่เทรนได้", "%d" % MP4["batch_used"],
             "2 เท่าของแบบ 2 ใบ · batch 32 เกิด Out of Memory ที่ GPU 3 (ขอเพิ่ม 4.64 GiB)", "ok"),
            ("ความเร็วเฉลี่ย 3 Epoch", "%.2f" % MP4["examples_per_sec"] + "<small>ตัวอย่างต่อวินาที</small>",
             "%.2f เท่าของ 2 ใบ · %.3f วินาทีต่อ step · เทรนรวม %.1f นาที" % (
                 MP4["speed_vs_2gpu_run"], MP4["sec_per_step"], MP4["train_minutes"]), "warn"),
            ("GPU utilization ต่อใบ", "%.1f–%.1f%%" % (min(MP4["gpu_util_pct"]), max(MP4["gpu_util_pct"])),
             "%.1f / %.1f / %.1f / %.1f%% · รวมกัน %.1f%% (ทำงานทีละใบ)" % (
                 MP4["gpu_util_pct"][0], MP4["gpu_util_pct"][1],
                 MP4["gpu_util_pct"][2], MP4["gpu_util_pct"][3], sum(MP4["gpu_util_pct"])), "bad"),
        ],
        post=note("ใช้ทรัพยากร GPU 4 ใบ แต่ได้ปริมาณงานต่อวินาทีเท่ากับ GPU 1 ใบ จึงควรใช้เมื่อจำเป็นต้องใช้พื้นที่ VRAM จริง ๆ เท่านั้น"),
        tag="3_model_parallel/gpu4/results/summary.json",
    ))

    add(fig(
        "Model Parallelism 4 ใบ · VRAM ไม่สมดุลชัด: GPU 3 สูงกว่าใบอื่นทุกขนาด batch และชนเพดาน 24 GB ที่ batch 32",
        P3 + "gpu4/results/images/vram_vs_batch.png",
        "กราฟแสดง VRAM ที่ PyTorch จองตอน probe · ตอนเทรนจริงที่ batch 16 (allocated) GPU 0–3 ใช้ **%.2f / %.2f / %.2f / %.2f GiB** โดย `lm_head` กองอยู่ที่ใบสุดท้าย" % tuple(
            MP4["train_peak_allocated_gib"]),
        tag="3_model_parallel/gpu4/results/summary.json",
    ))

    add(fig(
        "Model Parallelism 4 ใบ · GPU utilization ลดเหลือ 22–30% ต่อใบ โดย GPU 3 หนักสุดเพราะ `lm_head`",
        P3 + "gpu4/results/images/gpu_util.png",
        "ผลรวม GPU utilization ของทั้ง 4 ใบคือ **%.1f%%** ยืนยันตามทฤษฎีว่าข้อมูลไหลทีละสถานี ไม่ได้คำนวณพร้อมกัน" % sum(MP4["gpu_util_pct"]),
        tag="3_model_parallel/gpu4/results/train.json",
    ))

    add(fig(
        "Model Parallelism 4 ใบ · Exact Match ดีที่สุดที่ Epoch 2 (%.1f%%) แล้วลดลงเป็น %.1f%% ใน Epoch 3" % (
            MP4["exact_match"]["strict"]["epoch2"], MP4["exact_match"]["strict"]["epoch3"]),
        P3 + "gpu4/results/images/exact_match.png",
        "Base %.1f%% → Epoch 1: **%.1f%%** → Epoch 2: **%.1f%%** → Epoch 3: **%.1f%%** · test loss ต่ำสุดที่ Epoch 2 (%.4f → %.4f)" % (
            MP4["exact_match"]["strict"]["base"],
            MP4["exact_match"]["strict"]["epoch1"],
            MP4["exact_match"]["strict"]["epoch2"],
            MP4["exact_match"]["strict"]["epoch3"],
            MP4["test_loss_per_epoch"][1],
            MP4["test_loss_per_epoch"][2]),
        tag="3_model_parallel/gpu4/results/eval_all.json",
    ))

    CTX["kicker"] = "LAB 4.3 (3_model_parallel/gpu4/) · รอบ 4 ใบ · ช่วงลบเครื่อง (ขั้นที่ 6) และสรุปเทียบ"
    add(pslides("mp", "ขั้นที่ 6 ·", "LAB 4.3 ขั้นที่ 6 · สรุปผลและลบเครื่อง 4 GPU (ห้ามข้าม)"))

    t_mp_cmp = filter_table(
        T("mp", "2 ใบเทียบ 4 ใบ", "สิ่งที่วัด"),
        drop_starts=("ราคาเครื่อง", "$ ต่อ", "ใบคิดเงิน", "test loss"),
    )
    add(tbl(
        "Model Parallelism 2 ใบเทียบ 4 ใบ (1 เครื่องต่อรอบ): batch เพิ่ม 2 เท่า ความเร็วเท่าเดิม และใบสุดท้ายยังเต็มก่อน",
        t_mp_cmp,
        post=note("การส่งผลกลางทางข้ามใบเพิ่มจาก 1 เป็น 3 ครั้งแทบไม่ทำให้ช้าลง แต่ GPU ที่ว่างรอเพิ่มจาก 1 เป็น 3 ใบ · `*` 1.5% เมื่อตัด `;` ท้ายคำสั่งตามกติกาเดียวกับรอบ 4 ใบ"),
        tag="ตารางหลัก · LAB 4.3",
    ))

    # =========================================================================
    # 6 · บทสรุปทั้ง 3 แล็บ: ความต่าง · ผลการทดลองจริง · แนวทางเลือกใช้
    # =========================================================================
    CTX.update(kicker="", group="บทสรุปทั้ง 3 LAB · ความต่างและผลการทดลอง")
    add(E.divider(
        "บทสรุป LAB 4",
        "ทั้ง 3 แล็บต่างกันอย่างไร และผลการทดลองจริงบอกอะไร",
        "<p>สรุปเทียบ LAB 4.1 Single GPU · LAB 4.2 Data Parallelism · LAB 4.3 Model Parallelism (ทั้งหมดรันบนเครื่องเดียว 1 / 2 / 4 GPU) แบบครบทุกมิติ</p>",
        img=IMG_SL + "s06-summary.jpg",
        small="บทสรุปของทั้ง 3 LAB ย่อย",
    ))

    CTX["kicker"] = "บทสรุป · เทียบทั้ง 3 LAB"
    add(E.hero(
        CTX["kicker"],
        "สรุปความต่างทั้ง 3 แล็บ: 4.1 จุดตั้งต้น · 4.2 ซื้อความเร็ว · 4.3 ซื้อที่ว่าง VRAM",
        IMG_SL + "h12-3labs-summary.jpg",
        [
            ("LAB 4.1 · Single GPU (`1_single_gpu/`)", "1 ใบ",
             "1 เครื่อง × 1 ใบ · batch สูงสุด **4** · เร็ว **8.5 ตัวอย่างต่อวินาที** · GPU utilization 97% (ชนเพดานทั้งสองด้าน)", ""),
            ("LAB 4.2 · Data Parallelism (`2_data_parallel/`)", "เร็ว 1.87×",
             "1 เครื่อง × 2 และ 4 ใบ · แบ่งข้อมูลทำพร้อมกัน · เร็ว **19.1 → 35.6 ตัวอย่างต่อวินาที** (GPU utilization 97–99%) · batch ต่อใบยังเป็น 4", "ok"),
            ("LAB 4.3 · Model Parallelism (`3_model_parallel/`)", "batch 4×",
             "1 เครื่อง × 2 และ 4 ใบ · แบ่ง Layer ของโมเดลชุดเดียว · batch ขยาย **8 → 16** แต่ผลัดกันทำ ความเร็วคงที่ **10.1 / 9.9 ตัวอย่างต่อวินาที**", "warn"),
        ],
        post=note("ทั้ง 3 แล็บเช่า 1 เครื่องต่อรอบ ใช้โมเดล Dataset และค่าเทรนเดียวกันทุกประการ ความต่างของผลทั้งหมดเกิดจากวิธีจัดวางบน GPU"),
        tag="สรุป 3 LAB ย่อย",
    ))

    add(fig(
        "ผลจริงทั้ง 5 กรณีในภาพเดียว: เพิ่มใบใน Data Parallelism ได้ความเร็ว · เพิ่มใบใน Model Parallelism ได้ขนาด batch",
        IMG_S + "r-compare.png",
        "เทียบ 1 เครื่อง × 1 ใบ (Single GPU) · 1 เครื่อง × 2 และ 4 ใบ (Data Parallelism) · 1 เครื่อง × 2 และ 4 ใบ (Model Parallelism)",
        tag="สรุปผลจริง 5 กรณี",
    ))

    t_all = filter_table(
        T("ov", "ผลการทดลองจริงทั้ง 5 กรณี", "ค่าที่วัด"),
        drop_starts=("ราคาเครื่อง", "เงินต่อ", "วินาทีต่อ step", "Exact Match: Base"),
    )
    add(tbl(
        "ตารางสรุปตัวเลขวัดจริงทั้ง 5 กรณี: เทียบ Weights, Batch, ความเร็ว, VRAM, GPU utilization และ Exact Match",
        t_all,
        post=note("Exact Match ปรับเป็นกติกาเดียวกันทุกแบบ (ไม่นับ `;` ท้ายคำสั่งเป็นข้อผิด) · Base ทุกแบบได้ 1.5% เท่ากัน"),
        tag="ตารางหลัก · 5 แบบ",
    ))

    add(E.hero(
        CTX["kicker"],
        "ผลด้านความเร็ว: Data Parallelism เร็วขึ้นถึง 35.6 ตัวอย่างต่อวินาที ส่วน Model Parallelism คงที่ราว 10",
        IMG_SL + "h07-speed-battle.jpg",
        [
            ("Single GPU (1 เครื่อง × 1 ใบ)", "%.1f" % S1["examples_per_sec"] + "<small>ตัวอย่างต่อวินาที</small>",
             "batch 4 · GPU utilization 97.0% · เทรน 3 Epoch ใช้ 23.6 นาที", ""),
            ("Data Parallelism (1 เครื่อง × 2 → 4 ใบ)", "%.1f → %.1f" % (DP2["examples_per_sec"], DP4["examples_per_sec"]),
             "ตัวอย่างต่อวินาที · 4 ใบเร็วกว่า 2 ใบ **1.87 เท่า** (ประสิทธิภาพต่อใบ 93.4% · GPU utilization 97–99%)", "ok"),
            ("Model Parallelism (1 เครื่อง × 2 → 4 ใบ)", "%.1f → %.1f" % (MP2["examples_per_sec"], MP4["examples_per_sec"]),
             "ตัวอย่างต่อวินาที · เพิ่มใบไม่เร็วขึ้น เพราะผลัดกันทำ (GPU utilization รวมทุกใบ ~100% เสมอ)", "bad"),
        ],
        post=note("เพราะ LoRA ส่ง Gradient แค่ ~15 MB/step Data Parallelism จึงขยายความเร็วได้เกือบเป็นเส้นตรงแม้ไม่มี NVLink"),
        tag="สรุปด้านความเร็ว",
    ))

    add(E.hero(
        CTX["kicker"],
        "ผลด้าน VRAM และ Batch: Model Parallelism ขยาย batch เป็น 4 → 8 → 16 แต่ `lm_head` เต็มก่อนเสมอ",
        IMG_SL + "h08-vram-battle.jpg",
        [
            ("Single GPU & Data Parallelism", "4 ต่อใบ",
             "ทุกใบต้องถือ Weights 15.3 GiB ครบชุด · batch 8 ต่อใบเกิด Out of Memory เหมือนกัน (Data Parallelism ได้แค่ batch รวม 8 และ 16)", "warn"),
            ("Model Parallelism (1 เครื่อง × 2 → 4 ใบ)", "8 → 16",
             "Weights ต่อใบลดเหลือ 7.6 และ 3.2–4.4 GiB · รับ batch ใหญ่ขึ้น 2× และ 4× ของการ์ดใบเดียว", "ok"),
            ("คอขวดของใบสุดท้าย", "lm_head",
             "ตารางคะแนน 151,936 คำศัพท์กองอยู่ที่ใบสุดท้ายใบเดียว (ขอเพิ่ม 2.32 / 4.64 GiB ที่ batch 16 / 32)", "bad"),
        ],
        post=note("บทเรียนร่วม: แม้ probe จะผ่านแบบเฉียดขีด (< 1 GiB) เทรนจริงยังเกิด Out of Memory ได้จาก `attention_mask` หรือ logits จึงต้องเผื่อที่ว่างหรือใช้ `AnswerLoss`"),
        tag="สรุปด้าน VRAM",
    ))

    add(E.hero(
        CTX["kicker"],
        "ผลด้านคุณภาพหลัง 3 Epoch: ทุกวิธีได้ Exact Match 74.5–79.0% ใกล้กันหมด",
        IMG_SL + "h09-quality-epoch.jpg",
        [
            ("ก่อนเทรน (Base)", "1.5%",
             "ต่ำเพราะสไตล์ quote และตัวพิมพ์ (แบบผ่อนปรนได้ 52.5–54.5%)", ""),
            ("หลังเทรน 3 Epoch (ทั้ง 5 แบบ)", "74.5–79.0%",
             "Single GPU 77.5% · Data Parallelism 79.0% / 76.5% · Model Parallelism 77.0% / 74.5%", "ok"),
            ("จังหวะที่คุ้มที่สุด", "Epoch 2",
             "3 จาก 5 แบบได้ค่าดีสุดที่ Epoch 2 · batch ใหญ่ (16) ปรับน้ำหนักแค่ 250 ครั้งต่อ Epoch จึงเริ่มช้ากว่าใน Epoch 1", "warn"),
        ],
        post=note("การจัดวางบน GPU เปลี่ยนความเร็วและที่ว่าง VRAM ไม่ได้เปลี่ยนสิ่งที่โมเดลเรียนรู้ · Test Set 200 ข้อ (1 ข้อ = 0.5 จุด) ส่วนต่าง 1–2 จุดจึงยังสรุปไม่ได้ว่าแบบใดแม่นกว่า"),
        tag="สรุปด้านคุณภาพ",
    ))

    add(E.hero(
        CTX["kicker"],
        "แนวทางเลือกใช้งานจริง: ดูให้ชัดว่างานของคุณติดความเร็ว หรือติด VRAM",
        IMG_SL + "h10-choose-verdict.jpg",
        [
            ("ใส่ใบเดียวได้และไม่รีบ", "Single GPU",
             "ง่ายที่สุดและคุ้มค่าต่อตัวอย่างที่สุด (`1_single_gpu/`)", ""),
            ("ใส่ใบเดียวได้ แต่อยากเสร็จเร็ว", "Data Parallelism",
             "เพิ่ม GPU ในเครื่องเดียวแล้วได้ความเร็วเพิ่มเกือบเท่าตัว (`2_data_parallel/`)", "ok"),
            ("โมเดลหรือ batch ใส่ใบเดียวไม่ลง", "Model Parallelism",
             "รวม VRAM หลายใบในเครื่องเดียวมาถือโมเดลเดียว · ถ้าอยากได้ทั้งสองอย่างให้ใช้ร่วมกันข้ามเครื่องใน LAB 5 (`3_model_parallel/`)", "warn"),
        ],
        post=note("ในเชิงทรัพยากร Data Parallelism คุ้มค่าเพราะการ์ดทำงานเต็มทุกใบ ส่วน Model Parallelism มีการ์ดว่างรอจึงควรใช้เมื่อจำเป็นต้องใช้พื้นที่ VRAM จริง ๆ"),
        tag="แนวทางตัดสินใจ",
    ))

    t_choose = T("ov", "เลือกใช้แบบไหนดี", "สถานการณ์")
    add(tbl(
        "ตารางตัดสินใจเลือกใช้ทั้ง 4 สถานการณ์ (รวมการใช้ร่วมกันข้ามเครื่องใน LAB 5)",
        t_choose,
        post=note("ใช้ตารางนี้เช็กก่อนเช่าเครื่องทุกครั้ง เพื่อไม่ให้เช่า GPU หลายใบผิดวิธี"),
        tag="ตารางหลัก · การเลือกใช้",
    ))

    add(nfig("n04-caveats"))

    CTX.update(kicker="", group="บทสรุปทั้ง 3 LAB · ความต่างและผลการทดลอง")
    add(statement(
        "จบ LAB 4",
        IMG_SL + "s06-summary.jpg",
        "4.1 จุดตั้งต้น · 4.2 ซื้อความเร็ว · 4.3 ซื้อที่ว่าง VRAM",
        "ทุกการทดลองใน LAB 4 คือ **Multi-GPU ในเครื่องเดียว (1 เครื่อง · หลาย GPU)** — เลือกวิธีให้ตรงคอขวด วัด VRAM ด้วยตัวอย่างยาวสุดก่อนเทรนจริง และ **ลบเครื่องเช่าทุกครั้งที่จบงาน**",
        links_html=(
            '<a href="README.md" target="_blank">หน้ารวม LAB 4</a>'
            '<a href="1_single_gpu/README.md" target="_blank">LAB 4.1 (1_single_gpu/)</a>'
            '<a href="2_data_parallel/README.md" target="_blank">LAB 4.2 (2_data_parallel/)</a>'
            '<a href="3_model_parallel/README.md" target="_blank">LAB 4.3 (3_model_parallel/)</a>'
        ),
    ))

    return E.write(E.SL, OUT, TITLE)


if __name__ == "__main__":
    for st in (sys.stdout, sys.stderr):
        if hasattr(st, "reconfigure"):
            st.reconfigure(encoding="utf-8", errors="replace")
    build()
