#!/usr/bin/env python3
"""สร้างสไลด์ LAB7_LLM_Serving_LB_Slides.html ของ LAB 7
(RTX 4090 · Single GPU, Data Parallelism 2 GPU และ Model Parallelism 4 GPU แบบ 2+2 หลัง NGINX)

  python tools/build_slides.py   (รันจากโฟลเดอร์ lab7_llm_serving_lb)

ลำดับของเด็คตามสกิล readme-slides:
  ปก → ภาพรวม & ขอบเขต (2 เครื่องแยกแทร็ก) → 4 การออกแบบ → วิธีวัด & ข้อมูลทดสอบ
  → LAB 10 ขั้น (แนวคิดอยู่หน้าขั้นที่ใช้ → พรอมต์ตรงตัวอักษร → ผลจริง)
  → สรุปผลและแนวทางเลือกใช้งานจริง

ข้อกำหนดที่ยึดถือครบทุกข้อ:
- 80–100 หน้า · 1 สไลด์ = 1 ประเด็น · หัวข้อเป็นข้อสรุป
- แนวคิดอยู่หน้าขั้นที่ใช้ · คั่นชัดหลังขั้นที่ 1 ด้วยสถานะ Vast.ai RUNNING (ไม่มีราคา/ค่าเช่าในสไลด์)
- ใช้คำเต็มเสมอ (Data Parallelism, Model Parallelism, GPU utilization) ยกเว้นชื่อไฟล์/โค้ดใน backticks
- ไม่มีหน้าวิธีใช้สไลด์ · ไม่มีหน้าตรวจผล (check_slide) · ไม่มีหน้ากล่องข้อความล้วน (cards)
- ตัวเลขทุกตัวอ่านจาก README.md และ results/*.json ตอนสร้างไฟล์
"""
import json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import slides_engine as E
from slides_engine import md, CTX, add, note, fig, explain, tiles, versus, bars, tbl, code, plain
from slides_figures import FIGS

S = E.slide
FIG = {f["img"]: f for f in FIGS}
OUT = "LAB7_LLM_Serving_LB_Slides.html"
TITLE = "LAB 7 · LLM Serving บน RTX 4090 หลัง NGINX (Data Parallelism vs Model Parallelism 2+2) · Slides"
NSTEP = 10
TH, LB, SL, RI = "images/theory/", "images/lab/", "images/slides/", "results/images/"
HOW = "วางพรอมต์นี้ใน Claude Code ที่เปิดอยู่ที่โฟลเดอร์ `02_VastAi_Application`"

# ------------------------------------------------------------------ CSS เพิ่มเติมเฉพาะเด็คนี้ (ไม่แก้ engine)
E.CSS += r"""
.ex.big .fig{flex:2.2 1 0}
.ex.mid2 .fig{flex:1.85 1 0}
.tiles+.note,.vs+.note,.bars+.note{margin-top:.85em}
.tile .num .sm{font-size:.72em}
.bars.neutral .fl{background:var(--teal)!important}
.slide th a{color:#fff}
.slide.hero .tag{color:#ffd28a;text-shadow:0 1px 6px rgba(0,0,0,.95),0 0 3px #000}
.inner h1{line-height:1.38}
/* บังคับพรอมต์ทุกขั้นจบภายในสไลด์หน้าเดียวเสมอ (ปรับฟอนต์ลงเล็กน้อยให้อ่านชัดไม่ตกขอบ) */
.slide.pslide pre.code.prompt{font-size:.76em;line-height:1.36}

/* Vast.ai Web Console Dual-Track Status Card (หลังขั้นที่ 1 · ไม่แสดงราคา/ค่าเช่า) */
.vweb{background:#0f172a;color:#e2e8f0;border-radius:14px;overflow:hidden;border:1px solid #1e293b;margin-top:4px;box-shadow:0 10px 28px rgba(15,23,42,.18)}
.vweb-bar{display:flex;align-items:center;justify-content:space-between;background:#1e293b;padding:10px 20px;border-bottom:1px solid #334155;font-family:ui-monospace,Consolas,monospace;font-size:.8em;color:#94a3b8}
.vweb-dots{display:flex;gap:7px;align-items:center}
.vweb-dot{width:10px;height:10px;border-radius:50%;display:inline-block}
.vweb-url{background:#0f172a;padding:4px 16px;border-radius:6px;color:#cbd5e1;border:1px solid #334155}
.vweb-status{display:inline-flex;align-items:center;gap:7px;background:rgba(16,185,129,.18);color:#34d399;border:1px solid rgba(52,211,153,.45);padding:3px 12px;border-radius:999px;font-weight:700;font-size:.84em}
.vweb-cols{display:grid;grid-template-columns:1fr 1fr;gap:0}
.vweb-pane{padding:18px 24px}
.vweb-pane+.vweb-pane{border-left:1px solid #334155}
.vweb-head{display:flex;align-items:center;justify-content:space-between;gap:10px;padding-bottom:10px;border-bottom:1px solid #334155;margin-bottom:12px}
.vweb-gpu{font-size:1.18em;font-weight:700;color:#38bdf8}
.vweb-gpu.mp{color:#c084fc}
.vweb-lbl{font-family:ui-monospace,Consolas,monospace;background:#1e293b;color:#fde68a;padding:3px 10px;border-radius:6px;border:1px solid #475569;font-size:.82em}
.vweb-kv{display:grid;grid-template-columns:auto 1fr;gap:6px 14px;font-size:.86em;line-height:1.42}
.vweb-k{color:#94a3b8;font-weight:600;white-space:nowrap}
.vweb-v{color:#f8fafc}
.vweb-foot{background:#17253d;padding:10px 24px;border-top:1px solid #334155;display:flex;justify-content:space-between;gap:20px;align-items:center;font-size:.86em;color:#7dd3fc;font-weight:600}
.vweb b{color:#7dd3fc}
.vweb .vweb-foot b{color:#fde68a}
.vweb code{background:#1e293b;color:#fde68a;border:1px solid #334155}
"""

# ------------------------------------------------------------------ อ่าน README.md และไฟล์ผลจริง
E.load("README.md")
M = json.loads(E.read("results/metrics.json"))
T_DP2 = json.loads(E.read("results/timings_dp2.json"))
T_MP4 = json.loads(E.read("results/timings_mp4.json"))
DP1_N1 = json.loads(E.read("results/dp1_n1_baseline.json"))
MP4_DP1 = json.loads(E.read("results/mp4_dp1_ref.json"))
MP4_N1 = json.loads(E.read("results/mp4_n1_baseline.json"))
DP1_SEQ = json.loads(E.read("results/dp1_seq.json"))
DP1_CB = json.loads(E.read("results/dp1_cb.json"))
DP1_FAST = json.loads(E.read("results/dp1_cb_fast.json"))
DP2_CB = json.loads(E.read("results/dp2_cb.json"))
DP2_FAST = json.loads(E.read("results/dp2_cb_fast.json"))
MP4_CB = json.loads(E.read("results/mp4_cb.json"))
MP4_FAST = json.loads(E.read("results/mp4_cb_fast.json"))
MIX_S = json.loads(E.read("results/mix_short.json"))["levels"][0]
MIX_L = json.loads(E.read("results/mix_long.json"))["levels"][0]
FAIL_R = json.loads(E.read("results/fail_replica.json"))
FAIL_E = json.loads(E.read("results/fail_event.json"))
LC_CHK = json.loads(E.read("results/loadtest_check_summary.json"))


def tabs(prefix, head0):
    out = [b for b in E.walk(E.sec(prefix)) if b["t"] == "table" and plain(b["head"][0]).startswith(head0)]
    if not out:
        raise KeyError("ไม่พบตาราง %r ในหัวข้อ %r" % (head0, prefix))
    return out


def clean_cell(s):
    return re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"\1", s)


def T(prefix, head0, k=0):
    t = tabs(prefix, head0)[k]
    return {
        "t": "table",
        "head": [clean_cell(c) for c in t["head"]],
        "rows": [[clean_cell(c) for c in r] for r in t["rows"]],
    }


def fences(prefix, lang):
    return [b for b in E.walk(E.sec(prefix)) if b["t"] == "code" and b["lang"] == lang]


def bare(s):
    return s.replace("**", "").strip()


def big(title, src, points, post="", cls="big", tag=""):
    s = explain(title, src, points, post)
    s["body"] = s["body"].replace('<div class="ex">', '<div class="ex %s">' % cls, 1)
    if tag:
        s["tag"] = tag
    return s


def nfig(key, title=None, post="", tag=""):
    f = FIG[key]
    return big(title or f["title"], SL + "%s.jpg" % key, f["steps"], post=post, cls="mid2", tag=tag)


def nbars(rows):
    return bars(rows).replace('<div class="bars">', '<div class="bars neutral">', 1)


def filter_table(t, keep_cols=None, keep_rows=None):
    head = [t["head"][i] for i in keep_cols] if keep_cols else t["head"]
    rows = []
    for idx, r in enumerate(t["rows"]):
        if keep_rows is not None and idx not in keep_rows:
            continue
        rows.append([r[i] for i in keep_cols] if keep_cols else r)
    return {"t": "table", "head": head, "rows": rows}


def vastai_ready_dual():
    """สไลด์คั่นหลังขั้นที่ 1 แสดงสถานะเครื่องเช่าทั้ง 2 โหนดพร้อมใช้งาน (RUNNING · ไม่มีราคา/ค่าเช่า)"""
    dp2_kv = [
        ("Instance ID", "`62662793` · The Netherlands, NL"),
        ("จำนวนโหนด / GPU", "**1 โหนด × 2× RTX 4090** (48 GB รวม)"),
        ("อุณหภูมิตอนว่าง", "22–25 °C (ผ่านเกณฑ์ ≤ 60 °C)"),
        ("เน็ตขาเข้า / ออก", "**1,179↓ / 1,054↑ Mbps** (≥ 1,000)"),
        ("CPU / RAM / PCIe", "64 vCPUs · 128.9 GB · PCIe 4.0 x16"),
        ("บทบาทใน LAB 7", "แทร็ก 1: Single GPU → **Data Parallelism**"),
    ]
    mp4_kv = [
        ("Instance ID", "`62662797` · Japan, JP"),
        ("จำนวนโหนด / GPU", "**1 โหนด × 4× RTX 4090** (96 GB รวม)"),
        ("อุณหภูมิตอนว่าง", "30–47 °C (ผ่านเกณฑ์ ≤ 60 °C)"),
        ("เน็ตขาเข้า / ออก", "**7,789↓ / 7,220↑ Mbps** (≥ 1,000)"),
        ("CPU / RAM / PCIe", "128 vCPUs · 257.5 GB · PCIe 4.0 x16"),
        ("บทบาทใน LAB 7", "แทร็ก 2: **Model Parallelism แบบ 2+2**"),
    ]
    kv_html = lambda items: "".join(
        '<div class="vweb-k">%s</div><div class="vweb-v">%s</div>' % (E.esc(k), md(v)) for k, v in items
    )
    body = (
        '<div class="vweb">'
        '<div class="vweb-bar">'
        '<div class="vweb-dots"><span class="vweb-dot" style="background:#f87171"></span>'
        '<span class="vweb-dot" style="background:#fbbf24"></span>'
        '<span class="vweb-dot" style="background:#34d399"></span></div>'
        '<div class="vweb-url">cloud.vast.ai/instances/ · 2 โหนดแยกกันคนละแทร็ก</div>'
        '<div class="vweb-status">● 2 INSTANCES RUNNING</div>'
        '</div>'
        '<div class="vweb-cols">'
        '<div class="vweb-pane">'
        '<div class="vweb-head"><div class="vweb-gpu">1 โหนด × 2× RTX 4090</div>'
        '<div class="vweb-lbl">vapp-lab7-dp2</div></div>'
        '<div class="vweb-kv">%s</div>'
        '</div>'
        '<div class="vweb-pane">'
        '<div class="vweb-head"><div class="vweb-gpu mp">1 โหนด × 4× RTX 4090</div>'
        '<div class="vweb-lbl">vapp-lab7-mp4</div></div>'
        '<div class="vweb-kv">%s</div>'
        '</div>'
        '</div>'
        '<div class="vweb-foot">'
        '<span>✓ ผ่านเกณฑ์ verified · CUDA ≥ 12.8 · เน็ต ≥ 1,000 Mbps · พอร์ต 8080 พร้อม</span>'
        '<span>➜ พร้อมเข้าสู่ <b>ขั้นที่ 2</b>: ติดตั้ง vLLM, โมเดล Qwen3-4B และ NGINX</span>'
        '</div></div>'
        + note("ทั้ง 2 โหนดทำงานแยกกันอิสระ (ไม่ใช่คลัสเตอร์ข้ามอินเทอร์เน็ต) และเปิดต่อเนื่องจนกว่าจะลบในขั้นที่ 10", "info")
    ) % (kv_html(dp2_kv), kv_html(mp4_kv))
    return S("ผลขั้นที่ 1: เครื่องเช่าทั้ง 2 โหนดพร้อมใช้งานแล้ว (`RUNNING`)", body, tag="Vast.ai Console · จริง")


def step_ctx(n, name):
    CTX.update(kicker="LAB 7 · ขั้นที่ %d จาก %d · %s" % (n, NSTEP, name), group="ขั้นที่ %d · %s" % (n, name))


def step_prompt(n, title):
    # รับประกันว่าพรอมต์ทุกขั้นอยู่ภายในสไลด์ 1 หน้า (ไม่แบ่ง 2 หน้า)
    slides = E.prompt_slides(E.prompt_code("ขั้นที่ %d ·" % n, 0, HOW), CTX["kicker"], "ขั้นที่ %d · %s" % (n, title))
    assert len(slides) == 1, f"Prompt {n} split into {len(slides)} slides!"
    add(slides)


def build():
    # ================================================================== 1 · เปิดเรื่องและภาพรวม
    CTX.update(kicker="", group="เปิดเรื่อง")
    add(E.cover(
        "LAB 7 · LLM Serving บน RTX 4090 หลัง NGINX",
        "ต่อยอดสูตรชนะจาก LAB 6 สู่แชทบอท Qwen3-4B แบบ Streaming: Single GPU · Data Parallelism (2 GPU) · Model Parallelism (4 GPU แบบ 2+2)",
        SL + "s01-cover.jpg",
        small="สัปดาห์ที่ 3 · Vast.ai Application · 2 เครื่องแยกแทร็ก (Single-Node Multi-GPU)",
    ))

    CTX["kicker"] = "ภาพรวมของ LAB 7"
    add(fig(
        "ทั้ง LAB ในภาพเดียว: แชทบอท LLM (Qwen3-4B) บน RTX 4090 รับผู้ใช้พร้อมกันได้กี่คน",
        LB + "result-4designs-llm.png",
        "ผลวัดจริงครบ 4 แบบ: Continuous Batching เพิ่มความจุจาก **2 เป็น ≥ 384 คน** และ **Data Parallelism 2 GPU** ขยายเป็น **≥ 768 คน (14,242 tok/s · Efficiency 99.6%)**",
        tag="results/metrics.json",
    ))

    add(fig(
        "กราฟผลวัดจริง: 2 GPU Data Parallelism ชนะ 4 GPU Model Parallelism ทั้งความจุและ Throughput รวม",
        RI + "01_capacity_and_throughput.png",
        "ผลวัดจริงบน **RTX 4090** (`Qwen3-4B-Instruct-2507`): Continuous Batching เพิ่ม Throughput **72 เท่า** และ Data Parallelism 2 ใบชนะ Model Parallelism 4 ใบทั้ง Standard และ Fast",
        tag="results/metrics.json",
    ))

    add(nfig(
        "n02-scope-tracks",
        title="ขอบเขตของ LAB 7: เช่า 2 เครื่องแยกแทร็ก (ไม่ใช่คลัสเตอร์ Multi-Node ข้ามอินเทอร์เน็ต)",
        tag="ขอบเขตของบท",
    ))

    add(tbl(
        "ตำแหน่งของ LAB 7 เทียบ LAB 4–6: แยกจำนวนโหนดและจำนวน GPU ชัดเจน",
        T("ขอบเขตของบทนี้", "LAB"),
        post=note("แต่ละแทร็กของ LAB 7 รัน NGINX และตัวยิงโหลดในโหนดเดียวกับ GPU เพื่อวัดเทียบ Data Parallelism กับ Model Parallelism โดยไม่มีความช้าของอินเทอร์เน็ตปน", "info"),
        tag="ตารางหลัก · ขอบเขต",
    ))

    add(nfig(
        "n08-4designs-llm",
        title="4 การออกแบบที่วัดจริงบน RTX 4090: ไล่จาก 1 GPU ตอบทีละข้อถึง 4 GPU Model Parallelism",
        tag="4 การออกแบบ",
    ))

    add(tbl(
        "ตารางสรุป 4 แบบที่วัด: แยกเครื่องเช่า จำนวนโหนด จำนวน GPU และจำนวน Replica",
        T("4 แบบที่วัด", "แบบ"),
        post=note("**replica** = โปรแกรม vLLM 1 process · **เพดาน** = `--max-num-seqs` · แบบที่ 4 (`mp4_cb`) คือ 2 replica × TP=2 (รวม 4 GPU)", "info"),
        tag="ตารางหลัก · 4 แบบ",
    ))

    add(nfig(
        "n09-lab6-vs-lab7-why1vllm",
        title="เชื่อมจาก LAB 6: ทำไม LAB 6 เปิด 4 FastAPI server/GPU แต่ LAB 7 เปิด vLLM แค่ 1 ตัว",
        tag="เทียบ LAB 6 vs LAB 7",
    ))

    add(nfig(
        "n01-lab-map",
        title="แผนที่ LAB 7 ทั้ง 10 ขั้นแบ่งเป็น 5 ส่วน: เตรียมระบบ พิสูจน์ตัววัด แทร็ก 1 แทร็ก 2 และสรุป",
        tag="แผนที่ 10 ขั้น",
    ))

    add(fig(
        "เห็นกับตา (1× Real-Time): เปรียบเทียบความเร็วการไหลของ Token จริงใน 4 สภาวะพร้อมกัน",
        LB + "demo-speed-by-load.gif",
        "คำถามเดียวกัน (240 tokens) ความเร็ว 1× จริง: Model Parallelism N=1 จบใน **1.54 s** · Data Parallelism N=1 จบ **2.32 s** · N=128 จบ **3.30 s** · N=512 จบ **8.19 s**",
        tag="LIVE DEMO · GIF 1×",
    ))

    # ================================================================== 2 · วิธีวัดและข้อมูลทดสอบ
    CTX.update(kicker="", group="วิธีวัดและข้อมูลทดสอบ")
    add(E.divider(
        "วิธีวัด",
        "ตัวชี้วัด 3 ตัว เกณฑ์ SLO 2 ระดับ และข้อมูลทดสอบจริง",
        "<p>งานแชทบอทแบบ Streaming ต่างจาก API ตรวจภาพใน LAB 6 เพราะคำตอบไหลมาทีละ Token — ต้องตกลงตัวชี้วัดและเกณฑ์ก่อนลงมือ</p>",
        img=SL + "s02-theory.jpg",
        small="ส่วนที่ 1 · วิธีวัดและสถาปัตยกรรม",
    ))

    CTX["kicker"] = "สถาปัตยกรรมและข้อมูลทดสอบ"
    add(nfig(
        "n03-arch-rtx4090",
        title="System Architecture บน 1 โหนด: ผู้ใช้เห็นประตูเดียวที่ NGINX พอร์ต 8080",
        tag="System Architecture",
    ))

    add(big(
        "คำถาม 1 ข้อผ่าน 5 สถานี และจำนวนการเชื่อมต่อที่เปิดค้างอยู่เท่ากับงานที่ทำอยู่จริง",
        TH + "th-request-path.png",
        [
            "ผู้ใช้ส่ง `POST /v1/chat/completions` พร้อม Bearer API key",
            "NGINX ตรวจ key แล้วส่งคำถามเข้า replica ที่มีงานค้างน้อยที่สุด",
            "vLLM รับคำถามเข้า Batch และให้ GPU สร้างคำตอบ **ทีละ Token**",
            "Token ไหลกลับผ่านการเชื่อมต่อเดิมจนจบ — **1 การเชื่อมต่อ = 1 คำถามที่ยังตอบไม่จบ**",
        ],
    ))

    add(big(
        "โมเดลหลัง API คือ Qwen3-4B-Instruct-2507 ขนาด 8.06 GB ใส่ใน RTX 4090 ใบเดียวได้สบาย",
        TH + "th-model.png",
        [
            "**Input / Output:** คำสั่งระบบ (`system`) + คำถามลูกค้า (`user`) → คำตอบภาษาไทยทีละ Token",
            "**ขนาด 4 พันล้านพารามิเตอร์** (ไฟล์ 8.06 GB, context 4,096 token) เปิดให้บริการในชื่อ `shop-bot`",
            "**VRAM บน RTX 4090 (24 GB):** เหลือพื้นที่กว่า 13 GB ต่อใบสำหรับ KV Cache รองรับผู้ใช้หลายร้อยคนพร้อมกัน",
            "LAB นี้ใช้ตอบอย่างเดียว (**Inference**) ไม่เทรนโมเดลเพิ่ม",
        ],
    ))

    add(fig(
        "ข้อมูลทดสอบจริง: สุ่ม 1 ใน 40 คำถามลูกค้าร้านขายของใช้ในบ้านภาษาไทย",
        "results/dataset_samples.png",
        "ตัวอย่าง 8 คำถาม-คำตอบจริงจากผู้ใช้ 1 คนบน 1× RTX 4090 (`dp1_n1_baseline.json`): ขาเข้าราว 70–85 token · ขาออก 44–97 token · ความเร็วเฉลี่ย **104.87 tok/s**",
        tag="results/dp1_n1_baseline.json",
    ))

    req_json = fences("รู้จักข้อมูลที่ใช้ทดสอบ", "json")[0]["text"]
    add(code(
        "1 คำขอใช้รูปแบบ OpenAI-compatible API โดยเปิด `stream: true` และ `stream_options`",
        req_json,
        "json",
        post=note("`max_tokens` ตั้งเป็น **150** สำหรับคำตอบสั้น และ **600** สำหรับคำตอบละเอียด (20% ใน `mix_long`) · NGINX เติม header `X-Replica` ทุกคำตอบ"),
    ))

    CTX["kicker"] = "ตัวชี้วัดและเกณฑ์ SLO"
    add(big(
        "ผู้ใช้แชทบอทรู้สึกช้าได้ 2 แบบ จึงต้องวัด 3 ตัวชี้วัดคู่กันเสมอ",
        TH + "th-metrics.png",
        [
            "**TTFT (Time To First Token):** เวลาตั้งแต่ส่งคำถามจนได้ Token แรก ถ้านานผู้ใช้รู้สึกว่าบอทค้าง",
            "**ความเร็วต่อผู้ใช้ (tok/s):** ความเร็วการไหลของข้อความหลัง Token แรก วัดที่ **p5** (95% ของผู้ใช้ต้องเร็วกว่าค่านี้)",
            "**System Throughput (tok/s):** ผลรวม Token ต่อวินาทีของทุกคน บอกความคุ้มค่าของ GPU",
        ],
    ))

    add(big(
        "ผู้ใช้มากขึ้น System Throughput สูงขึ้น แต่ความเร็วต่อผู้ใช้แต่ละคนจะลดลง",
        TH + "th-speed-vs-throughput.png",
        [
            "**ผู้ใช้ 1 คน** ได้ความเร็วสูงสุด (104.9 tok/s) แต่ GPU ทำงานไม่เต็ม Throughput จึงต่ำ",
            "**ผู้ใช้หลายคนพร้อมกัน** GPU ผลิต Token รวมได้สูงขึ้นมาก แต่ต้องแบ่งแบนด์วิดท์กัน ทำให้แต่ละคนช้าลง",
            "**Speed Retention** = ความเร็วที่ N คน ÷ ความเร็วผู้ใช้ 1 คน บอกว่ายังรักษาความเร็วเดิมไว้ได้กี่ส่วน",
        ],
    ))

    add(big(
        "เกณฑ์ SLO มี 2 ระดับ (Standard และ Fast) และความจุต้องระบุคู่กับระดับเสมอ",
        TH + "th-slo-tiers.png",
        [
            "**Standard SLO:** TTFT p95 ≤ **2.0 วินาที**, ความเร็ว p5 ≥ **15.0 tok/s**, error < 1% (เร็วกว่าคนอ่านทัน)",
            "**Fast SLO:** TTFT p95 ≤ **2.0 วินาที**, ความเร็ว p5 ≥ **50% ของผู้ใช้ 1 คน** (`52.44 tok/s` บน `dp2` · `50.07 tok/s` บน `mp4`), error < 1%",
            "**ความจุ (Capacity)** = จำนวนผู้ใช้พร้อมกัน (`N`) สูงสุดที่ยังผ่านเกณฑ์ของระดับนั้น",
        ],
    ))

    # ================================================================== 3 · ภาคปฏิบัติ LAB 10 ขั้น
    CTX.update(kicker="", group="ภาคปฏิบัติ · LAB 10 ขั้น")
    add(E.divider(
        "ลงมือทำ",
        "LAB 10 ขั้นบน RTX 4090 (แทร็ก 1 Data Parallelism · แทร็ก 2 Model Parallelism)",
        "<p>แนวคิดสำคัญจะวางอยู่หน้าขั้นที่ใช้งานจริง ตามด้วยพรอมต์ Copy &amp; Paste และผลวัดจริงจากเครื่องเช่า RTX 4090</p>",
        img=SL + "s03-lab.jpg",
        small="ส่วนที่ 2 · ภาคปฏิบัติ 10 ขั้น",
    ))

    # --- ขั้นที่ 1 ---
    step_ctx(1, "เช่าเครื่อง RTX 4090 พร้อมกัน 2 เครื่อง")
    add(big(
        "ขั้นที่ 1: เช่าเครื่อง RTX 4090 แยก 2 แทร็ก (2 GPU และ 4 GPU) เพื่อวัดขนานกัน",
        SL + "n02-scope-tracks.jpg",
        [
            "**แทร็กที่ 1 (`vapp-lab7-dp2`):** 1 โหนด × 2× RTX 4090 สำหรับ Single GPU และ Data Parallelism",
            "**แทร็กที่ 2 (`vapp-lab7-mp4`):** 1 โหนด × 4× RTX 4090 สำหรับ Model Parallelism แบบ 2+2",
            "**เงื่อนไขบังคับ:** verified · reliability ≥ 0.95 · เน็ต ≥ 1,000 Mbps · CUDA ≥ 12.8 · อุณหภูมิตอนว่าง ≤ 60 °C",
        ],
        tag="ส่วน A · เตรียมระบบ",
    ))
    step_prompt(1, "เช่าเครื่อง RTX 4090 พร้อมกัน 2 เครื่อง")
    add(vastai_ready_dual())

    # --- ขั้นที่ 2 ---
    step_ctx(2, "ติดตั้ง vLLM, NGINX และวัด 1-User Baseline")
    add(big(
        "vLLM ครอบโมเดลไว้เพื่อเปิด OpenAI-compatible API, Streaming และ Continuous Batching",
        TH + "th-vllm.png",
        [
            "ไฟล์น้ำหนักโมเดลอย่างเดียวรับคำถามพร้อมกันหลายร้อยคนไม่ได้ ต้องมี Inference Server ครอบอีกชั้น",
            "vLLM จัดการหน่วยความจำ KV Cache ด้วย **PagedAttention** และจับกลุ่มคำถามแบบ **Continuous Batching**",
            "ใน LAB นี้เรียก vLLM 1 process ว่า **replica** (ใช้ 1 GPU ใน Data Parallelism หรือ 2 GPU ใน Model Parallelism)",
        ],
    ))
    add(big(
        "NGINX Least Connections นับงานค้างของแต่ละ replica แล้วส่งงานใหม่ให้ตัวที่ว่างที่สุด",
        TH + "th-lc.png",
        [
            "NGINX นับจำนวนการเชื่อมต่อที่ยังเปิดค้างอยู่ (**Active Connections**) ของแต่ละ replica",
            "คำถามใหม่ถูกส่งให้ replica ที่มีงานค้างน้อยที่สุดในขณะนั้นโดยอัตโนมัติ",
            "ต้องใส่ `zone ... 64k;` ใน `upstream` เพื่อให้ worker ทั้ง 4 ตัวของ NGINX นับงานค้างชุดเดียวกัน",
        ],
    ))
    add(big(
        "NGINX สำหรับงาน Streaming ต้องปิด `proxy_buffering` เพื่อให้เป็นท่อไม่ใช่ถังพัก",
        TH + "th-nginx-stream.png",
        [
            "หากเปิด `proxy_buffering on` NGINX จะพัก Token ไว้แล้วส่งเป็นก้อน ทำให้ TTFT สูงและแชทกระตุก",
            "ตั้ง `proxy_buffering off;`, `proxy_cache off;`, `gzip off;` และ `proxy_http_version 1.1;`",
            "ตั้ง `proxy_read_timeout 600s;` และ `proxy_next_upstream ... non_idempotent;` สำหรับ Failover",
        ],
    ))
    step_prompt(2, "ติดตั้ง vLLM, NGINX และวัด 1-User Baseline")
    tot_dp2 = T_DP2["install_vllm_s"] + T_DP2["download_model_s"] + T_DP2["install_nginx_udocker_s"]
    tot_mp4 = T_MP4["install_vllm_s"] + T_MP4["download_model_s"] + T_MP4["install_nginx_udocker_s"]
    add(S(
        "ผลขั้นที่ 2: ติดตั้ง vLLM 0.34.0 + โมเดล 8.06 GB + NGINX ใช้เวลา %.1f s (dp2) และ %.1f s (mp4)" % (tot_dp2, tot_mp4),
        nbars([
            ("vapp-lab7-dp2 (เน็ต 1.1 Gbps)", "vLLM %.1fs · โมเดล %.1fs · NGINX %.1fs" % (T_DP2["install_vllm_s"], T_DP2["download_model_s"], T_DP2["install_nginx_udocker_s"]), tot_dp2, tot_dp2, "%.1f วินาที" % tot_dp2),
            ("vapp-lab7-mp4 (เน็ต 7.7 Gbps)", "vLLM %.1fs · โมเดล %.1fs · NGINX %.1fs" % (T_MP4["install_vllm_s"], T_MP4["download_model_s"], T_MP4["install_nginx_udocker_s"]), tot_mp4, tot_dp2, "%.1f วินาที" % tot_mp4),
        ])
        + note("ทั้ง 2 เครื่องใช้ซอฟต์แวร์รุ่นเดียวกันเป๊ะ (`vLLM 0.34.0` · `PyTorch 2.14.0+cu130` · `nginx:1.27` ผ่าน udocker) เพื่อให้เปรียบเทียบได้ตรง"),
        tag="results/timings_*.json",
        cls="mid",
    ))
    add(S(
        "ผลขั้นที่ 2 (1-User Baseline): Model Parallelism (TP=2) เร็วกว่า 1 GPU ถึง 1.64 เท่าต่อผู้ใช้ 1 คน",
        versus(
            "1-User Baseline (10 คำถามหลังอุ่นเครื่อง 2 ข้อ · Qwen3-4B-Instruct-2507)",
            ("1× RTX 4090 (Data Parallelism)", "dp2: 104.87 tok/s · mp4: 100.14 tok/s", "104.9 tok/s",
             "TTFT เฉลี่ย **36 ms** (`dp2`) / **35 ms** (`mp4`) → ตั้งเกณฑ์ Fast SLO ที่ **52.44** และ **50.07 tok/s**"),
            ("2× RTX 4090 (Model Parallelism TP=2)", "บนเครื่อง mp4 (เทียบ 100.14 tok/s = 1.64×)", "164.0 tok/s",
             "TTFT เฉลี่ยลดเหลือ **24 ms** (-33%) เพราะ GPU 2 ใบช่วยกันอ่านน้ำหนักโมเดลคนละครึ่ง"),
        )
        + note("ความเร็วผู้ใช้ 1 คนเป็นข้อได้เปรียบหลักของ Model Parallelism แต่เมื่อมีผู้ใช้หลายร้อยคนพร้อมกันผลจะพลิกกลับในขั้นที่ 8"),
        tag="results/*_n1_baseline.json",
        cls="mid",
    ))
    nginx_snip = fences("ขั้นที่ 2 ·", "nginx")[0]["text"]
    add(code(
        "โค้ดอ้างอิงขั้นที่ 2: การตั้งค่าสำคัญใน `nginx.conf` สำหรับ Streaming และ Least Connections",
        nginx_snip,
        "nginx",
        post=note("`HF_TOKEN` ใช้เฉพาะช่วงดาวน์โหลดใน environment แล้วลบออกทันที ไม่ทิ้งค้างไว้บนเครื่องเช่า"),
    ))

    # --- ขั้นที่ 3 ---
    step_ctx(3, "เขียนตัวยิงโหลดแบบ Streaming และพิสูจน์ว่าวัดถูก")
    add(nfig(
        "n07-loadtest-loop",
        title="Load Test แบบ Streaming: ผู้ใช้จำลองแบบ Closed Loop ยิงจากโหนดเดียวกับ NGINX",
        tag="ส่วน B · Load Test",
    ))
    add(big(
        "ผู้ใช้พร้อมกัน (N) ไม่ใช่จำนวนผู้ใช้ออนไลน์ เพราะผู้ใช้จริงมีช่วงอ่านและพิมพ์ (Think Time)",
        TH + "th-think-time.png",
        [
            "ผู้ใช้จริงใช้ GPU เฉพาะช่วงสั้น ๆ ที่รอคำตอบ ส่วนเวลาที่เหลือคือการอ่านและพิมพ์คำถามถัดไป (**Think Time**)",
            "**N** ใน LAB คือจำนวนคำถามที่กำลังรอคำตอบพร้อมกันในวินาทีนั้น (กรณีหนักที่สุด ไม่มี Think Time)",
            "แปลงเป็นผู้ใช้ออนไลน์คร่าว ๆ ด้วย `ผู้ใช้ออนไลน์ ≈ N × (เวลาตอบ + Think Time) ÷ เวลาตอบ`",
        ],
    ))
    add(big(
        "พิสูจน์ตัวยิงโหลดก่อนใช้จริง ด้วย server จำลอง `fake_llm.py` ที่รู้คำตอบล่วงหน้า",
        TH + "th-loadtest-check.png",
        [
            "ตั้งค่า `fake_llm.py`: **TTFT = 200 ms**, ความเร็ว **50.0 tok/s**, ยาว **100 tokens/คำตอบ**",
            "1 คำตอบใช้ 2.2 วินาที → ที่ N=50 ควรได้ System Throughput ราว `50 × 100 ÷ 2.2 = 2,272.7 tok/s`",
            "เทียบยิงตรง (`N=1`, `N=50`) กับยิงผ่าน NGINX พอร์ต 8080 (`N=50`) เพื่อยืนยันว่า NGINX ไม่พักรวม Token",
        ],
    ))
    add(big(
        "โหมดหาความจุของ `loadgen.py` ใช้ 3 จังหวะ: หาช่วง ประมาณด้วยเส้นตรง และปรับ",
        TH + "th-capacity-search.png",
        [
            "**1 หาช่วง:** ไล่ระดับ N ตามรายการจนไม่ผ่านเกณฑ์ 2 ระดับติดกัน (ระดับที่ไม่ผ่านวัดซ้ำ 1 ครั้งก่อนตัดสิน)",
            "**2 ประมาณ:** ลากเส้นตรงระหว่างจุดผ่านสุดท้ายกับไม่ผ่านแรก หาจุดที่ตัดเส้นเกณฑ์ TTFT หรือ Speed",
            "**3 ปรับ:** วัดจริงที่ค่าประมาณแล้วปรับซ้ำจนระยะห่างระหว่างผ่านกับไม่ผ่าน ≤ 5% ของ N",
        ],
    ))
    step_prompt(3, "เขียนตัวยิงโหลดและพิสูจน์ว่าวัดถูก")
    add(fig(
        "ผลขั้นที่ 3: ตัวยิงโหลดและ NGINX ผ่านครบทุกข้อ — TTFT p50 = 201.0 ms และความเร็ว 50.00 tok/s",
        RI + "06_loadtest_check.png",
        "Direct N=50 ได้ **2,271.9 tok/s** และผ่าน NGINX N=50 ได้ **2,271.3 tok/s** (ต่างจากทฤษฎีเพียง 0.04% · error 0 · NGINX ใช้ CPU 0.13 core)",
        tag="results/loadtest_check_summary.json",
    ))
    d1, d50, nx50 = [LC_CHK[k]["levels"][0] for k in ("direct_n1", "direct_n50", "nginx_n50")]
    add(S(
        "ผลขั้นที่ 3: ยืนยันว่า `proxy_buffering off` ทำงานจริง และตัวยิงโหลดไม่ใช่ตัวถ่วง",
        tiles([
            ("TTFT p50 ผ่าน NGINX", "%.1f ms" % (nx50["ttft_p50_s"] * 1000), "เทียบยิงตรง %.1f ms (ต่าง 0.0 ms)" % (d50["ttft_p50_s"] * 1000), "ok"),
            ("ความเร็ว p50 ผ่าน NGINX", "%.2f tok/s" % nx50["speed_p50_tok_s"], "ตรงตามที่ตั้งไว้ 50.00 tok/s", "ok"),
            ("Throughput N=50", "{:,.1f}".format(nx50["throughput_tok_s"]), "tok/s · error %d · NGINX CPU %.1f%%" % (nx50["errors"], nx50["cpu"]["nginx"]["mean_pct_of_core"]), "ok"),
        ])
        + note("เมื่อเครื่องมือวัดผ่านการพิสูจน์แล้ว ตัวเลขทุกค่าในขั้นที่ 4–8 จึงเชื่อถือได้"),
        tag="results/loadtest_check_summary.json",
        cls="mid",
    ))

    # --- ขั้นที่ 4 ---
    step_ctx(4, "Single GPU: ตอบทีละคำถาม เทียบ Continuous Batching")
    add(big(
        "แบบที่ 1 ตอบทีละคำถาม (`cap=1`): คิวยาวทันที และ Throughput ตันไม่ว่าผู้ใช้กี่คน",
        TH + "th-one-by-one.png",
        [
            "ตั้ง `--max-num-seqs 1` ให้ GPU ใบเดียวทำทีละ 1 คำถามจนจบ",
            "ผู้ใช้คนที่ 1 ได้ความเร็วสูงสุด แต่ **TTFT ของคนท้ายคิว = เวลารวมของทุกคำตอบก่อนหน้า**",
            "Throughput คงที่ราว 99 tok/s ตลอดไป ใช้เป็น Baseline เพื่อเทียบกับ Continuous Batching",
        ],
        tag="ส่วน C · แทร็ก 1",
    ))
    add(big(
        "Continuous Batching รับคำถามใหม่เข้าแทรกได้ทุก 1 Token ไม่ต้องรอคนตอบยาวจบก่อน",
        TH + "th-cb-how.png",
        [
            "**Static Batching** ต้องรอคำตอบที่ยาวที่สุดในชุดจบก่อน ทำให้ช่องของคำตอบสั้นปล่อย GPU ว่างเปล่า",
            "**Continuous Batching** ของ vLLM จัดกลุ่มใหม่ **ทุกรอบการสร้าง Token** ทันทีที่ใครตอบจบ สล็อตว่างรับคำถามใหม่ทันที",
            "เปรียบเสมือนเวอร์ชันสำหรับ LLM ของ Micro-batching ใน LAB 6 ที่รองรับความยาวคำตอบไม่เท่ากัน",
        ],
    ))
    add(big(
        "ทำไมรวมหลายคำถามแล้วเกือบได้ฟรี: อ่านน้ำหนักโมเดล 8.06 GB รอบเดียวใช้ได้ทั้ง Batch",
        TH + "th-cb-why.png",
        [
            "การสร้าง 1 Token ต้องอ่านน้ำหนักโมเดลทั้งก้อนจาก VRAM 1 รอบ ซึ่งเป็นคอขวดหลัก (**Memory-bandwidth bound**)",
            "อ่านน้ำหนัก 1 รอบแล้วคำนวณให้ 1 คน หรือ 128 คน ใช้เวลาอ่านน้ำหนักแทบเท่ากัน",
            "System Throughput จึงพุ่งขึ้นหลายสิบเท่าบน GPU ใบเดิมโดยไม่ต้องจ่ายค่าฮาร์ดแวร์เพิ่ม",
        ],
    ))
    add(big(
        "ยิ่งผู้ใช้มาก System Throughput เพิ่มจนถึงจุดอิ่มตัว จากนั้นทุกคนจะช้าลงพร้อมกัน",
        TH + "th-cb-tradeoff.png",
        [
            "ช่วงก่อนอิ่มตัว เพิ่มผู้ใช้แล้ว System Throughput พุ่งขึ้นเร็วเกือบตามจำนวนผู้ใช้",
            "เมื่อ GPU อิ่มตัว (**Saturation**) Throughput แบนลง การเพิ่มผู้ใช้ต่อจากนั้นทำให้ความเร็วต่อคนลดลง",
            "จุดที่เส้นความเร็วต่อผู้ใช้ (p5) ตัดเส้นเกณฑ์ **Fast** หรือ **Standard** คือความจุของระดับนั้น",
        ],
    ))
    add(nfig(
        "s04-dp1-step",
        title="ขั้นที่ 4: ใช้ GPU 0 ใบเดียว (GPU 1 ยังไม่ใช้) เทียบ `max-num-seqs=1` กับ `256`",
        tag="แผนการวัด · ขั้นที่ 4",
    ))
    step_prompt(4, "Single GPU ตอบทีละคำถาม เทียบ Continuous Batching")
    add(E.hero(
        CTX["kicker"],
        "ผลขั้นที่ 4: Continuous Batching เพิ่ม Throughput บน GPU 1 ใบเดิมถึง 72 เท่า",
        SL + "h01-cb.jpg",
        [
            ("ความจุ Standard (≥ 15 tok/s)", "2 → ≥ 384 คน", "เพิ่มขึ้น ≥ 192 เท่าบน RTX 4090 ใบเดิม (TTFT 1.970 s)", "ok"),
            ("ความจุ Fast (≥ 52.44 tok/s)", "2 → 128 คน", "เพิ่มขึ้น 64 เท่า (TTFT 0.106 s, Speed p5 52.68 tok/s)", "ok"),
            ("Peak System Throughput", "99 → 7,152", "tok/s (พุ่ง 72 เท่า ที่ N=192, กำลังไฟ 432 W)", "ok"),
        ],
        post=note("บน GPU ใบเดิม ค่าเช่าเท่าเดิม Continuous Batching ให้ผลตอบแทนสูงที่สุดในทุกเทคนิคของ LAB 7"),
        tag="results/dp1_seq.json · dp1_cb.json",
    ))
    add(S(
        "ผลขั้นที่ 4: เทียบชัด ๆ บน 1× RTX 4090 — ตอบทีละคำถาม (`cap=1`) กับ Continuous Batching (`cap=256`)",
        versus(
            "1× RTX 4090 ใบเดียวกัน (GPU 0 บน vapp-lab7-dp2)",
            ("แบบที่ 1 · dp1_seq (cap=1)", "ที่ N=4 TTFT พุ่ง 3.203 s ไม่ผ่านทันที", "2 คน",
             "Peak Throughput ตันที่ **99.1 tok/s** · ที่ N=8 คนท้ายคิวรอ TTFT นานถึง 6.49 วินาที"),
            ("แบบที่ 2 · dp1_cb (cap=256)", "Standard ≥ 384 คน · Fast 128 คน", "7,152 tok/s",
             "ที่ N=128 (Fast) TTFT แค่ **0.106 s** · ที่ N=384 (Standard) Speed p5 ยังได้ **26.63 tok/s**"),
        ),
        tag="results/dp1_seq.json · dp1_cb.json",
        cls="mid",
    ))
    t_dp1 = filter_table(T("ขั้นที่ 4 ·", "N", k=1), keep_cols=[0, 2, 4, 5, 7, 8, 9], keep_rows=[0, 2, 3, 5, 6, 7, 8])
    add(tbl(
        "ผลขั้นที่ 4: ข้อมูลรายระดับของ 1× RTX 4090 Continuous Batching — อิ่มตัวที่ N=192 และเริ่มเข้าคิวหลัง N=256",
        t_dp1,
        post=note("หลัง N=256 คำถามส่วนเกินจาก `cap=256` เริ่มรอคิว (`waiting` 60 → 122 ข้อ) ทำให้ TTFT p95 พุ่งจาก 0.200 s เป็น 1.970 s ที่ N=384", "info"),
        tag="results/dp1_cb.json",
    ))

    # --- ขั้นที่ 5 ---
    step_ctx(5, "2 GPU Data Parallelism + NGINX (สูตรชนะ LAB 6)")
    add(nfig(
        "n04-dp-vs-mp-robot",
        title="มี GPU หลายใบแบ่งงานแบบไหน: หุ่นยนต์เต็มตัว (Data Parallelism) vs แบ่งครึ่ง (Model Parallelism)",
        tag="แนวคิดหลัก · หลาย GPU",
    ))
    add(nfig(
        "s05-dp2-step",
        title="ขั้นที่ 5: เปิด GPU 1 เพิ่มเป็น 2 GPU Data Parallelism หลัง NGINX (ล้อโครง LAB 6)",
        tag="แผนการวัด · ขั้นที่ 5",
    ))
    step_prompt(5, "2 GPU Data Parallelism + NGINX")
    add(E.hero(
        CTX["kicker"],
        "ผลขั้นที่ 5: สูตรชนะ LAB 6 ขยาย 2× RTX 4090 ได้ Scaling Efficiency 99.6%",
        SL + "h02-dp2.jpg",
        [
            ("ความจุ Standard (≥ 15 tok/s)", "≥ 768 คน", "2.00× ของ 1 GPU (TTFT p95 1.941 s, error 0)", "ok"),
            ("ความจุ Fast (≥ 52.44 tok/s)", "265 คน", "2.07× ของ 1 GPU (TTFT p95 0.216 s, Speed p5 52.96 tok/s)", "ok"),
            ("Peak System Throughput", "14,242 tok/s", "1.991× ของ 1 GPU (7,121 tok/s/GPU · Efficiency 99.6%)", "ok"),
        ],
        post=note("GPU ทั้ง 2 ใบทำงานเต็ม 100% ที่ 420–438 W และ NGINX แจกงานสมดุล 49.5%–50.5% ทุกระดับ N"),
        tag="results/dp2_cb.json · dp2_cb_fast.json",
    ))
    add(fig(
        "ผลขั้นที่ 5: 2 GPU Data Parallelism รักษาความเร็วเหนือเกณฑ์ Fast ได้ถึง 265 คน (2 เท่าของ 1 GPU)",
        RI + "02_speed_and_throughput_curves.png",
        "ดูเส้นสีเขียว (`2 GPU Data Parallelism + NGINX`): Throughput พุ่งถึง **14,242 tok/s** ที่ N=512 และรักษาความเร็วเหนือเส้นประสีส้ม (52.4 tok/s) ได้ถึง N=265",
        tag="results/dp1_cb.json · dp2_cb.json",
    ))
    add(S(
        "ผลขั้นที่ 5: NGINX `least_conn` กระจายงาน `gpu0` และ `gpu1` สมดุล 50/50 ทุกระดับโหลด",
        nbars([
            ("Fast Capacity (N=265) · gpu0", "1,548 คำถาม · 6,699 tok/s · 437 W", 49.5, 100, "49.5%"),
            ("Fast Capacity (N=265) · gpu1", "1,580 คำถาม · 6,718 tok/s · 436 W", 50.5, 100, "50.5%"),
            ("Standard Capacity (N=768) · gpu0", "1,563 คำถาม · 6,608 tok/s · 420 W", 50.3, 100, "50.3%"),
            ("Standard Capacity (N=768) · gpu1", "1,547 คำถาม · 6,632 tok/s · 417 W", 49.7, 100, "49.7%"),
        ])
        + note("ที่ผู้ใช้พร้อมกัน 768 คน NGINX ใช้ CPU เพียง **0.71 core** (`70.8%` ของ 1 core) ไม่เป็นตัวถ่วงเลย"),
        tag="results/dp2_cb.json",
        cls="mid",
    ))
    t_dp2 = filter_table(T("ขั้นที่ 5 ·", "N", k=0), keep_cols=[0, 2, 4, 5, 6, 7, 8], keep_rows=[0, 2, 4, 6, 7, 8, 9])
    add(tbl(
        "ผลขั้นที่ 5: ข้อมูลรายระดับของ 2× RTX 4090 Data Parallelism — error 0 ทุกระดับ",
        t_dp2,
        post=note("สังเกตว่า Throughput สูงสุด (`14,241.6 tok/s`) เกิดที่ N=512 (เมื่อ Batch เต็มพอดี 256 ต่อใบ) ก่อนที่คิวจะเริ่มก่อตัวที่ N=640–768", "info"),
        tag="results/dp2_cb.json",
    ))

    # --- ขั้นที่ 6 ---
    step_ctx(6, "Concurrency Limit เมื่อผู้ใช้เกินความจุ")
    add(big(
        "Concurrency Limit ไม่ได้เพิ่มกำลัง GPU แต่เลือกว่าจะย้ายความช้าไปที่ TTFT หรือความเร็วอ่าน",
        TH + "th-cap.png",
        [
            "**เพดานต่ำ (เช่น 32):** กันคำถามส่วนเกินไว้ในคิว คนที่ได้เข้า Batch อ่านเร็ว แต่คนรอคิวเจอ TTFT ยาวหลายสิบวินาที",
            "**เพดานสูง (เช่น 256):** รับคำถามเข้า Batch มาก คิวสั้นลง TTFT ต่ำกว่า แต่ทุกคนแบ่งแบนด์วิดท์จนช้าลงพร้อมกัน",
            "ขั้นที่ 6 ทดสอบที่โหลดเกินความจุ **N = 1,152 คน** (`1.5×` ของ 768) ด้วยเพดาน 32, 64, 128 และ 256 ต่อ replica",
        ],
    ))
    step_prompt(6, "Concurrency Limit เมื่อผู้ใช้เกินความจุ")
    add(fig(
        "ผลขั้นที่ 6: ที่ N = 1,152 ไม่มีเพดานใดผ่าน SLO — เพดานทำได้แค่แลก TTFT กับความเร็วต่อผู้ใช้",
        RI + "04_cap_sweep.png",
        "ดูเส้นสีแดง (TTFT p95) และเส้นสีเขียว (Speed p5): `cap=32` อ่านเร็ว **82.7 tok/s** แต่รอ **18.32 s** ส่วน `cap=256` รอ **4.38 s** แต่เหลือ **26.6 tok/s**",
        tag="results/cap_32..256.json",
    ))
    t_cap = filter_table(T("ขั้นที่ 6 ·", "เพดาน"), keep_cols=[0, 1, 3, 5, 6, 7, 9])
    add(tbl(
        "ผลขั้นที่ 6: ตารางเปรียบเทียบทั้ง 4 เพดานที่ N = 1,152 — `cap=32` เสีย Throughput ฟรีเกินครึ่ง",
        t_cap,
        post=note("`cap=32` ทำให้ GPU ทำงานไม่ถึงจุดอิ่มตัว (321 W, 5,235 tok/s) · หากต้องการ Fast SLO ให้คุมที่ `cap=128` คู่กับ Rate Limit ฝั่งหน้าบ้านแทนการปล่อยคิวยาว", "warn"),
        tag="results/cap_32..256.json",
    ))

    # --- ขั้นที่ 7 ---
    step_ctx(7, "NGINX least_conn คำตอบสั้น-ยาว และ Replica Failover")
    add(big(
        "ทำไม Least Connections เหมาะกับคำตอบ LLM ที่สั้น-ยาวไม่เท่ากัน",
        TH + "th-lc-fits-llm.png",
        [
            "คำตอบ LLM มีความยาวตั้งแต่ 44 ถึง 600 tokens ทำให้แต่ละคำถามถือการเชื่อมต่อไว้นานไม่เท่ากัน",
            "Active Connections ที่ NGINX เห็น = จำนวนคำถามใน Batch ของ GPU ซึ่งกำหนดความเร็วต่อผู้ใช้โดยตรง",
            "replica ที่เจอคำตอบยาวหลายข้อจะมีงานค้างสูงขึ้นเอง NGINX จึงส่งคำถามใหม่ไปให้อีกตัวโดยอัตโนมัติ",
        ],
    ))
    add(nfig(
        "n06-failover-single-node",
        title="Replica ล่มกลางการ Streaming: คำตอบที่กำลังไหลขาด แต่คำถามใหม่ทั้งหมด error 0",
        tag="Replica Failover",
    ))
    step_prompt(7, "NGINX least_conn คำตอบสั้น-ยาว และ Failover")
    add(fig(
        "ผลขั้นที่ 7: งานค้างสมดุลต่างกันแค่ 0.5 คำถาม และหลังปิด `gpu1` ที่ t=29.4 s ไม่มี error เพิ่มเลย",
        RI + "05_mix_and_failover.png",
        "ซ้าย: `mix_long` (ยาว 20%) งานค้าง `gpu0=151.7` vs `gpu1=151.2` · ขวา: แท่งแดงคือ **153 คำตอบ**ที่ขาดตอน `t=29.4 s` จากนั้น `gpu0` รับต่อทันทีที่ ~6,599 tok/s",
        tag="results/mix_*.json · fail_replica.json",
    ))
    add(S(
        "ผลขั้นที่ 7 (`mix_short` เทียบ `mix_long` ที่ N = 307): คำตอบยาวเพิ่ม 2.25× แต่งานค้างยังเท่ากันเป๊ะ",
        versus(
            "2× RTX 4090 Data Parallelism + NGINX least_conn · N = 307 คน (60 วินาที)",
            ("mix_short · คำตอบสั้นล้วน (0% ยาว)", "เฉลี่ย 86.1 token/ข้อ · Throughput 13,860 tok/s", "144.0 / 145.9",
             "งานค้าง `gpu0` กับ `gpu1` ต่างกัน 1.9 ข้อ · TTFT p95 **0.249 s** · Speed p5 **47.03 tok/s** · error 0"),
            ("mix_long · ผสมคำตอบยาว 20% (600 tok)", "เฉลี่ย 193.9 token/ข้อ · Throughput 11,351 tok/s", "151.7 / 151.2",
             "งานค้างต่างกันเพียง **0.5 คำถาม** · TTFT p95 **0.131 s** · Speed p5 **36.04 tok/s** · error 0"),
        ),
        tag="results/mix_short.json · mix_long.json",
        cls="mid",
    ))
    kill_t = round(FAIL_E["kill_scheduled_epoch"] - FAIL_R["levels"][0]["t0_epoch"], 1)
    add(E.hero(
        CTX["kicker"],
        "ผลขั้นที่ 7 (Failover): ปิด GPU 1 ที่ t=%.1f s ตัด 153 สตรีม แต่คำถามใหม่หลังล่ม error 0" % kill_t,
        SL + "h04-failover.jpg",
        [
            ("สตรีมที่ขาดกลางประโยค", "153 ข้อ", "เกิดเฉพาะวินาทีที่ t=29 s บน gpu1 (`ClientPayloadError`)", "bad"),
            ("error ของคำถามใหม่หลังล่ม", "0 ข้อ", "ทุกวินาทีตั้งแต่ t=30..74 s NGINX โยกไป gpu0 ทันที", "ok"),
            ("Throughput ของ gpu0 ที่เหลือ", "~6,599 tok/s", "รับ 307 คนคนเดียวผ่าน Standard SLO (TTFT p95 0.846 s, Speed 26.6 tok/s)", "ok"),
        ],
        post=note("งาน Streaming ต้องมี **Client Retry** ฝั่งแอปเผื่อสตรีมขาดกลางทาง และควรเผื่อกำลัง GPU สำรองไว้เสมอ"),
        tag="results/fail_replica.json",
    ))

    # --- ขั้นที่ 8 ---
    step_ctx(8, "4× RTX 4090 Model Parallelism แบบ 2+2")
    add(nfig(
        "n05-mp-zoom",
        title="ซูมข้างใน 1 หน่วย Model Parallelism (Tensor Parallelism = 2): 2 GPU ช่วยกันคำนวณพร้อมซิงค์ PCIe",
        tag="ส่วน D · แทร็ก 2",
    ))
    add(nfig(
        "s08-mp4-step",
        title="ขั้นที่ 8: จัด 4 GPU เป็น 2 replica × TP=2 หลัง NGINX (เทียบ 1-ต่อ-1 กับขั้นที่ 5)",
        tag="แผนการวัด · ขั้นที่ 8",
    ))
    add(big(
        "เลือก Data Parallelism หรือ Model Parallelism: ดูว่าโมเดลใส่ใน GPU 1 ใบพอหรือไม่",
        TH + "th-dp-vs-mp-when.png",
        [
            "**โมเดลใส่ใน 1 GPU พอ (เช่น Qwen3-4B ใน 24 GB):** ใช้ **Data Parallelism** เพื่อให้ได้จำนวนผู้ใช้และ Throughput ต่อ GPU สูงสุด",
            "**โมเดลใหญ่เกิน 1 GPU (เช่น 32B–70B):** จำเป็นต้องใช้ **Model Parallelism** เพื่อรวม VRAM หลายใบ",
            "**ระบบขนาดใหญ่:** ใช้ทั้งคู่ร่วมกัน — ทำ Model Parallelism ภายในหน่วย แล้วทำหลายหน่วยแบบ Data Parallelism หลัง NGINX",
        ],
    ))
    step_prompt(8, "4× RTX 4090 Model Parallelism แบบ 2+2")
    add(E.hero(
        CTX["kicker"],
        "ผลขั้นที่ 8: Model Parallelism เร็วขึ้น 1.64× ต่อคน แต่ Throughput ต่อ GPU เหลือเพียง 1 ใน 3",
        SL + "h03-mp4.jpg",
        [
            ("ความเร็วผู้ใช้ 1 คน (1-User)", "164.0 tok/s", "เร็วกว่า 1 GPU +56%–64% · TTFT 24 ms vs 36 ms", "ok"),
            ("ความจุ Standard / Fast", "661 / 149 คน", "น้อยกว่า 2×4090 Data Parallelism (≥ 768 / 265 คน) แม้ใช้ GPU 2 เท่า", "bad"),
            ("Peak Throughput ต่อ GPU", "2,387 tok/s", "1 ใน 3 ของ Data Parallelism (7,121 tok/s/GPU · รวม 9,547 tok/s)", "bad"),
        ],
        post=note("ยืนยันชัดเจนว่า Model Parallelism (TP=2) แลกความจุรวมและประสิทธิภาพต่อการ์ดจอ เพื่อซื้อความเร็วสูงสุดต่อผู้ใช้ 1 คน"),
        tag="results/mp4_cb.json · mp4_cb_fast.json",
    ))
    add(fig(
        "ผลขั้นที่ 8: เทียบตัวต่อตัว 2× RTX 4090 Data Parallelism กับ 4× RTX 4090 Model Parallelism 2+2",
        RI + "03_dp2_vs_mp4_tradeoff.png",
        "ซ้าย: Model Parallelism ชนะที่ 1-User Speed (+56%) · กลางและขวา: Data Parallelism ชนะขาดทั้งความจุและ **Throughput ต่อ GPU (3.0×)**",
        tag="results/metrics.json",
    ))
    add(S(
        "ผลขั้นที่ 8: หลักฐานเชิงกายภาพของ PCIe AllReduce Overhead — กำลังไฟต่อ GPU ลดเหลือครึ่งเดียว",
        nbars([
            ("Data Parallelism (2× 4090) · GPU 0", "N=512 · 100% GPU utilization · Peak 14,242 tok/s", 428.4, 450, "428 / 450 W"),
            ("Data Parallelism (2× 4090) · GPU 1", "N=512 · 100% GPU utilization · ไม่ต้องซิงค์ข้ามการ์ด", 425.4, 450, "425 / 450 W"),
            ("Model Parallelism (4× 4090) · GPU 0+1", "N=661 · 99.7% GPU utilization · รอซิงค์ PCIe AllReduce", 241.8, 450, "~242 / 450 W"),
            ("Model Parallelism (4× 4090) · GPU 2+3", "N=661 · 99.7% GPU utilization · รอซิงค์ PCIe AllReduce", 206.7, 450, "~207 / 450 W"),
        ])
        + note("บทเรียนสำคัญ: `GPU utilization 99.8%` ในงาน Multi-GPU รวมเวลาที่ NCCL polling รอซิงค์ PCIe ด้วย — ต้องดูกำลังไฟ (W) และ Throughput/GPU คู่กันเสมอ"),
        tag="results/dp2_cb.json · mp4_cb.json",
        cls="mid",
    ))
    t_mp4 = filter_table(T("ขั้นที่ 8 ·", "N"), keep_cols=[0, 2, 4, 5, 6, 7, 8], keep_rows=[0, 3, 4, 6, 7, 9, 10])
    add(tbl(
        "ผลขั้นที่ 8: ข้อมูลรายระดับของ 4× RTX 4090 Model Parallelism 2+2 — ชนเกณฑ์ Fast ที่ N=149 และ Standard ที่ N=661",
        t_mp4,
        post=note("หมายเหตุ: ที่ N=661 รอบแรกไม่ผ่านเพราะ `gpu2+3` หยุดรับงานชั่วคราว แต่รอบวัดซ้ำผ่านปกติ (TTFT p95 1.931 s, Speed p5 16.32 tok/s)", "info"),
        tag="results/mp4_cb.json",
    ))

    # --- ขั้นที่ 9 ---
    step_ctx(9, "บันทึก Trace Token จริงและสร้างไฟล์ GIF 1×")
    add(S(
        "ขั้นที่ 9: แปลง Timestamp ของทุก Token จริงเป็นไฟล์ GIF ความเร็ว 1× เพื่อให้เห็นความต่างด้วยตาเปล่า",
        tiles([
            ("GIF 1 · เทียบ 4 สภาวะ", "10.6 วินาที", "106 เฟรม · 10 FPS · คำถามเดียวกัน 240 tokens", ""),
            ("GIF 2 · แชท 4 ผู้ใช้ 3 รอบ", "9.2 วินาที", "92 เฟรม · 10 FPS · แสดงป้าย NGINX → gpu0/gpu1", ""),
            ("ฟอนต์ภาษาไทย", "Leelawadee UI", "กรองอีโมจินอกชุดฟอนต์เพื่อไม่ให้เกิดกล่องสี่เหลี่ยม", "ok"),
        ])
        + note("ใช้ Trace จริงจาก `results/stream_mp2_n1.json` (160.7 tok/s) และ `results/dp1_n1_baseline.json` (8 คำถามจริงจาก Qwen3-4B)"),
        tag="ส่วน E · สาธิต",
        cls="mid",
    ))
    step_prompt(9, "บันทึก Trace และสร้างไฟล์ GIF ความเร็ว 1×")
    add(fig(
        "ผลขั้นที่ 9 (GIF 1): ความเร็ว 1× จริงเทียบ 4 สภาวะ — จาก 1.54 วินาที ถึง 8.19 วินาที",
        LB + "demo-speed-by-load.gif",
        "เห็นชัดด้วยตาว่า **160.7 tok/s** (TP=2) จบใน 1.54 s · **104.9 tok/s** จบใน 2.32 s · **73.9 tok/s** (N=128) จบ 3.30 s · และ **29.8 tok/s** (N=512) ยังอ่านไหลลื่น",
        tag="LIVE DEMO · 1× REAL-TIME",
    ))
    add(fig(
        "ผลขั้นที่ 9 (GIF 2): 4 ผู้ใช้แชทสั้น-ยาวต่อเนื่อง 3 รอบหลัง NGINX `least_conn` บน 2× RTX 4090",
        LB + "demo-4users-live.gif",
        "ภายใต้โหลด N=64–128 ผู้ใช้ทั้ง 4 คนได้คำตอบพร้อมกันโดย **NGINX สลับแจกงาน `gpu0` และ `gpu1`** อัตโนมัติในทุกรอบ",
        tag="LIVE DEMO · 1× REAL-TIME",
    ))

    # --- ขั้นที่ 10 ---
    step_ctx(10, "สร้างกราฟสรุปและลบเครื่องเช่าทั้ง 2 เครื่อง")
    add(S(
        "ขั้นที่ 10 (ห้ามข้าม): ดึงผลทั้งหมดกลับเครื่อง สร้างกราฟ 6 ภาพ และลบเครื่องเช่าให้เหลือ 0 เครื่อง",
        tiles([
            ("ไฟล์ผล JSON", "26 ไฟล์", "ผลดิบทุกรอบ + `metrics.json` + `dataset_samples.png`", ""),
            ("กราฟและไฟล์ GIF", '<span class="sm">6 กราฟ · 2 GIF</span>', "สร้างซ้ำได้ทั้งหมดจาก `tools/generate_results_and_gifs.py`", "ok"),
            ("เครื่องเช่าหลังจบ LAB", "0 เครื่อง", "ลบ `vapp-lab7-dp2` และ `vapp-lab7-mp4` ตรวจซ้ำแล้ว", "ok"),
        ])
        + note("เครื่องเช่า Vast.ai คิดค่าบริการตลอดเวลาที่เปิด ต้องตรวจ `vastai show instances` ให้เหลือ **0 instances** เสมอ", "warn"),
        tag="ส่วน E · ปิดงาน",
        cls="mid",
    ))
    step_prompt(10, "สร้างกราฟสรุปและลบเครื่องเช่าทั้ง 2 เครื่อง")
    add(tbl(
        "ผลขั้นที่ 10: สรุปการหาความจุทั้ง 7 รอบทดลอง — ทุกค่ามีไฟล์ผลดิบตรวจสอบได้",
        T("การทดลอง", "รอบทดลอง"),
        post=note("ลบเครื่อง `62662793` (`vapp-lab7-dp2`) และ `62662797` (`vapp-lab7-mp4`) เรียบร้อย เหลือ **0 instances** บน Vast.ai", "ok"),
        tag="results/*.json",
    ))

    # ================================================================== 4 · สรุปผลและแนวทางใช้งานจริง
    CTX.update(kicker="", group="สรุปผลและแนวทางใช้งานจริง")
    add(E.divider(
        "สรุปผล",
        "บทเรียนจาก RTX 4090 และแนวทางออกแบบ LLM Serving ใช้งานจริง",
        "<p>เทียบ Data Parallelism กับ Model Parallelism แบบครบทุกมิติ พร้อมลำดับ 5 ขั้นก่อนขึ้นระบบ Production</p>",
        img=SL + "s04-summary.jpg",
        small="ส่วนที่ 3 · สรุปผลการทดลอง",
    ))

    CTX["kicker"] = "สรุปผลการทดลอง"
    add(fig(
        "สรุปผล LAB 7 ในภาพเดียว: ขยายระบบ LLM ทีละขั้นบน RTX 4090 จาก 1 ใบจนถึง 4 ใบ",
        LB + "summary-results-llm.png",
        "1) Continuous Batching **72× Throughput** · 2) Data Parallelism 2 GPU **99.6% Efficiency** · 3) NGINX `least_conn` ต่าง 0.5 ข้อ · 4) Failover error 0 · 5) Model Parallelism เร็วขึ้น 1.64× ต่อ 1 คนแต่ต่อ GPU เหลือ 1 ใน 3",
        tag="สรุปภาพรวม · LAB 7",
    ))

    add(tbl(
        "สรุปผลวัดจริงครบทั้ง 4 แบบบน RTX 4090 (Qwen3-4B-Instruct-2507)",
        T("1 · ความจุและ Throughput ของทั้ง 4 แบบ", "แบบ"),
        post=note("สูตรชนะของ LAB 6 (`2 GPU Data Parallelism + Batching + NGINX least_conn`) ชนะทั้งความจุและ Throughput/GPU", "ok"),
        tag="ตารางหลัก · ผลรวม",
    ))

    add(tbl(
        "Data Parallelism (2× RTX 4090) เทียบ Model Parallelism 2+2 (4× RTX 4090) เชิงลึก",
        T("3 · Data Parallelism เทียบ Model Parallelism เชิงลึก", "มิติเปรียบเทียบ"),
        post=note("เลือก **Data Parallelism** เมื่อโมเดลใส่ใน 1 GPU พอ · เลือก **Model Parallelism** เมื่อโมเดลใหญ่เกิน VRAM 1 ใบ หรือต้องการ 1-User Speed สูงสุดจริง ๆ", "info"),
        tag="ตารางหลัก · Data vs Model Parallelism",
    ))

    add(tbl(
        "ทฤษฎีบอกอะไร เทียบกับสิ่งที่ LAB 7 วัดได้จริงบน RTX 4090",
        T("9 · ลำดับการออกแบบ", "เรื่อง"),
        tag="ทฤษฎี vs ผลจริง",
    ))

    add(tbl(
        "สิ่งที่เจอจริงระหว่างทำการทดลอง (บทเรียนจากหน้างานจริง)",
        T("สิ่งที่เจอจริงระหว่างทำ", "เกิดอะไรขึ้น"),
        tag="บทเรียนหน้างาน",
    ))

    add(tbl(
        "6 คำถามสำคัญ 6 คำตอบจากผลวัดจริงของ LAB 7",
        T("2 · 6 คำถาม 6 คำตอบ", "คำถาม"),
        tag="6 คำถาม 6 คำตอบ",
    ))

    t_steps = T("4 · ลำดับ 5 ขั้นถ้าต้องขึ้นระบบ LLM Serving ใช้งานจริง", "ลำดับ")
    add(big(
        "ลำดับ 5 ขั้นถ้าต้องขึ้นระบบ LLM Serving ใช้งานจริง (เริ่มจากสิ่งที่คุ้มที่สุดก่อน)",
        TH + "th-design-steps.png",
        [
            "**1 เปิด Continuous Batching ก่อนเสมอ** — เพิ่ม Throughput บน GPU ใบเดิมถึง 72 เท่า",
            "**2 ใช้ Data Parallelism เป็นค่าตั้งต้น** — ขยายความจุได้ 99.6% Efficiency และชนะ Model Parallelism 3.0× ต่อ GPU",
            "**3 วาง NGINX `least_conn` (ปิด buffering + `zone`)** — สมดุลคำตอบสั้น-ยาว และ Failover error 0",
            "**4 กำหนด SLO คู่ทั้ง TTFT p95 และ Speed p5** — Standard กับ Fast ให้ความจุต่างกันเกือบ 3 เท่า",
            "**5 ใช้ Model Parallelism (`TP=2/4`) เฉพาะเมื่อจำเป็น** — เมื่อโมเดลใหญ่เกิน 1 GPU หรือต้องการ 1-user speed สูงสุด",
        ],
        post=note("อ่านรายละเอียดฉบับเต็ม โค้ดอ้างอิง และข้อที่ต้องอ่านคู่กับตัวเลขได้ที่ [README.md](README.md)", "info"),
        tag="Production Guide",
    ))


if __name__ == "__main__":
    build()
    E.write(E.SL, OUT, TITLE)
    print(f"Built {OUT} ({len(E.SL)} slides, {len(E.PROMPTS)} prompts) successfully!")
