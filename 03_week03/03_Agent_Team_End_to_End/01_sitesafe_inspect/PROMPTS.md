# รวมพรอมต์พร้อมคัดลอก (10 ขั้นตอน) · SiteSafe Inspect

พรอมต์ทุกข้อในหน้านี้ตรงตัวอักษรกับ `README.md` และ `SiteSafe_Inspect_Slides.html` ครอบคลุมทั้ง 4 ระยะ ตั้งแต่สัมภาษณ์ลูกค้า ออกแบบสถาปัตยกรรม **Next.js 15 + PostgreSQL + NGINX `least_conn` + 8× FastAPI Micro-batching บน `1 โหนด × 2× RTX 4090`** ไปจนถึงการทดสอบ Playwright 27 ข้อพร้อมไฟล์ `.gif` ทุกข้อ Bug Hunt และลบเครื่อง GPU

- บัญชี Agent Team ที่ใช้ในบทนี้: `yolo2`, `yolo3`, `cyolo1`, `gyolo1`
- เครื่อง GPU ที่ใช้: `1 โหนด × 2× RTX 4090` (Vast.ai · ติดป้ายชื่อ `e2e-sitesafe-nginx`)

---

## ระยะ A · วิเคราะห์โจทย์และออกแบบระบบ

### พรอมต์ที่ 1 · แปลงบทสัมภาษณ์เป็น User Stories

> [!IMPORTANT]
> **พรอมต์ที่ 1 · สร้าง `docs/USER-STORIES.md` จากบทสัมภาษณ์**
> ```text
> อ่าน INTERVIEW.md ของบริษัท ไทยมั่นคงก่อสร้าง จำกัด ให้ครบทุกข้อ
> แล้วสร้างไฟล์ docs/USER-STORIES.md ที่ประกอบด้วย:
> 1. บทบาทผู้ใช้ทั้ง 3 กลุ่ม (หัวหน้างานไซต์, ผู้จัดการความปลอดภัย, ผู้บริหาร) และขอบเขตสิทธิ์ของแต่ละกลุ่ม
> 2. User Stories ครบทุกเส้นทางงานหลัก: อัปโหลดรูปหน้างานเป็นชุด, ตรวจจับคนไม่ใส่หมวก (H) และไม่ใส่เสื้อสะท้อนแสง (V) พร้อมวาดกรอบ, กรองดูรูปที่มีปัญหา, แก้ผลตรวจพร้อมบันทึกเหตุผลแบบลบไม่ได้, ดูรายงานประจำวันรายไซต์, และดูแดชบอร์ดสถานะเครื่อง GPU
> 3. Acceptance Criteria แบบ Given / When / Then ที่วัดผลได้จริงในทุก Story
> 4. แยกรายการที่อยู่นอกขอบเขตรุ่นแรกไว้ชัดเจน (เช่น แจ้งเตือน LINE และวิดีโอสด)
> ```

### พรอมต์ที่ 2 · กำหนด Requirements และ Test Data เชิงขอบเขต

> [!IMPORTANT]
> **พรอมต์ที่ 2 · สร้าง `docs/REQUIREMENTS.md` และ `docs/TEST-DATA.md`**
> ```text
> จาก docs/USER-STORIES.md ให้สร้างเอกสารคู่กัน 2 ไฟล์:
> 1. docs/REQUIREMENTS.md:
>    - Functional Requirements (FR-01 ถึง FR-22) ครบทั้งการอัปโหลด ผลตรวจ การแก้ผล รายงาน และสิทธิ์ 3 บทบาท
>    - Business Rules 7 ข้อที่กระชับ ชัดเจน ไม่มีข้อยกเว้นซับซ้อน (BR-01: H ≥ 1 ไม่ผ่าน, BR-02: V ≥ 2 ไม่ผ่าน, BR-03: V = 1 เตือน, BR-04: อัตราผ่าน < 90% แสดงสีแดง, BR-05: ไฟล์ ≤ 15 MB เฉพาะ JPG/PNG แท้, BR-06: อัปโหลดครั้งละ ≤ 50 รูป, BR-07: รายงานประจำวันพร้อมแสดงผลที่ 18:00 น.)
>    - Non-Functional Requirements (NFR-01 ถึง NFR-08): Recall/Precision ≥ 0.80, ความเร็วช่วงปกติ p95 ≤ 30 วินาที, รองรับช่วงเร่งด่วน 150 รูปพร้อมกัน, รูปห้ามหาย, ป้องกันข้อมูลและ API Key, สิทธิ์ตรวจฝั่งเซิร์ฟเวอร์, และประวัติแก้ผลแบบ Append-only
> 2. docs/TEST-DATA.md: ตารางกรณีขอบเขต (Boundary Values) และผลที่คาดหวังคำนวณล่วงหน้าครบทั้ง 7 กติกา (R-1..R-8, F-1..F-10, P-1..P-9, บัญชีทดสอบ 5 บัญชีใน 3 ไซต์)
> ```

### พรอมต์ที่ 3 · ออกแบบสถาปัตยกรรมความเร็วสูง (`NGINX least_conn` + `2× RTX 4090`)

> [!IMPORTANT]
> **พรอมต์ที่ 3 · สร้าง `docs/DESIGN.md` สถาปัตยกรรม 2 ฝั่ง (Direct Concurrent HTTP → NGINX + 8× FastAPI)**
> ```text
> ออกแบบระบบใน docs/DESIGN.md เพื่อตอบโจทย์ทั้งความถูกต้องของกติกาและความเร็วช่วงเร่งด่วน 150 รูปพร้อมกัน โดยแบ่งเป็น 2 ฝั่ง:
> 1. ฝั่งเว็บ (Docker Compose ภายในเครื่อง · พอร์ต 3410):
>    - Next.js 15 (App Router) + Tailwind CSS + PostgreSQL 16 (7 ตาราง + คอลัมน์บันทึก GPU Telemetry) + volume photos เก็บรูปต้นฉบับก่อนตอบรับ 201
>    - รวม Business Rule BR-01..BR-07 และสวิตช์ BUG_MODE ไว้ในไฟล์เดียว (web/lib/rules.ts)
>    - Async HTTP Dispatcher ส่งรูปขนาน concurrency=16 ผ่าน HTTP POST /v1/detect พร้อม Authorization: Bearer ไปยังฝั่ง GPU โดยตรง (ไม่ต้องใช้โบรกเกอร์ข้อความภายนอก)
>    - หน้าเว็บ 8 หน้า รวมหน้า /telemetry แสดงสถานะเครื่อง GPU, Header X-Upstream, batch_size และ model_ms
>    - รองรับโหมดจำลอง AI_MODE=mock (mock-gateway พอร์ต 3411) สำหรับทดสอบกรณีขอบเขตและ Bug Hunt
> 2. ฝั่ง AI (1 โหนด × 2× RTX 4090 บน Vast.ai):
>    - NGINX Load Balancer พอร์ต 8080 ใช้ least_conn + Passive Failover ON (proxy_next_upstream error timeout non_idempotent, max_fails=1 fail_timeout=10s) + client_max_body_size 20m + แนบ Header X-Upstream
>    - 8× FastAPI Micro-batching (4 Processes ต่อ GPU, พอร์ต 8101–8104 และ 8201–8204, MAX_BATCH=32, MAX_WAIT_MS=5) โหลดโมเดล YOLO11s (best.pt)
> ระบุ ER Diagram, แผนภาพสถาปัตยกรรม, ลำดับคำขอ End-to-End, API Contract, และตาราง data-testid สำหรับ Playwright ให้ครบ
> ```

---

## ระยะ B · วางแผนการทำงานแบบ DAG

### พรอมต์ที่ 4 · แตกงาน 10 บล็อกและวางแผนเวลาด้วย KC-QUEST

> [!IMPORTANT]
> **พรอมต์ที่ 4 · สร้างแผนงาน `plan/PLAN.md`, `plan/dag.png` และ `plan/gantt-plan.png`**
> ```text
> อ่าน docs/REQUIREMENTS.md, docs/DESIGN.md และ docs/TEST-DATA.md แล้ววางแผนสร้างระบบ SiteSafe Inspect แบบขนานด้วยบัญชี yolo2, yolo3, cyolo1 (พร้อมกันสูงสุด 3 งาน):
> 1. แตกงานเป็น 10 บล็อก (B01 โครงโปรเจกต์ + Docker Compose, B02 ฐานข้อมูล 7 ตาราง + Seed, B03 กติกา BR-01..BR-07 + RBAC + 14 API, B04 Async HTTP Dispatcher + Mock, B05 NGINX least_conn + Failover ON, B06 8× FastAPI Micro-batch YOLO11s, B07 โค้ด Training & Evaluation, B08 หน้าเว็บ 8 หน้า + /telemetry, B09 โลโก้, B10 รวมระบบและทดสอบเบื้องต้น)
> 2. กำหนดให้บล็อก B03 เป็นงานแบบ review (ทำและตรวจคนละบัญชี) โดยตั้งขอบเขตการตรวจให้ชัดเจน: ผ่านทันทีเมื่อ unit test และกรณีขอบเขตทั้งหมดใน docs/TEST-DATA.md ผ่านครบโดยไม่ขยายขอบเขตเกิน Requirement เพื่อให้จบภายใน ≤ 3 รอบ
> 3. สร้าง plan/PLAN.md ระบุสายวิกฤต ตารางแจกงาน และวาดแผนภาพ plan/dag.png กับ plan/gantt-plan.png
> ```

---

## ระยะ C · สร้างระบบ เตรียมโมเดล และเปิดใช้งานบน `2× RTX 4090`

### พรอมต์ที่ 5 · สั่งทีม Agent Team สร้างโค้ดครบทั้ง 10 บล็อก

> [!IMPORTANT]
> **พรอมต์ที่ 5 · สร้างซอร์สโค้ดฝั่งเว็บและฝั่ง AI ครบทั้งระบบ**
> ```text
> ดำเนินการสร้างระบบ SiteSafe Inspect ตามแผน plan/PLAN.md ครบทั้ง 10 บล็อก โดยใช้บัญชี yolo2, yolo3, cyolo1:
> - ฝั่งเว็บ (code_reference/app/web/): Next.js 15 + Tailwind CSS + PostgreSQL 16 + lib/rules.ts (BR-01..BR-07 + BUG_MODE ไฟล์เดียว) + RBAC 3 บทบาทตรวจฝั่งเซิร์ฟเวอร์ + Async HTTP Dispatcher ส่งขนาน 16 รูป + หน้า /telemetry + mock-gateway
> - ฝั่ง AI (code_reference/app/ai/serving/): server.py (FastAPI + YOLO11s Dynamic Micro-batching), nginx.conf (least_conn + Failover ON + Bearer auth check + X-Upstream), cluster.sh, loadgen.py และ ai/train/evaluate.py
> - รัน npm run typecheck, npm run build, vitest (web) และ pytest (ai/train) ให้ผ่านครบทุกข้อ พร้อมสรุปเวลาและโทเคนจริงใน plan/REPORT.md และ plan/gantt-actual.png
> ```

### พรอมต์ที่ 6 · เช่าเครื่อง `1 โหนด × 2× RTX 4090` และเตรียมโมเดล YOLO11s

> [!IMPORTANT]
> **พรอมต์ที่ 6 · เช่าเครื่อง `2× RTX 4090` บน Vast.ai และวัดความแม่นยำโมเดล YOLO11s**
> ```text
> ค้นหาและเช่าเครื่อง 1 โหนด × 2× RTX 4090 บน Vast.ai ที่ผ่านการยืนยัน (verified=true, inet_down >= 1200 Mbps, เลือกค่าดาวน์โหลดต่ำสุด, เปิดพอร์ต 8080, ติดป้าย label e2e-sitesafe-nginx):
> 1. ตรวจสอบสเปกเครื่องจริง (2× RTX 4090, vCPU, RAM, สถานะ RUNNING) และอัปโหลดโค้ดฝั่ง AI กับโมเดล YOLO11s (best.pt)
> 2. ตรวจความแม่นยำโมเดลด้วย ai/train/evaluate.py เทียบก่อน-หลังเทรน และเลือก Confidence Threshold บน Validation Set ให้ได้ Recall ≥ 0.80 และ Precision ≥ 0.80 สำหรับทั้ง NO_HARDHAT และ NO_VEST
> 3. บันทึกผลประเมินลง results/model/metrics_before.json, results/model/metrics_after.json และ results/model/threshold.json
> ```

### พรอมต์ที่ 7 · วัดสมรรถนะ 4 รูปแบบและเปิดระบบจริง Design #4 เชื่อมกับหน้าเว็บ

> [!IMPORTANT]
> **พรอมต์ที่ 7 · วัดความจุ 4 รูปแบบ, ทดสอบ GPU ช้า & Failover และเปิดระบบจริง**
> ```text
> บนเครื่อง 1 โหนด × 2× RTX 4090 ให้รันชุดทดสอบความจุและเสถียรภาพด้วย cluster.sh และ loadgen.py (เกณฑ์ p95 ≤ 500 ms):
> 1. วัดความจุเปรียบเทียบ 4 รูปแบบ:
>    - Design #1: 1 GPU · 1 Process · Single
>    - Design #2: 1 GPU · 1 Process · Micro-batch
>    - Design #3: 1 GPU · 4 Processes · Micro-batch
>    - Design #4: 2× RTX 4090 · 8 Processes (4/GPU) · Micro-batch · NGINX least_conn
> 2. ทดสอบสถานการณ์ GPU 1 ช้าลง 3 เท่า (slow-factor 3) เปรียบเทียบ Round Robin กับ least_conn
> 3. ทดสอบสถานการณ์ปิด GPU 1 กะทันหันกลางโหลด 80 ผู้ใช้ เปรียบเทียบ Failover OFF กับ Failover ON
> 4. บันทึกผล JSON ลง results/lb/ สร้างกราฟ 4 แผ่นใน images/lab/ แล้วเปิด Design #4 (--gpus 2 --per-gpu 4 --mode micro --lb lc --failover on) เชื่อมต่อกับเว็บ Docker Compose (sitesafe-nginx พอร์ต 3410) และเปิด sitesafe-mock (พอร์ต 3411) คู่กัน
> ```

---

## ระยะ D · ทดสอบอัตโนมัติ Playwright 27 ข้อ, Bug Hunt และส่งมอบงาน

### พรอมต์ที่ 8 · รันชุดทดสอบ Playwright 24 ข้อพร้อมบันทึกวิดีโอ `.gif` ทุกข้อ

> [!IMPORTANT]
> **พรอมต์ที่ 8 · ทดสอบ E2E ครบ 24 Core Test Cases + บันทึก `.gif` รายข้อ + เดโมหน้าเว็บ**
> ```text
> ออกแบบและรันชุดทดสอบ Playwright (test/e2e/tests/) ครบ 24 Core Test Cases (TC-01 ถึง TC-24) ครอบคลุมทุก Requirement และ Business Rule:
> - กลุ่ม A (TC-01..06): ตรวจขนาดไฟล์ 14.9/15.0/15.1 MB (BR-05), ชนิดไฟล์จริงด้วย Magic Bytes (FR-02), จำนวน 0/50/51 รูป (BR-06), การผูกไซต์อัตโนมัติ (FR-04)
> - กลุ่ม B (TC-07..12): Decision Table 8 กรณี R-1..R-8 (BR-01..03), วาดกรอบ SVG, ตรวจภาพหน้างานจริง 6 รูปด้วย YOLO11s บน 2× RTX 4090, กรองหน้ารูปมีปัญหาและรูปทั้งหมด
> - กลุ่ม C (TC-13..17): ปิดเบราว์เซอร์กลางทาง 10 รูปไม่หาย, ไฟล์ใหญ่ 15 MB ตรวจผ่าน NGINX, ไฟล์เสียไม่ขวางภาพปกติ, ชุด 20 รูปพร้อมกันเช็ก p95 ≤ 30 วิ และกระจายข้ามทั้ง gpu0 และ gpu1, และ /api/health
> - กลุ่ม D (TC-18..22): เส้นแบ่งสีแดง 89.67% vs 90.00% vs 90.33% (BR-04), ขอบเขตพิเศษวันที่ 2, ป้ายเวลา 17:59 vs 18:00 น. (BR-07), แก้ผลพร้อมเหตุผลและ Audit Trail (FR-13..16)
> - กลุ่ม E (TC-23..24): แยกสิทธิ์ RBAC 3 บทบาท (401/403/404), แดชบอร์ด /telemetry ONLINE และตรวจไม่รั่ว API Key
> ทุก Test Case ต้องบันทึกวิดีโอหลักฐาน .gif ของตัวเองที่ images/tests/TC-XX.gif พร้อมบันทึกวิดีโอเดโมหน้าเว็บเริ่มตั้งแต่หน้า /login และสร้าง test/TEST-REPORT.md กับ test/index.html
> ```

### พรอมต์ที่ 9 · ทดสอบ Bug Hunt (`BUG_MODE=1`) พิสูจน์ว่าชุดทดสอบจับบักได้จริง

> [!IMPORTANT]
> **พรอมต์ที่ 9 · รัน Bug Hunt (`TC-25`–`TC-27`) ในโหมด `BUG_MODE=1`**
> ```text
> เปิดโหมด BUG_MODE=1 บนสแต็ก sitesafe-mock (พอร์ต 3411) แล้วรัน test/e2e/tests/06_bughunt.spec.ts (TC-25 ถึง TC-27) เพื่อพิสูจน์ว่าชุดทดสอบจับความผิดพลาดของ Business Rule ที่ซ่อนไว้ได้ครบ 3/3:
> - TC-25 (BR-02): ยืนยันตรวจพบว่า h0_v2.jpg ตอบ WARN แทน FAIL
> - TC-26 (BR-04): ยืนยันตรวจพบว่า SITE-B ที่ได้ 90.00% พอดีถูกไฮไลต์สีแดง พร้อมถ่ายภาพหน้าจอ images/lab/web-bug-9000.png
> - TC-27 (BR-06): ยืนยันตรวจพบว่าส่งชุด 51 รูปได้รับ 201 แทน 422
> บันทึกไฟล์ .gif หลักฐานทั้ง 3 ข้อ (images/tests/TC-25.gif ถึง TC-27.gif) บันทึกผลลง test/BUG-HUNT.md แล้วคืนค่า BUG_MODE=0 ทันที
> ```

### พรอมต์ที่ 10 · ลบเครื่อง GPU บน Vast.ai และสรุปเอกสารส่งมอบ

> [!IMPORTANT]
> **พรอมต์ที่ 10 · ปิดและลบเครื่อง GPU ทันที + ออกเอกสารส่งมอบ `DELIVERY.md`**
> ```text
> หลังจบการทดสอบทั้งหมดให้ดำเนินการปิดทรัพยากรและสรุปงานส่งมอบทันที:
> 1. ลบเครื่อง GPU ที่มี label e2e-sitesafe-nginx บน Vast.ai ด้วย vastai destroy instance <INSTANCE_ID> -y และตรวจสอบด้วย vastai show instances ว่าเหลือ 0 เครื่อง
> 2. ปิดคอนเทนเนอร์ทดสอบในเครื่อง (sitesafe-nginx และ sitesafe-mock) ด้วย docker compose down -v และลบไฟล์ชั่วคราวที่ไม่จำเป็น
> 3. ออกรายงานคำตัดสินส่งมอบใน DELIVERY.md สรุปผลความแม่นยำโมเดล ความจุบน 2× RTX 4090 ผลทดสอบ Playwright 24/24 + Bug Hunt 3/3 และข้อสังเกตโปร่งใสเรื่องขนาด Test Set
> ```
