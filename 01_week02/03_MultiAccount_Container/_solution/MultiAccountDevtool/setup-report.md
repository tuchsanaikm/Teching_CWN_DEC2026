# setup-report — image `multi-account:1.0`

image ที่เปิดมาแล้วใช้ Claude Code / Codex CLI / Antigravity CLI ได้คนละ 5 บัญชีทันที
ต่อยอดจาก `00_Devtool_Container` (Ubuntu 24.04 + Docker-in-Docker + Python + Node.js 22 + JupyterLab — คงไว้ครบ)
รองรับ `linux/amd64` และ `linux/arm64` ใน image ชื่อเดียว (manifest list)

## เวอร์ชันที่ pin

| ส่วน | เวอร์ชัน | วิธีติดตั้ง |
|---|---|---|
| Claude Code `@anthropic-ai/claude-code` | 2.1.330 | `npm install -g` + `node install.cjs` (npm บล็อก postinstall — ยืนยันจาก log: *"install scripts blocked … claude-code (postinstall: node install.cjs)"*) |
| Codex CLI `@openai/codex` | 0.171.0 | `npm install -g` (npm เลือก `@openai/codex-linux-x64` / `-linux-arm64` ตามสถาปัตยกรรมเอง) |
| Antigravity CLI `agy` | 1.5.15 (build `1.5.15-5514532022517760`) | ทำตามขั้นของ `install.sh` แต่ใช้ URL ที่มีเลขเวอร์ชัน + ตรวจ sha512 ต่อสถาปัตยกรรม (`install.sh` จริงดึง *latest* เสมอ จึง pin ไม่ได้) แล้วรัน `agy install --dir /opt/antigravity/bin` ด้วย `HOME` ชั่วคราว ⇒ ไม่แตะ shell profile ของ root |
| Playwright MCP `@playwright/mcp` | 0.0.86 (playwright `1.66.0-alpha-2026-11-18`) | `npm install -g`; Chromium ติดตั้งด้วย `playwright/cli.js` ที่อยู่ในแพ็กเกจ MCP เอง (`install --with-deps chromium`) ⇒ เวอร์ชันตรงกัน |
| Chromium | ตาม playwright ข้างบน | `PLAYWRIGHT_BROWSERS_PATH=/opt/ms-playwright` (โฟลเดอร์กลาง เพราะ gyoloN มี HOME ต่างกัน) |
| ฟอนต์ไทย | `fonts-thai-tlwg`, `fonts-noto-core` | apt |

ไฟล์ที่ดาวน์โหลดทุกตัวเลือกตาม `TARGETARCH` ตอน build (agy: `linux-x64` / `linux-arm64`, Codex: optional dependency ตามแพลตฟอร์ม, apt/NodeSource/Docker repo: `dpkg --print-architecture`) ไม่มี hardcode x64

## โครงสร้างโฟลเดอร์ (BASE = `/root/ai-accounts` เป็น VOLUME)

```text
/root/ai-accounts/
├── .Claude/
│   ├── shared/skills/shared-check/SKILL.md     ← ต้นฉบับ skill (ทุกบัญชี symlink มาที่นี่)
│   ├── shared/mcp/mcp.json                     ← MCP ส่วนกลาง (mcpServers)
│   └── yolo1 … yolo5/                          ← CLAUDE_CONFIG_DIR (credential/.claude.json/session ต่อบัญชี)
│       └── skills/shared-check → ../../shared/skills/shared-check  (symlink ทีละ skill)
├── .Codex/
│   ├── shared/skills/shared-check/SKILL.md
│   ├── shared/mcp/mcp.json
│   └── cyolo1 … cyolo5/                        ← CODEX_HOME (auth.json แบบไฟล์ต่อบัญชี)
│       ├── config.toml                         ← สร้างครั้งแรก: cli_auth_credentials_store = "file"
│       └── skills/shared-check → shared        (symlink ทีละ skill; skills/.system Codex เขียนเอง)
└── .Gemini/
    ├── shared/skills/shared-check/SKILL.md
    ├── shared/mcp/mcp_config.json
    └── gyolo1 … gyolo5/                        ← HOME ของ process agy
        └── .gemini/config/
            ├── skills/shared-check → shared    (symlink ทีละ skill)
            └── mcp_config.json → shared/mcp/mcp_config.json
```

ไฟล์ใน image:

```text
/usr/local/lib/multi-account/
├── install-ai-accounts.sh   ← installer (ลิงก์เป็น /usr/local/bin/install-ai-accounts)
├── wrapper.sh               ← wrapper เดียว; yolo1..5 / cyolo1..5 / gyolo1..5 ใน /usr/local/bin เป็น symlink มาที่นี่
├── common.sh                ← path + ฟังก์ชัน sync skill (ใช้ร่วมกัน)
└── mcp2codex.py             ← แปลง mcp.json (mcpServers) → อาร์กิวเมนต์ -c mcp_servers.<name>={…}
/opt/antigravity/bin/agy     ← ไบนารีเดียวของ 5 บัญชี (/usr/local/bin/agy → ที่นี่)
/opt/ms-playwright/          ← Chromium ของ Playwright
```

## installer (`install-ai-accounts`)

- `start.sh` เรียกทุกครั้งที่ container start (log: `/var/log/install-ai-accounts.log`) — รันเองซ้ำได้
- สร้างเฉพาะที่ยังไม่มี: โฟลเดอร์ทั้ง 15 บัญชี + shared, `SKILL.md`, ไฟล์ MCP, `config.toml` ของ Codex, symlink
  ถ้ามีไฟล์/ลิงก์ชื่อเดียวกันอยู่แล้วจะ **ข้าม** (ไม่ทับ credential/config/skill ที่ผู้ใช้แก้)
- skill `shared-check` ตอบ `SHARED_SKILL_OK-<claude|codex|agy>-<hex 16 ตัวสุ่มตอนติดตั้งครั้งแรก>` — ค่าสุ่มมีในไฟล์ SKILL.md เท่านั้น ไม่ถูกเก็บหรือพิมพ์ที่อื่น
- ไม่แตะ `~/.bashrc`, Git config, SSH; ไม่เปลี่ยน `$HOME` ของระบบ; ไม่พิมพ์ secret
- `umask 077`: โฟลเดอร์บัญชีเป็น `700`

## wrapper

| คำสั่ง | รันจริง | ตัวแปรที่ตั้ง (เฉพาะ process นั้น) |
|---|---|---|
| `yoloN` | `claude --dangerously-skip-permissions --mcp-config=$BASE/.Claude/shared/mcp/mcp.json "$@"` | `CLAUDE_CONFIG_DIR=$BASE/.Claude/yoloN`, `IS_SANDBOX=1` |
| `cyoloN` | `codex -c mcp_servers.playwright={…} --dangerously-bypass-approvals-and-sandbox "$@"` | `CODEX_HOME=$BASE/.Codex/cyoloN` |
| `gyoloN` | `agy --dangerously-skip-permissions "$@"` | `HOME=$BASE/.Gemini/gyoloN`, `AGY_CLI_DISABLE_AUTO_UPDATE=true` |

- ส่งต่อ `"$@"` ครบ (ทดสอบด้วย stub: `"a b" c` ถูกส่งต่อ)
- ถ้าโฟลเดอร์บัญชีไม่มี → พิมพ์ `account folder not found: … → run: install-ai-accounts` แล้ว exit 2
- ทุกครั้งที่เปิด wrapper จะ sync skill: skill ใหม่ใน `shared/skills/` ถูก symlink ให้บัญชีนั้นอัตโนมัติ (ไม่ทับของเดิม, ลบเฉพาะลิงก์ที่ชี้เข้า shared แต่ต้นทางหายแล้ว)
- อยู่ใน `/usr/local/bin` ⇒ ใช้ได้ทั้ง JupyterLab Terminal (`bash -l`) และ `docker exec` โดยไม่ต้องแก้ `.bashrc`

## แต่ละ CLI อ่าน skill / MCP จากไหน (ตรวจกับเวอร์ชันจริงแล้ว)

| CLI | skill | MCP | ตรวจ MCP ด้วย |
|---|---|---|---|
| Claude Code 2.1.330 | `$CLAUDE_CONFIG_DIR/skills/<name>/SKILL.md` | `--mcp-config=<ไฟล์>` (ใส่ `=` เพราะ option รับหลายค่า `<configs...>`) | `/mcp` ในเซสชัน — `yolo1 mcp list` ไม่แสดง MCP จาก `--mcp-config` (ยืนยันแล้ว: *"No MCP servers configured"*) |
| Codex CLI 0.171.0 | `$CODEX_HOME/skills/<name>` (symlink ทีละ skill; `skills/.system` Codex เขียนเอง จึงห้าม symlink ทั้งโฟลเดอร์) | `-c mcp_servers.<name>={…}` (`-c` เป็น global option ใช้กับ `mcp list` ได้) | `cyoloN mcp list` |
| Antigravity 1.5.15 | `$HOME/.gemini/config/skills/<name>` | `$HOME/.gemini/config/mcp_config.json` (รูปแบบ `mcpServers`, symlink ไป shared) | `gyoloN mcp list` |

แก้ skill หรือ MCP ใน `shared/` ครั้งเดียว ⇒ ทุกบัญชีของ CLI นั้นเห็นตอนเปิดครั้งถัดไป
(skill = symlink; MCP ของ Claude/Codex อ่านไฟล์ shared ทุกครั้งที่เปิด wrapper; ของ agy เป็น symlink ไฟล์)

Playwright MCP: `/usr/bin/playwright-mcp --browser chromium --headless --isolated --no-sandbox --output-dir /tmp/playwright-mcp-output`
+ `PLAYWRIGHT_BROWSERS_PATH=/opt/ms-playwright`

## ข้อเท็จจริงจากสเปกที่ตรวจกับเวอร์ชันจริง

| ข้อเท็จจริง | ผล |
|---|---|
| npm ไม่รัน postinstall ของ claude-code | จริง (npm แจ้ง install scripts blocked) — build รัน `install.cjs` เอง |
| `IS_SANDBOX=1`, `--dangerously-skip-permissions` (claude) | flag มีใน `claude --help` |
| `--mcp-config <configs...>` | มีใน `claude --help`; `claude mcp list` ไม่แสดง (จริง) |
| `--dangerously-bypass-approvals-and-sandbox`, `-c key=value` (codex) | มีใน `codex --help` / `codex mcp --help` |
| `cli_auth_credentials_store = "file"` | key มีในไบนารี codex 0.171.0 |
| `--dangerously-skip-permissions` (agy) | มีใน `agy --help` |
| `AGY_CLI_DISABLE_AUTO_UPDATE` | ชื่อตัวแปรมีในไบนารี agy 1.5.15 |
| `~/.gemini/config/skills`, `~/.gemini/config/mcp_config.json` | path มีในไบนารี agy; `gyolo1 mcp list` เห็น playwright |
| ยังไม่ล็อกอิน agy → "Please sign in" | จริง (`gyolo1 models`) |
| `install.sh` รัน `agy install` (แก้ shell profile) | จริง — รันด้วย HOME ชั่วคราว + `--dir` |

## ข้อจำกัด

- ต้องรันด้วย `-v ai-accounts:/root/ai-accounts` เพื่อให้บัญชีอยู่ถาวร (ถ้าไม่ใส่ Docker จะสร้าง anonymous volume ให้ ซึ่งหายเมื่อ `docker rm -v`)
- Docker-in-Docker ต้อง `--privileged`
- Claude: ตรวจ MCP ได้เฉพาะ `/mcp` ในเซสชันที่ล็อกอินแล้ว
- agy ปิด auto-update ใน wrapper ⇒ อัปเดตด้วยการ build image ใหม่ (แก้ `AGY_BUILD` + sha512 ใน Dockerfile)
- arm64 บนเครื่อง amd64 ทดสอบผ่าน QEMU emulation (ช้า) — การใช้งานจริงบน Mac Apple Silicon รันแบบ native
- image ชื่อ `multi-account:1.0` ที่ build ใหม่ย้าย tag มาจาก image เดิม (image เดิมยังอยู่แบบไม่มี tag และ container `multi-account` เดิมยังใช้อยู่ ไม่ได้ถูกลบ/หยุด)
- ผลทดสอบทั้งหมดดูใน `checklist.md`
