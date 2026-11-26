# พรอมต์ของบท 06 · KC-QUEST (หน้ารวม)

รวมพรอมต์และคำสั่งทั้งหมดของบทนี้ตามลำดับ คัดลอกไปวางได้ทันที คำอธิบาย ภาพ และผลจริงอยู่ใน [readme.md](readme.md)

**ก่อนเริ่ม:** เปิด terminal หรือ Claude Code app ที่โฟลเดอร์ `06_KC_QUEST` · บทนี้ไม่ใช้โทเคนและไม่ต้องมี container

## หัวข้อ 0 · ตรวจเครื่อง

วางที่: Terminal

```bash
python tools/kclab.py doctor
```

## หัวข้อ 2.1 · rank ของตัวอย่าง 14 บล็อก (ทวนบท 05)

วางที่: Terminal

```bash
python tools/kclab.py rank --blocks examples/system14/blocks.json
```

## หัวข้อ 2.3 · rank ของตัวอย่างบทนี้

วางที่: Terminal

```bash
python tools/kclab.py rank
```

## หัวข้อ 3 · ผลแจกงานทุกรอบ

วางที่: Terminal

```bash
python tools/kclab.py rounds --png
```

## หัวข้อ 4 · คำนวณทีละขั้น รอบที่ 1

วางที่: Terminal

```bash
python tools/kclab.py explain --round 1
```

## หัวข้อ 7.2 · เทียบกับวิธีอื่นด้วยตัวจำลอง

วางที่: Terminal

```bash
python tools/sim.py --seeds 200      # รันซ้ำเอง ใช้เวลาไม่ถึง 1 นาที
python tools/test_kclab.py           # ตรวจว่าตัวเลขในหน้านี้ยังตรงกับ base skill
```

## หัวข้อ 8.1 · พรอมต์สำหรับ Claude Code app

วางที่: Claude Code app ที่โฟลเดอร์ `06_KC_QUEST`

```text
อยู่ในโฟลเดอร์ 06_KC_QUEST ใช้ python tools/kclab.py (ดูวิธีใช้ด้วย --help) ห้ามแก้ไฟล์ใน base_skills
1. รันคำสั่ง rounds แล้ว explain รอบที่ 3 แบบ --png
2. อธิบายเป็นภาษาไทยสั้น ๆ ว่ารอบนั้น ① เรียงบล็อกอย่างไร ② บัญชีไหนถูกตัด เพราะอะไร ③ ตัวแปรไหนทำให้ผู้ชนะชนะ ④ หลังจองแล้วโควตาของผู้ชนะเปลี่ยนอย่างไร
3. บอก path ของภาพ round-3.png
```

## หัวข้อ 8.2 · เปลี่ยนน้ำหนัก

วางที่: Terminal

```bash
python tools/kclab.py rounds --weights urgency=0 --out out/w_u0
python tools/kclab.py rounds --weights load=-0.4 --out out/w_l4
```

## หัวข้อ 8.3 · เปลี่ยนสถานการณ์

วางที่: Terminal

```bash
python tools/kclab.py rounds --set yolo2.week_reset_h=200
python tools/kclab.py rounds --max-agents 4
```

## หัวข้อ 8.4 · ใช้คำสั่งจริงของสกิล

วางที่: Terminal

```bash
export DAGPLAN_DIR=out/plans
D=base_skills/dag-planner/scripts/dagplan.py
python $D dag meow-shop --blocks examples/meow-shop/blocks.json
python $D plan meow-shop --accounts yolo1:6,yolo2:90,yolo3:100,cyolo1:100,cyolo2:100
```
