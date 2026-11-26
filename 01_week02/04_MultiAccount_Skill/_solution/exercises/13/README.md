# แบบฝึกหัด 13 — ให้ agent-team เลือกบัญชีเองตามชนิดงาน

- กราฟงาน: `graph.json` (ไม่ระบุ `account` ในงานใดเลย จึงใช้ค่าเริ่มต้น `any` = router · ทุกงานใช้ `difficulty: 2`)
- run: `20261124-053820-pecp` (ใน container: `/workspace/.agent-team/20261124-053820-pecp/`) · log: `run.log` · สถานะ: `state.json`
- ผลงาน: `out/*.md`, `leap.py`, `password-guide.md`

| งาน | ชนิดของงาน (`kind`) | บัญชีที่สกิลเลือก | เหตุผลที่สกิลเลือกค่ายนั้น |
|---|---|---|---|
| 1. ฟังก์ชันตรวจปีอธิกสุรทิน | `code` | cyolo1 (Codex, gpt-6.2-sol/medium) | router ส่ง `code` ไป Codex ก่อน · cyolo1 คะแนนต่ำสุดในค่าย (โควตาที่ใช้ 10%, ไม่มีงานค้าง) |
| 2. ตรวจโค้ดจากงาน 1 | `review` | cyolo2 (Codex, gpt-6.2-sol/medium) | router ส่ง `review` ไป Codex ก่อน · cyolo1 มีงาน code อยู่แล้ว (+15 คะแนน) จึงได้ cyolo2 (ผลพลอยได้: ผู้ตรวจเป็นคนละบัญชีกับผู้เขียน แต่ยังเป็นค่ายเดียวกัน) |
| 3. คู่มือรหัสผ่าน ~1 หน้า | `doc` | yolo2 (Claude, sonnet/medium) | router ส่ง `doc`/`long` ไป Claude ก่อน · yolo2 โควตาที่ใช้ต่ำสุด (1%) เทียบ yolo1 30%, yolo3 47% |
| 4. ชื่อทีมฟุตบอล 5 ชื่อ | ไม่ระบุ (งานทั่วไป) | gyolo1 (Antigravity, gemini-3.8-flash-medium) | งานไม่มี kind → เลือกบัญชีคะแนนต่ำสุดจากทั้ง 3 ค่าย · gyolo1 session 5% / week 1% และยังไม่มีงานในคิว |

ทุกงานสำเร็จ (`ok`) · บัญชีที่ไม่ได้ล็อกอิน (yolo4–5, cyolo3–5, gyolo3–5) ถูกข้ามอัตโนมัติ
