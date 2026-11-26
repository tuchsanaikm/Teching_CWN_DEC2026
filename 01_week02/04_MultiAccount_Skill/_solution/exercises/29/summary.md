# Exercise 29 — Gemini creates · Codex reviews · Claude judges (up to 3 rounds)

run: `20261124-053517-myyf` · prompt sent to the creator: "รถเข็นขายน้ำผลไม้ริมถนน ภาพถ่ายสมจริง" (street juice cart, realistic photo; the shop's criteria were not included)
Hidden criteria (reviewer only): 1) the cart's umbrella is yellow 2) a sign reads "น้ำส้มคั้นสด 25 บาท" ("Fresh-squeezed orange juice 25 baht")

| Round | Review result | Feedback sent back to the creator | What changed in the next round's image | Verdict |
|---|---|---|---|---|
| 1 (gyolo1 creates · cyolo1 reviews) | FAIL — canopy is red/blue/yellow; signs read "น้ำปั่นสด" (fresh smoothies) / "น้ำผลไม้ปั่น" (blended fruit juice) | Make the whole canopy yellow · add a sign "น้ำส้มคั้นสด 25 บาท", large, clear, fully visible | Round 2: canopy all yellow · new yellow sign "น้ำส้มคั้นสด 25 บาท" (same scene, vendor and pose; edited from the round-1 image) | Continue |
| 2 (gyolo2 creates · cyolo2 reviews) | FAIL — the word "บาท" (baht) is cut off at the image edge | Change the angle or move the sign up so the whole sign shows · keep the yellow umbrella | Round 3: new scene (round yellow umbrella, orange-juice cart, juicer); sign centred and fully visible | Continue |
| 3 (gyolo2 creates · cyolo1 reviews) | PASS — yellow umbrella and the sign "น้ำส้มคั้นสด 25 บาท" are complete | — | — | **ACCEPT** (yolo2, Claude Sonnet) |

Files: `juice_cart.r1.png` `juice_cart.r2.png` `juice_cart.r3.png` · `juice_cart_final.png` (= r3) · `graph.json` / `plan_graph.json` (plan) · `run/` (the whole run: review results, judge result, ledger, state)
