#!/usr/bin/env python3
"""สร้างสไลด์ LAB5_Cluster_Slides.html ของ LAB 5 (เทรน LLM บนคลัสเตอร์: 1 Node เทียบ 2 Node เทียบ 3 Node)

  python tools/build_slides.py            (รันจากโฟลเดอร์ lab5_cluster)

LAB 5 มี 3 README (หน้ารวม · 1_data_parallel · 2_model_parallel)
ลำดับการนำเสนอ:
  1. เริ่มต้น: ปก · แผนที่เส้นทาง (ImageGen) · แผนที่โฟลเดอร์ (1 Node LAB 4 / 5.1 / 5.2) · 1 Node vs 2 Node · 2 แบบบนคลัสเตอร์ · ตารางเทียบ 2 แบบ · ตัวแปรควบคุม
  2. พื้นฐานร่วมของคลัสเตอร์: Dataset & โมเดล Qwen3-8B · LoRA 15.3 MB · Coordinator 1 port · ต้นทุนสื่อสาร PCIe vs อินเทอร์เน็ต · Speedup & Efficiency · สูตรประมาณเวลาส่งก่อนเทรน
  3. LAB 5.1 · Data Parallelism บนคลัสเตอร์ (`1_data_parallel/` และ `node3/`, 2 Node & 3 Node · 6 ขั้น):
     แนวคิด DP ข้ามเครื่อง → ส่วน 2 Node (ขั้น 1–3, ผลเน็ต, แก้ OOM padding, ผลจริง Hero & กราฟ) → ส่วน 3 Node (ขั้น 4–6, ผลเน็ต 3 ประเทศ, บั๊ก socket buffer, ผลจริง Hero & กราฟ) → เทียบ 1 vs 2 vs 3 Node
  4. LAB 5.2 · Model Parallelism บนคลัสเตอร์ (`2_model_parallel/` และ `node3/`, 2 Node & 3 Node · 6 ขั้น):
     แนวคิด MP ในเครื่อง + ข้ามเครื่อง + รอ 2 ชั้น → ส่วน 2 Node (ขั้น 1–3, ผลเน็ต 82 Mbps, 4 สาย TCP + กู้คืนจาก checkpoint หลังโฮสต์ reboot, การแบ่ง Layer & VRAM, ผลจริง Hero & กราฟ) → ส่วน 3 Node (ขั้น 4–6, เน็ตแกว่ง 2 รอบ, ใครรอใคร ส่ง/รอ/รับ, ผลจริง Hero & กราฟ) → เทียบ 1 vs 2 vs 3 Node
  5. บทสรุปทั้ง 2 LAB:
     ผลรวมทั้ง 2 แบบ · ตารางเทียบ 1 vs 2 vs 3 Node · Hero คอขวดเครือข่าย & ศักยภาพถ้าเน็ตเร็วพอ · Hero คุณภาพโมเดล & LoRA Sync · 5 บทเรียนหน้างานจริง · แนวทางตัดสินใจเมื่อไรควรใช้คลัสเตอร์ · ข้อจำกัด · จบ LAB 5

ข้อกำหนด:
- ทั้งเด็คอยู่ในกรอบ 80–100 หน้า
- แนวคิดของแต่ละเรื่องอยู่หน้าขั้นของ LAB ที่ใช้
- ไม่มีหน้าวิธีใช้สไลด์ · ไม่มีหน้ากล่องข้อความล้วน · ไม่มีหน้าตรวจผลของคุณ
- ไม่แสดงราคา ค่าเช่า หรือยอดที่ถูกคิดของเครื่องในหน้าผลและหน้าสรุป (พรอมต์ของทั้ง 2 แล็บคัดลอกตรงตัวอักษรจาก README ครบทั้ง 12 กล่อง)
- ตัวเลขผลทุกตัวอ่านจาก README และไฟล์ results/summary.json ของทั้ง 4 รอบตอนสร้างไฟล์
"""
import json, os, posixpath, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import slides_engine as E
from slides_engine import md, CTX, add, note, fig, explain, tbl, plain
from slides_figures import FIGS

S = E.slide
FIG = {f["img"]: f for f in FIGS}
OUT, TITLE = "LAB5_Cluster_Slides.html", "LAB 5 · เทรน LLM บนคลัสเตอร์ (DP · MP · 2 & 3 Node) · Slides"

P1, P2 = "1_data_parallel/", "2_model_parallel/"
IMG_OV, IMG_1, IMG_2, IMG_SL = (
    "image/",
    "1_data_parallel/image/",
    "2_model_parallel/image/",
    "image/slides/",
)

# ------------------------------------------------------------------ layout เพิ่มของเด็คนี้ (ไม่แก้ engine)
E.CSS += r"""
.ex.big .fig{flex:2.25 1 0}
.ex.mid2 .fig{flex:1.95 1 0}
.slide.stmt{padding:0;color:#fff}
.stmt img.bg{position:absolute;inset:0;width:100%;height:100%;object-fit:cover}
.stmt .shade{position:absolute;inset:0;background:linear-gradient(90deg,rgba(6,13,26,.95) 0%,rgba(6,13,26,.82) 52%,rgba(6,13,26,.18) 88%)}
.stmt .inner{justify-content:center;max-width:1060px}
.stmt .q{font-size:48px;font-weight:700;line-height:1.32;color:#fff}
.stmt .sub2{margin-top:28px;font-size:25px;line-height:1.6;color:#d6e4fb}
.stmt .sub2 b{color:#ffd28a}
.stmt .links{margin-top:26px;font-size:21px;line-height:1.7;color:#b9d2f5}
.stmt .links a{color:#8fe0dc;border-bottom-color:rgba(143,224,220,.45);margin-right:18px;white-space:nowrap}
.stmt .imgnote{bottom:60px}
.inner .dim{color:#9fb6dd;font-size:.9em}
.divider .inner .small{margin-bottom:22px}
.inner h1{line-height:1.32}
.slide.hero .tag{color:#ffd28a;text-shadow:0 1px 4px #000,0 0 10px rgba(0,0,0,.95),0 0 20px rgba(0,0,0,.98);padding:2px 8px;border-radius:4px;background:rgba(6,13,26,.55)}
.slide.hero code{background:rgba(255,255,255,.16);color:#fff}
.slide.hero .tiles.hl .num{font-size:2.1em}
.slide th a{color:#fff}
.slide.pslide .hd{margin-bottom:10px;padding-bottom:8px}
.slide.pslide .pbar{margin-bottom:6px}
.slide.pslide pre.code.prompt{font-size:.63em;line-height:1.36;padding:.65em .95em}
"""


# ------------------------------------------------------------------ อ่าน README 3 ไฟล์
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
    "dp": list(E.load("1_data_parallel/README.md", relink("1_data_parallel"))),
    "mp": list(E.load("2_model_parallel/README.md", relink("2_model_parallel"))),
}

DP2 = json.loads(E.read("1_data_parallel/results/summary.json"))
DP3 = json.loads(E.read("1_data_parallel/node3/results/summary.json"))
MP2 = json.loads(E.read("2_model_parallel/results/summary.json"))
MP3 = json.loads(E.read("2_model_parallel/node3/results/summary.json"))


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


def filter_table(t, drop_starts=(), keep_starts=None, replace_cells=None):
    rows = []
    for r in t["rows"]:
        c0 = plain(r[0])
        if keep_starts is not None and not any(c0.startswith(p) for p in keep_starts):
            continue
        if any(c0.startswith(p) for p in drop_starts):
            continue
        nr = list(r)
        if replace_cells:
            for old, new in replace_cells:
                nr = [c.replace(old, new) for c in nr]
        rows.append(nr)
    return {"t": "table", "head": list(t["head"]), "rows": rows}


def pslides(doc, prefix, title, how="คัดลอกแล้ววางใน Claude Code ที่โฟลเดอร์ 02_VastAi_Application"):
    """แสดงพรอมต์ทั้งหมดในหน้าเดียว (ไม่แบ่งส่วนที่ 1/2) พร้อมปุ่มคัดลอกข้อความตรงตัวอักษรจาก README"""
    use(doc)
    alert = E.prompt_code(prefix, 0, how)
    code = next(x for x in alert["blocks"] if x["t"] == "code")
    text = code["text"]
    pid = "prompt%d" % len(E.PROMPTS)
    E.PROMPTS.append(text)
    lines = text.split("\n")
    label = "พรอมต์ทั้งหมด %d บรรทัด" % len(lines)
    body = ('<div class="pbar"><span class="how">%s</span><span class="plabel">%s</span>'
            '<button class="copy big" data-full="%s">คัดลอกพรอมต์ทั้งหมด</button></div>'
            '<pre class="code prompt"><span class="t">%s</span></pre>') % (
        E.inline(how), label, pid, E.esc(text))
    return [E.S(CTX["kicker"], "พรอมต์ · " + title, body, tag="Copy &amp; Paste", cls="pslide", maxfs=1.35)]


# ------------------------------------------------------------------ ชิ้นส่วนช่วย
def big(title, src, points, post="", cls="big"):
    """ภาพใหญ่ด้านซ้าย + ข้อพูดเรียงเลข 3-4 ข้อด้านขวา"""
    s = explain(title, src, points, post)
    s["body"] = s["body"].replace('<div class="ex">', '<div class="ex %s">' % cls, 1)
    return s


def nfig(key, post=""):
    f = FIG[key]
    return big(f["title"], IMG_SL + "%s.jpg" % key, f["steps"], post=post, cls="mid2")


def statement(title, photo, q, sub, links_html=""):
    """ประโยคปิดบนภาพถ่ายเต็มหน้า"""
    lk = '<div class="links">%s</div>' % links_html if links_html else ""
    raw = ('<img class="bg" src="%s" alt="%s"><div class="shade"></div><div class="inner">'
           '<div class="q">%s</div><div class="sub2">%s</div>%s</div>'
           '<div class="imgnote">ภาพจำลอง</div>') % (photo, E.esc(title), md(q), md(sub), lk)
    return {"raw": raw, "cls": "stmt", "style": "", "title": title, "kicker": "", "tag": "", "lead": ""}


def avg_util(d):
    vals = [v for arr in d["gpu_util_pct"].values() for v in arr]
    return sum(vals) / len(vals), min(vals), max(vals)


def build():
    E.SL[:] = []
    E.PROMPTS[:] = []

    # =========================================================================
    # 1 · เริ่มต้น: ภาพรวมของ LAB 5 · แผนที่โฟลเดอร์ · 2 แบบบนคลัสเตอร์
    # =========================================================================
    CTX.update(kicker="", group="เริ่มต้น · ภาพรวมและแผนที่โฟลเดอร์")
    add(E.cover(
        "LAB 5 · เทรน LLM บนคลัสเตอร์หลายเครื่อง",
        "1 เครื่อง (1 Node) เทียบ 2 เครื่อง (2 Node) เทียบ 3 เครื่อง (3 Node) · เครื่องละ 2 GPU ต่อกันผ่านอินเทอร์เน็ต",
        IMG_SL + "s01-cover.jpg",
        small="02_VastAi_Application / lab5_cluster · 1 Node = เครื่องคอมพิวเตอร์ 1 เครื่อง (GPU 2 ใบ)",
    ))

    CTX["kicker"] = "ภาพรวมของ LAB 5"
    add(fig(
        "เส้นทางของทั้งบท: จาก 1 เครื่อง (1 Node) สู่คลัสเตอร์ 2–3 เครื่อง (หลาย Node) ผ่านอินเทอร์เน็ต",
        IMG_SL + "s07-lab5-journey.jpg",
        "**1 Node = เครื่องคอมพิวเตอร์ 1 เครื่อง (เครื่องละ 2 GPU)** · นำหลายเครื่องมาต่อกันเรียกว่า **คลัสเตอร์** — เทียบ 1, 2 และ 3 Node ทั้งแบบ Data Parallelism และ Model Parallelism",
        tag="ภาพจำลอง",
    ))

    add(nfig("n01-lab5-folders"))

    add(big(
        "1 Node คืออะไร และคลัสเตอร์หลายเครื่องต่างจาก LAB 4 อย่างไร",
        IMG_OV + "why-cluster.png",
        [
            "**1 Node = เครื่องคอมพิวเตอร์ 1 เครื่อง** (ใน LAB นี้ทุกเครื่องเสียบ **GPU 2 ใบ** คือ RTX 3090 × 2) · เมื่อนำหลายเครื่องมาต่อกันผ่านเครือข่ายเรียกว่า **คลัสเตอร์**",
            "**LAB 4** ใช้ **1 เครื่อง (1 Node)** GPU คุยกันในเครื่องผ่าน PCIe · **LAB 5** ขยายเป็น **2 เครื่อง (2 Node = 4 GPU)** และ **3 เครื่อง (3 Node = 6 GPU)** ต่อกันผ่านอินเทอร์เน็ต",
            "**1 Node ไม่ต้องรันใหม่** ใช้ผล 1 เครื่อง (GPU 2 ใบ) ของ LAB 4.2 และ LAB 4.3 เป็นตัวเทียบ เพื่อวัดว่าเพิ่มเครื่องแล้วเร็วขึ้นกี่เท่า และเวลา 1 step หมดไปกับอะไร",
        ],
    ))

    add(big(
        "คลัสเตอร์ 2 เครื่อง (2 Node · 4 GPU) ใช้ได้ 2 แบบ ต่างกันที่การจัดวางโมเดลในแต่ละเครื่อง",
        IMG_OV + "c-two-ways.png",
        [
            "**LAB 5.1 · Data Parallelism** 2 เครื่อง (GPU 4 ใบ) ทุกใบถือโมเดลครบชุด รวม **4 ชุด** แบ่งข้อมูลใบละ 1/4",
            "**LAB 5.2 · Model Parallelism** 2 เครื่อง (GPU 4 ใบ) แต่ละเครื่องวางโมเดล 1 ชุดคร่อม GPU 2 ใบ รวม **2 ชุด** แบ่งข้อมูลเครื่องละครึ่ง",
            "**ข้ามเครื่องทำเหมือนกันทั้งสองแบบ** คือส่งเฉพาะ **Gradient ของ LoRA** ผ่านอินเทอร์เน็ตไปเฉลี่ยที่โปรแกรมกลาง (**Coordinator**) บน Node 1",
        ],
    ))

    t_labs = T("ov", "LAB ย่อย 2 แบบ", "LAB ย่อย")
    add(tbl(
        "สรุปโครงสร้าง LAB 5.1 และ LAB 5.2: ในเครื่องทำอะไร ข้ามเครื่องทำอะไร และเทียบกับใคร",
        t_labs,
        post=note("ทั้งสอง LAB ย่อยใช้ Coordinator แบบ Synchronous บน Node 1 เหมือนกัน · รอบ 2 Node เก็บที่รากโฟลเดอร์ และรอบ 3 Node เก็บใน `node3/`", "info"),
        tag="ตารางหลัก · 2 LAB ย่อย",
    ))

    t_same = filter_table(
        T("ov", "สิ่งที่เหมือนกันทั้ง 2 LAB ย่อย", "หัวข้อ"),
        replace_cells=[
            (" · ไม่เกิน $0.60 ต่อชั่วโมงต่อเครื่อง", ""),
            (" · เงินต่อ 1,000 ตัวอย่าง", ""),
        ],
    )
    add(tbl(
        "ตัวแปรควบคุมที่ตรึงเหมือนกันทั้ง 2 LAB ย่อย เพื่อให้เทียบกับ 1 Node ได้ตรงไปตรงมา",
        t_same,
        post=note("แต่ละ LAB ย่อยมี **6 ขั้น ทุกขั้นคือ 1 พรอมต์** (ขั้น 1–3 ใช้ 2 Node · ขั้น 4–6 ใช้ 3 Node) และลบเครื่องทุก Node ในขั้นที่ 3 และ 6 เสมอ", "info"),
        tag="ค่าที่ตรึง",
    ))

    # =========================================================================
    # 2 · พื้นฐานร่วมของคลัสเตอร์: โจทย์เดิม · LoRA · Coordinator · ต้นทุนเครือข่าย
    # =========================================================================
    CTX.update(kicker="", group="พื้นฐานร่วม · โจทย์เดิมและกลไกข้ามเครื่อง")
    add(E.divider(
        "พื้นฐานร่วม",
        "โจทย์เดิมจาก LAB 4 และกลไกหลักของคลัสเตอร์",
        "<p>ก่อนเริ่มเช่าคลัสเตอร์ ต้องเข้าใจ 4 เรื่องร่วม: ข้อมูลและ LoRA 15.3 MB · Coordinator 1 port · ต้นทุนสื่อสารข้ามอินเทอร์เน็ต · และวิธีวัด Speedup</p>",
        img=IMG_SL + "s02-foundations.jpg",
        small="ใช้ร่วมกันทั้ง LAB 5.1 และ LAB 5.2",
    ))

    CTX["kicker"] = "พื้นฐานร่วม · Dataset และโมเดล"
    add(big(
        "งานเดิมจาก LAB 4: เทรน `Qwen3-8B` บน `sql-create-context` (4,000 / 200)",
        IMG_1 + "d-example.png",
        [
            "Dataset `b-mc2/sql-create-context` (78,577 ตัวอย่าง) สับด้วย **`seed 0`** แบ่งเป็น Training Set **4,000** และ Test Set **200**",
            "**ทุก Node ต้องได้ชุดข้อมูลเดียวกัน** ถ้าแบ่งไม่ตรงกัน บาง Node จะเทรนด้วยข้อสอบที่อีก Node ใช้ประเมิน",
            "โมเดล `Qwen/Qwen3-8B` (`bf16`, 36 Layer, 8.19B params) ปิดโหมด thinking เทรน **2 Epoch** วัด Exact Match บน Test Set 200 ข้อ",
        ],
    ))

    add(big(
        "ทำไมคลัสเตอร์นี้ส่งข้ามเครื่องแค่ ~15 MB ต่อ step แทนที่จะเป็น 16 GB",
        IMG_1 + "t-lora-qv.png",
        [
            "LoRA ล็อกน้ำหนักเดิมทั้งหมด แล้วเทรนเฉพาะตารางเล็ก (`r=8`, `alpha=16`) ที่ `q_proj` กับ `v_proj` ครบ 36 Layer = **72 จุด**",
            "จำนวนพารามิเตอร์ที่เทรนมีเพียง **3,833,856 ค่า** (0.047% ของโมเดล) สิ่งที่ต้องส่งข้ามเครื่องทุก step จึงมีเฉพาะ Gradient ส่วนนี้",
            "Gradient 1 ชุดแบบ `float32` = `3,833,856 × 4 byte` = **15.3 MB** (วัดได้ 15,335,424 byte) — ถ้าส่งแบบ `bf16` เหลือครึ่งเดียวคือ **7.67 MB**",
        ],
    ))

    CTX["kicker"] = "พื้นฐานร่วม · กลไกข้ามเครื่อง"
    add(big(
        "Coordinator: โปรแกรมกลางบน Node 1 เปิด port เดียวให้ทุก Worker ต่อเข้ามา",
        IMG_1 + "c-coordinator.png",
        [
            "ข้ามเครื่องเช่า GPU มองไม่เห็นกันโดยตรง และเครื่องเช่าเปิดรับพอร์ตภายนอกได้จำกัด จึงให้ **Node 1 เปิด 1 port** แล้วทุก Worker ต่อออกไปหา",
            "ทำงานแบบ **Synchronous** 3 ขั้น: (1) รอ Gradient ครบทุก Worker → (2) เฉลี่ย → (3) ส่งค่าเฉลี่ยเดียวกันกลับให้ทุกตัว Update พร้อมกัน",
            "ข้อดีคือน้ำหนัก LoRA ของทุก Worker **เท่ากันทุกค่าเสมอ** แต่ทั้งคลัสเตอร์จะเดินได้เร็วเท่า **Worker ที่ช้าที่สุด** เท่านั้น",
        ],
    ))

    add(big(
        "ต้นทุนการสื่อสาร: ในเครื่องวิ่งผ่าน PCIe แต่ข้ามเครื่องต้องผ่านอินเทอร์เน็ตทุก step",
        IMG_1 + "c-net-cost.png",
        [
            "ในเครื่องเดียว (LAB 4) GPU ส่ง Gradient ผ่าน PCIe ถนนสั้นและกว้าง ถึงเกือบทันทีจนแทบไม่เห็นเวลารอ",
            "ข้ามเครื่อง (LAB 5) Gradient เดินทางผ่านอินเทอร์เน็ตสาธารณะ ช้ากว่ามากและขึ้นกับทั้ง **RTT** (เวลาไปกลับ) และ **ความเร็วส่งข้อมูล**",
            "ระหว่างที่รอส่งและรับ Gradient กลับ **GPU จะว่างไม่ได้คำนวณ** จึงต้องวัดเน็ตระหว่าง Node เองก่อนเริ่มเทรนทุกครั้ง",
        ],
    ))

    add(big(
        "วัดความคุ้มของการเพิ่มเครื่องด้วย Speedup และ Efficiency",
        IMG_OV + "c-speedup.png",
        [
            "**Speedup** = ตัวอย่างต่อวินาทีของ N Node ÷ ตัวอย่างต่อวินาทีของ 1 Node (อุดมคติ = N เท่า)",
            "**Efficiency** = Speedup ÷ N (อุดมคติ = 100% แปลว่าเพิ่มเครื่องแล้วได้งานเต็มตามจำนวนเครื่อง)",
            "ถ้า **Speedup ต่ำกว่า 1** แปลว่าเพิ่มเครื่องแล้ว **ช้าลง** เพราะเวลาส่งและรอผ่านเครือข่ายยาวกว่าเวลาคำนวณที่แบ่งเบาได้",
        ],
    ))

    add(nfig("n02-comm-math"))

    # =========================================================================
    # 3 · LAB 5.1 · Data Parallelism บนคลัสเตอร์ (`1_data_parallel/` และ `node3/`)
    # =========================================================================
    CTX.update(kicker="", group="LAB 5.1 · Data Parallelism บนคลัสเตอร์")
    add(E.divider(
        "LAB 5.1",
        "Data Parallelism บนคลัสเตอร์ · 2 Node และ 3 Node",
        "<p>คำถาม: ให้ GPU ทุกใบข้ามเครื่องถือโมเดลครบชุด (4 และ 6 โมเดล) แบ่งข้อมูลกันเทรน จะเร็วขึ้นกี่เท่าเทียบกับ 1 Node ของ LAB 4.2</p>"
        "<p class=\"dim\">โฟลเดอร์: <code>1_data_parallel/</code> (ขั้น 1–3 · 2 Node = 4 GPU) และ <code>1_data_parallel/node3/</code> (ขั้น 4–6 · 3 Node = 6 GPU)</p>",
        img=IMG_SL + "s03-dp-cluster.jpg",
        small="ส่วนที่ 1 จาก 2 ของภาค LAB · โฟลเดอร์ 1_data_parallel/",
    ))

    CTX["kicker"] = "LAB 5.1 (1_data_parallel/) · แนวคิด DP ข้าม 2 Node"
    add(big(
        "Data Parallelism ข้าม 2 Node: โมเดล 4 ชุด แบ่งข้อมูลใบละ 1/4 แล้วเฉลี่ยที่ Node 1",
        IMG_1 + "c-dp-cluster.png",
        [
            "เปิด Worker **1 ตัวต่อ GPU** รวม 4 ตัว (โมเดล 4 ชุด) ตรึง `batch = 4` ต่อ GPU เท่า LAB 4.2 ทำให้ **batch รวม = 16** (250 step/Epoch)",
            "ทุกใบคำนวณบนข้อมูลคนละส่วนไม่ซ้ำกัน แล้วส่ง Gradient ของ LoRA ไปยัง Coordinator บน Node 1",
            "GPU 4 ใบคำนวณพร้อมกันได้ แต่ทุกตัวต้องหยุดรอให้ Gradient จาก Node 2 เดินทางข้ามอินเทอร์เน็ตมาถึงครบก่อน",
        ],
    ))

    add(big(
        "1 step ของ DP ข้าม 2 Node: เวลาต่อ step = เวลาคำนวณ + เวลาส่งและรอ",
        IMG_1 + "c-dp-cluster-step.png",
        [
            "**ช่วงคำนวณ** (Forward + Backward + Update) ทำพร้อมกันทั้ง 4 ใบ ใช้เวลาพอ ๆ กับ 1 Node (ราว 0.4 วินาที)",
            "**ช่วงส่งและรอ** Worker ทั้ง 4 ส่ง Gradient ไป Coordinator รอเฉลี่ย และรับค่าเฉลี่ยกลับ (2 เส้นของ Node 2 ข้ามอินเทอร์เน็ต)",
            "เพราะเป็น Synchronous แม้ Worker ของ Node 1 จะอยู่เครื่องเดียวกับ Coordinator ก็ต้องรอ Node 2 ด้วยทุก step",
        ],
    ))

    CTX["kicker"] = "LAB 5.1 (1_data_parallel/) · ส่วนที่ 1: 2 Node (ขั้นที่ 1–3)"
    add(big(
        "ขั้นที่ 1: เช่า 2 Node เตรียมโมเดลกับ Dataset และวัดเน็ตระหว่างเครื่องก่อนเทรน",
        IMG_1 + "s1-two-nodes.png",
        [
            "เช่า 2 เครื่องที่มี **IP สาธารณะต่างกัน** (RTX 3090 × 2 ต่อเครื่อง) ป้าย `vapp-lab5-dp-1` และ `vapp-lab5-dp-2` โดย Node 1 เปิด 1 port",
            "โหลด `Qwen3-8B` และแบ่ง `sql-create-context` (4,000 / 200 ด้วย `seed 0`) ให้ตรงกันทั้ง 2 Node",
            "วัดว่า Node 2 ต่อเข้า port ของ Node 1 ได้หรือไม่ พร้อมวัด **RTT** และความเร็วส่งข้อมูลทั้งสองทิศ (ถ้า RTT > 100 ms ให้เปลี่ยนเครื่อง)",
        ],
    ))

    add(pslides("dp", "ขั้นที่ 1 ·", "LAB 5.1 ขั้นที่ 1 · เช่า 2 Node เตรียมของ และวัดเน็ต"))

    dp2_net = DP2["network"][0]
    add(E.hero(
        CTX["kicker"],
        "ผลวัดเน็ต DP 2 Node (ไต้หวันทั้งคู่): RTT ต่ำแค่ %.2f ms แต่ส่งขึ้นได้เพียง %.0f Mbps" % (
            dp2_net["rtt_ms_avg"], dp2_net["mbps_node2_to_node1"]),
        IMG_SL + "h01-dp2-net.jpg",
        [
            ("RTT เฉลี่ยระหว่าง Node", "%.2f ms" % dp2_net["rtt_ms_avg"],
             "สองเครื่องอยู่ไต้หวันเหมือนกัน และ Node 2 ต่อเข้า port ของ Node 1 ได้ปกติ", "ok"),
            ("ขาขึ้น Node 2 → Node 1", "%.0f Mbps" % dp2_net["mbps_node2_to_node1"],
             "ต่ำกว่า 700 Mbps ที่หน้าเช่าประกาศไว้มาก · ทิศนี้ใช้ส่ง Gradient ของ 2 Worker ขึ้น", "bad"),
            ("ขาลง Node 1 → Node 2", "%.0f Mbps" % dp2_net["mbps_node1_to_node2"],
             "เร็วกว่าขาขึ้นกว่า 5 เท่า แต่คอขวดอยู่ที่ทิศที่ช้ากว่าเสมอ", "warn"),
        ],
        post=note("บทเรียนสำคัญ: ตัวเลขความเร็วในหน้าเช่าคือความเร็วออกอินเทอร์เน็ตของแต่ละเครื่อง ไม่ใช่ความเร็วระหว่างสองเครื่องที่เช่ามา **ต้องวัดเอง**"),
        tag="1_data_parallel/results/network.json",
    ))

    add(big(
        "ขั้นที่ 2 ทำอะไร: 5 งานต่อเนื่องในพรอมต์เดียว เพื่อจับเวลาคำนวณเทียบส่งและรอ",
        IMG_1 + "s2-flow-cluster.png",
        [
            "AI เขียน `coordinator.py` และ `worker.py` (4 ตัว) แล้ว **ลอง 3 step ด้วย batch ที่มี padding** ก่อนเทรนจริง",
            "เทรน 2 Epoch (500 step) พร้อมแยกเวลาคำนวณกับเวลาส่ง/รอทุก step และตรวจว่าน้ำหนัก LoRA ทั้ง 4 ตัวเท่ากันหลังจบทุก Epoch",
            "เขียน `eval.py` วัด Exact Match บน Test Set 200 ข้อของ Base และหลังจบ Epoch 1 และ 2",
        ],
    ))

    add(pslides("dp", "ขั้นที่ 2 ·", "LAB 5.1 ขั้นที่ 2 · เทรนแบบ Data Parallelism ข้าม 2 Node"))

    add(nfig("n03-dp-oom"))

    dp2_u_avg, dp2_u_min, dp2_u_max = avg_util(DP2)
    add(E.hero(
        CTX["kicker"],
        "ผล DP 2 Node: ได้ %.2f ตัวอย่าง/วิ · ส่งและรอ %.0f%% ของ step · GPU util เหลือ %.1f%%" % (
            DP2["examples_per_sec"], DP2["comm_share_pct"], dp2_u_avg),
        IMG_SL + "h02-dp2-res.jpg",
        [
            ("ความเร็วเฉลี่ย 2 Epoch", "%.2f" % DP2["examples_per_sec"] + "<small>ตัวอย่าง/วินาที</small>",
             "ช้ากว่า 1 Node (19.08) ราว 4 เท่า · Speedup = **0.24** · เทรน 500 step ใน %.1f นาที" % DP2["train_minutes"], "bad"),
            ("เวลาต่อ step เฉลี่ย", "%.2f วิ" % DP2["sec_per_step"],
             "คำนวณ **%.2f วิ (12%%)** · ส่งและรอ **%.2f วิ (%.0f%%)** · ค่ากลาง %.2f วิ" % (
                 DP2["compute_sec_per_step"], DP2["comm_sec_per_step"], DP2["comm_share_pct"], DP2["sec_per_step_median"]), "warn"),
            ("GPU util / Exact Match", "%.1f%% / %.1f%%" % (dp2_u_avg, DP2["exact_match_pct"]["epoch2"]),
             "GPU 4 ใบทำงานเพียง %.1f–%.1f%% · แต่น้ำหนัก LoRA เท่ากันทุกค่า (Epoch 2 = %.1f%%)" % (
                 dp2_u_min, dp2_u_max, DP2["exact_match_pct"]["epoch2"]), "ok"),
        ],
        post=note("ส่ง Gradient แบบ `float32` เต็ม (15.34 MB ต่อ Worker ทั้งขาขึ้นและขาลง) · Epoch 1 เน็ตสะดุดได้ 3.63 ตัวอย่าง/วิ ส่วน Epoch 2 เน็ตนิ่งขึ้นได้ 5.92"),
        tag="1_data_parallel/results/summary.json",
    ))

    add(fig(
        "DP 2 Node · 88% ของทุก step คือแถบสีส้ม (ส่งและรอ) และมีช่วงเน็ตค้างพุ่งถึง 19 วิ",
        P1 + "results/images/step_time.png",
        "ด้านซ้าย: แถบสีน้ำเงิน (คำนวณ 0.43 วิ) บางติดก้นกราฟ ส่วนช่วง step 120–200 เน็ตสะดุด 16 step (สูงสุด 44 วิ) · ด้านขวา: Worker ทั้ง 4 ตัวรอเท่ากัน",
        tag="1_data_parallel/results/metrics.json",
    ))

    add(fig(
        "DP 2 Node · GPU ทั้ง 4 ใบอยู่ที่ 0% เกือบตลอดเวลา เฉลี่ยเพียง 12.4–12.8%",
        P1 + "results/images/gpu_util.png",
        "เทียบกับ 1 Node ใน LAB 4.2 ที่ GPU util ราว **98%** · เมื่อรอเน็ตข้ามเครื่อง การ์ดจะพุ่งขึ้น 100% เป็นจังหวะสั้น ๆ แล้วหล่นกลับไปรอที่ 0%",
        tag="1_data_parallel/results/train/",
    ))

    add(fig(
        "DP 2 Node · Loss ลดลงราบรื่นตลอด 500 step แสดงว่าการเฉลี่ยข้ามเครื่องทำงานถูกต้อง",
        P1 + "results/images/loss.png",
        "train loss ลดจาก **%.4f → %.4f** · test loss ลดจาก Base **%.4f** เหลือ **%.4f** และ **%.4f** หลังจบ Epoch 1 และ 2" % (
            DP2["train_loss_per_epoch"][0], DP2["train_loss_per_epoch"][1],
            DP2["test_loss_base"], DP2["test_loss_per_epoch"][0], DP2["test_loss_per_epoch"][1]),
        tag="1_data_parallel/results/metrics.json",
    ))

    add(fig(
        "DP 2 Node · Exact Match พุ่งจาก %.1f%% เป็น %.1f%% และจบ Epoch 2 ที่ %.1f%%" % (
            DP2["exact_match_pct"]["base"], DP2["exact_match_pct"]["epoch1"], DP2["exact_match_pct"]["epoch2"]),
        P1 + "results/images/exact_match.png",
        "ใกล้เคียงกับ 1 Node (77.5% หลัง Epoch 2) ต่างกัน 5 ข้อจาก 200 · น้ำหนัก LoRA ของ Worker ทั้ง 4 ตัวตรงกันทุกค่าหลังจบทั้ง 2 Epoch",
        tag="1_data_parallel/results/summary.json",
    ))

    add(pslides("dp", "ขั้นที่ 3 ·", "LAB 5.1 ขั้นที่ 3 · สรุปผลและลบเครื่องทั้ง 2 Node (ห้ามข้าม)"))

    CTX["kicker"] = "LAB 5.1 (1_data_parallel/node3/) · ส่วนที่ 2: 3 Node (ขั้นที่ 4–6)"
    add(big(
        "ขยาย DP จาก 2 Node เป็น 3 Node (6 โมเดล): batch รวมเป็น 24 แต่ต้องรอครบ 6 ตัว",
        IMG_1 + "c-dp-cluster3.png",
        [
            "เพิ่มเป็น **3 Node (GPU 6 ใบ, โมเดล 6 ชุด)** ทำให้ batch รวมเพิ่ม 1.5 เท่าเป็น **24** (ลดเหลือ 167 step/Epoch)",
            "เวลาคำนวณต่อ step ควรใกล้เดิม (batch ต่อ GPU ยังเป็น 4) แต่ Coordinator ต้องรับ Gradient 6 ชุดและรอตัวที่ช้าที่สุดจาก 6 ตัว",
            "**คำถามชี้วัด**: ถ้าเวลาต่อ step นานขึ้นเกิน 1.5 เท่า การเพิ่มเป็น 3 Node จะไม่เร็วขึ้นเลย",
        ],
    ))

    add(big(
        "ขั้นที่ 4: เช่า 3 Node ให้ใกล้กัน เตรียมของ และวัดเน็ตทั้ง 2 เส้นทางเข้า Node 1",
        IMG_1 + "s1-three-nodes.png",
        [
            "เช่า 3 เครื่อง IP ต่างกัน ป้าย `vapp-lab5-3dp-1`, `vapp-lab5-3dp-2`, `vapp-lab5-3dp-3` เก็บงานแยกใน `1_data_parallel/node3/`",
            "หา 3 เครื่องที่อยู่ใกล้กันยากกว่า 2 เครื่อง รอบจริง AI เลือกชุดที่ถูกที่สุดในยุโรป 3 ประเทศ (**เอสโตเนีย · บัลแกเรีย · โรมาเนีย**)",
            "วัดเน็ตทั้งเส้น `Node 2 ↔ Node 1` และ `Node 3 ↔ Node 1` โดยตั้งเกณฑ์ RTT ไม่เกิน 100 ms เช่นเดิม",
        ],
    ))

    add(pslides("dp", "ขั้นที่ 4 ·", "LAB 5.1 ขั้นที่ 4 · เช่า 3 Node เตรียมของ และวัดเน็ต"))

    t_dp3_net = T("dp", "ขั้นที่ 4 ·", "เส้นทาง")
    add(tbl(
        "ผลวัดเน็ต DP 3 Node (ยุโรป 3 ประเทศ): RTT 74–81 ms ผ่านเกณฑ์ แต่ขาลงไป Node 3 เหลือ 73.2 Mbps",
        t_dp3_net,
        post=note("เส้นทางที่ช้าที่สุดคือ **Node 1 → Node 3 (73.2 Mbps)** · ค่าเฉลี่ย Gradient ขนาด 15.34 MB ที่ส่งกลับ Node 3 ต้องผ่านเส้นนี้ทุก step และทั้งคลัสเตอร์ต้องรอ"),
        tag="node3/results/network_*.json",
    ))

    add(pslides("dp", "ขั้นที่ 5 ·", "LAB 5.1 ขั้นที่ 5 · เทรนแบบ Data Parallelism ข้าม 3 Node"))

    add(nfig("n04-socket-bug", post=note("รอบ 3 Node นี้ AI แปลง Gradient ขาขึ้นเป็น `bf16` (7.67 MB) เอง ทำให้ขนาดเล็กลงครึ่งหนึ่ง แต่ขาลงยังส่ง `float32` เต็ม (15.34 MB)")))

    dp3_u_avg, dp3_u_min, dp3_u_max = avg_util(DP3)
    add(E.hero(
        CTX["kicker"],
        "ผล DP 3 Node: ได้ %.2f ตัวอย่าง/วิ (เท่า 2 Node) — ส่งและรอ %.0f%%, GPU util %.1f%%" % (
            DP3["examples_per_sec"], DP3["comm_share_pct"], dp3_u_avg),
        IMG_SL + "h03-dp3-res.jpg",
        [
            ("ความเร็วเฉลี่ย 2 Epoch", "%.2f" % DP3["examples_per_sec"] + "<small>ตัวอย่าง/วินาที</small>",
             "batch รวมเพิ่ม 1.5× แต่เวลาต่อ step เพิ่ม 1.5× ด้วย · Speedup ยังเป็น **0.24** (Efficiency **8%**)", "bad"),
            ("เวลาต่อ step เฉลี่ย", "%.2f วิ" % DP3["sec_per_step"],
             "คำนวณ **%.2f วิ (7%%)** · ส่งและรอ **%.2f วิ (%.0f%%)** · ค่ากลาง %.2f วิ" % (
                 DP3["compute_sec_per_step"], DP3["comm_sec_per_step"], DP3["comm_share_pct"], DP3["sec_per_step_median"]), "warn"),
            ("GPU util / Exact Match", "%.1f%% / %.1f%%" % (dp3_u_avg, DP3["exact_match_pct"]["epoch2"]),
             "GPU 6 ใบว่าง ~93%% ของเวลา (%.1f–%.1f%%) · การเชื่อมต่อหลุด 0 ครั้ง · LoRA เท่ากันทุกใบ" % (
                 dp3_u_min, dp3_u_max), "ok"),
        ],
        post=note("แม้จะส่งขาขึ้นเป็น `bf16` ครึ่งขนาดแล้ว แต่มี 5 step ที่เน็ตค้างเกิน 15 วิ (ช้าสุด **128 วิ**) ยิ่งมากเส้นทาง ยิ่งมีโอกาสสะดุด"),
        tag="1_data_parallel/node3/results/summary.json",
    ))

    add(fig(
        "DP 3 Node · 93–94% ของเวลาคือการส่งและรอ และมี 4 step ที่เครือข่ายค้าง 29–128 วินาที",
        P1 + "node3/results/images/step_time.png",
        "ด้านซ้าย: ทั้ง 6 GPU คำนวณเพียง 0.34–0.40 วิ แต่รอเกือบ 5 วิ · ด้านขวา: ช่วง step 155–210 เน็ตค้างสูงสุด 128\u00a0วิ",
        tag="1_data_parallel/node3/results/metrics.json",
    ))

    add(fig(
        "DP 3 Node · GPU ทั้ง 6 ใบทำงานเฉลี่ยเพียง 6.1–7.0% ตลอด 29.7 นาที",
        P1 + "node3/results/images/gpu_util.png",
        "เพิ่ม GPU เป็น 6 ใบใน 3 เครื่อง แต่เวลาแทบทั้งหมดหมดไปกับการรอเครือข่ายข้ามประเทศ ทำให้ GPU ว่างราว 93% ของเวลา",
        tag="1_data_parallel/node3/results/raw/",
    ))

    add(fig(
        "DP 3 Node · Loss ลดลงราบรื่นตลอด 334 step แม้มีจังหวะเน็ตค้างกลางทาง",
        P1 + "node3/results/images/loss.png",
        "train loss ลดจาก **%.4f → %.4f** · test loss ลดจาก Base **%.4f** เหลือ **%.4f** และ **%.4f** หลังจบ Epoch 1 และ 2" % (
            DP3["train_loss_per_epoch"][0], DP3["train_loss_per_epoch"][1],
            DP3["test_loss_base"], DP3["test_loss_per_epoch"][0], DP3["test_loss_per_epoch"][1]),
        tag="1_data_parallel/node3/results/metrics.json",
    ))

    add(fig(
        "DP 3 Node · Exact Match จบ Epoch 2 ที่ %.1f%% (test loss %.4f) น้ำหนัก LoRA ตรงกันทั้ง 6 ตัว" % (
            DP3["exact_match_pct"]["epoch2"], DP3["test_loss_per_epoch"][1]),
        P1 + "node3/results/images/exact_match.png",
        "Base **%.1f%%** → Epoch 1: **%.1f%%** (test loss %.4f) → Epoch 2: **%.1f%%** (test loss %.4f) · sha256 ของ LoRA ตรงกันทั้ง 6 Worker" % (
            DP3["exact_match_pct"]["base"], DP3["exact_match_pct"]["epoch1"], DP3["test_loss_per_epoch"][0],
            DP3["exact_match_pct"]["epoch2"], DP3["test_loss_per_epoch"][1]),
        tag="1_data_parallel/node3/results/summary.json",
    ))

    add(pslides("dp", "ขั้นที่ 6 ·", "LAB 5.1 ขั้นที่ 6 · สรุปผลและลบเครื่องทั้ง 3 Node (ห้ามข้าม)"))

    t_dp_cmp = filter_table(
        T("dp", "1 Node เทียบ 2 Node เทียบ 3 Node", ""),
        drop_starts=("ราคาต่อชั่วโมง", "เงินต่อ 1,000 ตัวอย่าง"),
    )
    add(tbl(
        "สรุป LAB 5.1 (Data Parallelism): 1 Node เร็วกว่า 2 และ 3 Node ผ่านอินเทอร์เน็ตถึง 4 เท่า",
        t_dp_cmp,
        post=note("ถ้าเครือข่ายเร็วพอจน step เท่ากับเวลาคำนวณ (ไม่รอเน็ต) 2 Node จะได้ราว **37** และ 3 Node ราว **66** ตัวอย่าง/วิ (ตัวเลขคำนวณ) — คอขวดจึงอยู่ที่อินเทอร์เน็ต ไม่ใช่ GPU"),
        tag="ตารางหลัก · LAB 5.1",
    ))

    # =========================================================================
    # 4 · LAB 5.2 · Model Parallelism บนคลัสเตอร์ (`2_model_parallel/` และ `node3/`)
    # =========================================================================
    CTX.update(kicker="", group="LAB 5.2 · Model Parallelism บนคลัสเตอร์")
    add(E.divider(
        "LAB 5.2",
        "Model Parallelism บนคลัสเตอร์ · แบ่งโมเดลในเครื่อง เฉลี่ยข้ามเครื่อง",
        "<p>คำถาม: แต่ละเครื่องแบ่ง Layer ของโมเดลลง GPU 2 ใบ แล้วเฉลี่ย Gradient ข้าม 2 และ 3 Node จะเร็วขึ้นกี่เท่าเทียบกับ 1 Node ของ LAB 4.3</p>"
        "<p class=\"dim\">โฟลเดอร์: <code>2_model_parallel/</code> (ขั้น 1–3 · 2 Node = 2 โมเดล) และ <code>2_model_parallel/node3/</code> (ขั้น 4–6 · 3 Node = 3 โมเดล)</p>",
        img=IMG_SL + "s04-mp-cluster.jpg",
        small="ส่วนที่ 2 จาก 2 ของภาค LAB · โฟลเดอร์ 2_model_parallel/",
    ))

    CTX["kicker"] = "LAB 5.2 (2_model_parallel/) · แนวคิด MP ในเครื่อง + ข้ามเครื่อง"
    add(big(
        "ทบทวน Model Parallelism ในเครื่องเดียว: แบ่ง Layer ลง 2 ใบ ได้ที่ว่าง VRAM แต่ผลัดกันทำ",
        IMG_2 + "c-mp.png",
        [
            "โมเดล 1 ชุดแบ่งครึ่ง: **GPU 0 ถือ `embed` + Layer 0–17** และ **GPU 1 ถือ Layer 18–35 + `norm` + `lm_head`**",
            "ได้พื้นที่ VRAM เพิ่มจนรับ `batch = 8` ต่อเครื่องได้สบาย (GPU ใบเดียวได้แค่ 4) แต่ GPU 2 ใบผลัดกันทำ util จึงอยู่ราว **49%**",
            "**ทำไมไม่แบ่ง Layer ข้ามเครื่อง?** เพราะผลกลางทางระหว่าง Layer ใหญ่และต้องส่งไป-กลับทุก step ผ่านอินเทอร์เน็ตจะช้ากว่าส่ง Gradient LoRA มาก",
        ],
    ))

    add(big(
        "1 step ของ Model Parallelism ในเครื่องเดียว: GPU 0 และ GPU 1 ผลัดกันคำนวณทีละใบ",
        IMG_2 + "c-mp-turns.png",
        [
            "**Forward** GPU 0 ทำครึ่งแรกแล้วส่งผลกลางทางให้ GPU 1 ทำครึ่งหลังและคำนวณ loss (ระหว่างนั้น GPU 0 ว่างรอ)",
            "**Backward** GPU 1 หา Gradient ครึ่งหลังแล้วส่งกลับให้ GPU 0 ทำครึ่งแรก (ระหว่างนั้น GPU 1 ว่างรอ)",
            "นี่คือสาเหตุที่ 1 Node ใน LAB 4.3 ได้ util เพียงราว 49% ต่อใบ ก่อนที่จะมีการรอเครือข่ายข้ามเครื่องซ้อนเพิ่มใน LAB 5.2",
        ],
    ))

    add(big(
        "ต่อ Model Parallelism ข้าม 2 Node: ในเครื่องแบ่ง Layer ข้ามเครื่องแบ่งข้อมูล (Hybrid)",
        IMG_2 + "c-mp-cluster.png",
        [
            "แต่ละ Node เปิด Worker **1 ตัว** ถือโมเดล 1 ชุดคร่อม GPU 2 ใบ (2 Node = โมเดล 2 ชุด · `batch = 8` ต่อ Node · batch รวม = 16)",
            "ระหว่าง Node ทำเหมือน Data Parallelism คือแบ่งข้อมูลคนละครึ่ง แล้วส่ง Gradient ของ LoRA ไปเฉลี่ยที่ Coordinator บน Node 1",
            "เทียบกับ LAB 5.1 ที่ 2 Node มี Worker 4 ตัว แบบนี้มี Worker **ครึ่งเดียว** ปริมาณ Gradient ที่เข้า Coordinator จึงน้อยกว่าครึ่งหนึ่ง",
        ],
    ))

    add(big(
        "1 step ของ MP บน 2 Node: GPU ต้องรอ 2 ชั้น ทั้งรออีกใบในเครื่องและรอเน็ตข้ามเครื่อง",
        IMG_2 + "c-mp-cluster-step.png",
        [
            "**รอชั้นที่ 1 (ในเครื่อง)** GPU 0 และ GPU 1 ผลัดกันทำ Forward และ Backward ทีละครึ่งโมเดล (เหมือน LAB 4.3 · คำนวณ ~0.70 วิ)",
            "**รอชั้นที่ 2 (ข้ามเครื่อง)** จบ Backward แล้วทั้ง 2 ใบหยุดรอส่ง Gradient ไปเฉลี่ยที่ Coordinator และรับค่าเฉลี่ยกลับ",
            "เมื่อการรอ 2 ชั้นซ้อนกัน GPU util ที่เดิมอยู่ ~49% บน 1 Node จึงถูกบีบลงอีกมาก",
        ],
    ))

    CTX["kicker"] = "LAB 5.2 (2_model_parallel/) · ส่วนที่ 1: 2 Node (ขั้นที่ 1–3)"
    add(pslides("mp", "ขั้นที่ 1 ·", "LAB 5.2 ขั้นที่ 1 · เช่า 2 Node เตรียมของ และวัดเน็ต"))

    mp2_net = MP2["network"][0]
    add(E.hero(
        CTX["kicker"],
        "ผลวัดเน็ต MP 2 Node (ฝรั่งเศส–เช็กเกีย): วัดได้เพียง %.1f–%.1f Mbps ช้ากว่าประกาศ 8 เท่า" % (
            mp2_net["mbps_node1_to_node2"], mp2_net["mbps_node2_to_node1"]),
        IMG_SL + "h04-mp2-net.jpg",
        [
            ("RTT (50 ครั้ง)", "30.0 ms",
             "ค่ากลาง 30.0 ms · เฉลี่ย %.1f ms · สูงสุด 97.8 ms (ผ่านเกณฑ์ไม่เกิน 100 ms)" % mp2_net["rtt_ms_avg"], "ok"),
            ("ความเร็ว 1 สาย (ไป / กลับ)", "%.1f / %.1f Mbps" % (
                mp2_net["mbps_node2_to_node1"], mp2_net["mbps_node1_to_node2"]),
             "ตอนเลือกเครื่องกรองไว้ ≥ 700 Mbps แต่ระหว่างสองเครื่องได้ราว 82 Mbps เท่านั้น", "bad"),
            ("เปิดเพิ่มเป็น 8 สายพร้อมกัน", "%.1f / %.1f Mbps" % (
                mp2_net["mbps_node2_to_node1_8streams"], mp2_net["mbps_node1_to_node2_8streams"]),
             "เร็วขึ้นเพียงเล็กน้อย ยืนยันว่าคอขวดอยู่ที่เส้นทางเครือข่ายของ Node 1", "warn"),
        ],
        post=note("สังเกตได้ตั้งแต่ตอนเตรียมเครื่อง: Node 1 โหลดโมเดล 16 GB นานราว **20 นาที** ส่วน Node 2 ใช้ไม่ถึง 1 นาที"),
        tag="2_model_parallel/results/network_test.json",
    ))

    add(pslides("mp", "ขั้นที่ 2 ·", "LAB 5.2 ขั้นที่ 2 · เทรนแบบ Model Parallelism ข้าม 2 Node"))

    add(nfig("n05-mp2-recovery"))

    t_mp2_vram = T("mp", "ขั้นที่ 2 ·", "GPU")
    add(tbl(
        "MP 2 Node · แบ่ง Layer 18+18 เหมือนกันทั้ง 2 เครื่อง ใช้ VRAM เพียง 14.0–14.4 GiB",
        t_mp2_vram,
        post=note("นี่คือข้อดีเดิมของ Model Parallelism: `batch = 8` ต่อ Node ผ่านการลอง 3 step ตั้งแต่ครั้งแรก ไม่เกิด Out of Memory ต่างจาก DP ที่ชนเพดาน 22.2 GiB", "ok"),
        tag="2_model_parallel/results/metrics.json",
    ))

    mp2_u_avg, mp2_u_min, mp2_u_max = avg_util(MP2)
    add(E.hero(
        CTX["kicker"],
        "ผล MP 2 Node: ได้ %.2f ตัวอย่าง/วิ · ส่งและรอ %.1f%% · GPU util เหลือราว %.0f%%" % (
            MP2["examples_per_sec"], MP2["comm_share_pct"], mp2_u_avg),
        IMG_SL + "h05-mp2-res.jpg",
        [
            ("ความเร็วเฉลี่ย 2 Epoch", "%.2f" % MP2["examples_per_sec"] + "<small>ตัวอย่าง/วินาที</small>",
             "เทียบ 1 Node (10.13) ได้ Speedup = **0.48** (Efficiency **24%%**) · เทรน 500 step ใน %.1f นาที" % MP2["train_minutes"], "warn"),
            ("เวลาต่อ step เฉลี่ย", "%.2f วิ" % MP2["sec_per_step"],
             "คำนวณ **%.2f วิ (21.5%%)** · ส่งและรอ **%.2f วิ (%.1f%%)** · ค่ากลาง %.2f วิ" % (
                 MP2["compute_sec_per_step"], MP2["comm_sec_per_step"], MP2["comm_share_pct"], MP2["sec_per_step_median"]), "bad"),
            ("GPU util / Exact Match", "%.1f%% / %.1f%%" % (mp2_u_avg, MP2["exact_match_pct"]["epoch2"]),
             "GPU 4 ใบอยู่ %.1f–%.1f%% (1 ใน 5 ของ 1 Node) · น้ำหนัก LoRA 2 Node ตรงกัน (sha256)" % (
                 mp2_u_min, mp2_u_max), "ok"),
        ],
        post=note("ส่ง Gradient ขาขึ้นเป็น `bf16` (7.67 MB) ผ่าน 4 สาย TCP และรับค่าเฉลี่ย `float32` (15.34 MB) · ตัวเลข 4.90 ไม่นับช่วงที่โฮสต์ Node 1 ดับ 5 นาที"),
        tag="2_model_parallel/results/summary.json",
    ))

    add(fig(
        "MP 2 Node · ส่งและรอกิน 78.5% ของทุก step และมีช่วงพุ่งแตะ 13 วิช่วงกลาง Epoch 1",
        P2 + "results/images/step_time.png",
        "ด้านซ้าย: เวลาคำนวณ 0.69–0.71 วิ (ใกล้เคียง 0.79 วิ ของ 1 Node) แต่เวลาส่งและรอ 2.56 วิ · ด้านขวา: Epoch 2 เน็ตนิ่งกว่า Epoch 1 (5.76 เทียบ 4.27 ตัวอย่าง/วิ)",
        tag="2_model_parallel/results/metrics.json",
    ))

    add(fig(
        "MP 2 Node · GPU util เฉลี่ยเหลือ 9.4–10.8% เพราะรอทั้งในเครื่องและข้ามเครื่องซ้อนกัน",
        P2 + "results/images/gpu_util.png",
        "1 Node ใน LAB 4.3 ได้ util ~49% จากการผลัดกันทำ พอเพิ่มเวลารอเน็ต 78.5% เข้าไป การ์ดจึงทำงานเพียงราว 1 ใน 10 ของเวลา",
        tag="2_model_parallel/results/run/",
    ))

    add(fig(
        "MP 2 Node · Loss ลดต่อเนื่องตลอด 500 step แม้ผ่านการกู้คืนจาก checkpoint step 150",
        P2 + "results/images/loss.png",
        "train loss ลดจาก **%.3f → %.3f** · test loss ลดจาก Base **%.3f** เหลือ **%.4f** และ **%.4f** โดยไม่มีรอยสะดุดหลังรีสตาร์ต" % (
            MP2["train_loss_per_epoch"][0], MP2["train_loss_per_epoch"][1],
            MP2["test_loss_base"], MP2["test_loss_per_epoch"][0], MP2["test_loss_per_epoch"][1]),
        tag="2_model_parallel/results/metrics.json",
    ))

    add(fig(
        "MP 2 Node · Exact Match จบ Epoch 2 ที่ %.1f%% ใกล้เคียง 1 Node (77.5%%)" % MP2["exact_match_pct"]["epoch2"],
        P2 + "results/images/exact_match.png",
        "Base **%.1f%%** (3/200) → Epoch 1: **%.1f%%** (139/200) → Epoch 2: **%.1f%%** (148/200) · ต่างจาก 1 Node เพียง 7 ข้อจาก 200" % (
            MP2["exact_match_pct"]["base"], MP2["exact_match_pct"]["epoch1"], MP2["exact_match_pct"]["epoch2"]),
        tag="2_model_parallel/results/summary.json",
    ))

    add(pslides("mp", "ขั้นที่ 3 ·", "LAB 5.2 ขั้นที่ 3 · สรุปผลและลบเครื่องทั้ง 2 Node (ห้ามข้าม)"))

    CTX["kicker"] = "LAB 5.2 (2_model_parallel/node3/) · ส่วนที่ 2: 3 Node (ขั้นที่ 4–6)"
    add(big(
        "ขยาย MP จาก 2 Node เป็น 3 Node (3 โมเดล, 6 GPU): เพิ่ม Node เท่ากับเพิ่มชุดโมเดล",
        IMG_2 + "c-mp-cluster3.png",
        [
            "เพิ่มเป็น **3 Node (โมเดล 3 ชุด, ชุดละ 2 GPU)** แบ่งข้อมูลเครื่องละ 1/3 · `batch = 8` ต่อ Node ทำให้ **batch รวม = 24** (167 step/Epoch)",
            "เวลาคำนวณต่อ step ควรคงที่ (~0.7 วิ) แต่ Coordinator ต้องรอ Gradient ครบทั้ง 3 Node และเดินเร็วเท่าเครื่องที่ช้าที่สุด",
            "เช่นเดียวกับ DP: ได้ตัวอย่างต่อ step เพิ่ม 1.5 เท่า ถ้าเวลาต่อ step นานขึ้นเกิน 1.5 เท่า ความเร็วรวมจะตกลง",
        ],
    ))

    add(pslides("mp", "ขั้นที่ 4 ·", "LAB 5.2 ขั้นที่ 4 · เช่า 3 Node เตรียมของ และวัดเน็ต"))

    t_mp3_net = T("mp", "ขั้นที่ 4 ·", "เส้นทาง")
    add(tbl(
        "ผลวัดเน็ต MP 3 Node (อาร์เจนตินา–ชิลี) 2 รอบ: RTT นิ่ง 29–36 ms แต่ความเร็วแกว่งหนัก",
        t_mp3_net,
        post=note("เส้นทางเดียวกันวัดห่างกันไม่กี่นาทีได้ **82 แล้วพุ่งเป็น 306 Mbps** (หรือ 644 แล้วหล่นเป็น 210 Mbps) · การวัดเพียงรอบเดียวจึงบอกได้แค่คร่าว ๆ"),
        tag="node3/results/net_probe_run*.json",
    ))

    add(pslides("mp", "ขั้นที่ 5 ·", "LAB 5.2 ขั้นที่ 5 · เทรนแบบ Model Parallelism ข้าม 3 Node"))

    t_mp3_node = T("mp", "ขั้นที่ 5 ·", "")
    add(tbl(
        "แยกเวลา ส่ง / รอ / รับ ราย Node ของ MP 3 Node: เห็นชัดว่าใครกำลังรอใครอยู่",
        t_mp3_node,
        post=note("Node 1 อยู่เครื่องเดียวกับ Coordinator จึงส่ง/รับเกือบทันที (0.01/0.02 วิ) แต่ต้อง **รอ 4.69 วิ** ให้ Node 2 และ Node 3 มาถึง · รอบนี้เจอบั๊กตั้ง socket buffer ซ้ำรอย (20–70 วิ → 3.5 วิ)"),
        tag="ตารางหลัก · node3/results/metrics.json",
    ))

    mp3_u_avg, mp3_u_min, mp3_u_max = avg_util(MP3)
    add(E.hero(
        CTX["kicker"],
        "ผล MP 3 Node: ได้ %.2f ตัวอย่าง/วิ (ช้ากว่า 2 Node) — ส่งและรอ %.0f%%, GPU util %.1f%%" % (
            MP3["examples_per_sec"], MP3["comm_share_pct"], mp3_u_avg),
        IMG_SL + "h06-mp3-res.jpg",
        [
            ("ความเร็วเฉลี่ย 2 Epoch", "%.2f" % MP3["examples_per_sec"] + "<small>ตัวอย่าง/วินาที</small>",
             "เทียบ 1 Node (10.13) ได้ Speedup = **0.43** (Efficiency **14%%**) · เทรน 334 step ใน %.1f นาที" % MP3["train_minutes"], "bad"),
            ("เวลาต่อ step เฉลี่ย", "%.2f วิ" % MP3["sec_per_step"],
             "คำนวณ **%.2f วิ (13%%)** · ส่งและรอ **%.2f วิ (%.0f%%)** · ส่ง `float32` เต็มทั้งสองขา (15.34 MB)" % (
                 MP3["compute_sec_per_step"], MP3["comm_sec_per_step"], MP3["comm_share_pct"]), "warn"),
            ("GPU util / Exact Match", "%.1f%% / %.1f%%" % (mp3_u_avg, MP3["exact_match_pct"]["epoch2"]),
             "GPU 6 ใบอยู่ %.1f–%.1f%% · ใช้ VRAM เพียง 12.6–14.4 GiB · LoRA ตรงกันทั้ง 3 Node" % (
                 mp3_u_min, mp3_u_max), "ok"),
        ],
        post=note("รอบนี้ AI ส่ง Gradient แบบ `float32` เต็มทั้งขาขึ้นและขาลง (ส่วน 2 Node ส่งขาขึ้น `bf16`) จึงเป็นส่วนหนึ่งที่ทำให้เวลาส่งและรอนานขึ้นเกือบ 2 เท่า"),
        tag="2_model_parallel/node3/results/summary.json",
    ))

    add(fig(
        "MP 3 Node · 87% ของเวลาต่อ step คือการส่งและรอ และมีจังหวะเน็ตค้างทะลุ 60 วินาที",
        P2 + "node3/results/images/step_time.png",
        "ด้านซ้าย: ทั้ง 3 Node เฉลี่ยเท่ากันเป๊ะ (5.51–5.53 วิ) เพราะ Synchronous · ด้านขวา: ช่วง step 250 เน็ตค้างเกิน 60\u00a0วิ",
        tag="2_model_parallel/node3/results/metrics.json",
    ))

    add(fig(
        "MP 3 Node · GPU ทั้ง 6 ใบเฉลี่ย 6.1–7.3% ตลอดการเทรน 30.9 นาที",
        P2 + "node3/results/images/gpu_util.png",
        "กราฟลักษณะเดียวกับ DP 3 Node คือ GPU ว่างราว 93% ของเวลา เพราะต้องรอการสื่อสารข้ามเครื่องแทบตลอดทุก step",
        tag="2_model_parallel/node3/results/train/",
    ))

    add(fig(
        "MP 3 Node · Loss ลดลงต่อเนื่องตลอด 334 step โดยไม่หลุดการเชื่อมต่อเลย",
        P2 + "node3/results/images/loss.png",
        "train loss ลดจาก **%.3f → %.3f** · test loss ลดจาก Base **%.3f** เหลือ **%.3f** และ **%.3f** หลังจบ Epoch 1 และ 2" % (
            MP3["train_loss_per_epoch"][0], MP3["train_loss_per_epoch"][1],
            MP3["test_loss_base"], MP3["test_loss_per_epoch"][0], MP3["test_loss_per_epoch"][1]),
        tag="2_model_parallel/node3/results/metrics.json",
    ))

    add(fig(
        "MP 3 Node · Exact Match จบ Epoch 2 ที่ %.1f%% (ต่ำกว่า 2 Node 6 ข้อ จาก batch รวม 24)" % MP3["exact_match_pct"]["epoch2"],
        P2 + "node3/results/images/exact_match.png",
        "Base **%.1f%%** → Epoch 1: **%.1f%%** (test loss %.3f) → Epoch 2: **%.1f%%** (test loss %.3f) · ปรับน้ำหนักเพียง 167 ครั้ง/Epoch · LoRA 3 Node ตรงกันทุกค่า" % (
            MP3["exact_match_pct"]["base"], MP3["exact_match_pct"]["epoch1"], MP3["test_loss_per_epoch"][0],
            MP3["exact_match_pct"]["epoch2"], MP3["test_loss_per_epoch"][1]),
        tag="2_model_parallel/node3/results/summary.json",
    ))

    add(pslides("mp", "ขั้นที่ 6 ·", "LAB 5.2 ขั้นที่ 6 · สรุปผลและลบเครื่องทั้ง 3 Node (ห้ามข้าม)"))

    t_mp_cmp = filter_table(
        T("mp", "1 Node เทียบ 2 Node เทียบ 3 Node", ""),
        drop_starts=("ราคาต่อชั่วโมง", "เงินต่อ 1,000 ตัวอย่าง"),
    )
    add(tbl(
        "สรุป LAB 5.2 (Model Parallelism): เพิ่มเครื่องแล้วช้าลงราวครึ่งหนึ่ง แต่ยังได้ข้อดีเรื่อง VRAM",
        t_mp_cmp,
        post=note("ถ้าเครือข่ายเร็วพอจน step เท่าเวลาคำนวณ 2 Node จะได้ราว **23** และ 3 Node ราว **33** ตัวอย่าง/วิ (ตัวเลขคำนวณ) · ใช้ VRAM เพียง 12.6–14.4 GiB ต่อใบ"),
        tag="ตารางหลัก · LAB 5.2",
    ))

    # =========================================================================
    # 5 · บทสรุปทั้ง 2 LAB · เปรียบเทียบ · แนวทางตัดสินใจ · ขั้นปิดท้ายสร้างสกิล
    # =========================================================================
    CTX.update(kicker="", group="บทสรุปทั้ง 2 LAB · เปรียบเทียบและแนวทางตัดสินใจ")
    add(E.divider(
        "บทสรุป LAB 5",
        "เทียบ 1 Node · 2 Node · 3 Node ทั้งสองแบบ และเมื่อไรควรใช้คลัสเตอร์",
        "<p>นำผลจริงของ LAB 5.1 (Data Parallelism) และ LAB 5.2 (Model Parallelism) มาวางคู่กัน สรุปบทเรียนหน้างาน และแนวทางตัดสินใจก่อนขยายเครื่อง</p>",
        img=IMG_SL + "s05-summary.jpg",
        small="บทสรุปรวมของทั้ง 2 LAB ย่อย",
    ))

    CTX["kicker"] = "บทสรุป · ภาพรวมผลจริงทั้ง 2 LAB"
    add(fig(
        "ผลรวมทั้ง 2 LAB ในภาพเดียว: เพิ่มเครื่องผ่านอินเทอร์เน็ตแล้วช้าลงทั้ง DP และ MP",
        IMG_OV + "r-compare-cluster.png",
        "DP ลดจาก **19.08 → 4.50 / 4.49** ตัวอย่าง/วิ (Speedup 0.24) · MP ลดจาก **10.13 → 4.90 / 4.32** ตัวอย่าง/วิ (Speedup 0.48 / 0.43) เพราะส่งและรอกิน **78–93%**",
        tag="สรุปผลจริง LAB 5",
    ))

    t_all = filter_table(
        T("ov", "ผลรวม: 1 Node เทียบ 2 Node เทียบ 3 Node", ""),
        drop_starts=("ราคาต่อชั่วโมง", "เงินต่อ 1,000 ตัวอย่าง", "ใบคิดเงินจริง"),
    )
    add(tbl(
        "ตารางสรุปตัวเลขวัดจริงทั้ง 6 กรณี: เทียบ 1, 2 และ 3 Node ของทั้ง DP และ MP",
        t_all,
        post=note("1 Node มาจาก LAB 4 (GPU 2 ใบในเครื่องเดียว) · จะเห็นว่าบนคลัสเตอร์ทั้ง 2 แบบได้ความเร็วใกล้กันมาก (4.3–4.9 ตัวอย่าง/วิ) แม้บน 1 Node จะต่างกันเกือบ 2 เท่า"),
        tag="ตารางหลัก · 6 กรณี",
    ))

    add(E.hero(
        CTX["kicker"],
        "คอขวดคืออินเทอร์เน็ต ไม่ใช่ GPU: เมื่อเน็ตช้ากว่าคำนวณ 4–14 เท่า วิธีจัดวางในเครื่องแทบไม่ต่างกัน",
        IMG_SL + "h07-network-wall.jpg",
        [
            ("สัดส่วนเวลาส่งและรอเน็ต", "78–93%",
             "GPU คำนวณแค่ **0.36–0.73 วิ/step** แต่รอเน็ต **2.56–4.97 วิ/step** · GPU util จึงร่วงเหลือ **6.6–12.7%**", "bad"),
            ("ความเร็วบนคลัสเตอร์ (ทุกแบบ)", "4.3–4.9 / วิ",
             "DP และ MP บนอินเทอร์เน็ตวิ่งพอ ๆ กัน และ **2 → 3 Node ไม่เร็วขึ้น** เพราะ Coordinator ต้องรอตัวที่ช้าที่สุดจากจำนวนที่มากขึ้น", "warn"),
            ("ถ้าเครือข่ายเร็วพอ (คำนวณ)", "37–66 / วิ",
             "หาก step ใช้เวลาเท่าเวลาคำนวณ (เช่น Data Center เดียวกัน) DP 2 Node จะได้ราว **37** และ 3 Node ราว **66** ตัวอย่าง/วิ", "ok"),
        ],
        post=note("คลัสเตอร์จริงในระดับโปรดักชันจึงวางทุก Node ในห้องเดียวกันและเชื่อมด้วยเครือข่ายความเร็วสูง (เช่น InfiniBand / RoCE) ไม่ใช่ต่อข้ามอินเทอร์เน็ตสาธารณะ"),
        tag="วิเคราะห์คอขวดเครือข่าย",
    ))

    add(E.hero(
        CTX["kicker"],
        "ด้านความถูกต้อง: การเฉลี่ย Gradient ข้ามเครื่องทำงานถูกทุกชุด น้ำหนัก LoRA ตรงกัน 100%",
        IMG_SL + "h08-quality-sync.jpg",
        [
            ("ความเท่ากันของน้ำหนัก LoRA", "100% ทุกรอบ",
             "ตรวจหลังจบทุก Epoch ทั้ง 4 รอบ (4, 6, 2, 3 Worker) ยืนยันว่าน้ำหนัก LoRA ตรงกันทุกค่า (sha256 ตรงกัน)", "ok"),
            ("Exact Match หลัง Epoch 2", "71.0–75.0%",
             "DP2 **75.0%** · DP3 **74.5%** · MP2 **74.0%** · MP3 **71.0%** (เทียบ 1 Node LAB 4 ที่ **77.5%**)", "ok"),
            ("ผลของ batch รวมที่ใหญ่ขึ้น", "8 → 16 → 24",
             "batch รวมใหญ่ขึ้นทำให้จำนวน Update ต่อ Epoch ลดลง (500 → 250 → 167 ครั้ง) และ Test Set มี 200 ข้อ (1 ข้อ = 0.5 จุด)", "warn"),
        ],
        post=note("การกระจายงานข้ามเครื่องแบบ Synchronous ไม่ได้ทำลายคุณภาพของโมเดล ปัญหาเดียวที่เกิดขึ้นในการทดลองนี้คือประสิทธิภาพด้านเวลาและทรัพยากรจากเครือข่าย"),
        tag="สรุปด้านคุณภาพโมเดล",
    ))

    t_real = T("ov", "ผลรวม: 1 Node เทียบ 2 Node เทียบ 3 Node", "เรื่อง")
    add(tbl(
        "5 ปัญหาจริงที่เจอระหว่างทำ LAB 5 และบทเรียนที่ต้องนำไปใช้กับงานคลัสเตอร์",
        t_real,
        post=note("ทุกปัญหาในตารางนี้เกิดขึ้นจริงในการรัน LAB 5.1 และ 5.2 และถูกออกแบบวิธีป้องกันไว้ในพรอมต์ของทั้งสอง LAB แล้ว", "info"),
        tag="ตารางหลัก · บทเรียนหน้างาน",
    ))

    CTX["kicker"] = "บทสรุป · แนวทางตัดสินใจและข้อจำกัด"
    add(fig(
        "ก่อนเพิ่มเครื่องให้ถาม 3 ข้อ และวัดความเร็วเน็ตเทียบเวลาคำนวณเสมอ",
        IMG_OV + "r-choose-cluster.png",
        "เริ่มที่ **1 Node ก่อนเสมอ** → ถ้าไม่พอให้ดูว่า Node อยู่ใน **เครือข่ายเร็วเดียวกันไหม** → ถ้าผ่านอินเทอร์เน็ตต้องคำนวณ **ขนาด Gradient ÷ ความเร็วเน็ต** เทียบเวลาคำนวณ",
        tag="แนวทางตัดสินใจ",
    ))

    t_choose = T("ov", "เมื่อไรควรใช้คลัสเตอร์", "สถานการณ์")
    add(tbl(
        "สรุป 4 สถานการณ์: เมื่อไรควรอยู่บน 1 Node เมื่อไรใช้คลัสเตอร์ และต้องปรับอะไรถ้าจำเป็นต้องผ่านเน็ต",
        t_choose,
        post=note("หากจำเป็นต้องเทรนผ่านอินเทอร์เน็ตจริง ๆ ทางแก้หลักคือ **ส่งให้เล็กลง** (บีบ Gradient เช่น `bf16`) หรือ **ส่งให้ห่างขึ้น** (Gradient Accumulation / เฉลี่ยทุกหลาย step)"),
        tag="ตารางหลัก · การเลือกใช้",
    ))

    add(nfig("n06-cluster-caveats"))

    CTX.update(kicker="", group="บทสรุปทั้ง 2 LAB · เปรียบเทียบและแนวทางตัดสินใจ")
    add(statement(
        "จบ LAB 5",
        IMG_SL + "s05-summary.jpg",
        "ขยายบน 1 Node ก่อน · วัดเน็ตก่อนขยายคลัสเตอร์ · และลบเครื่องทุก Node เสมอ",
        "LAB 5 พิสูจน์ด้วยตัวเลขจริงว่า **เครือข่ายคือตัวกำหนดความคุ้มค่าของคลัสเตอร์** — ใช้สูตร `ขนาด Gradient ÷ ความเร็วเน็ต` เช็กก่อนเทรนทุกครั้ง และเลือกวิธีจัดวางให้ตรงคอขวด",
        links_html=(
            '<a href="README.md" target="_blank">หน้ารวม LAB 5</a>'
            '<a href="1_data_parallel/README.md" target="_blank">LAB 5.1 (1_data_parallel/)</a>'
            '<a href="2_model_parallel/README.md" target="_blank">LAB 5.2 (2_model_parallel/)</a>'
        ),
    ))

    return E.write(E.SL, OUT, TITLE)


if __name__ == "__main__":
    for st in (sys.stdout, sys.stderr):
        if hasattr(st, "reconfigure"):
            st.reconfigure(encoding="utf-8", errors="replace")
    build()
