# LAB 7 · พรอมต์ Copy & Paste ทั้ง 10 ขั้น (RTX 4090 · Data Parallelism vs Model Parallelism 2+2)

[← กลับหน้าหลักของ LAB 7](README.md) · [สไลด์ประกอบการสอน](LAB7_LLM_Serving_LB_Slides.html)

วางทีละพรอมต์ในช่องพิมพ์ของ Claude Code ที่เปิดโฟลเดอร์ `02_VastAi_Application` · ทุกพรอมต์แบ่งหัวข้อเดียวกัน (`[ที่ทำงาน]`, `[งาน]`, `[ขั้นตอน]`, `[เกณฑ์]`, `[รายงาน]`) และออกแบบให้เริ่มจากโฟลเดอร์ว่างได้จริง · **เครื่องคิดเงินตลอดเวลาที่เปิด ห้ามข้ามขั้นที่ 10**

---

## ขั้นที่ 1 · เช่าเครื่อง RTX 4090 พร้อมกัน 2 เครื่อง (2 GPU และ 4 GPU)

```text
[ที่ทำงาน]
container `multi-account` · โฟลเดอร์ /workspace/vastapp_lab · สกิล vastai · SSH key: /root/.ssh/id_ed25519
เก็บโค้ดและผลที่: lab7_llm_serving_lb ของโฟลเดอร์ที่เปิด Claude Code อยู่

[งาน]
เช่าเครื่อง Vast.ai พร้อมกัน 2 เครื่องแบบ Single-Node แยกแทร็ก (ไม่ใช่คลัสเตอร์ Multi-Node):
1. `vapp-lab7-dp2`: 1 โหนด × 2× RTX 4090 (Track 1: Single GPU และ Data Parallelism 2×1 หลัง NGINX)
2. `vapp-lab7-mp4`: 1 โหนด × 4× RTX 4090 (Track 2: Model Parallelism 2+2 หลัง NGINX)

[ขั้นตอน]
1. ค้นหาข้อเสนอที่ถูกที่สุดตามเงื่อนไข: verified · reliability ≥ 0.95 · เน็ตขาเข้า/ออก ≥ 1,000 Mbps · CUDA ≥ 12.8 · ไม่อยู่ในจีน · disk ≥ 60 GB · direct_port_count ≥ 1
2. สร้างเครื่องทั้ง 2 ด้วย `--image vastai/pytorch:@vastai-automatic-tag --disk 60 --ssh --direct --env '-p 8080:8080'` (ถ้าเกิน 10 นาทียังไม่พร้อมให้ลบแล้วเช่าใหม่)
3. SSH เข้าทั้ง 2 เครื่องตรวจ `nproc` และ `nvidia-smi` ให้เห็น RTX 4090 ครบทุกใบ และอุณหภูมิตอนว่าง ≤ 60°C

[รายงาน]
สรุปตารางสเปก 2 เครื่อง (Instance ID · ที่ตั้ง · GPU · เน็ตขาเข้า/ออก · CPU/RAM · ราคา/ชม. · เวลาบูต) · ห้ามแสดงค่า key · บอกว่าเครื่องทั้ง 2 ยังเปิดอยู่
```

---

## ขั้นที่ 2 · ติดตั้ง vLLM, NGINX (udocker) และวัด 1-User Baseline

```text
[ที่ทำงาน]
container `multi-account` · /workspace/vastapp_lab · เครื่อง `vapp-lab7-dp2` และ `vapp-lab7-mp4` · SSH `/root/.ssh/id_ed25519` · เก็บที่ `lab7_llm_serving_lb`

[งาน]
ติดตั้งซอฟต์แวร์ชุดเดียวกันบนทั้ง 2 เครื่องขนานกัน ตั้ง NGINX แบบ container และวัดความเร็วผู้ใช้ 1 คน (1-User Baseline)

[ขั้นตอน]
1. เขียน `code/install_single.sh` รันขนานบนทั้ง 2 เครื่อง: สร้าง `uv venv` (Python 3.12), ติดตั้ง `vllm` และ `aiohttp` รุ่นเดียวกัน, ดาวน์โหลด `Qwen/Qwen3-4B-Instruct-2507` (ส่ง `HF_TOKEN` จาก `.env`/`.env_host` ทาง env เฉพาะตอนโหลดแล้ว `unset` และลบไฟล์ token ทันที), ติดตั้ง `udocker` + image `nginx:1.27`, สร้าง API key แบบสุ่มเก็บใน `runtime/api_key` และบันทึกเวลาลง `timings.json`
2. เขียน `code/nginx.conf`: พอร์ต 8080 · `worker_processes 4` · `zone ... 64k` · `least_conn` · pool `shop_dp1` (`:8001`), `shop_dp2` (`:8001–8002`), `shop_mp2` (`:8001–8002`), `shop_fake` (`:9000`) · `proxy_buffering off` · `gzip off` · `max_fails=1 fail_timeout=30s` · `proxy_next_upstream ... non_idempotent` · ตรวจ Bearer API key (ไม่มีตอบ 401) · แนบ header `X-Replica`
3. เขียน `code/node_single.sh` สลับโหมด `up <dp1|dp2|mp2> <cap>`, `set-pool`, `kill-port`, `stop`, `status` (ตั้ง `NCCL_CUMEM_HOST_ENABLE=0`, `--served-model-name shop-bot`, `--max-model-len 4096`, `--gpu-memory-utilization 0.90`, `HF_HUB_OFFLINE=1` และรอ ready สูงสุด 300 s สำหรับ cold start รอบแรก)
4. ตรวจ API key (`200` / `401`) แล้ววัด 1-User Baseline (อุ่นเครื่อง 2 + วัด 10 คำถาม) บน 1× RTX 4090 ของทั้ง 2 เครื่อง (ตั้งเกณฑ์ Fast SLO = 50% ของแต่ละเครื่อง) และบน 2× RTX 4090 (`TP=2`)

[รายงาน]
เวลาติดตั้งและโหลดโมเดลของทั้ง 2 เครื่อง · ยืนยันไม่เหลือ `HF_TOKEN` · ตารางเทียบ 1-User TTFT และความเร็ว (1× RTX 4090 vs `TP=2`) · บอกว่าเครื่องยังเปิดอยู่
```

---

## ขั้นที่ 3 · เขียนตัวยิงโหลดแบบ Streaming และพิสูจน์ว่าวัดถูก

```text
[ที่ทำงาน]
container `multi-account` · /workspace/vastapp_lab · เครื่อง `vapp-lab7-dp2` · SSH `/root/.ssh/id_ed25519` · เก็บที่ `lab7_llm_serving_lb`

[งาน]
เขียนตัวยิงโหลดแบบ Streaming (`code/loadgen.py`) และพิสูจน์ความแม่นยำกับ server จำลอง (`code/fake_llm.py`) ก่อนนำไปวัด vLLM จริง

[ขั้นตอน]
1. เขียน `code/loadgen.py` รันบนเครื่องเดียวกับ NGINX (หลาย worker process): จำลองผู้ใช้ N คนแบบ closed-loop สุ่ม 1 ใน 40 คำถามลูกค้าร้านขายของใช้ในบ้านภาษาไทย (`stream: true`, `max_tokens=150` สั้น / `600` ยาว) วัดระดับละ 30 s (อุ่นเครื่อง 10 s + นับผล 20 s) บันทึก TTFT p50/p95, Speed p50/p5, Throughput, error, สัดส่วน `X-Replica`, GPU (%/W) และ CPU
2. รองรับ 2 โหมด: `single` (ยิงระดับเดียวพร้อมผลรายวินาที) และ `capacity` (หาความจุ 3 จังหวะ: หาช่วง → ประมาณเส้นตรง → ปรับจนห่าง ≤ 5% โดยวัดซ้ำ 1 ครั้งเมื่อไม่ผ่าน)
3. เขียน `code/fake_llm.py` พอร์ต 9000 ตั้งค่าตายตัว TTFT = 200 ms, ความเร็ว 50 tok/s (20 ms/tok), 100 tokens/คำตอบ
4. สลับ NGINX เป็น `shop_fake` แล้วทดสอบ 3 กรณี (20 s, อุ่นเครื่อง 5 s): ยิงตรง `N=1`, ยิงตรง `N=50` และยิงผ่าน NGINX พอร์ต 8080 ที่ `N=50` บันทึก `results/loadtest_check_summary.json` และวาด `results/images/06_loadtest_check.png`

[เกณฑ์ผ่าน]
TTFT p50 คลาดเคลื่อนไม่เกิน 20 ms · ความเร็ว p50 อยู่ในช่วง 50±1 tok/s · Throughput ใกล้เคียงทฤษฎี (`N × 100 ÷ 2.2`) · error = 0 · NGINX ไม่พักรวม Token

[รายงาน]
ตารางเทียบค่าที่ควรได้กับค่าที่วัดได้ทั้ง 3 กรณี · CPU ของ loadgen และ NGINX · บอกว่าเครื่องยังเปิดอยู่
```

---

## ขั้นที่ 4 · Track 1 (Single GPU): ตอบทีละคำถาม เทียบ Continuous Batching

```text
[ที่ทำงาน]
container `multi-account` · /workspace/vastapp_lab · เครื่อง `vapp-lab7-dp2` (GPU 0 ใบเดียว) · SSH `/root/.ssh/id_ed25519` · เก็บที่ `lab7_llm_serving_lb`

[งาน]
วัดความจุบน 1× RTX 4090 ใบเดิม เทียบแบบที่ 1 ตอบทีละคำถาม (`dp1_seq`) กับแบบที่ 2 Continuous Batching (`dp1_cb`)

[ขั้นตอน]
1. เปิดโหมด 1 GPU ตอบทีละคำถาม (`node_single.sh up dp1 1`, `--max-num-seqs 1`) แล้วรัน `loadgen.py capacity` หาความจุ Standard ตั้งชื่อผล `dp1_seq`
2. เปิดโหมด 1 GPU Continuous Batching (`node_single.sh up dp1 256`, `--max-num-seqs 256`) บน GPU 0 ใบเดิม แล้วหาความจุ Standard (`dp1_cb`) และความจุ Fast (`dp1_cb_fast`, ใช้ค่า Fast SLO = 50% ของ 1-User จากขั้นที่ 2)
3. บันทึกผลลง `results/dp1_seq.json`, `results/dp1_cb.json`, `results/dp1_cb_fast.json` และดึงตัวอย่างคำถาม-คำตอบจริง 8 ข้อจาก 1-User Baseline วาด `results/dataset_samples.png`

[เกณฑ์ SLO]
Standard: TTFT p95 ≤ 2.0 s, Speed p5 ≥ 15.0 tok/s, error < 1% · Fast: TTFT p95 ≤ 2.0 s, Speed p5 ≥ 50% ของ 1-User, error < 1%

[รายงาน]
ตารางรายระดับ N และตารางเทียบ `dp1_seq` กับ `dp1_cb`: ความจุ Standard, ความจุ Fast, Peak Throughput (เพิ่มกี่เท่า), Running/Waiting และกำลังไฟ GPU (W) · บอกว่าเครื่องยังเปิดอยู่
```

---

## ขั้นที่ 5 · Track 1 (2 GPU Data Parallelism + NGINX — สูตรชนะ LAB 6)

```text
[ที่ทำงาน]
container `multi-account` · /workspace/vastapp_lab · เครื่อง `vapp-lab7-dp2` (2× RTX 4090) · SSH `/root/.ssh/id_ed25519` · เก็บที่ `lab7_llm_serving_lb`

[งาน]
เปิดครบ 2× RTX 4090 แบบ Data Parallelism (GPU ใบละ 1 โมเดลเต็ม) หลัง NGINX `least_conn` วัดความจุแบบที่ 3 (`dp2_cb`)

[ขั้นตอน]
1. เปิดโหมด 2 GPU Data Parallelism (`node_single.sh up dp2 256` · `gpu0 :8001` และ `gpu1 :8002` · NGINX `least_conn` พอร์ต 8080)
2. รัน `loadgen.py capacity` หาความจุ Standard ตั้งชื่อผล `dp2_cb` (ไล่ถึงระดับที่ชิดเกณฑ์หรือล้ม 2 ระดับติดกัน)
3. รัน `loadgen.py capacity` หาความจุ Fast (`dp2_cb_fast`, ใช้ค่า Fast SLO = 50% ของ 1-User บนเครื่อง `dp2` และ `--seed-from dp2_cb.json` เพื่อประหยัดเวลา)
4. บันทึกผลลง `results/dp2_cb.json` และ `results/dp2_cb_fast.json`

[เกณฑ์ SLO]
Standard: TTFT p95 ≤ 2.0 s, Speed p5 ≥ 15.0 tok/s, error < 1% · Fast: TTFT p95 ≤ 2.0 s, Speed p5 ≥ 50% ของ 1-User, error < 1%

[รายงาน]
ตารางรายระดับ N และตารางเทียบ 1 GPU (`dp1_cb`) กับ 2 GPU (`dp2_cb`): Speedup, Scaling Efficiency (%), สัดส่วนงาน `gpu0`/`gpu1` และกำลังไฟ (W) · บอกว่าเครื่องยังเปิดอยู่
```

---

## ขั้นที่ 6 · Concurrency Limit เมื่อผู้ใช้เกินความจุ

```text
[ที่ทำงาน]
container `multi-account` · /workspace/vastapp_lab · เครื่อง `vapp-lab7-dp2` (2× RTX 4090) · SSH `/root/.ssh/id_ed25519` · เก็บที่ `lab7_llm_serving_lb`

[งาน]
ทดสอบผลของเพดาน Concurrency Limit (`--max-num-seqs`) เมื่อมีผู้ใช้เข้ามาเกินความจุของระบบ 1.5 เท่า

[ขั้นตอน]
1. คำนวณระดับโหลดเกินความจุ `OVERLOAD_N = round(1.5 × ความจุ Standard จากขั้นที่ 5)` (เช่น 1,152 คนเมื่อความจุ 768)
2. วนทดสอบเพดาน 4 ค่า: `32`, `64`, `128` และ `256` ต่อ replica โดยสลับด้วย `node_single.sh up dp2 <cap>` แล้วรัน `loadgen.py single` ที่ `N = OVERLOAD_N` นาน 45 s (อุ่นเครื่อง 10 s นับผล 35 s)
3. บันทึกผลลง `results/cap_32.json` ถึง `results/cap_256.json` และวาดกราฟเปรียบเทียบ `results/images/04_cap_sweep.png`

[รายงาน]
ตารางเทียบทั้ง 4 เพดาน (Running/Waiting, TTFT p95, Speed p5, Throughput, กำลังไฟ GPU, ผ่าน SLO หรือไม่) · สรุปว่าเพดานช่วยรับคนเพิ่มได้จริงหรือไม่ และควรเลือกค่าไหนสำหรับ Fast vs Standard · บอกว่าเครื่องยังเปิดอยู่
```

---

## ขั้นที่ 7 · NGINX `least_conn` กับคำตอบยาวไม่เท่ากัน และ Replica Failover

```text
[ที่ทำงาน]
container `multi-account` · /workspace/vastapp_lab · เครื่อง `vapp-lab7-dp2` (2× RTX 4090) · SSH `/root/.ssh/id_ed25519` · เก็บที่ `lab7_llm_serving_lb`

[งาน]
ทดสอบ 2 สถานการณ์จริงบน Production ด้วย NGINX `least_conn`: (1) คำตอบสั้น-ยาวผสมกัน และ (2) Replica ล่มกลางการ Streaming

[ขั้นตอน]
1. เปิด `node_single.sh up dp2 256` และตั้งโหลด `MIX_N = round(0.4 × ความจุ Standard จากขั้นที่ 5)` (เช่น 307 คน)
2. วัดสมดุลคำตอบสั้น-ยาว (60 s, อุ่นเครื่อง 10 s): รัน `mix_short` (`--long-pct 0`, `max_tokens=150`) เทียบกับ `mix_long` (`--long-pct 20`, คำตอบยาว `max_tokens=600`)
3. วัด Replica Failover (`fail_replica`, 75 s, อุ่นเครื่อง 10 s): ตั้งเวลาสั่ง `node_single.sh kill-port 8002` (`SIGKILL`) ที่ +35 s กลางการ Streaming พร้อมบันทึก timestamp ลง `results/fail_event.json`
4. บันทึก `mix_short.json`, `mix_long.json`, `fail_replica.json` และวาด `results/images/05_mix_and_failover.png` (ปักเส้นเวลาปิด GPU 1 ตาม `kill_scheduled_epoch - t0_epoch` จริง)

[รายงาน]
ตารางเทียบ `mix_short` vs `mix_long` (งานค้างเฉลี่ย `gpu0`/`gpu1`, TTFT, Speed, error) และผล `fail_replica` (จำนวนสตรีมที่ขาดตอนล่ม, error หลังล่ม, Throughput ของ `gpu0` ที่เหลือ) · บอกว่าเครื่องยังเปิดอยู่
```

---

## ขั้นที่ 8 · Track 2 (4× RTX 4090 Model Parallelism 2+2 + NGINX `least_conn`)

```text
[ที่ทำงาน]
container `multi-account` · /workspace/vastapp_lab · เครื่อง `vapp-lab7-mp4` (4× RTX 4090) · SSH `/root/.ssh/id_ed25519` · เก็บที่ `lab7_llm_serving_lb`

[งาน]
วัดความจุแบบที่ 4: Model Parallelism แบบ 2+2 (`2 replica × TP=2`) บน 4× RTX 4090 หลัง NGINX `least_conn` เพื่อเทียบตรงกับ 2 GPU Data Parallelism

[ขั้นตอน]
1. เปิดโหมด Model Parallelism 2+2 (`node_single.sh up mp2 512`) แบ่ง 4 GPU เป็น 2 replica: `gpu0+1` (`:8001`, `--tensor-parallel-size 2`) และ `gpu2+3` (`:8002`, `--tensor-parallel-size 2`) วางหลัง NGINX `least_conn` พอร์ต 8080
2. รัน `loadgen.py capacity` หาความจุ Standard (`mp4_cb`) และความจุ Fast (`mp4_cb_fast`, ใช้ Fast SLO = 50% ของ 1-User 1 GPU บนเครื่อง `mp4` และ `--seed-from mp4_cb.json`)
3. บันทึกผลลง `results/mp4_cb.json` และ `results/mp4_cb_fast.json`

[เกณฑ์ SLO]
Standard: TTFT p95 ≤ 2.0 s, Speed p5 ≥ 15.0 tok/s, error < 1% · Fast: TTFT p95 ≤ 2.0 s, Speed p5 ≥ 50% ของ 1-User 1 GPU บนเครื่อง `mp4`, error < 1%

[รายงาน]
ตารางรายระดับ N และตารางเทียบ `mp4_cb` (4 GPU) กับ `dp2_cb` (2 GPU): 1-User Speed, TTFT, ความจุ Standard/Fast, Peak Throughput, Throughput/GPU และกำลังไฟ GPU (W) · บอกว่าเครื่องยังเปิดอยู่
```

---

## ขั้นที่ 9 · บันทึก Trace Token จริงและสร้างไฟล์ `.gif` ความเร็ว 1×

```text
[ที่ทำงาน]
container `multi-account` · /workspace/vastapp_lab · เครื่อง `vapp-lab7-dp2` และ `vapp-lab7-mp4` · เก็บที่ `lab7_llm_serving_lb`

[งาน]
อัด Timestamp ของทุก Token จริงจาก RTX 4090 แล้วเรนเดอร์เป็นไฟล์ `.gif` ความเร็ว 1× จริง (Real-Time) 2 ไฟล์เพื่อให้เห็นความเร็วการไหลด้วยตาเปล่า

[ขั้นตอน]
1. เขียนสคริปต์อัด trace การ Streaming จริง (`stream_options: include_usage`) จาก `TP=2 N=1` บน `mp4` และจาก `DP 1 GPU N=1`, `DP 2 GPU` โหลดกลาง/สูง บน `dp2` บันทึกลง `results/stream_*.json`
2. เขียนสคริปต์เรนเดอร์ `.gif` ความเร็ว 1× (10 FPS, ยาว 9–11 วินาที, ใช้ฟอนต์ไทยคมชัดและกรองอักขระนอกฟอนต์ไม่ให้เป็นกล่องสี่เหลี่ยม) 2 ไฟล์:
   - `images/lab/demo-speed-by-load.gif`: เทียบ 4 สภาวะพร้อมกัน (`TP=2 N=1`, `DP 1-GPU N=1`, `DP 2-GPU โหลดกลาง`, `DP 2-GPU โหลดสูง`)
   - `images/lab/demo-4users-live.gif`: แชทสั้น-ยาวต่อเนื่อง 3 รอบของ 4 ผู้ใช้พร้อมกันหลัง NGINX `least_conn` แสดงป้าย `gpu0` / `gpu1`
3. ตรวจเฟรมตัวอย่างของทั้ง 2 ไฟล์ว่าข้อความภาษาไทยคมชัด ไม่มีช่องสี่เหลี่ยม

[รายงาน]
เวลาจบของแต่ละสภาวะ · จำนวนเฟรมและความยาวจริงของทั้ง 2 ไฟล์ `.gif` · บอกว่าเครื่องยังเปิดอยู่
```

---

## ขั้นที่ 10 · ดึงผล วาดกราฟสรุป และลบเครื่องเช่าทั้ง 2 เครื่อง (ห้ามข้าม)

```text
[ที่ทำงาน]
container `multi-account` · /workspace/vastapp_lab · สกิล vastai · เก็บที่ `lab7_llm_serving_lb`

[งาน]
ดึงไฟล์ผลทั้งหมดกลับเข้าเครื่อง สร้างกราฟสรุปครบทุกการทดลอง และลบเครื่องเช่าทั้ง 2 เครื่องทันทีเพื่อหยุดค่าบริการ

[ขั้นตอน]
1. ดึงไฟล์ผลดิบ `.json` และ log จากทั้ง `vapp-lab7-dp2` และ `vapp-lab7-mp4` ลงมาเก็บที่ `lab7_llm_serving_lb/results/` และรวมตัวเลขสำคัญเป็น `results/metrics.json`
2. ลบเครื่องเช่าทั้ง 2 เครื่องทันทีด้วย `vastai destroy instance <id_dp2> -y` และ `vastai destroy instance <id_mp4> -y` แล้วตรวจ `vastai show instances` ให้เหลือ **0 instances**
3. วาดกราฟสรุปครบทุกภาพลง `results/images/` (`01_capacity_and_throughput.png`, `02_speed_and_throughput_curves.png`, `03_dp2_vs_mp4_tradeoff.png`, `04_cap_sweep.png`, `05_mix_and_failover.png`, `06_loadtest_check.png`)

[รายงาน]
ยืนยันผล `vastai show instances` = 0 เครื่อง · รายการไฟล์ผลและกราฟทั้งหมด · สรุปตารางเปรียบเทียบทั้ง 4 การออกแบบครบทุกมิติ
```
