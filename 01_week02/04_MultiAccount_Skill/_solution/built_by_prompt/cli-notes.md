# บันทึกการสำรวจคำสั่งหลายบัญชีใน container `multi-account`

ทดสอบเมื่อ 2026-11-23 ใน container `multi-account` (image `multi-account:1.0`) โดยใช้ `docker exec multi-account bash -lc '...'`
ไม่ได้ลบ หยุด หรือสร้าง container ไม่ได้เปิดไฟล์ credential (`auth.json`, oauth token) และไม่ได้ล็อกอินให้บัญชีใด
ไฟล์ทดสอบชั่วคราวทั้งหมดอยู่ใน container ที่ `/tmp/clinotes/` (ภาพทดสอบอยู่ที่ `/tmp/clinotes/img/test.png`)

## 0. โครงสร้าง

| ชุด | wrapper | โปรแกรมจริง (เวอร์ชัน) | โฟลเดอร์บัญชี | flag ที่ wrapper ใส่ให้เสมอ |
|---|---|---|---|---|
| yolo1–5 | `/usr/local/bin/yoloN` | `claude` 2.1.330 | `CLAUDE_CONFIG_DIR=/root/ai-accounts/.Claude/yoloN` | `--dangerously-skip-permissions` และ `--mcp-config` (ถ้ามี shared mcp) |
| cyolo1–5 | `/usr/local/bin/cyoloN` | `codex` 0.171.0 | `CODEX_HOME=/root/ai-accounts/.Codex/cyoloN` | `--dangerously-bypass-approvals-and-sandbox` และ `-c cli_auth_credentials_store="file"` และ MCP |
| gyolo1–5 | `/usr/local/bin/gyoloN` | `agy` 1.5.15 | **`HOME=/root/ai-accounts/.Gemini/gyoloN`** | `--dangerously-skip-permissions` และ `AGY_CLI_DISABLE_AUTO_UPDATE=true` |

wrapper ส่ง `"$@"` ต่อให้ครบ จึงใช้ flag ของโปรแกรมจริงได้ทุกตัว ทุกชุดรันแบบอนุมัติอัตโนมัติ ทำให้ agent สั่งคำสั่ง shell ใน container ได้เต็มที่

---

## 1. สั่งงาน 1 ครั้งแบบไม่ต้องโต้ตอบ

### Claude Code (yolo)
```bash
yolo1 -p "คำถาม" --model haiku --output-format json < /dev/null
```
- คำตอบอยู่ที่ `.result`
- ต้องตรวจ `.is_error` ซึ่งควรเป็น `false` ห้ามดูแค่ `.subtype` เพราะตอนล้มก็ยังเป็น `"success"`
- โทเค็นอยู่ที่ `.usage.input_tokens`, `.usage.output_tokens`, `.usage.cache_read_input_tokens`, `.usage.cache_creation_input_tokens`
  - input จริงส่วนใหญ่อยู่ใน cache ตัวอย่างจากการรัน: input 2, cache_read 11,842, cache_create 21,471, output 4
- ข้อมูลอื่นในผล: `.total_cost_usd` (มูลค่าเทียบเท่า API), `.num_turns`, `.duration_ms`, `.modelUsage` (key คือชื่อรุ่นจริง เช่น `claude-haiku-5-5`)
- ถ้าใช้ `--output-format stream-json --verbose` จะได้ event `system/init` → `assistant` → `rate_limit_event` → `result`

### Codex CLI (cyolo)
```bash
cyolo1 exec --skip-git-repo-check --ephemeral -m gpt-6-luna -c model_reasoning_effort="low" \
       --json -o last.txt "คำถาม" < /dev/null
```
- คำตอบมีได้ 3 ที่:
  - ไฟล์จาก `-o last.txt` ซึ่งสะอาดที่สุด
  - event `{"type":"item.completed","item":{"type":"agent_message","text":...}}`
  - stdout ในโหมด text
- โทเค็นอยู่ใน event สุดท้าย `{"type":"turn.completed","usage":{input_tokens, cached_input_tokens, output_tokens, reasoning_output_tokens}}`
- ถ้าไม่ใส่ `--json` โทเค็นจะออกทาง **stderr** เป็นบรรทัด `tokens used` ตามด้วย `8,019` ส่วน stdout มีแค่คำตอบ
- งานล้มจะจบด้วย event `turn.failed` และ exit 1
- `--ephemeral` ทำให้ไม่เก็บ session ลงดิสก์ แต่จะดูโควตาจากไฟล์ session ไม่ได้ (ดูข้อ 3)

### Antigravity CLI (gyolo)
```bash
gyolo1 -p "คำถาม" --model gemini-3.8-flash-low --output-format json < /dev/null
```
- คำตอบอยู่ที่ `.response` และ**มี `\n` ต่อท้าย** ต้อง trim ก่อนใช้
- สถานะอยู่ที่ `.status` (`SUCCESS` หรือ `ERROR`), `.error`, `.finished_reason`
- โทเค็นอยู่ที่ `.usage.{input_tokens, output_tokens, thinking_tokens, cache_read_tokens, total_tokens}`
- ถ้าใช้ `--output-format stream-json` แต่ละบรรทัดใช้ key `event` (ไม่ใช่ `type`): `init` → `step_update` … → `result`
- มี `--print-timeout 60s` ไว้จำกัดเวลา (ค่าเริ่มต้นคือ 0 ซึ่งหมายถึงรอไม่จำกัด)

---

## 2. รุ่นและระดับการคิด

### Claude Code
- `--model`: alias ได้แก่ `haiku`, `sonnet`, `opus`, `fable` (alias ชี้ไปรุ่นล่าสุด) หรือใส่ชื่อเต็มก็ได้ ตอนทดสอบ `haiku` แปลงเป็น `claude-haiku-5-5`
- `--effort low|medium|high|xhigh|max`
- `--fallback-model` ใช้กำหนดรุ่นสำรองได้
- Fable มีโควตารายสัปดาห์แยกต่างหาก (เห็นใน `/usage` บรรทัด "Current week (Fable)")

### Codex CLI
- ดูรายการรุ่นด้วย `cyoloN debug models` ซึ่งให้ JSON ที่มี slug, effort ที่รองรับ และ input ที่รับได้
- รุ่นที่แสดงในรายการ (`vis=list`):

| รุ่น | คำอธิบายจาก catalog |
|---|---|
| `gpt-6.2-astra` | รุ่นเก่งสุดสำหรับงานโค้ดซับซ้อนและงานมืออาชีพ |
| `gpt-6.2-sol` | รุ่นหลัก เร็ว ใช้กับงานโค้ดและงานทั่วไป |
| `gpt-6.1-terra` | เด่นด้านภาพและ computer use |
| `gpt-6-luna` | เร็ว ถูก เหมาะกับงานง่าย |
| รุ่นเก่ากว่า | `gpt-6.1-sol`, `gpt-6-astra`, `gpt-6-sol`, `gpt-5.6-*` |

- ระดับการคิดตั้งด้วย `-c model_reasoning_effort="low|medium|high|xhigh|max|ultra"` (`ultra` มีเฉพาะบางรุ่น ส่วน luna ขึ้นได้ถึง max)
- ทุกรุ่นรับทั้ง text และ image

### Antigravity CLI
- ดูรายการรุ่นด้วย `gyoloN models` ซึ่งต้องล็อกอินก่อน
- ชื่อรุ่นมีระดับการคิดอยู่ท้ายชื่อแล้ว เช่น `gemini-3.8-flash-low`
- แยกใส่ `--model gemini-3.8-flash --effort low` ก็ใช้ได้ (ทดสอบแล้ว SUCCESS)

| กลุ่ม | รุ่น |
|---|---|
| Gemini 4 | Neon (low, medium, high, xhigh), Hydrogen (low, medium, high, xhigh), Carbon (low, medium, high), Argon (low, medium, high) |
| Orchestrator | `gemini-pro-orchestrator`(Carbon), `-neon`, `-argon` |
| Gemini 3.8 Flash | low, medium, high |
| รุ่นของค่ายอื่น | `claude-opus-5-5-*`, `claude-sonnet-5-5-*`, `gpt-oss-120b-medium` |

- รุ่นของค่ายอื่นใช้โควตาคนละก้อนกับ Gemini ("Claude and GPT models")

### คำแนะนำการเลือกรุ่น
ส่วนนี้เป็นความเห็นจากคำอธิบายใน catalog และชื่อรุ่น ยังไม่ได้วัดคุณภาพจริง

| งาน | Claude Code | Codex CLI | Antigravity CLI |
|---|---|---|---|
| ง่าย | `--model haiku --effort low` | `-m gpt-6-luna` + effort `low` | `gemini-3.8-flash-low` |
| ปานกลาง | `--model sonnet --effort medium` | `-m gpt-6.2-sol` + effort `medium` | `gemini-3.8-flash-high` หรือ `gemini-4-carbon-medium` |
| ยาก | `--model opus` หรือ `fable` + `--effort high` หรือ `xhigh` | `-m gpt-6.2-astra` + effort `high` หรือ `xhigh` | `gemini-4-neon-high` หรือ `-xhigh` (หรือ `claude-opus-5-5-high` ซึ่งใช้โควตาอีกก้อน) |

ข้อควรระวังสำหรับ Antigravity: ยังไม่มีข้อมูลยืนยันว่า Neon, Hydrogen, Carbon และ Argon รุ่นไหนเก่งกว่ากัน ที่เดาว่า Neon และ Hydrogen เป็นรุ่นบน เพราะสองรุ่นนี้เท่านั้นที่มีระดับ xhigh

---

## 3. ตรวจว่าบัญชีใช้ได้จริงและดูโควตา

| | ตรวจว่าล็อกอินอยู่ (เร็ว ไม่เสียโควตา) | ดูโควตาที่เหลือ |
|---|---|---|
| Claude | `yoloN auth status` ได้ JSON ที่มี `loggedIn`, `subscriptionType`, `planTier`, `loginExpiresAt` และ exit 1 ถ้าไม่ได้ล็อกอิน (**ผลมี email/org ต้องกรองก่อนแสดง**) | `yoloN -p /usage --output-format json` แล้วอ่าน `.result` ซึ่งเป็นข้อความ "Current session / Current week / Current week (Fable): X% used · resets ..." โดย**ไม่เสียโทเค็น** (cost 0) หรือดู event `rate_limit_event.rate_limit_info.unifiedWindows.{five_hour,seven_day}.utilization` ใน stream-json |
| Codex | `cyoloN login status` ได้ "Logged in using ChatGPT" (exit 0) หรือ "Not logged in" (exit 1) | ไม่มีคำสั่ง non-interactive โดยตรง ต้องรันงาน**แบบไม่ใส่ `--ephemeral`** แล้วอ่านบรรทัด `"rate_limits"` ในไฟล์ `$CODEX_HOME/sessions/YYYY/MM/DD/rollout-*-<thread_id>.jsonl` (field `primary.used_percent`, `window_minutes`, `resets_at`, `credits.balance`, `plan_type`) |
| Antigravity | `gyoloN models` ได้รายการรุ่น (exit 0) หรือ "Please sign in..." (exit 1) | `gyoloN -p /usage --print-timeout 30s < /dev/null` ได้ตาราง "Gemini Models / Claude and GPT models" ทั้งแบบ Weekly และ Five Hour พร้อม **% ที่เหลือ** และเวลา reset (ไม่เรียกโมเดล) |

ผลจริงตอนทดสอบ (ไม่มีอีเมล):

| บัญชี | สถานะ | แผน/โควตา |
|---|---|---|
| yolo1 | ใช้ได้ | max_20x · สัปดาห์ใช้ไป 25% (Fable 20%) · reset 26 พ.ย. |
| yolo2 | ใช้ได้ | team · session 4% · สัปดาห์ 0% |
| yolo3 | ใช้ได้ | team · สัปดาห์ใช้ไป 47% · **Fable ใช้ไป 76%** · reset 24 พ.ย. 13:00 (เวลากรุงเทพฯ) |
| yolo4, yolo5 | ไม่ได้ล็อกอิน | — |
| cyolo1 | ใช้ได้ | prolite · 7 วันใช้ไป 10% · reset 28 พ.ย. · credits 62,500 |
| cyolo2 | ใช้ได้ | **ตัวเลขเหมือน cyolo1 ทุกค่า** |
| cyolo3–5 | ไม่ได้ล็อกอิน | — |
| gyolo1 | ใช้ได้ | Gemini: สัปดาห์เหลือ 92%, 5 ชม. เหลือ 76% · Claude/GPT: เหลือ 100% |
| gyolo2 | ใช้ได้ | **ตัวเลขและเวลา reset เหมือน gyolo1 ทุกค่า** |
| gyolo3–5 | ไม่ได้ล็อกอิน | — |

> cyolo1 กับ cyolo2 และ gyolo1 กับ gyolo2 มีโควตาเหมือนกันทุกค่าจนถึงระดับวินาที จึงน่าจะล็อกอินด้วยบัญชีเดียวกันหรือใช้ workspace ร่วมกัน ถ้าเป็นอย่างนั้น การสลับบัญชีจะไม่ได้โควตาเพิ่ม ควรตรวจเองว่าเป็นอีเมลเดียวกันหรือไม่

---

## 4. ภาพ: ใครสร้างได้ ใครอ่านได้

| | สร้างภาพ | อ่านภาพ |
|---|---|---|
| Claude Code | **ไม่ได้** (ไม่มีเครื่องมือสร้างภาพ) | **ได้** ด้วยการบอก path ใน prompt แล้วโมเดลใช้เครื่องมือ Read (ใช้ 2 turn) |
| Codex CLI | **ได้** เพราะ feature `image_generation` เปิดอยู่ ไฟล์ไปอยู่ที่ `$CODEX_HOME/generated_images/<thread>/*.png` | **ได้** ด้วย `-i ไฟล์.png` หรือบอก path ใน prompt (feature `view_image`) |
| Antigravity CLI | **มีเครื่องมือ** `generate_image` แต่**ตอนทดสอบล้ม**: image model `gemini-3.1-flash-image` ตอบ HTTP 503 "No capacity" | **ได้** ด้วยการบอก path ใน prompt (ใช้ 1 turn) |

ผลการทดสอบ:
1. gyolo1 สร้างภาพวงกลมแดงไม่สำเร็จ (503) **แต่ได้ status SUCCESS และ exit 0**
2. cyolo1 (`gpt-6-luna`, low) สร้างได้ เป็น PNG ขนาด 1254×1254 ประมาณ 1 MB แล้ว copy ไปไว้ที่ `/tmp/clinotes/img/test.png` ใช้ไป 65,084 input / 217 output tokens
3. yolo1 (haiku) อ่านได้: "A solid red circle, centered on a plain white background."
4. gyolo1 (flash-low) อ่านได้: "The image contains a solid red circle centered on a plain white background."
5. ทดสอบเพิ่มด้วย cyolo2 `-i test.png` ได้ "A large red circle is centered on a white background."

---

## 5. ส่งข้อมูลข้ามชุด (ส่งต่อ 3 ทอด)

แนวทางคือให้แต่ละทอดตอบ "เฉพาะตัวเลข" ใช้ output ที่สะอาดที่สุดของแต่ละชุด trim ช่องว่าง ตรวจว่าเป็นตัวเลข แล้วจึงใส่ลงใน prompt ของทอดถัดไป

```bash
isnum(){ [[ "$1" =~ ^-?[0-9]+$ ]] || { echo "NOT A NUMBER: [$1]" >&2; exit 2; }; }
# ทอด 1: Claude
J=$(yolo1 -p "Compute 7*6. Reply with only the integer, nothing else." --model haiku --output-format json < /dev/null) || exit 1
[ "$(jq -r .is_error <<<"$J")" = false ] || exit 1
A=$(jq -r .result <<<"$J" | tr -d '[:space:]'); isnum "$A"
# ทอด 2: Codex
cyolo1 exec --skip-git-repo-check --ephemeral -m gpt-6-luna -c model_reasoning_effort="low" -o chain2.txt \
  "Add 100 to $A. Reply with only the integer, nothing else. Do not run any commands." < /dev/null > /dev/null || exit 1
B=$(tr -d '[:space:]' < chain2.txt); isnum "$B"
# ทอด 3: Antigravity
G=$(gyolo1 -p "Multiply $B by 3. Reply with only the integer, nothing else." --model gemini-3.8-flash-low --output-format json < /dev/null) || exit 1
[ "$(jq -r .status <<<"$G")" = SUCCESS ] || exit 1
C=$(jq -r .response <<<"$G" | tr -d '[:space:]'); isnum "$C"
```
ผลจริง: `yolo1 → 42`, `cyolo1 → 142`, `gyolo1 → 426` ✅ (คาดไว้ 426)

ถ้าข้อมูลยาว ให้ส่งผ่านไฟล์ใน path แบบ absolute (เช่น `/tmp/...`) แล้วบอก path ใน prompt หรือ pipe เข้า stdin ของ Codex (`echo data | cyolo1 exec "..."` จะได้ข้อมูลเป็นบล็อก `<stdin>`) ส่วน Claude และ agy มี `--json-schema` สำหรับบังคับรูปแบบผลลัพธ์ และ Codex มี `--output-schema`

---

## 6. จุดที่พลาดง่าย

1. **จบปกติแต่งานล้ม (agy):** สั่ง `generate_image` แล้ว image model ตอบ 503 แต่ผลยังเป็น `status:"SUCCESS"` และ exit 0 ข้อความ error อยู่ใน `.response` เท่านั้น จึง**ต้องตรวจว่าไฟล์ที่คาดไว้มีอยู่จริง**
2. **Claude `subtype:"success"` ตอนล้ม:** เกิดทั้งกรณีไม่ได้ล็อกอินและกรณีชื่อรุ่นผิด ซึ่ง `.subtype` ยังเป็น `"success"` ต้องดู `.is_error` (กรณีนี้ exit code เป็น 1 ถูกต้อง)
3. **agy ที่ไม่ได้ล็อกอินจะค้าง:** โปรแกรมเปิด OAuth flow พิมพ์ลิงก์ออกมา แล้วรอ "paste the authorization code" นาน 60 วินาที ส่วน `/usage` ค้างจนชน `timeout` (exit 124) จึงควรใส่ `< /dev/null` และ `timeout` เสมอ และตรวจด้วย `gyoloN models` ก่อน (ได้ exit 1 ทันที)
4. **Codex ที่ไม่ได้ล็อกอินจะ retry นาน:** โปรแกรม retry ด้วย 401 ประมาณ 10 ครั้ง (WebSocket 5 ครั้ง แล้ว HTTPS อีก 5 ครั้ง) ราว 30 วินาที ระหว่างนั้นมี event `{"type":"error","message":"Reconnecting..."}` หลายบรรทัด ซึ่ง**ยังไม่ใช่จุดจบ** ต้องรอ `turn.failed` หรือดู exit code
5. **Codex อ่าน stdin:** ถ้า stdin ไม่ใช่ tty จะขึ้น "Reading additional input from stdin..." และอาจรอ ควรใส่ `< /dev/null` เสมอ (ยกเว้นตั้งใจ pipe ข้อมูลเข้า)
6. **slash command ที่ไม่รู้จักใน agy ถูกส่งให้โมเดล:** `gyolo1 -p /status` ทำให้โมเดลตอบเป็นข้อความยาวและเสียโควตา คำสั่งที่ใช้ได้จริงคือ `/usage` (หรือ `/quota`)
7. **`HOME` ของ agy ถูกเปลี่ยน:** `~` ในงานของ gyolo ชี้ไปที่ `/root/ai-accounts/.Gemini/gyoloN` ไม่ใช่ `/root` จึงควรใช้ path แบบ absolute เสมอ
8. **คำตอบ agy มี `\n` ต่อท้าย** และ Codex อาจมีช่องว่าง ต้อง trim ก่อนนำไปใช้ต่อ
9. **โทเค็น input ของ Claude ดูน้อยผิดปกติ** (`input_tokens: 2`) เพราะส่วนใหญ่อยู่ใน `cache_read_input_tokens` และ `cache_creation_input_tokens` ต้องรวมทุกช่อง ส่วน agy นับ prompt ระบบราว 9,200 tokens และ Codex ราว 19,000 tokens ต่อการเรียก 1 ครั้ง แม้จะถามแค่ "OK"
10. **Codex แบบ `--json` ไม่มี event ของการสร้างภาพ** เห็นแค่ `command_execution` (cp) และข้อความ ต้องดูไฟล์ใน `generated_images/` แทน
11. **`--ephemeral` ของ Codex** ทำให้ไม่มีไฟล์ rollout จึงอ่าน `rate_limits` ไม่ได้
12. **บัญชีที่อาจซ้ำกัน:** ดูหมายเหตุท้ายข้อ 3
13. **ชื่อรุ่นผิด:** ทั้ง 3 ชุด exit 1 แต่ Claude ยังได้ `subtype:"success"` (ดูข้อ 2) ส่วน agy พิมพ์รายการรุ่นที่ใช้ได้ออกมาให้
14. **`auth status` ของ Claude มีอีเมลและชื่อองค์กร** ต้องกรองก่อนแสดงหรือบันทึก
15. **ทุก wrapper ให้สิทธิ์เต็ม:** ถ้าต้องการให้ agent แค่ตอบ ไม่ไปแก้ไฟล์หรือรันคำสั่ง ควรเขียนใน prompt ให้ชัด (เช่น "Do not run any commands")
16. Codex ในโฟลเดอร์ที่ไม่ใช่ git repo: เวอร์ชันนี้ร่วมกับ bypass flag รันได้แม้ไม่ใส่ `--skip-git-repo-check` แต่ควรใส่ไว้เพื่อความแน่นอน

---

## สรุป

### ตาราง 1: เปรียบเทียบ 3 ชุด

| หัวข้อ | Claude Code (yolo) | Codex CLI (cyolo) | Antigravity CLI (gyolo) |
|---|---|---|---|
| สั่ง 1 ครั้ง | `yoloN -p "..." --output-format json` | `cyoloN exec --skip-git-repo-check --json -o out.txt "..."` | `gyoloN -p "..." --output-format json` |
| คำตอบอยู่ที่ | `.result` | ไฟล์ `-o` หรือ `item.completed` ที่เป็น `agent_message.text` | `.response` (trim `\n`) |
| โทเค็นอยู่ที่ | `.usage.*` (รวม cache) และ `.total_cost_usd` | event `turn.completed.usage` (หรือ stderr "tokens used") | `.usage.total_tokens` และอื่น ๆ |
| ตัวบอกว่าสำเร็จ | `.is_error == false` (ห้ามดู subtype) และ exit 0 | ไม่มี `turn.failed` และ exit 0 | `.status == "SUCCESS"` และ exit 0 **และตรวจผลงานจริง** |
| เลือกรุ่น | `--model haiku/sonnet/opus/fable` | `-m gpt-6-luna / gpt-6.2-sol / gpt-6.2-astra …` | `--model gemini-3.8-flash-low …` (ระดับอยู่ในชื่อ) |
| ระดับการคิด | `--effort low…max` | `-c model_reasoning_effort=low…ultra` | อยู่ท้ายชื่อรุ่น หรือ `--effort low…max` |
| งานง่าย / กลาง / ยาก | haiku / sonnet / opus หรือ fable | luna / 6.2-sol / 6.2-astra | 3.8-flash-low / flash-high หรือ 4-carbon / 4-neon-high (หรือ claude-opus-5-5) |
| ดูรายการรุ่น | ดูจาก `--help` (alias) | `cyoloN debug models` | `gyoloN models` |
| ตรวจการล็อกอิน | `auth status` (`loggedIn`) | `login status` | `models` (exit 0/1) |
| ดูโควตา | `-p /usage` (ฟรี) หรือ `rate_limit_event` | `rate_limits` ในไฟล์ rollout ของ session | `-p /usage` (% ที่เหลือ) |
| สร้างภาพ | ไม่ได้ | ได้ (ทดสอบสำเร็จ) | มีเครื่องมือ แต่ตอนทดสอบล้ม (503) |
| อ่านภาพ | ได้ (path ใน prompt) | ได้ (`-i` หรือ path) | ได้ (path ใน prompt) |
| รับข้อมูลเข้า | อาร์กิวเมนต์หรือ stdin, `--json-schema` | อาร์กิวเมนต์และ stdin (`<stdin>`), `--output-schema` | อาร์กิวเมนต์, `--json-schema` |
| อาการตอนไม่ได้ล็อกอิน | ล้มทันที (exit 1, `is_error`) | retry 401 ราว 30 วินาที แล้ว exit 1 | ค้างรอ OAuth 60 วินาที แล้ว exit 1 |
| จุดพลาดหลัก | `subtype` เป็น "success" แม้ล้ม | ต้องใส่ `< /dev/null` และ error ระหว่าง retry ยังไม่ใช่จุดจบ | SUCCESS แม้เครื่องมือล้ม, `HOME` ถูกเปลี่ยน, slash command ไม่รู้จักถูกส่งให้โมเดล |

### ตาราง 2: ความพร้อมของบัญชี

| บัญชี | พร้อมใช้หรือไม่ |
|---|---|
| yolo1 | ✅ พร้อม (สัปดาห์ใช้ไป 25%) |
| yolo2 | ✅ พร้อม (สัปดาห์ใช้ไป 0%) |
| yolo3 | ✅ พร้อม (สัปดาห์ใช้ไป 47%, Fable 76%) |
| yolo4 | ❌ ยังไม่ได้ล็อกอิน |
| yolo5 | ❌ ยังไม่ได้ล็อกอิน |
| cyolo1 | ✅ พร้อม (ใช้ไป 10% ต่อ 7 วัน) |
| cyolo2 | ✅ พร้อม (โควตาเหมือน cyolo1 ทุกค่า อาจเป็นบัญชีเดียวกัน) |
| cyolo3 | ❌ ยังไม่ได้ล็อกอิน |
| cyolo4 | ❌ ยังไม่ได้ล็อกอิน |
| cyolo5 | ❌ ยังไม่ได้ล็อกอิน |
| gyolo1 | ✅ พร้อม (Gemini สัปดาห์เหลือ 92%) |
| gyolo2 | ✅ พร้อม (โควตาเหมือน gyolo1 ทุกค่า อาจเป็นบัญชีเดียวกัน) |
| gyolo3 | ❌ ยังไม่ได้ล็อกอิน |
| gyolo4 | ❌ ยังไม่ได้ล็อกอิน |
| gyolo5 | ❌ ยังไม่ได้ล็อกอิน |
