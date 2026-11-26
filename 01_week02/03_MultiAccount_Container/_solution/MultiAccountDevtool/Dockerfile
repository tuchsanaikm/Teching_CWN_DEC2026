FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive \
    TZ=Asia/Bangkok \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8

RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        wget \
        gnupg \
        lsb-release \
        software-properties-common \
        sudo \
        vim \
        nano \
        less \
        net-tools \
        iputils-ping \
        dnsutils \
        git \
        tzdata \
        python3 \
        python3-pip \
        python3-venv \
        python-is-python3 \
 && ln -fs "/usr/share/zoneinfo/${TZ}" /etc/localtime \
 && dpkg-reconfigure -f noninteractive tzdata \
 && rm -rf /var/lib/apt/lists/*

# Git ล่าสุดจาก git-core PPA (git worktree ต้องใช้ git >= 2.5; Ubuntu 24.04 มี 2.43 อยู่แล้ว
# แต่ติดตั้งเวอร์ชันล่าสุดไว้เพื่อให้ได้ฟีเจอร์ worktree ครบทุกคำสั่ง เช่น repair/move)
RUN add-apt-repository -y ppa:git-core/ppa \
 && apt-get update && apt-get install -y --no-install-recommends git \
 && git --version \
 && git init -q /tmp/worktree-check \
 && git -C /tmp/worktree-check worktree list >/dev/null \
 && rm -rf /tmp/worktree-check /var/lib/apt/lists/*

RUN install -m 0755 -d /etc/apt/keyrings \
 && curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc \
 && chmod a+r /etc/apt/keyrings/docker.asc \
 && echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] \
https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "${VERSION_CODENAME}") stable" \
      > /etc/apt/sources.list.d/docker.list \
 && apt-get update && apt-get install -y --no-install-recommends \
        docker-ce \
        docker-ce-cli \
        containerd.io \
        docker-buildx-plugin \
        docker-compose-plugin \
 && rm -rf /var/lib/apt/lists/*

# Node.js (LTS 22.x) สำหรับ run Next.js / React / Vite
RUN curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
 && apt-get install -y --no-install-recommends nodejs \
 && npm install -g npm@latest \
 && rm -rf /var/lib/apt/lists/*

RUN install -d /workspace

# ------------------------------------------------------------------
# JupyterLab + extensions (ติดตั้งลง system python เพื่อให้ kernel เห็น
# package เดียวกับที่ใช้ใน terminal)
#   - jupytext                : เปิด .py / .md เป็น notebook ได้ (pair notebook <-> script)
#   - jupyterlab-git          : Git UI ใน sidebar
#   - jupyterlab-lsp          : autocomplete / hover / diagnostics (python-lsp-server)
#   - jupyterlab-code-formatter + black + isort : จัดรูปแบบโค้ด
#   - jupyterlab-execute-time : แสดงเวลารันของแต่ละ cell
#   - jupyter-resource-usage  : แสดง CPU / RAM ใน status bar
#   - ipywidgets              : interactive widgets
#   - bash_kernel             : เขียน notebook ด้วย Bash kernel (เหมาะกับ DevTools lab)
# ------------------------------------------------------------------
ENV PIP_BREAK_SYSTEM_PACKAGES=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_ROOT_USER_ACTION=ignore

RUN pip install \
        "jupyterlab>=4.3,<5" \
        notebook \
        ipywidgets \
        jupytext \
        jupyterlab-git \
        jupyterlab-lsp \
        "python-lsp-server[all]" \
        jupyterlab-code-formatter \
        black \
        isort \
        jupyterlab-execute-time \
        jupyter-resource-usage \
        bash_kernel \
 && python -m bash_kernel.install --sys-prefix \
 && jupyter lab --version \
 && jupyter labextension list 2>&1 | grep -E 'enabled|OK' | head -20

# Jupyter Server config (system-wide)
RUN mkdir -p /etc/jupyter \
 && cat > /etc/jupyter/jupyter_server_config.py <<'EOF'
c = get_config()  # noqa

c.ServerApp.ip = "0.0.0.0"
c.ServerApp.port = 8888
c.ServerApp.root_dir = "/"          # เห็นทั้ง filesystem (โฟลเดอร์งานอยู่ที่ /workspace)
c.ServerApp.allow_root = True
c.ServerApp.open_browser = False
c.ServerApp.allow_remote_access = True

# แสดง hidden file / folder (ชื่อขึ้นต้นด้วย ".") ใน file browser เช่น .env .git .gitignore
# (ฝั่ง UI ตั้ง showHiddenFiles ไว้ใน overrides.json; ต้องเปิดทั้งสองฝั่งจึงจะเห็น)
c.ContentsManager.allow_hidden = True

# terminal ใน JupyterLab ใช้ bash login shell (อ่าน /etc/profile, ~/.bashrc)
c.ServerApp.terminals_enabled = True
c.ServerApp.terminado_settings = {"shell_command": ["/bin/bash", "-l"]}

# ไม่ใช้ token; รหัสผ่าน (ถ้ามี) ถูกตั้งจาก start.sh ผ่าน $JUPYTER_PASSWORD (default: ไม่มีรหัสผ่าน)
c.IdentityProvider.token = ""
c.PasswordIdentityProvider.allow_password_change = False
EOF

# JupyterLab UI defaults — file browser แสดง hidden file/folder และ terminal ให้ copy/paste ได้สะดวก:
#   * Ctrl+V           = paste (pasteWithCtrlV)
#   * Ctrl+Shift+C / V = copy / paste
#   * Ctrl+Insert / Shift+Insert = copy / paste
#   * คลิกขวาที่ terminal จะมีเมนู Copy / Paste
COPY jupyter_overrides.json /usr/local/share/jupyter/lab/settings/overrides.json


# ==================================================================
# Multi-account AI CLI (Claude Code / Codex CLI / Antigravity CLI)
# + Playwright MCP + Chromium + ฟอนต์ไทย  — รองรับ linux/amd64 และ linux/arm64
# ทุกไฟล์ที่ดาวน์โหลดเลือกตาม TARGETARCH (ไม่ hardcode x64)
# ห้ามมีข้อมูลล็อกอินใน image: /root/ai-accounts เป็น VOLUME และถูกสร้างโดย installer ตอน start
# ==================================================================
ARG TARGETARCH
ARG CLAUDE_CODE_VERSION=2.1.330
ARG CODEX_VERSION=0.171.0
ARG PLAYWRIGHT_MCP_VERSION=0.0.86
ARG AGY_VERSION=1.5.15
ARG AGY_BUILD=1.5.15-5514532022517760
ARG AGY_SHA512_AMD64=af3f0be58b8475940d79f9abea19e762ecc3d265ea9f56cff8dd805e27ba299b44a305a79504a7ffe6ebdfa29a294c56edc4caed1875990bfaf2fef1508ec8b0
ARG AGY_SHA512_ARM64=d64ad759781b50dfacfa7d9826c0ad469959d01bdf5a170acd4c83472eba31c677baf0052ac8ab48eef40f0d3f0e26057e752aabd24331c79f4c881d4b872125

ENV PLAYWRIGHT_BROWSERS_PATH=/opt/ms-playwright \
    AI_ACCOUNTS_BASE=/root/ai-accounts

# ฟอนต์ไทย (screenshot ภาษาไทยไม่เป็นกล่อง)
RUN apt-get update && apt-get install -y --no-install-recommends \
        fonts-thai-tlwg fonts-noto-core fontconfig xz-utils \
 && fc-cache -f \
 && rm -rf /var/lib/apt/lists/*

# Claude Code + Codex CLI + Playwright MCP (pin เวอร์ชัน)
# npm รุ่นใหม่ไม่รัน postinstall ของ claude-code → ถ้ายังไม่มี native binary ให้รัน install.cjs เอง
RUN npm install -g \
        "@anthropic-ai/claude-code@${CLAUDE_CODE_VERSION}" \
        "@openai/codex@${CODEX_VERSION}" \
        "@playwright/mcp@${PLAYWRIGHT_MCP_VERSION}" \
 && if ! claude --version 2>&1 | grep -q "${CLAUDE_CODE_VERSION}"; then \
        node "$(npm root -g)/@anthropic-ai/claude-code/install.cjs"; \
    fi \
 && claude --version | grep -q "${CLAUDE_CODE_VERSION}" \
 && codex --version | grep -q "${CODEX_VERSION}" \
 && rm -rf /root/.claude /root/.claude.json /root/.codex /root/.npm /root/.cache

# Chromium ของ playwright ที่มากับ @playwright/mcp (เวอร์ชันตรงกัน) ไว้ในโฟลเดอร์กลาง
RUN set -eu; G="$(npm root -g)"; PW_CLI=""; \
    for c in "$G/@playwright/mcp/node_modules/playwright/cli.js" "$G/playwright/cli.js"; do \
        if [ -f "$c" ]; then PW_CLI="$c"; break; fi; done; \
    echo "playwright cli: $PW_CLI ($(node "$PW_CLI" --version))"; \
    node "$PW_CLI" install --with-deps chromium \
 && chmod -R a+rX "${PLAYWRIGHT_BROWSERS_PATH}" \
 && rm -rf /var/lib/apt/lists/* /root/.cache

# Antigravity CLI (agy) — ทำตามขั้นของ install.sh แต่ pin เวอร์ชัน + sha512 ต่อสถาปัตยกรรม
# (install.sh ดึง "latest" เสมอ) แล้วรัน "agy install --dir" ด้วย HOME ชั่วคราว
# เพื่อไม่ให้ไปแก้ shell profile ของ root
RUN set -eu; \
    case "${TARGETARCH}" in \
      amd64) AGY_PATH="linux-x64/cli_linux_x64.tar.gz";   AGY_SHA="${AGY_SHA512_AMD64}" ;; \
      arm64) AGY_PATH="linux-arm/cli_linux_arm64.tar.gz"; AGY_SHA="${AGY_SHA512_ARM64}" ;; \
      *) echo "unsupported TARGETARCH=${TARGETARCH}" >&2; exit 1 ;; \
    esac; \
    tmp="$(mktemp -d)"; \
    curl -fsSL -o "$tmp/agy.tar.gz" "https://storage.googleapis.com/antigravity-public/antigravity-cli/${AGY_BUILD}/${AGY_PATH}"; \
    echo "${AGY_SHA}  $tmp/agy.tar.gz" | sha512sum -c -; \
    tar -xzf "$tmp/agy.tar.gz" -C "$tmp" antigravity; \
    install -d /opt/antigravity/bin; \
    install -m 0755 "$tmp/antigravity" /opt/antigravity/bin/agy; \
    mkdir -p "$tmp/home"; \
    HOME="$tmp/home" AGY_CLI_DISABLE_AUTO_UPDATE=true /opt/antigravity/bin/agy install --dir /opt/antigravity/bin </dev/null || true; \
    ln -sf /opt/antigravity/bin/agy /usr/local/bin/agy; \
    rm -rf "$tmp"; \
    HOME=/tmp/agy-ver AGY_CLI_DISABLE_AUTO_UPDATE=true agy --version | grep -q "${AGY_VERSION}"; \
    rm -rf /tmp/agy-ver

# installer + wrapper yolo1..5 / cyolo1..5 / gyolo1..5 (ใน /usr/local/bin)
COPY multi-account/ /usr/local/lib/multi-account/
RUN chmod 0755 /usr/local/lib/multi-account/*.sh /usr/local/lib/multi-account/*.py \
 && ln -sf /usr/local/lib/multi-account/install-ai-accounts.sh /usr/local/bin/install-ai-accounts \
 && for n in 1 2 3 4 5; do \
        ln -sf /usr/local/lib/multi-account/wrapper.sh "/usr/local/bin/yolo$n"; \
        ln -sf /usr/local/lib/multi-account/wrapper.sh "/usr/local/bin/cyolo$n"; \
        ln -sf /usr/local/lib/multi-account/wrapper.sh "/usr/local/bin/gyolo$n"; \
    done \
 && mkdir -p /root/ai-accounts \
 && [ -z "$(ls -A /root/ai-accounts)" ]

# ข้อมูลบัญชีทั้งหมดอยู่ใน volume (image ไม่มี credential)
VOLUME /root/ai-accounts

# start script: dockerd + jupyter lab (ไม่มีรหัสผ่าน เว้นแต่ตั้ง $JUPYTER_PASSWORD)
COPY start.sh /usr/local/bin/start.sh
RUN chmod +x /usr/local/bin/start.sh

VOLUME /var/lib/docker

# 8888=jupyterlab (ไม่มี SSH — สั่งงานผ่าน docker exec / Claude Code app)
EXPOSE 8888

WORKDIR /workspace

CMD ["/usr/local/bin/start.sh"]
