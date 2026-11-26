# checklist — multi-account:1.0

Tested 2026-11-23 with a new test container and volume (`ma-test-26022`, `ma-test-vol-26022`), port 18899. Both were deleted after the tests (0 containers / 0 volumes left).
Existing containers, images and volumes, including `ai-accounts`, were not touched. No account was logged in.

Build: `docker buildx build --platform linux/amd64,linux/arm64 -t multi-account:1.0 --load ./MultiAccountDevtool` → exit 0, **1120 s**
(amd64 reused layer cache from an earlier amd64 probe build. arm64 built in full under QEMU.)
Size: linux/amd64 4.95 GB on disk (content 1.34 GB) · linux/arm64 1.33 GB (content 1.33 GB) · total 6.28 GB

## linux/amd64 (native)

| Item | Evidence | Result |
|---|---|---|
| No login data in the image | `/root` holds `.bashrc .ipython .jupyter .launchpadlib .npm(12K cache) .profile .ssh(empty) ai-accounts`. `ai-accounts` is empty. No `.claude*`/`.codex`/`.gemini`/auth/token files | PASS |
| installer runs on container start | `/var/log/install-ai-accounts.log`: `new_items=36` | PASS |
| yolo1..5 / cyolo1..5 / gyolo1..5 `--version` (15 commands) | 15/15 · `2.1.330 (Claude Code)` · `codex-cli 0.171.0` · `1.5.15` | PASS |
| Each account has its own config root | stub CLIs print env vars → 15 distinct roots `/root/ai-accounts/.{Claude/yolo,Codex/cyolo,Gemini/gyolo}N`. `"a b" c` is passed through. The shell's `HOME` stays `/root` | PASS |
| skill shared-check: every account points to one file in that CLI's shared folder | `readlink -f` for all 5 accounts → `.Claude/shared/skills/shared-check/SKILL.md`, `.Codex/shared/…`, `.Gemini/shared/…` (one file per CLI). `SHARED_SKILL_OK-<tool>-<16hex>` is found in that one file only | PASS |
| `cyolo1 mcp list` shows playwright | `playwright /usr/bin/playwright-mcp … enabled` | PASS |
| `gyolo1 mcp list` shows playwright | `playwright stdio enabled /usr/bin/playwright-mcp …` | PASS |
| Playwright MCP over stdio → example.com + screenshot | JSON-RPC initialize → server `Playwright 1.66.0-alpha-2026-11-18`, `browser_navigate` page contains "Example Domain", `browser_take_screenshot` → image/png 83,348 bytes (image checked) | PASS |
| installer round 2 keeps existing files | `new_items=0`. sha256 of 49 files/links identical before and after. User edits (`cyolo2/config.toml`, `yolo2/settings.json`) kept | PASS |
| `.bashrc` not modified | sha256 `34fbc467…` = image original (after start + round 2) | PASS |
| Delete container, create it again, volume data still there | marker file, skill sha `b5aa0d5b…` and user edit all still present after `rm -f` + `run`. installer `new_items=0` | PASS |
| JupyterLab `/lab` | `GET http://localhost:18899/lab → 200` | PASS |
| Commands work in JupyterLab Terminal (`bash -l`) and `docker exec` | `/usr/local/bin/yolo1 cyolo1 gyolo1 install-ai-accounts` · `sh -c command -v gyolo5` → `/usr/local/bin/gyolo5` | PASS |
| Docker-in-Docker still works | `docker info` inside the container: `29.10.0 overlayfs` | PASS |
| Login / using a skill in a real session / `/mcp` in Claude | needs a login. `gyolo1 models` → "Please sign in…" | SKIP |

## linux/arm64 (QEMU emulation, `--platform linux/arm64`)

| Item | Evidence | Result |
|---|---|---|
| `uname -m` | `aarch64` | PASS |
| 15 commands `--version` | 15/15 · `2.1.330 (Claude Code)` · `codex-cli 0.171.0` · `1.5.15` | PASS |
| No login data in the image | `/root/ai-accounts` empty (0 items) | PASS |
| Login-related items | needs a login | SKIP |
