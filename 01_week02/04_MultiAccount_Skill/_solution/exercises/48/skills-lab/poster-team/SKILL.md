---
name: poster-team
version: 0
description: รับหัวข้องานอีเวนต์ แล้วใช้ agent-team ทำโปสเตอร์ครบชุด - ข้อความโปสเตอร์ ภาพประกอบที่ตรวจข้ามค่าย และหน้าเว็บ 1 หน้า ใช้เมื่อผู้ใช้พูดว่า "ทำโปสเตอร์งาน...", "โปสเตอร์อีเวนต์", "หน้าเว็บประชาสัมพันธ์งาน" · Event topic → poster text, cross-checked illustration, one-page web poster via agent-team.
---

# poster-team v0

**ใช้เมื่อ** ต้องการโปสเตอร์ประชาสัมพันธ์งานอีเวนต์จากหัวข้อเดียว (ต้องมีสกิล agent-team และบัญชี yolo/cyolo/gyolo ใน container `multi-account`)

**สั่ง** (ใน container · `P=<ที่อยู่สกิล>/scripts/poster_team.py`):

```
python3 $P "งานวิ่งการกุศล 5 กิโลเมตร" --out /workspace/out/run5k [--difficulty 2] [--details "วันเวลา สถานที่จริง"] [--workers yolo1,cyolo1,gyolo1]
```

`--topic-file f.txt` = อ่านหัวข้อจากไฟล์ (กันภาษาไทยเพี้ยนใน shell) · `--graph-only` = เขียนแผนแล้วหยุด · `--dry-run` = ดูการจัดบัญชีโดยไม่เรียกโมเดล · `AGENT_TEAM_PY` = path ของ team.py (ค่าเริ่มต้น: สกิลกลาง ใช้อ่านอย่างเดียว)

**ได้ผล** ใน `--out`: `text.md` (ข้อความ) · `art.png` (ภาพที่ผ่านการตรวจข้ามค่าย + Claude ตัดสิน) · `index.html` (หน้าเว็บรวมข้อความกับภาพ) · `graph.json` · `run.log` (ตารางเวลา/โทเค็น/โควตา) · ผลตรวจบรรทัดแรก `ผ่าน`/`ไม่ผ่าน` อยู่ใน run folder `out/check.md` · คืน 1 ถ้ามีงานล้ม

**แผนงานต้นแบบ** (`references/graph.template.json` · ทุกงานใช้ `--difficulty` เดียวกัน):

| งาน | ฝั่ง | ขึ้นกับ | ทำอะไร |
|---|---|---|---|
| text | yolo | – | เขียน text.md: ชื่องาน คำโปรย วันเวลา สถานที่ จุดเด่น 3 ข้อ วิธีสมัคร |
| art | gyolo สร้าง → cyolo ตรวจ → Claude ตัดสิน | – | `type:image` + `criteria` (สื่อหัวข้อ ไม่มีตัวอักษร) สูงสุด 3 รอบ |
| page | cyolo | text, art | index.html ไฟล์เดียว ใช้ art.png ข้อความตรงทุกคำ รองรับมือถือ |
| check | gyolo | page | เทียบ index.html กับ text.md ตอบ ผ่าน/ไม่ผ่าน (ไม่แก้ไฟล์) |
