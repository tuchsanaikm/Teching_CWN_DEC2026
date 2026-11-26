---
name: gyolo
description: เรียก Antigravity CLI (agy) บัญชี gyolo1…gyoloN แบบไม่โต้ตอบให้ถูกวิธี เลือกรุ่น Gemini ตามความยาก ให้ดู/ตรวจภาพจากไฟล์ สร้างภาพ (ผ่าน subagent image-generator ของ agy) ตรวจล็อกอินด้วยการเรียกจริง ดูโควตา (/usage แปลงเป็น % ที่ใช้ เทียบกับ Claude/Codex ได้) และสถิติโทเค็นต่อครั้ง ใช้เมื่อผู้ใช้พูดว่า "เรียก gyolo1", "ให้ Gemini ดูภาพ", "ตรวจภาพ", "บัญชี Gemini ไหนพร้อม", "โควตา gyolo" · Use to call Antigravity/Gemini accounts (gyoloN) non-interactively, look at and generate images, pick model by difficulty, check real login state, read quota and per-call token stats.
---

# gyolo — Antigravity CLI ทุกบัญชี (gyolo1…gyoloN)

`G=/root/ai-accounts/.Claude/shared/skills/gyolo/scripts/gyolo.py` (สำเนาเดียวกันที่ `.Codex/shared/skills/gyolo` และ `.Gemini/shared/skills/gyolo`)

| ต้องการ | คำสั่ง |
|---|---|
| เรียกงานเดียว (บัญชีที่โควตาเหลือมากสุด) | `python3 $G run "โจทย์" -d 2` |
| บัญชีเจาะจง | `python3 $G run "โจทย์" -a gyolo2 -d 3` |
| กำหนดรุ่น/effort เอง | `python3 $G run "โจทย์" -m gemini-4-hydrogen -e high` (หรือ id เต็ม `-m gemini-4-hydrogen-high`) |
| ให้ดู/ตรวจภาพ | `python3 $G run "ป้ายในภาพเขียนว่าอะไร" --image /abs/sign.png -d 1` |
| ทำงานในโฟลเดอร์ | `python3 $G run "แก้โค้ดใน ./" --cwd /abs/proj -d 3` |
| ผลเป็น JSON | เติม `--json` |
| prompt ยาว | `python3 $G run - -a gyolo1 < prompt.txt` |
| ตรวจความพร้อม (เรียกจริง) | `python3 $G check` |
| โควตา (+ เวลาของข้อมูล) | `python3 $G quota` |
| รุ่นที่มี + ตารางความยาก 3 CLI | `python3 $G models` |
| สถิติ | `python3 $G stats` · `--account gyolo1` · `--run <run_id>` |
| สร้างภาพ PNG | `python3 $G image "ป้ายร้านกาแฟ" --out /workspace/img/sign.png` (เซิร์ฟเวอร์ภาพไม่ว่าง → ล้มชัดเจนด้วย `image_unavailable`) |
| แก้ภาพจากภาพเดิม | `python3 $G image "เปลี่ยนป้ายเป็นสีเขียว" --ref /workspace/img/sign.png --out /workspace/img/sign2.png` |
| งานหลายบัญชี | ใช้สกิล `agent-team` |

ทุกครั้งที่เรียกผ่าน `run`/`check` เพิ่ม 1 แถวใน `/workspace/.agent-team/ledger.jsonl` (`cli: gemini` · thinking → `reasoning_tokens` · cache read → `cached_input_tokens` · `cost_usd` ว่าง) และพิมพ์ตารางบัญชี | รุ่น | เวลา | tokens ไปที่ stderr

## ความยาก → รุ่น (`-d`) · effort อยู่ในชื่อรุ่น

| d | งาน | Antigravity |
|---|---|---|
| 1 | ดึงข้อมูล จัดรูปแบบ ตรวจความพร้อม ดูภาพ | `gemini-3.8-flash-low` |
| 2 | สรุป ถาม-ตอบ แก้โค้ดจุดเดียว (ค่าเริ่มต้น) | `gemini-3.8-flash-medium` |
| 3 | แก้หลายไฟล์ debug วิเคราะห์ | `gemini-4-hydrogen-medium` |
| 4 | reasoning ซับซ้อน | `gemini-4-hydrogen-high` |
| 5 | ต้องถูกแน่นอน | `gemini-4-argon-high` |
| 6 | งานใหญ่ที่วางแผนเอง | `gemini-4-carbon-high` |

รุ่นที่ไม่มีใน `gyoloN models` → ใช้รุ่นตระกูลเดียวกัน effort ใกล้สุด แล้วตระกูลสำรอง (หมายเหตุบอกเสมอ) · ตารางรวม 3 CLI: `python3 $G models`

## กฎสำคัญ (สคริปต์จัดการให้แล้ว ถ้าเรียก `gyoloN` เองต้องทำตาม)

- รูปแบบ: `gyoloN -p "<prompt>" --model <id> --output-format json --print-timeout 900s < /dev/null` → `{"status":"SUCCESS"|"ERROR","response","error","usage":{input_tokens,output_tokens,thinking_tokens,cache_read_tokens}}`
- **บัญชีที่ไม่ได้ล็อกอิน: `-p` ไม่ล้มทันที** แต่พิมพ์ลิงก์ sign-in ทาง stderr แล้วรอ 60 วินาที → สคริปต์หยุดให้ทันทีและไม่เก็บลิงก์ · ตรวจล็อกอินด้วย `gyoloN models` (ไม่ได้ล็อกอิน = `Please sign in` + exit 1)
- ล้ม: exit ≠ 0 และ `status: ERROR` · timeout = exit 3 + `finished_reason: print_timeout` · บรรทัด `AGY_ERROR: {...}` ทาง stderr บอกชนิด (เช่น `RESOURCE_EXHAUSTED` = โควตาหมด)
- `input_tokens` ไม่รวม cache read (เหมือน Claude) · `output_tokens` รวม thinking แล้ว
- โฟลเดอร์ทำงาน = cwd ของ process (`--cwd`) · อ่านไฟล์นอกโฟลเดอร์ได้ · เพิ่มโฟลเดอร์ด้วย `--add-dir`
- บัญชีเดียวรัน `-p` พร้อมกันได้หลายตัว และหลายบัญชีขนานกันได้ (โควตาใช้ร่วมทั้งบัญชี)
- ดูภาพ: agy ไม่มี flag แนบภาพ ให้ใส่ absolute path ใน prompt (`--image` ทำให้)
- **สร้างภาพ**: Gemini สร้างภาพผ่าน subagent `image-generator` (รุ่น `gemini-3.1-flash-image`) · `image "คำอธิบาย" --out /abs/a.png` สั่งให้ใช้เครื่องมือภาพเท่านั้น ห้ามวาดด้วยโค้ด แล้วตรวจว่าได้ PNG ที่ `--out` ซึ่งเขียนระหว่างการเรียก · ทดสอบ 2026-11-24: 43–77 วินาทีต่อภาพ ได้ 1024×1024 (ขอแนวนอน 16:9 ได้ 1376×768) ตัวหนังสือไทยบนป้ายสะกดถูก · **แก้ภาพเดิม**: `--ref old.png` ใช้ภาพเดิมเป็นภาพตั้งต้น เปลี่ยนเฉพาะที่สั่ง ส่วนอื่นคงเดิม · เซิร์ฟเวอร์ภาพไม่มีกำลังประมวลผล (HTTP 503 พบทุกครั้งเมื่อ 2026-11-23) → `image_unavailable` + ข้อความจากเซิร์ฟเวอร์ exit 1 และ agent-team ย้ายงานนั้นไป Codex ให้
- โควตา: `gyoloN -p "/usage" --output-format json` (ไม่เรียกโมเดล) รายงาน **% ที่เหลือ** ของกลุ่ม Gemini และกลุ่ม Claude/GPT (5 ชม. + สัปดาห์) → สคริปต์แปลงเป็น % ที่ใช้ (session = 5 ชม., week = สัปดาห์) ให้เทียบกับ Claude/Codex ได้
- ห้ามอ่าน/ส่งต่อไฟล์ token ใน `$BASE/.Gemini/gyoloN/` ห้ามแสดงอีเมล · ห้ามล็อกอินแทนผู้ใช้

รายละเอียด JSON, ข้อผิดพลาด, ผลวัดรุ่น: `references/details.md`

## เรียกจาก host

ใช้ได้ทั้ง PowerShell และ Git Bash โดยไม่ต้องแก้ (`//root/...` กัน Git Bash แปลง path):

```
docker exec multi-account cat //root/ai-accounts/.Claude/shared/skills/gyolo/SKILL.md
docker exec multi-account python3 //root/ai-accounts/.Claude/shared/skills/gyolo/scripts/gyolo.py check
docker exec multi-account python3 //root/ai-accounts/.Claude/shared/skills/gyolo/scripts/gyolo.py run "ตอบ OK" -a gyolo1 -d 1
docker exec multi-account python3 //root/ai-accounts/.Claude/shared/skills/gyolo/scripts/gyolo.py run "ภาพนี้คืออะไร" --image //workspace/img/red.png -d 1
docker exec multi-account python3 //root/ai-accounts/.Claude/shared/skills/gyolo/scripts/gyolo.py image "วงกลมสีเขียว" --out //workspace/img/green.png
docker exec multi-account python3 //root/ai-accounts/.Claude/shared/skills/gyolo/scripts/gyolo.py quota
docker exec multi-account python3 //root/ai-accounts/.Claude/shared/skills/gyolo/scripts/gyolo.py models
cat prompt.txt | docker exec -i multi-account python3 //root/ai-accounts/.Claude/shared/skills/gyolo/scripts/gyolo.py run - -a gyolo2
```
