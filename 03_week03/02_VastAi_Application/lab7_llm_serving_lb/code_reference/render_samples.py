#!/usr/bin/env python3
"""Draw results/dataset_samples.json as a table picture (Pillow with libraqm, so Thai vowels/tone marks sit right)."""
import json, os, sys
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
src = os.path.join(HERE, "..", "results", "dataset_samples.json")
dst = os.path.join(HERE, "..", "results", "dataset_samples.png")
d = json.load(open(src))
FONT = "/usr/share/fonts/truetype/tlwg/Loma.ttf"
S = 2                                                     # draw at 2x for a sharp picture
f = ImageFont.truetype(FONT, 15 * S, layout_engine=ImageFont.Layout.RAQM)
ft = ImageFont.truetype(FONT, 20 * S, layout_engine=ImageFont.Layout.RAQM)
INK, MUTED, GRID, HEAD, ZEBRA = "#1b1f24", "#5b6470", "#d5dae0", "#eef1f4", "#f8f9fb"
cols = [("#", 50, "c"), ("คำถามของลูกค้า", 410, "l"), ("คำตอบจริงของแชทบอท", 660, "l"), ("token\nขาเข้า", 70, "r"),
        ("token\nคำตอบ", 70, "r"), ("TTFT\n(วินาที)", 80, "r"), ("เวลารวม\n(วินาที)", 80, "r"), ("replica\nที่ตอบ", 84, "c")]
PAD, LH = 9 * S, 24 * S
tmp = ImageDraw.Draw(Image.new("RGB", (10, 10)))


def wrap(text, width):
    """Thai has no spaces between words: break at spaces when possible, else anywhere between clusters."""
    lines = []
    for para in str(text).replace("\r", "").split("\n"):
        para, cur = para.strip(), ""
        if not para:
            continue
        for word in para.split(" "):
            trial = (cur + " " + word).strip()
            if tmp.textlength(trial, font=f) <= width:
                cur = trial
                continue
            if cur:
                lines.append(cur)
            cur = ""
            for chx in word:                               # a single "word" wider than the cell
                combining = "ั" == chx or "ิ" <= chx <= "ฺ" or "็" <= chx <= "๎"
                lead = cur[-1:] in "เแโใไ"                  # a leading vowel must stay with its consonant
                if not combining and not lead and chx not in "ะาำๆ" and cur and tmp.textlength(cur + chx, font=f) > width - 12 * S:
                    lines.append(cur)
                    cur = chx
                else:
                    cur += chx
        if cur:
            lines.append(cur)
    return lines or [""]


rows = []
for i, s in enumerate(d["samples"], 1):
    cells = [str(s["q_index"] + 1), s["question"], s["answer"], str(s["tokens_in"]), str(s["tokens_out"]),
             "%.3f" % s["ttft_s"], "%.2f" % s["total_s"], s["replica"]]
    rows.append([wrap(c, w * S - 2 * PAD) for c, (_, w, _) in zip(cells, cols)])
W = sum(w for _, w, _ in cols) * S + 2 * 20 * S
title_h, head_h, foot_h = 74 * S, 2 * LH + 2 * PAD, 40 * S
H = title_h + head_h + sum(max(len(c) for c in r) * LH + 2 * PAD for r in rows) + foot_h
img = Image.new("RGB", (W, H), "white")
g = ImageDraw.Draw(img)
x0 = 20 * S
g.text((x0, 14 * S), "ชุดคำถามของ Load Test: ตัวอย่าง 8 ข้อจาก 40 ข้อ กับคำตอบจริงของแชทบอท", font=ft, fill=INK)
g.text((x0, 46 * S), "ถามทีละข้อผ่าน NGINX พอร์ต 8080 ตอนระบบว่าง · โมเดล %s · คำตอบไม่เกิน %d token · คำสั่งระบบ: %s"
       % (d["model"], d["max_tokens"], d["system"]), font=ImageFont.truetype(FONT, 12 * S, layout_engine=ImageFont.Layout.RAQM), fill=MUTED)


def draw_row(y, cells, h, fill, bold=False):
    g.rectangle([x0, y, W - x0, y + h], fill=fill)
    x = x0
    for lines, (_, w, al) in zip(cells, cols):
        for k, ln in enumerate(lines):
            tw = g.textlength(ln, font=f)
            tx = x + PAD if al == "l" else (x + w * S - PAD - tw if al == "r" else x + (w * S - tw) / 2)
            g.text((tx, y + PAD + k * LH), ln, font=f, fill=INK, stroke_width=1 if bold else 0, stroke_fill=INK)
        x += w * S
    g.line([x0, y + h, W - x0, y + h], fill=GRID, width=S)


y = title_h
draw_row(y, [c[0].split("\n") for c in cols], head_h, HEAD, bold=True)
y += head_h
for i, r in enumerate(rows):
    h = max(len(c) for c in r) * LH + 2 * PAD
    draw_row(y, r, h, ZEBRA if i % 2 else "white")
    y += h
ss = d["samples"]
g.text((x0, y + 10 * S), "เฉลี่ย 8 ข้อ: token ขาเข้า %.0f · token คำตอบ %.0f · TTFT %.3f วินาที · เวลารวม %.2f วินาที   (# = ลำดับของคำถามในชุด 40 ข้อ)" % (
    sum(s["tokens_in"] for s in ss) / 8, sum(s["tokens_out"] for s in ss) / 8, sum(s["ttft_s"] for s in ss) / 8, sum(s["total_s"] for s in ss) / 8),
    font=ImageFont.truetype(FONT, 13 * S, layout_engine=ImageFont.Layout.RAQM), fill=MUTED)
img.save(dst)
print("saved", os.path.normpath(dst), img.size)
