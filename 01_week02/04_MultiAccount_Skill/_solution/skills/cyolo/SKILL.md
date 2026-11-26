---
name: cyolo
description: เรียก Codex CLI บัญชี cyolo1…cyoloN แบบไม่โต้ตอบ เลือกรุ่นและ effort จาก models_cache.json สร้างภาพ (PNG — ผู้สร้างหลักของทีม) ตรวจล็อกอิน โควตา (rate_limits) และสถิติโทเค็นต่อครั้ง ใช้เมื่อผู้ใช้พูดว่า "ให้ cyolo ตรวจ", "เรียก cyolo1", "สร้างภาพ", "Codex บัญชีไหนพร้อม", "โควตา Codex" · Use to run Codex accounts (cyoloN) non-interactively, generate images (the team's primary image generator), check login, quota and per-call token stats.
---

# cyolo — Codex CLI ทุกบัญชี (cyolo1…cyoloN)

`C=/root/ai-accounts/.Codex/shared/skills/cyolo/scripts/cyolo.py` (สำเนาเดียวกันอยู่ที่ `.Claude/shared/skills/cyolo` และ `.Gemini/shared/skills/cyolo`)

| ต้องการ | คำสั่ง |
|---|---|
| เรียกงานเดียว (บัญชีที่โควตาเหลือมากสุด) | `python3 $C run "โจทย์" -d 2` |
| บัญชีเจาะจง / effort เอง | `python3 $C run "โจทย์" -a cyolo1 -e high` |
| เลือกรุ่น | `python3 $C run "โจทย์" -m <slug>` (ดู slug จาก `models`) |
| ให้ Codex ตรวจโค้ดในโฟลเดอร์ | `python3 $C run "ตรวจโค้ดใน /abs/path ..." --cwd /abs/path -d 3` |
| สร้างภาพ PNG | `python3 $C image "วงกลมสีแดงบนพื้นขาว" --out /workspace/img/red.png` |
| แนบภาพให้ดู | `python3 $C run "อธิบายภาพ" --image /abs/a.png` |
| ผลเป็น JSON | เติม `--json` |
| ตรวจความพร้อม (login status + เรียกจริง) | `python3 $C check` |
| โควตา (+ เวลาของข้อมูล) | `python3 $C quota` · `--refresh` = เรียกสั้น ๆ แบบไม่ ephemeral ก่อนเพื่ออัปเดต |
| รุ่นและ effort ที่รองรับ | `python3 $C models` |
| สถิติ | `python3 $C stats` · `--account cyolo1` |
| งานหลายบัญชี | ใช้สกิล `agent-team` |

## ความยาก → รุ่นและ effort (`-d`) · อ่านจาก `models_cache.json` เสมอ

| d | งาน | รุ่น | effort |
|---|---|---|---|
| 1 | ดึงข้อมูล จัดรูปแบบ ตรวจความพร้อม · สร้างภาพ | `gpt-6.2-sol` | low |
| 2 | สรุป ถาม-ตอบ แก้โค้ดจุดเดียว (ค่าเริ่มต้น) | `gpt-6.2-sol` | medium |
| 3 | แก้หลายไฟล์ debug วิเคราะห์ | `gpt-6.2-sol` | high |
| 4 | reasoning ซับซ้อน | `gpt-6.2-astra` | xhigh |
| 5 | ต้องถูกแน่นอน | `gpt-6.2-astra` | max |
| 6 | งานใหญ่ที่แตกงานย่อยเอง | `gpt-6.2-astra` | ultra (ถ้ารุ่นไม่รองรับ ลดเป็นระดับสูงสุดที่รองรับ และพิมพ์ว่าลดจากอะไร) |

รุ่นที่ไม่มีใน cache → ใช้รุ่นค่าเริ่มต้น (visibility `list` priority ต่ำสุด) · แนบภาพ (`--image`) ไม่ระบุ `-m` → ใช้ `gpt-6.1-terra` ถ้ามี (เก่งเรื่องดูภาพ) · สร้างภาพใช้รุ่นค่าเริ่มต้น effort low · ตารางรวม 3 CLI: `python3 $C models`

## กฎสำคัญ (สคริปต์จัดการให้แล้ว)

- รูปแบบ: `cyoloN exec --skip-git-repo-check --ephemeral -m <model> -c model_reasoning_effort=<level> --json -o <ไฟล์คำตอบ> "<prompt>" < /dev/null`
- คำตอบอยู่ในไฟล์ `-o` · stdout เป็น JSONL: `turn.completed.usage` = tokens · `turn.failed.error.message` = ล้ม
- **exit 0 ไม่ได้แปลว่าสำเร็จ**: บัญชีที่ไม่ได้ล็อกอินตอบ 401 แล้ว retry หลายรอบแต่ exit 0
- สถานะล็อกอินอ่านจากข้อความ `cyoloN login status` (`Logged in using ChatGPT` / `Not logged in`) ไม่ใช่ exit code
- `--ephemeral` เร็วกว่า แต่ไม่เขียน `sessions/` โควตาจึงมาจาก rollout ล่าสุดที่ไม่ ephemeral → รายงานเวลาของข้อมูลเสมอ
- สร้างภาพ: Codex เป็นผู้สร้างหลัก ใช้ effort `low` แล้วตรวจ PNG signature (สคริปต์ตรวจให้) · Gemini (`gyolo image`) สร้างได้เช่นกันผ่าน subagent ของ agy · agent-team ใช้ Codex ก่อน และใช้ Gemini เมื่อสั่ง `"account":"gyolo"` หรือเมื่อ Codex ใช้ไม่ได้
- ห้ามอ่าน/ส่งต่อ `auth.json` · ห้ามล็อกอินแทนผู้ใช้

รายละเอียด JSONL, โควตา, models_cache: `references/details.md`

## เรียกจาก host

ใช้ได้ทั้ง PowerShell และ Git Bash โดยไม่ต้องแก้:

```
docker exec multi-account cat //root/ai-accounts/.Codex/shared/skills/cyolo/SKILL.md
docker exec multi-account python3 //root/ai-accounts/.Codex/shared/skills/cyolo/scripts/cyolo.py check
docker exec multi-account python3 //root/ai-accounts/.Codex/shared/skills/cyolo/scripts/cyolo.py run "ตอบ OK" -a cyolo1 -d 1
docker exec multi-account python3 //root/ai-accounts/.Codex/shared/skills/cyolo/scripts/cyolo.py image "วงกลมสีแดง" --out //workspace/img/red.png
docker exec multi-account python3 //root/ai-accounts/.Codex/shared/skills/cyolo/scripts/cyolo.py quota
docker exec multi-account python3 //root/ai-accounts/.Codex/shared/skills/cyolo/scripts/cyolo.py models
```
