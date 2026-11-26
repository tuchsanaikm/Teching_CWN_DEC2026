"""Generate the 4 benchmark tasks (deterministic, seed fixed)."""
import random
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

OUT = Path(__file__).parent / "tasks"
OUT.mkdir(exist_ok=True)
FMT = "\n\nตอบโดยให้บรรทัดสุดท้ายเป็น `ANSWER: <คำตอบ>` เท่านั้น"

# 1) multi-step arithmetic  -> 490428.75
(OUT / "t1_math.txt").write_text(
    "โจทย์คิดเลข (ห้ามใช้เครื่องมือ ให้คิดเอง):\n"
    "ร้านค้าซื้อสินค้า 487 กล่อง กล่องละ 36 ชิ้น ตรวจพบชิ้นเสีย 2,958 ชิ้นจึงทิ้งไป "
    "ที่เหลือแบ่งเท่า ๆ กันให้ 7 สาขา จากนั้นแต่ละสาขาได้รับเพิ่มจากโกดังอีกสาขาละ 1,234 × 3 ชิ้น "
    "แล้วแต่ละสาขาขายไปสาขาละ 17² ชิ้น สินค้าที่เหลือทุกชิ้นตีราคาชิ้นละ 12.75 บาท "
    "มูลค่าสินค้าที่เหลือรวมทั้ง 7 สาขาเป็นกี่บาท" + FMT + " (ตัวเลขล้วน ไม่มีจุลภาค)\n",
    encoding="utf-8")

# 2) bug fix -> graded by running hidden-equal visible tests
BUGGY = '''def second_largest(nums):
    """Return the second largest DISTINCT value in nums, or None if there are fewer than 2 distinct values."""
    largest = second = None
    for n in nums:
        if largest is None or n > largest:
            second = largest
            largest = n
        elif n > second:
            second = n
    return second
'''
TESTS = '''assert second_largest([3, 1, 2]) == 2
assert second_largest([5, 5, 4]) == 4
assert second_largest([5, 5]) is None
assert second_largest([]) is None
assert second_largest([-1, -2, -3]) == -2
assert second_largest([1, 2, 2, 3, 3]) == 2
assert second_largest([7, 3, 9, 9, 8]) == 8
'''
(OUT / "tests_t2.py").write_text(TESTS, encoding="utf-8")
(OUT / "t2_bugfix.txt").write_text(
    "ฟังก์ชัน Python นี้มีบั๊ก แก้ให้เทสต์ทุกข้อผ่าน (ห้ามแก้เทสต์ ไม่ต้องสร้างไฟล์ ตอบในข้อความเท่านั้น)\n\n"
    "```python\n" + BUGGY + "```\n\nเทสต์:\n```python\n" + TESTS + "```\n\n"
    "ตอบเป็นฟังก์ชัน second_largest ที่แก้แล้วทั้งฟังก์ชัน ในโค้ดบล็อก ```python เพียงบล็อกเดียว\n",
    encoding="utf-8")

# 3) needle in 2,000-line document -> VX-7318-KAPPA (decoy: VX-2049-SIGMA revoked)
rnd = random.Random(20261123)
lines = []
for i in range(1, 2001):
    if i == 412:
        lines.append(f"L{i:04d} NOTE old secret code VX-2049-SIGMA REVOKED do not use")
    elif i == 1374:
        lines.append(f"L{i:04d} NOTE current secret code is VX-7318-KAPPA")
    else:
        lines.append(f"L{i:04d} id={rnd.randrange(16**6):06x} val={rnd.randrange(10000):04d} st={rnd.choice(['ok','ok','ok','warn','err'])}")
(OUT / "t3_needle.txt").write_text(
    "เอกสารต่อไปนี้ยาว 2,000 บรรทัด มีรหัสลับที่ยังใช้งานได้อยู่ (current) หนึ่งรหัส จงหารหัสนั้น\n"
    "=== BEGIN DOCUMENT ===\n" + "\n".join(lines) + "\n=== END DOCUMENT ===\n"
    "รหัสลับที่ยังใช้ได้คืออะไร" + FMT + "\n", encoding="utf-8")

# 4) read number on a sign -> 73915
W, H = 900, 600
img = Image.new("RGB", (W, H), (120, 160, 200))
d = ImageDraw.Draw(img)
d.rectangle([0, 430, W, H], fill=(90, 90, 90))           # road
d.rectangle([435, 300, 465, 560], fill=(70, 70, 70))      # pole
d.rounded_rectangle([170, 60, 730, 330], 28, fill=(20, 110, 60), outline=(255, 255, 255), width=10)
try:
    big = ImageFont.truetype("arialbd.ttf", 130)
    small = ImageFont.truetype("arialbd.ttf", 44)
except OSError:
    big = small = ImageFont.load_default()
d.text((450, 120), "PARKING ZONE", font=small, fill="white", anchor="mm")
d.text((450, 235), "73915", font=big, fill="white", anchor="mm")
img = img.rotate(4, resample=Image.BICUBIC, fillcolor=(120, 160, 200)).filter(ImageFilter.GaussianBlur(1.2))
img.save(OUT / "t4_sign.png")
(OUT / "t4_sign.txt").write_text(
    "ดูภาพป้ายที่ไฟล์ {IMG} แล้วบอกตัวเลขตัวใหญ่ที่เขียนบนป้าย" + FMT + "\n", encoding="utf-8")
print("ok")
