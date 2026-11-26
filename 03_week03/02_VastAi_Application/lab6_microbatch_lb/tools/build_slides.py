#!/usr/bin/env python3
"""สร้างสไลด์ LAB6_Microbatch_LB_Slides.html ของ LAB 6 (Inference บน 1 โหนด หลาย GPU · Load Test · Micro-batching · NGINX Load Balancer)

  python tools/build_slides.py            (รันจากโฟลเดอร์ lab6_microbatch_lb)

สไลด์ชุดเดียวอ่านจาก README.md ฉบับรวมหน้าเดียวของ LAB 6 เล่าตามลำดับ:
  ภาพรวม & ขอบเขต (1 โหนด หลาย GPU) → 4 การทดลองใน 1 โหนด → วิธีวัด → 12 ขั้นของ LAB (NGINX) โดยแนวคิดอยู่หน้าขั้นที่ใช้ → สรุปและข้อแนะนำ

ที่มาของเนื้อหา
- README.md (ไฟล์รวมหน้าเดียว: ขอบเขต + 4 การทดลอง + ทฤษฎี 10 เรื่อง + LAB 12 ขั้น + สรุป) อ่านตอนสร้างทุกครั้ง
- พรอมต์ 12 ขั้น (13 พรอมต์ ขั้นที่ 10 มี 2 ตอน): code fence ชนิด text ของ README.md (ตรงตัวอักษร)
- ตัวเลขผล: ตารางของ README · results/summary.json · same_machine/summary.json
- ภาพ: รวมศูนย์ไว้ใน images/ (images/theory · images/lab · images/slides) และกราฟผลจริงใน results/images/
- เครื่องมือเรนเดอร์: tools/slides_engine.py (ไม่แก้) · CSS และ layout เพิ่มเติมของเด็คนี้อยู่ในไฟล์นี้
"""
import json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import slides_engine as E
from slides_engine import md, CTX, add, note, fig, explain, tiles, cards, versus, bars, tbl, code, plain
from slides_figures import FIGS

S = E.slide
FIG = {f["img"]: f for f in FIGS}
OUT, TITLE = "LAB6_Microbatch_LB_Slides.html", "LAB 6 · Inference บน 1 โหนด หลาย GPU (Single-Node Multi-GPU) · Slides"
NSTEP = 12
TH, LB, SL = "images/theory/", "images/lab/", "images/slides/"

# ------------------------------------------------------------------ layout เพิ่มของเด็คนี้ (ไม่แก้ engine)
E.CSS += r"""
.ex.big .fig{flex:2.3 1 0}
.ex.mid2 .fig{flex:1.9 1 0}
.slide.stmt{padding:0;color:#fff}
.stmt img.bg{position:absolute;inset:0;width:100%;height:100%;object-fit:cover}
.stmt .shade{position:absolute;inset:0;background:linear-gradient(90deg,rgba(6,13,26,.94) 0%,rgba(6,13,26,.8) 50%,rgba(6,13,26,.15) 85%)}
.stmt .inner{justify-content:center;max-width:1040px}
.stmt .q{font-size:54px;font-weight:700;line-height:1.3;color:#fff}
.stmt .sub2{margin-top:30px;font-size:26px;line-height:1.55;color:#d6e4fb}
.stmt .sub2 b{color:#ffd28a}
.prog{display:flex;gap:9px;margin-top:30px;align-items:center}
.prog span{width:44px;height:10px;border-radius:5px;background:rgba(255,255,255,.2)}
.prog span.done{background:#8fe0dc}
.prog span.cur{background:var(--orange);height:14px}
.prog em{font-style:normal;font-size:19px;color:#9fb6dd;margin-left:10px}
.inner .dim{color:#9fb6dd;font-size:.9em}
.gap{height:.7em;flex:none}
.tiles+.note,.vs+.note,.bars+.note,.cards+.note,.tiles+.bars{margin-top:.9em}
.divider .inner .small{margin-bottom:26px}
.tile .num .sm{font-size:.72em}
.shotw{flex:1 1 0;min-height:0;display:flex;flex-direction:column;gap:.5em}
.shotw .fig{flex:1 1 0;min-height:200px}
.shotw .fig img{width:100%;max-height:100%}
.shotw .cap{font-size:.8em}
.pts{display:grid;grid-template-columns:repeat(var(--cols,2),minmax(0,1fr));gap:.5em 18px}
.pts .stp{font-size:.9em}
.slide th a{color:#fff}
.slide.hero .tag{color:#ffd28a;text-shadow:0 1px 6px rgba(0,0,0,.95),0 0 3px #000}
.inner h1{line-height:1.42}

/* Vast.ai Web Console Status Card (หลังขั้นที่ 1 สร้างเครื่องพร้อมใช้งาน) */
.vweb{background:#0f172a;color:#e2e8f0;border-radius:14px;overflow:hidden;border:1px solid #1e293b;margin-top:6px;box-shadow:0 10px 28px rgba(15,23,42,.18)}
.vweb-bar{display:flex;align-items:center;justify-content:space-between;background:#1e293b;padding:11px 20px;border-bottom:1px solid #334155;font-family:ui-monospace,Consolas,monospace;font-size:.82em;color:#94a3b8}
.vweb-dots{display:flex;gap:7px;align-items:center}
.vweb-dot{width:11px;height:11px;border-radius:50%;display:inline-block}
.vweb-url{background:#0f172a;padding:4px 16px;border-radius:6px;color:#cbd5e1;border:1px solid #334155}
.vweb-status{display:inline-flex;align-items:center;gap:7px;background:rgba(16,185,129,.18);color:#34d399;border:1px solid rgba(52,211,153,.45);padding:3px 13px;border-radius:999px;font-weight:700;font-size:.86em}
.vweb-body{padding:20px 26px}
.vweb-head{display:flex;align-items:center;justify-content:space-between;gap:16px;padding-bottom:14px;border-bottom:1px solid #334155;margin-bottom:16px;flex-wrap:wrap}
.vweb-gpu{font-size:1.3em;font-weight:700;color:#38bdf8}
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
"""


# ------------------------------------------------------------------ อ่าน README.md ฉบับรวมหน้าเดียว
SECS = list(E.load("README.md"))
E.SECS[:] = SECS
NS = json.loads(E.read("results/summary.json"))
S3 = json.loads(E.read("same_machine/summary.json"))   # ขั้นที่ 10.2: เครื่อง A และ B
c3 = lambda r, c, m: S3[r][c][m]["capacity"]


HERO = {"ผลขั้นที่ 6: แบบที่ 1 รับได้": SL + "h01-base.jpg",
        "ผลขั้นที่ 7: Micro-batching ทำให้": SL + "h02-batch.jpg",
        "ผลขั้นที่ 8: server 4 ตัวทำให้": SL + "h03-multi.jpg",
        "ผลขั้นที่ 9: GPU ใบที่ 2 ทำให้": SL + "h04-gpu2.jpg",
        "ผลขั้นที่ 10.1 กรณี GPU ช้า": SL + "h05-slow.jpg"}
TILE_RE = re.compile(r'<div class="tile (\w*)"><div class="num">(.*?)</div><div class="k">(.*?)</div><div class="s">(.*?)</div></div>', re.S)


def heroize(slides):
    """หน้าตัวเลขใหญ่ที่อยู่ใน HERO -> หน้าภาพเต็ม (ตัวเลขสีขาวเรียงลงฝั่งซ้าย + ป้าย "ภาพจำลอง")"""
    done = []
    for x in slides:
        key = next((k for k in HERO if plain(x.get("title") or "").startswith(k)), None)
        if not key or '<div class="tiles">' not in x["body"]:
            continue
        b = x["body"]
        i = b.index('<div class="tiles">')
        j = i + len('<div class="tiles">')
        depth, k = 1, j
        while depth:                                   # หา </div> ที่ปิด tiles
            o, c = b.find("<div", k), b.find("</div>", k)
            if o != -1 and o < c:
                depth, k = depth + 1, o + 4
            else:
                depth, k = depth - 1, c + 6
        inner, post = b[j:k - 6], b[:i] + b[k:]
        items = TILE_RE.sub(r'<div class="tile \1"><div class="num">\2</div><div class="txt"><div class="k">\3</div><div class="s">\4</div></div></div>', inner)
        x["body"] = '<div class="herobox"><div class="tiles hl">%s</div>%s</div><div class="imgnote">ภาพจำลอง</div>' % (items, post)
        x.update(cls="hero", maxfs=1.25, style=' style="background-image:url(%s)"' % HERO[key])
        done.append(key)
    missing = [k for k in HERO if k not in done]
    if missing:
        raise KeyError("HERO ไม่ตรงกับหน้าใด: %r" % missing)


def blocks(prefix):
    return E.sec(prefix)


def tabs(prefix, head0):
    """ตารางทุกตัวของหัวข้อ prefix ที่หัวคอลัมน์แรกขึ้นต้นด้วย head0 (เรียงตามลำดับใน README)"""
    out = [b for b in E.walk(blocks(prefix)) if b["t"] == "table" and plain(b["head"][0]).startswith(head0)]
    if not out:
        raise KeyError("ไม่พบตาราง %r ในหัวข้อ %r" % (head0, prefix))
    return out


def T(prefix, head0, k=0):
    return tabs(prefix, head0)[k]


def bare(s):
    return s.replace("**", "").strip()


def kv(prefix, head0, k=0, col=1):
    """ตาราง 2 คอลัมน์ขึ้นไป -> {ข้อความคอลัมน์แรก: ค่าในคอลัมน์ col}"""
    return {plain(r[0]): bare(r[col]) for r in T(prefix, head0, k)["rows"]}


def row(t, start):
    for r in t["rows"]:
        if plain(r[0]).startswith(start):
            return [bare(c) for c in r]
    raise KeyError("ไม่พบแถวที่ขึ้นต้นด้วย %r" % start)


def bullets(prefix, start="**อ่านผลอย่างไร**"):
    bl = blocks(prefix)
    for k, b in enumerate(bl):
        if b["t"] == "p" and b["lines"][0].startswith(start):
            return next(x["items"] for x in bl[k + 1:] if x["t"] == "ul")
    raise KeyError("ไม่พบรายการหลัง %r ในหัวข้อ %r" % (start, prefix))


def fences(prefix, lang):
    return [b for b in E.walk(blocks(prefix)) if b["t"] == "code" and b["lang"] == lang]


def f1(x):
    return "%.1f" % x


def n0(x):
    return "{:,}".format(int(x))


# ------------------------------------------------------------------ ชิ้นส่วนของเด็คนี้
def big(title, src, points, post="", cls="big"):
    """ภาพใหญ่ราว 70% ของความกว้าง + ข้อความ 2-4 ข้อด้านขวา"""
    s = explain(title, src, points, post)
    s["body"] = s["body"].replace('<div class="ex">', '<div class="ex %s">' % cls, 1)
    return s


def nfig(key):
    f = FIG[key]
    return big(f["title"], SL + "%s.jpg" % key, f["steps"], cls="mid2")


def statement(title, photo, q, sub):
    """ประโยคเดียวบนภาพถ่าย"""
    raw = ('<img class="bg" src="%s" alt="%s"><div class="shade"></div><div class="inner"><div class="q">%s</div>'
           '<div class="sub2">%s</div></div><div class="imgnote">ภาพจำลอง</div>') % (photo, E.esc(title), md(q), md(sub))
    return {"raw": raw, "cls": "stmt", "style": "", "title": title, "kicker": "", "tag": "", "lead": ""}


def vastai_ready(title, label, gpu_badge, specs, checks, next_text, post_note, tag="ช่วงสร้างเครื่องเสร็จ"):
    """สไลด์คั่นแสดงหน้าเว็บ Vast.ai ว่าเครื่องถูกสร้างและพร้อมใช้งาน (RUNNING) ก่อนเริ่มสร้างระบบ"""
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
        '<div class="vweb-chkh">ผลการตรวจเครื่องที่พร้อมใช้งานแล้ว</div>'
        '%s'
        '<div class="vweb-next">➜ %s</div>'
        '</div></div></div></div>%s'
    ) % (E.esc(gpu_badge), E.esc(label), kv_html, chk_html, md(next_text), post_note)
    return S(title, body, tag=tag)


# ------------------------------------------------------------------ ตัวเลขที่ใช้หลายหน้า (อ่านจาก README และ summary.json)
KEYS = ["base", "batch", "multi", "gpu2"]
ND = NS["designs"]
NCAP = [ND[k]["capacity_users"] for k in KEYS]
NSUM = T("ผลสรุป", "GPU")                 # GPU | แบบ | ความจุ | Throughput สูงสุด | p95 | เท่า
NTHR = [bare(r[3]) for r in NSUM["rows"]]
NP95 = [bare(r[4]) for r in NSUM["rows"]]
NX = [bare(r[5]) for r in NSUM["rows"]]
NEST = T("การทดลอง", "แบบ")              # แบบ | ช่วง | ค่าประมาณรอบแรก | ความจุ | ระดับ | สูตร
NSTR = NS["strategies"]
NFAIL = NS["failure"]
RR180 = [c for c in NSTR["equal"]["rr_single_level_checks"] if c["users"] == NCAP[3]]
RR250 = [c for c in NSTR["equal"]["rr_single_level_checks"] if c["users"] == NSTR["equal"]["lc"]["capacity_users"]]
NSPEED = "%.2f" % NS["scaling"]["speedup_gpu2_vs_multi"]


def step_data():
    """ผลจริงของ 12 ขั้นของ LAB จากตารางใน README.md"""
    d = {}
    d[1] = kv("ขั้นที่ 1 ·", "รายการ")
    d[2] = kv("ขั้นที่ 2 ·", "ทดสอบ")
    d[3] = kv("ขั้นที่ 3 ·", "ทดสอบจากนอกเครื่อง")
    d[4] = kv("ขั้นที่ 4 ·", "ลองยิง")
    d[5] = T("ขั้นที่ 5 ·", "ทดสอบ")
    d[6] = T("ขั้นที่ 6 ·", "N")
    d[7] = T("ขั้นที่ 7 ·", "")
    d[8] = T("ขั้นที่ 8 ·", "ที่ความจุ")
    d[9] = (T("ขั้นที่ 9 ·", "GPU"), kv("ขั้นที่ 9 ·", "ที่ความจุ"))
    d[10] = tabs("10.1 ·", "วิธี")
    d[11] = T("ขั้นที่ 11 ·", "")
    d[12] = (T("ขั้นที่ 12 ·", "ที่ความจุ"), kv("ขั้นที่ 12 ·", "ค่าใช้จ่ายจริง"))
    return d


D = step_data()
NAMES = {1: "เช่าเครื่อง 2 GPU", 2: "เขียน API ตรวจภาพ", 3: "ตั้ง NGINX เป็น Load Balancer แบบ container", 4: "เขียนตัวยิงโหลด",
         5: "พิสูจน์ว่าตัวยิงโหลดวัดถูก", 6: "แบบที่ 1: ทำทีละรูป", 7: "แบบที่ 2: Micro-batching",
         8: "แบบที่ 3: Micro-batching + server 4 ตัว", 9: "แบบที่ 4: GPU 2 ใบ", 10: "วิธีแจกงาน 3 วิธี",
         11: "server ล่มกลางทาง", 12: "กราฟ สรุป และลบเครื่อง (ห้ามข้าม)"}
SLOW = D[10][1]
EQ = D[10][0]
RRS, LCS = row(SLOW, "Round Robin"), row(SLOW, "Least Connections")
F11 = {plain(r[0]): (bare(r[1]), bare(r[2])) for r in D[11]["rows"]}
C12 = D[12][1]
LV6 = row(D[6], "29")
CMP7 = {plain(r[0]): [bare(c) for c in r[1:]] for r in D[7]["rows"]}
CAP8 = {plain(r[0]): [bare(c) for c in r[1:]] for r in D[8]["rows"]}
SC9 = row(D[9][0], "2")
E5 = NS["loadtest_check"]["E"]["measured"]

# ภาพของขั้น images/lab/sNN.png: (หัวข้อสไลด์, ข้อความข้างภาพ) · เรียบเรียงจาก [ขั้นตอน] ของพรอมต์ขั้นนั้น
PICS = {
    1: ("ขั้นที่ 1: เช่าเพียง 1 โหนด ที่มี RTX 3090 จำนวน 2 ใบในเครื่องเดียว แล้วตรวจ GPU กับ CPU", [
        "เช่า **1 โหนดเดียว (Single-Node Multi-GPU)** ที่มี RTX 3090 จำนวน 2 ใบ ติดป้าย `vapp-lab6-nginx` ไม่ใช่คลัสเตอร์หลายโหนด",
        "เงื่อนไขสำคัญคือ **CPU ที่ได้ใช้จริง 24 cores ขึ้นไป** เพราะโปรแกรม API หลายตัวและตัวยิงโหลดอยู่ในโหนดเดียวกัน",
        "เข้าไปตรวจว่าเห็น GPU ครบ 2 ใบ (`GPU 0`, `GPU 1`) และนับ CPU ที่ใช้ได้จริง"]),
    2: ("ขั้นที่ 2: AI เขียน `server.py` ที่มี 2 โหมดในตัว แล้วเปิด 1 ตัวบน GPU ใบแรก", [
        "`code/server.py` เขียนด้วย FastAPI รับรูป 1 รูปที่ `POST /v1/detect` แล้วตอบเป็น JSON",
        "server 1 ตัว (= โปรแกรม API 1 ตัว) เรียกโมเดลได้ทีละครั้ง ตั้งได้ 2 โหมด คือ **ทีละรูป** กับ **Micro-batching**",
        "ทดสอบด้วยรูป 6 รูปพร้อม API key และส่งแบบไม่มี key ซึ่งต้องถูกปฏิเสธ"]),
    3: ("ขั้นที่ 3: รัน NGINX เป็น container ที่พอร์ต 8080 และได้ `cluster.sh` ไว้เปิดระบบทุกแบบ", [
        "รัน NGINX จาก image ทางการ `nginx:1.27` ด้วย udocker และเก็บการตั้งค่าทั้งหมดไว้ใน `code/nginx.conf`",
        "ผู้ใช้เข้าที่ **พอร์ต 8080** แล้ว NGINX ส่งต่อให้ server ซึ่งรับเฉพาะคำขอจากภายในเครื่อง",
        "`code/cluster.sh` เปิดระบบในคำสั่งเดียว เลือกได้ 3 อย่าง คือ จำนวน GPU จำนวน server ต่อ GPU และโหมด"]),
    4: ("ขั้นที่ 4: AI เขียนตัวยิงโหลดตัวเดียวที่ใช้วัดทุกแบบ", [
        "`code/loadgen.py` จำลองผู้ใช้ N คน แต่ละคนส่งรูป รอคำตอบ แล้วส่งรูปถัดไปทันที",
        "วัด 1 ระดับ 20 วินาที ไม่นับ 5 วินาทีแรก แล้วบันทึก Throughput, p95, error, GPU และ CPU",
        "โหมดหาความจุทำ 3 จังหวะ คือ **หาช่วง ประมาณ และปรับ** ด้วยเกณฑ์ p95 ไม่เกิน 500 ms และ error ต่ำกว่า 1%"]),
    5: ("ขั้นที่ 5: ยิงตัวยิงโหลดใส่ server จำลองที่รู้คำตอบล่วงหน้า 5 ทดสอบ", [
        "AI เขียน `code/fake_server.py` ซึ่งไม่ใช้โมเดล รอตามเวลาที่ตั้งไว้แล้วตอบ และนับคำขอที่ได้รับ",
        "ยิง **ทดสอบ A ถึง E** แล้วเทียบค่าที่วัดได้กับค่าที่ควรได้",
        "ข้อที่ไม่ผ่านให้หาสาเหตุ แก้ แล้วทดสอบข้อนั้นซ้ำ ผ่านครบจึงนำไปวัดระบบจริง"]),
    6: ("ขั้นที่ 6: วัดความจุของแบบที่ 1 เป็น Baseline ชื่อผล `base`", [
        "เปิดระบบแบบที่ 1 คือ **GPU 1 ใบ โปรแกรม API 1 ตัว โหมดทีละรูป** (บนโหนดเช่า 1 โหนดเดิม)",
        "หาความจุด้วยตัวยิงโหลดเป็นงานเบื้องหลัง แล้วเช็กจนเห็นคำว่า DONE",
        "ผล `base` ใช้เป็นตัวเทียบของทุกแบบ"]),
    7: ("ขั้นที่ 7: เปิด server ตัวเดิมในโหมด Micro-batching แล้ววัดความจุ ชื่อผล `batch`", [
        "เปิดระบบใหม่เป็น **GPU 1 ใบ โปรแกรม API 1 ตัว โหมด Micro-batching** รวมไม่เกิน 32 รูป และรอไม่เกิน 5 ms",
        "หาความจุด้วยตัวยิงโหลดตัวเดิมและเกณฑ์เดิม",
        "ถ้าผลแย่กว่าแบบที่ 1 แปลว่าโค้ดมีปัญหา ให้แก้แล้ววัด `base` ซ้ำด้วยโค้ดฉบับแก้"]),
    8: ("ขั้นที่ 8: เปิดโปรแกรม API 4 ตัว (4 process) บน GPU ใบเดิม แล้ววัดความจุ ชื่อผล `multi`", [
        "เปิดระบบใหม่เป็น **GPU 1 ใบ โปรแกรม API 4 ตัว (`:8101–:8104` บน `127.0.0.1`) โหมด Micro-batching** ในโหนดเดียวกัน",
        "NGINX แจกงานให้ทั้ง 4 ตัวแบบ Round Robin และแต่ละตัวมีคิวกับชุดรูปของตัวเอง ใช้ GPU 0 ร่วมกัน",
        "รายงานต้องบอกว่าคำขอกระจายไป server 4 ตัวเท่ากันหรือไม่ และส่วนใดเป็นตัวถ่วงของแต่ละแบบ"]),
    9: ("ขั้นที่ 9: เปิดใช้ GPU ทั้ง 2 ใบในโหนดเดียวกัน (ใบละ 4 โปรแกรม) แล้ววัดความจุ ชื่อผล `gpu2`", [
        "เปิดระบบใหม่เป็น **GPU 2 ใบในโหนดเดิม (โปรแกรม API ใบละ 4 ตัว รวม 8 ตัว) โหมด Micro-batching**",
        "NGINX แจกงานแบบ Round Robin ให้ครบทั้ง 8 โปรแกรมบน `127.0.0.1:8101–8104` และ `8201–8204`",
        "รายงานเทียบกับแบบที่ 3 ว่าได้กี่เท่า และ Efficiency เท่าไร"]),
    10: ("ขั้นที่ 10: เทียบวิธีแจกงาน 3 วิธี ใน 2 ตอน (ทุกตอนวัดบนโหนดเดี่ยว 1 โหนด × 2 GPU)", [
         "**10.1 เครื่องหลัก** Round Robin เทียบ Least Connections ชื่อผล `lc_equal` `rr_slow` `lc_slow` (ตัวเทียบกรณีเท่ากันคือ `gpu2`)",
         "**10.2 เช่าเครื่องใหม่แยกกัน 2 เครื่อง (เครื่อง A และเครื่อง B)** แต่ละเครื่องเป็น **1 โหนด × 2 GPU** (ไม่ได้ต่อเป็นคลัสเตอร์) วัดครบทั้ง 3 วิธีในเครื่องเดียวกัน",
         "ทั้งสองตอนวัด 2 กรณี คือ GPU เร็วเท่ากัน และ GPU ใบที่ 2 ช้าลง 3 เท่า โดยเปลี่ยนเฉพาะบรรทัดเลือกวิธีแจกงาน"]),
    11: ("ขั้นที่ 11: ปิด server ของ GPU ใบที่ 2 ที่วินาทีที่ 20 ของการยิงโหลด 60 วินาที", [
         "ยิงด้วยผู้ใช้เท่ากับ **หนึ่งในสามของความจุแบบที่ 4** แล้วปิดโปรแกรม API ทั้ง 4 ตัวของ GPU ใบที่ 2 แบบกะทันหัน",
         "รอบ `fail_off` NGINX ไม่ป้องกัน และรอบ `fail_on` NGINX ป้องกัน",
         "ป้องกันหมายถึง ส่งคำขอที่ล้มต่อให้ server ตัวอื่น และเลิกส่งงานให้ตัวที่ล่ม"]),
    12: ("ขั้นที่ 12: รวมตัวเลขเป็นกราฟ นำผลกลับมา แล้วลบเครื่อง", [
         "AI เขียน `code/report.py`",
         "รวมตัวเลขของทุกผลลง `results/metrics.json` และวาดกราฟ 7 ภาพ",
         "นำผลทั้งหมดกลับมาที่ `results` และโค้ดทุกไฟล์ที่ `code` แล้วตรวจว่ามาครบ",
         "**ลบเครื่องป้าย `vapp-lab6-nginx`** แล้วตรวจว่าไม่เหลือ"]),
}


def results(n):
    """สไลด์ผลจริงของขั้นที่ n"""
    g = "results/images/"
    if n == 1:
        m = NS["machine"]
        return [vastai_ready(
            "ผลขั้นที่ 1: โหนดเดียว (1 เครื่อง × %s จำนวน %d ใบ) พร้อมใช้งานแล้ว" % (m["gpu"], m["count"]),
            "vapp-lab6-nginx",
            "1 โหนด (Single-Node Multi-GPU) · %s × %d ใบ (24 GB ต่อใบ)" % (m["gpu"], m["count"]),
            [
                ("จำนวนโหนด (เครื่อง)", "**1 โหนด (1 เครื่อง)** ไม่ใช่คลัสเตอร์หลายโหนด"),
                ("GPU ภายในโหนด", "**%s × %d ใบ** (`GPU 0` และ `GPU 1`)" % (m["gpu"], m["count"])),
                ("ที่ตั้งเครื่อง", m["location"]),
                ("CPU ที่ใช้ได้จริง", "**ราว %s cores** (โควตา container · เครื่องแสดง %d threads)" % (m["cpu_cores_usable"], m["cpu_threads_shown"])),
                ("ระบบและพอร์ต", "`%s` · Disk 40 GB · เปิดพอร์ต `8080`" % m["image"]),
                ("เวลารอพร้อม", "%d วินาที" % m["wait_ready_seconds"]),
            ],
            [
                "ตรวจเห็น GPU ครบ **%d ใบในโหนดเดียวกัน** (`GPU 0` และ `GPU 1`)" % m["count"],
                "CPU ที่ใช้ได้จริงราว **%s cores** ผ่านเกณฑ์ 24 cores ขึ้นไป (พอสำหรับโปรแกรม API 8 ตัวและตัวยิงโหลด)" % m["cpu_cores_usable"],
                "โหนดนี้เปิดใช้งานต่อเนื่องตลอดขั้นที่ 1–12 สำหรับงาน Inference (ยังไม่ลบเครื่องจนกว่าจะจบขั้นที่ 12)",
            ],
            "พร้อมเข้าสู่ **ขั้นที่ 2**: ให้ AI เขียน `server.py` และเปิดทดสอบ Inference บน `GPU 0` ของโหนดนี้",
            note("ตลอดการทดลองหลักใช้ **1 โหนดเดิม** สลับจำนวน GPU (1 หรือ 2 ใบ) และจำนวนโปรแกรม API ด้วย `cluster.sh`", "info"),
            tag="results/machine_verify.txt",
        )]
    if n == 2:
        d = D[2]
        js = fences("รู้จักข้อมูลที่ใช้ทดสอบ", "json")[0]["text"]
        return [code("ผลขั้นที่ 2: คำตอบจริงบอก server ที่ตอบ จำนวนรูปที่เข้าโมเดลพร้อมกัน และเวลารอคิว", js, "json",
                     post=note("ช่อง `server` บอกว่า server ตัวไหนตอบ ช่อง `batch_size` บอกว่ารูปนี้เข้าโมเดลพร้อมกันกี่รูป "
                               "ส่วน `queue_ms` และ `model_ms` คือเวลารอคิวและเวลาที่โมเดลใช้")),
                big("ผลขั้นที่ 2: โมเดลตรวจรูปทดสอบได้ครบ 6 รูป และใช้ %s ต่อรูป" % re.search(r"โมเดลใช้ ([\d.–]+ ms)", d["ส่ง 6 รูปพร้อม key"]).group(1),
                    "results/dataset_samples.jpg", [
                    "**ส่ง 6 รูปพร้อม key** ได้ %s" % d["ส่ง 6 รูปพร้อม key"].replace(" · ", " ").replace("รอบที่ 2 ", ""),
                    "**ไม่มี key, key ผิด หรือไม่ใช่ Bearer** ได้ %s" % d["ไม่มี key · key ผิด · ไม่ใช่ Bearer"],
                    ], cls="mid2")]
    if n == 3:
        d = D[3]
        conf = fences("ขั้นที่ 3 ·", "nginx")[0]["text"]
        return [code("ผลขั้นที่ 3: ใน `nginx.conf` ไม่ใส่คำสั่งเลือกวิธีแจกงาน NGINX จึงใช้ Round Robin", conf, "nginx", maxfs=1.2),
                S("ผลขั้นที่ 3: จากนอกเครื่องเข้าได้เฉพาะพอร์ต 8080 และคำขอที่ไม่มี key ไม่ถูกส่งถึง server",
                  cards([("ส่งรูปพร้อม key ผ่านพอร์ต 8080", d["ส่งรูป 1 รูปพร้อม key ผ่านพอร์ต 8080"], "ok"),
                         ("ส่งรูปแบบไม่มี key", d["ส่งรูปแบบไม่มี key"], "warn"),
                         ("ส่งรูปพร้อม key ผิด", d["ส่งรูปพร้อม key ผิด"], "warn"),
                         ("ต่อพอร์ต 8101 ของ server ตรงจากนอกเครื่อง", d["ต่อพอร์ต 8101 ของ server ตรงจากนอกเครื่อง"], "bad")], 2)
                  + note("NGINX ไม่มี Dashboard จึงดูว่าคำขอไป server ตัวไหนจาก log และดูสถานะทั้งระบบด้วย `cluster.sh status`"),
                  tag="README.md", cls="mid")]
    if n == 4:
        d = D[4]
        q, m = [x.strip() for x in d["เวลารอคิว · เวลาของโมเดล"].split("·")]
        return [S("ผลขั้นที่ 4: ผู้ใช้เพียง 4 คน เวลารอคิว %s ก็ยาวกว่าเวลาของโมเดล %s แล้ว" % (q, m),
                  tiles([("เวลารอคิว", q, "ที่ N = 4", "warn"), ("เวลาของโมเดล", m, "ต่อการเรียก 1 ครั้ง", ""),
                         ("GPU ใบที่ 0", d["GPU ใบที่ 0"], "ยังว่างเป็นส่วนใหญ่", "")])
                  + note("Throughput %s และ error %s ตัวเลขเหล่านี้ยังเชื่อไม่ได้จนกว่าตัวยิงโหลดจะผ่านการพิสูจน์ในขั้นที่ 5" % (d["Throughput"], d["error"])),
                  tag="results/try_n4.json", cls="mid")]
    if n == 5:
        t = D[5]
        rows = [[bare(c) for c in r] for r in t["rows"]]
        a = NS["loadtest_check"]["A"]["measured"]
        worst = max(abs(x) for x in a["throughput_diff_pct"])
        return [fig("ผลขั้นที่ 5 ทดสอบ A: จุดที่วัดได้ทั้ง 4 จุดอยู่บนเส้นที่คำนวณ ต่างมากสุด %.1f%%" % worst, "results/loadtest_check.png",
                    "เส้นคือค่าที่คำนวณ **N ÷ 0.05 วินาที** แถบสีเทาคือช่วงผ่าน ±10% และจุดคือค่าที่ตัวยิงโหลดวัดได้", tag="results/loadtest_check.json"),
                S("ผลขั้นที่ 5: ตัวยิงโหลดผ่านครบ 5 ทดสอบ จึงนำไปวัดระบบจริงได้",
                  cards([((plain(r[0])[0], plain(r[0])[2:].split(" (")[0]), r[2], "ok") for r in rows], 3), tag="results/loadtest_check.json", cls="mid"),
                S("ผลขั้นที่ 5: วัดซ้ำ 3 ครั้ง Throughput ต่างกัน %.1f%% แต่ p95 ต่างกัน %.0f%%" % (E5["throughput_spread_pct"], E5["p95_spread_pct_not_in_rule"]),
                  tiles([("Throughput ของ 3 ครั้ง", "ต่าง %.1f%%" % E5["throughput_spread_pct"], " / ".join(f1(x) for x in E5["throughput_rps"]) + " คำขอ/วินาที", "ok"),
                         ("p50 ของ 3 ครั้ง", "ต่าง %.1f%%" % E5["p50_spread_pct"], " / ".join(f1(x) for x in E5["p50_ms"]) + " ms", "ok"),
                         ("p95 ของ 3 ครั้ง", "ต่าง %.0f%%" % E5["p95_spread_pct_not_in_rule"], " / ".join(f1(x) for x in E5["p95_ms"]) + " ms", "bad")])
                  + note("ทดสอบ E ผ่านเพราะเกณฑ์ดู Throughput และ p50 แต่ความจุตัดสินด้วย p95 ซึ่งแกว่งมากกว่า "
                         "ตัวเลขความจุทุกตัวใน LAB นี้จึงต้องอ่านแบบมีความคลาดเคลื่อน"),
                  tag="ทดสอบ E · API จริงที่ N = 8", cls="mid")]
    if n == 6:
        runs = ND["base"]["capacity_level_runs"]
        return [S("ผลขั้นที่ 6: แบบที่ 1 รับได้ %d คน ทั้งที่ GPU ทำงานเพียง %s" % (NCAP[0], LV6[4]),
                  tiles([("ความจุของแบบที่ 1", "%d คน" % NCAP[0], "p95 %s ms ที่ N = %d" % (LV6[3], NCAP[0]), ""),
                         ("Throughput", "%s" % LV6[1], "คำขอต่อวินาที และไม่เพิ่มอีกตั้งแต่ N = 2", "warn"),
                         ("GPU ทำงาน", LV6[4], "ตัวถ่วงคือการเรียกโมเดลทีละรูป", "bad")])
                  + note("ความจุ %d อยู่ชิดเส้นเกณฑ์: ที่ N = %d วัดครั้งแรกได้ %s ms (ไม่ผ่าน) และวัดซ้ำได้ %s ms (ผ่าน) "
                         "ตัวยิงโหลดตัดสินว่าไม่ผ่านเฉพาะเมื่อไม่ผ่านทั้งสองครั้ง" % (NCAP[0], NCAP[0], runs[0]["p95"], runs[1]["p95"])),
                  tag="results/base.json", cls="mid"),
                S("ผลขั้นที่ 6: ที่ความจุ เวลาเกือบทั้งหมดของผู้ใช้คือเวลารอคิว ไม่ใช่เวลาของโมเดล",
                  bars([("เวลารอคิว", "ที่ N = %d" % NCAP[0], float(LV6[5]), float(LV6[2]), "%s ms" % LV6[5]),
                        ("เวลาของโมเดล", "ต่อการเรียก 1 ครั้ง", float(LV6[6]), float(LV6[2]), "%s ms" % LV6[6])])
                  + note("แท่งเทียบกับ p50 ที่ความจุ ซึ่งเท่ากับ %s ms การเพิ่มผู้ใช้จึงได้เพียงคิวที่ยาวขึ้น" % LV6[2]),
                  tag="results/base.json", cls="mid"),
                tbl("ผลขั้นที่ 6: ตัวยิงโหลดใช้ p95 ของสองระดับเดาว่าควรวัด N ค่าไหนต่อ แล้ววัดยืนยัน", T("ขั้นที่ 6 ·", "รอบ"),
                    post=note("ค่าที่เดาได้มีไว้เลือก N ที่จะวัดต่อเท่านั้น ความจุคือค่าที่วัดแล้วผ่านจริง"))]
    if n == 7:
        c = CMP7
        probe = T("ขั้นที่ 7 ·", "รูปต่อครั้ง")
        per = {r[0]: r[2] for r in probe["rows"]}
        lv = T("ขั้นที่ 7 ·", "N")
        b4, b52, b64 = row(lv, "4")[1], row(lv, "52")[1], row(lv, "64")[1]
        return [S("ผลขั้นที่ 7: Micro-batching ทำให้ GPU ใบเดิมรับได้ %d คน จากเดิม %d คน" % (NCAP[1], NCAP[0]),
                  tiles([("ความจุ", "%d → %d คน" % (NCAP[0], NCAP[1]), "%s เท่าของแบบที่ 1" % c["ความจุ"][2], "ok"),
                         ("Throughput สูงสุด (คำขอ/วินาที)", "%s → %s" % (c["Throughput สูงสุด"][0], c["Throughput สูงสุด"][1]), "%s เท่า วัดที่ N = %d ซึ่งไม่ผ่านเกณฑ์" % (c["Throughput สูงสุด"][2], ND["batch"]["max_throughput_at_users"]), ""),
                         ("ผู้ใช้คนเดียว", c["p50 ตอนผู้ใช้คนเดียว"][2], "p50 %s เทียบกับ %s" % (c["p50 ตอนผู้ใช้คนเดียว"][1], c["p50 ตอนผู้ใช้คนเดียว"][0]), "warn")])
                  + note("GPU ยังทำงานเพียง %s ตัวถ่วงจึงน่าจะย้ายมาที่งานฝั่ง CPU ของ server ตัวเดียว ซึ่งรอบนี้ยังไม่ได้วัดยืนยัน" % c["GPU ที่ความจุ"][1]),
                  tag="results/batch.json", cls="mid"),
                fig("ผลขั้นที่ 7: จำนวนรูปต่อรอบปรับเองตามคิว จาก %s รูปที่ N = 4 เป็น %s รูปที่ N = %d" % (b4, b52, NCAP[1]),
                    g + "4_images_per_call_vs_users.png",
                    "ดูเส้น `2 batch` ของแบบที่ 2 ซึ่งเป็นเส้นสีส้มแดงที่อยู่บนสุด: จำนวนรูปเฉลี่ยต่อการเรียกโมเดล 1 ครั้งเพิ่มตาม N และ **ชนเพดาน %s รูปที่ N = 64**" % b64.split(".")[0],
                    tag="results/batch.json"),
                S("ผลขั้นที่ 7: รวมเกิน 4 รูปแล้ว เวลาต่อรูปแทบไม่ลดอีก",
                  tiles([("เรียกโมเดลครั้งละ 1 รูป", "%s ms" % per["1"], "ต่อรูป", ""),
                         ("ครั้งละ 4 รูป", "%s ms" % per["4"], "ต่อรูป", "ok"),
                         ("ครั้งละ 32 รูป", "%s ms" % per["32"], "ต่อรูป", "ok")])
                  + note("ค่านี้วัดแยกการเรียกโมเดล 1 ครั้งบน GPU ใบที่ว่าง นอก server "
                         "ที่ 32 รูปต่อรอบ การเตรียมรูปและแปลงผลใช้เวลามากกว่าครึ่งของทั้งรอบ ซึ่งเป็นงานฝั่ง CPU"),
                  tag="results/batch_model_call_probe.txt", cls="mid")]
    if n == 8:
        c = CAP8
        return [S("ผลขั้นที่ 8: server 4 ตัวทำให้ GPU ใบเดิมรับได้ %d คน และ GPU ทำงานถึง %s" % (NCAP[2], c["GPU"][2]),
                  tiles([("ความจุ", "%d คน" % NCAP[2], "%s เท่าของแบบที่ 1" % c["เท่าของแบบที่ 1"][2], "ok"),
                         ("GPU ทำงาน", c["GPU"][2], "จาก %s ของแบบที่ 2" % c["GPU"][1], "ok"),
                         ("CPU ของ server", c["CPU ของ server"][2], "รวม 4 ตัว จาก %s ของแบบที่ 2" % c["CPU ของ server"][1], "")])
                  + note("รูปถูกแบ่งไป 4 คิว รอบหนึ่งจึงรวมได้ %s รูป ไม่ใช่ %s รูป และ VRAM ที่ใช้ทั้งใบคือ %s" % (
                      c["รูปเฉลี่ยต่อการเรียกโมเดล 1 ครั้ง"][2], c["รูปเฉลี่ยต่อการเรียกโมเดล 1 ครั้ง"][1], c["VRAM ที่ใช้ทั้งใบ"][2])),
                  tag="results/multi.json", cls="mid"),
                fig("ผลขั้นที่ 8: GPU ทำงาน %s ในแบบที่ 1, %s ในแบบที่ 2 และ %s ในแบบที่ 3" % (c["GPU"][0], c["GPU"][1], c["GPU"][2]),
                    g + "5_gpu_cpu_at_capacity.png",
                    "ซ้ายคือ GPU ทำงานกี่ % ที่ความจุ ขวาคือ CPU ของ server รวม (100% = 1 core) "
                    "ตัวถ่วงของแบบที่ 3 **น่าจะเป็น GPU** ซึ่งรอบนี้ยังไม่ได้วัดแยกยืนยัน", tag="results/metrics.json")]
    if n == 9:
        k = D[9][1]
        p = [c["p95"] for c in RR180]
        return [S("ผลขั้นที่ 9: GPU ใบที่ 2 ทำให้รับได้ %d คน จาก %d คน หรือประมาณ 2 เท่า" % (NCAP[3], NCAP[2]),
                  tiles([("ความจุ", "%d → %d คน" % (NCAP[2], NCAP[3]), "%s เท่าของแบบที่ 3" % SC9[5], "ok"),
                         ("Efficiency", SC9[6], "Speedup ÷ จำนวน GPU", "ok"),
                         ("คำขอ GPU 0 / GPU 1", '<span class="sm">%s</span>' % k["สัดส่วนคำขอ GPU 0 / GPU 1"].split(" (")[0], "GPU ทำงาน %s" % k["GPU ทำงาน GPU 0 / GPU 1"], "")])
                  + note("ค่า %s เท่าอ่านว่าประมาณ 2 เท่า: ยิง Round Robin ซ้ำที่ N = %d อีก 3 ครั้ง ได้ p95 %s และ %s ms (ผ่าน) กับ %s ms (ไม่ผ่าน)" % (
                      SC9[5], NCAP[3], p[0], p[1], p[2])),
                  tag="results/gpu2.json", cls="mid"),
                fig("ผลขั้นที่ 9: p95 ของทุกแบบเริ่มต่ำแล้วหักขึ้น และความจุคือจุดสุดท้ายใต้เส้น 500 ms", g + "1_p95_vs_users.png",
                    "ดูเส้นของแบบที่ 4: จุด N = 128 สูงกว่าจุด N = 142 เพราะ NGINX พัก server ตัวหนึ่ง 10 วินาที "
                    "ค่าประมาณของจังหวะที่ 2 (%s) จึง **ต่ำกว่าความจุจริง %d คน**" % (row(NEST, "4")[2], NCAP[3] - round(ND["gpu2"]["first_estimate_users"])),
                    tag="results/metrics.json")]
    if n == 10:
        e_rr, e_lc = row(EQ, "Round Robin"), row(EQ, "Least Connections")
        p = [c["p95"] for c in RR180]
        p250 = [c["p95"] for c in RR250]
        diff = fences("10.1 ·", "nginx")[0]["text"]
        return [fig("ผลขั้นที่ 10.1: เมื่อ GPU ใบที่ 2 ช้าลง 3 เท่า Least Connections รับได้ %s คน เทียบกับ %s คนของ Round Robin" % (LCS[2], RRS[2]),
                    g + "6_round_robin_vs_least_conn.png",
                    "ซ้ายคือความจุของ 2 กรณี ขวาคือสัดส่วนคำขอที่ความจุ: ทุกแท่งแบ่งราว 50 ต่อ 50 ยกเว้น **Least Connections กรณี GPU ช้า** ส่วนต่าง %s กับ %s คนของกรณี GPU เร็วเท่ากันมาจากการวัดวิธีละ 1 รอบ จึงอ่านได้แค่ทิศทาง" % (e_rr[2], e_lc[2]),
                    tag="results/metrics.json"),
                S("ผลขั้นที่ 10.1 กรณี GPU ช้า: Least Connections ส่งคำขอ %s ไป GPU ใบเร็วเอง" % LCS[5].split(" / ")[0],
                  tiles([("Round Robin · rr_slow", "%s คน" % RRS[2],
                          "คำขอ GPU 0 / GPU 1 = %s · GPU ทำงาน %s ใบช้าเป็นตัวกำหนด p95 ของทั้งระบบ" % (RRS[5], RRS[6]), "bad"),
                         ("Least Connections · lc_slow", "%s คน" % LCS[2],
                          "คำขอ GPU 0 / GPU 1 = %s · GPU ทำงาน %s ใบช้างานค้างสูง จึงได้งานใหม่น้อยลงเอง" % (LCS[5], LCS[6]), "ok")])
                  + note("ช่องว่าง %s กับ %s คนกว้างกว่าความแกว่งระหว่างรอบมาก และสัดส่วนคำขอเปลี่ยนจริง ข้อสรุปของกรณีนี้จึงเชื่อได้ แม้วัดอย่างละรอบ" % (RRS[2], LCS[2])),
                  tag="results/rr_slow.json · lc_slow.json", cls="mid"),
                S("ผลขั้นที่ 10.1 กรณี GPU เร็วเท่ากัน: %s เทียบ %s คน มาจากการหาความจุวิธีละ 1 รอบ ขนาดของส่วนต่างยังไม่แน่น" % (e_rr[2], e_lc[2]),
                  tiles([("Round Robin · gpu2", "%s คน" % e_rr[2], "หาความจุ 1 รอบ ในขั้นที่ 9", ""),
                         ("Least Connections · lc_equal", "%s คน" % e_lc[2], "หาความจุ 1 รอบ", ""),
                         ("Round Robin ยิงซ้ำที่ N = %s" % e_rr[2], "ไม่ผ่าน 1 ใน 3", "p95 %s / %s / %s ms" % (p[0], p[1], p[2]), "bad")])
                  + note("ทิศทางเชื่อได้: Round Robin ที่ N = %s ยิงซ้ำ 2 ครั้งได้ p95 %s และ %s ms ซึ่งไม่ผ่านทั้งสองครั้ง "
                         "แต่ถ้าจะใช้ตัวเลขส่วนต่าง ต้องวัดแต่ละวิธีซ้ำหลายรอบ" % (e_lc[2], p250[0], p250[1])),
                  tag="results/rr_equal_check_*.json", cls="mid"),
                code("ผลขั้นที่ 10.1: สองวิธีต่างกันบรรทัดเดียวใน `nginx.conf`", diff, "nginx",
                     post=note("ไฟล์ตั้งค่าที่ใช้จริงของ `rr_slow` กับ `lc_slow` ต่างกันบรรทัดนี้บรรทัดเดียว การเปรียบเทียบจึงเปลี่ยนเฉพาะวิธีแจกงาน"))]
    if n == 11:
        off, on = NFAIL["off"], NFAIL["on"]
        prot = fences("ขั้นที่ 11 ·", "nginx")[0]["text"]
        return [fig("ผลขั้นที่ 11: ไม่ป้องกัน error %s%% ของคำขอทั้งหมด ส่วนรอบที่ป้องกัน error 0" % off["error_pct"], g + "7_gpu_failure.png",
                    "บนคือรอบ `fail_off` ล่างคือรอบ `fail_on` เส้นประคือวินาทีที่ 20 ที่ปิด GPU ใบที่ 2 และ **แถบสีแดงคือ error**", tag="results/metrics.json"),
                S("ผลขั้นที่ 11: หลังล่ม รอบที่ไม่ป้องกันมี error %s%% ของคำขอที่เริ่มหลังล่ม จึงไม่ผ่านเกณฑ์" % f1(off["after_error_pct"]),
                  versus("", ("ไม่ป้องกัน · fail_off", "error %s จาก %s คำขอ" % (n0(off["errors"]), n0(off["requests"])), "%s%%" % off["error_pct"],
                              "HTTP 502 ทั้งหมด p95 หลังล่ม %s ms ดูดีเพราะคิดจากคำขอที่สำเร็จเท่านั้น" % off["p95_after_ms"]),
                         ("ป้องกัน · fail_on", "error %s จาก %s คำขอ" % (n0(on["errors"]), n0(on["requests"])), "%d%%" % on["error_pct"],
                          "p95 หลังล่ม %s ms ยังผ่านเกณฑ์ เพราะผู้ใช้ %d คนน้อยกว่าความจุของ GPU 1 ใบ (%d คน)" % (on["p95_after_ms"], on["users"], NCAP[2])))
                  + note("ต้องดู error คู่กับ p95 เสมอ คำตอบของ AI ในรอบจริงเขียนว่ารอบไม่ป้องกัน \"ผ่าน\" เพราะดู p95 อย่างเดียว "
                         "ตามเกณฑ์ของ LAB รอบนั้นไม่ผ่าน"),
                  tag="results/fail_off.json · fail_on.json", cls="mid"),
                code("ผลขั้นที่ 11: การป้องกันของ NGINX คือ Retry และการพัก server ที่ล้ม 10 วินาที", prot, "nginx",
                     post=note("ต้องมี `non_idempotent` เพราะ `/v1/detect` เป็น POST การส่งซ้ำใช้ได้เมื่อไม่ก่อผลซ้ำ เช่น การตรวจรูป"))]
    if n == 12:
        cost = NS["cost"]
        return [fig("ผลขั้นที่ 12: ความจุของ 4 แบบคือ %d, %d, %d และ %d คน" % tuple(NCAP), g + "3_capacity_bar.png",
                    "แบบที่ 2 และ 3 ใช้ GPU ใบเดิมโดยค่าเช่าเท่าเดิม แบบที่ 2 ได้ %s เท่า และแบบที่ 3 ได้ **%s เท่าของแบบที่ 1** ก่อนเพิ่ม GPU ใบที่ 2" % (NX[1], NX[2]), tag="results/metrics.json"),
                fig("ผลขั้นที่ 12: Throughput ของทุกแบบเพิ่มแล้วแบนเมื่อระบบเต็ม", g + "2_throughput_vs_users.png",
                    "Throughput สูงสุดของ 4 แบบคือ %s, %s, %s และ %s คำขอต่อวินาที ของแบบที่ 2 ถึง 4 **เกิดที่ระดับที่ไม่ผ่านเกณฑ์**" % tuple(NTHR),
                    tag="results/metrics.json"),
                S("ผลขั้นที่ 12: ยอดใน billing ที่อ่านทันทีหลังลบเครื่องต่ำกว่าค่าใช้จ่ายจริง",
                  tiles([("อายุเครื่อง", '<span class="sm">%s</span>' % C12["อายุเครื่อง"].split(" (")[0], "ราคา $%s ต่อชั่วโมง" % cost["dollars_per_hour"], ""),
                         ("ยอดในหน้า billing", "$%s" % cost["charged_dollars"], "อ่านหลังลบเครื่องราว 10 นาที", "warn"),
                         ("อายุเครื่อง × ราคา", "ราว $%.2f" % cost["lifetime_x_price_dollars"], "ค่าใช้จ่ายของทั้ง LAB", "")])
                  + note("ยอดใน billing ขึ้นช้ากว่าอายุเครื่อง ให้เทียบกับ อายุเครื่อง × ราคา ทุกครั้ง และลบเครื่องทุกครั้งที่จบ"),
                  tag="results/cost.md", cls="mid")]
    return []


# เด็คนี้ตั้งเป้า 80–100 หน้า: เก็บหน้าผลเฉพาะตัวเลขหลักและกราฟหรือภาพจริงของแต่ละขั้น (ไม่มีหน้าตรวจผล ไม่แสดงค่าเช่า)
KEEP_RES = {1: [0], 2: [1], 3: [0], 5: [0], 6: [0], 7: [0], 8: [0], 9: [0, 1], 10: [0, 1], 11: [0, 2], 12: [0, 1]}
# หน้าที่ไม่นำขึ้นเด็ค (เนื้อหายังอยู่ใน README) · เทียบจากต้นชื่อหน้า
DROP = ("คำ 4 คำที่ใช้", "คำขอ 1 รายการเดินทาง", "ค่าประมาณมีไว้เลือก N", "การพิสูจน์ตัวยิงโหลดมี 5 ทดสอบ",
        "Micro-batching ทำงาน 4 จังหวะ", "รวมแล้วเร็วขึ้น", "ความคุ้มของ GPU ใบที่ 2", "Round Robin ตัดสินจากลำดับ",
        "Load Balancer รันเป็น container ด้วย udocker", "ลำดับที่คุ้ม", "บทเรียนจากการวัด 4 ข้อ",
        "ตัวถ่วงย้ายที่ทุกครั้งที่แก้", "ข้อที่ต้องอ่านคู่กับตัวเลข", "จบ LAB 6")


STEP_PAGES = {
    3: [("ขั้นที่ 3: ใน 1 โหนด NGINX พอร์ต 8080 แจกงานให้โปรแกรม API 8 ตัวบน `127.0.0.1`", LB + "arch-nginx.png", [
            "ทุกส่วนอยู่ใน **1 โหนด (เครื่องเช่า Vast.ai เครื่องเดียว)**: NGINX container, API ของ GPU 0 (`8101–8104`), API ของ GPU 1 (`8201–8204`) และ `loadgen.py`",
            "ผู้ใช้ภายนอกเห็นประตูเดียวคือ **พอร์ต 8080** ส่วนโปรแกรม API ทั้ง 8 ตัวฟังเฉพาะ `127.0.0.1` ภายในเครื่อง",
            "แม้สคริปต์ชื่อ `cluster.sh` แต่เป็นการจัดการ **หลายโปรแกรม (process) ในโหนดเดียว** (ไม่ใช่คลัสเตอร์หลายโหนดแบบ LAB 5)"]),
        ("ขั้นที่ 3: NGINX เป็นประตูเดียวที่พอร์ต 8080 และ server รับเฉพาะคำขอจากในเครื่อง", SL + "s03a-gateway.png", [
            "NGINX รันเป็น **container** จาก image `nginx:1.27` ด้วย udocker และการตั้งค่าอยู่ใน `code/nginx.conf`",
            "คำขอที่ **ไม่มี API key** NGINX ตอบ 401 เอง ไม่ถึง server ส่วนค่าของ key ตรวจที่ server",
            "server ฟังเฉพาะ `127.0.0.1` จึงเข้าพอร์ต 8101 ตรงจากนอกเครื่องไม่ได้"]),
        ("ขั้นที่ 3: `cluster.sh` เปิดระบบทั้ง 4 แบบภายในโหนดเดียวจากค่า 3 ค่า", SL + "s03b-cluster.png", [
            "เลือก 3 ค่า คือ **จำนวน GPU** (1 หรือ 2 ใบในเครื่อง) **จำนวนโปรแกรม API ต่อ GPU** และ **โหมด** ทีละรูปหรือ Micro-batching",
            "`cluster.sh` เขียนรายชื่อ server ลง `nginx.conf` ตามจำนวนที่สั่ง",
            "คำสั่งเปิดรอจน server ทุกตัวพร้อม และมีคำสั่งดูสถานะกับปิดทั้งระบบ"])],
    4: [("ขั้นที่ 4: ตัวยิงโหลดเก็บตัวเลขจาก 3 แหล่งในทุกระดับ N", SL + "s04a-sources.png", [
            "`code/loadgen.py` จำลองผู้ใช้ N คน ยิงเข้า **พอร์ต 8080** จากในเครื่องเดียวกับ server",
            "**จากคำตอบ** ได้ Throughput เวลารอ p50 p95 p99 และ error",
            "**จาก server** ได้เวลารอคิว เวลาของโมเดล และจำนวนรูปที่เข้าโมเดลพร้อมกัน",
            "**จากเครื่อง** ได้ GPU ทำงานกี่ % และ CPU ของ server, NGINX และตัวยิงโหลด"]),
        ("ขั้นที่ 4: ตัวยิงโหลดมี 2 โหมด คือหาความจุ และระดับเดียว", SL + "s04b-modes.png", [
            "**โหมดหาความจุ** ไล่ระดับ N แบบ 3 จังหวะ คือหาช่วง ประมาณ และปรับ จบแล้วพิมพ์ความจุกับคำว่า DONE",
            "**โหมดระดับเดียว** ยิงด้วย N ค่าเดียวตามเวลาที่กำหนด และบันทึกผลรายวินาที",
            "วัด 1 ระดับ 20 วินาที ไม่นับ 5 วินาทีแรก และเกณฑ์ผ่านคือ p95 ไม่เกิน 500 ms กับ error ต่ำกว่า 1%"])],
}


def lab_step(n):
    prefix = "ขั้นที่ %d ·" % n
    name = NAMES[n]
    CTX.update(kicker="LAB 6 · ขั้นที่ %d จาก %d" % (n, NSTEP), group="ขั้นที่ %d · %s" % (n, name))
    if n in STEP_PAGES:
        add([big(t, src, pts) for t, src, pts in STEP_PAGES[n]])
    else:
        title, pts = PICS[n]
        src = SL + "s01-step1.png" if n == 1 else LB + "s10-plan.png" if n == 10 else LB + "s%02d.png" % n
        add(big(title, src, pts))
    how = "วางพรอมต์นี้ใน Claude Code ที่เปิดอยู่ที่โฟลเดอร์ `02_VastAi_Application`"
    if n == 10:
        add(E.prompt_slides(E.prompt_code("10.1 ·", how=how), CTX["kicker"], "ขั้นที่ 10.1 · Round Robin เทียบ Least Connections"))
    else:
        add(E.prompt_slides(E.prompt_code(prefix, how=how), CTX["kicker"], "ขั้นที่ %d · %s" % (n, name)))
    res = results(n)
    keep = [res[k] for k in KEEP_RES.get(n, [])]
    if n == 12:
        for m in (7, 8):
            x = results(m)[1]
            x["title"] = x["title"].replace("ผลขั้นที่ %d:" % m, "ผลขั้นที่ 12:")
            keep.append(x)
    add(keep)
    if n == 10:
        step10_2()


def step10_2():
    """ตอน 10.2 ของขั้นที่ 10: 3 วิธีบนเครื่องเดียวกัน (เครื่อง A และ B แยกกัน ไม่ใช่คลัสเตอร์)"""
    rr_main = NCAP[3]
    add(big("ขั้นที่ 10.2: Round Robin ได้ %d, %d และ %d คนบน 3 เครื่อง จึงต้องเทียบในเครื่องเดียว" % (
        rr_main, c3("a", "equal", "rr"), c3("b", "equal", "rr")), LB + "why-same-machine.png", [
        "ตัวเลขข้ามเครื่องใช้เทียบวิธีแจกงานไม่ได้ เพราะเครื่องเช่าแต่ละเครื่องให้กำลังไม่เท่ากัน",
        "10.2 เช่าเครื่องใหม่ **แยกกัน 2 เครื่อง (เครื่อง A และเครื่อง B)** โดย **ไม่ได้ต่อเป็นคลัสเตอร์** แต่ละเครื่องเป็น **1 โหนด × 2 GPU** ที่วัดครบทั้ง 3 วิธีในเครื่องเดียว",
        "เครื่อง B วัดกลับลำดับ (Power of Two Choices → Least Connections → Round Robin) เพื่อไม่ให้ลำดับการวัดเอนเอียง"]))
    add(big("ขั้นที่ 10.2: ไฟล์ตั้งค่าของ 3 วิธีต่างกันเพียงบรรทัดเดียว", LB + "nginx-3lines.png", [
        "Round Robin ไม่ใส่คำสั่ง · Least Connections `least_conn;` · Power of Two Choices `random two least_conn;`",
        "Least Connections ดูงานค้างของ server **ทุกตัว** ส่วน Power of Two Choices **สุ่มมา 2 ตัว** แล้วเลือกตัวที่งานค้างน้อยกว่า",
        "การตั้งค่าอื่นของ NGINX เหมือนกันทุกบรรทัด"]))
    add(E.prompt_slides(E.prompt_code("10.2 ·", how="พรอมต์นี้เช่าเครื่องใหม่ป้าย `vapp-lab6-p2c` (1 โหนด × 2 GPU) และลบเองเมื่อจบ วางต่อจาก 10.1 ได้ทันที"),
                        CTX["kicker"], "ขั้นที่ 10.2 · 3 วิธีบนเครื่องเดียวกัน"))
    add(fig("ผลขั้นที่ 10.2 (GPU ช้า): Least Connections ได้ %d และ %d คน สูงกว่า Power of Two Choices" % (
        c3("a", "slow", "lc"), c3("b", "slow", "lc")), LB + "result-3methods.png",
        "สองโหนดเดี่ยว (เครื่องละ 1 โหนด × 2 GPU) วัดกลับลำดับกัน ขวาคือกรณี GPU ช้า: **Least Connections > Power of Two Choices (%d และ %d คน) > Round Robin ทั้งสองเครื่อง**" % (
            c3("a", "slow", "p2c"), c3("b", "slow", "p2c")),
        tag="same_machine/summary.json"))
    add(fig("ผลขั้นที่ 10.2: ผู้ใช้ 64 คนเท่ากัน เมื่อ GPU ช้า 1 ใบ Round Robin เกินเกณฑ์ ส่วน Least Connections มี p95 ต่ำที่สุด", LB + "result-p95-n64.png",
            "p95 ของ Least Connections คือ **%.0f และ %.0f ms** ของ Power of Two Choices คือ %.0f และ %.0f ms และของ Round Robin คือ %.0f และ %.0f ms ซึ่งเกินเส้น 500 ms" % tuple(
                S3[r]["slow"][m]["p95_at_n64_first_try"] for m in ("lc", "p2c", "rr") for r in ("a", "b")), tag="same_machine/summary.json"))
    add(tbl("ผลขั้นที่ 10.2: เชื่อได้เมื่อ server เร็วไม่เท่ากัน และยังสรุปไม่ได้เมื่อ server เร็วเท่ากัน", T("10.2 ·", "ข้อสรุป")))
    add(tbl("สรุปขั้นที่ 10: ระบบขนาดนี้เลือก Least Connections", T("สรุปขั้นที่ 10", "กรณี"),
            post=note("เครื่องหลัก · เครื่อง A · เครื่อง B ต่างเป็น **โหนดเดี่ยว (1 โหนด × 2 GPU)** ที่วัดแยกกันคนละรอบ ไม่ใช่คลัสเตอร์ จึงเทียบกันได้เฉพาะภายในคอลัมน์เดียวกัน", "info")))


def build():
    # ===== 1 · เปิด
    CTX.update(kicker="", group="เริ่มต้น")
    add(E.cover("LAB 6 · Inference บน 1 โหนด หลาย GPU",
                "Single-Node Multi-GPU (1 เครื่อง × 2 GPU) · Load Test · Micro-batching · NGINX Load Balancer",
                SL + "s01-cover.jpg", small="สัปดาห์ที่ 3 · VastAi Application · API ตรวจภาพ (Inference / Serving ไม่ใช่คลัสเตอร์หลายโหนด)"))
    CTX["kicker"] = "ภาพรวมของ LAB"
    add(fig("ทั้ง LAB ในภาพเดียว: โหนดเดิม 1 GPU รับได้ %d → %d คน และเปิดใช้ 2 GPU รับได้ %d คน" % (NCAP[0], NCAP[2], NCAP[3]),
            LB + "result-4designs.png",
            "ผลวัดจริงของงาน **Inference บน 1 โหนด (RTX 3090 จำนวน 2 ใบ)** ทุกแบบใช้เกณฑ์เดียวกัน คือ **p95 ไม่เกิน 500 ms และ error ต่ำกว่า 1%**", tag="NGINX · 1 โหนด × 2 GPU"))
    add(big("คำถามของ LAB: API ตรวจภาพ (Inference) บน 1 โหนดรับผู้ใช้พร้อมกันได้กี่คน", TH + "th-overview.png", [
        "LAB 1 ได้โมเดลตรวจอุปกรณ์ความปลอดภัยมาแล้ว LAB นี้เปิดโมเดลนั้นเป็น **API สำหรับ Inference / Serving**",
        "คำถามมี 2 ส่วน คือ GPU 1 ใบรับผู้ใช้พร้อมกันได้กี่คน และทำอย่างไรให้รับได้มากขึ้นในโหนดเดียวกัน",
        "เราไม่เดา แต่ **สร้างระบบ 4 แบบบน 1 โหนดเดียว (RTX 3090 × 2 ใบ) แล้ววัดด้วยวิธีเดียวกัน**"]))
    add(nfig("n06-1node-vs-multinode"))
    add(tbl("ขอบเขตของ LAB 6: งาน Inference บน 1 โหนด หลาย GPU (ไม่ใช่ Multi-Node)",
            T("ขอบเขตของบทนี้", "LAB"),
            post=note("LAB 6 ใช้ **1 โหนด (Single-Node Multi-GPU)** เพื่อวัดผล Micro-batching และ Load Balancer โดยไม่มีความช้าของเครือข่ายข้ามเครื่องปน · การกระจาย Inference ข้ามหลายโหนดจริงอยู่ใน **LAB 7**", "info"),
            tag="ตารางหลัก · ขอบเขตของบท"))
    add(nfig("n02-4designs-1node"))
    add(tbl("4 แบบที่วัดใน LAB 6: ทุกแบบใช้ 1 โหนดเดียว ต่างกันที่ GPU และจำนวนโปรแกรม API",
            T("4 แบบที่วัด", "แบบ"),
            post=note("ทุกแบบรัน Inference บนโหนดป้าย `vapp-lab6-nginx` เครื่องเดิม (server 1 ตัว = โปรแกรม FastAPI 1 ตัว ไม่ใช่คนละโหนด) · เกณฑ์ผ่านคือ **p95 ไม่เกิน 500 ms และ error ต่ำกว่า 1%**", "info"),
            tag="ตารางหลัก · 4 แบบที่วัด"))

    # ===== 2 · ภาคทฤษฎี
    CTX.update(kicker="", group="ภาคทฤษฎี")
    add(E.divider("วัดอย่างไร", "ตัวเลข 3 ตัว ความจุ และ Load Test",
                  "<p>ก่อนลงมือ ต้องตกลงกันก่อนว่าคำว่า \"รับได้\" วัดด้วยอะไร และรู้ได้อย่างไรว่าวัดถูก</p>"
                  "<p class=\"dim\">เนื้อหาเต็มอยู่ใน <a href=\"README.md#ภาคทฤษฎี--แนวคิดพื้นฐาน-10-เรื่อง\" target=\"_blank\">README.md (ภาคทฤษฎี)</a></p>",
                  img=SL + "s02-theory.jpg", small="ส่วนที่ 1 ของสไลด์"))
    CTX["kicker"] = "ทฤษฎี · คำที่ใช้"
    g = T("ภาคทฤษฎี", "คำที่ใช้")["rows"]
    add(S("คำ 4 คำที่ใช้ตลอด LAB นี้", cards([("%s (%s)" % (r[0], r[1]), r[2]) for r in g], 2), cls="mid"))

    CTX["kicker"] = "ทฤษฎี · 1 โจทย์และระบบที่จะสร้าง"
    add(big("ระบบของ LAB 6: ทุกส่วนอยู่ใน 1 โหนดเดียว (RTX 3090 จำนวน 2 ใบ สำหรับ Inference)", TH + "th-architecture.png", [
        "**1 โหนด หลาย GPU (Single-Node Multi-GPU)** มี RTX 3090 จำนวน 2 ใบในเครื่องเดียวกัน ไม่ใช่คลัสเตอร์หลายโหนดแบบ LAB 5",
        "**Load Balancer** (NGINX container) เป็นประตูเดียวที่พอร์ต 8080 แจกงาน Inference ไปยัง server ในโหนดเดียวกัน",
        "**server 8 ตัว** คือโปรแกรม FastAPI 8 ตัว (8 process บน `127.0.0.1` ใบละ 4 ตัว) ไม่ใช่คอมพิวเตอร์ 8 เครื่อง",
        "**ตัวยิงโหลด** (`loadgen.py`) อยู่ในโหนดเดียวกัน ยิงเข้า `127.0.0.1:8080` เพื่อไม่ให้ความช้าของอินเทอร์เน็ตปน"]))
    add(fig("คำขอ 1 รายการเดินทาง 5 ขั้น และ Latency คือเวลาตั้งแต่ขั้นที่ 1 ถึงขั้นที่ 5", TH + "th-request-path.png",
            "ผู้ใช้ส่ง `POST /v1/detect` พร้อมรูป 1 รูปและ API key แล้วได้ JSON กลับมา **ช้าที่ขั้นไหน คิวก็ไปยาวที่ขั้นนั้น**"))
    m = kv("โมเดลที่อยู่หลัง API", "หัวข้อ")
    add(big("โมเดลหลัง API คือ YOLO11s ขนาดเล็ก งานส่วนใหญ่ของ 1 คำขอจึงอยู่ที่ CPU", TH + "model-yolo11s.png", [
        "**Input และ Output** %s" % m["Input / Output"],
        "**ขนาด** %s และใช้ตอบอย่างเดียว (Inference) ไม่เทรนเพิ่ม" % m["ขนาด"].replace(" · ", " "),
        "GPU ตรวจ 1 รูปเสร็จในเวลาสั้นมาก งานที่เหลือคือ **รับรูป ถอดไฟล์ JPEG เตรียมรูป และแปลงผล** ซึ่งใช้ CPU"]))

    CTX["kicker"] = "ทฤษฎี · 2 ตัวเลข 3 ตัว และความจุ"
    t3 = {plain(r[0]).split(" (")[0]: (r[1], r[2]) for r in T("2 · ตัวเลข", "ตัวเลข")["rows"]}
    add(big("เมื่อระบบเต็ม เพิ่ม N แล้ว Throughput ไม่เพิ่ม แต่ Latency เพิ่มแทน", TH + "th-three-numbers.png", [
        "**N** คือ%s หน่วยเป็น%s" % t3["N"],
        "**Throughput** คือ%s หน่วยเป็น%s" % t3["Throughput"],
        "**Latency** คือ%s หน่วยเป็น %s" % t3["Latency"],
        "สามค่านี้ผูกกันด้วย **Little's Law**: `Latency เฉลี่ย (วินาที) ≈ N ÷ Throughput`"]))
    add(fig("p95 ของ 1 ระดับ N คือ 1 จุดบนกราฟความจุ", TH + "th-p95.png",
            "ผลจริงของแบบที่ 1 ที่ N = 29: 939 คำขอ คำขอลำดับที่ 892 ใช้ 494.4 ms จึงได้ **p95 = 494.4 ms** · ค่านี้คือจุด (29, 494.4 ms) บนกราฟความจุ"))
    add(big("ความจุคือ N สูงสุดที่ p95 ไม่เกิน 500 ms และ error ต่ำกว่า 1%", TH + "th-capacity.png", [
        "**แกน X** คือ N ผู้ใช้พร้อมกัน (คน) · **แกน Y** คือ p95 ของ Latency (ms) · 1 จุด = วัด 1 ระดับ N",
        "**ผ่านเกณฑ์ (SLO)** หมายถึง p95 ไม่เกิน 500 ms และ error ต่ำกว่า 1%",
        "**ความจุ** คือ N สูงสุดที่ยังผ่านเกณฑ์ · ผลจริง N = 29 ได้ 494.4 ms ผ่าน N = 30 ได้ 521.5 ms ไม่ผ่าน จึงได้ 29 คน",
        "เปลี่ยนเกณฑ์ ตัวเลขความจุก็เปลี่ยน จึงต้องบอกเกณฑ์คู่กับตัวเลขเสมอ"]))

    CTX["kicker"] = "ทฤษฎี · 3 Load Test"
    add(big("ผู้ใช้จำลองส่งรูป รอคำตอบ แล้วส่งรูปถัดไปทันที จำนวนคนในระบบจึงเท่ากับ N พอดี", TH + "th-loadtest-loop.png", [
        "การวนแบบนี้เรียกว่า **closed-loop** และไม่มีเวลาหยุดคิดระหว่างรูป จึงเป็นภาระหนักที่สุดต่อคน",
        "วัด 1 ระดับ 20 วินาที โดย **5 วินาทีแรกไม่นับ** เพราะระบบยังไม่นิ่ง",
        "ตัวยิงโหลดอยู่บนเครื่องเดียวกับ server จึงไม่มีเวลาของอินเทอร์เน็ตปน",
        "คำขอที่รอเกิน 10 วินาทีนับเป็น error"]))
    add(big("หาความจุด้วย 3 จังหวะ: หาช่วง ประมาณ แล้วปรับ", TH + "th-loadtest-ladder.png", [
        "**หาช่วง** ไล่ N = 1, 2, 4, 8, … จนไม่ผ่าน 2 ระดับติดกัน",
        "**ประมาณ** ใช้ p95 ของระดับสุดท้ายที่ผ่านกับระดับแรกที่ไม่ผ่าน ลากเส้นตรงหา N ที่ p95 ถึง 500 ms แล้ววัดที่ N นั้น",
        "**ปรับ** ประมาณซ้ำจนระดับที่ผ่านกับระดับที่ไม่ผ่านห่างกันไม่เกิน 2 คน (N เกิน 100 ใช้ 4 คน)",
        "ระดับที่ไม่ผ่าน **วัดซ้ำอีก 1 ครั้ง** ก่อนตัดสิน"]))
    add(statement("ค่าประมาณมีไว้เลือก N ที่จะวัดต่อ คำตอบคือค่าที่วัดได้", SL + "s02-theory.jpg",
                  "ค่าประมาณมีไว้เลือก N ที่จะวัดต่อ<br>คำตอบคือค่าที่วัดได้",
                  "ค่าประมาณที่คิดในใจได้คือ `N ≈ Throughput สูงสุด × 0.5 วินาที` ค่านี้ใช้ได้ดีกับแบบที่ทำทีละรูปเท่านั้น "
                  "เมื่อใช้ Micro-batching ค่านี้ **สูงเกินจริงมาก** จึงใช้เป็นเพดานคร่าว ๆ"))
    add(fig("ตัวยิงโหลดเป็นโค้ดที่ AI เขียน จึงต้องพิสูจน์กับ server จำลองที่รู้คำตอบล่วงหน้า", TH + "th-loadtest-check.png",
            "ถ้าตัวยิงโหลดวัดผิด ตัวเลขทุกตัวของ LAB ก็ผิด **เครื่องมือวัดต้องถูกก่อน ผลวัดจึงเชื่อได้**"))
    add(tbl("การพิสูจน์ตัวยิงโหลดมี 5 ทดสอบ แต่ละข้อจับความผิดคนละชนิด", T("พิสูจน์ตัวยิงโหลดก่อนใช้", "ทดสอบ")))
    add(fig("ส่วนที่เต็มก่อนคือตัวถ่วง ถ้าตัวถ่วงไม่ใช่ GPU การเช่า GPU เพิ่มก็ไม่ช่วย", TH + "th-bottleneck.png",
            "ทุกระดับ N ตัวยิงโหลดบันทึก **4 ค่า** คู่กับ Latency คือ GPU ทำงานกี่ %, CPU ของ server, CPU ของ Load Balancer และ CPU ของตัวยิงโหลด"))

    CTX["kicker"] = "ทฤษฎี · 4 แบบที่ 1 ทำทีละรูป"
    add(big("แบบที่ 1 ทำทีละรูป: ผู้ใช้ต่อคิวกัน ทั้งที่ GPU ยังทำงานไม่ถึงครึ่ง", TH + "th-one-by-one.png", [
        "server 1 ตัวหยิบรูปจากคิวครั้งละ 1 รูป เรียกโมเดล 1 ครั้ง แล้วหยิบรูปถัดไป",
        "ผู้ใช้ 1 คนได้คำตอบเร็วที่สุด เพราะไม่ต้องรอใคร",
        "ผู้ใช้หลายคนต้องต่อคิวหลังคนก่อนหน้า แบบนี้เป็น **Baseline** ที่ใช้เทียบกับแบบอื่น"]))

    CTX["kicker"] = "ทฤษฎี · 5 แบบที่ 2 Micro-batching"
    add(fig("แบบที่ 2 Micro-batching: server รวมรูปที่รออยู่ แล้วเรียกโมเดลครั้งเดียว", TH + "mb-how.png",
            "GPU ตรวจหลายรูปพร้อมกันได้ในเวลาใกล้เคียงกับรูปเดียว คำว่า **batch** คือชุดรูปที่เข้าโมเดลพร้อมกัน 1 รอบ"))
    s4 = [r[1] for r in T("ทำงานอย่างไร", "จังหวะ")["rows"]]
    add(big("Micro-batching ทำงาน 4 จังหวะ และผู้ใช้ยังส่งทีละ 1 รูปเหมือนเดิม", TH + "th-mb-steps.png",
            [x.replace(" · ", " ") for x in s4]))
    add(big("รวมแล้วเร็วขึ้น เพราะงานเตรียมต่อการเรียกโมเดลจ่ายเพียงครั้งเดียว", TH + "th-mb-why.png", [
        "การเรียกโมเดล 1 ครั้งมีงาน 2 ส่วน คือ **งานเตรียม** (ฝั่ง Python และการสั่งงาน GPU) กับ **เวลาที่ GPU คำนวณ**",
        "ทำทีละรูป 4 รูปต้องจ่ายงานเตรียม 4 ครั้ง ส่วน Micro-batching จ่าย **1 ครั้ง**",
        "GPU คำนวณ 4 รูปพร้อมกันใช้เวลานานขึ้นเพียงเล็กน้อย"]))
    add(big("Micro-batching มีปุ่มปรับ 2 ปุ่ม และผู้ใช้คนเดียวจะช้าลงเล็กน้อย", TH + "th-mb-knobs.png", [
        "**จำนวนรูปสูงสุดต่อรอบ 32 รูป** ถ้าตั้งมากไป รอบหนึ่งนานขึ้นและใช้ VRAM มาก",
        "**รอรูปเพิ่มได้นานสุด 5 ms** ถ้าตั้งมากไป ผู้ใช้คนเดียวก็ต้องรอนาน",
        "จำนวนรูปต่อรอบปรับเองตามคิว ผู้ใช้น้อยได้รอบละ 1–2 รูป ผู้ใช้มากได้รอบละหลายสิบรูป"]))

    CTX["kicker"] = "ทฤษฎี · 6 แบบที่ 3 server หลายตัว"
    add(fig("server ตัวเดียวยังไม่พอ เพราะตัวถ่วงน่าจะย้ายไปอยู่ที่ CPU ของ server ตัวเดียว", TH + "th-mp-why.png",
            "โค้ด Python ส่วนใหญ่ใน process เดียวรันได้ทีละ 1 core (ข้อจำกัดชื่อ **GIL**) งานรับรูป ถอดไฟล์ JPEG เตรียมรูป และแปลงผลจึงต่อคิวกัน ขณะที่ GPU ยังว่าง · ผลวัด: งานส่วนนี้กิน 56% ของรอบที่ 32 รูป และ GPU ทำงานแค่ 31%"))
    p3 = kv("แก้อย่างไร", "ของแบบที่ 3")
    add(big("แบบที่ 3 เปิดโปรแกรม API 4 ตัวบน GPU ใบเดิม งาน CPU จึงกระจายไป 4 core", TH + "th-mp-how.png", [
        "เปิด 4 process ในโหนดเดียวกัน แต่ละตัวมีคิวและ Micro-batching ของตัวเอง โดยมี NGINX แจกงานให้ทั้ง 4 ตัว",
        "**สิ่งที่ได้** %s" % p3["สิ่งที่ได้"].replace(" · ", " และ "),
        "**ราคาที่จ่าย** ใช้ VRAM เพิ่มตามจำนวนตัว และรอบหนึ่งรวมได้น้อยรูปลง",
        "แบบที่ 2 และ 3 ใช้ GPU ใบเดิม โดย **ค่าเช่าเท่าเดิม**"]))

    CTX["kicker"] = "ทฤษฎี · 7 แบบที่ 4 Load Balancer กับ GPU 2 ใบ"
    add(big("แบบที่ 4 เปิดใช้ GPU ใบที่ 2 ในโหนดเดียวกัน แล้วให้ Load Balancer แจกงานข้าม 2 ใบ", TH + "th-lb-what.png", [
        "GPU 1 ใบมีเพดาน จึงเปิดใช้ **GPU ใบที่ 2 ในโหนดเดิม** (รวม API 8 ตัว ใบละ 4 ตัว) แล้วให้ NGINX แจกงาน เพื่อจำลองหลักการ **Horizontal Scaling** โดยไม่มีความช้าของอินเทอร์เน็ตปน",
        "ทำได้เพราะ server แต่ละตัวไม่เก็บข้อมูลของผู้ใช้ไว้ในตัว (**stateless**) ส่งรูปให้ตัวไหนก็ได้คำตอบเหมือนกัน",
        "ผู้ใช้ยังเรียกที่อยู่เดิม (พอร์ต 8080) ไม่รู้ว่าข้างหลังมีกี่ GPU และแนวคิดเดียวกันนี้นำไปต่อขยายข้ามหลายโหนด (Multi-Node) ใน **LAB 7**"]))
    add(big("ความคุ้มของ GPU ใบที่ 2 วัดด้วย Speedup และ Efficiency โดยเทียบกับแบบที่ 3", TH + "th-efficiency.png", [
        "**Speedup** = ความจุ 2 ใบ ÷ ความจุ 1 ใบ อุดมคติคือ 2 เท่า",
        "**Efficiency** = Speedup ÷ จำนวน GPU อุดมคติคือ 100%",
        "ต้องเทียบกับ **แบบที่ 3** ซึ่งเป็น 1 ใบที่ปรับเต็มแล้ว มิฉะนั้นผลของ Micro-batching จะปนเข้าไปในผลของ GPU ใบที่ 2"]))

    CTX["kicker"] = "ทฤษฎี · 8 วิธีแจกงาน"
    add(big("Round Robin แจกวนทีละตัวและไม่ดูงานค้าง ถ้ามีตัวช้า งานจะไปกองที่ตัวนั้น", TH + "th-rr.png", [
        "แจกตามลำดับ A → B → C → A ทุกตัวได้ **จำนวนคำขอเท่ากัน**",
        "**ไม่ดู** ว่าตอนนี้ใครยังมีงานค้างอยู่เท่าไร",
        "ได้ผลดีเมื่อทุกตัวเร็วเท่ากัน"]))
    lc = [r[1] for r in T("Least Connections: ส่งให้ตัวที่งานค้างน้อยที่สุด", "ขั้น")["rows"]]
    add(big("Least Connections ส่งคำขอใหม่ให้ server ที่งานค้างน้อยที่สุดในตอนนั้น", TH + "th-lc.png", lc
            + ["Load Balancer ไม่ต้องรู้ว่าตัวไหนช้า ตัวที่ช้าคืนงานช้า งานค้างจึงสูง แล้วได้งานใหม่น้อยลงเอง"]))
    add(fig("เมื่อมี GPU ช้า 1 ใบ Round Robin ให้ใบช้าครึ่งหนึ่ง ส่วน Least Connections ให้งานไหลไปใบเร็ว", TH + "th-rr-vs-lc.png",
            "ใน LAB จำลอง GPU ช้าโดยให้ server ของ GPU ใบที่ 2 **เรียกโมเดลช้าลง 3 เท่า**"))
    add(tbl("Round Robin ตัดสินจากลำดับ ส่วน Least Connections ตัดสินจากงานค้าง", T("เทียบกันเมื่อมี GPU ช้า 1 ใบ", "")))
    p2 = [r[1] for r in T("Power of Two Choices (p2c)", "ขั้น")["rows"]]
    add(big("Power of Two Choices สุ่ม server มา 2 ตัว แล้วส่งคำขอให้ตัวที่งานค้างน้อยกว่า", TH + "th-p2c.png", p2
            + ["Power of Two Choices (เรียกย่อว่า p2c) เป็น **อีกวิธีหนึ่ง** ไม่ใช่ชื่ออื่นของ Least Connections ใช้จำนวนงานค้างเหมือนกัน แต่ไม่เทียบทุกตัว"]))
    LCP = "Least Connections เทียบ Power of Two Choices"
    add(fig("Least Connections ดู server ทุกตัว ส่วน Power of Two Choices สุ่มมา 2 ตัว", LB + "summary-lc-vs-p2c.png",
            "server 8 ตัวชุดเดียวกัน: Least Connections ได้ **S4** ที่งานค้าง 0 ส่วน Power of Two Choices สุ่มได้ S3 กับ S6 จึงได้ **S6** ที่งานค้าง 2"))
    add(tbl("Least Connections กับ Power of Two Choices ต่างกันที่จำนวน server ที่นำมาเทียบ", T(LCP, ""),
            post=note("ใน NGINX เขียน `least_conn;` (Least Connections) หรือ `random two least_conn;` (Power of Two Choices) ในบล็อก `upstream`", "info")))

    CTX["kicker"] = "ทฤษฎี · 9 เมื่อ GPU ล่มกลางทาง"
    add(big("เมื่อ GPU ล่ม Retry ส่งคำขอต่อให้ตัวอื่น และ Health Check เลิกส่งงานให้ตัวที่ล่ม", TH + "th-failover.png", [
        "**Retry** คำขอที่ส่งไปแล้วล้ม ถูกส่งต่อให้ server ตัวอื่นทันที ผู้ใช้ไม่เห็น error",
        "**Health Check** เลิกส่งงานให้ตัวที่ล่ม จนกว่าจะกลับมาปกติ · NGINX ใช้แบบ **Passive** คือดูจากคำขอจริงที่ล้ม",
        "ส่งซ้ำได้อย่างปลอดภัยเพราะการตรวจรูปเดิมซ้ำได้ผลเดิม (**idempotent**)",
        "หลังล่มระบบเหลือ GPU ใบเดียว จึงต้องเผื่อกำลังไว้"]))

    CTX["kicker"] = "ทฤษฎี · 10 NGINX แบบ container"
    add(big("Load Balancer รันเป็น container ด้วย udocker จึงไม่ต้องติดตั้งโปรแกรมลงเครื่อง", TH + "th-container.png", [
        "ดึง image ทางการ เขียนไฟล์ตั้งค่า แล้วรัน ทุกอย่างของ Load Balancer อยู่ในไฟล์ตั้งค่า",
        "เครื่องเช่าของ Vast.ai เป็น container อยู่แล้ว จึงรัน Docker ซ้อนข้างในไม่ได้ LAB จึงใช้ **udocker**",
        "ไฟล์ตั้งค่าที่ได้นำไปใช้กับ Docker หรือ Docker Compose บนเครื่องของเราเองได้"]))
    CTX["kicker"] = "ทฤษฎี · สรุป"
    add(tbl("สรุป 4 แบบ: แต่ละแบบแก้ตัวถ่วงคนละตัว และมีราคาที่ต้องจ่ายต่างกัน", T("สรุปใน 1 ตาราง", "แบบ")))

    # ===== 3 · ภาค LAB (NGINX)
    CTX.update(kicker="", group="ภาค LAB · NGINX")
    add(E.divider("ภาค LAB", "Load Balancer ด้วย NGINX บน 1 โหนด",
                  "<p>12 ขั้น ทุกขั้นคือ 1 พรอมต์ โค้ดทุกไฟล์ AI เขียนให้จากพรอมต์ โดยเริ่มจากโฟลเดอร์ว่าง</p>"
                  "<p class=\"dim\">ทุกขั้นเรียงเหมือนกัน: แนวคิดที่ใช้ → ภาพของขั้น → พรอมต์ → ผลจริง</p>",
                  img=SL + "s03-lab.jpg", small="ส่วนที่ 2 ของสไลด์"))
    CTX["kicker"] = "LAB 6 · ก่อนเริ่ม"
    add(nfig("n01-lab-map"))
    add(big("ก่อนเริ่ม: ทำ LAB 0 ให้เสร็จ และเปิด Claude Code ที่โฟลเดอร์ของบท", SL + "n05-before-start.png", [
        "ทำ [LAB 0](../README.md) เตรียม key ให้เสร็จก่อน",
        "เปิด Claude Code ที่โฟลเดอร์ `02_VastAi_Application`",
        "วางพรอมต์ทีละขั้นตามลำดับ AI เขียนโค้ดให้ทุกไฟล์ลง `lab6_microbatch_lb/code/`",
        "ถ้าหยุดกลางทาง ให้ทำ **ขั้นที่ 12** เพื่อลบเครื่องก่อนเลิก"], cls="mid2"))
    for n in range(1, NSTEP + 1):
        lab_step(n)

    # ===== 4 · สรุป
    CTX.update(kicker="", group="สรุป")
    add(E.divider("สรุป", "สิ่งที่ได้จาก LAB 6", "<p>ลำดับที่คุ้ม บทเรียนจากการวัด และข้อที่ต้องอ่านคู่กับตัวเลข</p>",
                  img=SL + "s05-summary.jpg", small="ส่วนที่ 3 ของสไลด์"))
    add(fig("สรุปผล LAB 6: เพิ่ม Capacity ได้ทีละขั้น โดย 2 ขั้นแรกไม่เสียค่าเช่าเพิ่ม", LB + "summary-results.png",
            "ขั้นที่ 1–2 คือกี่เท่าของแบบที่ 1 ขั้นที่ 3 คือกี่เท่าของแบบที่ 3 และขั้นที่ 4 คือ **Least Connections เทียบ Round Robin เมื่อ GPU ใบที่ 2 ช้าลง 3 เท่า** บน 3 เครื่อง"))
    g12 = D[12][0]
    gpu1 = row(g12, "GPU ทำงาน")[1]
    add(statement("ลำดับที่คุ้ม", SL + "s03-lab.jpg", "ใช้ GPU ใบเดิมให้เต็มก่อน แล้วค่อยเพิ่ม GPU",
                  "แบบที่ 2 และ 3 ไม่เสียค่าเช่าเพิ่ม ถ้าเพิ่ม GPU ใบที่ 2 ตั้งแต่แบบที่ 1 จะจ่าย 2 เท่าเพื่อ GPU ที่ทำงานเพียง **%s**" % gpu1))
    CTX["kicker"] = "สรุป"
    add(tbl("ถ้าต้องเลือกใช้จริง ให้ทำตามลำดับ 5 ขั้น เพราะขั้นบนถูกกว่าขั้นล่าง", T("4 · ถ้าต้องเลือกใช้จริง", "ลำดับ"),
            post=note("LAB 6 พิสูจน์ครบ 5 ขั้นสำหรับงาน **Inference บน 1 โหนด หลาย GPU (Single-Node Multi-GPU)** · เมื่อ GPU ในโหนดเดียวเต็มแล้ว จึงนำ NGINX ชุดเดียวกันขยายข้ามหลายโหนด (**Multi-Node**) ใน **LAB 7**", "info")))
    add(tbl("เลือกวิธีแจกงาน: ระบบขนาดนี้เลือก Least Connections ระบบใหญ่ใช้ Power of Two Choices", T("3 · Least Connections เทียบ", "สถานการณ์"),
            post=note("ทั้งสองวิธีดีกว่า Round Robin ชัดเจนเมื่อ server เร็วไม่เท่ากัน", "info")))
    add(S("บทเรียนจากการวัด 4 ข้อ", cards([
        (("1", "พิสูจน์เครื่องมือวัดก่อน"), "ตัวยิงโหลดเป็นโค้ดที่ AI เขียน จึงต้องผ่าน 5 ทดสอบกับ server จำลองที่รู้คำตอบก่อนนำไปวัดระบบจริง"),
        (("2", "บอกเกณฑ์คู่กับตัวเลข"), "ความจุคือ N สูงสุดที่ p95 ไม่เกิน 500 ms และ error ต่ำกว่า 1% เปลี่ยนเกณฑ์ ตัวเลขก็เปลี่ยน"),
        (("3", "ดู error คู่กับ p95"), "รอบที่ไม่ป้องกันมี p95 ดูดี เพราะคิดจากคำขอที่สำเร็จเท่านั้น ทั้งที่ error หลังล่มราวครึ่งหนึ่ง"),
        (("4", "วัดรอบเดียวมีความคลาดเคลื่อน"), "ผลที่อยู่ใกล้เส้นเกณฑ์ขึ้นกับรอบที่วัด ผลต่างที่อยู่ในช่วงความแกว่งต้องวัดซ้ำหลายรอบก่อนสรุป")], 2), cls="mid"))
    add(fig("ตัวถ่วงย้ายที่ทุกครั้งที่แก้ จึงต้องดู GPU % คู่กับ CPU ของ server ทุกครั้ง", "results/images/5_gpu_cpu_at_capacity.png",
            "**ตัวที่เต็มก่อนคือตัวถ่วง** แบบที่ 1 คือการทำทีละรูป ส่วนตัวถ่วงของแบบที่ 2 ถึง 4 เป็นข้อสันนิษฐานที่ยังไม่ได้วัดแยกยืนยัน",
            tag="results/metrics.json"))
    lim = bullets("ผลสรุป", "**ข้อที่ต้องอ่านคู่กับตัวเลข**")
    pick = [x for x in lim if x.startswith(("วัดแบบละ 1 รอบ", "Throughput สูงสุด", "ผู้ใช้จำลอง", "\"GPU ช้า\""))]
    heads = ["วัดแบบละ 1 รอบ", "Throughput สูงสุด", "ผู้ใช้จำลอง", "GPU ช้าเป็นการจำลอง"]
    add(S("ข้อที่ต้องอ่านคู่กับตัวเลขของ LAB 6", cards([
        (heads[k], x.replace(" · ", "<br>"), "warn") for k, x in enumerate(pick)], 2)
        + note("รายการเต็มอยู่ในหัวข้อ \"ผลสรุป\" ของ [README.md](README.md)", "info"), cls="mid"))
    add(S("จบ LAB 6: อ่านรายละเอียดเต็มได้ในโฟลเดอร์นี้", cards([
        ("เอกสารรวม", "[README.md](README.md) ขอบเขต · ทฤษฎี 10 เรื่อง · LAB 12 ขั้น · สรุปผล"),
        ("พรอมต์ทั้งหมด", "[PROMPTS.md](PROMPTS.md) พรอมต์ Copy & Paste 13 กล่อง"),
        ("โค้ดและผลวัดจริง", "[code_reference/](code_reference) · [results/](results) · [same_machine/](same_machine)")], 3)
        + note("ลบเครื่องทุกครั้งที่จบ และตรวจว่าไม่มีเครื่องป้าย `vapp-lab6-nginx` หรือ `vapp-lab6-p2c` เหลืออยู่", "warn"), cls="mid"))
    add(fig("บทเรียน 4 ข้อจากการวัด: พิสูจน์เครื่องมือ บอกเกณฑ์ ดู error และวัดซ้ำ", SL + "n04-lessons.png",
            "รอบที่ไม่ป้องกัน GPU ล่มมี p95 ดูดี ทั้งที่ error หลังล่มราวครึ่งหนึ่ง จึงต้อง **ดู error คู่กับ p95 เสมอ**"))
    add(big("อ่านต่อ: เนื้อหา พรอมต์ โค้ด และผลวัดจริงทั้งหมดรวมอยู่ในโฟลเดอร์เดียว", SL + "n01-lab-map.jpg", [
        "[README.md](README.md) รวมทฤษฎี 10 เรื่อง, LAB 12 ขั้นด้วย NGINX และสรุปผลการทดลองไว้ในหน้าเดียว",
        "[PROMPTS.md](PROMPTS.md) รวมพรอมต์ Copy & Paste ครบทั้ง 12 ขั้น (13 พรอมต์)",
        "[code_reference/](code_reference) และ [results/](results) เก็บโค้ดอ้างอิง กราฟ และผลวัดจริงของทุกรอบ"], cls="mid2"))

    # ----- ตัดหน้าที่ไม่ใช้ แล้วจัดลำดับใหม่: แนวคิดของแต่ละเรื่องอยู่หน้าขั้นของ LAB ที่ใช้
    title = lambda x: plain(x.get("title") or "")
    drop = [x for x in E.SL if title(x).startswith(DROP)]
    missing = [d for d in DROP if not any(title(x).startswith(d) for x in drop)]
    if missing:
        raise KeyError("DROP ไม่ตรงกับหน้าใด: %r" % missing)
    pool = [x for x in E.SL if not any(x is d for d in drop)]
    heroize(pool)

    def take(pred, what):
        got = [x for x in pool if pred(x)]
        pool[:] = [x for x in pool if not pred(x)]
        if not got:
            raise KeyError("จัดลำดับ: ไม่พบหน้า %s" % what)
        return got

    G = lambda p: take(lambda x: (x.get("group") or "").startswith(p), p)
    Tt = lambda p: take(lambda x: title(x).startswith(p), p)
    th_ = lambda k: take(lambda x: (x.get("kicker") or "").startswith("ทฤษฎี · %s" % k + (" " if isinstance(k, int) else "")), "ทฤษฎี %s" % k)
    step = lambda n: G("ขั้นที่ %d ·" % n)

    arch = Tt("ระบบของ LAB 6:")
    scope_fig = Tt("ขอบเขตของ LAB 6 เทียบกับ LAB 4, LAB 5 และ LAB 7")
    scope_tbl = Tt("ขอบเขตของ LAB 6: งาน Inference")
    designs_fig = Tt("4 การทดลองใน LAB 6:")
    designs_tbl = Tt("4 แบบที่วัดใน LAB 6:")
    lab_map, preview = Tt("12 ขั้นของ LAB 6"), Tt("ทั้ง LAB ในภาพเดียว")
    intro = G("เริ่มต้น")                               # ปก · คำถาม
    th_div = take(lambda x: x.get("group") == "ภาคทฤษฎี" and "divider" in (x.get("cls") or ""), "divider ทฤษฎี")
    parts = [
        ("เริ่มต้น", intro + scope_fig + scope_tbl + designs_fig + designs_tbl + arch + lab_map + preview),
        ("วัดอย่างไร", th_div + th_(2) + th_(3)),
        ("ส่วน A · เตรียมระบบ", G("ภาค LAB") + step(1) + th_(1) + step(2) + step(3)),
        ("ส่วน B · Load Test", step(4) + step(5)),
        ("ส่วน C · GPU 1 ใบ", th_(4) + step(6) + th_(5) + step(7) + th_(6) + step(8)),
        ("ส่วน D · GPU 2 ใบ", th_(7) + step(9) + th_(8) + step(10) + th_(9) + step(11)),
        ("ส่วน E · สรุปของ LAB", step(12) + th_("สรุป")),
        ("สรุป", G("สรุป")),
    ]
    if pool:
        raise KeyError("จัดลำดับ: มีหน้าที่ยังไม่ได้วาง %r" % [title(x) for x in pool])
    E.SL[:] = []
    for x in arch + scope_fig + scope_tbl + designs_fig + designs_tbl + lab_map:
        x["kicker"] = "ภาพรวมของ LAB"
    for name, sl in parts:
        for x in sl:
            x["group"] = name
            x["kicker"] = re.sub(r"^ทฤษฎี · (\d+ )?", "แนวคิด · ", x.get("kicker") or "")
            if name == "สรุป" and not x["kicker"] and "divider" not in (x.get("cls") or ""):
                x["kicker"] = "สรุป"
            E.SL.append(x)
    return E.write(E.SL, OUT, TITLE)


if __name__ == "__main__":
    for st in (sys.stdout, sys.stderr):
        if hasattr(st, "reconfigure"):
            st.reconfigure(encoding="utf-8", errors="replace")
    build()
