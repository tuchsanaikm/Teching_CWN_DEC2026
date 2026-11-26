# แบบฝึกหัด 11 — ตรวจรูปแบบคำตอบ (expect) ก่อนส่งต่อ

run_id: `20261124-053524-oczp` · บัญชี: yolo1 (haiku/low), cyolo1 (gpt-6.2-sol/low) · ความยาก 1 ทุกงาน
expect ของ coupon: `regex:^CP-\d{4}$`

| งาน | รอบแรกเกิดอะไรขึ้น | รอบที่รันต่อเกิดอะไรขึ้น |
|---|---|---|
| coupon (yolo1) | รันแล้ว ตอบ `` `SAVE15ONLINE` `` ไม่ตรง regex จึงได้ **bad_output** (คำตอบยังเก็บไว้ใน out/coupon.md) | คำสั่งบอกรูปแบบแล้ว รันใหม่ ตอบ `CP-7429` ผ่านการตรวจ ได้ **ok** |
| notice (cyolo1) | **blocked** ไม่ได้เรียกโมเดลเลย (0 tokens) เพราะ coupon ไม่ผ่าน | รันครั้งแรกด้วย `CP-7429` ได้ **ok**: "ใช้รหัสคูปอง CP-7429 เพื่อรับส่วนลดได้เลยค่ะ" |

ไม่มีงานไหนถูกทำซ้ำโดยไม่จำเป็น: ledger มี 3 แถว (coupon ×2, notice ×1) coupon รันซ้ำเพราะรอบแรกไม่ผ่าน ส่วน notice รันครั้งเดียว
เพราะ expect บล็อกไว้ ข้อมูลที่ผิดรูปแบบจึงไม่ไปถึง cyolo1

ไฟล์: `graph.json` (รอบแรก) · `graph_fixed.json` (รอบรันต่อ) · `run1_result.txt` · `status_round1.txt` · `run2_resume_result.txt` · `run/` (สำเนา run directory)
