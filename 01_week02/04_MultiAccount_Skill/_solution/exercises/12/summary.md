# แบบฝึกหัด 12 — แผนเที่ยวเชียงใหม่ 1 วัน (agent-team)

run_id: `20261124-052446-qfkx` · บัญชี: yolo1, cyolo1, gyolo1 · ความยาก 2 ทุกงาน

| งาน | บัญชี (รุ่น) | ต้องรองานไหนก่อน | เวลา (วินาที) |
|---|---|---|---|
| 1. places — เลือก 3 สถานที่ | yolo1 (sonnet/medium) | – | 5.7 |
| 2a. schedule — ตารางเวลา 09:00–18:00 | cyolo1 (gpt-6.2-sol/medium) | places | 27.2 |
| 2b. cost — ค่าใช้จ่ายต่อคน | gyolo1 (gemini-3.8-flash-medium) | places | 30.4 |
| 3. merge — รวมเป็นแผนเดียว | yolo1 (sonnet/medium) | schedule, cost | 16.5 |
| 4. verify — ตรวจเวลา/ยอดรวม | cyolo1 (gpt-6.2-sol/medium) | merge | 13.6 |

ผลตรวจ: **ผ่าน** (ไม่มีช่วงเวลาทับซ้อน · 50+50+120+80+70+150 = 520 บาท)
เวลารวมตามเส้นทางวิกฤต ≈ 5.7 + 30.4 + 16.5 + 13.6 = 66.2 วินาที (2a และ 2b รันพร้อมกัน)

ไฟล์: `graph.json` (แผนงาน) · `plan_final.md` (แผนเที่ยวฉบับสุดท้าย) · `run_result.json` · `run/` (สำเนา run folder)
