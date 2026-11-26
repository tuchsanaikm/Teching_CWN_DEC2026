# MultiAccountDevtool — image `multi-account:1.0`

ต่อยอดจาก `../00_Devtool_Container` (Ubuntu 24.04 + Docker-in-Docker + Python + Node.js 22 + JupyterLab)
เพิ่ม Claude Code / Codex CLI / Antigravity CLI แบบ 5 บัญชีต่อ CLI + Playwright MCP + Chromium + ฟอนต์ไทย
รองรับ `linux/amd64` และ `linux/arm64` (Mac Apple Silicon)

```bash
docker buildx build --platform linux/amd64,linux/arm64 -t multi-account:1.0 --load .
docker run -d --name multi-account --privileged -p 8888:8888 \
  -v ai-accounts:/root/ai-accounts multi-account:1.0
```

| คำสั่ง | CLI | config root |
|---|---|---|
| `yolo1..5` | `claude --dangerously-skip-permissions` | `/root/ai-accounts/.Claude/yoloN` |
| `cyolo1..5` | `codex --dangerously-bypass-approvals-and-sandbox` | `/root/ai-accounts/.Codex/cyoloN` |
| `gyolo1..5` | `agy --dangerously-skip-permissions` | `/root/ai-accounts/.Gemini/gyoloN` (HOME ของ agy) |

```text
MultiAccountDevtool/
├── Dockerfile                 ← base devtools + AI CLI (pin เวอร์ชัน) + Playwright/Chromium + ฟอนต์ไทย
├── start.sh                   ← dockerd + install-ai-accounts + jupyter lab
├── multi-account/             ← installer, wrapper, common.sh, mcp2codex.py (→ /usr/local/lib/multi-account)
├── jupyter_overrides.json
├── docker-compose.yml
├── setup-report.md            ← โครงสร้าง, wrapper, skill/MCP, ข้อจำกัด
├── login-guide.md             ← ล็อกอินทีละบัญชี
└── checklist.md               ← ผลทดสอบ PASS/FAIL/SKIP
```
