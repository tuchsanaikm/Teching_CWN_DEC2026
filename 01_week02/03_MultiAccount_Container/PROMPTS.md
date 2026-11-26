# พรอมต์ของบท 03 · MultiAccount Container (หน้ารวม)

รวมพรอมต์และคำสั่งทั้งหมดของบทนี้ตามลำดับ คัดลอกไปวางได้ทันที คำอธิบาย ภาพ และผลจริงอยู่ใน [README.md](README.md)

**ก่อนเริ่ม:** Claude Code app → **Code** → **New session** → เลือกโฟลเดอร์ `03_MultiAccount_Container` · Docker Desktop **Engine running** · ดิสก์ว่าง ~10 GB

## ขั้นที่ 1 · ให้ Claude สร้าง image (~30 นาที)

วางที่: Claude Code app (อนุญาตคำสั่ง `docker` เมื่อถูกถาม)

````markdown
# สร้าง Docker image `multi-account:1.0` ที่เปิดมาแล้วใช้หลายบัญชี AI ได้ทันที

## 1. Input · Spec · Output

**Input** · `./00_Devtool_Container`
โฟลเดอร์ที่มี Dockerfile ใช้เป็นฐานของ image (ไม่แก้ไฟล์ในโฟลเดอร์นี้)

**Spec** · `./prompt_multi_account.md`
สเปกระบบหลายบัญชี ทุกข้อต้องเป็นจริงใน image
ส่วน "ข้อเท็จจริงจากการทดลอง" ให้ลองกับ CLI เวอร์ชันที่ติดตั้งจริงก่อนใช้ (ดู flag ด้วย `--help`)

**Output** · `./MultiAccountDevtool` และ image `multi-account:1.0`
คัดลอก Input มาเป็นโฟลเดอร์นี้ แล้วแก้ในนี้เท่านั้น (ถ้ามีอยู่แล้ว ให้เทียบกับ Spec แล้วแก้เฉพาะที่ขาด)

## 2. สิ่งที่ต้องอยู่ใน image

- Claude Code, Codex CLI, Antigravity CLI และ Playwright MCP (pin เวอร์ชันทุกตัว) + Chromium + ฟอนต์ไทย
- installer และคำสั่ง `yolo1..5` / `cyolo1..5` / `gyolo1..5` ใน `/usr/local/bin`
  ใช้ได้ทั้งใน JupyterLab Terminal และ `docker exec`
- ไม่มีข้อมูลล็อกอินใน image: `/root/ai-accounts` เป็น volume
  และ installer รันทุกครั้งที่ container start โดยไม่ทับของเดิม
- คง Docker-in-Docker และ JupyterLab ไว้
- รองรับ `linux/amd64` และ `linux/arm64` (Mac Apple Silicon) ใน image ชื่อเดียว

## 3. Build

```bash
docker buildx build --platform linux/amd64,linux/arm64 -t multi-account:1.0 --load ./MultiAccountDevtool
```

## 4. ทดสอบ

ใช้ container และ volume ทดสอบชื่อใหม่ แล้วลบทิ้งเมื่อเสร็จ รายงาน PASS / FAIL / SKIP ตามจริง
ข้อที่ต้องล็อกอินให้เป็น SKIP ห้ามล็อกอินแทนผม

**สถาปัตยกรรมของเครื่องนี้**

- `yolo1..5` / `cyolo1..5` / `gyolo1..5 --version` ครบ 15 คำสั่ง และ config root คนละโฟลเดอร์
- skill `shared-check` ทุกบัญชีชี้ไปไฟล์เดียวกันใน shared ของ CLI นั้น
- `cyolo1 mcp list` และ `gyolo1 mcp list` เห็น `playwright`
- Playwright MCP ผ่าน stdio เปิด https://example.com แล้ว screenshot ได้
- installer รอบ 2 ไม่ทับของเดิม และ `.bashrc` ไม่ถูกแก้
- ลบ container แล้วสร้างใหม่ ของใน volume ยังอยู่
- JupyterLab `/lab` ตอบ `200`

**อีกสถาปัตยกรรมหนึ่ง** (รันผ่าน emulation ด้วย `--platform`)

- `uname -m` ถูกต้อง และ 15 คำสั่ง `--version` ครบ

## 5. รายงาน

- เขียนรายงานตามหัวข้อ "รายงาน" ของ Spec ไว้ใน Output (`./MultiAccountDevtool`) ห้ามมี secret
- สรุปเป็นตารางสั้น ๆ: ผลทดสอบแยกตามสถาปัตยกรรม · ขนาด image · เวลา build แล้วหยุด
````

## ขั้นที่ 2 · สร้าง container + ตรวจล็อกอิน (~1 นาที)

วางที่: Claude Code app · ข้ามขั้นที่ 1 ได้ พรอมต์นี้ดึง `tuchsanai/multi-account:1` ให้เอง · จากนั้นล็อกอินเองใน JupyterLab Terminal

````markdown
# รัน container ชื่อ `multi-account` จาก image `multi-account:1.0`

## 1. เตรียม image และ container

ถ้ายังไม่มี image `multi-account:1.0` ให้ดึงจาก Docker Hub แล้วตั้งชื่อใหม่

```bash
docker pull tuchsanai/multi-account:1
docker tag  tuchsanai/multi-account:1 multi-account:1.0
```

ถ้ามี container ชื่อ `multi-account` อยู่แล้ว ให้ลบออก (ห้ามลบ volume `ai-accounts`)

```bash
docker rm -f multi-account
```

## 2. สร้าง container

`PORT` เริ่มที่ `8886` ถ้าชนใช้เลขว่างถัดไป

```bash
docker run -dit \
  --name multi-account \
  --privileged \
  -p <PORT>:8888 \
  -v ai-accounts:/root/ai-accounts \
  multi-account:1.0 \
  bash -c 'F=/etc/jupyter/jupyter_server_config.py; grep -q delete_to_trash $F || printf "c.FileContentsManager.delete_to_trash = False\nc.FileContentsManager.always_delete_dir = True\n" >> $F; exec /usr/local/bin/start.sh'
```

จับเวลาตั้งแต่ `docker run` จน `http://localhost:<PORT>/lab` ตอบ `200`

## 3. ตรวจผ่าน `docker exec` แล้วสรุปเป็นตาราง

- `yolo1..5`, `cyolo1..5` และ `gyolo1..5 --version`
- `cyolo1 mcp list` และ `gyolo1 mcp list` ต้องเห็น `playwright`
- สถานะล็อกอินทุกบัญชี (ห้ามล็อกอินแทนผม ห้ามแก้ไฟล์ใด ๆ)
  - Claude: `yolo1` ถึง `yolo5` ใช้คำสั่ง `yoloN auth status` แล้วดูเฉพาะค่า `loggedIn`
  - Codex: `cyolo1` ถึง `cyolo5` ใช้คำสั่ง `cyoloN login status`
  - Antigravity: `gyolo1` ถึง `gyolo5` ใช้คำสั่ง `gyoloN models` (ขึ้น "Please sign in" = ยังไม่ล็อกอิน)
- ตารางสรุป: image มาจากไหน (build เอง / pull) · URL ของ JupyterLab · เวลาที่ใช้
  และตาราง บัญชี | เวอร์ชัน | ล็อกอินแล้ว/ยัง ห้ามแสดงอีเมล ชื่อองค์กร หรือ token
- ถ้ามีบัญชีที่ยังไม่ล็อกอิน ให้บอกวิธีล็อกอินใน JupyterLab Terminal
  (พิมพ์ `yoloN` แล้วเลือก Claude account with subscription / พิมพ์ `cyoloN login --device-auth`
  / พิมพ์ `gyoloN` แล้วเปิดลิงก์ล็อกอิน Google และวางรหัสกลับมา)
````

## ขั้นที่ 3 · ทดสอบ Playwright MCP ทุกบัญชี (~5 นาที)

วางที่: Claude Code app

```markdown
# ทดสอบ Playwright MCP ในบัญชีที่ล็อกอินแล้วของ container `multi-account`

ให้แต่ละบัญชีที่ล็อกอินแล้วใน container `multi-account` ทำงานต่อไปนี้ ห้ามล็อกอินแทนผม ห้ามแก้ไฟล์ตั้งค่า

- ใช้ skill `shared-check` แล้วบอกรหัสที่ได้
- ใช้ MCP ชื่อ `playwright` เท่านั้น ห้ามใช้ curl, python หรือ web search
- เปิด https://www.google.com/travel/flights?hl=en
- ค้นหาเที่ยวบินเที่ยวเดียว Bangkok (BKK) ไป Tokyo ชั้นประหยัด ผู้ใหญ่ 1 คน วันที่ 15 ของเดือนถัดไป
- ค้นหาอย่างเดียว ห้ามกดจอง ห้ามกรอกข้อมูลส่วนตัว ห้ามชำระเงิน ห้ามล็อกอินเว็บไซต์ใด
- screenshot ทุกขั้นตอนด้วย tool ของ playwright: เปิดหน้าเว็บ, กรอกต้นทาง-ปลายทาง, เลือกวันที่, ผลค้นหา
- รายงานเที่ยวบิน 3 อันดับแรก (สายการบิน เวลาออก-ถึง ราคา) ตามที่เห็นบนหน้าเว็บ
  ถ้าหน้าเว็บไม่แสดงผล ให้รายงานตามจริง ห้ามเดาราคา

เมื่อทุกบัญชีเสร็จ ให้รวม screenshot ของแต่ละบัญชีตามลำดับขั้นตอนเป็นไฟล์ `./evidence/<บัญชี>.gif` บนเครื่องผม
```

## ขั้นที่ 3 · รันซ้ำเฉพาะบัญชีที่เว็บ error

วางที่: Claude Code app (เปลี่ยน cyolo1 เป็นบัญชีที่ error)

```text
รัน cyolo1 ซ้ำอีกรอบด้วยพรอมต์เดิม แล้วอัปเดตหลักฐาน
```
