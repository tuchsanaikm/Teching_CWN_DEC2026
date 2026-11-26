#!/usr/bin/env python3
"""Load generator for the shop-bot cluster (run ON machine 1, against NGINX port 8080).

How many customers can chat at the same time, and how fast does each one get an answer?

A simulated user is a closed loop: ask -> read the streamed answer to the end -> ask the next
question at once. N users are split over several processes so the load generator is not the brake.

  capacity mode : loadgen.py capacity --name cap_dp --levels 8,16,32,64,128,256 \
                      --ttft-p95-max 1.0 --speed-p5-min 20
       1 scan     : walk the levels until 2 levels in a row fail (a failed level is measured once more)
       2 estimate : straight line between last passing and first failing level -> N where the limit is hit
       3 refine   : measure there, estimate again, until pass and fail are <= 5 % of N apart (at least 2)
  single mode   : loadgen.py single --name mix20 --users 64 --duration 120 --long-pct 20
       one N for a fixed time, per-second results; --long-pct = share of "detailed answer" questions

Per question: TTFT, speed (tokens/s after the first token), total time, tokens, replica that answered.
Per level   : TTFT p50/p95, speed p50/p5, throughput (tokens/s of all users), finished questions/s,
              errors; per replica: questions, running/waiting every second, TTFT, speed;
              machine: GPU % and temperature per card, CPU of the load generator and of NGINX.
Result      : results/<name>.json   (the API key is read from a file and never printed or stored)
"""
import argparse, asyncio, json, math, multiprocessing as mp, os, random, re, subprocess, sys, threading, time
import http.client, urllib.parse

# ----------------------------------------------------------------------------- the dataset
QUESTIONS = [
    "ใบเสร็จรับเงินที่ไม่มีเลขประจำตัวผู้เสียภาษีใช้หักภาษีซื้อได้ไหมคะ",
    "ค่าวัตถุดิบร้านอาหารควรจัดอยู่ในหมวดรายจ่ายใดครับ",
    "ภาษีมูลค่าเพิ่ม 7% คิดจากยอดก่อนภาษีหรือหลังภาษีคะ",
    "ใบเสร็จที่ยอดรวมไม่ตรงกับผลรวมรายการย่อยควรตรวจสอบอย่างไรครับ",
    "บิลเงินสดธรรมดาสามารถนำมาลงบัญชีรายจ่ายบริษัทได้หรือไม่คะ",
    "ค่าบริการจัดส่งสินค้าต้องหักภาษี ณ ที่จ่ายกี่เปอร์เซ็นต์ครับ",
    "ใบกำกับภาษีอย่างย่อต่างจากใบกำกับภาษีเต็มรูปอย่างไรคะ",
    "ถ้าใบเสร็จลงวันที่ 1 ของเดือน ควรนับรวมในสรุปรายจ่ายเดือนไหนครับ",
    "ค่าเช่าพื้นที่ร้านค้าต้องหักภาษี ณ ที่จ่ายเท่าไรคะ",
    "ค่าสาธารณูปโภคเช่นค่าน้ำค่าไฟของร้านต้องเก็บเอกสารกี่ปีครับ",
    "ใบเสร็จที่ภาพเบลอจนอ่านยอดรวมไม่ได้ควรจัดการอย่างไรในสำนักงานบัญชีคะ",
    "ลูกค้าส่งใบเสร็จซ้ำสองรอบ ระบบบัญชีควรตรวจสอบจากข้อมูลใดบ้างครับ",
    "ค่าซ่อมแซมอุปกรณ์ในครัวถือเป็นค่าใช้จ่ายหรือสินทรัพย์ถาวรคะ",
    "การปิดงบรายเดือนของร้านอาหารควรกระทบยอดใบเสร็จกับอะไรบ้างครับ",
    "ค่าโฆษณาออนไลน์สามารถขอใบกำกับภาษีเพื่อเครดิตภาษีซื้อได้ไหมคะ",
    "ใบเสร็จที่พิมพ์เป็นปี พ.ศ. 2569 ต้องแปลงเป็นปี ค.ศ. อะไรครับ",
    "ความแตกต่างระหว่างรายจ่ายต้องห้ามกับรายจ่ายที่หักภาษีได้คืออะไรคะ",
    "ถ้าพนักงานบัญชีแก้ไขยอดรวมบนใบเสร็จ ต้องเก็บประวัติการแก้ไขไว้ทำไมครับ",
    "ใบเสร็จที่มีค่าบริการ Service Charge 10% และ VAT 7% คำนวณยอดรวมอย่างไรคะ",
    "ค่าวัสดุสิ้นเปลืองสำนักงาน เช่น กระดาษและหมึกพิมพ์ อยู่หมวดใดครับ",
    "งานด่วนสิ้นเดือนควรจัดลำดับการตรวจใบเสร็จอย่างไรไม่ให้กระทบงานปกติคะ",
    "ใบเสร็จรับเงินจากตลาดสดที่ไม่มีใบกำกับภาษีต้องทำใบสำคัญรับเงินอย่างไรครับ",
    "การตรวจสอบความมั่นใจของ AI อ่านใบเสร็จที่ต่ำกว่า 0.90 ช่วยลดความผิดพลาดอย่างไรคะ",
    "ยอดรวมรายจ่ายเดือนนี้สูงกว่าเดือนก่อน 25% ควรวิเคราะห์จากหมวดใดก่อนครับ",
    "ค่าเดินทางและค่าน้ำมันของพนักงานส่งอาหารเบิกจ่ายด้วยหลักฐานอะไรได้บ้างคะ",
    "ภาษีซื้อต้องห้ามคืออะไร ยกตัวอย่างที่พบบ่อยในร้านอาหารครับ",
    "สรุปรายจ่ายรายเดือนให้ลูกค้าควรส่งออกเป็นไฟล์ CSV รูปแบบใดคะ",
    "ถ้าวันที่บนใบเสร็จไม่ชัดเจนควรตรวจสอบจากหลักฐานประกอบใดบ้างครับ",
    "ค่าจ้างฟรีแลนซ์ออกแบบเมนูร้านอาหารต้องหัก ณ ที่จ่ายกี่เปอร์เซ็นต์คะ",
    "การแยกใบเสร็จตามหมวดรายจ่ายช่วยเจ้าของร้านอาหารวางแผนต้นทุนอย่างไรครับ",
    "ใบเสร็จรับเงินที่ออกเป็นสกุลเงินต่างประเทศต้องแปลงเป็นเงินบาทด้วยอัตราใดคะ",
    "ส่วนลดการค้าบนใบเสร็จควรบันทึกบัญชีอย่างไรให้ยอดตรงกับใบกำกับภาษีครับ",
    "กรณีลูกค้าส่งใบเสร็จเข้ามาพร้อมกัน 100 ใบ ควรจัดคิวการตรวจอย่างไรคะ",
    "เอกสารใบเสร็จอิเล็กทรอนิกส์ e-Tax Invoice มีผลทางกฎหมายเหมือนกระดาษไหมครับ",
    "ค่าประกันภัยร้านค้าควรรับรู้เป็นค่าใช้จ่ายรายเดือนอย่างไรคะ",
    "เหตุใดระบบบัญชีจึงห้ามลูกค้าเห็นยอดใบเสร็จก่อนพนักงานยืนยันครับ",
    "ค่าธรรมเนียมเครื่องรูดบัตร EDC ของร้านอาหารลงบัญชีหมวดไหนคะ",
    "การกระทบยอดจำนวนใบเสร็จรับเข้ากับจำนวนใบที่ยืนยันแล้วมีประโยชน์อย่างไรครับ",
    "ถ้าพบใบเสร็จที่ยอดรวมเป็น 0.00 บาท ควรอนุญาตให้ยืนยันเข้าบัญชีหรือไม่คะ",
    "สรุปขั้นตอนการปิดบัญชีรายเดือนสำหรับสำนักงานบัญชีที่ดูแลลูกค้า 60 รายครับ",
]
assert len(QUESTIONS) == 40

SYSTEM_SHORT = ("คุณเป็นผู้ช่วยบัญชี AI ของ ReceiptDesk ตอบนักบัญชีเป็นภาษาไทย กระชับ ถูกต้อง "
                "และตอบไม่เกิน 3 ประโยค")
SYSTEM_LONG = ("คุณเป็นผู้ช่วยบัญชี AI ของ ReceiptDesk ตอบนักบัญชีเป็นภาษาไทยอย่างละเอียด "
               "อธิบายเป็นข้อ ๆ ครบถ้วน พร้อมแนวทางปฏิบัติทางบัญชีและข้อควรระวัง")
LONG_SUFFIX = " ช่วยอธิบายแบบละเอียดเป็นข้อ ๆ ด้วยนะคะ"
MAX_TOKENS_SHORT, MAX_TOKENS_LONG = 150, 600
REQUEST_TIMEOUT_S = 60.0          # waiting longer than this for one answer = error

HERE = os.path.dirname(os.path.abspath(__file__))


def build_request(model, q_index, long_answer, temperature=0.7):
    """One request body (OpenAI chat-completions format, as served by vLLM)."""
    q = QUESTIONS[q_index]
    return {
        "model": model,                                             # name of the served model
        "messages": [
            {"role": "system", "content": SYSTEM_LONG if long_answer else SYSTEM_SHORT},
            {"role": "user", "content": q + LONG_SUFFIX if long_answer else q},
        ],
        "max_tokens": MAX_TOKENS_LONG if long_answer else MAX_TOKENS_SHORT,   # answer length limit
        "temperature": temperature,
        "stream": True,                                             # send token by token (SSE)
        # usage in every chunk: exact token count at any moment, also when chunks carry >1 token
        "stream_options": {"include_usage": True, "continuous_usage_stats": True},
    }


# ----------------------------------------------------------------------------- one question
async def ask_once(session, url, headers, body, t0, on_tokens=None, keep_text=False, live=None):
    """Send one question, read the stream to the end. Times are seconds relative to t0."""
    rec = {"t_send": time.time() - t0, "status": None, "replica": None, "ttft": None, "t_first": None,
           "t_end": None, "total": None, "n_out": 0, "n_in": None, "speed": None, "err": None}
    t_send = time.perf_counter()
    if live is not None:
        live["rec"] = rec                                           # visible to the caller if we get cancelled
    text = [] if keep_text else None
    n_seen = n_first = 0
    t_first = t_last = None
    try:
        async with asyncio.timeout(REQUEST_TIMEOUT_S):
            async with session.post(url, json=body, headers=headers) as r:
                rec["status"] = r.status
                rec["replica"] = r.headers.get("X-Replica")
                addr = r.headers.get("X-Replica-Addr")              # "a, b" = NGINX passed the question on
                if addr:
                    rec["tries"] = addr.count(",") + 1
                if r.status != 200:
                    rec["err"] = "http_%d" % r.status
                    await r.read()
                else:
                    complete = False
                    async for raw in r.content:                    # one SSE line at a time
                        if not raw.startswith(b"data:"):
                            continue
                        data = raw[5:].strip()
                        if data == b"[DONE]":
                            complete = True
                            break
                        ev = json.loads(data)
                        if "error" in ev:
                            rec["err"] = "stream_error"
                            break
                        piece = None
                        ch = ev.get("choices")
                        if ch:
                            piece = (ch[0].get("delta") or {}).get("content")
                            if ch[0].get("finish_reason"):
                                rec["finish"] = ch[0]["finish_reason"]
                        u = ev.get("usage")
                        if u:
                            rec["n_in"] = u.get("prompt_tokens")
                        if piece:
                            now = time.perf_counter()
                            n_now = (u or {}).get("completion_tokens") or (n_seen + 1)
                            if t_first is None:
                                t_first, n_first = now, n_now
                                rec["ttft"] = now - t_send
                                rec["t_first"] = rec["t_send"] + rec["ttft"]
                            t_last = now
                            if on_tokens and n_now > n_seen:
                                on_tokens(rec["replica"], n_now - n_seen)
                            n_seen = max(n_seen, n_now)
                            if keep_text:
                                text.append(piece)
                        elif u and (u.get("completion_tokens") or 0) > n_seen and not ch:
                            n_seen = u["completion_tokens"]        # final usage-only chunk
                    if rec["err"] is None and t_first is None:
                        rec["err"] = "empty_answer"
                    elif rec["err"] is None and not complete:
                        rec["err"] = "stream_cut"                   # the stream ended without [DONE]
    except TimeoutError:
        rec["err"] = "timeout_60s"
    except asyncio.CancelledError:
        rec["err"] = "open_at_end"                                  # level ended while still in flight
        rec["waited"] = time.perf_counter() - t_send
        rec["n_out"] = n_seen
        raise
    except Exception as e:                                          # connection refused/reset, ...
        rec["err"] = "conn_" + type(e).__name__
    end = time.perf_counter()
    rec["total"] = end - t_send
    rec["t_end"] = rec["t_send"] + rec["total"]
    rec["n_out"] = n_seen
    if rec["err"] is None and t_last is not None and t_last > t_first and n_seen > n_first:
        rec["speed"] = (n_seen - n_first) / (t_last - t_first)     # tokens/s after the first token
    if keep_text:
        rec["answer"] = "".join(text)
    if live is not None:
        live.pop("rec", None)
    return rec


# ----------------------------------------------------------------------------- worker process
async def worker_main(cfg, user_ids, t0, duration, seed):
    import aiohttp
    records, tok, live = [], {}, {}
    url, headers = cfg["url"] + "/v1/chat/completions", cfg["headers"]
    conn = aiohttp.TCPConnector(limit=0, keepalive_timeout=30)
    timeout = aiohttp.ClientTimeout(total=None, sock_connect=10)

    def on_tokens(replica, n):                                      # tokens per (second, replica)
        k = (int(time.time() - t0), replica)
        tok[k] = tok.get(k, 0) + n

    async def user_loop(uid, session):
        """One simulated user: ask, read the whole answer, ask the next question at once."""
        rng = random.Random(seed * 100003 + uid)
        await asyncio.sleep(max(0.0, t0 + rng.random() * cfg["ramp"] - time.time()))   # spread the starts
        while True:
            qi = rng.randrange(len(QUESTIONS))                      # random question
            long_answer = rng.random() * 100.0 < cfg["long_pct"]
            body = build_request(cfg["model"], qi, long_answer, cfg["temperature"])
            slot = live[uid] = {"user": uid, "q": qi, "long": int(long_answer)}
            rec = await ask_once(session, url, headers, body, t0, on_tokens, live=slot)
            rec.update(slot)
            records.append(rec)
            del live[uid]
            if rec["err"] and rec["err"] != "timeout_60s":
                await asyncio.sleep(0.2)                            # do not spin on a dead server

    async with aiohttp.ClientSession(connector=conn, timeout=timeout, auto_decompress=False) as session:
        tasks = [asyncio.create_task(user_loop(u, session)) for u in user_ids]
        await asyncio.sleep(max(0.0, t0 + duration - time.time()))
        for t in tasks:                                             # end of the level: drop what is in flight
            t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
    open_recs = []
    for slot in live.values():                                      # questions still open at the end
        r = slot.pop("rec", None)
        if r is not None:
            r.update(slot)
            open_recs.append(r)
    return records, tok, open_recs


def worker_entry(idx, cfg, user_ids, ready_q, go_ev, t0_val, duration, seed, out_q):
    try:
        try:
            import uvloop
            uvloop.install()
        except Exception:
            pass
        import aiohttp  # noqa: F401  (import before the start signal, it takes a moment)
        ready_q.put(idx)
        go_ev.wait()
        recs, tok, open_recs = asyncio.run(worker_main(cfg, user_ids, t0_val.value, duration, seed + idx))
        out_q.put((idx, recs, [(s, rep, n) for (s, rep), n in tok.items()], open_recs, None))
    except Exception as e:
        out_q.put((idx, [], [], [], "%s: %s" % (type(e).__name__, e)))


# ----------------------------------------------------------------------------- monitors (1 sample/s)
class Monitors:
    """Background threads on the master: replica counters, GPUs, CPU. All samples carry time.time()."""

    def __init__(self, targets, key):
        self.t, self.key = targets, key
        self.stop = threading.Event()
        self.rep = {r["name"]: [] for r in targets["replicas"]}      # (t, running, waiting)
        self.gpu = {}                                                 # "n1:0" -> [(t, util, temp, watt)]
        self.cpu = []                                                 # (t, {"loadgen":..., "nginx":...})
        self.worker_pids = []
        self.threads, self.procs = [], []
        self.lock = threading.Lock()

    def start(self):
        for r in self.t["replicas"]:
            self._th(self._replica_loop, r)
        for g in self.t.get("gpu_sources", []):
            self._th(self._gpu_loop, g)
        self._th(self._cpu_loop)

    def _th(self, fn, *a):
        th = threading.Thread(target=fn, args=a, daemon=True)
        th.start()
        self.threads.append(th)

    def close(self):
        self.stop.set()
        for p in self.procs:
            try:
                p.terminate()
            except Exception:
                pass

    def _tick(self):
        """Sleep to the next whole second so that all monitors sample at the same moments."""
        now = time.time()
        return self.stop.wait(math.floor(now) + 1.0 - now)

    def _replica_loop(self, r):
        u = urllib.parse.urlparse(r["metrics"])
        hdr = {"Authorization": "Bearer " + self.key}
        conn = None
        rx = re.compile(r'^vllm:num_requests_(running|waiting)\{[^}]*\}\s+([0-9.eE+-]+)', re.M)
        while not self._tick():
            t = time.time()
            try:
                if conn is None:
                    conn = http.client.HTTPConnection(u.hostname, u.port, timeout=0.9)
                conn.request("GET", u.path, headers=hdr)
                body = conn.getresponse().read().decode("utf-8", "replace")
                v = {"running": 0.0, "waiting": 0.0}
                for k, x in rx.findall(body):
                    v[k] += float(x)
                self.rep[r["name"]].append((t, int(v["running"]), int(v["waiting"])))
            except Exception:
                try:
                    conn and conn.close()
                except Exception:
                    pass
                conn = None

    def _gpu_loop(self, g):
        cmd = ["nvidia-smi", "--query-gpu=index,utilization.gpu,temperature.gpu,power.draw",
               "--format=csv,noheader,nounits", "-l", "1"]
        if g.get("ssh"):
            cmd = list(g["ssh"]) + [" ".join(cmd)]
        while not self.stop.is_set():
            try:
                p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                     stdin=subprocess.DEVNULL, text=True)
                self.procs.append(p)
                for line in p.stdout:
                    f = [x.strip() for x in line.split(",")]
                    if len(f) >= 4:
                        try:
                            self.gpu.setdefault("%s:%s" % (g["machine"], f[0]), []).append(
                                (time.time(), float(f[1]), float(f[2]), float(f[3])))
                        except ValueError:
                            pass
                    if self.stop.is_set():
                        break
            except Exception:
                pass
            self.stop.wait(2.0)

    @staticmethod
    def _ticks(pid):
        try:
            with open("/proc/%d/stat" % pid) as f:
                s = f.read()
            f2 = s[s.rindex(")") + 2:].split()
            return int(f2[11]) + int(f2[12])                         # utime + stime
        except Exception:
            return None

    @staticmethod
    def _nginx_pids():
        out = {"nginx": [], "nginx_proot": []}
        for d in os.listdir("/proc"):
            if not d.isdigit():
                continue
            try:
                with open("/proc/%s/cmdline" % d, "rb") as f:
                    c = f.read(300)
            except Exception:
                continue
            if c.startswith(b"nginx: "):
                out["nginx"].append(int(d))
            elif b"proot" in c.split(b"\0")[0] and b"nginx" in c:
                out["nginx_proot"].append(int(d))
        return out

    def _cpu_loop(self):
        hz = os.sysconf("SC_CLK_TCK")
        prev, prev_t, scan = {}, None, 0
        groups = self._nginx_pids()
        while not self._tick():
            t = time.time()
            scan += 1
            if scan % 10 == 0:
                groups = self._nginx_pids()
            g = dict(groups)
            g["loadgen"] = list(self.worker_pids)
            g["loadgen_master"] = [os.getpid()]
            cur, sample, busiest, busiest_ng = {}, {}, 0.0, 0.0
            for name, pids in g.items():
                tot = 0.0
                for pid in pids:
                    x = self._ticks(pid)
                    if x is None:
                        continue
                    cur[pid] = x
                    if pid in prev and prev_t:
                        d = (x - prev[pid]) / hz / (t - prev_t) * 100.0
                        tot += d
                        if name == "loadgen":
                            busiest = max(busiest, d)
                        elif name == "nginx":
                            busiest_ng = max(busiest_ng, d)
                sample[name] = round(tot, 1)                          # % of one CPU core
            sample["loadgen_busiest_proc"] = round(busiest, 1)
            sample["nginx_busiest_proc"] = round(busiest_ng, 1)   # NGINX workers are single-threaded: 100 = full
            if prev_t:
                self.cpu.append((t, sample))
            prev, prev_t = cur, t


# ----------------------------------------------------------------------------- statistics
def pct(xs, p):
    if not xs:
        return None
    s = sorted(xs)
    k = (len(s) - 1) * p / 100.0
    lo, hi = math.floor(k), math.ceil(k)
    return s[lo] + (s[hi] - s[lo]) * (k - lo)


def rnd(x, n=3):
    return None if x is None else round(x, n)


def summarize(records, tokens, open_recs, mon, t0, w0, w1, replica_names):
    """Everything for the window [w0, w1) seconds after t0.
    TTFT: questions whose first token arrived in the window; speed / total time: questions finished in it."""
    span = w1 - w0
    first = [r for r in records if r["t_first"] is not None and w0 <= r["t_first"] < w1]
    done = [r for r in records if r["err"] is None and w0 <= r["t_end"] < w1]
    errs = [r for r in records if r["err"] is not None and w0 <= r["t_end"] < w1]
    sent = [r for r in records if w0 <= r["t_send"] < w1] + [r for r in open_recs if w0 <= r["t_send"] < w1]
    tok_win = sum(n for s, rep, n in tokens if w0 <= s < w1)
    no_token = [r for r in open_recs if r.get("ttft") is None]

    def block(first, done):
        tt = [r["ttft"] for r in first]
        sp = [r["speed"] for r in done if r["speed"] is not None]
        return {
            "questions_done": len(done),
            "ttft_p50_s": rnd(pct(tt, 50)), "ttft_p95_s": rnd(pct(tt, 95)), "ttft_max_s": rnd(max(tt) if tt else None),
            "speed_p50_tok_s": rnd(pct(sp, 50), 2), "speed_p5_tok_s": rnd(pct(sp, 5), 2),
            "total_p50_s": rnd(pct([r["total"] for r in done], 50)), "total_p95_s": rnd(pct([r["total"] for r in done], 95)),
            "tokens_out_mean": rnd(sum(r["n_out"] for r in done) / len(done), 1) if done else None,
        }

    out = block(first, done)
    kinds = {}
    for r in errs:
        kinds[r["err"]] = kinds.get(r["err"], 0) + 1
    out.update({
        "window_s": [w0, w1],
        "questions_sent": len(sent),
        "first_tokens": len(first),
        "throughput_tok_s": rnd(tok_win / span, 1),
        "questions_per_s": rnd(len(done) / span, 2),
        "errors": len(errs), "error_kinds": kinds,
        "error_pct": rnd(100.0 * len(errs) / max(1, len(errs) + len(done)), 2),
        "tokens_in_mean": rnd(sum(r["n_in"] or 0 for r in done) / len(done), 1) if done else None,
        "long_answer_questions": sum(r.get("long", 0) for r in done),
        "open_at_end": len(open_recs),
        "open_at_end_without_first_token": len(no_token),
        "open_at_end_longest_wait_without_token_s": rnd(max((r["waited"] for r in no_token), default=0.0)),
    })
    # per replica
    reps = {}
    names = list(replica_names) + sorted({r["replica"] for r in done if r["replica"] and r["replica"] not in replica_names})
    for name in names:
        b = block([r for r in first if r["replica"] == name], [r for r in done if r["replica"] == name])
        b["share_pct"] = rnd(100.0 * b["questions_done"] / len(done), 1) if done else None
        b["throughput_tok_s"] = rnd(sum(n for s, rep, n in tokens if rep == name and w0 <= s < w1) / span, 1)
        b["errors"] = sum(1 for r in errs if r["replica"] == name)
        ser = [(int(t - t0), run, wait) for t, run, wait in mon.rep.get(name, []) if w0 <= t - t0 < w1]
        if ser:
            b["running_mean"] = rnd(sum(x[1] for x in ser) / len(ser), 1)
            b["running_max"] = max(x[1] for x in ser)
            b["waiting_mean"] = rnd(sum(x[2] for x in ser) / len(ser), 1)
            b["waiting_max"] = max(x[2] for x in ser)
        b["per_second"] = {"t": [x[0] for x in ser], "running": [x[1] for x in ser], "waiting": [x[2] for x in ser]}
        reps[name] = b
    out["replicas"] = reps
    # machine
    gpus = {}
    for g, ser in sorted(mon.gpu.items()):
        s = [x for x in ser if w0 <= x[0] - t0 < w1]
        if s:
            gpus[g] = {"util_mean_pct": rnd(sum(x[1] for x in s) / len(s), 1), "util_max_pct": max(x[1] for x in s),
                       "temp_mean_c": rnd(sum(x[2] for x in s) / len(s), 1), "temp_max_c": max(x[2] for x in s),
                       "power_mean_w": rnd(sum(x[3] for x in s) / len(s), 1), "samples": len(s)}
    out["gpus"] = gpus
    cs = [c for t, c in mon.cpu if w0 <= t - t0 < w1]
    cpu = {}
    if cs:
        for k in sorted(cs[0]):
            v = [c.get(k, 0.0) for c in cs]
            cpu[k] = {"mean_pct_of_core": rnd(sum(v) / len(v), 1), "max_pct_of_core": max(v)}
    out["cpu"] = cpu
    return out


def per_second(records, tokens, open_recs, mon, t0, duration, replica_names):
    """Second-by-second table for the whole run (single mode)."""
    rows = []
    n = int(math.ceil(duration))
    tok_s, tok_rep = [0] * n, {}
    for s, rep, k in tokens:
        if 0 <= s < n:
            tok_s[s] += k
            tok_rep.setdefault(rep, [0] * n)[s] += k
    by_first, by_end, by_send = [[] for _ in range(n)], [[] for _ in range(n)], [0] * n
    for r in records:
        if 0 <= int(r["t_send"]) < n:
            by_send[int(r["t_send"])] += 1
        if r["t_first"] is not None and 0 <= int(r["t_first"]) < n:
            by_first[int(r["t_first"])].append(r)
        if 0 <= int(r["t_end"]) < n:
            by_end[int(r["t_end"])].append(r)
    for r in open_recs:
        if 0 <= int(r["t_send"]) < n:
            by_send[int(r["t_send"])] += 1
    rep_s = {name: {int(t - t0): (run, wait) for t, run, wait in ser} for name, ser in mon.rep.items()}
    gpu_s = {g: {int(t - t0): (u, c) for t, u, c, w in ser} for g, ser in mon.gpu.items()}
    cpu_s = {int(t - t0): c for t, c in mon.cpu}
    for s in range(n):
        ok = [r for r in by_end[s] if r["err"] is None]
        sp = [r["speed"] for r in ok if r["speed"] is not None]
        tt = [r["ttft"] for r in by_first[s]]
        row = {"t": s, "sent": by_send[s], "first_tokens": len(by_first[s]), "done": len(ok),
               "errors": len(by_end[s]) - len(ok), "tokens": tok_s[s],
               "ttft_p50_s": rnd(pct(tt, 50)), "ttft_p95_s": rnd(pct(tt, 95)),
               "speed_p50_tok_s": rnd(pct(sp, 50), 2), "speed_p5_tok_s": rnd(pct(sp, 5), 2),
               "replicas": {name: {"running": rep_s.get(name, {}).get(s, (None, None))[0],
                                   "waiting": rep_s.get(name, {}).get(s, (None, None))[1],
                                   "tokens": tok_rep.get(name, [0] * n)[s],
                                   "done": sum(1 for r in ok if r["replica"] == name)} for name in replica_names},
               "gpu_util_pct": {g: v.get(s, (None, None))[0] for g, v in sorted(gpu_s.items())},
               "gpu_temp_c": {g: v.get(s, (None, None))[1] for g, v in sorted(gpu_s.items())},
               "cpu_pct_of_core": cpu_s.get(s)}
        rows.append(row)
    return rows


# ----------------------------------------------------------------------------- one level
def default_procs(n_users):
    cores = os.cpu_count() or 4
    return max(1, min(n_users, max(2, math.ceil(n_users / 32)), 16, max(1, cores // 2)))


def run_level(args, targets, key, mon, n_users, duration, warmup, want_per_second=False, seed=0):
    """Run N users for `duration` seconds. Returns (summary, per_second_rows, raw_records)."""
    procs = getattr(args, "procs_for", {}).get(n_users) or args.procs or default_procs(n_users)
    procs = min(procs, n_users)
    cfg = {"url": targets["url"], "model": targets["model"], "long_pct": args.long_pct,
           "temperature": args.temperature, "ramp": min(args.ramp, warmup / 2 if warmup else args.ramp),
           "headers": {"Authorization": "Bearer " + key}}
    ctx = mp.get_context("spawn")
    ready_q, out_q, go_ev, t0_val = ctx.Queue(), ctx.Queue(), ctx.Event(), ctx.Value("d", 0.0)
    shares = [list(range(i, n_users, procs)) for i in range(procs)]
    ws = [ctx.Process(target=worker_entry, args=(i, cfg, shares[i], ready_q, go_ev, t0_val, duration,
                                                 seed * 1000 + n_users, out_q), daemon=True) for i in range(procs)]
    for w in ws:
        w.start()
    for _ in ws:
        ready_q.get(timeout=60)
    mon.worker_pids = [w.pid for w in ws]
    t0 = math.floor(time.time()) + 2.0          # start on a whole second, the monitors tick on whole seconds
    t0_val.value = t0
    go_ev.set()
    print("T0 %.3f" % t0, flush=True)            # clock time of second 0 (run_fail_node.sh schedules the failure from it)
    records, tokens, open_recs, werr = [], [], [], []
    deadline = t0 + duration + 30
    for _ in ws:
        try:
            idx, recs, tok, opn, err = out_q.get(timeout=max(1.0, deadline - time.time()))
        except Exception:
            werr.append("worker result missing")
            continue
        for r in recs:
            r["proc"] = idx
        records += recs
        tokens += tok
        open_recs += opn
        if err:
            werr.append(err)
    for w in ws:
        w.join(timeout=5)
        if w.is_alive():
            w.terminate()
    time.sleep(1.2)                              # let the monitors take the last sample of the window
    mon.worker_pids = []
    names = [r["name"] for r in targets["replicas"]]
    summ = summarize(records, tokens, open_recs, mon, t0, warmup, duration, names)
    # every question that left the load generator in this level, warm-up and still-open ones included
    summ["questions_sent_total"] = len(records) + len(open_recs)
    summ["tokens_received_total"] = sum(n for _, _, n in tokens)
    summ["t0_epoch"] = t0
    summ.update({"users": n_users, "processes": procs, "duration_s": duration, "warmup_s": warmup,
                 "started_at": time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(t0)), "worker_errors": werr})
    rows = per_second(records, tokens, open_recs, mon, t0, duration, names) if want_per_second else None
    return summ, rows, records


def settle(mon, max_wait=20.0):
    """Wait until no replica has work left from the level before (cancelled questions are aborted)."""
    t_end = time.time() + max_wait
    time.sleep(1.5)
    while time.time() < t_end:
        last = [ser[-1] for ser in mon.rep.values() if ser and time.time() - ser[-1][0] < 3]
        if last and all(run == 0 and wait == 0 for _, run, wait in last):
            return
        time.sleep(0.5)


def judge(summ, args):
    """pass / fail of one level against the two limits (plus errors)."""
    why = []
    if summ["ttft_p95_s"] is None or summ["speed_p5_tok_s"] is None:
        why.append("no finished questions")
    else:
        if summ["ttft_p95_s"] > args.ttft_p95_max:
            why.append("TTFT p95 %.3fs > %.3fs" % (summ["ttft_p95_s"], args.ttft_p95_max))
        if summ["speed_p5_tok_s"] < args.speed_p5_min:
            why.append("speed p5 %.1f < %.1f tok/s" % (summ["speed_p5_tok_s"], args.speed_p5_min))
    if summ["open_at_end_longest_wait_without_token_s"] > args.ttft_p95_max and \
            summ["open_at_end_without_first_token"] > 0.05 * summ["users"]:
        why.append(">5%% of users still waiting for a first token at the end (longest %.1fs)"
                   % summ["open_at_end_longest_wait_without_token_s"])
    if summ["error_pct"] > args.max_error_pct:
        why.append("errors %.1f%% > %.1f%%" % (summ["error_pct"], args.max_error_pct))
    return (not why), why


def cpu_full(summ, args):
    """Which CPU was the brake in this level? {} = none. A process is single-threaded: 100 % of a core = full."""
    c, full = summ.get("cpu") or {}, {}
    lg = (c.get("loadgen_busiest_proc") or {}).get("mean_pct_of_core")
    ng = (c.get("nginx_busiest_proc") or {}).get("mean_pct_of_core")
    if lg is not None and lg > args.cpu_full_pct:
        full["loadgen"] = "busiest process %.0f%% of a core" % lg
    if ng is not None and ng > args.cpu_full_pct:
        full["nginx"] = "busiest worker %.0f%% of a core" % ng
    return full


def line(summ, tag=""):
    f = lambda v, p="%.3f": "-" if v is None else p % v
    reps = " ".join("%s=%d(run%s/wait%s)" % (k, v["questions_done"], f(v.get("running_mean"), "%.0f"),
                                              f(v.get("waiting_mean"), "%.0f")) for k, v in summ["replicas"].items())
    gp = " ".join("%s=%s%%/%sC" % (g, f(v["util_mean_pct"], "%.0f"), f(v["temp_max_c"], "%.0f")) for g, v in summ["gpus"].items())
    c = summ["cpu"]
    cpu = "loadgen=%s%% (busiest proc %s%%) nginx=%s%% (busiest worker %s%%)+proot %s%%" % (
        f(c.get("loadgen", {}).get("mean_pct_of_core"), "%.0f"), f(c.get("loadgen_busiest_proc", {}).get("max_pct_of_core"), "%.0f"),
        f(c.get("nginx", {}).get("mean_pct_of_core"), "%.0f"), f(c.get("nginx_busiest_proc", {}).get("max_pct_of_core"), "%.0f"), f(c.get("nginx_proot", {}).get("mean_pct_of_core"), "%.0f")) if c else "-"
    return ("N=%-4d %s| TTFT p50 %ss p95 %ss | speed p50 %s p5 %s tok/s | throughput %s tok/s | %s q/s | "
            "done %d err %d open %d\n        replicas: %s\n        GPU util/temp: %s\n        CPU (%% of 1 core): %s") % (
        summ["users"], tag, f(summ["ttft_p50_s"]), f(summ["ttft_p95_s"]), f(summ["speed_p50_tok_s"], "%.1f"),
        f(summ["speed_p5_tok_s"], "%.1f"), f(summ["throughput_tok_s"], "%.0f"), f(summ["questions_per_s"], "%.2f"),
        summ["questions_done"], summ["errors"], summ["open_at_end"], reps, gp or "-", cpu)


# ----------------------------------------------------------------------------- capacity mode
def crossing(n_pass, v_pass, n_fail, v_fail, limit):
    """Straight line through (n_pass, v_pass) and (n_fail, v_fail): N where the value equals the limit."""
    if v_pass is None or v_fail is None or v_fail == v_pass:
        return None
    return n_pass + (limit - v_pass) * (n_fail - n_pass) / (v_fail - v_pass)


def estimate(lo, hi, args):
    """lo = passing level, hi = failing level (summaries). Returns dict with the per-limit crossings."""
    c_ttft = crossing(lo["users"], lo["ttft_p95_s"], hi["users"], hi["ttft_p95_s"], args.ttft_p95_max)
    c_speed = crossing(lo["users"], lo["speed_p5_tok_s"], hi["users"], hi["speed_p5_tok_s"], args.speed_p5_min)
    inside = [c for c in (c_ttft, c_speed) if c is not None and lo["users"] <= c <= hi["users"]]
    est = min(inside) if inside else None        # the limit that is reached first decides
    return {"between": [lo["users"], hi["users"]],
            "pass_point": {"users": lo["users"], "ttft_p95_s": lo["ttft_p95_s"], "speed_p5_tok_s": lo["speed_p5_tok_s"]},
            "fail_point": {"users": hi["users"], "ttft_p95_s": hi["ttft_p95_s"], "speed_p5_tok_s": hi["speed_p5_tok_s"]},
            "n_at_ttft_limit": rnd(c_ttft, 2), "n_at_speed_limit": rnd(c_speed, 2), "estimate_n": rnd(est, 2)}


def tolerance(n):
    return max(2, int(round(0.05 * n)))


def capacity_mode(args, targets, key, mon, result, save):
    levels = sorted({int(x) for x in args.levels.split(",") if x.strip()})
    measured = result["levels"] = []
    result["estimates"] = []
    result["limits"] = {"ttft_p95_max_s": args.ttft_p95_max, "speed_p5_min_tok_s": args.speed_p5_min,
                        "max_error_pct": args.max_error_pct, "single_user_speed_tok_s": args.single_speed or None}
    args.procs_for = {}
    counter = [0]

    def measure(n, phase):
        """One level = one measurement; a failed one is measured once more before the verdict."""
        final = None
        attempt = 0
        while attempt < 2:
            attempt += 1
            counter[0] += 1
            settle(mon)
            summ, _, _ = run_level(args, targets, key, mon, n, args.duration, args.warmup, seed=counter[0])
            ok, why = judge(summ, args)
            full = cpu_full(summ, args)
            summ.update({"phase": phase, "attempt": attempt, "pass": ok, "fail_reasons": why, "cpu_full": full})
            print(line(summ, "[%s%s] %s " % (phase, " repeat" if attempt == 2 else "", "PASS" if ok else "FAIL: " + "; ".join(why))), flush=True)
            if "loadgen" in full and summ["processes"] < min(n, args.max_procs):
                # the load generator itself was the brake: this measurement does not count, more processes, again
                more = min(n, args.max_procs, summ["processes"] * 2)
                args.procs_for[n] = more
                summ["discarded"] = "load generator CPU full (%s) -> repeated with %d processes" % (full["loadgen"], more)
                print("        !! %s" % summ["discarded"], flush=True)
                measured.append(summ)
                save()
                attempt -= 1
                continue
            if full:
                print("        !! CPU full: %s" % full, flush=True)
            measured.append(summ)
            save()
            final = summ
            if ok:
                break
        final["verdict"] = final["pass"]
        return final

    # ---- 1 scan
    print("== 1 scan: levels %s  (limits: TTFT p95 <= %.3fs, speed p5 >= %.1f tok/s)" % (
        ("reused from " + args.seed_from + (" + %s" % levels if args.levels_given else "")) if args.seed_from else levels,
        args.ttft_p95_max, args.speed_p5_min), flush=True)
    verdicts, fails_in_row = [], 0
    if args.seed_from:
        # levels already measured by another run of the SAME system: judged again with this run's limits, not measured again
        with open(args.seed_from) as f:
            src = json.load(f)
        last = {}
        for s in src["levels"]:
            if not s.get("discarded"):
                last[s["users"]] = s                 # the last measurement of each N is the one that counted
        for n in sorted(last):
            s = dict(last[n])
            ok, why = judge(s, args)
            s.update({"phase": "reused", "reused_from": src["name"], "attempt": 1, "pass": ok, "fail_reasons": why, "verdict": ok})
            measured.append(s)
            verdicts.append(s)
            print(line(s, "[reused from %s] %s " % (src["name"], "PASS" if ok else "FAIL: " + "; ".join(why))), flush=True)
        save()
        levels = [n for n in levels if n not in last] if args.levels_given else []
    for n in levels:
        v = measure(n, "scan")
        verdicts.append(v)
        fails_in_row = 0 if v["verdict"] else fails_in_row + 1
        if fails_in_row >= 2 and not args.scan_all:
            break
    verdicts.sort(key=lambda v: v["users"])
    # first failing level = the lowest level that fails (without --scan-all: the first of 2 failures in a row)
    first_fail_i = next((i for i, v in enumerate(verdicts) if not v["verdict"]), None)
    if first_fail_i is not None and not args.scan_all and not args.seed_from:
        first_fail_i = len(verdicts) - 2 if fails_in_row >= 2 else (len(verdicts) - 1 if fails_in_row == 1 else None)
    if first_fail_i is None:
        best = max((v["users"] for v in verdicts if v["verdict"]), default=None)
        result["capacity"] = {"users": best, "bound": ">=", "note": "no level failed twice in a row; give higher levels"}
        return
    passing = [v for v in verdicts[:first_fail_i] if v["verdict"]]
    if not passing:
        result["capacity"] = {"users": None, "bound": "<", "below": verdicts[first_fail_i]["users"],
                              "note": "the lowest level already fails; give lower levels"}
        return
    lo, hi = passing[-1], verdicts[first_fail_i]
    print("== scan result: last pass N=%d, first fail N=%d" % (lo["users"], hi["users"]), flush=True)

    # ---- 2 estimate + 3 refine
    rnd_no, last_side, same_side = 0, None, 0
    while hi["users"] - lo["users"] > tolerance(lo["users"]) and rnd_no < args.max_rounds:
        rnd_no += 1
        e = estimate(lo, hi, args)
        method = "line"
        x = e["estimate_n"]
        if x is None or same_side >= 2:
            # no usable line (e.g. failed on errors), or the line kept landing on the same side twice
            method, x = "midpoint", (lo["users"] + hi["users"]) / 2.0
        n = int(math.floor(x))                   # users are whole numbers: the last N still under the limit
        n = min(max(n, lo["users"] + 1), hi["users"] - 1)
        e.update({"round": rnd_no, "phase": "estimate" if rnd_no == 1 else "refine", "method": method, "measure_n": n})
        fr = (n - lo["users"]) / float(hi["users"] - lo["users"])    # the same straight line, read at the N we measure
        if lo["ttft_p95_s"] is not None and hi["ttft_p95_s"] is not None:
            e["predicted_ttft_p95_s"] = rnd(lo["ttft_p95_s"] + fr * (hi["ttft_p95_s"] - lo["ttft_p95_s"]))
        if lo["speed_p5_tok_s"] is not None and hi["speed_p5_tok_s"] is not None:
            e["predicted_speed_p5_tok_s"] = rnd(lo["speed_p5_tok_s"] + fr * (hi["speed_p5_tok_s"] - lo["speed_p5_tok_s"]), 2)
        print("== %d %s: line between N=%d and N=%d -> TTFT limit at N=%s, speed limit at N=%s -> measure N=%d (%s)" % (
            2 if rnd_no == 1 else 3, e["phase"], lo["users"], hi["users"], e["n_at_ttft_limit"], e["n_at_speed_limit"], n, method), flush=True)
        v = measure(n, e["phase"])
        e.update({"measured_pass": v["verdict"], "measured_ttft_p95_s": v["ttft_p95_s"], "measured_speed_p5_tok_s": v["speed_p5_tok_s"]})
        side = "lo" if v["verdict"] else "hi"
        same_side = same_side + 1 if side == last_side else 1
        last_side = side
        if v["verdict"]:
            lo = v
        else:
            hi = v
        e["gap_after"] = hi["users"] - lo["users"]
        e["gap_allowed"] = tolerance(lo["users"])
        result["estimates"].append(e)
        save()
    final = estimate(lo, hi, args)
    final.update({"round": "final", "phase": "final", "method": "line", "measure_n": None})
    result["estimates"].append(final)
    result["capacity"] = {"users": lo["users"], "bound": "=", "last_pass": lo["users"], "first_fail": hi["users"],
                          "gap": hi["users"] - lo["users"], "gap_allowed": tolerance(lo["users"]),
                          "converged": hi["users"] - lo["users"] <= tolerance(lo["users"]),
                          "line_estimate_n": final["estimate_n"],
                          "at_capacity": {k: lo[k] for k in ("ttft_p50_s", "ttft_p95_s", "speed_p50_tok_s", "speed_p5_tok_s",
                                                             "throughput_tok_s", "questions_per_s", "errors")},
                          "replica_share_pct": {k: v.get("share_pct") for k, v in lo["replicas"].items()},
                          "replica_questions": {k: v.get("questions_done") for k, v in lo["replicas"].items()}}


# ----------------------------------------------------------------------------- main
def load_targets(path):
    with open(path) as f:
        return json.load(f)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mode", choices=["capacity", "single"])
    ap.add_argument("--name", required=True, help="name of this run -> results/<name>.json")
    ap.add_argument("--targets", default=os.path.join(HERE, "loadgen_targets.json"),
                    help="JSON: NGINX url, model, key file, replicas (/metrics), GPU sources")
    ap.add_argument("--results-dir", default=os.path.join(HERE, "..", "results"))
    ap.add_argument("--procs", type=int, default=0, help="load-generator processes (0 = 1 per 32 users, 2..16)")
    ap.add_argument("--long-pct", type=float, default=0.0, help="%% of questions asking for a detailed answer (up to 600 tokens)")
    ap.add_argument("--temperature", type=float, default=0.7)
    ap.add_argument("--ramp", type=float, default=2.0, help="users start spread over this many seconds")
    ap.add_argument("--warmup", type=float, default=10.0, help="seconds at the start that are not counted")
    ap.add_argument("--duration", type=float, default=30.0, help="seconds per level (capacity) / of the run (single)")
    # capacity
    ap.add_argument("--levels", default="8,16,32,64,128,256,512", help="N to scan, comma separated")
    ap.add_argument("--ttft-p95-max", type=float, default=1.0, help="limit: TTFT p95 in seconds")
    ap.add_argument("--speed-p5-min", type=float, default=20.0, help="limit: per-user speed p5 in tokens/s")
    ap.add_argument("--max-error-pct", type=float, default=1.0, help="a level with more errors than this fails")
    ap.add_argument("--max-rounds", type=int, default=10, help="upper bound for estimate/refine rounds")
    ap.add_argument("--scan-all", action="store_true", help="measure every level of --levels, also after 2 failures in a row")
    ap.add_argument("--seed-from", default="", help="result JSON of an earlier capacity run of the same system: its levels are "
                    "judged with this run's limits instead of being measured again")
    ap.add_argument("--single-speed", type=float, default=0.0, help="speed of one user alone (tok/s), stored with the limits")
    ap.add_argument("--cpu-full-pct", type=float, default=80.0, help="busiest load-generator process / NGINX worker above this "
                    "%% of a core = CPU full: the level is measured again with twice the processes")
    ap.add_argument("--max-procs", type=int, default=24, help="most load-generator processes the CPU guard may use")
    # single
    ap.add_argument("--users", type=int, default=8, help="N for single mode")
    ap.add_argument("--keep-requests", action="store_true", help="also store every question's record in the JSON")
    args = ap.parse_args()
    args.levels_given = any(a == "--levels" or a.startswith("--levels=") for a in sys.argv)
    args.procs_for = {}

    targets = load_targets(args.targets)
    with open(targets["key_file"]) as f:
        key = f.read().strip()                   # never printed, never written to the result
    os.makedirs(args.results_dir, exist_ok=True)
    out_path = os.path.join(args.results_dir, args.name + ".json")
    result = {"name": args.name, "mode": args.mode, "started": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
              "target": {"url": targets["url"], "model": targets["model"],
                         "replicas": [r["name"] for r in targets["replicas"]]},
              "settings": {k: v for k, v in vars(args).items() if k not in ("targets", "results_dir", "procs_for")},
              "request": {"system_short": SYSTEM_SHORT, "system_long": SYSTEM_LONG,
                          "max_tokens_short": MAX_TOKENS_SHORT, "max_tokens_long": MAX_TOKENS_LONG,
                          "timeout_s": REQUEST_TIMEOUT_S, "questions": len(QUESTIONS)},
              "definitions": {
                  "ttft": "seconds from sending the question to the first answer token; questions whose first token arrived in the window",
                  "speed": "(tokens after the first chunk) / (time from first to last token) of one question; questions finished in the window",
                  "throughput_tok_s": "answer tokens received by all users in the window / window length",
                  "window": "level time minus warm-up", "cpu": "% of one CPU core, summed over the processes"}}

    def save():
        result["saved"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        tmp = out_path + ".tmp"
        with open(tmp, "w") as f:
            json.dump(result, f, ensure_ascii=False, indent=1)
        os.replace(tmp, out_path)

    mon = Monitors(targets, key)
    mon.start()
    time.sleep(2.2)
    try:
        if args.mode == "capacity":
            capacity_mode(args, targets, key, mon, result, save)
            c = result["capacity"]
            save()
            if c["bound"] == "=":
                print("CAPACITY %s: N = %d users  (last pass %d, first fail %d, gap %d <= %d; line estimate %s)" % (
                    args.name, c["users"], c["last_pass"], c["first_fail"], c["gap"], c["gap_allowed"], c["line_estimate_n"]))
            elif c["bound"] == ">=":
                print("CAPACITY %s: N >= %s users (%s)" % (args.name, c["users"], c["note"]))
            else:
                print("CAPACITY %s: N < %s users (%s)" % (args.name, c["below"], c["note"]))
        else:
            settle(mon, 10)
            print("== single: N=%d for %.0fs (warm-up %.0fs, long answers %.0f%%)" % (args.users, args.duration, args.warmup, args.long_pct), flush=True)
            summ, rows, records = run_level(args, targets, key, mon, args.users, args.duration, args.warmup, want_per_second=True)
            result["levels"] = [summ]
            result["per_second"] = rows
            if args.keep_requests:
                result["requests"] = [{k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items()} for r in records]
            save()
            for r in rows:
                rp = " ".join("%s:%s/%s" % (k, v["running"], v["waiting"]) for k, v in r["replicas"].items())
                print("  t=%3d sent %3d done %3d err %d tok %5d ttft_p95 %s  run/wait %s" % (
                    r["t"], r["sent"], r["done"], r["errors"], r["tokens"], r["ttft_p95_s"], rp))
            print(line(summ, "[single] "), flush=True)
            print("CAPACITY %s: not searched (single level N=%d: throughput %s tok/s, %s q/s)" % (
                args.name, args.users, summ["throughput_tok_s"], summ["questions_per_s"]))
        print("saved %s" % os.path.normpath(out_path))
    finally:
        mon.close()
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
