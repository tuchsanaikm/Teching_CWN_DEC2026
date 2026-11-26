"""Generate 5 hard tasks + answer key (deterministic). Writes tasks/*.txt and key.json."""
import itertools, json, random
from pathlib import Path

OUT = Path(__file__).parent / "tasks"
OUT.mkdir(parents=True, exist_ok=True)
KEY = {}
FMT = "\n\nตอบโดยให้บรรทัดสุดท้ายเป็น `ANSWER: <คำตอบ>` เท่านั้น"

# ---------------------------------------------------------------- 1) multi-step math
A = sum(2026 // 5 ** i for i in range(1, 6))          # trailing zeros of 2026!
B = pow(7, 2026, 1000)                                 # last 3 digits of 7^2026
C = 9                                                  # d(2026^2) = d(2^2 * 1013^2)
D = sum(n for n in range(1, 1001) if n % 6 == 1 or n % 6 == 5)  # sum of n<=1000 coprime to 6
ans1 = A * B + C * D
KEY["h1_math"] = str(ans1)
(OUT / "h1_math.txt").write_text(
    "โจทย์คณิต (ให้คิดเอง ห้ามเขียนหรือรันโค้ด ห้ามใช้เครื่องมือใด ๆ):\n"
    "ให้ A = จำนวนเลข 0 ที่ลงท้ายของ 2026!\n"
    "ให้ B = เศษจากการหาร 7^2026 ด้วย 1000\n"
    "ให้ C = จำนวนตัวหารบวกทั้งหมดของ 2026²\n"
    "ให้ D = ผลรวมของจำนวนเต็ม n ทุกตัวที่ 1 ≤ n ≤ 1000 และ ห.ร.ม.(n, 6) = 1\n"
    "จงหาค่า A×B + C×D" + FMT + " (จำนวนเต็มล้วน ไม่มีจุลภาค)\n", encoding="utf-8")

# ---------------------------------------------------------------- 2) logic puzzle (generated, verified unique)
NAMES = ["อรุณ", "บีม", "ชัย", "ดาว", "เอก"]
COLORS = ["แดง", "เขียว", "น้ำเงิน", "ขาว", "เหลือง"]
PETS = ["แมว", "หมา", "ปลา", "นก", "กระต่าย"]
DRINKS = ["กาแฟ", "ชา", "นม", "น้ำส้ม", "น้ำเปล่า"]
CATS = [("name", NAMES), ("color", COLORS), ("pet", PETS), ("drink", DRINKS)]
rnd = random.Random(7)
SOL = {k: rnd.sample(v, 5) for k, v in CATS}           # SOL[k][pos] = value at house pos (0-based)
pos_of = lambda sol, k, v: sol[k].index(v)
ALL = [list(p) for p in itertools.permutations(range(5))]


def label(k, v):
    return {"name": f"{v}", "color": f"คนที่อยู่บ้านสี{v}", "pet": f"คนที่เลี้ยง{v}", "drink": f"คนที่ดื่ม{v}"}[k]


def make_clue():
    t = rnd.choice(["same", "same", "left", "next", "notnext", "pos", "notsame", "between"])
    k1, k2 = rnd.sample([c[0] for c in CATS], 2)
    v1 = rnd.choice(dict(CATS)[k1]); v2 = rnd.choice(dict(CATS)[k2])
    p1, p2 = pos_of(SOL, k1, v1), pos_of(SOL, k2, v2)
    if t == "same":
        v2 = SOL[k2][p1]; return (t, k1, v1, k2, v2), f"{label(k1, v1)} คือ{label(k2, v2)}"
    if t == "notsame" and p1 != p2:
        return (t, k1, v1, k2, v2), f"{label(k1, v1)} ไม่ใช่{label(k2, v2)}"
    if t == "left" and p2 == p1 + 1:
        return (t, k1, v1, k2, v2), f"บ้านของ{label(k1, v1)} อยู่ติดกันทางซ้ายของบ้านของ{label(k2, v2)} (เลขบ้านน้อยกว่าอยู่ 1 พอดี)"
    if t == "next" and abs(p1 - p2) == 1:
        return (t, k1, v1, k2, v2), f"บ้านของ{label(k1, v1)} อยู่ติดกับบ้านของ{label(k2, v2)}"
    if t == "notnext" and abs(p1 - p2) > 1:
        return (t, k1, v1, k2, v2), f"บ้านของ{label(k1, v1)} ไม่ได้อยู่ติดกับบ้านของ{label(k2, v2)}"
    if t == "between" and p2 > p1:
        return ("lt", k1, v1, k2, v2), f"บ้านของ{label(k1, v1)} อยู่ทางซ้ายของบ้านของ{label(k2, v2)} (ไม่จำเป็นต้องติดกัน)"
    if t == "pos":
        return ("pos", k1, v1, p1), f"{label(k1, v1)} อยู่บ้านหลังที่ {p1 + 1}"
    return None


def holds(c, sol):
    if c[0] == "pos":
        return pos_of(sol, c[1], c[2]) == c[3]
    t, k1, v1, k2, v2 = c
    a, b = pos_of(sol, k1, v1), pos_of(sol, k2, v2)
    return {"same": a == b, "notsame": a != b, "left": b == a + 1, "next": abs(a - b) == 1,
            "notnext": abs(a - b) > 1, "lt": a < b}[t]


def keys_of(c):
    return {c[1]} if c[0] == "pos" else {c[1], c[3]}


def solutions(clues, limit=2):
    order = [k for k, _ in CATS]
    vals = dict(CATS)
    stage = [[c for c in clues if keys_of(c) <= set(order[:j + 1]) and order[j] in keys_of(c)]
             for j in range(len(order))]
    res = []

    def rec(j, sol):
        if len(res) >= limit:
            return
        if j == len(order):
            res.append({k: list(v) for k, v in sol.items()}); return
        k = order[j]
        for p in ALL:
            sol[k] = [vals[k][i] for i in p]
            if all(holds(c, sol) for c in stage[j]):
                rec(j + 1, sol)
        del sol[k]

    rec(0, {})
    return res


def count_fast(clues):
    # prune per category: precompute valid name perms first via single-category clues
    return len(solutions(clues))


# greedy: add clues until unique (use cheap pruning by checking full solver only occasionally)
clues, texts = [], []
while True:
    c = make_clue()
    if not c or c[0] in [x for x in clues] or c[0][0] == "pos" and sum(x[0] == "pos" for x in clues) >= 1:
        continue
    clues.append(c[0]); texts.append(c[1])
    if len(clues) >= 12 and count_fast(clues) == 1:
        break
# drop redundant clues
i = 0
while i < len(clues):
    trial = clues[:i] + clues[i + 1:]
    if count_fast(trial) == 1:
        clues, texts = trial, texts[:i] + texts[i + 1:]
    else:
        i += 1
assert solutions(clues)[0] == SOL
KEY["h2_logic"] = ",".join(SOL["name"])
(OUT / "h2_logic.txt").write_text(
    "ปริศนาตรรกะ (ให้คิดเอง ห้ามเขียนหรือรันโค้ด ห้ามใช้เครื่องมือ):\n"
    "บ้าน 5 หลังเรียงเป็นแถว เลขบ้าน 1 ถึง 5 จากซ้ายไปขวา แต่ละหลังมีเจ้าของ 1 คน "
    f"เจ้าของคือ {', '.join(NAMES)} · สีบ้าน {', '.join(COLORS)} · สัตว์เลี้ยง {', '.join(PETS)} · "
    f"เครื่องดื่ม {', '.join(DRINKS)} (ไม่มีค่าใดซ้ำกัน)\n\nเงื่อนไข:\n"
    + "\n".join(f"{i + 1}. {t}" for i, t in enumerate(texts))
    + "\n\nปริศนานี้มีคำตอบเดียว จงบอกชื่อเจ้าของบ้านหลังที่ 1 ถึง 5 ตามลำดับ"
    + FMT + " (ชื่อ 5 ชื่อคั่นด้วยจุลภาค เช่น `ANSWER: ก,ข,ค,ง,จ`)\n", encoding="utf-8")
print("logic clues:", len(clues), "solution:", KEY["h2_logic"])

# ---------------------------------------------------------------- 3) hidden bugs in ~60-line evaluator
BUGGY = '''import re

TOKEN = re.compile(r"\\s*(?:(\\d+\\.\\d*|\\.\\d+|\\d+)|(.))")


def tokenize(src):
    tokens = []
    for num, op in TOKEN.findall(src):
        if num:
            tokens.append(("num", float(num)))
        elif op.strip():
            if op not in "+-*/^()":
                raise ValueError(f"bad char {op!r}")
            tokens.append(("op", op))
    tokens.append(("end", None))
    return tokens


class Parser:
    """Grammar (lowest -> highest precedence):
        expr   := term (('+' | '-') term)*          left-associative
        term   := unary (('*' | '/') unary)*        left-associative, '/' is true division
        unary  := '-' unary | power                 so -2^2 == -4
        power  := atom ('^' unary)?                 RIGHT-associative: 2^3^2 == 2^(3^2) == 512, 2^-1 == 0.5
        atom   := number | '(' expr ')'
    Division by zero must raise ZeroDivisionError. Any leftover token must raise ValueError."""

    def __init__(self, src):
        self.toks = tokenize(src)
        self.i = 0

    def peek(self):
        return self.toks[self.i]

    def take(self, kind=None, val=None):
        t = self.toks[self.i]
        if (kind and t[0] != kind) or (val and t[1] != val):
            raise ValueError(f"expected {val or kind}, got {t}")
        self.i += 1
        return t

    def expr(self):
        v = self.term()
        while self.peek() in (("op", "+"), ("op", "-")):
            op = self.take()[1]
            v = v + self.term() if op == "+" else v - self.term()
        return v

    def term(self):
        v = self.unary()
        while self.peek() in (("op", "*"), ("op", "/")):
            op = self.take()[1]
            rhs = self.unary()
            v = v * rhs if op == "*" else v // rhs
        return v

    def unary(self):
        if self.peek() == ("op", "-"):
            self.take()
            return -self.power()
        return self.power()

    def power(self):
        v = self.atom()
        while self.peek() == ("op", "^"):
            self.take()
            v = v ** self.atom()
        return v

    def atom(self):
        t = self.peek()
        if t[0] == "num":
            return self.take()[1]
        self.take("op", "(")
        v = self.expr()
        self.take("op", ")")
        return v


def evaluate(src):
    p = Parser(src)
    v = p.expr()
    return v
'''
(OUT / "h3_bug_buggy.py").write_text(BUGGY, encoding="utf-8")
(OUT / "h3_bug.txt").write_text(
    "โค้ด Python ด้านล่าง (ตัวคำนวณนิพจน์ ราว 80 บรรทัด) มีบั๊กซ่อนอยู่หลายจุด ทำให้ผลไม่ตรงกับสเปกใน docstring ของ Parser\n"
    "แก้ให้ทำงานตรงสเปกทุกข้อ (จะตรวจด้วยเทสต์ที่ซ่อนไว้ ซึ่งเรียก `evaluate(src)` และ `tokenize(src)`)\n\n"
    "```python\n" + BUGGY + "```\n\n"
    "ตอบเป็นโค้ดทั้งไฟล์ที่แก้แล้ว ในโค้ดบล็อก ```python เพียงบล็อกเดียว (ไม่ต้องสร้างไฟล์)\n", encoding="utf-8")
KEY["h3_bug"] = "hidden tests"

# ---------------------------------------------------------------- 4) algorithm with hidden tests
(OUT / "h4_algo.txt").write_text(
    "เขียนฟังก์ชัน Python `shortest_subarray(nums: list[int], k: int) -> int`\n"
    "คืนความยาวของ subarray ที่ต่อเนื่องและไม่ว่าง ที่สั้นที่สุด ซึ่งผลรวม ≥ k ถ้าไม่มีให้คืน -1\n"
    "- nums มีได้ทั้งจำนวนบวก ลบ และศูนย์ · 1 ≤ len(nums) ≤ 200,000 · |nums[i]| ≤ 10^9 · 1 ≤ k ≤ 10^15\n"
    "- เทสต์ที่ซ่อนไว้มีกรณีขอบหลายแบบ และมีกรณีขนาด 200,000 ตัวที่ต้องรันเสร็จภายใน 3 วินาที\n"
    "ตัวอย่าง: shortest_subarray([2, -1, 2], 3) == 3 · shortest_subarray([1, 2], 4) == -1\n\n"
    "ตอบเป็นโค้ด (ใช้แค่ standard library) ในโค้ดบล็อก ```python เพียงบล็อกเดียว (ไม่ต้องสร้างไฟล์)\n",
    encoding="utf-8")
KEY["h4_algo"] = "hidden tests"

# ---------------------------------------------------------------- 5) combine 3 facts from 2,000-line doc
r = random.Random(99)
accts = [f"ACC-{n}" for n in r.sample(range(1000, 9999), 60) if n not in (7731, 7713, 7371)]
special = {
    233: "ACC-7731 account opened, opening balance set to 15,250.00 THB",
    412: "ACC-7731 interest rate set to 2.0% per year",
    587: "ACC-7713 account opened, opening balance set to 9,800.00 THB",
    961: "ACC-7371 interest rate set to 4.25% per year",
    1102: "ACC-7731 interest rate changed to 3.5% per year (supersedes the rate set at L0412)",
    1490: "ACC-7731 withdrawal 900.00 THB -- REVERSED same day, void, no effect on balance",
    1633: "ACC-7713 withdrawal 4,125.50 THB",
    1846: "ACC-7731 withdrawal 2,318.75 THB",
}
lines = []
for i in range(1, 2001):
    if i in special:
        lines.append(f"L{i:04d} NOTE {special[i]}")
    else:
        kind = r.choice(["deposit", "fee", "transfer-in", "transfer-out", "audit-ok"])
        lines.append(f"L{i:04d} {r.choice(accts)} {kind} {r.randrange(1, 99999) / 100:.2f} ref={r.randrange(16**6):06x}")
ans5 = round((15250.00 - 2318.75) * 1.035, 2)
KEY["h5_doc"] = f"{ans5:.2f}"
(OUT / "h5_doc.txt").write_text(
    "เอกสารบันทึกบัญชียาว 2,000 บรรทัดด้านล่าง ให้หาข้อมูลของบัญชี ACC-7731 เท่านั้น:\n"
    "(ก) ยอดเปิดบัญชี (ข) อัตราดอกเบี้ยต่อปีที่มีผลล่าสุด (ค) ผลรวมยอดถอนที่มีผลจริง (ไม่นับรายการที่ถูกยกเลิก)\n"
    "แล้วคำนวณ (ก − ค) × (1 + ข) ปัดเป็นทศนิยม 2 ตำแหน่ง\n"
    "=== BEGIN DOCUMENT ===\n" + "\n".join(lines) + "\n=== END DOCUMENT ===\n"
    + FMT + " (ตัวเลขล้วน ไม่มีจุลภาค)\n", encoding="utf-8")

(Path(__file__).parent / "key.json").write_text(json.dumps(KEY, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps(KEY, ensure_ascii=False))
