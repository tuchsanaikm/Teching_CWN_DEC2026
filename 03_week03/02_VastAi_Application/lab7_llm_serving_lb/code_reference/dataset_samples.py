#!/usr/bin/env python3
"""Ask 8 of the 40 load-test questions once each through NGINX (one at a time, idle system) and store
question, real answer, tokens in/out, TTFT and total time -> JSON. Rendered to a picture by render_samples.py."""
import argparse, asyncio, json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import loadgen as lg


async def main(a):
    import aiohttp
    t = lg.load_targets(a.targets)
    key = open(t["key_file"]).read().strip()
    rows = []
    async with aiohttp.ClientSession() as s:
        for qi in range(2, 40, 5):                       # 8 questions spread over the list
            body = lg.build_request(t["model"], qi, False)
            r = await lg.ask_once(s, t["url"] + "/v1/chat/completions", {"Authorization": "Bearer " + key},
                                  body, time.time(), keep_text=True)
            rows.append({"q_index": qi, "question": lg.QUESTIONS[qi], "answer": r.get("answer"), "tokens_in": r["n_in"],
                         "tokens_out": r["n_out"], "ttft_s": lg.rnd(r["ttft"]), "total_s": lg.rnd(r["total"]),
                         "speed_tok_s": lg.rnd(r["speed"], 1), "replica": r["replica"], "finish": r.get("finish"), "error": r["err"]})
            print("q%02d %s in=%s out=%s ttft=%.3fs total=%.2fs" % (qi, r["replica"], r["n_in"], r["n_out"], r["ttft"] or -1, r["total"]))
    json.dump({"system": lg.SYSTEM_SHORT, "max_tokens": lg.MAX_TOKENS_SHORT, "model": t["model"], "samples": rows},
              open(a.out, "w"), ensure_ascii=False, indent=1)
    print("DONE")

ap = argparse.ArgumentParser()
ap.add_argument("--out", required=True)
ap.add_argument("--targets", default=os.path.join(lg.HERE, "loadgen_targets.json"))
asyncio.run(main(ap.parse_args()))
