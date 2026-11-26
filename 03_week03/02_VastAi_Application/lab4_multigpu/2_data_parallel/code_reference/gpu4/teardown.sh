#!/bin/bash
# Destroy every instance labelled exactly vapp-lab4-dp4 (and nothing else), verify it is gone,
# then save the charges billed to that label. Never prints the API key.
#   teardown.sh            snapshot + destroy + verify + charges
#   teardown.sh charges    only refresh results/billing/charges.json
export PATH=$PATH:~/.local/bin
LABEL=vapp-lab4-dp4
B=$(cd "$(dirname "$0")/.." && pwd)/results/billing
mkdir -p "$B"

ids() {  # ids of instances carrying exactly our label
  vastai show instances --raw | python3 -c "
import sys, json
print(' '.join(str(i['id']) for i in json.load(sys.stdin) if i.get('label') == '$LABEL'))"
}

charges() {  # all charge rows of the last 7 days whose label is ours (paginated)
  python3 - "$B" "$LABEL" <<'EOF'
import json, subprocess, sys, time
out, label = sys.argv[1], sys.argv[2]
rows, token = [], None
while True:
    cmd = ["vastai", "show", "invoices-v1", "--charges", "--charge-type", "instance", "--limit", "100", "--raw"]
    if token:
        cmd += ["--next-token", token]
    page = json.loads(subprocess.run(cmd, capture_output=True, text=True, check=True).stdout)
    rows += page.get("results", [])
    token = page.get("next_token")
    if not token or not page.get("results"):
        break
mine = [r for r in rows if (r.get("metadata") or {}).get("label") == label]
json.dump({"fetched_at": time.time(), "label": label, "charges": mine}, open(f"{out}/charges.json", "w"), indent=1)
print(f"charge rows for {label}: {len(mine)}  total ${sum(r['amount'] for r in mine):.3f}")
EOF
}

if [ "$1" = charges ]; then charges; exit 0; fi

IDS=$(ids)
echo "instances labelled $LABEL: ${IDS:-none}"
for ID in $IDS; do
  # snapshot of the billing-relevant fields only (no tokens / keys are stored)
  vastai show instance "$ID" --raw | python3 -c "
import sys, json, time
d = json.load(sys.stdin)
keep = ['id', 'label', 'machine_id', 'gpu_name', 'num_gpus', 'actual_status', 'start_date', 'duration', 'dph_total',
        'dph_base', 'storage_cost', 'storage_total_cost', 'disk_space', 'inet_down_cost', 'inet_up_cost',
        'inet_down_billed', 'inet_up_billed', 'geolocation', 'image_uuid']
s = {k: d.get(k) for k in keep}
assert s['label'] == '$LABEL', s['label']
s['snapshot_time'] = time.time()
s['age_sec_at_snapshot'] = s['snapshot_time'] - s['start_date']
json.dump(s, open('$B/instance_before_destroy.json', 'w'), indent=1)
print('snapshot', s['id'], s['label'], s['actual_status'], 'age %.1f min' % (s['age_sec_at_snapshot'] / 60))" || { echo "label check failed for $ID - not destroying"; exit 1; }
  vastai destroy instance "$ID" -y
  date +%s > "$B/destroy_time.txt"
done

for n in $(seq 1 20); do
  LEFT=$(ids)
  [ -z "$LEFT" ] && { echo "VERIFIED: no instance labelled $LABEL remains"; break; }
  echo "still present: $LEFT"; sleep 6
done
[ -n "$LEFT" ] && { echo "ERROR: $LEFT still exists"; exit 1; }
vastai show instances --raw | python3 -c "
import sys, json
d = json.load(sys.stdin)
json.dump({'remaining_instances': [{'id': i['id'], 'label': i.get('label')} for i in d]}, open('$B/after_destroy.json', 'w'), indent=1)
print('remaining instances in account (untouched):', [(i['id'], i.get('label')) for i in d])"
charges
