#!/usr/bin/env python3
"""ภาพใหม่ของสไลด์ LAB 6 (ภาพเดิมของบทใช้ซ้ำเกือบทั้งหมด: 01_theory/image · image/s01..s12 · กราฟใน results)

FIGS   = ภาพอธิบาย 1 ภาพต่อ 1 สไลด์ "ภาพ + ขั้นตอน" (ภาพด้านซ้าย ขั้นตอนเรียงเลขด้านขวา)
  img    ชื่อไฟล์ใน img/ (ไม่ใส่นามสกุล)
  title  หัวข้อของสไลด์ และข้อความบนป้ายชื่อของภาพ
  labels ข้อความสั้นบนภาพ
  scene  คำบรรยายภาพเป็นภาษาอังกฤษ
  steps  ข้อความข้างภาพ · เรียบเรียงจาก README.md ของ LAB 6 เท่านั้น
PHOTOS = ภาพถ่ายสมจริงของหน้าปกและหน้าคั่น (ไม่มีตัวอักษรในภาพ · ฝั่งซ้ายมืดไว้วางหัวข้อ · สไลด์ใส่ป้าย "ภาพจำลอง")

  python tools/slides_figures.py <โฟลเดอร์ปลายทาง นอกรีโป> [ภาพอ้างอิงสไตล์ ...]
      เขียนพรอมต์ 1 ไฟล์ต่อภาพ (<img>.txt) · ภาพอ้างอิงสไตล์ = ภาพเดิมของบท เช่น image/s04.png 01_theory/image/th-container.png
"""
import os, sys

SETTING = ('a Thai construction-site safety service: workers and supervisors photograph the site with phones, and a small engineering '
           'team runs an image-detection API on one rented cloud GPU server that has two graphics cards')

FIGS = [
    {"img": "n01-lab-map", "title": "12 ขั้นของ LAB 6 แบ่งเป็น 5 ส่วน",
     "labels": ["A เตรียมระบบ", "ขั้นที่ 1–3", "B Load Test", "ขั้นที่ 4–5", "C GPU 1 ใบ", "ขั้นที่ 6–8",
                "D GPU 2 ใบ", "ขั้นที่ 9–11", "E สรุป", "ขั้นที่ 12"],
     "scene": "Five rounded cards in one row from left to right, joined by arrows, like a road map. Each card has a letter badge "
              "(A, B, C, D, E) in a circle, a small icon, the name of the part, and under it the range of steps. "
              "Card A icon: a rented server box with a shipping container gate. Card B icon: a small robot arm that throws picture "
              "cards and a stopwatch. Card C icon: one graphics card. Card D icon: two graphics cards behind a gate. "
              "Card E icon: a clipboard with a tick and a recycle bin for the rented server. "
              "No charts, no bars, no gauges, no other numbers.",
     "steps": ["**ส่วน A (ขั้นที่ 1–3)** เช่า 1 โหนดที่มี 2 GPU ให้ AI เขียน API ตรวจภาพ และตั้ง NGINX Load Balancer แบบ container",
               "**ส่วน B (ขั้นที่ 4–5)** ให้ AI เขียนตัวยิงโหลด แล้วพิสูจน์ว่าตัวยิงโหลดวัดถูกด้วย 5 ทดสอบ",
               "**ส่วน C (ขั้นที่ 6–8)** วัดแบบที่ 1, 2 และ 3 บน GPU 1 ใบในโหนดเดียว",
               "**ส่วน D (ขั้นที่ 9–11)** เปิดใช้ GPU ใบที่ 2 ในโหนดเดิม วัดแบบที่ 4 เทียบวิธีแจกงาน 3 วิธี และทดสอบ GPU ล่มกลางทาง",
               "**ส่วน E (ขั้นที่ 12)** ทำกราฟ สรุปผล และลบเครื่อง"]},
    {"img": "n02-4designs-1node", "title": "4 การทดลองใน LAB 6: ทั้งหมดรันอยู่ใน 1 โหนด (เครื่องเช่า 1 เครื่อง)",
     "labels": ["1 โหนด (เครื่องเช่า 1 เครื่อง)",
                "แบบที่ 1 · base", "GPU 0 (1 ใบ)", "API 1 ตัว (:8101)", "ส่งทีละ 1 รูป",
                "แบบที่ 2 · batch", "รวมรูปเป็นชุด (Micro-batching)",
                "แบบที่ 3 · multi", "NGINX (:8080)", "API 4 ตัว (:8101–:8104)", "ใช้ GPU 0 ร่วมกัน",
                "แบบที่ 4 · gpu2", "GPU 0 + GPU 1 (2 ใบ)", "API 8 ตัว (ใบละ 4 ตัว)", ":8101–:8104", ":8201–:8204",
                "ทุกแบบใช้ 1 โหนดเดิม · API หลายตัว = เปิดหลายโปรแกรมในเครื่องเดียว"],
     "scene": "A clean 2x2 grid of four rounded pastel panels comparing four architecture setups. Every panel has a thin dashed outer computer-chassis frame representing one single rented machine, with a small badge at the top of the whole grid reading '1 โหนด (เครื่องเช่า 1 เครื่อง)'. "
              "Top-left panel (light purple tint) titled 'แบบที่ 1 · base': inside one machine box, 1 single picture icon enters 1 small gear box labeled 'API 1 ตัว (:8101)' connected to 1 purple graphics card labeled 'GPU 0 (1 ใบ)', with a small tag 'ส่งทีละ 1 รูป'. "
              "Top-right panel (light blue tint) titled 'แบบที่ 2 · batch': inside one machine box, a neat bundle of multiple picture icons grouped together enters 1 small gear box labeled 'API 1 ตัว (:8101)' connected to 1 purple graphics card labeled 'GPU 0 (1 ใบ)', with a tag 'รวมรูปเป็นชุด (Micro-batching)'. "
              "Bottom-left panel (light teal tint) titled 'แบบที่ 3 · multi': inside one machine box, a green gate icon labeled 'NGINX (:8080)' distributes arrows to a row of 4 small gear boxes labeled 'API 4 ตัว (:8101–:8104)', and all 4 gear boxes point into 1 single purple graphics card labeled 'GPU 0 (1 ใบ)' with a note 'ใช้ GPU 0 ร่วมกัน'. "
              "Bottom-right panel (warm light orange tint) titled 'แบบที่ 4 · gpu2': inside one machine box, a green gate icon labeled 'NGINX (:8080)' splits arrows into two rows: top row has 4 small gear boxes (':8101–:8104') pointing to a purple graphics card GPU 0, and bottom row has 4 small gear boxes (':8201–:8204') pointing to a second purple graphics card GPU 1, grouped with labels 'API 8 ตัว (ใบละ 4 ตัว)' and 'GPU 0 + GPU 1 (2 ใบ)'. "
              "At the bottom of the entire canvas, a light green rounded footer banner reads 'ทุกแบบใช้ 1 โหนดเดิม · API หลายตัว = เปิดหลายโปรแกรมในเครื่องเดียว'. "
              "No bar charts, no line charts, no gauges, no speed numbers, no extra text.",
     "steps": ["**แบบที่ 1 (`base`)** เปิดโปรแกรม API เพียง **1 ตัว** (`:8101`) บน **GPU 0** ตรวจทีละ 1 รูป (Baseline)",
               "**แบบที่ 2 (`batch`)** ยังเปิดโปรแกรม API **1 ตัว** บน **GPU 0** แต่เปิด **Micro-batching** รวมหลายรูปเข้าโมเดลครั้งเดียว",
               "**แบบที่ 3 (`multi`)** เปิดโปรแกรม API พร้อมกัน **4 ตัว** (`:8101–:8104`) ใช้ **GPU 0 ใบเดียวกัน** ให้ NGINX แจกงานเพื่อกระจายงาน CPU ไป 4 core",
               "**แบบที่ 4 (`gpu2`)** เปิดใช้ **GPU ใบที่ 2 ในโหนดเดิม** เพิ่ม API อีก 4 ตัวบน GPU 1 (`:8201–:8204`) รวมเป็น **8 โปรแกรม** ให้ NGINX แจกงานข้าม 2 GPU"]},
    {"img": "n06-1node-vs-multinode", "title": "ขอบเขตของ LAB 6 เทียบกับ LAB 4, LAB 5 และ LAB 7",
     "labels": ["งาน Training (เทรนโมเดล)", "งาน Inference (เปิด API ให้บริการ)",
                "LAB 4", "1 โหนด · 1, 2 หรือ 4 GPU",
                "LAB 5", "2–3 โหนด (Multi-Node) · โหนดละ 2 GPU",
                "LAB 6 (บทนี้)", "1 โหนด · RTX 3090 × 2 ใบ", "NGINX + API 8 ตัวในเครื่องเดียว",
                "LAB 7", "2 โหนด (Multi-Node) · โหนดละ 2 GPU",
                "LAB 6 = Inference บน 1 โหนด หลาย GPU (Single-Node Multi-GPU)"],
     "scene": "A clean 2x2 comparison matrix with two row headers on the left or subtle group labels: top row is 'งาน Training (เทรนโมเดล)', bottom row is 'งาน Inference (เปิด API ให้บริการ)'. Left column shows Single-Node (one machine box), right column shows Multi-Node (multiple machine boxes connected by a cloud network icon). "
              "Top-left card (soft gray-blue): badge 'LAB 4', shows 1 server box containing graphics cards inside, label '1 โหนด · 1, 2 หรือ 4 GPU'. "
              "Top-right card (soft gray-blue): badge 'LAB 5', shows 2 to 3 separate server boxes linked by a cloud/network line, label '2–3 โหนด (Multi-Node) · โหนดละ 2 GPU'. "
              "Bottom-left card (highlighted with bright warm amber/orange outline and small yellow spark strokes): badge 'LAB 6 (บทนี้)', shows 1 prominent server box containing a small green NGINX gate, 8 tiny API gear icons, and 2 purple graphics cards inside the same single box, labels '1 โหนด · RTX 3090 × 2 ใบ' and 'NGINX + API 8 ตัวในเครื่องเดียว'. "
              "Bottom-right card (soft light blue): badge 'LAB 7', shows 2 separate server boxes linked by a cloud/network line with an NGINX gate distributing across both boxes, label '2 โหนด (Multi-Node) · โหนดละ 2 GPU'. "
              "Bottom rounded light green footer banner: 'LAB 6 = Inference บน 1 โหนด หลาย GPU (Single-Node Multi-GPU)'. "
              "No bar charts, no line charts, no gauges, no prices, no extra numbers.",
     "steps": ["**LAB 4 และ LAB 5** เป็นงาน **Training** (เทรนโมเดล): LAB 4 ใช้ 1 โหนดหลาย GPU ส่วน LAB 5 ใช้ 2–3 โหนดต่อข้ามอินเทอร์เน็ต",
               "**LAB 6 (บทนี้)** เปลี่ยนเป็นงาน **Inference / API Serving** แต่ใช้เพียง **1 โหนด (RTX 3090 × 2 ใบ)** เพื่อให้วัดผล Micro-batching และ Load Balancer โดยไม่มีความช้าของเน็ตข้ามเครื่องปน",
               "**LAB 7 (บทถัดไป)** นำ NGINX รูปแบบเดียวกันไปขยายเป็น **Multi-Node (2 โหนด × 2 GPU)** ข้ามอินเทอร์เน็ตจริง"]},
]

PHOTOS = [
    {"img": "s01-cover", "scene": "On a real construction site in Thailand in the late afternoon, a site supervisor wearing a white hardhat "
                                  "and an orange reflective safety vest holds up a smartphone to photograph a group of workers in hardhats "
                                  "and vests standing near scaffolding. Several other workers in the background also hold phones up. "
                                  "Mood: many people sending photos at the same time."},
    {"img": "s02-theory", "scene": "A Thai engineer in her thirties stands at a whiteboard in a small office and explains a hand-drawn "
                                   "diagram of boxes and arrows (completely blurred, abstract) to two colleagues sitting with laptops. "
                                   "Calm teaching mood, daylight from a window."},
    {"img": "s03-lab", "scene": "A Thai software developer in his twenties works at a desk at night with an open laptop (screen blurred), "
                                "next to an open computer case on the desk with two large glowing graphics cards. Focused hands-on mood."},
    {"img": "s05-summary", "scene": "Two Thai engineers stand at a table and compare two printed sheets with abstract blurred charts, one "
                                    "sheet in each hand, discussing calmly. A laptop is closed on the table. Late afternoon light, "
                                    "mood of wrapping up a project."},
]

CARTOON = """Generate ONE illustration with your image generation tool and save it as a PNG file at exactly this path:
{out}/{img}.png

First open and look at these reference images, then match their illustration style exactly (same kind of flat, cute, clean
cartoon infographic: white or very light background, a pastel blue rounded title banner at the top with small yellow spark strokes,
rounded pastel cards, thin dark outlines, circle badges, small white-and-blue robot helper, bold rounded Thai lettering):
{refs}

Canvas: landscape 16:9 (about 1672 x 941). Setting: {setting}.

Title banner text at the top (exact): {title}

Scene: {scene}

Text labels to place in the picture, each next to the element it names (exact text, one label per line below):
{labels}

Strict text rules:
- Write every label EXACTLY as given, character by character. Thai stays Thai, English stays English, numbers and symbols stay as they are.
- Do NOT add any other words, numbers, captions, watermarks or logos beyond the title and the labels above.
- Do NOT draw bar charts, line charts, gauges, meters or progress bars. Nothing in the picture may suggest a measured value.
- Text must be large, bold and easy to read from the back of a classroom.
- Characters: fictional cartoon characters only.

Rules: create only that one file. Do not modify any other file. Do not run any git command (no add, commit, push).
When the file is saved, reply with the file path and stop.
"""

PHOTO = """Generate ONE photorealistic image with your image generation tool and save it as a JPG file at exactly this path:
{out}/{img}.jpg

Scene: {scene}

Requirements:
- Photorealistic, like a real photograph taken with a full-frame camera, natural light, shallow depth of field, landscape 16:9 (about 1920x1080).
- Setting: {setting}.
- People are fictional adults of Thai appearance; no real person's likeness.
- NO readable text anywhere: no letters, no numbers, no logos, no signs, no watermarks. Screens and papers must be blurred or abstract.
- Keep the left 45% of the frame calm and darker (out-of-focus background), main subject on the right side, because a title will be placed over the left side later.

Rules: create only that one file. Do not modify any other file. Do not run any git command (no add, commit, push).
When the file is saved, reply with the file path and stop.
"""

if __name__ == "__main__":
    out = os.path.abspath(sys.argv[1]).replace("\\", "/")
    refs = [os.path.abspath(p).replace("\\", "/") for p in sys.argv[2:]]
    os.makedirs(out, exist_ok=True)
    for f in FIGS:
        open(os.path.join(out, f["img"] + ".txt"), "w", encoding="utf-8").write(CARTOON.format(
            out=out, img=f["img"], refs="\n".join(refs), setting=SETTING, title=f["title"], scene=f["scene"], labels="\n".join(f["labels"])))
    for f in PHOTOS:
        open(os.path.join(out, f["img"] + ".txt"), "w", encoding="utf-8").write(PHOTO.format(out=out, img=f["img"], setting=SETTING, scene=f["scene"]))
    print("%d prompts -> %s" % (len(FIGS) + len(PHOTOS), out))
