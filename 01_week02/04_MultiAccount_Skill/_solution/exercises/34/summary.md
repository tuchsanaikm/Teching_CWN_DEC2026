# Exercise 34 — งบโทเค็นลูกทีม: yolo1 เต็มหลังงานแรก (run 20261124-054147-vizr)

- คำสั่ง: `cat graph.json | docker exec -i multi-account python3 //root/ai-accounts/.Claude/shared/skills/agent-team/scripts/team.py run - --workers yolo1,yolo3 --worker-token-budget yolo1=1`
- 4 งานต่อกันเป็นลำดับ (`depends_on`) · `account: "yolo"` (ฝั่ง Claude ไม่เจาะจงบัญชี) · `difficulty: 1` → haiku/low
- `--workers yolo1,yolo3`: router เลือกบัญชีที่ใช้โควตาน้อยสุด ถ้าเปิด yolo2 (1%) ไว้ yolo1 (30%) จะไม่ได้งานแรก จึงจับคู่ yolo1 กับ yolo3 (47%) แทน
- โทเค็นที่นับกับงบ = input + cache write + output (ไม่นับ cache read)

| งาน | บัญชี | โทเค็นของงาน | โทเค็นสะสมของบัญชีนั้น |
|---|---|---|---|
| summer (ฤดูร้อน) | yolo1 | 19,080 | yolo1 = 19,080 |
| rainy (ฤดูฝน) | yolo3 | 18,017 | yolo3 = 18,017 |
| winter (ฤดูหนาว) | yolo3 | 15,359 | yolo3 = 33,376 |
| holiday (วันหยุด) | yolo3 | 17,109 | yolo3 = 50,485 |

yolo1 หยุดรับงานใหม่ตอน 05:41:57 ทันทีหลัง summer เสร็จ (19,080 > งบ 1) → `worker_stop`
งานที่แผนเดิมให้ yolo1 (rainy, holiday) ถูกย้ายไป yolo3 (`worker_switch` 2 แถว) ส่วน winter เป็นของ yolo3 อยู่แล้ว

ไฟล์: graph.json · run.log · run/ (ledger.jsonl, out/*.md)
