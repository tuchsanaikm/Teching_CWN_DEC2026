#!/usr/bin/env python3
"""สร้างสไลด์ Multi_Account_Container_Slides.html ของบท 03_MultiAccount_Container

  python tools/build_slides.py            (รันจากโฟลเดอร์ของบท)

หลักการจัดสไลด์: 1 สไลด์ = 1 ประเด็น · นำด้วยภาพหรือแผนภาพพร้อมขั้นตอน · มีตารางเฉพาะจุดที่ต้องโฟกัส
รายละเอียดเต็มของทุกหัวข้ออยู่ใน README.md (สไลด์ไม่ได้ยกทุกตารางมา)

ที่มาของเนื้อหา
- ตาราง โค้ด พรอมต์ และตัวเลขผล: อ่านจาก README.md ตอนสร้าง (พรอมต์ตรงตัวอักษร · ตัวเลขดึงด้วย rx() ไม่พิมพ์ซ้ำด้วยมือ)
- ภาพเดิมของบท: img/concept-* · img/desktop-* · img/step3-evidence-* · img/docker-desktop-multi-account.png · img/photo-04-step1-why.jpg
- ภาพตัดจากภาพหน้าจอจริง: img/cNN-*.jpg (ตัดจาก img/desktop-step*-result.png โดยไม่แก้พิกเซล)
- ภาพใหม่ (nNN = ภาพอธิบาย · sNN = ภาพถ่ายหน้าคั่น): tools/slides_figures.py · เครื่องมือเรนเดอร์: tools/slides_engine.py
"""
import os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import slides_engine as E
from slides_engine import md, sec, walk, table, codes, para, prompt, CTX, add, note, fig, explain, tiles, cards, tbl, code
from slides_figures import FIGS

S = E.slide

# README ของบทนี้มีพรอมต์ที่ใช้ code fence 4 ตัว (````markdown) ซึ่งมี ```bash อยู่ข้างใน
# parse() ของ engine ปิด fence ที่ ``` แรก ทำให้พรอมต์ขาด · ตัวนี้ปิด fence ด้วยบรรทัด backtick ที่ยาวเท่ากันหรือมากกว่า (แบบ CommonMark)
_parse = E.parse


def parse_long_fences(lines):
    out, seg, i = [], [], 0
    while i < len(lines):
        m = re.match(r"^\s*(`{4,})(.*)$", lines[i])
        if not m:
            seg.append(lines[i])
            i += 1
            continue
        out += _parse(seg)
        seg, j, buf = [], i + 1, []
        while j < len(lines) and not re.match(r"^\s*`{%d,}\s*$" % len(m.group(1)), lines[j]):
            buf.append(lines[j])
            j += 1
        out.append({"t": "code", "lang": m.group(2).strip(), "text": "\n".join(buf)})
        i = j + 1
    return out + _parse(seg)


E.parse = parse_long_fences      # กล่องพรอมต์ (> [!IMPORTANT]) เรียก parse() ซ้ำผ่านชื่อนี้ จึงได้ตัวที่แก้แล้วด้วย
SECS = E.load("README.md")
FIG = {f["img"]: f for f in FIGS}
OUT, TITLE = "Multi_Account_Container_Slides.html", "การสร้าง Docker image สำหรับระบบหลายบัญชี · Slides"
VARY = "ผลขึ้นกับ AI และเครื่องของผู้เรียน ตัวเลข เวลา และราคาของคุณอาจต่างจากของผู้สอนได้"


# ------------------------------------------------------------------ ตัวช่วยอ่าน README.md
def heading(prefix):
    return next(s["text"] for s in SECS if s["text"].startswith(prefix))


def rx(pat, text, g=1):
    """ดึงตัวเลขหรือคำจากข้อความของ README · ไม่พบ = README เปลี่ยน ให้แก้ตัวค้น"""
    m = re.search(pat, text)
    if not m:
        raise KeyError("ไม่พบ %r ใน %r" % (pat, text[:80]))
    return m.group(g)


def image(prefix, name):
    return next(b for b in walk(sec(prefix)) if b["t"] == "img" and name in b["src"])


def ptext(prefix, start):
    """ย่อหน้าของหัวข้อ prefix ที่ขึ้นต้นด้วย start (รวมทุกบรรทัด)"""
    return " ".join(para(prefix, start)["lines"])


def italic(prefix, start):
    """ย่อหน้าตัวเอียง *...* ของ README → ข้อความ"""
    t = ptext(prefix, "*" + start)
    return t.strip().strip("*").strip()


def plines(text, pat):
    """บรรทัดของพรอมต์ที่ตรงกับ pat (ตัดเครื่องหมายนำออก)"""
    return [re.sub(pat, "", l) for l in text.split("\n") if re.match(pat, l)]


def nfig(key, steps=None, title=None, post=""):
    f = FIG[key]
    return explain(title or f["title"], "img/%s.jpg" % key, steps or f["steps"], post)


def facts(what, items):
    return "<p>%s</p><div class=\"facts\">%s</div>" % (md(what), "".join(
        '<div><span class="fl">%s</span>%s</div>' % (k, md(v)) for k, v in items if v))


def shot(title, src, full, cap, tag="ภาพหน้าจอจริง"):
    """ส่วนหนึ่งของภาพหน้าจอจริง + ลิงก์ภาพเต็ม"""
    return fig(title, src, cap + " · [ภาพเต็ม](%s)" % full, tag=tag)


def gifs(prefix):
    """ตาราง 1 แถวของ README ที่แต่ละช่องเป็น GIF → [(หัวคอลัมน์, alt ที่ตัด "GIF จริงจาก …:" ออก, src)]"""
    t = next(b for b in walk(sec(prefix)) if b["t"] == "table" and ".gif" in E.plain(b["head"][0]))
    out = []
    for head, cell in zip(t["head"], t["rows"][0]):
        m = re.match(r"!\[(.*?)\]\((.*?)\)", cell.strip())
        out.append((head, m.group(1).split(":", 1)[1].strip(), m.group(2)))
    return out


# ------------------------------------------------------------------ โครงเรื่อง
def build():
    flow = table("3. ภาพรวม", "ขั้น")["rows"]                      # ขั้น · ทำที่ไหน · ใครทำ · เวลา
    stepname = lambda n: heading("ขั้นที่ %d ·" % n).split("·", 1)[1].strip()

    def step_divider(n, img, what, result):
        CTX.update(kicker="ภาค LAB · ขั้นที่ %d จาก 3 · %s" % (n, stepname(n)), group="ขั้นที่ %d · %s" % (n, E.plain(stepname(n))))
        r = flow[n - 1]
        add(E.divider("ขั้นที่ %d จาก 3" % n, stepname(n), facts(what, [("ทำที่ไหน", r[1]), ("ใครทำ", r[2]), ("เวลา", r[3]),
                                                                        ("ผลจริง", result)]), "img/%s.jpg" % img, small="ภาค LAB"))

    # ===== เปิด
    CTX.update(kicker="", group="เริ่มต้น")
    add(E.cover(E.plain(SECS[0]["text"]), "เขียน Dockerfile แล้ว build ครั้งเดียว ทุกครั้งที่ docker run ได้ yolo1–5 · cyolo1–5 · gyolo1–5 พร้อมใช้",
                "img/s01-cover.jpg", small="01_week02 · บทที่ 03"))
    CTX["kicker"] = "ภาพรวมของบท"
    add(explain("ทั้งบทในภาพเดียว: สั่ง Claude Code app 3 ขั้น ได้ image, container และหลักฐานจากทุกบัญชี", image("3. ภาพรวม", "concept-04")["src"],
                ["%s · %s · %s" % (r[0], r[2], r[3]) for r in flow]))
    theory = ["1 · เตรียมสภาพแวดล้อมได้ 3 แบบ", "2 · องค์ประกอบของ Docker และสาม CLI", "3 · ภาพรวมการทดลอง"]
    box = lambda cls, name, small, inner: '<div class="partbox %s"><div class="ph">%s<small>%s</small></div>%s</div>' % (cls, name, small, inner)
    road = box("", "ภาคทฤษฎี", "%d หัวข้อ" % len(theory), "".join('<div class="secbox"><b>%s</b></div>' % md(t) for t in theory))
    road += box("lab", "ภาค LAB", "3 ขั้น · พรอมต์ Copy &amp; Paste", "".join(
        '<div class="secbox"><b>%s</b><span>%s · %s</span></div>' % (md(r[0]), md(r[1]), md(r[3])) for r in flow))
    add(S("บทนี้มี 2 ภาค: เข้าใจองค์ประกอบก่อน แล้วสั่ง Claude Code app ทำ 3 ขั้น", '<div class="road">%s</div>' % road + note(
        "รายละเอียดเต็มของทุกหัวข้ออยู่ใน [`README.md`](README.md)", "info"), cls="mid"))
    add(S("วิธีใช้สไลด์นี้", cards([
        ("ไปหน้าถัดไป / ก่อนหน้า", '<p><span class="kbd">→</span> <span class="kbd">Space</span> / <span class="kbd">←</span> หรือปุ่มมุมขวาล่าง</p>'),
        ("สารบัญทุกหน้า", '<p><span class="kbd">O</span> แล้วคลิกหน้าที่ต้องการ · <span class="kbd">F</span> เต็มจอ</p>'),
        ("ขยายภาพ", "คลิกที่ภาพ · คลิกอีกครั้งหรือกด Esc เพื่อปิด"),
        ("คัดลอกพรอมต์", "ปุ่ม **คัดลอกพรอมต์ทั้งหมด** ให้ข้อความเดียวกับ `README.md` ตรงตัวอักษร", "warn"),
        ("ตรวจผลหลังรัน", "สไลด์ **ตรวจผลของคุณ** ต่อจากพรอมต์ของแต่ละขั้น ติ๊กได้และจำค่าไว้ในเบราว์เซอร์นี้", "warn"),
        ("เปิดไฟล์จริง", "ลิงก์สีน้ำเงินเปิดไฟล์ในโฟลเดอร์ของบท · เปิดสไลด์จากโฟลเดอร์ `03_MultiAccount_Container`"),
    ]), cls="mid"))

    # ===== ภาคทฤษฎี
    CTX.update(kicker="", group="ภาคทฤษฎี")
    add(E.divider("ภาคทฤษฎี", "image · container · volume และสาม AI CLI", "<p>%s</p>" % " · ".join(md(t.split("·", 1)[1].strip()) for t in theory),
                  "img/s02-theory.jpg"))

    # 1 · สามแบบ
    CTX.update(kicker="ภาคทฤษฎี · " + E.plain(heading("1.")), group="ภาคทฤษฎี · 1 · สามแบบ")
    t = table("1. เตรียม", "")
    rows = {E.plain(r[0]): r[1:] for r in t["rows"]}
    add(explain("เมื่อลบ container มีเพียงแบบที่ 3 ที่ docker run ใหม่แล้วใช้ต่อได้ทันที", image("1. เตรียม", "concept-01")["src"],
                ["**%s** · AI CLI: %s · เมื่อลบ container: %s" % (E.plain(head).split("·", 1)[1].strip(), rows["AI CLI"][k], rows["เมื่อลบ container"][k])
                 for k, head in enumerate(t["head"][1:])],
                post=note("แบบที่ 3 เก็บข้อมูลล็อกอินใน %s จึงไม่หายไปพร้อม container" % rows["ข้อมูลล็อกอิน"][2], "info")))

    # 2 · องค์ประกอบ
    CTX.update(kicker="ภาคทฤษฎี · " + E.plain(heading("2.")), group="ภาคทฤษฎี · 2 · องค์ประกอบของ Docker")
    t = table("2. องค์ประกอบ", "องค์ประกอบ")
    add(explain("Dockerfile → image → container โดยมี volume เก็บข้อมูลถาวร", image("2. องค์ประกอบ", "concept-02")["src"],
                ["%s %s · %s" % (r[0], r[1], r[2]) for r in t["rows"]]))
    p21 = ptext("2.1", "image")
    add(explain("โปรแกรมอยู่ใน image ส่วนล็อกอินอยู่ใน volume",
                image("2.1", "concept-03")["src"], [
                    "**image** `multi-account:1.0` เก็บโปรแกรมทั้งหมด: Claude Code · Codex CLI · Antigravity CLI",
                    "**volume** `ai-accounts` เก็บล็อกอิน skills และ MCP",
                    rx(r"^(image .+?โดยไม่เปิดเผยบัญชีของเรา)", p21),
                    rx(r"(ทุกครั้งที่ container .+)$", p21)]))
    t = table("2.2", "คำสั่ง")
    add(explain("สาม CLI ใน container เดียว แต่ละ CLI แยกบัญชีด้วยตัวแปรของตัวเอง", image("2.2", "concept-05")["src"],
                ["%s → **%s** แยกด้วย %s" % (r[0], E.plain(r[1]), r[2]) for r in t["rows"]]
                + ["ทุก CLI ใช้ Playwright MCP + Chromium ที่ติดตั้งครั้งเดียวใน image"]))
    home = ptext("2.2", "Antigravity CLI")
    add(nfig("n01-home-agy", [rx(r"^(.+?config) จึง", home), "คำสั่ง `gyoloN` จึงเปลี่ยน `HOME` ให้ **agy เท่านั้น** เป็น `%s`" % E.plain(t["rows"][2][3]),
                              rx(r"ส่วน (.+)$", home)]))

    # 3 · ภาพรวมการทดลอง
    CTX.update(kicker="ภาคทฤษฎี · " + E.plain(heading("3.")), group="ภาคทฤษฎี · 3 · ภาพรวมการทดลอง")
    pre = ptext("3. ภาพรวม", "**ก่อนเริ่ม:**").replace("**ก่อนเริ่ม:**", "").split(" · ")
    opn = ptext("3. ภาพรวม", "**เปิดโฟลเดอร์งาน:**").replace("**เปิดโฟลเดอร์งาน:**", "").strip()
    add(code("ก่อนเริ่ม: เปิดโฟลเดอร์ 03_MultiAccount_Container ใน Claude Code app", codes("3. ภาพรวม", "text")[0]["text"],
             pre=cards([((k + 1, "ก่อนเริ่ม"), x.strip()) for k, x in enumerate(pre)], 3),
             post=note("เปิดโฟลเดอร์งาน: " + opn, "info")))

    # ===== ภาค LAB
    CTX.update(kicker="", group="ภาค LAB")
    add(E.divider("ภาค LAB", "สั่ง Claude Code app ทำ 3 ขั้น", "<p>%s</p>" % " → ".join("%s (%s)" % (E.plain(r[0]), E.plain(r[3])) for r in flow),
                  "img/s03-lab.jpg"))

    # ----- ขั้นที่ 1
    h1 = "1.3"
    res1 = ptext(h1, "**0 FAIL")
    step_divider(1, "s04-step1", "เขียน Dockerfile แล้ว build เป็น image `multi-account:1.0` ทั้ง amd64 และ arm64",
                 E.plain(rx(r"^(\*\*0 FAIL.+?\*\*)", res1)))
    hs = "ขั้นที่ 1"
    why = ptext(hs, "**ทำไมต้อง build:**").replace("**ทำไมต้อง build:**", "").strip()
    add(fig("ถ้าให้ผู้เรียนแต่ละคนติดตั้งเอง ผลจะต่างกันทุกเครื่อง", image(hs, "photo-04")["src"], why, tag="ภาพจำลอง"))
    arch = ptext(hs, "**สองสถาปัตยกรรม").split(":**", 1)[1].strip()
    add(nfig("n02-multiarch", [rx(r"^(build .+?\(Mac Apple Silicon\))", arch), rx(r"Silicon\) (.+?ให้อัตโนมัติ)", arch), rx(r"(ไม่ต้องรันผ่าน emulation)", arch)]))
    add(explain("ขั้นที่ 1: Claude แก้ Dockerfile, build และทดสอบ จนผ่านทั้ง 2 สถาปัตยกรรม", image(hs, "concept-06")["src"], [
        "**input**: `00_Devtool_Container` (Dockerfile มาตรฐาน) และ `prompt_multi_account.md` (สเปก)",
        "**Claude Code app** คัดลอก แก้ Dockerfile, `docker buildx build` แล้วทดสอบ ถ้าไม่ผ่านวนกลับไปแก้",
        "**output**: โฟลเดอร์ `MultiAccountDevtool` และ image `multi-account:1.0` แบบ linux/amd64 และ linux/arm64"],
        post=note("เฉลยจากการรันจริงอยู่ที่ [`_solution/MultiAccountDevtool/`](_solution/MultiAccountDevtool/) (ถ้าอยากให้ Claude ทำเองทั้งหมด ให้ย้ายออกก่อน)", "info")))
    t = table("1.1", "หัวข้อ")
    add(nfig("n03-spec", ["**%s**: %s" % (r[0], r[1]) for r in t["rows"]],
             post=note("อ่านฉบับเต็มได้ที่ [`prompt_multi_account.md`](prompt_multi_account.md)", "info")))
    add(E.prompt_slides(prompt("1.2"), CTX["kicker"], "ขั้นที่ 1 · สร้าง image"))
    add(E.check_slide("ขั้นที่ 1", [
        "image `multi-account:1.0` มีทั้ง linux/amd64 และ linux/arm64",
        "ตารางผลทดสอบแยกตามสถาปัตยกรรม **ไม่มี FAIL** และข้อที่ต้องล็อกอินเป็น SKIP",
        "arm64 (ผ่าน emulation): `uname -m` ได้ `aarch64` และ 15 คำสั่ง `--version` ครบ",
        "โฟลเดอร์ `MultiAccountDevtool/` มี Dockerfile · start.sh · multi-account/ · docker-compose.yml และรายงาน 3 ไฟล์ (ไม่มี secret)",
        "container และ volume ทดสอบถูกลบแล้ว ส่วน volume `ai-accounts` ไม่ถูกแตะ"],
        "ผลของผู้สอน: " + res1, VARY, "ขั้นที่ 1 · สร้าง image"))
    add(S("ผลจริงของขั้นที่ 1: ไม่มี FAIL ทั้ง 2 สถาปัตยกรรม", tiles([
        ("ผลทดสอบ", rx(r"\*\*(0 FAIL)", res1), "ทั้ง 2 สถาปัตยกรรม · ข้อที่ต้องล็อกอิน = SKIP", "ok"),
        ("arm64 ผ่าน emulation", "<code>%s</code>" % rx(r"`(aarch64)`", res1), "และ %s ครบ" % rx(r"(15 คำสั่ง)", res1), "ok"),
        ("ขนาดดาวน์โหลด", rx(r"(~[\d.]+ GB)", res1), "ต่อสถาปัตยกรรม", "")])
        + note("เวอร์ชันที่ติดตั้ง: " + rx(r"ได้ (Claude Code .+)$", res1), "info"), cls="mid", tag="ผลของรอบตัวอย่าง"))
    alt1 = image(h1, "desktop-step1-result")["alt"]
    add(shot("ตารางผลทดสอบจริง: amd64 ทดสอบครบทุกข้อ arm64 ได้ aarch64 และ 15/15", "img/c01-step1-table.jpg", "img/desktop-step1-result.png",
             "ส่วนหนึ่งของคำตอบจริงจาก Claude · %s" % rx(r"(เวลา build ~\d+ นาที)", alt1)))

    # ----- ขั้นที่ 2
    h2 = "ขั้นที่ 2"
    res2 = ptext(h2, "**ผลจริง:**").replace("**ผลจริง:**", "").strip()
    step_divider(2, "s05-step2", "สร้าง container `multi-account` จาก image แล้วผู้เรียนล็อกอินเอง", E.plain(rx(r"(container พร้อมใน \*\*[\d.]+ วินาที\*\*)", res2)))
    pull = ptext(h2, "ถ้าไม่ได้ทำขั้นที่ 1")
    pr2 = prompt(h2)
    p2 = next(x for x in pr2["blocks"] if x["t"] == "code")["text"]
    add(explain("ขั้นที่ 2: docker run สร้าง container ที่มีครบ 3 CLI และต่อกับ volume", image(h2, "concept-07")["src"], [
        pull,
        "`docker run` สร้าง container `multi-account` · `%s`" % rx(r"`(PORT` เริ่มที่ `8886`[^\n]*)", p2).replace("`", ""),
        "`-v ai-accounts:/root/ai-accounts` เชื่อม volume เก็บล็อกอิน skills และ MCP",
        "ตรวจผ่าน `docker exec`: เวอร์ชัน · `mcp list` · สถานะล็อกอินทุกบัญชี"]))
    add(E.prompt_slides(pr2, CTX["kicker"], "ขั้นที่ 2 · สร้าง container"))
    add(tbl("option ของ docker run แต่ละตัวทำหน้าที่อะไร", table(h2, "option"),
            post=note("`--privileged` เปิดให้ใช้ Docker-in-Docker · `-v` ทำให้ล็อกอินไม่หายเมื่อลบ container")))
    add(E.check_slide("ขั้นที่ 2", [
        "`http://localhost:<PORT>/lab` ตอบ `200` (PORT เริ่มที่ 8886)",
        "`yolo1..5` · `cyolo1..5` · `gyolo1..5 --version` ครบ 15 คำสั่ง",
        "`cyolo1 mcp list` และ `gyolo1 mcp list` เห็น `playwright`",
        "ตาราง บัญชี | เวอร์ชัน | ล็อกอินแล้ว/ยัง โดยไม่แสดงอีเมล ชื่อองค์กร หรือ token",
        "Docker Desktop เห็น container `multi-account` สร้างจาก image `multi-account:1.0`"],
        "ผลของผู้สอน: " + res2, italic(h2, "เครื่องตัวอย่าง"), "ขั้นที่ 2 · สร้าง container"))
    add(S("ผลจริงของขั้นที่ 2: container พร้อมใน %s วินาที" % rx(r"\*\*([\d.]+) วินาที", res2), tiles([
        ("docker run → /lab ตอบ 200", rx(r"\*\*([\d.]+) วินาที", res2) + "<small> วินาที</small>", "พร้อมใช้", "ok"),
        ("คำสั่งที่ใช้ได้", rx(r"ครบ (\d+) คำสั่ง", res2) + "<small> คำสั่ง</small>", "yolo · cyolo · gyolo อย่างละ 5", "ok"),
        ("mcp list", "<code>playwright</code>", "เห็นทั้ง `cyolo1` และ `gyolo1`", "ok")]), cls="mid", tag="ผลของรอบตัวอย่าง"))
    add(shot("Claude รายงานที่มาของ image, URL และเวลาที่ใช้", "img/c02-step2-container.jpg", "img/desktop-step2-result.png",
             "ส่วนหนึ่งของคำตอบจริงจาก Claude · image มีอยู่ในเครื่องแล้ว จึงไม่ต้อง pull ใหม่"))
    add(shot("ทั้ง 15 บัญชีมีเวอร์ชันครบ บัญชีที่ยังไม่ล็อกอินขึ้น ❌", "img/c03-step2-accounts.jpg", "img/desktop-step2-result.png",
             "ส่วนหนึ่งของคำตอบจริงจาก Claude · ของผู้เรียนจะเป็น ❌ ทั้งหมดจนกว่าจะล็อกอิน"))
    add(fig("Docker Desktop ยืนยันว่า container ทำงานจาก image multi-account:1.0", image(h2, "docker-desktop")["src"],
            "ภาพจริงจาก Docker Desktop · ค้นหา `multi-account` แล้วดูจุดสีเขียว ชื่อ image และ port", tag="ภาพหน้าจอจริง"))
    t = table("ล็อกอิน", "พิมพ์")
    own = next(b for b in walk(sec("ล็อกอิน")) if b["t"] == "p" and "ล็อกอินด้วยตนเอง" in b["lines"][0])
    lg = ptext("ล็อกอิน", "เปิด JupyterLab")
    add(nfig("n04-login", [rx(r"^(เปิด JupyterLab .+?บัญชี) \(", lg)] + ["%s → **%s**" % (r[0], E.plain(r[2]).split(" → ")[0].split(" หรือ ")[0]) for r in t["rows"]],
             post=note(E.plain(" ".join(own["lines"])), "bad")))

    # ----- ขั้นที่ 3
    h3 = "ขั้นที่ 3"
    res3 = ptext(h3, "**ผลจริง:**").replace("**ผลจริง:**", "").strip()
    alt3 = image(h3, "desktop-step3")["alt"]
    step_divider(3, "s06-step3", ptext(h3, "แต่ละบัญชี"), "อันดับ 1 คือ " + rx(r"อันดับ 1 คือ (Vietjet THB [\d,]+)", res3))
    pr3 = prompt(h3)
    p3 = next(x for x in pr3["blocks"] if x["t"] == "code")["text"]
    b3 = plines(p3, r"^- ")
    add(nfig("n05-step3-test", [b3[0], b3[1], b3[3], b3[5].split(":")[0] + ": " + b3[5].split(":", 1)[1].strip()],
             post=note(b3[4], "bad")))
    add(E.prompt_slides(pr3, CTX["kicker"], "ขั้นที่ 3 · ทดสอบ Playwright MCP"))
    add(E.check_slide("ขั้นที่ 3", [
        "ทุกบัญชีที่ล็อกอินแล้วบอกรหัสจาก skill `shared-check`",
        "ทุกบัญชีใช้ MCP `playwright` เท่านั้น ไม่ใช้ curl, python หรือ web search",
        "มีไฟล์ `./evidence/<บัญชี>.gif` ของทุกบัญชี " + rx(r"(แต่ละไฟล์มี \d+ ภาพ)", ptext(h3, "ไฟล์ `./evidence")),
        "รายงานเที่ยวบิน 3 อันดับแรก หรือรายงานตามจริงเมื่อหน้าเว็บไม่แสดงผล โดยไม่เดาราคา",
        "ไม่มีการจอง กรอกข้อมูลส่วนตัว ชำระเงิน หรือล็อกอินเว็บไซต์"],
        "ผลของผู้สอน: " + res3, italic(h3, "เครื่องตัวอย่าง"), "ขั้นที่ 3 · ทดสอบ Playwright MCP"))
    accts = rx(r"\(`(.+?)`\)", res3).replace("`", "")
    failed = rx(r"ส่วน (yolo1 .+?) หน้าเว็บ", alt3).split()
    # "yolo1–3, cyolo1–2, gyolo1" → จำนวนบัญชี (ช่วง a–b นับ b-a+1)
    n_ok = sum(int(m.group(2)) - int(m.group(1)) + 1 if m.group(2) else 1 for m in re.finditer(r"yolo(\d)(?:–(\d))?", accts))
    add(S("ทุกบัญชีใช้ skill และ Playwright MCP ได้ แต่ Google Flights แสดงผลเพียง %d บัญชี" % (n_ok - len(failed)), tiles([
        ("ใช้ skill + Playwright MCP ได้", "%d<small> บัญชี</small>" % n_ok, accts, "ok"),
        ("อันดับ 1 · yolo3 และ gyolo1", rx(r"(THB [\d,]+)", res3), rx(r"อันดับ 1 คือ (\w+)", res3), "ok"),
        ("หน้าเว็บ error", "%d<small> บัญชี</small>" % len(failed), " ".join(failed) + " · Oops, something went wrong.", "bad")])
        + note(rx(r"(Claude จึงรายงานตามจริงโดยไม่เดาราคา)", res3)), cls="mid", tag="ผลของรอบตัวอย่าง"))
    add(shot("Claude รายงานผลรายบัญชี และ 3 อันดับแรกที่ yolo3 และ gyolo1 ได้ตรงกัน", "img/c04-step3-result.jpg",
             "img/desktop-step3-playwright-result.png", "ส่วนหนึ่งของคำตอบจริงจาก Claude · บัญชีที่เว็บ error รายงานตามจริง ไม่เดาราคา · "
             + rx(r"(`yolo` กับ `cyolo` จึงได้รหัสขึ้นต้น `claude` เหมือนกัน.+?\))", italic(h3, "เครื่องตัวอย่าง")).replace("`", "")))
    order = rx(r"(\d+ ภาพตามลำดับ: .+)$", ptext(h3, "ไฟล์ `./evidence"))
    for head, alt, src in gifs(h3):
        add(fig("หลักฐานจริงจาก " + head, src, "%s · GIF %s" % (alt, order), tag="GIF จริงจาก ./evidence/"))
    add(E.prompt_slides([b for b in sec(h3) if b["t"] == "alert"][-1], CTX["kicker"], "ขั้นที่ 3 · รันบัญชีที่เว็บ error ซ้ำ"))

    # ===== สรุป
    CTX.update(kicker="", group="สรุป")
    add(E.divider("สรุป", "สิ่งที่ได้จากบทนี้", "<p>image ที่ build ครั้งเดียว · container ที่พร้อมใช้ · หลักฐานจากทุกบัญชี</p>", "img/s07-summary.jpg"))
    CTX["kicker"] = "สรุป"
    add(S("ทั้งบท: %s, container พร้อมใน %s วินาที และ %d บัญชีใช้ Playwright MCP ได้" % (
            rx(r"\*\*(0 FAIL)", res1), rx(r"\*\*([\d.]+) วินาที", res2), n_ok), tiles([
        ("ขั้นที่ 1 · build image", rx(r"\*\*(0 FAIL)", res1), "ทั้ง 2 สถาปัตยกรรม · ดาวน์โหลดสถาปัตยกรรมละ %s" % rx(r"(~[\d.]+ GB)", res1), "ok"),
        ("ขั้นที่ 2 · run container", rx(r"\*\*([\d.]+) วินาที", res2) + "<small> วินาที</small>", "ครบ %s คำสั่ง" % rx(r"ครบ (\d+) คำสั่ง", res2), "ok"),
        ("ขั้นที่ 3 · Playwright MCP", "%d<small> บัญชี</small>" % n_ok, "ใช้ได้ครบ · %d บัญชีหน้าเว็บ error และรายงานตามจริง" % len(failed), "warn")])
        + note(E.plain(ptext("ล็อกอิน", "ข้อมูลล็อกอินอยู่ใน")), "info"), cls="mid", tag="ผลของรอบตัวอย่าง"))
    CTX.update(kicker="", group="จบบท")
    add(E.divider("จบบท", "build ครั้งเดียว ใช้ได้ทุกเครื่อง",
                  '<p>รายละเอียดเต็มของบทนี้: <a href="README.md" target="_blank">README.md</a></p>'
                  '<p>สเปกระบบหลายบัญชี: <a href="prompt_multi_account.md" target="_blank">prompt_multi_account.md</a> · '
                  'เฉลย: <a href="_solution/MultiAccountDevtool/" target="_blank">_solution/MultiAccountDevtool/</a></p>'))
    return E.SL


E.CSS += """
.divider .inner .big{margin-top:26px}
.road .secbox span{font-size:.78em;display:block}
"""

if __name__ == "__main__":
    for st in (sys.stdout, sys.stderr):
        if hasattr(st, "reconfigure"):
            st.reconfigure(encoding="utf-8", errors="replace")
    E.write(build(), out=OUT, title=TITLE)
