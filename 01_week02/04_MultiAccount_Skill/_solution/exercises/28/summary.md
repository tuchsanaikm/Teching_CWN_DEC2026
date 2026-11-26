# ข้อ 28 — โปสเตอร์ "วิ่งเพื่อน้อง 5 กม." (Gemini สร้าง → Codex ตรวจ → Claude ตัดสิน)

run_id: `20261124-054422-rwpx` · max_rounds 3 · ใช้ไป 2 รอบ · ผลสุดท้าย: **ACCEPT**

| รอบ | ผู้สร้าง | ผู้ตรวจ | ผลตรวจ | คำแนะนำของผู้ตรวจ | คำตัดสิน | เวลา (วินาที) |
|---|---|---|---|---|---|---|
| 1 | gyolo1 (Gemini, gemini-3.8-flash-medium) | cyolo1 (Codex, gpt-6.1-terra/low) | FAIL | ลบนักวิ่งทั้งหมดที่อยู่ด้านหลังและตามถนน ให้เหลือเฉพาะนักวิ่งสามคนด้านหน้า คงข้อความและภาพทะเลไว้ | – (ส่งกลับไปสร้างรอบ 2) | 53.7 + 10.7 = 64.4 |
| 2 | gyolo2 (Gemini, gemini-3.8-flash-medium, ใช้ภาพรอบ 1 เป็นภาพตั้งต้น) | cyolo2 (Codex, gpt-6.1-terra/low) | PASS | ข้อความสะกดถูกต้อง เห็นนักวิ่ง 3 คนพอดี และเห็นทะเลชัดเจน | ACCEPT โดย yolo2 (Claude sonnet/medium) | 58.0 + 10.6 + 6.9 = 75.5 |

รวมทั้งหมด 140.0 วินาที

## ไฟล์
- `graph.json` — แผนงานที่เขียนและส่งเข้า run
- `run/graph.run.json`, `run/state.json`, `run/ledger.jsonl` — แผน, สถานะ และสถิติจาก run directory
- `run/poster.r1.png`, `run/poster.r2.png` — ภาพของแต่ละรอบ
- `run/poster.r1.check.md`, `run/poster.r2.check.md`, `run/poster.judge.md` — ผลตรวจและคำตัดสิน
- `poster_final.png` — ภาพที่ได้ ACCEPT (ไฟล์เดียวกับรอบ 2)
