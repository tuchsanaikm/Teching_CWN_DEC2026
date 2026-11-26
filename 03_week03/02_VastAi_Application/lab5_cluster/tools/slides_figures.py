#!/usr/bin/env python3
"""ภาพใหม่ของสไลด์ LAB 5 (20 ภาพ: ภาพประกอบอธิบาย 6 ภาพ + ภาพถ่าย/3D render เชิงเปรียบเปรย 14 ภาพ)

FIGS   = ภาพประกอบอธิบายแบบการ์ตูน 1 ภาพต่อ 1 สไลด์ "ภาพ + ขั้นตอน" (ภาพด้านซ้าย ขั้นตอนเรียงเลขด้านขวา)
PHOTOS = ภาพถ่าย / 3D render แบบภาพยนตร์ 16:9 ของหน้าปก หน้าแผนที่เส้นทาง หน้าคั่น และหน้า Hero ตัวเลขใหญ่
         (ไม่มีตัวอักษรในภาพ · ฝั่งซ้าย 45% มืดและโล่ง · สไลด์ใส่ป้าย "ภาพจำลอง")

  python tools/slides_figures.py <โฟลเดอร์ปลายทาง นอกรีโป> [ภาพอ้างอิงสไตล์ ...]
"""
import os, sys

SETTING = ('an AI engineering training workshop running Qwen3-8B LoRA fine-tuning across a multi-node cloud GPU cluster '
           '(2-node and 3-node clusters of RTX 3090 24 GB x2 machines connected over the public internet)')

FIGS = [
    {"img": "n01-lab5-folders",
     "title": "แผนที่โฟลเดอร์ของ LAB 5: เทียบ 1 Node กับ 2 แล็บย่อยบนคลัสเตอร์",
     "labels": ["ตัวเทียบ 1 Node · LAB 4", "lab4_multigpu/ (ไม่รันใหม่)", "1 เครื่อง · GPU 2 ใบผ่าน PCIe",
                "LAB 5.1 · Data Parallelism", "1_data_parallel/ (+ node3/)", "2 และ 3 Node · GPU ละ 1 โมเดล",
                "LAB 5.2 · Model Parallelism", "2_model_parallel/ (+ node3/)", "2 และ 3 Node · Node ละ 1 โมเดล"],
     "scene": "Three rounded pastel cards arranged cleanly in one horizontal row from left to right, joined by crisp navy arrows like a course roadmap. "
              "Each card has a colored title pill at the top, a yellow folder tab with monospace folder name underneath, a cute flat icon in the middle, and a clean white pill at the bottom (NO numbered circles anywhere). "
              "Card 1 (soft grey-blue): top 'ตัวเทียบ 1 Node · LAB 4', folder 'lab4_multigpu/ (ไม่รันใหม่)', middle icon a single server box with two GPUs linked tightly inside, bottom '1 เครื่อง · GPU 2 ใบผ่าน PCIe'. "
              "Card 2 (soft sky blue): top 'LAB 5.1 · Data Parallelism', folder '1_data_parallel/ (+ node3/)', middle icon two small server boxes connected by a cloud each containing two GPUs with smiling robot faces, bottom '2 และ 3 Node · GPU ละ 1 โมเดล'. "
              "Card 3 (soft peach-orange): top 'LAB 5.2 · Model Parallelism', folder '2_model_parallel/ (+ node3/)', middle icon two small server boxes connected by a cloud each containing one robot split across two GPUs, bottom '2 และ 3 Node · Node ละ 1 โมเดล'. "
              "No charts, no bars, no gauges, no extra numbers.",
     "steps": ["**ตัวเทียบ 1 Node (`lab4_multigpu/`)** ไม่ต้องรันใหม่ ใช้ผล GPU 2 ใบในเครื่องเดียวของ LAB 4.2 และ LAB 4.3 เป็นจุดเทียบความเร็ว",
               "**LAB 5.1 (`1_data_parallel/` และ `node3/`)** เทรนแบบ Data Parallelism ข้าม 2 Node (GPU 4 ใบ) แล้วขยายเป็น 3 Node (GPU 6 ใบ) รวม 6 ขั้น",
               "**LAB 5.2 (`2_model_parallel/` และ `node3/`)** แบ่ง Layer ของโมเดลลง 2 GPU ในแต่ละเครื่อง แล้วเฉลี่ย Gradient ข้าม 2 Node และ 3 Node รวม 6 ขั้น"]},

    {"img": "n02-comm-math",
     "title": "ประมาณเวลาส่งก่อนเทรน: ขนาด Gradient หารความเร็วเน็ต",
     "labels": ["1 ขนาด Gradient", "2 Worker × 15.3 MB", "= 30.7 MB (245 Mbit)",
                "2 วัดความเร็วเน็ต", "Node 2 → Node 1", "วัดได้ 143 Mbps",
                "3 เทียบเวลาต่อ step", "ส่งขึ้น ≈ 1.7 วิ (ไม่รวมขากลับ)", "คำนวณบน GPU 0.43 วิ"],
     "scene": "Three rounded pastel cards arranged left to right connected by bold arrows, with numbered circle badges 1, 2, 3. "
              "Card 1 (soft lavender): two neat orange data parcel boxes being weighed on a simple flat icon scale, with labels '1 ขนาด Gradient', '2 Worker × 15.3 MB', '= 30.7 MB (245 Mbit)'. "
              "Card 2 (soft sky blue): two small server icons linked by a narrow cloud tube with a stopwatch icon, with labels '2 วัดความเร็วเน็ต', 'Node 2 → Node 1', 'วัดได้ 143 Mbps'. "
              "Card 3 (soft peach-pink): a small white-and-blue robot looking surprised at a simple hourglass icon beside a small GPU chip icon (NO bar chart, NO gauge), with labels '3 เทียบเวลาต่อ step', 'ส่งขึ้น ≈ 1.7 วิ (ไม่รวมขากลับ)', 'คำนวณบน GPU 0.43 วิ'. "
              "No bar charts, no line graphs, no gauges, no meters.",
     "steps": ["**คำนวณปริมาณข้อมูลต่อ step** Node 2 มี 2 Worker ส่ง Gradient ของ LoRA ขึ้นพร้อมกัน `2 × 15.3 MB = 30.7 MB = 245 Mbit`",
               "**วัดความเร็วเน็ตจริงระหว่าง Node** ในรอบ DP 2 Node ทิศ `Node 2 → Node 1` วัดได้จริงเพียง **143 Mbps** (ไม่ใช่ 700 Mbps ที่หน้าเช่าประกาศ)",
               "**เทียบกับเวลาคำนวณบน GPU** แค่ส่งขาขึ้นก็ใช้ `245 ÷ 143 ≈ 1.7 วินาที` นานกว่าเวลาคำนวณ (0.43 วินาที) ราว 4 เท่าแล้ว จึงรู้ก่อนเทรนว่าเน็ตจะเป็นคอขวด"]},

    {"img": "n03-dp-oom",
     "title": "แก้ OOM ตอนลอง 3 step ใน DP 2 Node: คิดคะแนนเฉพาะคำตอบ",
     "labels": ["1 ลอง 3 step (มี padding)", "แถวยาวสุด 256 token", "คำนวณคะแนนทุกตำแหน่ง → OOM",
                "2 แก้โค้ด worker.py", "คิดคะแนนเฉพาะตำแหน่งคำตอบ SQL", "ไม่เปลี่ยนค่าที่ตรึง · loss เท่าเดิม",
                "3 ผ่านฉลุย", "VRAM สูงสุด 22,063 MiB", "เทรนครบ 2 Epoch (500 step)"],
     "scene": "Three rounded pastel cards arranged left to right connected by crisp navy arrows, with numbered circle badges 1, 2, 3. "
              "Card 1 (soft pink-red): four horizontal token strips with dotted padding blocks feeding into a giant heavy matrix box with a red X warning icon, with labels '1 ลอง 3 step (มี padding)', 'แถวยาวสุด 256 token', 'คำนวณคะแนนทุกตำแหน่ง → OOM'. "
              "Card 2 (soft sky blue): the same strips where question and padding tokens are faded grey and ONLY the short SQL answer tokens feed into a small neat matrix box, with labels '2 แก้โค้ด worker.py', 'คิดคะแนนเฉพาะตำแหน่งคำตอบ SQL', 'ไม่เปลี่ยนค่าที่ตรึง · loss เท่าเดิม'. "
              "Card 3 (soft mint green): a smiling white-and-blue robot giving a thumbs-up next to a green checkmark badge and a clean GPU card icon, with labels '3 ผ่านฉลุย', 'VRAM สูงสุด 22,063 MiB', 'เทรนครบ 2 Epoch (500 step)'. "
              "No bar charts, no gauges, no meters.",
     "steps": ["**ลอง 3 step ก่อนเทรนจริง** ด้วย batch ที่มีตัวอย่างยาว 256 token ปนตัวอย่างสั้น แล้วเกิด Out of Memory เพราะต้องสร้างตารางคะแนนคำศัพท์ทุกตำแหน่ง",
               "**แก้ใน `worker.py` โดยไม่แตะค่าที่ตรึง** คำนวณ logits เฉพาะตำแหน่งที่เป็นคำตอบ SQL ซึ่งให้ค่า loss เท่าเดิมทุกประการ",
               "**ผลลัพธ์** ผ่านการทดสอบที่ VRAM สูงสุด **22,063 MiB** และเทรนครบ 2 Epoch (500 step) โดยไม่ล้มกลางทาง"]},

    {"img": "n04-socket-bug",
     "title": "บทเรียน 3 Node: ตั้งขนาด socket buffer เองทำให้ช้าลงหลายเท่า",
     "labels": ["1 ตั้ง socket buffer เอง", "รันทดสอบช้าผิดปกติ", "16–70 วินาทีต่อ step",
                "2 ปล่อยระบบจัดการเอง", "เอาการตั้ง buffer ออก", "เหลือ 3.5–4 วินาทีต่อ step",
                "3 บทเรียนคลัสเตอร์", "เกิดซ้ำใน 3 Node ทั้ง 5.1 และ 5.2", "ถ้า step ช้าผิดปกติ ให้เช็กข้อนี้ก่อน"],
     "scene": "Three rounded pastel cards arranged left to right connected by arrows, with numbered circle badges 1, 2, 3. "
              "Card 1 (soft pink-orange): a cute clogged narrow water pipe with a tiny wrench stuck inside and a slow snail icon next to a red X, with labels '1 ตั้ง socket buffer เอง', 'รันทดสอบช้าผิดปกติ', '16–70 วินาทีต่อ step'. "
              "Card 2 (soft mint green): a wide smooth open network pipe with glowing data packets flowing smoothly and a green checkmark, with labels '2 ปล่อยระบบจัดการเอง', 'เอาการตั้ง buffer ออก', 'เหลือ 3.5–4 วินาทีต่อ step'. "
              "Card 3 (soft lavender): a cute white-and-blue robot holding a magnifying glass and a checklist card, with labels '3 บทเรียนคลัสเตอร์', 'เกิดซ้ำใน 3 Node ทั้ง 5.1 และ 5.2', 'ถ้า step ช้าผิดปกติ ให้เช็กข้อนี้ก่อน'. "
              "No bar charts, no gauges, no meters.",
     "steps": ["**ปัญหาที่เจอตอนลอง 3 step** AI ตั้งค่าขนาด socket buffer เอง ทำให้ระบบ TCP autotuning ของ OS ทำงานไม่เต็มที่จนช้าถึง **16–70 วินาทีต่อ step**",
               "**วิธีแก้ที่เรียบง่าย** เอาโค้ดที่กำหนดขนาด buffer ออก ให้ระบบปฏิบัติการปรับขนาดเอง เวลาต่อ step ลดฮวบเหลือ **3.5–4 วินาที**",
               "**ข้อควรจำ** บั๊กนี้เกิดซ้ำในรอบ 3 Node ของทั้ง LAB 5.1 และ LAB 5.2 ถ้าเห็น step ช้าผิดปกติตั้งแต่ทดสอบ 3 step ให้ตรวจการตั้งค่า socket ก่อน"]},

    {"img": "n05-mp2-recovery",
     "title": "รับมือปัญหาหน้างาน MP 2 Node: 4 สาย TCP และต่อจาก checkpoint",
     "labels": ["1 สายเดียวค้าง 92 วิ", "แก้เป็น 4 สาย + ส่งขาขึ้น bf16", "ตัดต่อใหม่เมื่อนิ่ง 8 วิ",
                "2 โฮสต์ Node 1 reboot", "ดับกลางรัน 5 นาที", "ช่วง step 162–168",
                "3 รันต่อจาก checkpoint", "เริ่มต่อจาก step 150", "เทรนครบ 500 step · LoRA เท่ากัน"],
     "scene": "Three rounded pastel cards arranged left to right connected by arrows, with numbered circle badges 1, 2, 3. "
              "Card 1 (soft sky blue): one tangled single cable transforming into four clean parallel neat cables between two small servers, with labels '1 สายเดียวค้าง 92 วิ', 'แก้เป็น 4 สาย + ส่งขาขึ้น bf16', 'ตัดต่อใหม่เมื่อนิ่ง 8 วิ'. "
              "Card 2 (soft pink-red): a server icon with a small lightning bolt / power restart symbol above it and a warning triangle, with labels '2 โฮสต์ Node 1 reboot', 'ดับกลางรัน 5 นาที', 'ช่วง step 162–168'. "
              "Card 3 (soft mint green): a smiling white-and-blue robot loading a glowing save-disk checkpoint icon into two servers with a green checkmark, with labels '3 รันต่อจาก checkpoint', 'เริ่มต่อจาก step 150', 'เทรนครบ 500 step · LoRA เท่ากัน'. "
              "No bar charts, no gauges, no meters.",
     "steps": ["**แก้ปัญหาการส่งค้าง** รอบแรกส่งแบบ 1 สายแล้วค้างถึง **92 วินาที** AI จึงเปลี่ยนเป็น **4 สาย TCP** พร้อมแปลงขาขึ้นเป็น `bf16` (ขนาดครึ่งเดียว) และตัดต่อใหม่เมื่อข้อมูลนิ่ง 8 วินาที",
               "**โฮสต์ของ Node 1 reboot เองกลางรัน** เครื่องดับไปราว **5 นาที** ช่วง step 162–168 แสดงว่ายิ่งมีหลายเครื่อง โอกาสที่เครื่องใดเครื่องหนึ่งจะมีปัญหายิ่งสูง",
               "**กู้คืนจาก checkpoint สำเร็จ** เปิด Coordinator และ Worker ใหม่ให้ต่อจาก **step 150** จนครบ 500 step และยืนยันว่าน้ำหนัก LoRA ทั้ง 2 Node เท่ากันทุกค่า"]},

    {"img": "n06-cluster-caveats",
     "title": "ข้อจำกัดที่ต้องรู้เมื่ออ่านตัวเลขเทียบข้ามรอบใน LAB 5",
     "labels": ["1 คนละชุดเครื่อง คนละประเทศ", "เน็ตต่างกันและแกว่ง", "เทียบข้ามรอบได้คร่าว ๆ",
                "2 โค้ดและ batch ต่างกัน", "batch รวม 8 · 16 · 24", "บางรอบส่งขาขึ้น bf16 บางรอบ float32",
                "3 จำนวน Epoch และ Test Set", "1 Node เทรน 3 Epoch · คลัสเตอร์ 2 Epoch", "Test Set 200 ข้อ (1 ข้อ = 0.5 จุด)"],
     "scene": "Three rounded pastel cards arranged side by side from left to right with numbered circle badges 1, 2, 3 and a friendly small white-and-blue robot holding a magnifying glass at the bottom right. "
              "Card 1 (soft blue): small globe icon with two server icons on opposite sides and a wavy dotted line between them, with labels '1 คนละชุดเครื่อง คนละประเทศ', 'เน็ตต่างกันและแกว่ง', 'เทียบข้ามรอบได้คร่าว ๆ'. "
              "Card 2 (soft peach): three stacked trays of data cards of increasing sizes next to a small code file icon, with labels '2 โค้ดและ batch ต่างกัน', 'batch รวม 8 · 16 · 24', 'บางรอบส่งขาขึ้น bf16 บางรอบ float32'. "
              "Card 3 (soft lavender): a small calendar / epoch loop icon next to a 200-question exam clipboard icon, with labels '3 จำนวน Epoch และ Test Set', '1 Node เทรน 3 Epoch · คลัสเตอร์ 2 Epoch', 'Test Set 200 ข้อ (1 ข้อ = 0.5 จุด)'. "
              "No bar charts, no line charts, no gauges.",
     "steps": ["**เครื่องเช่าคนละชุด คนละประเทศ** ความเร็วเน็ตของแต่ละรอบต่างกันมากและแกว่งระหว่างวัน จึงเทียบข้ามรอบได้คร่าว ๆ และรอบของผู้เรียนอาจได้เลขต่างออกไป",
               "**โค้ดและ batch รวมไม่เท่ากัน** 1 Node ใช้ PyTorch ในเครื่อง ส่วนคลัสเตอร์ใช้ Coordinator ที่ AI เขียนใหม่ทีละรอบ (บางรอบส่งขาขึ้น `bf16` บางรอบ `float32`) และ batch รวมต่างกัน (8, 16, 24)",
               "**Epoch และขนาด Test Set** 1 Node เทรน 3 Epoch (เทียบ Exact Match ที่ Epoch 2) และ Test Set มี 200 ข้อ (1 ข้อ = 0.5 จุด) ส่วนต่าง 2–3 จุดจึงยังสรุปไม่ได้ว่าแบบใดแม่นกว่า"]},

]

PHOTOS = [
    # ---- ปก หน้าคั่น และแผนที่เส้นทาง (6 ภาพ)
    {"img": "s01-cover",
     "scene": "Cinematic dark studio 3D photograph on the right half of the frame: three sleek dark metallic AI server racks standing slightly separated across dark atmospheric space, "
              "each glowing with twin cyan GPU cores inside, connected together by luminous amber-orange fiber-optic light arcs spanning the gap between them. "
              "The left 45% of the frame is deep dark navy-black shadow with smooth uncluttered negative space for title text. Dramatic rim lighting, ultra-sharp, photorealistic."},

    {"img": "s02-foundations",
     "scene": "Cinematic high-contrast 3D architectural render on the right half of the frame: a central glowing obsidian-and-gold network coordinator hub receiving thin streams of cyan and amber data packets from distant illuminated server nodes floating in dark space. "
              "The left 45% of the frame is deep dark midnight shadow with calm empty negative space. Crisp studio lighting, sleek tech aesthetic."},

    {"img": "s03-dp-cluster",
     "scene": "Cinematic dark studio 3D render on the right half of the frame: three sleek dark server towers spaced apart, each housing two glowing electric-cyan GPU cards carrying identical luminous crystal neural cubes, "
              "sending synchronized thin golden-orange light threads toward the first tower. "
              "The left 45% of the frame is deep dark shadow and clean negative space. High contrast, photorealistic."},

    {"img": "s04-mp-cluster",
     "scene": "Cinematic high-contrast 3D architectural render on the right half of the frame: two separate dark server nodes facing forward; inside each node, a single luminous split neural core spans across two linked GPUs (cyan front half, warm amber back half), "
              "while a long glowing amber fiber bridge links the two separate nodes across dark space. "
              "The left 45% of the frame is deep dark slate-black empty space. Dramatic volumetric light."},

    {"img": "s05-summary",
     "scene": "Cinematic photograph seen from behind on the right half of the frame: two fictional engineers in dark smart-casual shirts standing in a dim modern network operations room, "
              "looking calmly at softly glowing dark server racks and out-of-focus fiber-optic trunk cables with warm amber and cyan indicator lights (completely out of focus, zero readable symbols). "
              "The left 45% of the frame is deep dark out-of-focus shadow for text. Photorealistic, shallow depth of field."},

    {"img": "s07-lab5-journey",
     "scene": "Wide cinematic 3D architectural illustration (full-frame scenic vista, vibrant twilight navy sky with glowing cyan and warm amber lights, NO text anywhere): "
              "On the far left sits a compact blazing-fast glowing single server tower (1 Node) with ultra-bright thick short cyan internal links. "
              "From it, a long winding narrow glowing amber suspension bridge stretches across a wide dark ocean valley (symbolizing the public internet) toward the right side, "
              "where TWO separate multi-tower server islands stand (2 Nodes and 3 Nodes): the upper island shows glowing twin-core cyan replica towers (Data Parallel cluster) and the lower island shows split cyan-and-gold relay towers (Model Parallel cluster). "
              "Tiny amber light packets travel slowly across the long narrow internet bridge while the distant GPU towers wait calmly. Rich sci-fi editorial aesthetic, razor sharp, zero text, zero numbers, zero letters."},

    # ---- หน้า Hero ตัวเลขใหญ่ (8 ภาพ · ซ้าย 45% มืดโล่ง ไม่มีตัวอักษร)
    {"img": "h01-dp2-net",
     "scene": "Cinematic dark 3D studio render on the right half of the frame: two bright glowing modern server towers standing close together, "
              "connected by a dramatic glass funnel pipe that starts wide and bright cyan on one side but pinches sharply into a narrow glowing amber bottleneck in the middle, visually depicting low ping yet constrained upload bandwidth. "
              "The left 45% of the frame is completely dark calm negative space. Zero text, zero numbers."},

    {"img": "h02-dp2-res",
     "scene": "Cinematic dark 3D studio render on the right half of the frame: four sleek black graphics cards resting quietly in dim cool-blue standby glow inside two server frames, "
              "while a single bright warm-amber glowing data capsule slowly traverses a long winding glass fiber bridge looping between them — metaphor for GPUs sitting idle waiting on the network. "
              "The left 45% of the frame is deep dark empty shadow. Zero text, zero numbers."},

    {"img": "h03-dp3-res",
     "scene": "Cinematic dark 3D studio render on the right half of the frame: three distant dark metallic server clusters arranged in a semicircle, "
              "each with dim standby cyan GPUs funneling glowing amber data streams into one single congested glowing central glass hub where bright orange light packets back up in a queue. "
              "The left 45% of the frame is deep dark empty shadow. Zero text, zero numbers."},

    {"img": "h04-mp2-net",
     "scene": "Cinematic dark studio 3D render on the right half of the frame: two sleek dark server towers positioned across a misty dark gulf, "
              "connected by a thin flickering golden-amber laser thread struggling through faint atmospheric haze — depicting cross-country internet bandwidth far slower than advertised. "
              "The left 45% of the frame is pitch-dark calm negative space. Zero text, zero numbers."},

    {"img": "h05-mp2-res",
     "scene": "Cinematic dark 3D studio render on the right half of the frame: two dark metallic glass server chambers showing generous cool-cyan empty headroom inside each translucent memory core (only partially filled), "
              "connected across the dark gap by four thin parallel glowing amber fiber threads carrying tiny light pulses. "
              "The left 45% of the frame is deep dark empty shadow. Zero text, zero numbers."},

    {"img": "h06-mp3-res",
     "scene": "Cinematic dark 3D studio render on the right half of the frame: three sequential dual-GPU server pods arranged radially around a central glowing coordinator pedestal, "
              "with two pods already dimmed in waiting standby while a single bright amber light packet slowly finishes arriving from the farthest third pod — depicting synchronous barrier waiting for the slowest node. "
              "The left 45% of the frame is deep dark empty shadow. Zero text, zero numbers."},

    {"img": "h07-network-wall",
     "scene": "Cinematic dark high-contrast 3D visual on the right half of the frame: six blazing electric-cyan high-speed light streams surging forward like race tracks, "
              "abruptly halted against a tall dramatic translucent glowing amber glass barrier wall across the center, with only a thin trickle of amber light passing through — metaphor for the internet communication bottleneck capping cluster speed. "
              "The left 45% of the frame is deep dark calm shadow for big white hero numbers. Zero text, zero numbers."},

    {"img": "h08-quality-sync",
     "scene": "Cinematic dark studio photograph on the right half of the frame: a precision dark-metal archery target lit by dramatic warm rim lighting, "
              "with glowing cyan and golden arrows clustered tightly together inside the luminous golden center bullseye, surrounded by subtle concentric synchronized light ripples — metaphor for distributed gradient averaging preserving exact model quality. "
              "The left 45% of the frame is pitch-dark calm negative space. Zero text, zero numbers."},
]

CARTOON = """Generate ONE illustration with your image generation tool and save it as a PNG file at exactly this path:
{out}/{img}.png

First open and look at these reference images, then match their illustration style exactly (same kind of flat, cute, clean
cartoon infographic: white or very light background, a pastel sky-blue rounded title banner at the top, rounded pastel cards
with thin dark navy outlines, numbered circle badges, small white-and-blue robot helper, bold rounded Thai lettering):
{refs}

Canvas: landscape 16:9 (about 1672 x 941). Setting: {setting}.

Title banner text at the top (exact): {title}

Scene: {scene}

Text labels to place in the picture, each next to the element it names (exact text, one label per line below):
{labels}

Strict text rules:
- Write every label EXACTLY as given, character by character. Thai stays Thai, English stays English, numbers and symbols stay as they are.
- Do NOT add any other words, numbers, captions, watermarks or logos beyond the title and the labels above.
- When a label starts with a number (for example "1 ขนาด Gradient"), draw that number ONLY inside the circle badge and write the rest of the label next to it. Never repeat the same number twice.
- Do NOT draw bar charts, line charts, gauges, meters or progress bars. Nothing in the picture may suggest an unmeasured value.
- Text must be large, bold and easy to read from the back of a classroom. Code-like labels use a monospace style.
- Characters: fictional cartoon characters only.

Rules: create only that one file. Do not modify any other file. Do not run any git command (no add, commit, push).
When the file is saved, reply with the file path and stop.
"""

PHOTO = """Generate ONE high-impact cinematic image with your image generation tool and save it as a JPG file at exactly this path:
{out}/{img}.jpg

Scene: {scene}

Requirements:
- Landscape 16:9 (about 1920x1080), cinematic high-contrast lighting, deep shadows, crisp cyan, orange, and warm gold accents.
- Keep the left 45% of the frame very dark, calm, and uncluttered (negative space) because white titles and big white numbers will be placed over the left side later; place the main visual subject on the right 55% (except for full-frame scenic maps where explicitly noted).
- ABSOLUTELY NO readable text anywhere: no letters, no numbers, no logos, no brand names, no signs, no watermarks, no UI text on screens.
- Any people must be generic fictional adults seen from behind or in silhouette; no recognizable real person's likeness.

Rules: create only that one file. Do not modify any other file. Do not run any git command (no add, commit, push).
When the file is saved, reply with the file path and stop.
"""

if __name__ == "__main__":
    out = os.path.abspath(sys.argv[1]).replace("\\", "/")
    refs = [os.path.abspath(p).replace("\\", "/") for p in sys.argv[2:]]
    os.makedirs(out, exist_ok=True)
    for f in FIGS:
        open(os.path.join(out, f["img"] + ".txt"), "w", encoding="utf-8").write(CARTOON.format(
            out=out, img=f["img"], refs="\n".join(refs), setting=SETTING, title=f["title"], scene=f["scene"], labels="\n".join(f["labels"])))
    for f in PHOTOS:
        open(os.path.join(out, f["img"] + ".txt"), "w", encoding="utf-8").write(PHOTO.format(
            out=out, img=f["img"], scene=f["scene"]))
    print("%d prompts -> %s" % (len(FIGS) + len(PHOTOS), out))
