# Exercise 32 — ย้ายงานเมื่อลูกทีมโควตาหมด (จำลอง)

- run: `20261124-053803-sblo` (สำเนาอยู่ที่ `./run/`)
- คำสั่ง: `cat graph.json | docker exec -i multi-account python3 //root/ai-accounts/.Claude/shared/skills/agent-team/scripts/team.py run - --workers cyolo1,cyolo2,yolo2,gyolo1 --simulate-limit cyolo1`
- งานทั้ง 3 ชิ้น: `kind: code`, `difficulty: 1`, ไม่ระบุบัญชี (`any`) → router ส่งให้ Codex ก่อน (gpt-6.2-sol/low)
- แผนตอนแรก: find_max→cyolo1, find_min→cyolo2, find_mean→cyolo1

| งาน | บัญชีที่ได้รับงานตอนแรก | บัญชีที่ทำจนเสร็จ | เหตุผลที่ย้าย |
|---|---|---|---|
| find_max | cyolo1 | cyolo2 | cyolo1 ล้มเพราะ limit (จำลองโควตาหมด, 0 tokens) → ย้ายไปบัญชีฝั่งเดียวกัน (Codex) ก่อน |
| find_min | cyolo2 | cyolo2 | ไม่ได้ย้าย |
| find_mean | cyolo1 | cyolo2 | cyolo1 ล้มเพราะ limit (จำลองโควตาหมด, 0 tokens) → ย้ายไปบัญชีฝั่งเดียวกัน (Codex) ก่อน |

หลักฐาน: `run/ledger.jsonl` มี `event: worker_switch` 2 แถว (cyolo1 → cyolo2) · `run/msgs/cyolo1__cyolo2.md` · ผลโค้ดใน `run/out/*.md`
