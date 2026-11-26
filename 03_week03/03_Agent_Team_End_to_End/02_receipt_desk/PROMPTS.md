# พรอมต์ทั้งหมด · หัวข้อที่ 2 ReceiptDesk (15 ขั้น · `1 โหนด × 2× RTX 4090` · NGINX + 2× vLLM)

คัดลอกพรอมต์แต่ละขั้นไปวางใน Claude Code ที่เปิดอยู่ที่โฟลเดอร์ `02_receipt_desk` · ทุกพรอมต์ตรงตัวอักษรกับ [README.md](README.md) และ [ReceiptDesk_Slides.html](ReceiptDesk_Slides.html)

---

## ระยะ A · จากคำพูดเป็น Requirement

### ขั้นที่ 1 · User Story จากบันทึกการสัมภาษณ์

```text
จากบันทึกการสัมภาษณ์ลูกค้าใน ./INTERVIEW.md เขียน User Story ไว้ที่ ./docs/USER-STORIES.md
1. เขียนรูปแบบ "ในฐานะ… ฉันต้องการ… เพื่อ…" ให้ครบทุกบทบาทที่ลูกค้าพูดถึง ทุกข้อมีรหัส US-01… ระดับ Must / Should / Could และเกณฑ์ยอมรับที่ตรวจได้
2. ทุกข้อต้องอ้างคำพูดในบันทึกที่เป็นที่มา ห้ามเพิ่มความต้องการที่ลูกค้าไม่ได้พูด
3. รวบรวมจุดที่ลูกค้าพูดขัดกันเอง และคำถามที่ต้องถามลูกค้าเพิ่ม เป็น 2 ตารางท้ายไฟล์
4. แยกสิ่งที่ลูกค้าบอกว่ายังไม่ทำในรุ่นแรกไว้ในหัวข้อ "นอกขอบเขต"
(ยังไม่ออกแบบระบบ ยังไม่เขียนโค้ด)
สรุปเป็นตารางภาษาไทย: จำนวน User Story แยกตามระดับ · จำนวนจุดที่ขัดกัน · จำนวนคำถาม
```

### ขั้นที่ 2 · Requirement และ Business Rule ที่เรียบง่ายชัดเจน

```text
จาก User Story ใน ./docs/USER-STORIES.md เขียน Requirement ไว้ที่ ./docs/REQUIREMENTS.md
1. Functional Requirement (FR-01…) ทุกข้ออ้างรหัส User Story
2. Business Rule (BR-01…) ให้เรียบง่าย ชัดเจน และตรวจได้ด้วยตัวเลขเส้นแบ่ง (ต่ำกว่า / เท่ากับ / สูงกว่า) ครอบคลุม: ขนาดชุดและชนิด/ขนาดไฟล์ · ธงความมั่นใจต่ำกว่า 0.90 · ธงผลต่างรายการเกิน 1.00 บาทพร้อมคำนวณใหม่ทันทีเมื่อแก้ยอด · ยอดยืนยันตั้งแต่ 0.01 บาท · ลองส่งอ่านไม่เกิน 3 ครั้งแล้วพักให้คนพิมพ์เอง · ชุดเร่งด่วนไม่เกิน 10 ใบและ 5 งานต่อวัน · เพดานใบค้าง 400 ใบตอบ HTTP 429 พร้อมนาทีลองใหม่ · งานค้างเกิน 120 นาที · การนับเดือนตั้งแต่วันที่ 1 ถึงสิ้นเดือน
3. Non-functional Requirement (NFR-01…) ครอบคลุม: เกณฑ์ของโมเดล (M1–M4) · SLO ของงานปกติ งานเร่งด่วน และผู้ช่วยบัญชีแบบสตรีมสด · ความจุช่วงสิ้นเดือน · ข้อมูลใบเสร็จไม่หาย · ความเป็นส่วนตัวแยกตามร้าน · ความคุ้มของการใช้ GPU 2 ใบ
4. จุดที่ลูกค้าพูดขัดกัน ให้เลือกทางที่เสี่ยงน้อยที่สุดแล้วบันทึกเป็น "ข้อสมมติ" พร้อมเหตุผล
(ยังไม่เขียนโค้ด)
สรุปเป็นตารางภาษาไทย: จำนวน FR · BR · NFR · ข้อสมมติ และเกณฑ์ของโมเดลกับ SLO ที่ใช้
```

### ขั้นที่ 3 · System Design (`NGINX least_conn` + `2× vLLM`) และข้อมูลทดสอบ

```text
จาก Requirement ใน ./docs/REQUIREMENTS.md ออกแบบระบบไว้ที่ ./docs/DESIGN.md และข้อมูลทดสอบไว้ที่ ./docs/TEST-DATA.md
ระบบมี 2 ฝั่งที่เชื่อมต่อกันโดยตรงผ่าน HTTP/SSE (ไม่ใช้บริการตัวกลางภายนอก):
- ฝั่งเว็บเครื่องสำนักงาน: Next.js 16 + Tailwind CSS v4 + PostgreSQL 16 + Async Dispatcher รันด้วย docker compose (พอร์ต 3420 เชื่อมต่อสด และพอร์ต 3421 โหมดจำลอง)
- ฝั่ง AI บนเครื่องเช่า 1 โหนด × 2× RTX 4090: NGINX 1.27 (least_conn, proxy_buffering off, ตรวจ Bearer API key, แนบ header X-Replica, Passive Failover max_fails=1 fail_timeout=30s) กระจายโหลดไปยัง vLLM 2 Replicas (1 Replica ต่อ 1 GPU · Data Parallelism 2×1 · Continuous Batching --max-num-seqs 256 · โมเดล Qwen3-VL-2B-Instruct + LoRA) รองรับทั้ง Vision OCR อ่านใบเสร็จ และ Live SSE Streaming Accounting Copilot
1. แผนภาพ Mermaid 4 ภาพ: Architecture · ER Diagram (11 ตาราง) · ลำดับการทำงานตั้งแต่ส่งชุดจนยืนยัน · วงจรสถานะ 5 สถานะใน PostgreSQL
2. API Contract ระหว่างเว็บกับ NGINX + vLLM (Vision OCR, SSE Streaming Copilot, Bearer API key, X-Replica)
3. การจัดการลำดับงานเร่งด่วน 4:1, เพดานกันระบบล้น 400 ใบ (HTTP 429) และสถานะ unreadable เมื่ออ่านไม่สำเร็จครบ 3 ครั้งใน PostgreSQL
4. เว็บต้องมี /api/health ทางรีเซ็ตข้อมูลทดสอบ และ data-testid ทุกปุ่มและช่องกรอก
5. เว็บต้องมีโหมด BUG_MODE=1 ที่ทำให้ Business Rule ผิด 3 ข้อ เก็บเฉลยไว้ที่ ./docs/BUGS-SECRET.md ที่เดียว
6. ข้อมูลทดสอบ: ผู้ใช้ 4 บทบาท ลูกค้า 2 ร้าน และกรณีขอบของทุก Business Rule พร้อมผลที่คาดหวัง
(ยังไม่เขียนโค้ด)
สรุปเป็นตารางภาษาไทย: จำนวนตาราง · จำนวน API · จำนวนแถวข้อมูลทดสอบ · คำถามที่การออกแบบยังตอบไม่ได้
```

---

## ระยะ B · วางแผนงานให้ทีม AI

### ขั้นที่ 4 · แตกงาน 14 บล็อก วาด DAG และ Gantt

```text
ทำงานใน container multi-account ด้วยสกิล dag-planner
โจทย์: สร้างระบบ ReceiptDesk ตาม Requirement และ System Design ในโฟลเดอร์ ./docs
1. แตกงานเป็น 14 บล็อก ชื่อแผน receiptdesk
2. ครอบคลุม: โครงโปรเจกต์ docker compose · ฐานข้อมูล PostgreSQL 11 ตาราง · โมดูลกติกา Business Rule · สิทธิ์ 4 บทบาทและ API 35 เส้น · Async Dispatcher (โหมด vllm/mock) · กติกาชุดเร่งด่วน 4:1 และเพดาน 400 ใบ · SSE Copilot Proxy และ Telemetry · คอนฟิก NGINX least_conn + สคริปต์ 2× vLLM Data Parallelism · โค้ดเทรน LoRA (1 และ 2 GPU) + Evaluation · หน้าเว็บตามบทบาท · หน้า Split-Pane Review · โลโก้ · รวมระบบและทดสอบเบื้องต้น
3. ใช้ให้ครบ 6 สกิล: บล็อกกติกา Business Rule ใช้ review (ผู้ทำกับผู้ตรวจคนละ CLI · กำหนดขอบเขตตรวจชัดให้ผ่านเมื่อกรณีขอบใน ./docs ผ่านครบและไม่ขัด Requirement เพื่อให้จบภายในไม่เกิน 3 รอบ) · บล็อกออกแบบกติกางานเร่งด่วนใช้ debate · บล็อกหน้า Split-Pane Review ใช้ best_of · บล็อกอื่นใช้ yolo, cyolo หรือ image
4. ให้เวลาทำงานต่อบล็อก: ขนาด S 15 นาที · M 30 นาที · L 45 นาที
5. วางแผนด้วยบัญชี 4 บัญชีที่มีสิทธิ์จริง (yolo2, yolo3, cyolo1, gyolo1) จำนวน agent พร้อมกันไม่เกิน 4
6. คัดลอกไฟล์บล็อก ภาพ DAG ภาพ Gantt และไฟล์แผน มาไว้ที่ ./plan
(วางแผนเท่านั้น ห้ามรันจริง ห้ามแสดงข้อมูลล็อกอินของบัญชี)
สรุปเป็นตารางภาษาไทย: บล็อก · สกิล · ขนาด · รอบล็อกใด · บัญชี · เริ่ม–จบ (นาที) แล้วบอก Critical Path และเวลารวมของแผน
```

### ขั้นที่ 5 · What-if ก่อนตัดสินใจรัน

```text
ทำงานใน container multi-account ด้วยสกิล dag-planner
ใช้ไฟล์บล็อกของแผน receiptdesk ที่มีอยู่แล้ว ห้ามแก้บล็อก
1. วางแผนเพิ่มอีก 2 แบบ: ชื่อแผน receiptdesk-2 ใช้ agent พร้อมกันไม่เกิน 2 · ชื่อแผน receiptdesk-nocodex ใช้เฉพาะ Claude (ไม่มี Codex)
2. เทียบ 3 แผน: เวลารวม · Critical Path · บัญชีที่งานหนักที่สุด · บล็อกที่วางไม่ได้หรือถูกลดคุณภาพ
3. แนะนำว่าควรรันแผนใด พร้อมเหตุผล 2–3 บรรทัด แล้วเก็บภาพ Gantt ของแผน receiptdesk-2 ไว้ที่ ./plan/whatif
(วางแผนเท่านั้น ห้ามรันจริง ห้ามแสดงข้อมูลล็อกอินของบัญชี)
สรุปเป็นตารางภาษาไทย: แผน · agent พร้อมกัน · บัญชี · เวลารวม (นาที) · Critical Path · ข้อจำกัด
```

---

## ระยะ C · สร้างระบบ เทรนโมเดล และเปิดบริการบน `1 โหนด × 2× RTX 4090`

### ขั้นที่ 6 · Agent Team สร้างระบบตามแผน (ผ่านครบในขอบเขตที่กำหนด)

```text
ทำงานใน container multi-account ด้วยสกิล agent-team และ dag-planner
ใช้แผน receiptdesk ที่มีอยู่แล้ว ห้ามวางแผนใหม่ ผมอนุมัติให้รันจริงด้วยบัญชี yolo2, yolo3, cyolo1, gyolo1
1. ส่งเอกสารในโฟลเดอร์ ./docs ให้ทีมเปิดดูได้ แล้วรันแผนจริงตามบัญชีที่วางไว้
2. สำหรับบล็อก review (โมดูล Business Rule): ใช้เกณฑ์ผ่านที่ชัดเจนคือผ่านกรณีทดสอบทุกข้อใน ./docs/TEST-DATA.md และไม่ขัด ./docs/REQUIREMENTS.md ข้อสังเกตนอกขอบเขตให้จดไว้ที่ ./plan/FOLLOW-UPS.md เพื่อให้การตรวจจบภายในไม่เกิน 3 รอบ
3. รันจบแล้วออกรายงานแผนเทียบของจริง คัดลอกโค้ดที่ทีมสร้างมาไว้ที่ ./code_reference/app และคัดลอกรายงานกับภาพเทียบแผนมาไว้ที่ ./plan
4. บล็อกที่ล้มให้รายงานตามจริง ห้ามเขียนโค้ดแทนทีม
(ห้ามแสดงข้อมูลล็อกอินของบัญชี ไม่ต้อง commit)
สรุปเป็นตารางภาษาไทย: บล็อก · นาทีตามแผน · นาทีจริง · โทเคน · สถานะ แล้วบอกเวลารวมและโทเคนรวม
```

### ขั้นที่ 7 · เช่าเครื่อง `1 โหนด × 2× RTX 4090` และเตรียม Dataset CORD-v2

```text
ทำงานใน container multi-account โฟลเดอร์ /workspace/e2e_receipt_nginx ด้วยสกิล vastai · ใช้ key จากไฟล์ .env
1. เช่าเครื่องที่มี NVIDIA GeForce RTX 4090 จำนวน 2 ใบในเครื่องเดียว (verified=true, inet_down >= 1,200 Mbps, ค่าดาวน์โหลดต่ำที่สุด, disk >= 80 GB, เปิดพอร์ต 8080) ติดป้าย e2e-receipt-nginx
2. ดาวน์โหลดโมเดล Qwen/Qwen3-VL-2B-Instruct และ Dataset naver-clova-ix/cord-v2 จาก Hugging Face ลงเครื่องที่เช่า แล้วนับจำนวนใบเสร็จของ Training / Validation / Test Set
3. ทำภาพตัวอย่างจาก Training Set 6 ใบ: รูปใบเสร็จคู่กับ JSON เฉลยของใบนั้น เก็บกลับมาที่ ./results/dataset_samples.jpg
4. อธิบายโครงสร้าง JSON 5 ช่องของใบเสร็จ 1 ใบ และระบุช่องที่ใช้ตัดสินตาม Requirement
(ห้ามแสดงค่า key ห้ามแตะเครื่องป้ายอื่น)
สรุปเป็นตารางภาษาไทย: รุ่นและจำนวน GPU · ความเร็วเน็ตขาเข้า/ออก · จำนวนใบเสร็จแต่ละชุด · ช่องที่ใช้ตัดสินตาม Requirement แล้วบอกว่าเครื่องยังเปิดอยู่
```

### ขั้นที่ 8 · เทรน LoRA 1 GPU เทียบ 2 GPU (Data Parallelism) และตัดสินด้วย Acceptance Gate

```text
ทำงานใน container multi-account ด้วยสกิล vastai · เครื่องที่ใช้คือเครื่องป้าย e2e-receipt-nginx
1. นำโค้ด Training และ Evaluation ใน ./code_reference/app/ai/train ไปเทรน Qwen/Qwen3-VL-2B-Instruct ด้วย LoRA rank 16 ให้อ่านใบเสร็จเป็น JSON ใช้ Training Set 400 ใบ 1 Epoch seed 0
2. เทรน 2 รอบด้วยค่าเดิมทุกอย่าง: รอบแรก GPU 1 ใบ รอบที่สอง GPU 2 ใบ (Data Parallelism) วัดเวลาต่อ Epoch แล้วคำนวณ Speedup และ Scaling Efficiency
3. วัดผลบน Test Set 100 ใบ ก่อนเทรนเทียบหลังเทรน (โมเดลรอบ 2 GPU) ตามตัวชี้วัด M1–M4 ใน Requirement แล้วตัดสินว่าผ่าน Acceptance Gate และคุ้มค่าการเพิ่ม GPU หรือไม่
4. เก็บ LoRA ที่ดีที่สุดไว้ใน ./results/model/lora_g2 และเก็บผลวัดกับกราฟกลับมาที่ ./results/model
(ห้ามแสดงค่า key ห้ามแตะเครื่องป้ายอื่น)
สรุปเป็นตาราง 2 ตารางภาษาไทย: (ก) จำนวน GPU · เวลาต่อ Epoch · Speedup · Efficiency (ข) ตัวชี้วัด · ก่อนเทรน · หลังเทรน · เกณฑ์ · ผ่านหรือไม่
```

### ขั้นที่ 9 · เปิดบริการด้วย NGINX `least_conn` + `2× vLLM` และเชื่อมเว็บ ReceiptDesk

```text
ทำงานใน container multi-account โฟลเดอร์ /workspace/e2e_receipt_nginx ด้วยสกิล vastai · เครื่องที่ใช้คือเครื่องป้าย e2e-receipt-nginx (1 โหนด × 2× RTX 4090)
1. บนเครื่อง 2× RTX 4090: รวมน้ำหนัก LoRA จาก ./results/model/lora_g2 เข้ากับ Qwen/Qwen3-VL-2B-Instruct ด้วย merge_and_unload() แล้วเปิด vLLM 2 Replicas (Data Parallelism 2×1: GPU 0 พอร์ต 8001, GPU 1 พอร์ต 8002) ด้วย Continuous Batching (--max-num-seqs 256, --gpu-memory-utilization 0.90, --max-model-len 4096) หลัง NGINX 1.27 (พอร์ต 8080, least_conn, proxy_buffering off, ตรวจ Bearer API key, แนบ header X-Replica, Passive Failover max_fails=1 fail_timeout=30s)
2. เปิดเว็บ ReceiptDesk (Next.js 16 + Tailwind CSS v4 + PostgreSQL 16) ด้วย docker compose -p receiptdesk-nginx ที่พอร์ต 3420 เชื่อมตรงไปยังเครื่อง 2× RTX 4090 และเปิดชุดจำลอง docker compose -p receiptdesk-mock ที่พอร์ต 3421
3. ตรวจเส้นทางครบทุกหน้า: /api/health, ส่งใบเสร็จ CORD-v2 จริง, Split-Pane Review (BR-05 คำนวณธงสด), Live SSE Streaming Accounting Copilot (/copilot) และ /telemetry
(ห้ามแสดงค่า key ห้ามแตะเครื่องป้ายอื่น)
สรุปเป็นตารางภาษาไทย: ส่วนของระบบ · ที่อยู่ · สถานะ · ผลทดสอบ
```

### ขั้นที่ 10 · วัดความจุคลัสเตอร์ `2× RTX 4090` (Continuous Batching · Data Parallelism · Failover · OCR Batch)

```text
ทำงานใน container multi-account ด้วยสกิล vastai · เครื่องที่ใช้คือเครื่องป้าย e2e-receipt-nginx (1 โหนด × 2× RTX 4090)
รันชุดทดสอบสมรรถนะจริงกับคลัสเตอร์ Qwen3-VL-2B-Instruct + LoRA ที่เปิดอยู่ (20 วินาทีต่อระดับ + warmup 5 วินาที)
1. 1-user baseline: วัดความเร็วและ TTFT ของผู้ใช้ 1 คนบน 1× RTX 4090 เพื่อคำนวณเกณฑ์ Fast SLO (≥ 50% ของ 1 ผู้ใช้)
2. Sequential Baseline (1 GPU, --max-num-seqs 1): หาจำนวนผู้ใช้สูงสุดตาม Standard SLO (TTFT p95 ≤ 2.0 วินาที, speed p5 ≥ 15 tok/s, error < 1%)
3. Continuous Batching (1 GPU, --max-num-seqs 256): หาจำนวนผู้ใช้สูงสุดทั้ง Standard SLO และ Fast SLO พร้อม Peak Throughput
4. Data Parallelism 2×1 + NGINX least_conn (2 GPUs, --max-num-seqs 256): หาจำนวนผู้ใช้สูงสุด, Peak Throughput และคำนวณ Scaling Efficiency % เทียบ 1 GPU
5. Concurrency Cap Trade-off: เทียบ --max-num-seqs 32 กับ 256 ภายใต้โหลดสูง (N=640)
6. Short/Long Mix: ยิงคำถามบัญชีสั้นผสมยาว (25% คำตอบยาว 600 โทเคน) ตรวจความสมดุลระหว่าง gpu0 กับ gpu1
7. Mid-Stream Failover: ปิด Replica บน gpu1 (:8002) กลางสตรีมขณะมีโหลด 160 ผู้ใช้ ตรวจว่า NGINX สลับไป gpu0 โดยไม่มี error หลังฟื้นตัว
8. Real Receipt OCR Batch: ยิงรูปใบเสร็จ CORD-v2 จริง เทียบกำลังผลิต (ใบเสร็จต่อนาที) ระหว่าง 1 GPU กับ 2 GPUs Data Parallelism
9. ดึงไฟล์ผล JSON กลับมาที่ ./results/lb และสร้างกราฟภาษาไทย 4 รูปไว้ที่ ./results/images และ ./images/lab
(ห้ามแสดงค่า key ห้ามแตะเครื่องป้ายอื่น)
สรุปเป็นตารางภาษาไทยเทียบทุกการทดสอบ พร้อม Scaling Efficiency % และ Speedup ของการอ่านใบเสร็จ
```

---

## ระยะ D · พิสูจน์ว่าระบบทำตาม Requirement

### ขั้นที่ 11 · Test Charter และ Exploration พร้อมกัน

```text
เว็บ ReceiptDesk เปิดอยู่ที่ http://localhost:3420 ใช้ playwright-cli สำรวจ (ห้ามเปิดโค้ดใน ./code_reference/app และห้ามเปิดไฟล์ BUGS-SECRET)
1. ดู Requirement ในโฟลเดอร์ ./docs และเดินดูเว็บ 1 รอบ แล้วเขียน Test Charter 6 ข้อไว้ที่ ./test/CHARTERS.md รูปแบบ "สำรวจ… ด้วย… เพื่อหา…" ทุก Business Rule ต้องมี Charter รับผิดชอบ
2. รีเซ็ตข้อมูลทดสอบ 1 ครั้ง แล้วสั่ง subagent 6 ตัวในข้อความเดียว ตัวละ 1 Charter ตัวละ 1 session และบัญชีทดสอบของตัวเอง
3. แต่ละตัวเขียนผลที่คาดหวังจาก Requirement ก่อนลอง แล้วบันทึกผลจริง ✅ ⚠️ ❌ พร้อมภาพหน้าจอ
4. รวมผลไว้ที่ ./test/EXPLORATION.md: ฟีเจอร์ที่พบ · กฎที่ยืนยันแล้ว · จุดที่เว็บไม่ตรง Requirement · ตารางความเสี่ยง P1 / P2 / P3
สรุปเป็นตารางภาษาไทย: Charter · จำนวนกฎที่ลอง · ✅ · ⚠️ · ❌
```

### ขั้นที่ 12 · Test Plan และการตรวจไขว้ต่างบัญชี

```text
จาก Requirement ข้อมูลทดสอบ และผล Exploration ในโฟลเดอร์ ./docs กับ ./test เขียน Test Plan ไว้ที่ ./test/TEST-PLAN.md
1. โครง 8 หัวข้อ: ภาพรวม · ขอบเขต · เทคนิค · ระดับ · Test Case · Entry/Exit Criteria · ข้อมูลทดสอบ · คุณภาพของแผน
2. Test Case ครอบคลุมครบทุกกลุ่ม: การรับชุดไฟล์ · ธงความมั่นใจและยอดไม่ตรง · Split-Pane Review และประวัติแก้ไข · ชุดเร่งด่วนและเพดาน 400 ใบ · ใบอ่านไม่ได้ 3 ครั้ง · รายงานรายเดือนและงานค้าง · สิทธิ์ 4 บทบาทและพอร์ทัลลูกค้า · Live 2× RTX 4090 (OCR + SSE Copilot + Telemetry)
3. ผลที่คาดหวังต้องมาจาก Requirement ไม่ใช่จากที่เห็นบนเว็บ
4. แยก Test Case เส้นแบ่งแน่นอน (พอร์ต 3421 โหมดจำลอง) ออกจากชุดทดสอบสดกับโมเดลจริงบน 2× RTX 4090 (พอร์ต 3420)
5. ให้ผู้ตรวจต่างบัญชี (cyolo1) ตรวจแผน แล้วบันทึกผลตรวจไว้ที่ ./test/PLAN-REVIEW.md และแก้แผนตามข้อที่รุนแรงสูง
สรุปเป็นตารางภาษาไทย: กลุ่ม · จำนวน TC · P1 · ข้อที่ผู้ตรวจพบ · ข้อที่แก้แล้ว
```

### ขั้นที่ 13 · Playwright E2E 28 ข้อพร้อมบันทึก `.gif` รายข้อทุกข้อ และวิดีโอสาธิตเริ่มจาก `/login`

```text
เขียนและรันชุด Playwright E2E Test ใน ./test/e2e/run_e2e.py ครอบคลุมครบทุกกติกาและทุกบทบาท โดยบันทึกวิดีโอหลักฐาน .gif (1000×562 @ 8fps) แยกไฟล์ให้ครบทุก Test Case ที่ ./images/tests/TC-XX.gif
1. รันชุดกำหนดเส้นแบ่ง 22 ข้อ (TC-01..TC-22) กับเว็บโหมดจำลองที่พอร์ต 3421 และรันชุดสด 3 ข้อ (TC-23..TC-25) กับเว็บที่พอร์ต 3420 ซึ่งเชื่อมกับ 2× RTX 4090 จริง
2. บันทึกวิดีโอสาธิตหลักความยาว 6.5 วินาที (1200×675 @ 10fps) จำนวน 2 ไฟล์ไว้ที่ ./images/lab:
   - receiptdesk_review_flow.gif (เริ่มจากหน้า /login พิมพ์อีเมล-รหัสผ่าน → อัปโหลดใบเสร็จ CORD-v2 → Split-Pane OCR Review & ยืนยัน → รายงานรายเดือน)
   - receiptdesk_streaming_copilot.gif (Live SSE Streaming Copilot แสดง TTFT, tok/s, X-Replica + หน้าสุขภาพคลัสเตอร์ /telemetry)
3. สรุปผลเป็นตารางครบทุกข้อลงใน ./test/TEST-REPORT.md และสร้างหน้าเว็บดูหลักฐานแบบโต้ตอบที่ ./test/index.html พร้อมเก็บ JSON ใน ./test/evidence/
สรุปเป็นตารางภาษาไทย: กลุ่ม · พอร์ต · ผ่าน · ล้ม · จำนวนไฟล์ .gif
```

### ขั้นที่ 14 · Bug Hunt (`BUG_MODE=1`) พร้อม `.gif` และรายงานส่งมอบ

```text
เปิดเว็บชุดจำลองที่พอร์ต 3421 ใหม่ด้วย BUG_MODE=1 แล้วรันชุด Bug Hunt (TC-26..TC-28) พร้อมบันทึก .gif หลักฐานของแต่ละบั๊กไว้ที่ ./images/tests/ (ห้ามเปิดไฟล์ BUGS-SECRET จนกว่าจะเขียนรายงานบั๊กเสร็จ)
1. เทียบกับรอบปกติ: ข้อที่ล้มเพิ่มคือข้อใด แล้วสรุปเป็นบั๊กทีละตัวไว้ที่ ./test/BUG-HUNT.md พร้อมขั้นตอนทำซ้ำ ผลที่คาดหวัง ผลจริง และลิงก์ .gif หลักฐาน
2. เขียนรายงานบั๊กเสร็จแล้วจึงเปิดไฟล์ BUGS-SECRET เทียบว่าจับได้กี่ตัวจาก 3 ตัว
3. เขียนรายงานส่งมอบสำหรับลูกค้าไว้ที่ ./DELIVERY.md
4. ปิด BUG_MODE=0 กลับเป็นโหมดปกติ
สรุปเป็นตารางภาษาไทย: บั๊ก · Test Case ที่จับได้ · ความรุนแรง · หลักฐาน .gif
```

### ขั้นที่ 15 · ลบเครื่อง GPU (`e2e-receipt-nginx`) และปิดระบบ (ห้ามข้าม)

```text
ทำงานใน container multi-account โฟลเดอร์ /workspace/e2e_receipt_nginx ด้วยสกิล vastai
1. ตรวจว่าดึงผลวัด JSON และหลักฐานการทดสอบทั้งหมดกลับมาในโฟลเดอร์โปรเจกต์ครบแล้ว
2. ลบเครื่องป้าย e2e-receipt-nginx ทันทีหลังทดสอบและบันทึก GIF เสร็จ แล้วตรวจซ้ำด้วย vastai show instances ว่าไม่มีเครื่องป้าย e2e-receipt-nginx เหลืออยู่
3. หยุดเว็บและฐานข้อมูลบนเครื่องนี้ทั้ง 2 ชุด (receiptdesk-nginx และ receiptdesk-mock) และล้างค่า API key จริงออกจากไฟล์ .env
(ห้ามแตะเครื่องป้ายอื่น ห้ามแสดงค่า key)
สรุปเป็นตารางภาษาไทย: เครื่องที่ลบ · ระยะเวลาที่เปิดใช้งาน · สถานะหลังลบ
```
