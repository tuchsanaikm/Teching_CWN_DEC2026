import re

TOKEN = re.compile(r"\s*(?:(\d+\.\d*|\.\d+|\d+)|(.))")


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
            v = v * rhs if op == "*" else v / rhs
        return v

    def unary(self):
        if self.peek() == ("op", "-"):
            self.take()
            return -self.unary()
        return self.power()

    def power(self):
        v = self.atom()
        if self.peek() == ("op", "^"):
            self.take()
            v = v ** self.unary()
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
    p.take("end")
    return v
