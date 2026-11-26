# exercises/10 — ส่งข้อมูลยาวข้ามค่ายด้วยไฟล์ (difficulty 2)

run_id: `20261124-052342-ponq` · แผน: `graph.json` · ผลดิบ: `run_result.txt`
ไฟล์ข้อมูล: `/workspace/ex/10/products.csv` ใน container (200 แถว, รหัสไม่ซ้ำ 200, ราคาไม่ซ้ำ 200, 6 หมวด)

| งาน | บัญชี | คำตอบ | ถูกหรือไม่ | ส่งข้อมูลด้วยอะไร |
|---|---|---|---|---|
| 1. make_csv | cyolo1 (gpt-6.2-sol/medium, 28.3 s) | `/workspace/ex/10/products.csv` | ถูก (200 แถว ราคาไม่ซ้ำ) | ไฟล์ (เขียน products.csv) |
| 2. max_price | gyolo1 (gemini-3.8-flash-medium, 15.4 s) | `P099` | ถูก (Blue Tea Kettle, 99602) | ไฟล์ (อ่าน products.csv) |
| 2. min_price | yolo1 (sonnet/medium, 5.0 s) | `P087` | ถูก (Cinnamon Waffle Mix, 214) | ไฟล์ (อ่าน products.csv) |
| 3. ตรวจคำตอบ | หัวหน้า (python3 ใน container) | max = P099 · min = P087 | ตรงทั้งสองข้อ | ไฟล์ (คำนวณจาก products.csv) + ค่าในข้อความ (รหัสที่ได้จากงานที่ 2) |

งานที่ 2 ทั้งสองเริ่มพร้อมกันหลัง make_csv เสร็จ
