---
name: gyolo
description: สั่งงานบัญชี Antigravity CLI (gyolo1–gyolo5, รุ่น Gemini และอื่น ๆ) ใน docker container "multi-account" ได้แก่ ส่ง prompt แบบไม่โต้ตอบ, เลือกบัญชีที่โควตาเหลือมากสุดให้อัตโนมัติ, แปลงความยาก 1–6 เป็นรุ่น, อ่านไฟล์ภาพ, สร้างภาพ (ตรวจผลจริง), ตรวจความพร้อม, ดูโควตา, ดูรุ่น และสรุปสถิติการใช้ ใช้เมื่อผู้ใช้ต้องการส่งงานให้ gyolo, Antigravity หรือ Gemini
---

# gyolo — Antigravity CLI (gyolo1–5)

`G = python <โฟลเดอร์สกิลนี้>/scripts/gyolo.py` (ในเครื่องนี้คือ `python C:\t\ma04\b\app\skills\gyolo\scripts\gyolo.py`)

| ต้องการอะไร | ใช้คำสั่งไหน |
|---|---|
| สั่งงาน 1 ครั้ง (เลือกบัญชีที่โควตาเหลือมากสุดให้) | `G run -d 2 "คำสั่ง"` |
| ระบุบัญชีเอง | `G run -a gyolo2 -d 3 "คำสั่ง"` (`-a 2` ก็ได้) |
| prompt ยาวหรืออยู่ในไฟล์ | `G run -d 3 -f prompt.txt` หรือ `type prompt.txt \| G run -d 3` |
| ให้อ่านหรือตรวจภาพ | `G run -d 1 -i pic.png "ในภาพมีอะไร"` (ใส่ `-i` ซ้ำได้) |
| สร้างภาพเป็นไฟล์ | `G image -o out.png "คำอธิบายภาพ"` ตอนทดสอบใช้ไม่ได้เพราะ image model ตอบ 503 **ถ้าต้องการภาพแน่นอนให้ใช้สกิล `cyolo`** |
| ตรวจความพร้อม (เรียกจริงทุกบัญชี) | `G check` |
| ดูโควตาที่ใช้ไป (%) | `G quota` |
| ดูรุ่นที่ใช้ได้และตารางความยาก | `G models` |
| ดูสถิติการใช้ | `G stats` · `G stats --all --since 24` |
| จำกัดให้แตะได้เฉพาะบางบัญชี | ตั้ง `AI_SKILL_ACCOUNTS=gyolo2,gyolo3` ก่อนรัน (บัญชีอื่นจะไม่ถูกเรียกเลย; `AI_SKILL_AUDIT=<ไฟล์>` จดทุกการเรียก) |
| ได้ผลเป็น JSON | เติม `--json` ได้ทุกคำสั่ง |

**ความยาก (`-d`):** ระดับการคิดอยู่ในชื่อรุ่นแล้ว

| `-d` | รุ่น |
|---|---|
| 1 | gemini-3.8-flash-low |
| 2 (ค่าเริ่มต้น) | gemini-3.8-flash-medium |
| 3 | gemini-3.8-flash-high |
| 4 | gemini-4-carbon-medium |
| 5 | gemini-4-neon-high |
| 6 | gemini-4-neon-xhigh |

- ยังไม่ได้ยืนยันว่า Neon, Carbon, Argon และ Hydrogen รุ่นไหนเก่งกว่ากัน
- ถ้าต้องการระบุเอง ใช้ `-m gemini-4-argon-high` หรือรุ่นของค่ายอื่นในรายการ เช่น `-m claude-sonnet-5-5-medium` ซึ่งใช้โควตา "claude+gpt" แยกต่างหาก

## ผลลัพธ์
- **stdout** มีเฉพาะคำตอบ หรือ path ของไฟล์ภาพเมื่อใช้ `image`
- **stderr** มีบรรทัดเดียวในรูป `[บัญชี · รุ่น · เวลา · tokens · ok|FAILED ชนิด]`
- exit code: `0` สำเร็จจริง · `1` งานล้ม · `2` ใช้คำสั่งผิด · `3` ไม่มีบัญชีพร้อมหรือบัญชีที่ระบุไม่ได้ล็อกอิน
- agy ตอบ `status:"SUCCESS"` และ exit 0 แม้เครื่องมือล้ม สคริปต์จึงตรวจผลซ้ำ โดยเฉพาะ `image` ที่จะล้ม (exit 1) เมื่อเจอกรณีเหล่านี้:
  - `capacity` หรือ `tool_failed`: image model ใช้ไม่ได้
  - `fake_image`: agent วาดภาพด้วยโค้ดแทน image model
  - `no_image`: ไม่มีไฟล์ภาพจริง

## เรียกจากที่ไหน
- **เครื่องของผู้ใช้ (นอก container):** รันคำสั่งข้างบนได้เลย สคริปต์จะ `docker cp` ตัวเองเข้าไปแล้ว `docker exec` ให้ ไฟล์ที่ส่งด้วย `-i` และ `-o` ใช้ path บนเครื่องได้
  - ต้องมี `docker` และ Python 3
  - ถ้า container ชื่ออื่น ให้ตั้ง `AI_SKILL_CONTAINER`
- **ใน container:** `python3 .../gyolo.py ...`
- ถ้าไม่ใช้สคริปต์ ให้ copy เข้าไปเอง: `docker cp gyolo.py multi-account:/tmp/ai-skills/bin/` แล้วรัน `docker exec multi-account python3 /tmp/ai-skills/bin/gyolo.py check`
- `--cwd` เป็น path **ใน container**
- ให้ใช้ path แบบ absolute เสมอ เพราะ wrapper ตั้ง `HOME` เป็นโฟลเดอร์บัญชี ทำให้ `~` ไม่ใช่ `/root`

## กฎ
- **ห้าม**เปิดไฟล์ credential (`antigravity-oauth-token` และไฟล์อื่นในโฟลเดอร์บัญชี)
- **ห้าม**ล็อกอินแทนผู้ใช้
- ถ้าเจอ `not_logged_in` ให้บอกผู้ใช้รัน `docker exec -it multi-account gyoloN` เอง
- ห้ามเรียก `gyoloN -p ...` ตรง ๆ กับบัญชีที่ไม่ได้ล็อกอิน เพราะ CLI จะค้างรอ OAuth 60 วินาที สคริปต์ตรวจด้วย `models` ก่อนแล้ว
- `check`, `run` และ `image` ใช้โควตาจริง ส่วน `quota` (`/usage`) และ `models` ไม่เรียกโมเดล
- ทุกครั้งที่ใช้ `run`, `image` หรือ `check` สคริปต์จะจด 1 บรรทัดลง `/root/ai-accounts/.skill-usage/usage.jsonl` (บันทึกกลาง) โดยไม่จดข้อความคำสั่ง คำตอบ หรือ secret

## ข้อควรรู้
- gyolo1 กับ gyolo2 มีโควตาและเวลา reset ตรงกันทุกค่า น่าจะเป็นบัญชีเดียวกัน
- `quota` แปลงค่า "Remaining" ของ agy ให้เป็น % ที่ใช้ไปแล้ว
- slash command ที่ agy ไม่รู้จักจะถูกส่งไปเป็น prompt ให้โมเดลและเสียโควตา สคริปต์จึงใส่ `--disable-slash-commands` และเติม `Task:` นำหน้า prompt ที่ขึ้นต้นด้วย `/`
