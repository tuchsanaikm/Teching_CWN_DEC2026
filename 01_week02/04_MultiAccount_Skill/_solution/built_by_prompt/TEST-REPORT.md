# TEST-REPORT — สกิล yolo, cyolo, gyolo, agent-team

ทดสอบเมื่อ 2026-11-23 ถึง 2026-11-24 ใน container `multi-account` โดยเรียกจาก Windows host ผ่าน docker เป็นหลัก

**สภาพแวดล้อม:**
- Claude Code 2.1.330, Codex CLI 0.171.0, Antigravity CLI 1.5.15
- ใช้รุ่นเล็กทั้งหมด (haiku/low, gpt-6-luna/low, gemini-3.8-flash-low) ยกเว้นตอนสั่งให้ agy สร้างภาพ ซึ่งใช้ gemini-4-carbon-low

**ขอบเขต:**
- ไม่ได้ลบ หยุด หรือสร้าง container ไม่ได้เปิดไฟล์ credential และไม่ได้ล็อกอินแทน
- ผลที่มี "(จำลอง)" ใช้กลไก `--simulate` และ `simulate` ของ agent-team: ไม่เรียก CLI จริงและไม่เสียโทเค็น

**บัญชีที่พร้อม** (`check` ล่าสุด 2026-11-24 00:40):
- yolo1–3, cyolo1–2, gyolo1–2 พร้อมใช้
- yolo4–5, cyolo3–5, gyolo3–5 ยังไม่ล็อกอิน
- cyolo1 กับ cyolo2 เป็นการล็อกอินเดียวกัน (fingerprint เท่ากัน)

---

## สรุปรวม

| สกิล | ผ่าน | ไม่ผ่าน / ข้อจำกัด |
|---|---|---|
| yolo | 10/10 | – |
| cyolo | 10/10 | – |
| gyolo | 9/10 | **สร้างภาพไม่ได้**: image model ของ Google ตอบ 503 (no capacity) ทุกครั้งที่ลอง สกิลรายงานเป็นงานล้มได้ถูกต้อง |
| agent-team | 27/27 (ของเดิม 11 + ของใหม่ 16) | ข้อสังเกตอยู่ในหัวข้อ "ข้อจำกัด" ท้ายรายงาน |

---

## 1. สกิล yolo (Claude Code)

| ความสามารถ | ผล | หลักฐาน |
|---|---|---|
| ตรวจความพร้อม (เรียกจริงทุกบัญชี) | ✅ | `check` ได้ yolo1–3 พร้อม (ผ่าน test call ด้วย claude-haiku-5-5) และ yolo4–5 `not_logged_in` |
| แยกสถานะ "ล็อกอินแล้วแต่ใช้ไม่ได้" | ✅ | (จำลองด้วยการชี้ HTTPS ไป port ปิดบนเครื่อง) yolo1–3 เป็น `logged_in_unusable: timeout` และ exit 3 |
| โควตา + เวลาของข้อมูล | ✅ | `quota` ผ่าน `/usage` ไม่เสียโทเค็น เช่น yolo3: session 0%, week 47%, Fable 76% พร้อม `data_time` ส่วนบัญชีที่ไม่ล็อกอินแสดง `no data` |
| รุ่น + ตารางความยาก | ✅ | `models` ได้ alias 10 ตัวจาก `/model` และตาราง 1→haiku/low … 6→fable/xhigh ซึ่งทุกตัว available |
| สั่งงาน เลือกบัญชีอัตโนมัติ | ✅ | `run -d 1 "…12+30…"` เลือก yolo2 (ใช้ไป 4%) แล้วตอบ `42` |
| สั่งงาน ระบุบัญชี / ไฟล์ / prompt ที่ขึ้นต้นด้วย `/` | ✅ | `-a 3 -f p.txt` ตอบ `142` และ prompt "/tmp is…" ตอบ `SLASH-OK` |
| อ่านภาพ | ✅ | `-i star.png` ตอบ "A bright yellow five-pointed star … dark blue background." |
| สร้างภาพ | ✅ ปฏิเสธถูกต้อง | `image` ตอบว่า "cannot generate images. Use the cyolo skill" และ exit 2 |
| บัญชีที่ระบุแต่ไม่ล็อกอิน / รุ่นผิด | ✅ | `-a 4` จบใน 1 วินาทีด้วย exit 3 และ `-m no-such-model` ได้ `bad_model` exit 1 |
| สมุดบันทึกกลาง + allowlist + audit | ✅ | `stats --all` ได้ 147 ครั้ง ไม่มีข้อความ prompt หรืออีเมล ส่วน `AI_SKILL_ACCOUNTS=yolo3` ทำให้ `-a yolo1` ถูกปฏิเสธ และ audit มีแค่ yolo3 |

## 2. สกิล cyolo (Codex CLI)

| ความสามารถ | ผล | หลักฐาน |
|---|---|---|
| ตรวจความพร้อม | ✅ | cyolo1–2 พร้อม (gpt-6-luna), cyolo3–5 `not_logged_in` และ cyolo2 มี "(same login as cyolo1)" |
| ล็อกอินแล้วแต่ใช้ไม่ได้ | ✅ | (จำลองด้วยการปิดเน็ต) cyolo1–2 เป็น `logged_in_unusable: cli_error: workspace routing discovery failed` |
| โควตา + เวลาของข้อมูล | ✅ | ผ่าน app-server `account/rateLimits/read` ไม่เสียโทเค็น: 7d ใช้ไป 10%, reset 2026-11-28, credits 62500 และระบุ "identical numbers to cyolo1" |
| รุ่น + ตารางความยาก | ✅ | `debug models` ได้ 10 รุ่น และตาราง 1→gpt-6-luna/low … 6→gpt-6.2-astra/xhigh ทุกตัว available |
| สั่งงาน อัตโนมัติ / ระบุบัญชี / JSON | ✅ | ตอบ `42` (cyolo1) และ `-a cyolo2 --json` ได้ `JSON-OK` พร้อม tokens in 19668 / out 7 |
| สร้างภาพเป็นไฟล์ | ✅ | `image -o star.png` ได้ PNG ขนาด 1.1 MB บนเครื่อง เมื่อเปิดดูเป็นดาวเหลืองบนพื้นน้ำเงินจริง และ agent-team สร้างภาพวงกลมสำเร็จ 4 ครั้ง |
| อ่านภาพ | ✅ | `-i star.png` ตอบ "A large yellow five-pointed star sits on a solid dark blue background." |
| บัญชีที่ระบุแต่ไม่ล็อกอิน | ✅ | `-a 3` จบใน 1 วินาทีด้วย exit 3 (ถ้าไม่ตรวจก่อน CLI จะ retry 401 ราว 30 วินาที) |
| รุ่นผิด | ✅ | `bad_model` exit 1 |
| allowlist + audit | ✅ | `AI_SKILL_ACCOUNTS=yolo3,cyolo2` ทำให้ audit มีแค่ `cyolo2 login` และ `cyolo2 app-server` |

## 3. สกิล gyolo (Antigravity CLI)

| ความสามารถ | ผล | หลักฐาน |
|---|---|---|
| ตรวจความพร้อม | ✅ | gyolo1–2 พร้อม (gemini-3.8-flash-low) และ gyolo3–5 `not_logged_in` ใน 0.8 วินาที ไม่ค้างรอ OAuth |
| ล็อกอินแล้วแต่ใช้ไม่ได้ | ✅ | (จำลองด้วยการปิดเน็ต) gyolo1–2 เป็น `logged_in_unusable` ภายหลังเพิ่มผลตรวจล็อกอินต่อท้ายเพื่อบอกสาเหตุจริง |
| โควตา + เวลาของข้อมูล | ✅ | ผ่าน `/usage` ไม่เสียโทเค็น: gemini 7d ใช้ไป 9%, 5h ใช้ไป 24% (แปลงมาจากค่า Remaining) และ claude+gpt 0% |
| รุ่น + ตารางความยาก | ✅ | `models` ได้ 27 รุ่น และตาราง 1→gemini-3.8-flash-low … 6→gemini-4-neon-xhigh ทุกตัว available |
| สั่งงาน อัตโนมัติ / stdin | ✅ | ตอบ `42` และ `echo … \| gyolo.py run -a 2` ตอบ `PIPE-OK` |
| อ่านภาพ | ✅ | ตอบ "five-pointed yellow star centered against a solid dark blue background" |
| **สร้างภาพ** | ❌ (ข้อจำกัดภายนอก) | ลอง 4 ครั้ง ได้ `HTTP 503 No capacity for gemini-3.1-flash-image` ทุกครั้ง สกิลตรวจจับได้ว่าล้มจริงแม้ agy ตอบ `SUCCESS` และ exit 1 ด้วย `capacity` |
| ตรวจภาพปลอม | ✅ | เมื่อป้อนบันทึกเก่าที่ agy วาด PNG ด้วย Python กลับเข้าไป ได้ `REJECT fake_image` |
| บัญชีที่ระบุแต่ไม่ล็อกอิน | ✅ | `-a 3` จบใน 2 วินาทีด้วย exit 3 ไม่ค้าง 60 วินาที |
| allowlist | ✅ | `AI_SKILL_ACCOUNTS=yolo3,cyolo2` ได้ "allows no gyoloN account here; nothing was called" exit 3 |

---

## 4. สกิล agent-team

ผลของแต่ละ run อยู่ใน container ที่ `/root/team-runs/<run-id>/` (มี `state.json`, `report.md`, `handover.md`, `audit.log`, `prompts/`, `out/`)

### 4.1 ความสามารถเดิม (regression หลังเพิ่มความสามารถใหม่)

| ความสามารถ | ผล | หลักฐาน (run-id) |
|---|---|---|
| ส่งต่อข้ามค่าย (ค่าสั้นส่งในข้อความ) | ✅ | `t-relay-20261124-002441`: yolo2 `42` → cyolo1 `142` → gyolo1 `426` |
| ข้อมูลยาวส่งเป็นไฟล์ | ✅ | `t-relay-…`: prompt ของ count เป็น "[… is in the file …/out/nums.txt]" และตอบ `COUNT=60 LAST=60` |
| ทำพร้อมกันแล้วรวมผล | ✅ | `t-relay-…`: fruit_a/b/c ทำพร้อมกันบน 3 ค่าย แล้วรวมเป็น `apple + banana + cherry` |
| ตรวจงานกันเอง | ✅ | `t-review-20261124-003506`: รอบ 1 FAIL รอบ 2 PASS ได้ `passed (2 รอบ)` |
| กระดานความรู้กลาง | ✅ | `t-board-20261124-000635`: NOTE ของ cyolo1 ไปอยู่บนกระดาน แล้ว gyolo1 ตอบ `ORCHID-7` ใน 5 วินาทีและ 9k tokens โดยไม่อ้าง `{{scout}}` |
| ภาพที่ผ่านการตรวจ | ✅ | `t-image-20261124-003545`: cyolo1 สร้าง → gyolo1 FAIL → สร้างใหม่ → PASS → หัวหน้า yolo2 ตัดสิน `ACCEPT` และพิกเซลกลางภาพของ run ก่อนหน้าคือ (250,1,1) แล้วเป็น (0,0,253) |
| เลือกคนตามงาน | ✅ | `t-route-20261124-003704`: code-review → cyolo1, doc → yolo2, image-review → gyolo2, text → yolo2 |
| ใช้เฉพาะบัญชีที่อนุญาต | ✅ | `t-route-…` ที่ใช้ `--accounts yolo2,cyolo1,gyolo2` ได้ audit = cyolo1, gyolo2, yolo2 ส่วน `bad-allow.toml` ได้ `PLAN ERROR - nothing was called` exit 2 |
| ตารางสรุป + รันต่อเฉพาะงานที่ล้ม | ✅ | `t-fail-20261124-003730`: bad เป็น failed (`bad_model` ไม่ถูกย้ายบัญชี) และ after เป็น blocked จากนั้น `resume --plan` รันแค่ bad กับ after ส่วน ok1 ถูกเรียก 1 ครั้งเท่าเดิม |
| ไม่รันผลของ AI เป็นคำสั่ง | ✅ | `t-safety-20261124-003818`: ข้อความ `touch /tmp/ai-skills/PWNED && echo hacked` ถูกส่งต่อเป็นข้อมูล ไฟล์ไม่ถูกสร้าง และในโค้ดไม่มี `shell=True`, `os.system` หรือ `eval` |
| ไม่ทำซ้ำเมื่อล้มหลังเสียโทเค็น | ✅ | `t-safety-…`: agy สร้างภาพล้มหลังใช้ไป 29k tokens ถูกบันทึกเป็น failed 1 ครั้ง ไม่ย้ายและไม่ลองซ้ำ |

### 4.2 ความสามารถใหม่

| ความสามารถ | ผล | หลักฐาน (run-id) |
|---|---|---|
| 1a. แข่งกัน (compete) | ✅ | `t-contest-20261124-002659`: yolo2 `Chao Phraya Coffee` · cyolo1 `Bangkok Brew` · gyolo1 `Siam Roast Coffee` และหัวหน้า yolo2 เลือก **B (cyolo1)** พร้อมเหตุผล ("most memorable … names the city directly") |
| 1b. ถกกัน (debate) | ✅ | `t-contest-…` task float: 3 ค่ายตอบ แล้วเห็นคำตอบกันและกันอีก 1 รอบ จากนั้นผู้ตัดสินสังเคราะห์ว่า "No … `0.30000000000000004` …" |
| 2. หยุดรับงานเมื่อโควตาเกิน 80% (จำลอง) | ✅ | `t-quota-20261124-002748` ใช้ `quota:yolo1=95@1`: yolo1 ถูกหยุดรับงานใหม่ตอนเริ่ม call แรก งาน q3 ที่กำลังทำ**ทำต่อจนจบ** และ **q5 ในคิวถูกย้ายจาก yolo1 ไป yolo2** |
| 2. หยุดรับงานเมื่อเกินงบ (จริง) | ✅ | `t-quota-…` ใช้ `budgets = {yolo3 = 30000}`: หลัง call แรกของ yolo3 (32,235 tokens) ได้ `pause: tokens 32235 >= budget 30000` |
| 3a. ล้มกลางคัน → ย้ายไปค่ายเดียวกัน | ✅ | `t-failover-20261124-003948` ใช้ `fail:gyolo1@2`: gyolo1 ทำรอบ 1 แล้วล้มในรอบ 2 รอบ 2 จึงย้ายไป **gyolo2** แล้ว PASS |
| 3b. ไม่มีบัญชีค่ายเดียวกันเหลือ → ข้ามค่าย | ✅ | `t-failover-…`: cross ย้ายจาก cyolo1 ไป cyolo2 (ค่ายเดียวกัน) แล้วจาก cyolo2 ไป **gyolo2** (คนละค่าย) และตอบ `CROSS-OK` |
| 3c. งานที่ระบุบัญชีเองไม่ถูกย้ายเงียบ ๆ | ✅ | `t-failover-…`: pinned (`who="yolo3"`) กลายเป็น **held** และรายงานว่า "the task pins this account, so it was not moved" exit 1 จากนั้น `resume --move-held` จึงย้ายไป yolo2 พร้อมบันทึก |
| 4a. เปลี่ยนหัวหน้าเมื่อโควตาใกล้หมด | ✅ | `t-leader-20261124-002945` ใช้ `quota:yolo2=95@1`: หัวหน้าเปลี่ยนจาก yolo2 เป็น **yolo1** โดย prompt ระบุว่า "You took over from yolo2" หัวหน้าใหม่อ่าน state แล้วตอบว่า `l1,l2` เสร็จแล้ว และสรุปท้ายระบุการเปลี่ยนหัวหน้า |
| 4b. เปลี่ยนหัวหน้าเมื่อหัวหน้าล้ม | ✅ | `t-approve-20261124-003242`: yolo2 ล้ม (จำลอง) จึงได้ `leader: yolo2 → yolo1 (yolo2 is down)` |
| 4c. โปรเซสหัวหน้าตาย → `takeover` | ✅ | `t-takeover-20261124-003036` ใช้ `leader-crash@2`: โปรเซสจบด้วย exit 9 จากนั้น `takeover` ตั้ง yolo1 เป็นหัวหน้าแล้วทำ s3–s4 และสรุปจนจบ แต่ละงานถูกเรียก 1 ครั้ง ไม่มีงานทำซ้ำ |
| 4d. takeover ขณะมีงานค้างกลางทาง | ✅ | `t-takeover2-20261124-003136` ใช้ `leader-crash@1` ตอน p2 กำลังทำอยู่: takeover บันทึก `interrupted: p2` แล้วเริ่ม p2 ใหม่ จากนั้นทำ p3 ส่วน p1 ไม่ถูกทำซ้ำ |
| 5a. รออนุมัติ | ✅ | `t-approve-…`: a1 เสร็จ แล้วได้ `PAUSED: waiting for your approval of a2` exit 4 โดยไม่มี step ของ a2 จนกว่าจะสั่ง `approve` ซึ่งทำต่อจนจบ (a3 = `published draft`) |
| 5b. ไม่อนุมัติ | ✅ | `t-reject-20261124-003428`: a2 เป็น `rejected_by_user` และ a3 เป็น `blocked`, steps มีแค่ `['a1']` (รอบแรก `…003333` พบว่า a3 ค้างเป็น pending จึงแก้แล้วทดสอบใหม่) |
| 6. จำลองเหตุการณ์ | ✅ | ใช้ครบ 3 แบบ: `quota:…@N` (2, 4a), `fail:…@N` (3, 4b) และ `leader-crash@N` (4c, 4d) ทั้งตอนเริ่ม run และสั่ง `simulate` ระหว่าง run หยุดรอ (5a) ทุกแบบไม่เรียก CLI และไม่เสียโทเค็น |
| 7. ภาพรวมทีม | ✅ | `team t-quota-…` และ `team t-failover-…` แสดงตาราง `บัญชี \| บทบาท \| งานที่ทำอยู่ \| โทเค็นที่ใช้ \| โควตา \| สถานะ` (เช่น "yolo1 \| ผู้ทำ \| - \| 33510 \| 95% (จำลอง) \| หยุดรับงานใหม่") พร้อมประวัติ leader, pause, move, down และ held ทั้งหมดอยู่ใน `report.md` ด้วย ระหว่างที่ run หยุดรออนุมัติก็แสดงคิวได้ ("yolo2 \| หัวหน้า (ปัจจุบัน), ผู้ทำ \| - · คิว: a2") |
| ของเดิมใช้ได้เหมือนเดิม | ✅ | ทุกแถวในหัวข้อ 4.1 รันซ้ำหลังเพิ่มความสามารถใหม่ ส่วนแผนตัวอย่างผ่าน `--dry-run` |

### 4.3 บั๊กที่พบและแก้ระหว่างทดสอบ
1. NOTE pattern เดิมจะจับประโยคธรรมดาอย่าง "Note that…" ด้วย จึงแก้ให้ต้องมี `NOTE:` เท่านั้น
2. agent เปิดไฟล์ prompt ของงานอื่นใน run folder ทำให้การทดสอบกระดานรอบแรกไม่เป็นธรรม จึงเพิ่มคำสั่งให้ใช้เฉพาะข้อมูลที่ได้รับ แล้วทดสอบกระดานใหม่จนผ่าน
3. scheduler ตรวจงานที่กำลังรันด้วย future object แทน task id จึงแก้ให้ใช้ task id
4. `resume --move-held` ยังหยุดงานซ้ำเมื่อบัญชีที่ระบุไว้ล้มอีก จึงแก้ให้ย้ายตามที่อนุญาต
5. `handover.md` ไม่ทันสมัย (หัวหน้าใหม่จับได้เอง) จึงแก้ให้เขียนใหม่ทุกครั้งที่งานจบ
6. หลัง `reject` งานที่ต้องรองานนั้นค้างเป็น pending จึงแก้ให้กลายเป็น blocked
7. `resume --plan` ยอมรับแผนที่ไม่ตรงกับ run จึงแก้ให้ปฏิเสธเมื่อขาด task id ของ run (เจอเพราะผมเผลอ resume `t-failover-20261124-002822` ด้วยแผนผิด ทำให้ run นั้นมีงานปนกัน หลักฐานข้อ 3 จึงใช้ run ใหม่ `…003948`)

### 4.4 ข้อจำกัดและสิ่งที่ยังไม่ได้ทดสอบ
- **gyolo สร้างภาพไม่ได้** ในช่วงทดสอบ (503 จากฝั่ง Google) ทีมจึงใช้ cyolo เป็นผู้สร้างภาพเป็นค่าเริ่มต้น
- **คำสั่งใน prompt ไม่ได้รับประกันว่า agent จะทำตาม:** ใน `t-relay-20261124-002441` งาน ask ของ gyolo ยังค้นไฟล์เองนาน 73 วินาทีและใช้ 180k tokens เพราะแผนเก่าไม่มี NOTE จริงให้อ่าน (ใน `t-board` ที่มี NOTE จริงทำงานถูก) เพราะ wrapper ให้ agent มีสิทธิ์เต็มใน container
- **งานที่ค้างตอนหัวหน้าตายจะเริ่มใหม่ทั้งงาน:** โทเค็นที่ใช้ไปใน call ที่ถูก kill จะเสียไป ส่วนรอบที่ทำเสร็จแล้วของงาน review/image ที่ค้างอยู่ก็ไม่ถูกเก็บ
- **ยังไม่ได้ทดสอบ:**
  - การรออนุมัติแบบรอค้าง (`approval_wait` > 0)
  - `takeover --force`
  - debate ที่มี `rounds` > 1
  - การย้ายงานในคิวเมื่อเกินงบ: ทดสอบแค่การหยุดรับงาน เพราะตอนนั้นไม่มีงานในคิวเหลือ ส่วนการย้ายงานในคิวทดสอบแล้วในกรณีโควตา
  - แผนตัวอย่างใน `examples/`: ทดสอบแค่ dry run เพราะใช้ความยาก 2 และสร้างภาพ
- **เกณฑ์โควตาของทีมใช้หน้าต่างที่เกี่ยวข้องเท่านั้น:** Claude ไม่นับหน้าต่าง Fable และ agy ไม่นับกลุ่ม claude+gpt จึงอาจต่างจาก % สูงสุดที่ `quota` ของสกิลย่อยแสดง
- **cyolo1 กับ cyolo2 เป็นบัญชีเดียวกัน** การย้ายงานระหว่างสองบัญชีนี้จึงไม่ช่วยเรื่องโควตาจริง
