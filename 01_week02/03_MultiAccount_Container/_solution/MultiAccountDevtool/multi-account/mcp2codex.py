#!/usr/bin/env python3
"""แปลงไฟล์ mcp.json (รูปแบบ mcpServers) เป็นอาร์กิวเมนต์ -c ของ Codex CLI
พิมพ์ทีละบรรทัด:  -c  แล้วตามด้วย  mcp_servers.<name>={command="...",args=[...],env={...}}
(สตริง JSON เป็น TOML basic string ที่ถูกต้อง จึงใช้ json.dumps ได้ตรง ๆ)"""
import json
import re
import sys


def toml(v):
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return json.dumps(v)
    if isinstance(v, str):
        return json.dumps(v)
    if isinstance(v, list):
        return "[" + ",".join(toml(x) for x in v) + "]"
    if isinstance(v, dict):
        return "{" + ",".join(f"{key(k)}={toml(x)}" for k, x in v.items()) + "}"
    raise TypeError(type(v))


def key(k):
    return k if re.fullmatch(r"[A-Za-z0-9_-]+", k) else json.dumps(k)


try:
    servers = json.load(open(sys.argv[1], encoding="utf-8")).get("mcpServers", {})
except Exception as e:  # ไฟล์เสีย → ไม่ส่ง MCP แต่ไม่ทำให้ CLI เปิดไม่ได้
    print(f"[cyolo] warning: cannot read {sys.argv[1]}: {e}", file=sys.stderr)
    sys.exit(0)

for name, cfg in servers.items():
    cfg = {k: v for k, v in cfg.items() if k != "type"}
    print("-c")
    print(f"mcp_servers.{key(name)}={toml(cfg)}")
