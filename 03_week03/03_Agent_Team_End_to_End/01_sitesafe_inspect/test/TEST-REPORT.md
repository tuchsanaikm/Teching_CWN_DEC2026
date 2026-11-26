# รายงานผลการทดสอบระบบ (Test Report) · SiteSafe Inspect

- **วันที่ทดสอบจริง:** 2026-11-26 (เวลาประเทศไทย)
- **สถาปัตยกรรมฝั่งเว็บ:** Next.js 15 + Tailwind CSS + PostgreSQL 16 + Async HTTP Dispatcher (`concurrency=16`) บน Docker Compose (`sitesafe-nginx` พอร์ต `3410` และ `sitesafe-mock` พอร์ต `3411`)
- **สถาปัตยกรรมฝั่ง AI (Design #4):** `1 โหนด × 2× RTX 4090` (Illinois, US · 48 vCPU · 125.6 GB RAM · Instance `62729107` · ลบเครื่องหลังทดสอบแล้ว) รัน **NGINX `least_conn` + Failover ON** หน้า **8× FastAPI Micro-batching (`4 Processes/GPU`, `MAX_BATCH=32`, `5 ms`, YOLO11s `best.pt`)**
- **ตัวดูผลแบบโต้ตอบพร้อมวิดีโอทุกข้อ:** เปิด [`test/index.html`](index.html) ในเบราว์เซอร์เพื่อกรองและดู `.gif` ครบทั้ง 27 ข้อได้ทันที

## 1. สรุปภาพรวมการทดสอบ

| หมวดการทดสอบ | จำนวน Test Case | ผ่าน / จับบักได้ | ล้มเหลว | หลักฐาน `.gif` |
|---|---:|---:|---:|---:|
| Core Functional, GPU & Security (`TC-01`–`TC-24`) | 24 | **24/24 (100%)** | 0 | 24 ไฟล์ |
| Bug Hunt Verification (`BUG_MODE=1` · `TC-25`–`TC-27`) | 3 | **3/3 จับครบ (100%)** | 0 | 3 ไฟล์ |
| **รวมทั้งหมด** | **27** | **27/27 (100%)** | **0** | **27 ไฟล์** |

## 2. ตาราง Test Case ครบทั้ง 27 ข้อ (พร้อมลิงก์ `.gif` หลักฐานทุกข้อ)

| TC ID | ชื่อ Test Case | หมวด / กติกา | โหมด | ผลที่คาดหวัง | ผลจริง | สถานะ | หลักฐาน (`.gif`) |
|---|---|---|---|---|---|---|---|
| **TC-01** | รับไฟล์ขนาด 14.9 MB และ 15.0 MB พอดี | Upload & Validation · `BR-05` | Live GPU | HTTP 201 ทั้งสองไฟล์ | HTTP 201, 201 | ✅ ผ่าน | [`TC-01.gif`](../images/tests/TC-01.gif) (128 KB) |
| **TC-02** | ปฏิเสธไฟล์เกิน 15 MB (+1 B และ 15.1 MB) | Upload & Validation · `BR-05` | Live GPU | HTTP 413 ทั้งสองไฟล์พร้อมข้อความ 15 MB | HTTP 413, 413 | ✅ ผ่าน | [`TC-02.gif`](../images/tests/TC-02.gif) (104 KB) |
| **TC-03** | รับเฉพาะ JPG และ PNG แท้ (ตรวจ Magic Bytes) | Upload & Validation · `FR-02` | Live GPU | รับ 2/2 ไฟล์ผ่าน UI และเก็บลง Volume | รับครบ 2/2 (JPG + PNG) | ✅ ผ่าน | [`TC-03.gif`](../images/tests/TC-03.gif) (127 KB) |
| **TC-04** | ปฏิเสธ GIF, PDF และไฟล์ text ปลอมนามสกุล .jpg | Upload & Validation · `FR-02` | Live GPU | HTTP 415 ทุกไฟล์ | HTTP 415, 415, 415 | ✅ ผ่าน | [`TC-04.gif`](../images/tests/TC-04.gif) (109 KB) |
| **TC-05** | ขอบเขตจำนวนรูปต่อครั้ง (0, 50, 51 รูป) | Upload & Validation · `BR-06` | Live GPU | 0→422 · 50→201 · 51→422 | 422 · 201 · 422 | ✅ ผ่าน | [`TC-05.gif`](../images/tests/TC-05.gif) (108 KB) |
| **TC-06** | หน้า /upload ผูกไซต์ตามบัญชีหัวหน้างานอัตโนมัติ | Upload & Validation · `FR-04` | Live GPU | แสดง SITE-A และไม่มี select เปลี่ยนไซต์ | SITE-A · select=0 | ✅ ผ่าน | [`TC-06.gif`](../images/tests/TC-06.gif) (110 KB) |
| **TC-07** | Decision Table ครบ 8 กรณี R-1..R-8 (รวม H=0, V=2) | Rules & AI Detection · `BR-01..03` | Mock | 8/8 ตรงตารางตัดสิน (R-5 = FAIL) | 8/8 ตรงครบทุกกรณี | ✅ ผ่าน | [`TC-07.gif`](../images/tests/TC-07.gif) (70 KB) |
| **TC-08** | หน้า PhotoDetail วาดกรอบ Bounding Boxes ครบตาม H+V | Rules & AI Detection · `FR-07, FR-08` | Mock | H=1, V=1, 2 กรอบ SVG, ผล FAIL | H=1, V=1, 2 กรอบ, FAIL | ✅ ผ่าน | [`TC-08.gif`](../images/tests/TC-08.gif) (94 KB) |
| **TC-09** | Live 2× RTX 4090 YOLO11s ตรวจภาพหน้างานจริง 6 รูป + วาดกรอบ | Rules & AI Detection · `FR-07, NFR-01` | Live GPU | 6/6 DONE พร้อมกรอบ PPE และ GPU telemetry | 6/6 DONE (gpu0-8103, model=26.38ms) | ✅ ผ่าน | [`TC-09.gif`](../images/tests/TC-09.gif) (158 KB) |
| **TC-10** | หน้า /photos/problems แสดงเฉพาะรูป FAIL และ WARN | Rules & AI Detection · `FR-11` | Live GPU | รวม 31 (FAIL=20, WARN=11) | รวม 31 (FAIL=20, WARN=11) | ✅ ผ่าน | [`TC-10.gif`](../images/tests/TC-10.gif) (59 KB) |
| **TC-11** | หน้า /photos กรองตามวันที่ ไซต์ และผลตรวจ (WARN) | Rules & AI Detection · `FR-12` | Live GPU | กรอง WARN ไซต์ ก = 11 รูป | photos-total-count = 11 | ✅ ผ่าน | [`TC-11.gif`](../images/tests/TC-11.gif) (52 KB) |
| **TC-12** | API /api/photos/{id} คืนกรอบ PPE และ GPU Telemetry ครบ | Rules & AI Detection · `FR-07` | Live GPU | มี detections[], lb_upstream, lb_server, lb_model_ms | gpu0-8102 (127.0.0.1:8102) | ✅ ผ่าน | [`TC-12.gif`](../images/tests/TC-12.gif) (99 KB) |
| **TC-13** | ปิดหน้าเบราว์เซอร์กลางทาง 10 รูปยังตรวจจบครบ 10/10 | Reliability & GPU LB · `FR-05, NFR-04` | Live GPU | done=10, failed=0 หลังปิดหน้าจอ | done=10, failed=0 | ✅ ผ่าน | [`TC-13.gif`](../images/tests/TC-13.gif) (52 KB) |
| **TC-14** | ไฟล์ใหญ่ 14.9 MB และ 15.0 MB ตรวจจบครบผ่าน NGINX | Reliability & GPU LB · `BR-05, NFR-04` | Live GPU | done=2, failed=0 ไม่หลุด timeout | done=2 ใน 2.5 วินาที | ✅ ผ่าน | [`TC-14.gif`](../images/tests/TC-14.gif) (52 KB) |
| **TC-15** | ไฟล์เสีย corrupt_half.jpg จบ FAILED โดยไม่ขวางภาพปกติ | Reliability & GPU LB · `FR-06, NFR-04` | Live GPU | corrupt=FAILED, ปกติ=DONE 2/2 | done=2, failed=1 (เปิดไฟล์รูปไม่ได้) | ✅ ผ่าน | [`TC-15.gif`](../images/tests/TC-15.gif) (63 KB) |
| **TC-16** | ส่ง 20 รูปพร้อมกัน p95 ≤ 30 วิ และกระจายข้ามทั้ง 2× RTX 4090 | Reliability & GPU LB · `NFR-02, NFR-03` | Live GPU | 20/20 DONE, p95 ≤ 30s, gpu0 > 0 & gpu1 > 0 | 20/20 ใน 2.69s · p95=2.23s · gpu0=7, gpu1=13 | ✅ ผ่าน | [`TC-16.gif`](../images/tests/TC-16.gif) (139 KB) |
| **TC-17** | GET /api/health รายงาน db, storage, dispatcher, gateway = ok | Reliability & GPU LB · `NFR-04` | Live GPU | status=ok ทุกบริการ · ai_mode=real | status=ok, db=ok, dispatcher=ok, gateway=ok | ✅ ผ่าน | [`TC-17.gif`](../images/tests/TC-17.gif) (38 KB) |
| **TC-18** | BR-04 เส้นแบ่งสีแดง 89.67% แดง · 90.00% และ 90.33% ปกติ | Reports & Override · `BR-04` | Live GPU | SITE-A แดง · SITE-B/C ปกติ | 89.67%(แดง) · 90.00%(ปกติ) · 90.33%(ปกติ) | ✅ ผ่าน | [`TC-18.gif`](../images/tests/TC-18.gif) (62 KB) |
| **TC-19** | ขอบเขตพิเศษรายงาน (ไม่มีข้อมูล / 9÷10 / ตัด FAILED ออก) | Reports & Override · `FR-15, BR-04` | Live GPU | ไม่มีข้อมูล · 90.00% · 100.00% (ไม่แดง) | ตรงครบทั้ง 3 ไซต์ | ✅ ผ่าน | [`TC-19.gif`](../images/tests/TC-19.gif) (62 KB) |
| **TC-20** | BR-07 ป้ายความพร้อมรายงาน 17:59 น. vs 18:00 น. | Reports & Override · `BR-07` | Live GPU | 17:59→ระหว่างวัน · 18:00→พร้อมแล้ว | data-ready=false → true ตรงเวลา | ✅ ผ่าน | [`TC-20.gif`](../images/tests/TC-20.gif) (50 KB) |
| **TC-21** | แก้ผล FAIL → PASS เปลี่ยนไซต์ ก จาก 89.67% (แดง) เป็น 90.00% (ปกติ) | Reports & Override · `FR-13, FR-14, NFR-07` | Live GPU | คง model_result=FAIL, รายงานเป็น 90.00% ไม่แดง | 90.00% ไม่แดง · edited=1 | ✅ ผ่าน | [`TC-21.gif`](../images/tests/TC-21.gif) (123 KB) |
| **TC-22** | ปฏิเสธเหตุผลว่าง (422) + Audit History + ปุ่มเลื่อนวันรายงาน | Reports & Override · `FR-13, FR-16` | Live GPU | ว่าง→422 · มีเหตุผล→201 · เลื่อนวันได้ | 422 · 201 · 2026-11-17→16 | ✅ ผ่าน | [`TC-22.gif`](../images/tests/TC-22.gif) (71 KB) |
| **TC-23** | แยกสิทธิ์ RBAC ครบ 3 บทบาท (401/403/404) + UI Login | RBAC & Telemetry · `FR-18..22, NFR-06` | Live GPU | ไม่ล็อกอิน→401 · ข้ามไซต์→404 · เกินสิทธิ์→403 | 401 · 404 · 403 · UI Executive ซ่อนเมนูครบ | ✅ ผ่าน | [`TC-23.gif`](../images/tests/TC-23.gif) (92 KB) |
| **TC-24** | แดชบอร์ด /telemetry ONLINE (2× RTX 4090) + ไม่รั่ว API Key | RBAC & Telemetry · `NFR-05` | Live GPU | ONLINE · ครบ 4 รูปแบบ · 0 API Key ใน HTML/API | ONLINE (gpu0-8103) · 3/3 บทบาทเข้าได้ · 0 รั่วไหล | ✅ ผ่าน | [`TC-24.gif`](../images/tests/TC-24.gif) (107 KB) |
| **TC-25** | Bug Hunt #1 (BR-02): จับบัก H=0, V=2 ได้ WARN แทน FAIL | Bug Hunt (BUG_MODE=1) · `BR-02` | Mock (BUG_MODE=1) | ตรวจพบบัก: ระบบตอบ WARN แทน FAIL | จับได้! h0_v2.jpg ตอบ WARN แทน FAIL | 🐛 จับบักได้ | [`TC-25.gif`](../images/tests/TC-25.gif) (103 KB) |
| **TC-26** | Bug Hunt #2 (BR-04): จับบักอัตราผ่าน 90.00% พอดีเป็นสีแดง | Bug Hunt (BUG_MODE=1) · `BR-04` | Mock (BUG_MODE=1) | ตรวจพบบัก: SITE-B 90.00% แสดงสีแดง | จับได้! SITE-B 90.00% ได้ red=true | 🐛 จับบักได้ | [`TC-26.gif`](../images/tests/TC-26.gif) (63 KB) |
| **TC-27** | Bug Hunt #3 (BR-06): จับบักเปิดชุด 51 รูปแล้วรับ 201 แทน 422 | Bug Hunt (BUG_MODE=1) · `BR-06` | Mock (BUG_MODE=1) | ตรวจพบบัก: count=51 ตอบ HTTP 201 | จับได้! count=51 ตอบ HTTP 201 | 🐛 จับบักได้ | [`TC-27.gif`](../images/tests/TC-27.gif) (112 KB) |

## 3. ไฮไลต์การทดสอบบน `2× RTX 4090` จริง

- **`TC-09` (Live YOLO11s 6 รูปหน้างานจริง):** ตรวจครบ 6/6 รูปในเวลาไม่กี่วินาที พร้อมวาดกรอบ PPE และบันทึก `lb_server = gpu0-8103`, `model_ms = 26.38 ms`
- **`TC-14` (ไฟล์ใหญ่ 14.9 MB และ 15.0 MB พอดี):** ส่งผ่าน NGINX (`client_max_body_size 20m`) และตรวจจบทั้ง 2 ไฟล์ใน **2.5 วินาที**
- **`TC-16` (ชุด 20 รูปหน้างานจริงพร้อมกัน):** ตรวจจบครบ **20/20 รูปใน 2.69 วินาที** · **p95 = 2.23 วินาที** (เร็วกว่าเกณฑ์ 30 วินาทีถึง **13.5 เท่า**) และ NGINX `least_conn` กระจายงานข้ามทั้ง 2 การ์ดจอจริง (**GPU 0 = 7 รูป**, **GPU 1 = 13 รูป**)
- **`TC-25`–`TC-27` (Bug Hunt `BUG_MODE=1`):** จับบักซ่อนได้ครบทั้ง 3 ข้อ (`BR-02`, `BR-04`, `BR-06`) แล้วคืนค่า `BUG_MODE=0` เรียบร้อย

## 4. การยืนยันการลบเครื่อง GPU หลังทดสอบ

- ลบเครื่อง Vast.ai `62729107` (`label=e2e-sitesafe-nginx`) ทันทีหลังจบการทดสอบและยืนยันเหลือ `0` เครื่อง
- ปิดและลบคอนเทนเนอร์ทดสอบภายในเครื่อง (`sitesafe-nginx`, `sitesafe-mock`) เรียบร้อยแล้ว
