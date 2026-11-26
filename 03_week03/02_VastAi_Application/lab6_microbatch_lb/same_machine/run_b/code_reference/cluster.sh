#!/usr/bin/env bash
# LAB 6 - open / inspect / close the whole system with one command (run ON the rented machine).
#
#   cluster.sh up [--gpus 1|2] [--per-gpu N] [--mode single|micro] [--lb rr|lc|p2c] [--slow-gpu G --slow-factor F]
#                 [--failover default|on|off]
#                                                   default: --gpus 1 --per-gpu 1 --mode single --lb rr, no slow GPU
#   cluster.sh status
#   cluster.sh down
#   cluster.sh kill-gpu G        a GPU "dies": kill -9 every server of GPU G at once (no clean shutdown, NGINX is
#                                not told; the other GPU and NGINX keep running). "up" brings the system back.
#
#   --lb rr = Round Robin (requests go to the servers in turn)      --lb lc = Least Connections (NGINX least_conn:
#             the server with the fewest unanswered requests gets the next one).
#   --lb p2c = Power of Two Choices (NGINX "random two least_conn": pick 2 servers at random, the one of the two
#             with fewer unanswered requests gets the next one). Between rr / lc / p2c ONLY this one line of
#             nginx.conf changes. After the start the method is checked in the config NGINX really loaded
#             (nginx -T of the mounted file -> logs/nginx/running_config.txt).
#   --slow-gpu G --slow-factor F = every server of GPU G takes F times as long for each model call (a slower GPU;
#             server.py MODEL_SLOWDOWN). Without these two options no server is slowed down.
#   --failover = what NGINX does when a server fails (see the FAILOVER comment in nginx.conf):
#             on  = protect: a failed request is sent again to another server (proxy_next_upstream error timeout
#                   non_idempotent) and a failed server gets no requests for 10 s (max_fails=1 fail_timeout=10s)
#             off = no protection: no retry (proxy_next_upstream off -> the user gets 502), dead servers stay in
#                   the rotation (max_fails=0)
#             default (or option left out) = the settings of all capacity measurements, nothing changed
#
# up = stop the old system -> start N detect servers on every chosen GPU (127.0.0.1 only)
#      -> wait until EVERY server is ready -> start NGINX (nginx:1.27 in udocker) on port 8080 -> say READY.
# Server ports: GPU0 = 8101, 8102, ...   GPU1 = 8201, 8202, ...
set -u
CODE=$(cd "$(dirname "$0")" && pwd)
BASE=$(dirname "$CODE")                      # /workspace/lab6
LOGS=$BASE/logs
NLOG=$LOGS/nginx
KEYFILE=$BASE/api_key.env
CONF=$CODE/nginx.conf
STATE=$LOGS/cluster.state
LB_PORT=8080
IMAGE=nginx:1.27
CNAME=lab6-nginx
EXECMODE=${NGINX_EXECMODE:-F3}               # udocker engine: F3 = fakechroot (no ptrace, fast); P1 = proot
READY_TIMEOUT=${READY_TIMEOUT:-600}
UD="udocker --allow-root"
mkdir -p "$LOGS" "$NLOG"

say()  { echo "[cluster] $*"; }
die()  { echo "[cluster] ERROR: $*" >&2; exit 1; }
http() { curl -s -o /dev/null -m 3 -w '%{http_code}' "$1" 2>/dev/null; }
port_of() { echo $(( 8000 + 100 * ($1 + 1) + $2 )); }      # port_of <gpu> <k>

# ---------------------------------------------------------------- API key
ensure_key() {   # random the first time, the same value on every later start; never printed
  if [ ! -s "$KEYFILE" ]; then
    ( umask 077; python3 -c "import secrets; print('API_KEY=' + secrets.token_urlsafe(32))" > "$KEYFILE" )
    say "API key: created (first start) -> $KEYFILE"
  else
    say "API key: reusing the existing one in $KEYFILE"
  fi
  chmod 600 "$KEYFILE"
}

# ---------------------------------------------------------------- stop
nginx_pids() { pgrep -f '^nginx: (master|worker)' 2>/dev/null; }
server_pids() { pgrep -f 'uvicorn server:app' 2>/dev/null; }

stop_all() {
  local quiet=${1:-}
  local n; n=$(nginx_pids | wc -l); local s; s=$(server_pids | wc -l)
  # NGINX first: the door closes before the servers behind it go away
  if [ -s "$NLOG/nginx.pid" ]; then kill -QUIT "$(cat "$NLOG/nginx.pid")" 2>/dev/null; fi
  for _ in 1 2 3 4 5 6; do [ -z "$(nginx_pids)" ] && break; sleep 0.5; done
  [ -n "$(nginx_pids)" ] && kill -9 $(nginx_pids) 2>/dev/null
  pkill -f "udocker.* run .*$CNAME" 2>/dev/null
  if [ -n "$(server_pids)" ]; then
    kill $(server_pids) 2>/dev/null
    for _ in $(seq 1 20); do [ -z "$(server_pids)" ] && break; sleep 0.5; done
    [ -n "$(server_pids)" ] && kill -9 $(server_pids) 2>/dev/null
  fi
  rm -f "$LOGS"/server_*.pid "$NLOG/nginx.pid" "$STATE"
  sleep 1
  [ -n "$(server_pids)$(nginx_pids)" ] && die "some processes are still alive"
  [ -z "$quiet" ] && say "stopped: $n nginx processes, $s servers"
  return 0
}

# ---------------------------------------------------------------- nginx
write_block() {   # write_block <MARKER> : replace the lines between "# BEGIN <MARKER>" and "# END <MARKER>" by stdin
  local m=$1 tmp; tmp=$(mktemp)
  [ "$(grep -c "^ *# BEGIN $m" "$CONF")" = 1 ] && [ "$(grep -c "^ *# END $m" "$CONF")" = 1 ] || die "markers $m missing in $CONF"
  { sed -n "1,/^ *# BEGIN $m/p" "$CONF"; cat; sed -n "/^ *# END $m/,\$p" "$CONF"; } > "$tmp"
  cat "$tmp" > "$CONF"; rm -f "$tmp"
}

write_upstreams() {   # write_upstreams <gpus> <per_gpu> <failover> : the server list of the upstream block
  local gpus=$1 per=$2 opt="" k g
  case "$3" in
    on)  opt=" max_fails=1 fail_timeout=10s";;   # 1 failure -> no requests to this server for 10 s
    off) opt=" max_fails=0";;                    # failures are not counted: a dead server stays in the rotation
  esac
  for k in $(seq 1 "$per"); do              # gpu0, gpu1, gpu0, gpu1 ... so round robin alternates the GPUs
    for g in $(seq 0 $((gpus - 1))); do
      printf '        server 127.0.0.1:%s%s;           # gpu%s server %s\n' "$(port_of "$g" "$k")" "$opt" "$g" "$k"
    done
  done | write_block SERVERS
}

write_failover() {   # write_failover default|on|off : may a failed request go to another server?
  case "$1" in
    on)  printf '            proxy_next_upstream error timeout non_idempotent;   # failed -> next server, also a POST already sent\n';;
    off) printf '            proxy_next_upstream off;                 # never retry: the user gets the 502\n';;
    *)   printf '            proxy_next_upstream error timeout;       # server unreachable -> try the next one\n';;
  esac | write_block FAILOVER
}

write_lb() {   # write_lb rr|lc|p2c : the ONLY line of nginx.conf that differs between the balancing methods
  case "$1" in
    lc)  printf '        least_conn;                      # Least Connections\n';;
    p2c) printf '        random two least_conn;           # Power of Two Choices\n';;
    *)   printf '        # (no directive)                 # Round Robin\n';;
  esac | write_block LB
}

check_lb() {   # check_lb rr|lc|p2c <file> : does this config select exactly the asked method? (comments do not count)
  local nlc np2c nother
  nlc=$(grep -Ec '^[[:space:]]*least_conn;' "$2")
  np2c=$(grep -Ec '^[[:space:]]*random[[:space:]]+two[[:space:]]+least_conn;' "$2")
  # any other balancing directive (hash, ip_hash, random without "two least_conn") must not be there
  nother=$(grep -E '^[[:space:]]*(ip_hash|hash|random)([[:space:]]|;)' "$2" | grep -Evc '^[[:space:]]*random[[:space:]]+two[[:space:]]+least_conn;')
  case "$1" in
    lc)  [ "$nlc" = 1 ] && [ "$np2c" = 0 ] && [ "$nother" = 0 ];;
    p2c) [ "$nlc" = 0 ] && [ "$np2c" = 1 ] && [ "$nother" = 0 ];;
    *)   [ "$nlc" = 0 ] && [ "$np2c" = 0 ] && [ "$nother" = 0 ];;
  esac
}

ensure_container() {
  command -v udocker >/dev/null || pip install -q --root-user-action=ignore udocker >/dev/null 2>&1 \
    || die "cannot install udocker"
  [ -d "$HOME/.udocker/bin" ] || $UD install >/dev/null 2>&1
  if ! $UD ps 2>/dev/null | grep -q "$CNAME"; then
    $UD images 2>/dev/null | grep -q "^$IMAGE" || { say "pulling $IMAGE"; $UD pull "$IMAGE" >/dev/null 2>&1 || die "pull failed"; }
    $UD create --name="$CNAME" "$IMAGE" >/dev/null 2>&1 || die "udocker create failed"
    say "container $CNAME created from $IMAGE"
  fi
  $UD setup --execmode="$EXECMODE" "$CNAME" >/dev/null 2>&1 || die "udocker setup --execmode=$EXECMODE failed"
}

nginx_run() {   # nginx_run <nginx args...> : run the nginx binary of the image with our config mounted
  $UD run --nobanner --entrypoint="" \
      -v "$CONF":/etc/nginx/nginx.conf -v "$NLOG":/var/log/nginx "$CNAME" /usr/sbin/nginx "$@"
}

start_nginx() {
  ensure_container
  nginx_run -t > "$NLOG/configtest.log" 2>&1 || { cat "$NLOG/configtest.log"; stop_all quiet; die "nginx.conf is not valid"; }
  # the config as the nginx binary itself reads it from the mounted file (the same file the server below loads)
  # (udocker adds its own "Warning: this container exposes TCP/IP ports" after the dump: not part of the config)
  nginx_run -T 2>"$NLOG/running_config.err" | grep -v '^Warning: this container exposes' > "$NLOG/running_config.raw"
  [ "${PIPESTATUS[0]}" = 0 ] || { stop_all quiet; die "nginx -T failed"; }
  sed -e :a -e '/^\n*$/{$d;N;ba' -e '}' "$NLOG/running_config.raw" > "$NLOG/running_config.txt"   # drop empty lines at the end
  rm -f "$NLOG/running_config.raw"
  nohup setsid $UD run --nobanner --entrypoint="" \
      -v "$CONF":/etc/nginx/nginx.conf -v "$NLOG":/var/log/nginx "$CNAME" /usr/sbin/nginx -g 'daemon off;' \
      > "$NLOG/container.log" 2>&1 < /dev/null &
  for _ in $(seq 1 60); do
    [ "$(http "http://127.0.0.1:$LB_PORT/lb/health")" = 200 ] && return 0
    sleep 0.5
  done
  tail -20 "$NLOG/container.log" "$NLOG/error.log" 2>/dev/null
  stop_all quiet
  die "NGINX did not open port $LB_PORT"
}

# ---------------------------------------------------------------- up
cmd_up() {
  local gpus=1 per=1 mode=single lb=rr slow_gpu="" slow_factor="" failover=default
  while [ $# -gt 0 ]; do
    case "$1" in
      --gpus)    gpus=${2:-}; shift 2;;
      --per-gpu) per=${2:-};  shift 2;;
      --mode)    mode=${2:-}; shift 2;;
      --lb)      lb=${2:-};   shift 2;;
      --slow-gpu)    slow_gpu=${2:-};    shift 2;;
      --slow-factor) slow_factor=${2:-}; shift 2;;
      --failover)    failover=${2:-};    shift 2;;
      *) die "unknown option $1 (see the top of this file)";;
    esac
  done
  case "$gpus" in 1|2) ;; *) die "--gpus must be 1 or 2";; esac
  case "$per" in ''|*[!0-9]*) die "--per-gpu must be a number";; esac
  [ "$per" -ge 1 ] && [ "$per" -le 99 ] || die "--per-gpu must be 1..99"
  case "$mode" in single|micro) ;; *) die "--mode must be single or micro";; esac
  case "$lb" in rr|lc|p2c) ;; *) die "--lb must be rr (Round Robin), lc (Least Connections) or p2c (Power of Two Choices)";; esac
  case "$failover" in default|on|off) ;; *) die "--failover must be default, on or off";; esac
  if [ -n "$slow_gpu$slow_factor" ]; then
    [ -n "$slow_gpu" ] && [ -n "$slow_factor" ] || die "--slow-gpu and --slow-factor go together"
    case "$slow_gpu" in ''|*[!0-9]*) die "--slow-gpu must be a GPU index";; esac
    [ "$slow_gpu" -lt "$gpus" ] || die "--slow-gpu $slow_gpu is not one of the $gpus GPU(s) in use (0..$((gpus - 1)))"
    echo "$slow_factor" | grep -Eq '^[0-9]+(\.[0-9]+)?$' || die "--slow-factor must be a number >= 1"
    python3 -c "import sys; sys.exit(0 if 1 <= float('$slow_factor') <= 100 else 1)" || die "--slow-factor must be 1..100"
    # factor 1 = not slowed: same as leaving the options out
    python3 -c "import sys; sys.exit(0 if float('$slow_factor') == 1 else 1)" && { slow_gpu=""; slow_factor=""; }
  fi
  local have; have=$(nvidia-smi --query-gpu=index --format=csv,noheader | wc -l)
  [ "$gpus" -le "$have" ] || die "asked for $gpus GPUs, machine has $have"
  [ -f "$BASE/best.pt" ] || die "model $BASE/best.pt not found"

  local t0; t0=$(date +%s)
  local lbname="Round Robin"; [ "$lb" = lc ] && lbname="Least Connections"; [ "$lb" = p2c ] && lbname="Power of Two Choices"
  local slowtxt="none"; [ -n "$slow_gpu" ] && slowtxt="gpu$slow_gpu x$slow_factor"
  say "up: gpus=$gpus per-gpu=$per mode=$mode lb=$lb ($lbname) slow=$slowtxt failover=$failover  ($((gpus * per)) servers)"
  stop_all quiet
  ensure_key
  write_upstreams "$gpus" "$per" "$failover"
  write_lb "$lb"
  write_failover "$failover"

  # ---- start every server (they load and warm up in parallel) ----
  local ports=() g k port
  for k in $(seq 1 "$per"); do
    for g in $(seq 0 $((gpus - 1))); do
      port=$(port_of "$g" "$k")
      (
        cd "$CODE"
        set -a; . "$KEYFILE"; set +a          # API_KEY goes in by environment, not on the command line
        export CUDA_VISIBLE_DEVICES=$g MODE=$mode SERVER_ID="gpu$g-$port" MODEL_PATH=$BASE/best.pt \
               IMGSZ=640 CONF=0.35 MAX_BATCH=32 MAX_WAIT_MS=5 YOLO_VERBOSE=False \
               OMP_NUM_THREADS=${OMP_NUM_THREADS:-4} MODEL_SLOWDOWN=1
        [ "$g" = "$slow_gpu" ] && export MODEL_SLOWDOWN=$slow_factor      # only the servers of the slow GPU
        # more than 1 server on a GPU: each may use at most 0.85 / per-gpu of its memory (PyTorch part;
        # the CUDA context of each process, ~0.4 GB, comes on top), so the parallel warm-up cannot run out
        [ "$per" -gt 1 ] && export GPU_MEM_FRACTION=$(python3 -c "print(round(0.85 / $per, 4))")
        nohup setsid python -m uvicorn server:app --host 127.0.0.1 --port "$port" --workers 1 --no-access-log \
              > "$LOGS/server_$port.log" 2>&1 < /dev/null &
        echo $! > "$LOGS/server_$port.pid"
      )
      ports+=("$port")
    done
  done

  # ---- wait until EVERY server answers /health = 200 (the server opens its port only after warm-up) ----
  local ready=0 total=${#ports[@]} last=-1
  while :; do
    ready=0
    for port in "${ports[@]}"; do
      if [ "$(http "http://127.0.0.1:$port/health")" = 200 ]; then ready=$((ready + 1))
      elif ! kill -0 "$(cat "$LOGS/server_$port.pid")" 2>/dev/null; then
        tail -15 "$LOGS/server_$port.log"; stop_all quiet; die "server on port $port died during start"
      fi
    done
    [ "$ready" != "$last" ] && { say "servers ready: $ready/$total  ($(( $(date +%s) - t0 ))s)"; last=$ready; }
    [ "$ready" = "$total" ] && break
    [ $(( $(date +%s) - t0 )) -gt "$READY_TIMEOUT" ] && { stop_all quiet; die "timeout: only $ready/$total servers ready"; }
    sleep 1
  done

  # ---- only now open the door ----
  start_nginx
  # every server must also be reachable THROUGH nginx (round robin walks over all of them; p2c picks at
  # random, so it may need many more requests: stop as soon as every server was seen)
  local seen="" i up
  for i in $(seq 1 $((total * 40))); do
    up=$(curl -s -o /dev/null -m 5 -D - "http://127.0.0.1:$LB_PORT/health" | tr -d '\r' | awk 'tolower($1)=="x-upstream:"{print $2}')
    case " $seen " in *" $up "*) ;; *) seen="$seen $up";; esac
    [ "$(echo $seen | wc -w)" = "$total" ] && break
  done
  [ "$(echo $seen | wc -w)" = "$total" ] || { say "seen through nginx:$seen"; stop_all quiet; die "nginx does not reach all $total servers"; }

  # the running NGINX must use the asked method. Checked in the config NGINX really loaded: the nginx -T dump
  # taken when it started, which must still be the file on disk (nobody changed it after the start).
  check_lb "$lb" "$CONF" || { stop_all quiet; die "nginx.conf does not match --lb $lb"; }
  check_lb "$lb" "$NLOG/running_config.txt" || { stop_all quiet; die "the config NGINX loaded does not match --lb $lb"; }
  grep -v '^# configuration file ' "$NLOG/running_config.txt" | cmp -s - "$CONF" \
    || { stop_all quiet; die "the config NGINX loaded (nginx -T) is not $CONF"; }
  say "method check: --lb $lb ($lbname) = line '$(sed -n '/# BEGIN LB/,/# END LB/p' "$NLOG/running_config.txt" | sed -n 2p | sed 's/^ *//; s/  *#.*//')' in the config NGINX loaded"
  # ... and the asked failover settings (in the file the running NGINX was started with)
  local nmf nni noff
  nmf=$(grep -c '^ *server 127.*max_fails=1 fail_timeout=10s;' "$CONF"); nni=$(grep -c '^ *proxy_next_upstream error timeout non_idempotent;' "$CONF")
  noff=$(( $(grep -c '^ *server 127.*max_fails=0;' "$CONF") + $(grep -c '^ *proxy_next_upstream off;' "$CONF") ))
  case "$failover" in
    on)  [ "$nmf" = "$total" ] && [ "$nni" = 1 ] && [ "$noff" = 0 ];;
    off) [ "$noff" = $((total + 1)) ] && [ "$nmf" = 0 ] && [ "$nni" = 0 ];;
    *)   [ "$noff" = 0 ] && [ "$nmf" = 0 ] && [ "$nni" = 0 ] && [ "$(grep -c '^ *proxy_next_upstream error timeout;' "$CONF")" = 1 ];;
  esac || { stop_all quiet; die "nginx.conf does not match --failover $failover"; }
  # a slowed server says so in /health: check every server has the factor it was started with
  local want got
  for port in "${ports[@]}"; do
    want=1; [ -n "$slow_gpu" ] && [ "$port" -ge "$(port_of "$slow_gpu" 1)" ] && [ "$port" -le "$(port_of "$slow_gpu" 99)" ] && want=$slow_factor
    got=$(curl -s -m 3 "http://127.0.0.1:$port/health" | python3 -c "import json,sys; print(json.load(sys.stdin).get('slowdown'))")
    python3 -c "import sys; sys.exit(0 if float('$got') == float('$want') else 1)" 2>/dev/null \
      || { stop_all quiet; die "server $port has slowdown=$got, wanted $want"; }
  done

  printf 'GPUS=%s\nPER_GPU=%s\nMODE=%s\nLB=%s\nSLOW_GPU=%s\nSLOW_FACTOR=%s\nFAILOVER=%s\nPORTS="%s"\nSTARTED_UTC=%s\nSTART_SECONDS=%s\n' \
         "$gpus" "$per" "$mode" "$lb" "${slow_gpu:-none}" "${slow_factor:-1}" "$failover" "${ports[*]}" "$(date -u +%FT%TZ)" "$(( $(date +%s) - t0 ))" > "$STATE"
  say "READY in $(( $(date +%s) - t0 ))s: nginx :$LB_PORT -> $total server(s) [${ports[*]}] mode=$mode lb=$lb slow=$slowtxt failover=$failover"
}

# ---------------------------------------------------------------- kill-gpu
cmd_kill_gpu() {   # every server of one GPU dies at the same moment: SIGKILL, nothing is told to NGINX
  local g=${1:-} port pid pids=() ports=()
  [ -f "$STATE" ] || die "system is not started by cluster.sh"
  LB=rr; FAILOVER=default; . "$STATE"
  case "$g" in ''|*[!0-9]*) die "kill-gpu needs a GPU index (0..$((GPUS - 1)))";; esac
  [ "$g" -lt "$GPUS" ] || die "GPU $g is not in use (0..$((GPUS - 1)))"
  for port in $PORTS; do
    [ "$port" -ge "$(port_of "$g" 1)" ] && [ "$port" -le "$(port_of "$g" 99)" ] || continue
    ports+=("$port")
    pid=$(cat "$LOGS/server_$port.pid" 2>/dev/null)
    # only a pid that really is the server of this port (a pid file can be stale)
    [ -n "$pid" ] && tr '\0' ' ' < "/proc/$pid/cmdline" 2>/dev/null | grep -q -- "uvicorn server:app .*--port $port " && pids+=("$pid")
  done
  [ ${#pids[@]} -gt 0 ] || die "no running server of gpu$g found (ports ${ports[*]})"
  local t; t=$(date -u +%FT%T.%3NZ)
  kill -9 "${pids[@]}" 2>/dev/null           # one system call list: all of them die together
  local left=1 i
  for i in $(seq 1 50); do
    left=0; for pid in "${pids[@]}"; do kill -0 "$pid" 2>/dev/null && left=$((left + 1)); done
    [ "$left" = 0 ] && break; sleep 0.02
  done
  [ "$left" = 0 ] || die "$left server(s) of gpu$g are still alive"
  echo "KILLED_GPU=$g KILLED_UTC=$t KILLED_PORTS=\"${ports[*]}\"" >> "$STATE"
  say "kill-gpu $g at $t: ${#pids[@]} server(s) killed with SIGKILL [${ports[*]}]; nginx failover=$FAILOVER; other servers and NGINX untouched"
}

# ---------------------------------------------------------------- status
cmd_status() {
  if [ -f "$STATE" ]; then
    LB=rr; SLOW_GPU=none; SLOW_FACTOR=1; FAILOVER=default; KILLED_GPU=""
    . "$STATE"; say "layout: gpus=$GPUS per-gpu=$PER_GPU mode=$MODE lb=$LB slow-gpu=$SLOW_GPU slow-factor=$SLOW_FACTOR failover=$FAILOVER started=$STARTED_UTC${KILLED_GPU:+ KILLED: gpu$KILLED_GPU at $KILLED_UTC}"
  else say "layout: (system is not started by cluster.sh)"; PORTS=""; fi
  local bad=0 port pid code info
  for port in $PORTS; do
    pid=$(cat "$LOGS/server_$port.pid" 2>/dev/null)
    code=$(http "http://127.0.0.1:$port/health")
    info=$(curl -s -m 3 "http://127.0.0.1:$port/health" 2>/dev/null | python3 -c "
import json,sys
try:
    h=json.load(sys.stdin); print(h['server'],h['mode'],h['device'],'max_batch=%s'%h['max_batch'],'slowdown=%s'%h.get('slowdown'),'queue=%s'%h['queue_len'])
except Exception: print('-')")
    kill -0 "$pid" 2>/dev/null && [ "$code" = 200 ] || bad=$((bad + 1))
    echo "  server 127.0.0.1:$port pid=${pid:--} health=$code $info"
  done
  local nmaster; nmaster=$(cat "$NLOG/nginx.pid" 2>/dev/null)
  code=$(http "http://127.0.0.1:$LB_PORT/lb/health")
  echo "  nginx  0.0.0.0:$LB_PORT pid=${nmaster:--} processes=$(nginx_pids | wc -l) health=$code upstreams=$(grep -c '^ *server 127' "$CONF") lb_line="$(sed -n '/# BEGIN LB/,/# END LB/p' "$CONF" | sed -n 2p | sed 's/^ *//; s/  *#.*//')""
  [ "$code" = 200 ] || bad=$((bad + 1))
  echo "  listening: $(python3 - <<'EOF'
import re, socket
out = []
for line in open('/proc/net/tcp').read().splitlines()[1:]:
    f = line.split()
    if f[3] != '0A': continue
    ip, port = f[1].split(':')
    port = int(port, 16)
    if port == 8080 or 8100 < port < 8300:
        out.append('%s:%d' % (socket.inet_ntoa(bytes.fromhex(ip)[::-1]), port))
print(' '.join(sorted(set(out))) or '-')
EOF
)"
  nvidia-smi --query-gpu=index,memory.used,utilization.gpu --format=csv,noheader | sed 's/^/  gpu /'
  if [ -z "$PORTS" ]; then say "status: DOWN"; return 3; fi
  [ "$bad" = 0 ] && say "status: OK" || { say "status: $bad problem(s)"; return 1; }
}

case "${1:-}" in
  up)     shift; cmd_up "$@";;
  status) cmd_status;;
  down)   stop_all;;
  kill-gpu) shift; cmd_kill_gpu "$@";;
  *) sed -n '2,25p' "$0"; exit 2;;
esac
