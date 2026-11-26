# สรุปการแก้ไข `slug.py`

ตามรายการปัญหาใน [review.md](file:///workspace/ex/23/review.md)

## ปัญหา: `slugify()` คืนสตริงว่างที่ใช้เป็นชื่อไฟล์ไม่ได้
- **สาเหตุเดิม:** เมื่ออินพุตว่างหรือมีเฉพาะอักขระพิเศษ/ช่องว่าง/ขีดกลาง ฟังก์ชันประมวลผลแล้วตัดออกจนเหลือ `""` ซึ่งไม่สามารถใช้เป็นชื่อไฟล์ได้
- **การแก้ไข:**
  - เพิ่มพารามิเตอร์ทางเลือก `default: str | None = None` ใน `slugify(title: str, default: str | None = None) -> str`
  - ตรวจสอบผลลัพธ์หลังตัดขีดกลางหัวท้าย หากผลลัพธ์เป็นสตริงว่าง (`not slug`):
    1. ถ้ามีการระบุ `default` (ไม่ใช่ `None`) จะคืนค่า `default` เป็นชื่อไฟล์สำรอง
    2. ถ้าไม่ได้ระบุ `default` (เป็น `None`) จะยกเลิกด้วย `ValueError(f"Cannot generate a valid filename slug from title: {title!r}")` เพื่อปฏิเสธอินพุตที่นำไปสร้างชื่อไฟล์ไม่ได้อย่างชัดเจน
  - เพิ่ม docstring ระบุรายละเอียดพารามิเตอร์, ค่าส่งคืน และข้อยกเว้น (`Raises: ValueError`)

## ผลการทดสอบด้วย `python3`

| กรณีทดสอบ | อินพุต | เรียกฟังก์ชัน | ผลลัพธ์ | สถานะ |
| --- | --- | --- | --- | --- |
| สตริงว่าง | `''` | `slugify('')` | ยกเลิกด้วย `ValueError` | ผ่าน |
| สตริงว่าง (มี fallback) | `''` | `slugify('', default='untitled')` | `'untitled'` | ผ่าน |
| อักขระพิเศษล้วน | `'!@#$%^&*()_+'` | `slugify('!@#$%^&*()_+')` | ยกเลิกด้วย `ValueError` | ผ่าน |
| ช่องว่างล้วน | `' \t\n '` | `slugify(' \t\n ')` | ยกเลิกด้วย `ValueError` | ผ่าน |
| ขีดกลางล้วน | `'---'` | `slugify('---')` | ยกเลิกด้วย `ValueError` | ผ่าน |
| ขีดกลางล้วน (มี fallback) | `'---'` | `slugify('---', default='default-doc')` | `'default-doc'` | ผ่าน |
| ข้อความปกติ | `'Hello, World! My First Article #1'` | `slugify(...)` | `'hello-world-my-first-article-1'` | ผ่าน |
| เว้นวรรคซ้อน | `'Hello   World'` | `slugify(...)` | `'hello-world'` | ผ่าน |
| ขีดกลางซ้อน | `'Hello---World'` | `slugify(...)` | `'hello-world'` | ผ่าน |
| ขีดกลางหัวท้าย | `'--Hello World---'` | `slugify(...)` | `'hello-world'` | ผ่าน |
| ตัวเลข | `'2026'` | `slugify(...)` | `'2026'` | ผ่าน |
| อักษรมีเครื่องหมาย | `'Café Déjà Vu'` | `slugify(...)` | `'cafe-deja-vu'` | ผ่าน |
| ขีดล่าง | `'foo_bar'` | `slugify(...)` | `'foobar'` | ผ่าน |
| แท็บและขึ้นบรรทัด | `'Hello\tWorld\nAgain'` | `slugify(...)` | `'hello-world-again'` | ผ่าน |

บันทึกสรุปเรียบร้อยที่ [fixes.md](file:///workspace/ex/23/fixes.md)