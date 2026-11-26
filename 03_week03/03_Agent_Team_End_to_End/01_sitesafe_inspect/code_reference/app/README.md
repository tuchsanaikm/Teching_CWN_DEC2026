# SiteSafe Inspect · Pure LAB 6 Serving Architecture

ระบบตรวจรูปหน้างานก่อสร้างด้วยสถาปัตยกรรม **Pure LAB 6 (NGINX `least_conn` + 8× FastAPI Micro-batching บน `2× RTX 4090`)**: หัวหน้างานอัปโหลดรูป ระบบนับคนไม่ใส่หมวก (H) และคนไม่ใส่เสื้อสะท้อนแสง (V) แล้วตัดสินผล ผ่าน / เตือน / ไม่ผ่าน ตาม BR-01 ถึง BR-07 แก้ผลได้พร้อมร่องรอย (Audit Trail) และมีรายงานรายวันต่อไซต์พร้อมหน้า `/telemetry`

เอกสารประกอบ: `docs/REQUIREMENTS.md` · `docs/DESIGN.md` · `docs/TEST-DATA.md` · `docs/USER-STORIES.md` · ผลทดสอบ: `TEST.md`

| ฝั่ง | ที่ตั้ง | ส่วนประกอบ |
|---|---|---|
| เว็บ | เครื่องนี้ · `docker-compose.yml` | `db` (PostgreSQL 16 + Outbox) · `migrate` · `web` (Next.js 15 + Tailwind CSS + `/telemetry`) · `dispatcher` (`concurrency=16`) · volume `photos` · `mock-gateway` (เฉพาะ profile `test`) |
| AI | เครื่อง `2× RTX 4090` (Vast.ai) · `ai/serving/` | `nginx` (`least_conn` + Failover ON · พอร์ต `8080`) · `8× FastAPI Micro-batching` (`4 Processes/GPU` · `MAX_BATCH=16`, `MAX_WAIT_MS=15` · โมเดล YOLO11s `best.pt`) |

```text
web/          Next.js 15 (หน้าเว็บ + /api + /telemetry) · dispatcher/ · db/ · lib/rules.ts
ai/serving/   Pure LAB 6 Serving Stack: server.py · nginx.conf · cluster.sh · loadgen.py
ai/train/     evaluate.py · classes.json (ประเมินโมเดล YOLO11s ตาม NFR-01)
scripts/      smoke_test.py (ทดสอบเบื้องต้นผ่าน HTTP)
```

---

## 1. ฝั่งเว็บ (Docker Compose)

### 1.1 เชื่อมต่อเครื่อง `2× RTX 4090` จริง (`sitesafe-nginx`, พอร์ต `3410`)

```bash
cp .env.example .env          # ตั้ง GATEWAY_URL=http://<VAST_IP>:<PORT_8080>, GATEWAY_API_KEY, GATEWAY_PROTOCOL=lab6, DISPATCH_CONCURRENCY=16
docker compose -p sitesafe-nginx up -d --build
curl -s http://127.0.0.1:3410/api/health
```

### 1.2 โหมดจำลอง Deterministic Mock (`sitesafe-mock`, พอร์ต `3411`)

ใช้สำหรับทดสอบกรณีขอบเขต `BR-01`..`BR-03` และ **Bug Hunt (`BUG_MODE=1`)** โดยคืนค่า `H`, `V` ตามชื่อไฟล์ `h{H}_v{V}*.jpg`:

```bash
docker compose -p sitesafe-mock --env-file .env.test --profile test up -d --build
curl -s http://127.0.0.1:3411/api/health   # "status":"ok","ai_mode":"mock"
```

---

## 2. ฝั่ง AI บนเครื่อง `2× RTX 4090` (Pure LAB 6 Stack)

รันชุด `ai/serving/` บนเครื่อง `2× RTX 4090` (ใช้ไฟล์น้ำหนักที่เทรนไว้แล้ว `results/model/best.pt`):

```bash
cd ai/serving
export API_KEY="<GATEWAY_API_KEY>"
export MODEL_PATH="/workspace/best.pt"
bash cluster.sh up --gpus 2 --per-gpu 4 --mode micro --lb lc --failover on
curl -s http://127.0.0.1:8080/lb/health    # {"status":"ok","service":"nginx"}
curl -s http://127.0.0.1:8080/health       # {"status":"ready","server":"gpu0-8101","mode":"micro",...}
```

### ประเมินโมเดล (NFR-01)

```bash
pip install -r ai/train/requirements.txt
python ai/train/evaluate.py --data dataset/data.yaml --model results/model/best.pt --model-version ppe-yolo-v1 \
       --threshold results/model/threshold.json --classes ai/train/classes.json --device 0 --output metrics.json
```
