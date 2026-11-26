# TEST.md · ผลตรวจสอบการประกอบระบบ SiteSafe Inspect (Pure LAB 6 NGINX)

- สถาปัตยกรรม: **Pure LAB 6** (Next.js 15 + PostgreSQL Outbox + Async Dispatcher `concurrency=16` → NGINX `least_conn` + Failover ON → `8× FastAPI Micro-batching` บน `2× RTX 4090`)
- โหมดการทดสอบ:
  - **Live GPU (`sitesafe-nginx`, พอร์ต `3410`)**: ต่อ NGINX + 8× FastAPI บน `2× RTX 4090` จริง
  - **Mock (`sitesafe-mock`, พอร์ต `3411`)**: `AI_MODE=mock` สำหรับกรณีขอบเขต `BR-01`..`BR-03` และ `BUG_MODE=1` Bug Hunt

## สรุปเกณฑ์ความพร้อมของซอร์สโค้ด

| # | รายการตรวจ | ผล | รายละเอียด |
|---|---|---|---|
| 1 | `web` Next.js 15 Build + TypeScript + Unit Test | **ผ่าน** | `npm run typecheck`, `npm run build`, `vitest` ผ่านครบ 119/119 |
| 2 | `ai/train` Evaluation Unit Test | **ผ่าน** | `pytest ai/train/tests -q` ผ่าน 30/30 |
| 3 | `ai/serving` Pure LAB 6 Stack (`server.py`, `nginx.conf`, `cluster.sh`) | **ผ่าน** | รันจริงบน `2× RTX 4090` ความจุ 88 ผู้ใช้พร้อมกัน · 444.55 RPS · 0.00% Failover Error |
| 4 | Single Source of Truth ของ `BUG_MODE` และ `BR-01`..`BR-07` | **ผ่าน** | อ่าน `BUG_MODE` ที่ `web/lib/rules.ts` เพียงไฟล์เดียว |
| 5 | สิทธิ์ฐานข้อมูลแบบ Append-only (`NFR-07`) | **ผ่าน** | `sitesafe_app` ถูกปฏิเสธ `UPDATE`/`DELETE` บน `result_overrides` |
| 6 | ชุดทดสอบ E2E Playwright + วิดีโอ `.gif` ครบทุก Test Case | **ผ่าน** | ดูรายละเอียดครบทุกข้อใน `test/TEST-REPORT.md` และ `test/index.html` |
