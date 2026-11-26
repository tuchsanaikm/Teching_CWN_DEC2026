#!/usr/bin/env python3
"""รายการภาพของสไลด์ LAB 7 (RTX 4090 · Single GPU, 2 GPU Data Parallelism และ 4 GPU Model Parallelism 2+2 หลัง NGINX)

FIGS   = ภาพการ์ตูนอธิบายสไตล์เดียวกับ LAB 6 (ใช้สัญลักษณ์หุ่นยนต์เต็มตัว = โมเดลเต็ม 1 ใบ และหุ่นยนต์แบ่งครึ่ง = Model Parallelism)
PHOTOS = ภาพถ่าย/3D สมจริง 16:9 สำหรับหน้าปก หน้าคั่น และหน้า Hero (ด้านซ้าย 45% มืดและโล่ง ไม่มีตัวอักษร ป้าย "ภาพจำลอง")
"""
import os, sys

SETTING = (
    "a Thai e-commerce LLM chatbot service (Qwen3-4B-Instruct on vLLM behind NGINX Least Connections) "
    "running on rented single-node RTX 4090 machines"
)

# Reference image pairs inside container multi-account:/workspace/lab7_audit/l6/
DEFAULT_REFS = ["th-architecture.png", "ref-dp-vs-mp-robot.jpg"]

FIGS = [
    {
        "img": "n01-lab-map",
        "refs": ["s01.png"],
        "title": "10 ขั้นของ LAB 7 แบ่งเป็น 5 ส่วน",
        "labels": [
            "A เตรียมระบบ", "ขั้นที่ 1–2",
            "B Load Test", "ขั้นที่ 3",
            "C แทร็ก 1: Data Parallelism", "ขั้นที่ 4–7",
            "D แทร็ก 2: Model Parallelism", "ขั้นที่ 8",
            "E สาธิตและสรุป", "ขั้นที่ 9–10",
            "ทำครบ 10 ขั้น · ห้ามข้ามขั้นที่ 10 ลบเครื่องเช่า",
        ],
        "scene": (
            "Five rounded pastel cards arranged in one clean horizontal row from left to right, connected by short arrows like a roadmap. "
            "Each card has a letter badge (A, B, C, D, E) in a colored circle, a simple flat icon, the part name, and the step range below it. "
            "At the bottom, a rounded light orange warning banner reads the footer text."
        ),
        "steps": [
            "**ส่วน A (ขั้นที่ 1–2)** เช่าเครื่อง RTX 4090 พร้อมกัน 2 เครื่อง (2 GPU และ 4 GPU) ติดตั้ง vLLM, โมเดล Qwen3-4B, NGINX และวัดความเร็วผู้ใช้ 1 คน",
            "**ส่วน B (ขั้นที่ 3)** เขียนตัวยิงโหลดแบบ Streaming และพิสูจน์ความแม่นยำด้วย server จำลอง `fake_llm.py`",
            "**ส่วน C (ขั้นที่ 4–7)** แทร็กที่ 1 บน 2× RTX 4090: วัดทีละคำถาม, Continuous Batching, Data Parallelism 2 GPU, Concurrency Limit, คำตอบสั้น-ยาว และ Replica Failover",
            "**ส่วน D (ขั้นที่ 8)** แทร็กที่ 2 บน 4× RTX 4090: วัด Model Parallelism แบบ 2+2 (Tensor Parallelism = 2) เทียบกับ Data Parallelism",
            "**ส่วน E (ขั้นที่ 9–10)** อัด Trace จริงสร้างไฟล์ GIF ความเร็ว 1×, วาดกราฟสรุป และลบเครื่องเช่าทั้ง 2 เครื่อง",
        ],
    },
    {
        "img": "n09-lab6-vs-lab7-why1vllm",
        "refs": ["th-architecture.png", "ref-dp-vs-mp-robot.jpg"],
        "title": "ทำไม LAB 6 เปิด 4 server ต่อ 1 GPU แต่ LAB 7 เปิด vLLM แค่ 1 ตัว",
        "labels": [
            "LAB 6: ตรวจภาพ (YOLO11s · 19 MB)",
            "งานเตรียมภาพบน CPU เยอะ",
            "เปิด 4 FastAPI server แชร์ 1 GPU",
            "server",
            "GPU 0",
            "โมเดลเล็ก · 4 server ช่วยกันเตรียมภาพและ Micro-batching ป้อน 1 GPU",
            "LAB 7: แชทบอท LLM (Qwen3-4B · 8.06 GB)",
            "จอง VRAM สูงสุด 90% (โมเดล + KV Cache)",
            "เปิด 1 vLLM replica คุม 1 GPU",
            "vLLM :8001",
            "Continuous Batching (max-num-seqs=256)",
            "โมเดลใหญ่กว่า 400 เท่า · vLLM ตัวเดียวจัดคิวและจัดการ VRAM ทั้งใบ",
            "คอขวดต่างกัน · LAB 7 ใช้ 1 vLLM/GPU เพื่อไม่ให้โหลดโมเดลซ้ำหลายชุดจน VRAM ไม่พอ",
        ],
        "scene": (
            "Match the exact airy pastel cartoon style of the attached reference images (pastel blue rounded title banner with yellow spark strokes, bold dark outlines, rounded pastel panels, purple dual-fan GPU cards, cute white-and-blue robot icon INSIDE the GPU card, bold rounded Thai text). "
            "Two large equal side-by-side rounded panels comparing LAB 6 (left) and LAB 7 (right): "
            "LEFT PANEL (soft sky-blue tint) titled 'LAB 6: ตรวจภาพ (YOLO11s · 19 MB)' with a small lilac pill 'งานเตรียมภาพบน CPU เยอะ': "
            "inside, a warm-cream box has top header pill 'เปิด 4 FastAPI server แชร์ 1 GPU' above FOUR small square white boxes with blue gear icons labeled 'server' arranged in a 2x2 grid pointing right into ONE purple dual-fan GPU card labeled 'GPU 0'. Below the cream box, a lilac pill reads 'โมเดลเล็ก · 4 server ช่วยกันเตรียมภาพและ Micro-batching ป้อน 1 GPU'. "
            "RIGHT PANEL (soft mint-green tint) titled 'LAB 7: แชทบอท LLM (Qwen3-4B · 8.06 GB)' with a small lilac pill 'จอง VRAM สูงสุด 90% (โมเดล + KV Cache)': "
            "inside, a warm-cream box has top header pill 'เปิด 1 vLLM replica คุม 1 GPU' above multiple pastel chat bubbles pointing right into ONE white rounded server box with a blue gear icon labeled 'vLLM :8001' (and small tag 'Continuous Batching (max-num-seqs=256)' below it) pointing right into ONE purple dual-fan GPU card labeled 'GPU 0' that displays ONE complete cute white-and-blue robot INSIDE the GPU card (consistent with all other LAB 7 diagrams! Do NOT place the robot outside the GPU). Below the cream box, a lilac pill reads 'โมเดลใหญ่กว่า 400 เท่า · vLLM ตัวเดียวจัดคิวและจัดการ VRAM ทั้งใบ'. "
            "Bottom rounded pastel green banner reads 'คอขวดต่างกัน · LAB 7 ใช้ 1 vLLM/GPU เพื่อไม่ให้โหลดโมเดลซ้ำหลายชุดจน VRAM ไม่พอ'. "
            "No bar charts, no gauges, no prices."
        ),
        "steps": [
            "**LAB 6 (`YOLO11s`, 19 MB):** โมเดลเล็กมาก GPU ตรวจเสร็จไว งานเตรียมภาพบน CPU กินเวลาถึง 56% ของรอบ จึงทดลองเปิด **4 FastAPI server แชร์ 1 GPU** พร้อม Micro-batching เพื่อช่วยกันป้อนงานให้ GPU ทำงานเต็มขึ้น",
            "**LAB 7 (`Qwen3-4B`, 8.06 GB):** โมเดลใหญ่กว่า 400 เท่า และ vLLM ตั้ง `--gpu-memory-utilization 0.90` เพื่อจองพื้นที่ทั้งน้ำหนักโมเดลและ **KV Cache** ไว้ใน GPU 1 ใบ",
            "**1 vLLM replica ต่อ 1 GPU** มีตัวจัดคิว **Continuous Batching** (`--max-num-seqs 256` ในการทดลอง) ภายใน process เดียวและดึงกำลัง RTX 4090 เต็ม 100% (~432 W) อยู่แล้ว",
            "**ไม่เปิด 4 vLLM แชร์ 1 GPU** เพราะจะโหลดน้ำหนักโมเดลซ้ำหลายชุดและแบ่งเสี้ยว KV Cache จนเสี่ยง Out of Memory",
        ],
    },
    {
        "img": "n02-scope-tracks",
        "refs": ["s08-mp4-step.png", "ref-dp-vs-mp-robot.jpg"],
        "title": "ขอบเขตของ LAB 7: 2 เครื่องแยกกันทดลอง (ไม่ใช่ Multi-Node)",
        "labels": [
            "แทร็กที่ 1 · เครื่อง 2 GPU",
            "1 โหนด × 2× RTX 4090",
            "โมเดล 1 (GPU 0)",
            "โมเดล 2 (GPU 1)",
            "Data Parallelism",
            "GPU ละ 1 โมเดลเต็ม",
            "วัดแบบที่ 1, 2, 3 · Cap · Failover",
            "แทร็กที่ 2 · เครื่อง 4 GPU",
            "1 โหนด × 4× RTX 4090",
            "คู่ที่ 1 · โมเดล 1 (GPU 0+1)",
            "คู่ที่ 2 · โมเดล 2 (GPU 2+3)",
            "Model Parallelism 2+2",
            "2 GPU ช่วยกันถือ 1 โมเดล (2 คู่ = 2 โมเดล)",
            "วัดแบบที่ 4 เทียบกับแทร็กที่ 1",
            "แยกเครื่องวัดอิสระ · ไม่มีสายเน็ตคั่นระหว่าง NGINX กับ GPU",
        ],
        "scene": (
            "Match the exact airy pastel cartoon style of the attached reference images (pastel blue rounded title banner with yellow spark strokes, bold dark outlines, rounded pastel panels, open wooden-door NGINX gateway, purple GPU cards, cute white-and-blue robot icon). "
            "Do NOT draw any construction worker or hardhat. "
            "Two large equal side-by-side rounded server chassis separated by a clean vertical dashed gap (NO cable or arrow connecting the two machines): "
            "LEFT BOX (soft sky-blue tint) titled 'แทร็กที่ 1 · เครื่อง 2 GPU' with pill badge '1 โหนด × 2× RTX 4090': "
            "inside the white server chassis sits an open wooden-door NGINX gateway on the left with TWO separate purple arrows branching right to TWO stacked rounded dashed-outline group capsules: "
            "Top capsule (soft blue dashed border) labeled 'โมเดล 1 (GPU 0)' containing ONE purple GPU card with ONE complete cute robot inside; "
            "Bottom capsule (soft blue dashed border) labeled 'โมเดล 2 (GPU 1)' containing ONE purple GPU card with ONE complete cute robot inside. "
            "Below the chassis: bold label 'Data Parallelism', subtitle 'GPU ละ 1 โมเดลเต็ม', and white pill 'วัดแบบที่ 1, 2, 3 · Cap · Failover'. "
            "RIGHT BOX (soft peach-amber tint) titled 'แทร็กที่ 2 · เครื่อง 4 GPU' with pill badge '1 โหนด × 4× RTX 4090': "
            "inside the white server chassis sits an open wooden-door NGINX gateway on the left with TWO separate purple arrows branching right to TWO VERY CLEAR, DISTINCT rounded dashed-outline grouping boxes stacked vertically with generous vertical gap between them: "
            "TOP GROUP BOX (bold orange dashed rounded border with soft cream fill) with top tag 'คู่ที่ 1 · โมเดล 1 (GPU 0+1)' tightly grouping TWO side-by-side purple GPU cards linked by a bright orange double-headed arrow — left GPU holds upper/head half of ONE cute robot, right GPU holds lower/legs half of that SAME robot! "
            "BOTTOM GROUP BOX (bold teal-purple dashed rounded border with soft lavender fill) with top tag 'คู่ที่ 2 · โมเดล 2 (GPU 2+3)' tightly grouping TWO side-by-side purple GPU cards linked by a bright orange double-headed arrow — left GPU holds upper/head half of a SECOND cute robot, right GPU holds lower/legs half of that SAME robot! "
            "Below the chassis: bold label 'Model Parallelism 2+2', subtitle '2 GPU ช่วยกันถือ 1 โมเดล (2 คู่ = 2 โมเดล)', and white pill 'วัดแบบที่ 4 เทียบกับแทร็กที่ 1'. "
            "Bottom rounded pastel green banner reads 'แยกเครื่องวัดอิสระ · ไม่มีสายเน็ตคั่นระหว่าง NGINX กับ GPU'. "
            "No bar charts, no gauges, no prices, no construction worker."
        ),
        "steps": [
            "**ต่อยอดสูตรชนะจาก LAB 6** (Multi-GPU + Batching + NGINX `least_conn`) มาใช้กับแชทบอท LLM แบบ Streaming",
            "**แทร็กที่ 1 (`vapp-lab7-dp2`)** 1 โหนด × 2× RTX 4090: GPU แต่ละใบถือโมเดลครบทั้งก้อน (หุ่นยนต์เต็มตัวใบละ 1 ตัว) วัดตั้งแต่แบบที่ 1–3, Cap Sweep, คำตอบสั้น-ยาว และ Failover",
            "**แทร็กที่ 2 (`vapp-lab7-mp4`)** 1 โหนด × 4× RTX 4090: จับคู่ 2 GPU แบ่งถือ 1 โมเดล (หุ่นยนต์แบ่งครึ่ง 2 หน่วย = 2+2) วัดแบบที่ 4 เพื่อเทียบกับแทร็กที่ 1",
            "**ทั้ง 2 เครื่องแยกกันอิสระ** ไม่ใช่คลัสเตอร์ Multi-Node และตัวยิงโหลดรันภายในเครื่องเดียวกับ NGINX",
        ],
    },
    {
        "img": "n03-arch-rtx4090",
        "refs": ["th-architecture.png", "ref-dp-vs-mp-robot.jpg"],
        "title": "System Architecture ของ LAB 7 (แทร็ก Data Parallelism 2 GPU)",
        "labels": [
            "เครื่องเช่า 1 เครื่อง: RTX 4090 2 ใบ",
            "ผู้ใช้ N คน",
            "คำถาม + API Key",
            "NGINX (container)",
            "พอร์ต 8080",
            "ตัวยิงโหลด: ผู้ใช้จำลอง",
            "GPU 0",
            "GPU 1",
            "vLLM :8001",
            "vLLM :8002",
            "ผู้ใช้เห็นที่อยู่เดียว · ข้างหลังเพิ่ม vLLM และ GPU ได้",
        ],
        "scene": (
            "Follow the EXACT visual layout and composition of the attached LAB 6 System Architecture diagram (th-architecture.png) so learners can compare LAB 6 and LAB 7 side by side effortlessly, replacing LAB 6's 4-servers-per-GPU with LAB 7's 1-vLLM-per-GPU and placing a complete cute white-and-blue robot inside each GPU card! "
            "Far left outside the blue server box: three cute pastel user silhouettes labeled 'ผู้ใช้ N คน' sending a purple arrow carrying a white CHAT SPEECH BUBBLE with three dots (...) and a tiny golden key icon (STRICTLY a speech bubble for text chat, NEVER a mountain/photo/landscape picture icon!) labeled 'คำถาม + API Key' into the server box. "
            "Large light-blue rounded outer server box with white pill header at top center reading 'เครื่องเช่า 1 เครื่อง: RTX 4090 2 ใบ' with yellow spark strokes. "
            "Inside left of the blue box: the exact open wooden-door gateway icon labeled 'NGINX (container)' with an orange pill below reading 'พอร์ต 8080'. "
            "Below the gateway inside the blue box: a soft-lilac rounded card with a yellow robotic arm icon labeled 'ตัวยิงโหลด: ผู้ใช้จำลอง' and a dashed purple arrow pointing UP into the orange port pill. "
            "Inside right of the blue box: TWO stacked warm-cream rounded panels. "
            "Top panel has a pastel green pill header 'GPU 0': a clean rounded white server box with blue gear icon labeled 'vLLM :8001' pointing right into a purple dual-fan GPU card that displays ONE complete cute white-and-blue robot face/body on it (meaning full model on 1 GPU). "
            "Bottom panel has a pastel green pill header 'GPU 1': a clean rounded white server box with blue gear icon labeled 'vLLM :8002' pointing right into a second purple dual-fan GPU card that displays ONE complete cute white-and-blue robot face/body on it. "
            "Two crisp single-direction purple arrows branch cleanly from the right side of the NGINX gateway into 'vLLM :8001' and 'vLLM :8002'. Do NOT draw confusing dotted return loops under the GPUs. "
            "Bottom pastel green rounded banner reads 'ผู้ใช้เห็นที่อยู่เดียว · ข้างหลังเพิ่ม vLLM และ GPU ได้'. "
            "No bar charts, no gauges, no prices."
        ),
        "steps": [
            "**ภาพคู่ขนาน 1-ต่อ-1 กับ LAB 6:** เปลี่ยนจาก 4 FastAPI server ต่อ 1 GPU เป็น **1 vLLM replica ต่อ 1 GPU** (หุ่นยนต์เต็มตัว 1 ตัวต่อการ์ด 1 ใบ)",
            "**NGINX Container (พอร์ต 8080)** ทำหน้าที่เป็นประตูเดียว ตรวจ Bearer API key ปิด buffering สำหรับ Streaming และแจกงานแบบ `least_conn`",
            "**vLLM Replica (`127.0.0.1:8001–8002`)** ครอบโมเดล `Qwen3-4B-Instruct-2507` ทำ Continuous Batching และรับเฉพาะคำขอจากภายในเครื่อง",
            "**ตัวยิงโหลด (`loadgen.py`)** รันในเครื่องเดียวกัน ยิงเข้าพอร์ต 8080 ผ่านทางเดียวกับผู้ใช้จริง พร้อมเก็บค่า GPU, CPU และคิว vLLM ทุกวินาที",
        ],
    },
    {
        "img": "n04-dp-vs-mp-robot",
        "refs": ["ref-dp-vs-mp-robot.jpg", "th-architecture.png"],
        "title": "มี GPU หลายใบในงาน LLM Serving: แบ่งงานแบบไหนดี",
        "labels": [
            "โจทย์คืออะไร?",
            "อยากรับคำขอพร้อมกันเยอะขึ้น",
            "โมเดลเกิน 1 ใบ หรืออยากลดเวลาตอบต่อคำขอ",
            "Data Parallelism",
            "GPU ละ 1 โมเดลเต็ม · แยกกันตอบคนละคำถาม",
            "ไม่ต้องซิงค์ข้าม GPU · ขยายความจุได้ตามจำนวนใบ",
            "Model Parallelism",
            "โมเดลเดียวแบ่งลง 2 GPU · ช่วยกันตอบคำถามเดียวกัน",
            "ซิงค์ข้าม PCIe (Tensor Parallelism)",
            "อาจลดเวลาตอบต่อคำขอ แต่มีต้นทุนซิงค์ · ต้องวัดเทียบ",
        ],
        "scene": (
            "Follow the EXACT clear visual storytelling and cute robot-on-GPU metaphor of the attached reference image (ref-dp-vs-mp-robot.jpg), adapted cleanly for LAB 7 LLM Serving! "
            "Top pastel blue rounded title banner reads 'มี GPU หลายใบในงาน LLM Serving: แบ่งงานแบบไหนดี'. "
            "Directly below title: a clean white rounded box with dark outline reading 'โจทย์คืออะไร?' (NO extra door icon beside it!) branching left and right with clean dark arrows to two pastel pills: "
            "Left pill (light blue) 'อยากรับคำขอพร้อมกันเยอะขึ้น' pointing down to LEFT PANEL; "
            "Right pill (light orange) 'โมเดลเกิน 1 ใบ หรืออยากลดเวลาตอบต่อคำขอ' pointing down to RIGHT PANEL. "
            "LEFT PANEL (soft sky-blue rounded card) titled bold 'Data Parallelism': "
            "shows TWO blue-purple GPU cards side by side with yellow spark marks on outer edges — LEFT GPU holds ONE complete cute white-and-blue robot, RIGHT GPU holds ONE complete cute white-and-blue robot (NO link between the two GPUs). "
            "Below GPUs: bold Thai line 'GPU ละ 1 โมเดลเต็ม · แยกกันตอบคนละคำถาม' and rounded blue pill 'ไม่ต้องซิงค์ข้าม GPU · ขยายความจุได้ตามจำนวนใบ'. "
            "RIGHT PANEL (soft peach-orange rounded card) titled bold 'Model Parallelism': "
            "shows TWO blue-purple GPU cards side by side with yellow spark marks — LEFT GPU holds the TOP HALF (head & torso) of ONE cute white-and-blue robot, RIGHT GPU holds the BOTTOM HALF (legs) of that SAME robot as a friendly visual symbol of 1 model split across 2 GPUs, with a crisp orange double-headed arrow between the two GPUs labeled 'ซิงค์ข้าม PCIe (Tensor Parallelism)'. "
            "Below GPUs: bold Thai line 'โมเดลเดียวแบ่งลง 2 GPU · ช่วยกันตอบคำถามเดียวกัน' and rounded orange pill 'อาจลดเวลาตอบต่อคำขอ แต่มีต้นทุนซิงค์ · ต้องวัดเทียบ'. "
            "No bar charts, no gauges, no prices, no cursor icons, no door icon."
        ),
        "steps": [
            "**Data Parallelism (สัญลักษณ์: หุ่นยนต์เต็มตัวใบละ 1 ตัว):** แต่ละ GPU ถือโมเดลครบทั้งก้อน แยกกันตอบคำถามคนละข้อ ไม่ต้องคุยข้ามการ์ดจอ เหมาะเมื่อโมเดลใส่ใน 1 GPU พอและต้องการรับคำขอพร้อมกันจำนวนมาก",
            "**Model Parallelism (สัญลักษณ์: หุ่นยนต์ 1 ตัวแบ่งลง 2 ใบ):** จับคู่ GPU 2 ใบช่วยกันถือ 1 โมเดลเพื่อรวม VRAM สำหรับโมเดลขนาดใหญ่ หรือช่วยกันคำนวณเพื่อลดเวลาตอบต่อคำขอเดียว",
            "**ราคาที่ต้องแลก (ต้องวัดเทียบจริง):** ในแบบ Tensor Parallelism ทั้ง 2 GPU ต้องสื่อสารผลข้าม PCIe ระหว่างกันตลอดการสร้าง Token ซึ่งเราจะวัดเทียบจริงในขั้นที่ 8",
        ],
    },
    {
        "img": "n08-4designs-llm",
        "refs": ["n02-4designs-1node.jpg", "ref-dp-vs-mp-robot.jpg"],
        "title": "4 การออกแบบที่วัดเทียบกันใน LAB 7 บน RTX 4090",
        "labels": [
            "แบบที่ 1 · dp1_seq",
            "เครื่อง 1 · GPU 1 ใบ · ทีละ 1 คำถาม",
            "แบบที่ 2 · dp1_cb",
            "เครื่อง 1 · GPU 1 ใบ · Continuous Batching",
            "แบบที่ 3 · dp2_cb",
            "เครื่อง 1 · GPU 2 ใบ · Data Parallelism",
            "แบบที่ 4 · mp4_cb",
            "เครื่อง 2 · GPU 4 ใบ · Model Parallelism 2+2",
            "NGINX",
            "vLLM",
            "ทุกแบบใช้ Qwen3-4B (vLLM) และวัดด้วยเกณฑ์ SLO เดียวกัน",
        ],
        "scene": (
            "Follow the EXACT uniform 2x2 grid composition of the attached LAB 6 4-designs diagram (n02-4designs-1node.jpg) AND use the exact complete-robot vs split-half-robot metaphor from ref-dp-vs-mp-robot.jpg consistently in all 4 panels! "
            "Every single one of the 4 rounded pastel panels uses the EXACT same clean left-to-right flow (chat bubbles -> NGINX/vLLM -> GPU): "
            "TOP-LEFT PANEL (soft lavender tint) header 'แบบที่ 1 · dp1_seq': 1 single chat bubble -> 1 small white box 'vLLM' -> 1 purple GPU card containing ONE complete cute robot. Subtitle at bottom of panel: 'เครื่อง 1 · GPU 1 ใบ · ทีละ 1 คำถาม'. "
            "TOP-RIGHT PANEL (soft sky-blue tint) header 'แบบที่ 2 · dp1_cb': 4 parallel chat bubbles -> 1 small white box 'vLLM' -> 1 purple GPU card containing ONE complete cute robot. Subtitle: 'เครื่อง 1 · GPU 1 ใบ · Continuous Batching'. "
            "BOTTOM-LEFT PANEL (soft mint-green tint) header 'แบบที่ 3 · dp2_cb': chat bubbles -> small open-door gateway 'NGINX' branching to TWO stacked purple GPU cards, EACH holding ONE complete cute robot (2 complete robots total). Subtitle: 'เครื่อง 1 · GPU 2 ใบ · Data Parallelism'. "
            "BOTTOM-RIGHT PANEL (soft peach-amber tint) header 'แบบที่ 4 · mp4_cb': chat bubbles -> small open-door gateway 'NGINX' branching to TWO stacked pairs of purple GPU cards (4 GPUs total), where EACH pair holds ONE cute robot split in half (top/head half on left GPU, bottom/legs half on right GPU, linked by a tiny orange double arrow). Subtitle: 'เครื่อง 2 · GPU 4 ใบ · Model Parallelism 2+2'. "
            "Bottom pastel green rounded banner reads 'ทุกแบบใช้ Qwen3-4B (vLLM) และวัดด้วยเกณฑ์ SLO เดียวกัน'. "
            "No bar charts, no gauges, no speed numbers, no prices."
        ),
        "steps": [
            "**แบบที่ 1 (`dp1_seq`)** เครื่อง 1 · GPU 1 ใบ ตอบทีละ 1 คำถาม (`cap=1`) เป็น Baseline",
            "**แบบที่ 2 (`dp1_cb`)** เครื่อง 1 · GPU 1 ใบเดิม แต่เปิด **Continuous Batching** (`cap=256`)",
            "**แบบที่ 3 (`dp2_cb`)** เครื่อง 1 · GPU 2 ใบแบบ **Data Parallelism** (หุ่นยนต์เต็มตัวใบละ 1 ตัว) หลัง NGINX `least_conn`",
            "**แบบที่ 4 (`mp4_cb`)** เครื่อง 2 · GPU 4 ใบแบบ **Model Parallelism 2+2** (หุ่นยนต์แบ่งครึ่งคู่ละ 1 ตัว รวม 2 หน่วย) หลัง NGINX `least_conn`",
        ],
    },
    {
        "img": "s04-dp1-step",
        "refs": ["s06.png", "ref-dp-vs-mp-robot.jpg"],
        "title": "ขั้นที่ 4: วัดแบบที่ 1 (ทีละคำถาม) และแบบที่ 2 (Continuous Batching)",
        "labels": [
            "NGINX",
            "พอร์ต 8080",
            "ตัวยิงโหลด",
            "GPU 0",
            "GPU 1",
            "vLLM :8001",
            "แบบ 1: max-num-seqs=1 | แบบ 2: 256",
            "ยังไม่ใช้",
            "ผลชื่อ dp1_seq & dp1_cb",
            "Continuous Batching ช่วยรับคำขอพร้อมกันเพิ่มกี่เท่าบน GPU ใบเดิม",
            "GPU 1 ใบ · vLLM 1 ตัว · โมเดลเต็มทั้งก้อน",
        ],
        "scene": (
            "Follow the EXACT split-panel step-diagram layout of the attached LAB 6 reference image (s06.png): a large light-blue rounded host box on the left (68% width) and a crisp white rounded result box with dark outline on the right (28% width), plus pastel blue top title banner and pastel green bottom summary banner. "
            "LEFT HOST BOX: on the left side sits the open wooden-door gateway labeled 'NGINX' with orange pill 'พอร์ต 8080' below it, and below that a lilac card with a yellow robot arm labeled 'ตัวยิงโหลด' pointing a dashed purple arrow UP into the port pill. "
            "On the right side inside the host box are TWO stacked panels: "
            "TOP PANEL (warm cream, bright active) has lilac pill header 'แบบ 1: max-num-seqs=1 | แบบ 2: 256', a white server box with blue gear icon labeled 'vLLM :8001' connected by a purple arrow from NGINX and pointing right into a purple dual-fan GPU card labeled 'GPU 0' holding ONE complete cute white-and-blue robot inside! "
            "BOTTOM PANEL (soft gray, faded/inactive with dashed outline) has faded gray GPU card silhouette labeled 'GPU 1' and centered gray pill 'ยังไม่ใช้' (NO arrow from NGINX to GPU 1). "
            "RIGHT WHITE RESULT BOX: top pastel-yellow pill with sparks reading 'ผลชื่อ dp1_seq & dp1_cb', middle clean illustration of 1 small blue chat bubble with an arrow to 4 colorful chat bubbles (NOT a bar chart!), and bottom pastel-lilac pill reading 'Continuous Batching ช่วยรับคำขอพร้อมกันเพิ่มกี่เท่าบน GPU ใบเดิม'. "
            "Bottom pastel green rounded banner reads 'GPU 1 ใบ · vLLM 1 ตัว · โมเดลเต็มทั้งก้อน'. "
            "No numbers on charts, no prices."
        ),
        "steps": [
            "**ใช้ GPU ใบเดียว (`GPU 0`)** ส่วน `GPU 1` ยังไม่เปิดใช้งาน เพื่อให้เห็นผลของ Continuous Batching อย่างชัดเจนโดยยังไม่เพิ่มฮาร์ดแวร์",
            "**รอบแรก (`dp1_seq`)** ตั้ง `--max-num-seqs 1` บังคับให้ vLLM ตอบจบทีละ 1 คำถามเพื่อสร้าง Baseline",
            "**รอบสอง (`dp1_cb`)** เปลี่ยนแค่ค่าเป็น `--max-num-seqs 256` บน GPU ใบเดิม แล้ววัดเทียบว่าความจุและ Throughput เพิ่มขึ้นกี่เท่า",
        ],
    },
    {
        "img": "s05-dp2-step",
        "refs": ["s09.png", "ref-dp-vs-mp-robot.jpg"],
        "title": "ขั้นที่ 5: วัดแบบที่ 3 Data Parallelism (GPU 2 ใบหลัง NGINX)",
        "labels": [
            "Least Connections",
            "NGINX",
            "พอร์ต 8080",
            "ตัวยิงโหลด",
            "GPU 0",
            "GPU 1",
            "vLLM :8001",
            "vLLM :8002",
            "ผลชื่อ dp2_cb",
            "ความจุของ 2 GPU ได้กี่เท่าของ 1 GPU",
            "GPU 2 ใบ · ใบละ 1 โมเดลเต็ม · Continuous Batching",
        ],
        "scene": (
            "Follow the EXACT split-panel step-diagram layout of the attached LAB 6 reference image (s09.png) so learners see the 1-to-1 parallel with LAB 6 Step 9! "
            "LEFT HOST BOX (68% width, light blue rounded frame): on the left side sits a lilac pill 'Least Connections' above the open wooden-door gateway 'NGINX' with orange pill 'พอร์ต 8080' below it, and a lilac card with a yellow robot arm labeled 'ตัวยิงโหลด' pointing a dashed purple arrow UP into the port pill. "
            "On the right side inside the host box are TWO bright active warm-cream panels stacked vertically: "
            "TOP PANEL has green pill 'GPU 0': white server box 'vLLM :8001' pointing right into a purple dual-fan GPU card holding ONE complete cute white-and-blue robot inside! "
            "BOTTOM PANEL has green pill 'GPU 1': white server box 'vLLM :8002' pointing right into a second purple dual-fan GPU card holding ONE complete cute white-and-blue robot inside! "
            "Two crisp purple arrows route from NGINX to 'vLLM :8001' and 'vLLM :8002'. "
            "RIGHT WHITE RESULT BOX (28% width, dark outline): top pastel-yellow pill with sparks reading 'ผลชื่อ dp2_cb', middle cute simple rising blocks illustration (4 pastel rounded steps going up, NO numbers/axes, just like s09.png!), and bottom pastel-lilac pill reading 'ความจุของ 2 GPU ได้กี่เท่าของ 1 GPU'. "
            "Bottom pastel green rounded banner reads 'GPU 2 ใบ · ใบละ 1 โมเดลเต็ม · Continuous Batching'. "
            "No prices, no extra words."
        ),
        "steps": [
            "**เปิด `GPU 1` เพิ่มเป็น replica ที่ 2 (`vLLM :8002`)** ถือโมเดลเต็มอีก 1 ชุดเหมือนกันทุกประการ",
            "**NGINX `least_conn`** กระจายคำถามให้ `vLLM :8001` และ `vLLM :8002` ตามจำนวนคำถามที่กำลังรันค้างอยู่",
            "**เป้าหมายของการวัด (`dp2_cb`)** คือพิสูจน์ว่า GPU 2 ใบแบบ Data Parallelism ขยายความจุได้ใกล้ 2.0× ของ 1 GPU จริงหรือไม่",
        ],
    },
    {
        "img": "s08-mp4-step",
        "refs": ["s09.png", "ref-dp-vs-mp-robot.jpg"],
        "title": "ขั้นที่ 8: วัดแบบที่ 4 Model Parallelism 2+2 (GPU 4 ใบหลัง NGINX)",
        "labels": [
            "Least Connections",
            "NGINX",
            "พอร์ต 8080",
            "ตัวยิงโหลด",
            "หน่วยที่ 1 (GPU 0 + GPU 1)",
            "หน่วยที่ 2 (GPU 2 + GPU 3)",
            "vLLM :8001",
            "vLLM :8002",
            "ผลชื่อ mp4_cb",
            "เร็วกว่าต่อ 1 คนไหม และความจุเทียบ 2 GPU เป็นอย่างไร",
            "GPU 4 ใบ (แบ่ง 2+2) · หน่วยละ 1 โมเดลแบ่งครึ่ง · NGINX",
        ],
        "scene": (
            "Follow the EXACT split-panel step-diagram layout of the attached LAB 6 reference image (s09.png) so it matches s05-dp2-step 1-to-1, changing ONLY the GPU panels from 1 full-robot GPU per replica to 2 half-robot GPUs per replica! "
            "LEFT HOST BOX (68% width, light blue rounded frame): on the left side sits a lilac pill 'Least Connections' above the open wooden-door gateway 'NGINX' with orange pill 'พอร์ต 8080' below it, and a lilac card with a yellow robot arm labeled 'ตัวยิงโหลด' pointing a dashed purple arrow UP into the port pill. "
            "On the right side inside the host box are TWO bright active warm-cream panels stacked vertically: "
            "TOP PANEL has peach-orange pill 'หน่วยที่ 1 (GPU 0 + GPU 1)': white server box 'vLLM :8001' pointing right into TWO side-by-side purple GPU cards holding ONE split cute white-and-blue robot (head/upper half on left GPU, legs/lower half on right GPU, linked by a tiny orange double arrow). "
            "BOTTOM PANEL has peach-orange pill 'หน่วยที่ 2 (GPU 2 + GPU 3)': white server box 'vLLM :8002' pointing right into TWO side-by-side purple GPU cards holding ONE split cute white-and-blue robot (head/upper half on left GPU, legs/lower half on right GPU, linked by a tiny orange double arrow). "
            "Two crisp purple arrows route from NGINX to 'vLLM :8001' and 'vLLM :8002'. "
            "RIGHT WHITE RESULT BOX (28% width, dark outline): top pastel-yellow pill with sparks reading 'ผลชื่อ mp4_cb', middle cute simple balance-scale icon comparing a fast lightning bolt vs a group of users (NO numbers/charts), and bottom pastel-lilac pill reading 'เร็วกว่าต่อ 1 คนไหม และความจุเทียบ 2 GPU เป็นอย่างไร'. "
            "Bottom pastel green rounded banner reads 'GPU 4 ใบ (แบ่ง 2+2) · หน่วยละ 1 โมเดลแบ่งครึ่ง · NGINX'. "
            "No prices, no extra words."
        ),
        "steps": [
            "**ย้ายไปทดลองบนเครื่องที่ 2 (`4× RTX 4090`)** จัดกลุ่มเป็น 2 หน่วย (`GPU 0+1` และ `GPU 2+3`) หน่วยละ 1 vLLM replica (`--tensor-parallel-size 2`)",
            "**NGINX `least_conn`** ยังทำหน้าที่ประตูเดียวที่พอร์ต 8080 เหมือนขั้นที่ 5 ทุกประการ แจกงานให้ 2 หน่วยอย่างสมดุล",
            "**เป้าหมายของการวัด (`mp4_cb`)** คือเทียบตรงๆ กับ `dp2_cb` ทั้งความเร็วผู้ใช้ 1 คน และความจุเมื่อผู้ใช้หลายร้อยคนพร้อมกัน",
        ],
    },
    {
        "img": "n05-mp-zoom",
        "refs": ["ref-dp-vs-mp-robot.jpg", "th-architecture.png"],
        "title": "ซูมข้างใน 1 หน่วย Model Parallelism (Tensor Parallelism = 2)",
        "labels": [
            "คำถาม 1 ข้อ",
            "vLLM 1 replica (TP=2)",
            "GPU 0",
            "GPU 1",
            "แบ่งส่วนน้ำหนักของแต่ละ Layer",
            "สื่อสารผลระหว่าง GPU ผ่าน PCIe",
            "ส่งคำตอบกลับผู้ใช้",
            "2 GPU ช่วยกันคำนวณพร้อมกัน · อาจลดเวลาตอบต่อคำขอ แต่มีต้นทุนสื่อสารข้าม PCIe (ต้องวัดเทียบ)",
        ],
        "scene": (
            "Match the exact airy pastel cartoon style of the attached reference images (pastel blue top title banner with sparks, bold dark outlines, soft warm-peach unit frame, purple/blue GPU cards, cute split white-and-blue robot symbol, bold rounded Thai text). "
            "CRITICAL LAYOUT TO AVOID PIPELINE MISCONCEPTION: "
            "Place ONE white rounded server box with blue gear icon at the TOP CENTER of the soft-peach unit box labeled 'vLLM 1 replica (TP=2)'. "
            "From the far left, a blue chat bubble labeled 'คำถาม 1 ข้อ' points right directly into the left side of 'vLLM 1 replica (TP=2)'. "
            "From the right side of 'vLLM 1 replica (TP=2)', a green arrow points right to a green chat bubble labeled 'ส่งคำตอบกลับผู้ใช้'. "
            "From the BOTTOM of 'vLLM 1 replica (TP=2)', TWO symmetrical purple double-headed arrows branch simultaneously down-left into 'GPU 0' and down-right into 'GPU 1' (clearly showing BOTH GPUs compute in PARALLEL for the same request — NOT GPU 0 passing sequentially into GPU 1!). "
            "Inside the peach unit box sit TWO equal purple GPU cards side by side: "
            "LEFT GPU card labeled 'GPU 0' holds the upper half of ONE cute white-and-blue robot (as a visual symbol of a split model) with a single clean white pill below it reading 'แบ่งส่วนน้ำหนักของแต่ละ Layer'. "
            "RIGHT GPU card labeled 'GPU 1' holds the lower half of that SAME robot with a single clean white pill below it reading 'แบ่งส่วนน้ำหนักของแต่ละ Layer'. "
            "Between GPU 0 and GPU 1: a bold orange double-headed horizontal arrow with a clean peach pill above it reading 'สื่อสารผลระหว่าง GPU ผ่าน PCIe'. "
            "Bottom pastel amber rounded banner reads '2 GPU ช่วยกันคำนวณพร้อมกัน · อาจลดเวลาตอบต่อคำขอ แต่มีต้นทุนสื่อสารข้าม PCIe (ต้องวัดเทียบ)'. "
            "No bar charts, no gauges, no prices."
        ),
        "steps": [
            "**Tensor Parallelism = 2 (`vLLM 1 replica` คุม 2 GPU พร้อมกัน):** แบ่ง tensor/น้ำหนักบางส่วนของแต่ละ Layer กระจายลง GPU 0 และ GPU 1 เพื่อช่วยกันคำนวณคำถามเดียวกันแบบขนาน",
            "**ทำไมถึงช่วยลดเวลาตอบต่อคำขอเดียวได้:** GPU ทั้ง 2 ใบช่วยกันอ่านน้ำหนักและคำนวณในเวลาเดียวกัน จึงช่วยลด latency ต่อคำขอเมื่อผู้ใช้ยังไม่เยอะ (หรือใช้เมื่อโมเดลใหญ่เกิน VRAM 1 ใบ)",
            "**ต้นทุนที่ต้องวัดเทียบจริง:** ระหว่างสร้างแต่ละ Token ทั้ง 2 GPU ต้องสื่อสารรวมผลข้าม **PCIe 4.0** (AllReduce) ทำให้เมื่อมีคำขอพร้อมกันหลายร้อยข้อ ประสิทธิภาพต่อ GPU อาจลดลงอย่างมาก",
        ],
    },
    {
        "img": "n06-failover-single-node",
        "refs": ["th-architecture.png"],
        "title": "Replica ล่มกลางการ Streaming บน 1 โหนด (2× RTX 4090)",
        "labels": [
            "NGINX (Least Connections)",
            "gpu0 ทำงานปกติ",
            "gpu1 ล่มกลางทาง (SIGKILL)",
            "1 คำตอบที่กำลังไหล: ขาดกลางประโยค ส่งต่อไม่ได้",
            "2 คำถามใหม่: NGINX โยกไป gpu0 ทันที (error 0)",
            "ฝั่งผู้ใช้: ถามซ้ำเมื่อคำตอบขาด (Client Retry)",
            "ฝั่ง NGINX: พักตัวที่ล่มอัตโนมัติ (max_fails=1, fail_timeout=30s)",
        ],
        "scene": (
            "A clean flat cartoon diagram with a central green NGINX box ('NGINX (Least Connections)'). "
            "On the right are two stacked boxes inside one host frame: top box is bright green/purple labeled 'gpu0 ทำงานปกติ' with a happy robot and glowing purple GPU; bottom box is grayed out with a big red X and small cartoon smoke cloud labeled 'gpu1 ล่มกลางทาง (SIGKILL)'."
        ),
        "steps": [
            "**คำตอบที่กำลัง Streaming บน `gpu1`** ถูกตัดกลางทาง (`ClientPayloadError`) เพราะผู้ใช้ได้รับ Token ไปแล้วบางส่วน NGINX จึงต่อกลางประโยคบนตัวอื่นไม่ได้",
            "**คำถามใหม่ทั้งหมดหลังล่ม** ถูก NGINX โยกไปที่ `gpu0` ทันทีด้วย `max_fails=1 fail_timeout=30s` และ `proxy_next_upstream ... non_idempotent`",
            "**ฝั่งแอปผู้ใช้** ต้องมีกลไก Client Retry สำหรับกรณีสตรีมขาด และระบบต้องเผื่อความจุรองรับกรณีเหลือ GPU เพียงครึ่งเดียว",
        ],
    },
    {
        "img": "n07-loadtest-loop",
        "refs": ["th-architecture.png"],
        "title": "Load Test แบบ Streaming: ผู้ใช้จำลองแบบ Closed Loop บนโหนดเดียว",
        "labels": [
            "ผู้ใช้จำลอง 1 คน (Closed Loop)",
            "1 ส่งคำถาม",
            "2 จับเวลา Token แรก (TTFT)",
            "3 รับ Token จนคำตอบจบ",
            "4 ถามข้อใหม่ทันที",
            "N คนทำพร้อมกัน",
            "NGINX (:8080) → vLLM",
            "วัด 1 ระดับ = 30 วินาที · อุ่นเครื่อง 10 วินาที · นับผล 20 วินาที",
            "ตัวยิงโหลดรันบนโหนดเดียวกับ NGINX จึงไม่มีความช้าของอินเทอร์เน็ตปน",
        ],
        "scene": (
            "A clean two-panel flat cartoon diagram showing closed-loop streaming load generation on the same node as NGINX."
        ),
        "steps": [
            "**Closed Loop (ไม่มี Think Time):** ผู้ใช้จำลองแต่ละคนส่งคำถาม รออ่านสตรีมจนจบ แล้วถามข้อใหม่ทันที จึงมีคำถามค้างในระบบเท่ากับ `N` ตลอดเวลา",
            "**จับเวลา 3 จุดในคำถามเดียว:** เวลาส่ง → เวลา Token แรก (**TTFT**) → เวลา Token สุดท้าย (**ความเร็วต่อผู้ใช้**)",
            "**ช่วงอุ่นเครื่อง 10 วินาทีไม่นับผล:** ปล่อยให้ Batch เต็มและระบบนิ่งก่อน แล้วนับผลจริงในช่วง 20 วินาทีหลัง",
            "**แยกหลาย Process:** แบ่งผู้ใช้จำลองหลาย process บนโหนดเดียวกับ NGINX เพื่อไม่ให้ตัวยิงโหลดเป็นตัวถ่วงเสียเอง",
        ],
    },
]

PHOTOS = [
    {
        "img": "s01-cover",
        "scene": (
            "Cinematic photorealistic wide shot of a sleek modern AI compute server chassis open on the right half of the frame, "
            "revealing glowing high-end RTX graphics cards with subtle cyan and warm amber LED rim lights and delicate light streams "
            "representing flowing tokens in a dark moody data lab. The entire left 45 percent of the image is deep dark shadow and "
            "clean empty negative space for white headline text."
        ),
    },
    {
        "img": "s02-theory",
        "scene": (
            "Cinematic moody 3D photorealistic studio scene: on the right half, luminous cyan and warm gold optical fiber strands "
            "carrying pulsing light beads (symbolizing streaming tokens) flow neatly through a dark sleek prism gateway against a deep "
            "navy-black background. The entire left 45 percent is deep dark empty shadow for slide titles."
        ),
    },
    {
        "img": "s03-lab",
        "scene": (
            "Photorealistic dark moody close-up inside a high-performance workstation on the right half of the frame: a clean row of "
            "matte-black GPU cards with crisp teal and warm orange accent lighting, faint heat-sink metal texture, dramatic studio rim "
            "light. The entire left 45 percent is deep dark shadow and empty space for white text."
        ),
    },
    {
        "img": "s04-summary",
        "scene": (
            "Cinematic architectural photography at dusk on the right half: sleek modern illuminated glass server towers reflecting "
            "calm teal and amber lights over dark still water, crisp contrast and serene sense of completion. The entire left 45 "
            "percent is deep dark empty sky/shadow for slide headline text."
        ),
    },
    {
        "img": "h01-cb",
        "scene": (
            "Cinematic dark 3D render metaphor for Continuous Batching: on the right half, a single thin beam of light expands into "
            "dozens of synchronized parallel bright cyan and gold light streams racing forward in unison through a dark futuristic "
            "tunnel. The entire left 45 percent is pure deep dark shadow with zero clutter for bold white numbers."
        ),
    },
    {
        "img": "h02-dp2",
        "scene": (
            "Cinematic photorealistic 3D render metaphor for 2x Data Parallelism: on the right half, two identical sleek matte-black "
            "twin GPU modules glowing with bright emerald-cyan light running side by side in perfect symmetry, each with its own clear "
            "outgoing stream of golden light. The entire left 45 percent is deep dark shadow and empty space for white stats."
        ),
    },
    {
        "img": "h03-mp4",
        "scene": (
            "Cinematic dark 3D render metaphor for Model Parallelism trade-off: on the right half, a hyper-bright violet-gold laser "
            "beam flashes rapidly between two paired crystalline GPU prisms linked by bright orange electric interconnect bridges, "
            "suggesting ultra-fast single-beam speed with heavy synchronization overhead. Left 45 percent is deep dark empty shadow."
        ),
    },
    {
        "img": "h04-failover",
        "scene": (
            "Cinematic moody architectural metaphor for Failover: on the right half at night, two parallel illuminated suspension "
            "bridges cross dark water — the lower bridge goes dark with a faint amber spark while streams of bright cyan light trails "
            "smoothly divert across the bright upper bridge without stopping. Left 45 percent is deep dark shadow for white numbers."
        ),
    },
]

CARTOON_TMPL = """Generate ONE illustration with your image generation tool and save it as a PNG file at exactly this path:
{out}/{img}.png

Match the exact illustration style and visual pattern of the attached reference images (clean airy Thai educational infographic on a pure white/very light background, pastel blue rounded title banner at the top with small yellow spark strokes, bold dark outlines, rounded pastel cards, open wooden-door gateway icon for Load Balancer/NGINX, purple/blue graphics cards, cute white-and-blue robot icon where 1 complete robot = 1 full model on 1 GPU and 1 split half-and-half robot across 2 GPUs = Model Parallelism, bold rounded legible Thai lettering).

Canvas: landscape 16:9 (1600 x 900 or 1672 x 941). Setting: {setting}.

Title banner text at the top (exact): {title}

Scene: {scene}

Text labels to place in the picture, each next to the element it names (exact text, one label per line below):
{labels}

Strict rules:
- Write EVERY Thai and English label EXACTLY as given, character by character. Use full terms (Data Parallelism, Model Parallelism, Out of Memory), never invent abbreviations.
- Do NOT add any extra words, numbers, captions, watermarks, mouse cursors, or logos beyond the title and the labels above.
- Do NOT draw bar charts with numbers/axes, line charts, gauges, or meters.
- Text must be large, bold, crisp, well-spaced, and easy to read from the back of a classroom.
- Do not modify any other file and do not run any git command.
When the PNG file is saved at {out}/{img}.png, reply with the file path and stop.
"""

PHOTO_TMPL = """Generate ONE cinematic photorealistic image with your image generation tool and save it as a PNG file at exactly this path:
{out}/{img}.png

Scene: {scene}

Strict requirements:
- Landscape 16:9 widescreen, high contrast, cinematic lighting with cyan, amber, and warm gold accents.
- The LEFT 45% of the canvas MUST be very dark, low-contrast, and visually empty so white headline text and white statistics placed on the left are effortlessly legible.
- Main visual subject sits cleanly on the RIGHT half of the frame.
- ZERO text, ZERO letters, ZERO numbers, ZERO watermarks, ZERO logos, ZERO UI overlays anywhere in the image.
- Do not modify any other file and do not run any git command.
When the PNG file is saved at {out}/{img}.png, reply with the file path and stop.
"""


def write_prompts(out_dir, only=None):
    os.makedirs(out_dir, exist_ok=True)
    n_f = 0
    for f in FIGS:
        if only and f["img"] not in only:
            continue
        lbls = "\n".join("- " + l for l in f["labels"])
        txt = CARTOON_TMPL.format(
            out=out_dir, img=f["img"], setting=SETTING,
            title=f["title"], scene=f["scene"], labels=lbls,
        )
        open(os.path.join(out_dir, f["img"] + ".txt"), "w", encoding="utf-8").write(txt)
        n_f += 1
    n_p = 0
    for p in PHOTOS:
        if only and p["img"] not in only:
            continue
        txt = PHOTO_TMPL.format(out=out_dir, img=p["img"], scene=p["scene"])
        open(os.path.join(out_dir, p["img"] + ".txt"), "w", encoding="utf-8").write(txt)
        n_p += 1
    print(f"Wrote {n_f} cartoon + {n_p} photo prompts to {out_dir}")


if __name__ == "__main__":
    out_dir = sys.argv[1] if len(sys.argv) > 1 else "/workspace/lab7_gen_v2"
    only = set(sys.argv[2:]) if len(sys.argv) > 2 else None
    write_prompts(out_dir, only=only)
