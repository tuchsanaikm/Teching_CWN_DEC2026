#!/usr/bin/env python3
"""Print status/ssh info of our 3 nodes (never prints keys)."""
import json,subprocess,sys
IDS=[l.split()[0] for l in open(sys.argv[1])] if len(sys.argv)>1 else []
out=json.loads(subprocess.run(['vastai','show','instances','--raw'],capture_output=True,text=True).stdout)
for i in out:
    if not str(i.get('label','')).startswith('vapp-lab5-3dp-'): continue
    ports=i.get('ports') or {}
    pm={k:v[0]['HostPort'] for k,v in ports.items() if v}
    print(i['label'],i['id'],i.get('actual_status'),i.get('public_ipaddr'),pm,round(i.get('dph_total') or 0,4),(i.get('status_msg') or '')[:70].strip())
