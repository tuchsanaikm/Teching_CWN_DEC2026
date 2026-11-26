# common.sh — ค่าร่วมของ installer และ wrapper (source เท่านั้น ไม่รันตรง)
# ไม่พิมพ์ secret ใด ๆ ออกหน้าจอ

AI_ACCOUNTS_BASE="${AI_ACCOUNTS_BASE:-/root/ai-accounts}"
MA_ACCOUNTS="1 2 3 4 5"
MA_PLAYWRIGHT_OUTPUT="/tmp/playwright-mcp-output"
: "${PLAYWRIGHT_BROWSERS_PATH:=/opt/ms-playwright}"
export PLAYWRIGHT_BROWSERS_PATH

# โฟลเดอร์ของแต่ละ CLI ใต้ BASE
ma_tool_dir() {
    case "$1" in
        claude) echo "$AI_ACCOUNTS_BASE/.Claude" ;;
        codex)  echo "$AI_ACCOUNTS_BASE/.Codex" ;;
        agy)    echo "$AI_ACCOUNTS_BASE/.Gemini" ;;
    esac
}

# โฟลเดอร์ skills ของบัญชี (ที่ CLI อ่านจริง)
ma_account_skills_dir() {   # $1=tool $2=account-dir
    case "$1" in
        claude) echo "$2/skills" ;;                 # $CLAUDE_CONFIG_DIR/skills
        codex)  echo "$2/skills" ;;                 # $CODEX_HOME/skills
        agy)    echo "$2/.gemini/config/skills" ;;  # $HOME/.gemini/config/skills
    esac
}

# symlink ทีละ skill จาก shared/skills → skills ของบัญชี
# ไม่ทับของเดิม: ถ้าชื่อนั้นมีอยู่แล้ว (ไฟล์/โฟลเดอร์/ลิงก์) จะข้าม
# ลิงก์ที่ชี้เข้า shared แต่ต้นทางถูกลบไปแล้ว (dangling) จะถูกลบออก
ma_sync_skills() {   # $1=tool $2=account-dir
    local shared dst s name
    shared="$(ma_tool_dir "$1")/shared/skills"
    dst="$(ma_account_skills_dir "$1" "$2")"
    [ -d "$shared" ] || return 0
    mkdir -p "$dst" || return 0
    for s in "$shared"/*/; do
        [ -d "$s" ] || continue
        name="$(basename "$s")"
        if [ ! -e "$dst/$name" ] && [ ! -L "$dst/$name" ]; then
            ln -s "$shared/$name" "$dst/$name"
        fi
    done
    for s in "$dst"/*; do
        if [ -L "$s" ] && [ ! -e "$s" ]; then
            case "$(readlink "$s")" in "$shared"/*) rm -f "$s" ;; esac
        fi
    done
}
