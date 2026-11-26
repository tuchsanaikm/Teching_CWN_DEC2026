#!/bin/bash
# wrapper ของ yolo1..5 / cyolo1..5 / gyolo1..5  (ทุกชื่อเป็น symlink มาที่ไฟล์นี้)
#   yoloN  → claude --dangerously-skip-permissions                 CLAUDE_CONFIG_DIR=$BASE/.Claude/yoloN
#   cyoloN → codex  --dangerously-bypass-approvals-and-sandbox     CODEX_HOME=$BASE/.Codex/cyoloN
#   gyoloN → agy    --dangerously-skip-permissions                 HOME=$BASE/.Gemini/gyoloN (เฉพาะ process agy)
# ส่งต่อ "$@" ครบ, MCP/skill ส่วนกลางมาจาก $BASE/.<CLI>/shared, ไม่พิมพ์ secret
set -u
. /usr/local/lib/multi-account/common.sh
BASE="$AI_ACCOUNTS_BASE"
me="$(basename "$0")"

die() { echo "[$me] $*" >&2; exit 2; }

case "$me" in
    yolo[1-5])  tool=claude; acct="$BASE/.Claude/$me" ;;
    cyolo[1-5]) tool=codex;  acct="$BASE/.Codex/$me" ;;
    gyolo[1-5]) tool=agy;    acct="$BASE/.Gemini/$me" ;;
    *) die "unknown wrapper name '$me' (expected yolo1..5, cyolo1..5, gyolo1..5)" ;;
esac

if [ ! -d "$acct" ]; then
    die "account folder not found: $acct
  → run: install-ai-accounts   (ถ้า $BASE ไม่ได้ mount เป็น volume ให้รัน container ด้วย -v ai-accounts:$BASE)"
fi

# skill ใหม่ที่เพิ่มใน shared จะถูกลิงก์ให้บัญชีนี้ตอนเปิดครั้งถัดไป (ไม่ทับของเดิม)
ma_sync_skills "$tool" "$acct" 2>/dev/null || true

case "$tool" in
claude)
    export CLAUDE_CONFIG_DIR="$acct"
    export IS_SANDBOX=1          # root ใน container ต้องตั้งจึงใช้ --dangerously-skip-permissions ได้
    mcp="$BASE/.Claude/shared/mcp/mcp.json"
    extra=()
    [ -f "$mcp" ] && extra+=("--mcp-config=$mcp")
    exec claude --dangerously-skip-permissions "${extra[@]}" "$@"
    ;;
codex)
    export CODEX_HOME="$acct"
    mcp="$BASE/.Codex/shared/mcp/mcp.json"
    extra=()
    if [ -f "$mcp" ]; then
        mapfile -t extra < <(python3 /usr/local/lib/multi-account/mcp2codex.py "$mcp")
    fi
    exec codex "${extra[@]}" --dangerously-bypass-approvals-and-sandbox "$@"
    ;;
agy)
    export AGY_CLI_DISABLE_AUTO_UPDATE=true   # 5 บัญชีใช้ไบนารีเดียวกัน → ห้ามอัปเดตตัวเอง
    export HOME="$acct"                       # agy ไม่มีตัวแปร config dir; เปลี่ยน HOME เฉพาะ process นี้
    exec agy --dangerously-skip-permissions "$@"
    ;;
esac
