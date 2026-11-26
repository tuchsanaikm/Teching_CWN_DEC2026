#!/usr/bin/env python3
"""ภาพใหม่ของสไลด์ LAB 4 (23 ภาพ: ภาพประกอบอธิบาย 4 ภาพ + ภาพถ่าย/3D render เชิงเปรียบเปรย 19 ภาพ)

FIGS   = ภาพประกอบอธิบายแบบการ์ตูน 1 ภาพต่อ 1 สไลด์ "ภาพ + ขั้นตอน" (ภาพด้านซ้าย ขั้นตอนเรียงเลขด้านขวา)
PHOTOS = ภาพถ่าย / 3D render แบบภาพยนตร์ 16:9 ของหน้าปก หน้าแผนที่เส้นทาง หน้าคั่น และหน้า Hero ตัวเลขใหญ่
         (ไม่มีตัวอักษรในภาพ · ฝั่งซ้าย 45% มืดและโล่ง · สไลด์ใส่ป้าย "ภาพจำลอง")

  python tools/slides_figures.py <โฟลเดอร์ปลายทาง นอกรีโป> [ภาพอ้างอิงสไตล์ ...]
"""
import os, sys

SETTING = ('an AI engineering training workshop running Qwen3-8B LoRA fine-tuning on rented cloud GPU servers '
           '(RTX 3090 24 GB single, 2-GPU, and 4-GPU machines)')

FIGS = [
    {"img": "n01-lab4-folders",
     "title": "แผนที่โฟลเดอร์และการทดลองทั้ง 3 LAB ย่อย (1 เครื่อง)",
     "labels": ["LAB 4.1 · Single GPU", "1_single_gpu/", "1 เครื่อง · 1 GPU · หาจุดตั้งต้น",
                "LAB 4.2 · Data Parallelism", "2_data_parallel/ (+ gpu4/)", "1 เครื่อง · 2 และ 4 GPU · เน้นความเร็ว",
                "LAB 4.3 · Model Parallelism", "3_model_parallel/ (+ gpu4/)", "1 เครื่อง · 2 และ 4 GPU · ขยาย batch"],
     "scene": "Three rounded pastel cards arranged cleanly in one horizontal row from left to right, joined by crisp navy arrows like a course roadmap. "
              "Each card has a colored title pill at the top, a yellow folder tab with monospace folder name underneath, a cute flat icon in the middle, and a clean white pill at the bottom (NO numbered circles anywhere). "
              "Card 1 (soft grey-blue): top 'LAB 4.1 · Single GPU', folder '1_single_gpu/', middle icon one graphics card with a smiling robot face inside, bottom '1 เครื่อง · 1 GPU · หาจุดตั้งต้น'. "
              "Card 2 (soft sky blue): top 'LAB 4.2 · Data Parallelism', folder '2_data_parallel/ (+ gpu4/)', middle icon four small graphics cards inside a single-machine frame each holding a smiling robot face, bottom '1 เครื่อง · 2 และ 4 GPU · เน้นความเร็ว'. "
              "Card 3 (soft peach-orange): top 'LAB 4.3 · Model Parallelism', folder '3_model_parallel/ (+ gpu4/)', middle icon one robot split across four graphics cards by dashed lines inside a single-machine frame, bottom '1 เครื่อง · 2 และ 4 GPU · ขยาย batch'. "
              "No charts, no bars, no gauges, no extra numbers.",
     "steps": ["**LAB 4.1 (`1_single_gpu/`)** เช่า **1 เครื่อง (RTX 3090 × 1 ใบ)** · 3 ขั้น เพื่อหาขีดจำกัดของ batch และความเร็วตั้งต้น",
               "**LAB 4.2 (`2_data_parallel/` และ `gpu4/`)** เช่า **1 เครื่อง (2 ใบ)** แล้วทำซ้ำด้วย **1 เครื่อง (4 ใบ)** · 6 ขั้น ใช้ DDP ให้ทุกใบถือโมเดลครบชุดแล้วแบ่งข้อมูลกันเทรน",
               "**LAB 4.3 (`3_model_parallel/` และ `gpu4/`)** เช่า **1 เครื่อง (2 ใบ)** แล้วทำซ้ำด้วย **1 เครื่อง (4 ใบ)** · 6 ขั้น แบ่ง Layer ของโมเดลชุดเดียวลงหลายใบเพื่อเพิ่ม VRAM และ batch"]},

    {"img": "n02-oom-padding",
     "title": "วัดผ่านที่ batch 4 แต่เทรนจริง Out of Memory ได้อย่างไร",
     "labels": ["1 ตอนวัด (Probe)", "4 แถวยาวเท่ากัน ไม่มี padding", "ผ่าน (เหลือ < 1 GiB)",
                "2 ตอนเทรนจริง", "แถวยาวไม่เท่ากัน เติม padding", "ส่ง attention_mask → เกิน 24 GB",
                "3 วิธีแก้", "ไม่ส่ง attention_mask", "padding ด้านขวา + causal → ผลเท่าเดิม"],
     "scene": "Three rounded pastel cards arranged left to right connected by arrows, with numbered circle badges 1, 2, 3. "
              "Card 1 (soft sky blue): four horizontal token strips of identical full length stacked neatly with a green checkmark, with labels '1 ตอนวัด (Probe)', '4 แถวยาวเท่ากัน ไม่มี padding', and 'ผ่าน (เหลือ < 1 GiB)'. "
              "Card 2 (soft pink-red): four horizontal strips of unequal lengths where shorter rows have grey dotted padding blocks on the right side plus a small mask tag and a red X warning icon, with labels '2 ตอนเทรนจริง', 'แถวยาวไม่เท่ากัน เติม padding', and 'ส่ง attention_mask → เกิน 24 GB'. "
              "Card 3 (soft mint green): the same four right-padded strips with leftward causal arrows (showing real tokens only look left) and a smiling small white-and-blue robot holding a green checkmark, with labels '3 วิธีแก้', 'ไม่ส่ง attention_mask', and 'padding ด้านขวา + causal → ผลเท่าเดิม'. "
              "No bar charts, no line graphs, no gauges.",
     "steps": ["**ตอนวัด (Probe)** ใช้ตัวอย่างที่ยาวที่สุดซ้ำกัน 4 แถว ทุกแถวยาวเท่ากัน จึงไม่มี padding และผ่านแบบเหลือที่ว่างไม่ถึง 1 GiB",
               "**ตอนเทรนจริง** แถวใน batch ยาวไม่เท่ากัน ต้องเติม padding ทางขวา และส่ง `attention_mask` ทำให้ส่วน attention กินหน่วยความจำเพิ่มจนเกิด Out of Memory",
               "**วิธีแก้** หยุดส่ง `attention_mask` ตอนเทรน เพราะ padding อยู่ด้านขวา attention มองย้อนหลังอย่างเดียว และตำแหน่ง padding มี label `-100` ผลจึงเท่าเดิม"]},

    {"img": "n03-answer-loss",
     "title": "แก้ Out of Memory ใน Data Parallelism 4 ใบ: คิดคะแนนเฉพาะคำตอบ",
     "labels": ["แบบเดิม", "คำถาม + ตาราง + คำตอบ", "คำนวณ lm_head ทุกตำแหน่ง", "ขอเพิ่ม 594 MiB → Out of Memory",
                "AnswerLoss", "ข้ามคำถามและ padding", "คำนวณ lm_head เฉพาะคำตอบ", "ผ่านครบ 3 Epoch · loss เท่าเดิม"],
     "scene": "Two large rounded pastel comparison panels side by side connected by a bold arrow from left to right. "
              "Left panel (soft pink-orange): a horizontal sequence of colored blocks (question, table schema, SQL answer) where EVERY block feeds arrows into a giant heavy matrix block marked with a red X, with labels 'แบบเดิม', 'คำถาม + ตาราง + คำตอบ', 'คำนวณ lm_head ทุกตำแหน่ง', and 'ขอเพิ่ม 594 MiB → Out of Memory'. "
              "Right panel (soft mint green): the same horizontal sequence where the question and padding blocks are faded grey and skipped, and ONLY the short SQL answer blocks feed into a small compact block with a smiling white-and-blue robot and a green checkmark, with labels 'AnswerLoss', 'ข้ามคำถามและ padding', 'คำนวณ lm_head เฉพาะคำตอบ', and 'ผ่านครบ 3 Epoch · loss เท่าเดิม'. "
              "No bar charts, no gauges, no extra numbers.",
     "steps": ["**ต้นเหตุที่ล้ม** ที่ batch 4 ต่อใบ ตารางคะแนนคำศัพท์ทุกตำแหน่งมีขนาด `4 × 256 × 151,936 × 4 byte = 594 MiB` จนเกิด Out of Memory",
               "**`expandable_segments` ไม่ช่วย** เพราะปัญหาไม่ใช่หน่วยความจำแตกเป็นช่อง แต่ที่ว่างบนการ์ดไม่พอจริง",
               "**ทางแก้ (`AnswerLoss`)** ส่งเฉพาะตำแหน่งที่เป็นคำตอบเข้า `lm_head` เพื่อคิด loss ลด VRAM ที่ batch 4 จาก 22.71 เหลือ 21.25 GiB โดยได้ loss เท่าเดิม"]},

    {"img": "n04-caveats",
     "title": "ข้อจำกัดที่ต้องรู้เมื่ออ่านตัวเลขเทียบกัน",
     "labels": ["1 คนละเครื่องเช่า", "ความเร็วรวมความต่างของเครื่อง",
                "2 batch ไม่เท่ากัน", "4 · 8 · 16 จำนวน Update ต่างกัน",
                "3 เพิ่ม batch ทีละเท่าตัว", "ยังไม่ได้ลองค่าระหว่างกลาง"],
     "scene": "Three rounded pastel cards arranged side by side from left to right with numbered circle badges 1, 2, 3 and a friendly small white-and-blue robot holding a magnifying glass at the bottom right. "
              "Card 1 (soft blue): two distinct server chassis icons of slightly different shapes with small globe pin icons (no text on icons), with labels '1 คนละเครื่องเช่า' and 'ความเร็วรวมความต่างของเครื่อง'. "
              "Card 2 (soft peach): three neatly stacked trays of data cards (small, medium, large) next to a small circular refresh arrow icon, with labels '2 batch ไม่เท่ากัน' and '4 · 8 · 16 จำนวน Update ต่างกัน'. "
              "Card 3 (soft lavender): rounded stepping stones jumping over gaps with subtle question-mark bubbles in the gaps, with labels '3 เพิ่ม batch ทีละเท่าตัว' and 'ยังไม่ได้ลองค่าระหว่างกลาง'. "
              "No bar charts, no line charts, no gauges.",
     "steps": ["**ทั้ง 5 แบบรันบนเครื่องเช่าคนละเครื่อง** ตัวเลขความเร็วที่เทียบข้ามแบบจึงรวมความต่างของ CPU, PCIe และสภาพเครื่องไว้ด้วย",
               "**แต่ละแบบเทรนที่ batch ใหญ่สุดของตัวเอง** (4, 8 และ 16) จำนวนครั้งที่ปรับน้ำหนักต่อ Epoch จึงต่างกัน (1,000 · 500 · 250 ครั้ง)",
               "**การหา batch ในรอบตัวอย่างเพิ่มทีละเท่าตัว** (1, 2, 4, 8, 16, 32) แต่พรอมต์ปัจจุบันให้ AI ประมาณและลองค่าระหว่างกลางต่อได้"]},
]

PHOTOS = [
    # ---- ปกและหน้าคั่นเดิม (6 ภาพ)
    {"img": "s01-cover",
     "scene": "Cinematic dark studio photograph of an open high-performance AI server workstation on the right half of the frame, "
              "showing four sleek modern black graphics cards mounted inside with crisp cyan and warm amber LED edge lighting reflecting on brushed dark metal. "
              "The left 45% of the frame is deep dark navy-black shadow with smooth negative space for title text. Dramatic rim lighting, ultra-sharp, photorealistic."},

    {"img": "s02-foundations",
     "scene": "Cinematic high-contrast 3D render on the right half of the frame: translucent glowing glass data blocks smoothly flowing into stacked luminous cyan and gold neural network layers floating in dark space. "
              "The left 45% of the frame is deep dark midnight shadow with calm empty negative space. Crisp studio lighting, sleek architectural tech aesthetic."},

    {"img": "s03-single",
     "scene": "Cinematic dark studio close-up photograph on the right half of the frame: a single powerful black graphics card resting on a dark matte engineering desk, "
              "glowing intensely with warm orange-gold heat light along its cooling fins and a bright cyan core accent. "
              "The left 45% of the frame is dark shadowed background with clean negative space. Shallow depth of field, high contrast, photorealistic."},

    {"img": "s04-dp",
     "scene": "Cinematic dark studio photograph on the right half of the frame: four identical graphics cards aligned in parallel inside an open server rack, "
              "all glowing together in bright synchronized electric cyan light beams streaming forward in unison, representing parallel speed. "
              "The left 45% of the frame is deep dark shadow and clean negative space. High contrast, photorealistic."},

    {"img": "s05-mp",
     "scene": "Cinematic high-contrast 3D architectural render on the right half of the frame: four dark metallic GPU modules arranged in a sequential relay chain, "
              "with a single luminous golden-orange energy beam passing cleanly from the first module through the second and third to the fourth module. "
              "The left 45% of the frame is deep dark slate-black empty space. Dramatic volumetric light."},

    {"img": "s06-summary",
     "scene": "Cinematic photograph seen from behind on the right half of the frame: two fictional Thai engineers in dark smart-casual shirts standing in a dim modern data center aisle, "
              "looking calmly at a softly glowing server rack with warm amber and cyan indicator lights (completely out of focus, no readable symbols). "
              "The left 45% of the frame is deep dark out-of-focus shadow for text. Photorealistic, shallow depth of field."},

    # ---- ภาพใหม่สำหรับภาพรวม (1 ภาพ)
    {"img": "s07-lab4-journey",
     "scene": "Wide cinematic 3D architectural illustration (full-frame scenic vista, vibrant twilight navy sky with glowing cyan and warm gold lights, NO text anywhere): "
              "In the foreground left, a single lone glowing GPU tower reaches a glowing glass ceiling wall. From there, a luminous highway splits into TWO distinct dramatic elevated paths going toward the horizon: "
              "the upper left-to-right path is a blazing four-lane electric-cyan expressway with four sleek parallel light trains racing side by side (symbolizing Data Parallelism speed); "
              "the lower path is a monumental golden-amber multi-span bridge carrying one massive glowing crystal neural core across four sequential bridge pillars, with the final pillar glowing brightest gold (symbolizing Model Parallelism VRAM capacity). "
              "In the distant background, both paths converge at a bright glowing beacon tower. Rich storybook sci-fi editorial aesthetic, razor sharp, zero text, zero numbers, zero letters."},

    # ---- หน้า Hero เดิม (4 ภาพ)
    {"img": "h01-single",
     "scene": "Cinematic dark 3D studio render on the right half of the frame: a single dark metal graphics card tilted slightly at a heroic angle, "
              "its internal translucent glass chamber almost completely filled to the very top rim with glowing amber-orange energy and cyan edge highlights, conveying maximum capacity on one card. "
              "The left 45% of the frame is completely dark calm negative space."},

    {"img": "h02-dp2",
     "scene": "Cinematic dark 3D studio render on the right half of the frame: two identical sleek graphics cards standing side by side, "
              "both firing matching intense twin streaks of bright cyan light forward through dark atmospheric haze, evoking doubled parallel speed. "
              "The left 45% of the frame is deep dark empty shadow."},

    {"img": "h03-dp4",
     "scene": "Cinematic dark 3D studio render on the right half of the frame: four identical sleek graphics cards stacked in a dramatic diagonal formation, "
              "launching four brilliant synchronized streams of electric cyan and gold light forward at high velocity through dark space. "
              "The left 45% of the frame is deep dark empty shadow."},

    {"img": "h04-mp4",
     "scene": "Cinematic dark 3D studio render on the right half of the frame: four sequential dark metallic graphics card modules linked by a single massive translucent glowing neural spine spanning all four cards, "
              "with the fourth module at the end glowing noticeably brighter in vivid warm orange-gold energy than the calmer cyan modules before it. "
              "The left 45% of the frame is deep dark empty shadow."},

    # ---- หน้า Hero เชิงเปรียบเปรยใหม่สำหรับผลลัพธ์และบทสรุป (8 ภาพ)
    {"img": "h05-base-style",
     "scene": "Cinematic dark macro 3D studio render on the right half of the frame: jagged rough-cut amber glass puzzle pieces on one side smoothly transforming through a beam of cyan light into perfectly aligned, polished luminous crystal blocks clicking seamlessly into a precision golden frame. "
              "Metaphor for raw correct logic being refined into exact formatting style. Left 45% is pitch-dark clean shadow. Zero text, zero letters, zero numbers."},

    {"img": "h06-mp2",
     "scene": "Cinematic dark studio 3D photograph on the right half of the frame: a futuristic two-station dark metallic robotic relay assembly line in a dim lab. "
              "Station one is bathed in bright glowing orange-gold spotlight actively handing a glowing orb of energy to station two, while the inactive half waits quietly in cool dim blue shadow — visually depicting two GPUs taking turns one at a time. "
              "Left 45% is deep dark empty negative space. Zero text, zero numbers."},

    {"img": "h07-speed-battle",
     "scene": "Cinematic dark high-contrast 3D visual on the right half of the frame: long-exposure light-trail racing photography metaphor. "
              "In the upper half, four blazing electric-cyan parallel light streams rocket forward at blistering speed leaving shimmering streaks; "
              "below them, a single steady warm amber light ribbon moves calmly at constant pace on a single track. "
              "Left 45% is deep dark empty negative space for big white hero numbers. Zero text, zero numbers."},

    {"img": "h08-vram-battle",
     "scene": "Cinematic dark architectural 3D render on the right half of the frame: four tall sleek obsidian glass memory vaults standing in a row, "
              "the first three holding calm low cyan liquid light with generous headroom, while the fourth vault on the far right surges upward with intense blazing golden-amber light nearly reaching the top rim — symbolizing expanded total memory with the last card filling first. "
              "Left 45% is deep dark calm shadow. Zero text, zero numbers."},

    {"img": "h09-quality-epoch",
     "scene": "Cinematic dark studio photograph on the right half of the frame: a precision weathered archery target lit by dramatic warm rim lighting, "
              "with five sleek metallic arrows glowing with cyan and gold energy trails all clustered tightly together right inside the glowing golden bullseye center — metaphor for all five GPU arrangements achieving nearly identical model accuracy. "
              "Left 45% is pitch-dark calm negative space. Zero text, zero numbers."},

    {"img": "h10-choose-verdict",
     "scene": "Cinematic dark studio 3D architectural metaphor on the right half of the frame: a dramatic illuminated crossroads viewed from a slightly elevated angle, "
              "branching cleanly into three glowing futuristic bridges — one compact silver lane, one wide four-lane electric-cyan expressway, and one massive golden heavy-load viaduct — leading into a bright horizon. "
              "Left 45% is deep dark shadow for white text. Zero text, zero signs, zero numbers."},

    {"img": "h11-single-limit",
     "scene": "Cinematic dark studio close-up photograph on the right half of the frame: a single heavy black industrial graphics card encased in a glowing crimson-amber glass barrier wall, "
              "its internal cooling core glowing red-hot at maximum capacity with sparks of golden energy pressing right against the transparent ceiling limit. "
              "Left 45% is deep dark shadow for white hero numbers. Zero text, zero numbers."},

    {"img": "h12-3labs-summary",
     "scene": "Cinematic dark gallery-style 3D render on the right half of the frame: three dramatic illuminated architectural pedestals arranged cleanly in perspective — "
              "a sleek lone silver-amber GPU monolith (baseline), a synchronized parallel cyan quad-GPU array pulsing together (speed), and a massive golden interconnected four-pillar bridge holding one giant luminous core (capacity). "
              "Left 45% is deep dark calm shadow for big white summary text. Ultra-crisp, zero text, zero numbers."},
]

CARTOON = """Generate ONE illustration with your image generation tool and save it as a PNG file at exactly this path:
{out}/{img}.png

First open and look at these reference images, then match their illustration style exactly (same kind of flat, cute, clean
cartoon infographic: white or very light background, a pastel sky-blue rounded title banner at the top, rounded pastel cards
with thin dark navy outlines, numbered circle badges, small white-and-blue robot helper, bold rounded Thai lettering):
{refs}

Canvas: landscape 16:9 (about 1672 x 941). Setting: {setting}.

Title banner text at the top (exact): {title}

Scene: {scene}

Text labels to place in the picture, each next to the element it names (exact text, one label per line below):
{labels}

Strict text rules:
- Write every label EXACTLY as given, character by character. Thai stays Thai, English stays English, numbers and symbols stay as they are.
- Do NOT add any other words, numbers, captions, watermarks or logos beyond the title and the labels above.
- When a label starts with a number (for example "1 ตอนวัด (Probe)"), draw that number ONLY inside the circle badge and write the rest of the label next to it. Never repeat the same number twice.
- Do NOT draw bar charts, line charts, gauges, meters or progress bars. Nothing in the picture may suggest an unmeasured value.
- Text must be large, bold and easy to read from the back of a classroom. Code-like labels use a monospace style.
- Characters: fictional cartoon characters only.

Rules: create only that one file. Do not modify any other file. Do not run any git command (no add, commit, push).
When the file is saved, reply with the file path and stop.
"""

PHOTO = """Generate ONE high-impact cinematic image with your image generation tool and save it as a JPG file at exactly this path:
{out}/{img}.jpg

Scene: {scene}

Requirements:
- Landscape 16:9 (about 1920x1080), cinematic high-contrast lighting, deep shadows, crisp cyan, orange, and warm gold accents.
- Keep the left 45% of the frame very dark, calm, and uncluttered (negative space) because white titles and big white numbers will be placed over the left side later; place the main visual subject on the right 55% (except for full-frame scenic maps where explicitly noted).
- ABSOLUTELY NO readable text anywhere: no letters, no numbers, no logos, no brand names, no signs, no watermarks, no UI text on screens.
- Any people must be generic fictional adults seen from behind or in silhouette; no recognizable real person's likeness.

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
        open(os.path.join(out, f["img"] + ".txt"), "w", encoding="utf-8").write(PHOTO.format(
            out=out, img=f["img"], scene=f["scene"]))
    print("%d prompts -> %s" % (len(FIGS) + len(PHOTOS), out))
