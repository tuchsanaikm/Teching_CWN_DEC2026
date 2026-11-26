#!/bin/bash
# show status of the two lab instances (never prints keys)
cd /workspace/vastapp_lab; .venv/bin/vastai show instances --raw 2>/dev/null | python3 -c "
import json,sys
for i in json.load(sys.stdin):
    if 'mp' in (i.get('label') or ''): print(i['id'],i.get('label'),i.get('actual_status'),i.get('intended_status'),i.get('public_ipaddr'),{k:v[0]['HostPort'] for k,v in (i.get('ports') or {}).items()}, round(i.get('dph_total') or 0,3))
"
