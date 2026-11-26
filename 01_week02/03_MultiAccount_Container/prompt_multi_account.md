ฐานของ image คือ Dockerfile ในโฟลเดอร์ Input ที่พรอมต์ระบุ อ่านก่อนว่ามีอะไรอยู่แล้ว (OS, Node.js, Python ฯลฯ)
image ต้องรันได้ทั้ง linux/amd64 (Windows/Intel) และ linux/arm64 (Mac Apple Silicon)
ทุกไฟล์ที่ดาวน์โหลดต้องเลือกตามสถาปัตยกรรมขณะ build (TARGETARCH) ห้าม hardcode x64
ติดตั้ง AI CLI ให้ครบ 3 ตัวใน image และ pin เวอร์ชัน (ตัวไหนมีในฐานแล้ว ให้ตรวจ --version แล้วข้าม)
- Claude Code: npm install -g @anthropic-ai/claude-code
- Codex CLI: npm install -g @openai/codex
- Antigravity CLI (agy): curl -fsSL https://antigravity.google/cli/install.sh | bash
ตรวจ --help ของเวอร์ชันจริงก่อนใช้ env/flag ห้ามเดา

## เป้าหมาย (BASE=/root/ai-accounts)
- yolo1..yolo5   → claude --dangerously-skip-permissions  (CLAUDE_CONFIG_DIR=$BASE/.Claude/yoloN)
- cyolo1..cyolo5 → codex --dangerously-bypass-approvals-and-sandbox  (CODEX_HOME=$BASE/.Codex/cyoloN)
- gyolo1..gyolo5 → agy --dangerously-skip-permissions  (HOME=$BASE/.Gemini/gyoloN เฉพาะ process ของ agy)
- wrapper วางใน /usr/local/bin ให้พิมพ์ได้ทันที ส่งต่อ "$@" ครบ แจ้งชัดถ้าโฟลเดอร์บัญชีไม่มี ไม่พิมพ์ secret
- $BASE/.Claude/shared, $BASE/.Codex/shared และ $BASE/.Gemini/shared มี skills/ และ mcp/
  แก้ครั้งเดียว ทุกบัญชีของ CLI นั้นเห็นตอนเปิดครั้งถัดไป

## กติกา
- แยก credential/config/session ต่อบัญชี เปิดพร้อมกันได้ ใช้ CLAUDE_CONFIG_DIR/CODEX_HOME
  ห้ามเปลี่ยน $HOME ของระบบ ยกเว้น wrapper gyoloN ที่ตั้ง HOME ให้ agy เท่านั้น (agy ไม่มีตัวแปร config dir)
- Codex ใช้ file-based credential ต่อ CODEX_HOME ห้ามแชร์ credential ใน shared
- installer เป็นไฟล์ใน image รันทุกครั้งที่ container start รันซ้ำได้ ไม่เขียนทับ credential/config เดิม
  ห้ามแก้ .bashrc/Git/SSH
- MCP ส่วนกลางตัวแรก: Playwright (@playwright/mcp) + Chromium ติดตั้งครั้งเดียว
- skill ตัวอย่าง shared-check: ตอบ SHARED_SKILL_OK-<tool>-<ค่าสุ่มตอนติดตั้ง> ซึ่งมีในไฟล์ skill เท่านั้น

## ข้อเท็จจริงจากการทดลอง (ตรวจว่ายังจริงกับเวอร์ชันนี้)
- npm 12 ไม่รัน postinstall ของ claude-code ให้ ถ้า claude --version ขึ้น "native binary not installed"
  ให้รัน node "$(npm root -g)/@anthropic-ai/claude-code/install.cjs"
- root ต้องตั้ง IS_SANDBOX=1; CODEX_HOME ต้อง mkdir -p ก่อน
- Claude: skill อ่านจาก $CLAUDE_CONFIG_DIR/skills; MCP ส่งผ่าน --mcp-config=<ไฟล์> (ต้องมี =)
  ห้าม symlink .claude.json (มีสถานะล็อกอิน); claude mcp list ไม่แสดง MCP นี้ ให้ตรวจด้วย /mcp
- Codex: skill อ่านจาก $CODEX_HOME/skills และเขียน skills/.system เอง ห้าม symlink ทั้งโฟลเดอร์
  MCP ส่งด้วย -c mcp_servers.<name>={...} (ใช้กับ codex mcp list ได้)
- Antigravity: เก็บทุกอย่างใต้ $HOME/.gemini และ token เป็นไฟล์ใต้ $HOME (container ไม่มี keyring)
  skill อ่านจาก ~/.gemini/config/skills (symlink ทีละ skill), MCP อ่านจาก ~/.gemini/config/mcp_config.json
  (รูปแบบ mcpServers, symlink ไฟล์นี้ไป shared ได้ ใช้กับ gyoloN mcp list ได้)
  install.sh จะรัน agy install ที่แก้ shell profile ให้รันด้วย HOME ชั่วคราวและ --dir โฟลเดอร์กลาง
  ปิด auto-update ใน wrapper (AGY_CLI_DISABLE_AUTO_UPDATE=true) เพราะ 5 บัญชีใช้ไบนารีเดียว
  ตรวจล็อกอินด้วย gyoloN models (ยังไม่ล็อกอิน = "Please sign in")
- Playwright ใน root container: --browser chromium --headless --isolated --no-sandbox และ --output-dir นอกโฟลเดอร์งาน
  ติดตั้ง Chromium ด้วย playwright ในแพ็กเกจ @playwright/mcp ให้เวอร์ชันตรงกัน (อาจต้อง install-deps)
  ตั้ง PLAYWRIGHT_BROWSERS_PATH เป็นโฟลเดอร์กลาง เพราะ gyolo แต่ละบัญชีมี HOME ต่างกัน

## ทดสอบใน container (PASS/FAIL/SKIP ตามจริง)
- 15 คำสั่ง --version ครบ, config root คนละโฟลเดอร์, installer รอบ 2 ไม่ทำลายของเดิม, .bashrc ไม่ถูกแก้
- cyoloN/gyoloN mcp list เห็น playwright, skill shared-check ทุกบัญชี readlink -f ไปไฟล์เดียวกันใน shared
- อะไรที่ต้องล็อกอิน = SKIP

## รายงาน (ห้ามมี secret)
- setup-report.md: โครงสร้างโฟลเดอร์, wrapper, แต่ละ CLI อ่าน skill/MCP จากไหน, ข้อจำกัด
- login-guide.md: ล็อกอินทีละบัญชีใน JupyterLab Terminal
- checklist.md: รายการ | หลักฐาน | PASS/FAIL/SKIP
เสร็จแล้วสรุปเป็นตารางสั้น ๆ แล้วหยุดรอ ห้ามล็อกอินแทนฉัน
