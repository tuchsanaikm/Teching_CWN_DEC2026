#!/usr/bin/env python3
"""ภาพใหม่ของสไลด์บท 03_MultiAccount_Container

FIGS   = ภาพอธิบาย 1 ภาพต่อ 1 สไลด์ "ภาพ + ขั้นตอน" (ภาพด้านซ้าย ขั้นตอนเรียงเลขด้านขวา)
  img    ชื่อไฟล์ใน img/ (ไม่ใส่นามสกุล)
  title  หัวข้อของสไลด์ และข้อความบนป้ายชื่อของภาพ
  labels ข้อความสั้นบนภาพ (ป้ายที่เป็นขั้นตอนขึ้นต้นด้วยเลข)
  scene  คำบรรยายภาพเป็นภาษาอังกฤษ
  steps  ขั้นตอนข้างภาพ · เรียบเรียงจาก README.md ของบทเท่านั้น
PHOTOS = ภาพถ่ายสมจริงของหน้าปกและหน้าคั่น (ไม่มีตัวอักษรในภาพ · ฝั่งซ้ายมืดไว้วางหัวข้อ)

  python tools/slides_figures.py <โฟลเดอร์ปลายทาง นอกรีโป> [ภาพอ้างอิงสไตล์ ...]
      ภาพอ้างอิงสไตล์ = ภาพอธิบายเดิมของบท เช่น img/concept-01-three-approaches.png img/concept-05-three-clis.png
"""
import os, sys

SETTING = "a clean technical infographic about Docker containers on a developer's computer (Docker image, container, volume, terminals)"
PHOTO_SETTING = "a modern Thai university computer laboratory or a developer's desk"

FIGS = [
    {"img": "n01-home-agy", "title": "gyolo แยกบัญชีด้วย HOME เฉพาะ process ของ agy",
     "labels": ["1 พิมพ์ gyoloN", "2 HOME=/root/ai-accounts/.Gemini/gyoloN", "3 agy อ่าน config ของบัญชีนั้น",
                "shell ของระบบ: HOME=/root", "Antigravity CLI ไม่มีตัวแปรกำหนดโฟลเดอร์ config"],
     "scene": "Left: a terminal window (the system shell) with a house icon and the label for HOME=/root that stays unchanged. "
              "Right: a numbered flow left to right: (1) the user types the command; (2) a small wrapper box sets a different home folder "
              "only for one child process, drawn as a separate bubble branching off the shell; (3) the agy process reads its own config folder "
              "inside a volume drawn as a cylinder. A note card at the bottom with the last label.",
     "steps": ["**Antigravity CLI** ไม่มีตัวแปรกำหนดโฟลเดอร์ config",
               "คำสั่ง `gyoloN` จึงเปลี่ยน `HOME` ให้ **agy เท่านั้น** เป็น `/root/ai-accounts/.Gemini/gyoloN`",
               "`HOME` ของระบบยังเป็น `/root` เหมือนเดิม"]},
    {"img": "n02-multiarch", "title": "image ชื่อเดียว รองรับ 2 สถาปัตยกรรม",
     "labels": ["multi-account:1.0", "linux/amd64", "linux/arm64", "Windows / Intel", "Mac Apple Silicon",
                "ดึงแบบที่ตรงกับ CPU อัตโนมัติ", "ไม่ต้องรันผ่าน emulation"],
     "scene": "Top center: one Docker image drawn as a box of stacked layers with a padlock, containing two side-by-side inner layers "
              "(one for each architecture label). Two arrows go down: left arrow to a Windows desktop PC with an Intel-style chip icon, "
              "right arrow to an Apple-Silicon-style laptop (no brand logos). A ribbon between the arrows with the 'automatic' label, "
              "and a small crossed-out turtle icon next to the 'no emulation' label.",
     "steps": ["build ทั้ง `linux/amd64` (Windows / Intel) และ `linux/arm64` (Mac Apple Silicon) ใน image ชื่อเดียว",
               "เครื่องของผู้เรียนดึงแบบที่ตรงกับ **CPU ของตัวเอง** ให้อัตโนมัติ",
               "จึง**ไม่ต้องรันผ่าน emulation**"]},
    {"img": "n03-spec", "title": "สเปก prompt_multi_account.md มี 5 หัวข้อ",
     "labels": ["prompt_multi_account.md", "1 ฐานของ image", "2 เป้าหมาย", "3 กติกา", "4 ข้อเท็จจริงจากการทดลอง", "5 ทดสอบ · รายงาน"],
     "scene": "A large document page in the center titled with the file name, divided into five numbered horizontal sections stacked "
              "top to bottom. Each section has a small icon on its left: (1) stacked image layers; (2) three groups of user-account "
              "badges; (3) a shield with a check mark; (4) a lab flask with a magnifying glass; (5) a checklist next to three small report pages.",
     "steps": []},
    {"img": "n04-login", "title": "ล็อกอิน 1 บัญชีต่อ 1 แท็บ Terminal",
     "labels": ["JupyterLab Terminal", "1 yolo1 · Claude account with subscription", "2 cyolo1 · Sign in with ChatGPT",
                "3 gyolo1 · ลิงก์ accounts.google.com", "volume ai-accounts"],
     "scene": "A browser window showing JupyterLab with three terminal tabs side by side, numbered 1 to 3, each tab showing a simple "
              "login menu drawn as boxes (no extra text). A person sits in front of it and confirms in a second browser window. "
              "Below, arrows from all three tabs lead into one volume cylinder that stores the logins.",
     "steps": []},
    {"img": "n05-step3-test", "title": "ทุกบัญชีที่ล็อกอินแล้วค้นหาเที่ยวบินผ่าน Playwright MCP",
     "labels": ["1 skill shared-check", "2 MCP playwright", "3 Google Flights · BKK → Tokyo", "4 screenshot ทุกขั้น",
                "./evidence/<บัญชี>.gif", "ค้นหาอย่างเดียว ไม่จอง ไม่ชำระเงิน"],
     "scene": "Four numbered stages left to right connected by arrows: (1) an account badge reading a shared skill card; "
              "(2) a robot hand controlling a headless browser; (3) a simple flight search form with an airplane icon (no prices, no extra text); "
              "(4) a camera capturing four small frames. At the far right, the four frames are combined into one animated-image file icon. "
              "A red-bordered warning ribbon along the bottom with the last label, with crossed-out credit card and booking icons.",
     "steps": []},
]

PHOTOS = [
    {"img": "s01-cover", "scene": "A Thai developer in her twenties sits at a tidy desk in the evening with a laptop; beside the laptop stands a small "
                                  "toy model of stacked colorful shipping containers. Calm, focused mood."},
    {"img": "s02-theory", "scene": "A Thai university lecturer stands in front of a whiteboard on which only simple boxes and arrows are drawn "
                                   "(no writing at all), explaining to a few attentive students seen from behind."},
    {"img": "s03-lab", "scene": "Thai university students in white uniform shirts work on laptops in a bright computer laboratory, "
                                "screens blurred and abstract. Hands-on lab session mood."},
    {"img": "s04-step1", "scene": "Close-up of a developer's hands on a keyboard; on the desk a model of a cargo ship being loaded with identical "
                                  "shipping containers, symbolizing building one image for everyone. Monitor blurred."},
    {"img": "s05-step2", "scene": "A Thai student at a laptop confirms a sign-in on a smartphone held in one hand; the laptop screen is blurred. "
                                  "Personal, careful mood about logging in by oneself."},
    {"img": "s06-step3", "scene": "A laptop on a desk near a large window with an airplane taking off in the far distance at dusk; "
                                  "the laptop screen shows an abstract blurred map. A student watches the screen."},
    {"img": "s07-summary", "scene": "Three Thai students sit around a table reviewing results on one laptop together and nodding, "
                                    "late afternoon light, relaxed sense of completion."},
]

CARTOON = """Generate ONE illustration with your image generation tool and save it as a PNG file at exactly this path:
{out}/{img}.png

First open and look at these reference images, then match their illustration style exactly (clean flat technical infographic,
light background, navy-blue title banners, thick dark outlines, rounded cards, teal / orange / navy / light-blue palette,
numbered circle badges, simple icons, bold rounded Thai lettering, like a well-made textbook figure, not a children's cartoon):
{refs}

Canvas: landscape 4:3 (about 1448 x 1086). Topic: {setting}.

Title banner text at the top (exact): {title}

Scene: {scene}

Text labels to place in the picture, each next to the element it names (exact text, one label per line below):
{labels}

Strict text rules:
- Write every label EXACTLY as given, character by character. Thai stays Thai, English stays English, numbers and symbols stay as they are.
- Do NOT add any other words, numbers, captions, watermarks or logos beyond the title and the labels above.
- When a label starts with a number followed by a space (for example "3 กติกา"), draw that number ONLY inside the circle badge and write the rest of the label next to it. Never show the same number twice.
- Text must be large, bold and easy to read from the back of a classroom. Code-like labels (paths, commands, file names) use a monospace font.
- Do NOT draw any bar chart, line chart, gauge or progress bar.
- No real company logos (no Docker whale, no Apple, no Windows, no Google logo).

Rules: create only that one file. Do not modify any other file. Do not run any git command (no git add, commit, push or any other git command).
When the file is saved, reply with the file path and stop.
"""

PHOTO = """Generate ONE photorealistic image with your image generation tool and save it as a JPG file at exactly this path:
{out}/{img}.jpg

Scene: {scene}

Requirements:
- Photorealistic, natural warm light, shallow depth of field, landscape 16:9 (about 1920x1080).
- Setting: {setting}.
- People are fictional adults of Thai appearance; no real person's likeness.
- NO readable text anywhere: no letters, no numbers, no logos, no signs, no watermarks. Screens, whiteboards and papers must be blurred or abstract.
- Keep the left 45% of the frame calm and darker (out-of-focus background), main subject on the right side, because a title will be placed over the left side later.

Rules: create only that one file. Do not modify any other file. Do not run any git command (no git add, commit, push or any other git command).
When the file is saved, reply with the file path and stop.
"""

if __name__ == "__main__":
    out = os.path.abspath(sys.argv[1]).replace("\\", "/")
    refs = [os.path.abspath(p).replace("\\", "/") for p in sys.argv[2:]]
    if not refs:
        assets = os.path.join(os.path.expanduser("~"), ".claude", "skills", "readme-slides", "assets")
        refs = [os.path.join(assets, n).replace("\\", "/") for n in ("style-cartoon-1.jpg", "style-cartoon-2.jpg")]
    os.makedirs(out, exist_ok=True)
    for f in FIGS:
        open(os.path.join(out, f["img"] + ".txt"), "w", encoding="utf-8").write(CARTOON.format(
            out=out, img=f["img"], refs="\n".join(refs), setting=SETTING, title=f["title"], scene=f["scene"], labels="\n".join(f["labels"])))
    for f in PHOTOS:
        open(os.path.join(out, f["img"] + ".txt"), "w", encoding="utf-8").write(PHOTO.format(out=out, img=f["img"], setting=PHOTO_SETTING, scene=f["scene"]))
    print("%d พรอมต์ -> %s" % (len(FIGS) + len(PHOTOS), out))
