#!/bin/bash
# install-ai-accounts — เตรียมโครงสร้างหลายบัญชีใน $AI_ACCOUNTS_BASE (ค่าเริ่มต้น /root/ai-accounts)
#
# - รันอัตโนมัติทุกครั้งที่ container start (จาก start.sh) และรันซ้ำเองได้
# - idempotent: สร้างเฉพาะสิ่งที่ยังไม่มี ไม่เขียนทับ credential / config / skill / MCP ที่มีอยู่
# - ไม่แตะ ~/.bashrc, Git config, SSH และไม่พิมพ์ secret
#
#   $BASE/.Claude/{yolo1..5,shared/{skills,mcp}}     CLAUDE_CONFIG_DIR=$BASE/.Claude/yoloN
#   $BASE/.Codex/{cyolo1..5,shared/{skills,mcp}}     CODEX_HOME=$BASE/.Codex/cyoloN
#   $BASE/.Gemini/{gyolo1..5,shared/{skills,mcp}}    HOME=$BASE/.Gemini/gyoloN (เฉพาะ process agy)
set -u
. /usr/local/lib/multi-account/common.sh

BASE="$AI_ACCOUNTS_BASE"
created=0
log() { echo "[install-ai-accounts] $*"; }

mkd() {  # mkdir ที่นับว่าสร้างใหม่
    if [ ! -d "$1" ]; then mkdir -p "$1" && chmod 700 "$1" && created=$((created+1)); fi
}

# เขียนไฟล์จาก stdin เฉพาะเมื่อยังไม่มี (ไม่ทับของเดิม)
write_if_missing() {
    local f="$1"
    if [ -e "$f" ] || [ -L "$f" ]; then cat >/dev/null; return 0; fi
    mkdir -p "$(dirname "$f")"
    cat > "$f" && created=$((created+1))
}

rand_token() { python3 -c 'import secrets; print(secrets.token_hex(8))'; }

PW_BIN="$(command -v playwright-mcp || echo /usr/bin/playwright-mcp)"

mcp_json() {  # รูปแบบ mcpServers (ใช้ได้ทั้ง Claude --mcp-config, agy mcp_config.json และแปลงเป็น -c ของ Codex)
cat <<EOF
{
  "mcpServers": {
    "playwright": {
      "command": "$PW_BIN",
      "args": ["--browser", "chromium", "--headless", "--isolated", "--no-sandbox",
               "--output-dir", "$MA_PLAYWRIGHT_OUTPUT"],
      "env": { "PLAYWRIGHT_BROWSERS_PATH": "$PLAYWRIGHT_BROWSERS_PATH" }
    }
  }
}
EOF
}

skill_md() {  # $1=tool  — โค้ดยืนยันมีอยู่ในไฟล์ skill นี้เท่านั้น
cat <<EOF
---
name: shared-check
description: Verify that the shared skill folder is wired up. Use when the user asks to run shared-check or to check the shared skill.
---

# shared-check

When this skill is invoked, reply with exactly the following single line and nothing else:

SHARED_SKILL_OK-$1-$(rand_token)
EOF
}

umask 077
mkd "$BASE"

for tool in claude codex agy; do
    td="$(ma_tool_dir "$tool")"
    mkd "$td/shared/skills"
    mkd "$td/shared/mcp"
    skill_md "$tool" | write_if_missing "$td/shared/skills/shared-check/SKILL.md"
    case "$tool" in
        agy) mcp_json | write_if_missing "$td/shared/mcp/mcp_config.json" ;;
        *)   mcp_json | write_if_missing "$td/shared/mcp/mcp.json" ;;
    esac
done
# skill / MCP เป็นไฟล์ที่ทุกบัญชีอ่านได้ (ไม่ใช่ credential)
chmod -R go+rX "$BASE/.Claude/shared" "$BASE/.Codex/shared" "$BASE/.Gemini/shared" 2>/dev/null || true

for n in $MA_ACCOUNTS; do
    # Claude Code
    d="$BASE/.Claude/yolo$n"; mkd "$d"; ma_sync_skills claude "$d"
    # Codex CLI (CODEX_HOME ต้องมีอยู่ก่อน) — credential เป็นไฟล์ต่อบัญชี
    d="$BASE/.Codex/cyolo$n"; mkd "$d"; ma_sync_skills codex "$d"
    if [ ! -e "$d/config.toml" ]; then
        printf '# per-account Codex config (สร้างโดย install-ai-accounts ครั้งแรก — แก้ได้ ไม่ถูกทับ)\ncli_auth_credentials_store = "file"\n' > "$d/config.toml"
        created=$((created+1))
    fi
    # Antigravity CLI (HOME ของ agy = โฟลเดอร์บัญชี)
    d="$BASE/.Gemini/gyolo$n"; mkd "$d"; mkd "$d/.gemini/config"
    ma_sync_skills agy "$d"
    if [ ! -e "$d/.gemini/config/mcp_config.json" ] && [ ! -L "$d/.gemini/config/mcp_config.json" ]; then
        ln -s "$BASE/.Gemini/shared/mcp/mcp_config.json" "$d/.gemini/config/mcp_config.json"
        created=$((created+1))
    fi
done

mkdir -p "$MA_PLAYWRIGHT_OUTPUT"
log "base=$BASE accounts=5x3 new_items=$created (existing files kept)"
