---
name: agent-team
description: ให้หลายบัญชีจาก 3 CLI (Claude yoloN, Codex cyoloN, Antigravity gyoloN) ทำงานร่วมกัน - relay, fan-out/fan-in, DAG, review, debate, best-of-N, router, สร้างภาพแล้วตรวจข้าม CLI, failover ตามโควตา, human gate, สลับหัวหน้าทีม, สถิติโทเค็น ใช้เมื่อผู้ใช้พูดว่า "แบ่งงานหลายบัญชี", "ให้ Claude Codex Gemini ช่วยกัน", "ตรวจไขว้", "สร้างภาพแล้วให้อีกตัวตรวจ" · Use for multi-account agent teams across Claude, Codex and Antigravity: task graphs, cross-CLI review and image checks, quota-aware failover, leader handoff, token stats.
---

# agent-team — หลายบัญชีทำงานร่วมกัน

`T=/root/ai-accounts/.Claude/shared/skills/agent-team/scripts/team.py` (สำเนาเดียวกันที่ `.Codex/shared/skills/` และ `.Gemini/shared/skills/`) · ทุก run อยู่ที่ `/workspace/.agent-team/<run_id>/`

| ต้องการ | คำสั่ง |
|---|---|
| รันกราฟงาน → ตารางสรุป + โควตา | `python3 $T run graph.json` (path สัมพัทธ์ = ใต้ `/workspace`) · `run -` = อ่าน stdin |
| ใช้เฉพาะบางบัญชี (ไม่แตะบัญชีอื่นเลย) | `python3 $T run graph.json --workers yolo2,cyolo1,gyolo1` |
| ผลเป็น JSON | เติม `--json` |
| ดูแผนโดยไม่เรียกโมเดล | `--dry-run` |
| รันต่อเฉพาะงานที่ล้ม/ถูกบล็อก | `python3 $T run --resume <run_id>` (+ `--set fix.expect=number` หรือ `run fixed.json --resume <id>`) |
| อนุมัติงานที่ `"approve": true` | `python3 $T approve <run_id> <node>` |
| ภาพรวมบัญชี/งานของ run | `python3 $T status` (`--run <id>`, `--refresh`) |
| สถิติ (ตามบัญชี/รุ่น/run) | `python3 $T stats` (run ล่าสุด) · `--all` · `--run <id>` · `--account gyolo1` |
| ตรวจความพร้อม / โควตาทุกบัญชี | `python3 $T check` · `python3 $T quota` (`--workers a,b` = เฉพาะบัญชีนี้) |
| หัวหน้าทีมวางแผนเอง + สลับหัวหน้าได้ | `python3 $T lead --goal "เป้าหมาย"` |
| แชร์ความรู้ / ส่งข้อความ | `python3 $T board "ข้อค้นพบ" --author yolo1` · `python3 $T msg yolo1 gyolo1 "ข้อความ"` |

`check` `quota` `status` `stats` คืน 0 เสมอ · `run`/`lead` คืน 1 เมื่อมีงานล้ม · โควตาทุกฝั่งแสดงเป็น **% ที่ใช้** พร้อมเวลาของข้อมูล

## กราฟงาน (JSON)

```json
{"goal": "ทำขนาน → ตรวจ → แก้และทดสอบ",
 "nodes": [
  {"id": "code", "account": "yolo", "cwd": "/workspace/proj", "prompt": "เขียน calc.py มี add(a,b) และ div(a,b) (หารศูนย์ raise ValueError)"},
  {"id": "test", "account": "cyolo", "cwd": "/workspace/proj", "prompt": "เขียน unittest test_calc.py ทดสอบ add และ div รวมหารศูนย์"},
  {"id": "review", "kind": "review", "depends_on": ["code", "test"], "difficulty": 3,
   "prompt": "ตรวจ /workspace/proj/calc.py และ test_calc.py แล้วเขียนรายการปัญหาที่ต้องแก้"},
  {"id": "fix", "account": "gyolo", "depends_on": ["review"], "cwd": "/workspace/proj", "expect": "regex:OK",
   "prompt": "แก้โค้ดตาม {{file:review}} แล้วรัน python3 -m unittest test_calc ตอบบรรทัดสุดท้ายของผลเทสต์"}
 ]}
```

| ฟิลด์ | ความหมาย |
|---|---|
| `id` | ชื่องาน (A-Z a-z 0-9 _ . -) · ผลที่ `out/<id>.md` |
| `prompt` | โจทย์ · `{{id}}` = ค่าสั้นของงานก่อน · `{{file:id}}` = path ไฟล์ผล (ข้อมูลยาว) · `{{run_dir}}` |
| `account` | `gyolo2` (เจาะจง ไม่ย้าย) · `yolo`/`cyolo`/`gyolo` (ฝั่ง) · `any` (ค่าเริ่มต้น: router) |
| `difficulty` | 1–6 (ค่าเริ่มต้น 2) · override: `model` `effort` (เฉพาะ CLI ที่ชื่อรุ่นตรง) |
| `depends_on` | id ที่ต้องเสร็จก่อน |
| `expect` | `number` `int` `json` `regex:<pat>` `contains:<text>` → ตรวจก่อนส่งต่อ |
| `kind` | `image` → cyolo (Codex ใช้ไม่ได้ → gyolo) · `vision` (ดูภาพ) → gyolo→cyolo→yolo · `review`/`code` → Codex ก่อน · `doc`/`long` → Claude ก่อน · ไม่ระบุ → โควตาเหลือมากสุด |
| `type` | `task` (ค่าเริ่มต้น) · `image` (+`path` .png) · `review` · `debate` · `best_of` |
| อื่น ๆ | `cwd` (absolute) · `approve: true` = รอคนอนุมัติ · `timeout` วินาที · `board: false` = ไม่ใช้กระดาน |

ความยาก → รุ่นของ 3 CLI: ตารางใน references (d6 Claude = **fable**/high แพง ~2× opus มีโควตาสัปดาห์แยก)

รูปแบบพิเศษ (ใส่ `prompt` เสมอ · บัญชีฝั่งใดก็ได้):
- review loop: `{"type":"review","worker":"cyolo1","reviewer":"gyolo1","max_rounds":3,"criteria":"..."}` วนจนผู้ตรวจตอบ `APPROVED`
- debate: `{"type":"debate","accounts":["yolo","gyolo"],"judge":"cyolo1"}` ผู้ตัดสินสรุปคำตอบ + เหตุผล (`{{id}}` = คำตอบ)
- best-of-N: `{"type":"best_of","accounts":["yolo2","cyolo1","gyolo1"],"judge":"any","criteria":"..."}`
- ภาพ: `{"type":"image","path":"/workspace/out/a.png"}` (cyolo สร้าง ตรวจ PNG ให้ · Codex ใช้ไม่ได้ → gyolo) · `"account":"gyolo"` = ให้ Gemini สร้าง (subagent image-generator ~45–80 วินาทีต่อภาพ) ถ้าเซิร์ฟเวอร์ภาพของ Gemini ไม่มีกำลังประมวลผล (HTTP 503) ย้ายไป Codex + `worker_switch` · `gyolo1` เจาะจง = ล้มพร้อมเหตุผล
- **ภาพ + ตรวจข้าม CLI**: เติม `"criteria": "..."` (หรือ `"check": true`) [+ `checker` `judge` `max_rounds`] → ผู้สร้าง (cyolo หรือ `"account":"gyolo"`) → ผู้ตรวจจากคนละค่ายกับผู้สร้าง (cyolo สร้าง → gyolo ตรวจ · gyolo สร้าง → cyolo ตรวจ) ดูไฟล์แล้วตอบ PASS/FAIL + คำแนะนำ (FAIL = คำแนะนำเป็นคำสั่งรอบใหม่ · ผู้สร้างที่เป็น gyolo ได้ภาพรอบก่อนเป็นภาพตั้งต้นด้วย) → Claude ตัดสิน ACCEPT/REJECT · ภาพที่ ACCEPT อยู่ที่ `path` (`{{id}}`)

board: ทุก agent ได้ path ของ `board.md` · บรรทัด `BOARD: ...` ในคำตอบถูกต่อท้ายลงกระดานให้งานหลังใช้ · ข้อมูลข้าม CLI ส่งด้วยไฟล์ใน run folder

อัตโนมัติ: ตรวจความพร้อมด้วยการเรียกจริง (cache 10 นาที) · ส่งงานไปบัญชีที่โควตาเหลือมาก · โควตา ≥80% หรือเกินงบ → หยุดรับงานใหม่ · ล้มเพราะโควตา/ล็อกอิน → ย้ายในฝั่งเดียวกันก่อน แล้วฝั่งอื่น (เฉพาะ `any`) · บัญชีเจาะจงไม่ย้าย · งานที่ขึ้นกับงานที่ล้มถูกบล็อก · ตัวเลือก `--per-account 3` `--max-total 8` `--threshold 80` `--worker-token-budget N|gyolo1=N` `--simulate-limit gyolo1` `--recheck`

## หัวหน้าทีม + สลับหัวหน้า (lead)

```
python3 $T lead --goal "แบ่งงานให้ลูกทีม ... รวมเป็นไฟล์ {run_dir}/final/result.md"
python3 $T lead --demo [--goal "..."]   # สาธิตครบ: หัวหน้าล้ม + เกินงบ + ย้ายงานลูกทีม
```

หัวหน้าทำงานเป็นรอบ อ่าน `handoff.md` สั่งงานลูกทีม (process แยก) เขียน checkpoint · ผู้ควบคุม (สคริปต์) สลับหัวหน้าเมื่อเกินงบ/โควตา (เชิงรุก) หรือล้ม (เชิงรับ) · ลูกทีมมาจาก 3 ฝั่ง · หัวหน้าอัตโนมัติ = Claude แล้ว Codex (gyolo เฉพาะ `--leader`/`--succession` ที่ระบุเอง ดู references)
ตัวเลือก: `--leader` `--succession` `--workers` `--lead-token-budget N` `--worker-token-budget N` `--simulate-crash yolo1` `--simulate-limit cyolo2` `--resume <id>`

รายละเอียด (ไฟล์ใน run, ledger, router, ตารางความยาก, หัวหน้า, ภาพ+ตรวจ): `references/details.md`

## เรียกจาก host

ใช้ได้ทั้ง PowerShell และ Git Bash ไม่ต้องแก้ (`//root/...` กัน Git Bash แปลง path):

```
docker exec multi-account cat //root/ai-accounts/.Claude/shared/skills/agent-team/SKILL.md
docker exec multi-account python3 //root/ai-accounts/.Claude/shared/skills/agent-team/scripts/team.py check
cat graph.json | docker exec -i multi-account python3 //root/ai-accounts/.Claude/shared/skills/agent-team/scripts/team.py run -
cat graph.json | docker exec -i multi-account python3 //root/ai-accounts/.Claude/shared/skills/agent-team/scripts/team.py run - --workers yolo1,cyolo1,gyolo1 --json
docker exec multi-account python3 //root/ai-accounts/.Claude/shared/skills/agent-team/scripts/team.py lead --demo
docker exec multi-account python3 //root/ai-accounts/.Claude/shared/skills/agent-team/scripts/team.py stats
```

เขียน `graph.json` บน host ด้วย Write แล้ว pipe เข้า `run -` (ห้าม heredoc) · PowerShell 5.1 ทำภาษาไทยใน pipe เป็น `?` → ใช้ PowerShell 7 หรือ `\uXXXX` · ติดตั้ง: คัดลอก 4 โฟลเดอร์ (yolo cyolo gyolo agent-team) ไป `.Claude` `.Codex` `.Gemini` `/shared/skills/` wrapper ลิงก์ให้ตอนเปิดครั้งถัดไป
