"""Hidden tests. Usage: python -I hidden_tests.py <h3|h4> <solution.py>  -> prints PASS or failure."""
import importlib.util, random, sys, time
from collections import deque

kind, path = sys.argv[1], sys.argv[2]
spec = importlib.util.spec_from_file_location("sol", path)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def close(a, b):
    return abs(a - b) < 1e-9 * max(1, abs(b))


def raises(fn, exc):
    try:
        fn()
    except exc:
        return True
    except Exception:
        return False
    return False


if kind == "h3":
    ev = m.evaluate
    cases = [("1+2*3", 7), ("(1+2)*3", 9), ("7/2", 3.5), ("-7/2", -3.5), ("10-4-3", 3),
             ("2^3^2", 512), ("-2^2", -4), ("2^-1", 0.5), ("--3", 3), ("-(2+3)*2", -10),
             ("2*-3", -6), ("(2^3)^2", 64), (".5+1.25", 1.75), ("8/4/2", 1), ("2^-2^-1", 2 ** (-(2 ** -1))),
             ("3 - -2", 5), ("100 / 8 * 2", 25), ("-3^2^-1", -(3 ** 0.5))]
    for src, want in cases:
        got = ev(src)
        assert close(got, want), f"evaluate({src!r}) = {got!r}, want {want!r}"
    assert raises(lambda: ev("1/0"), ZeroDivisionError), "1/0 must raise ZeroDivisionError"
    assert raises(lambda: ev("2 3"), ValueError), "leftover token must raise ValueError"
    assert raises(lambda: ev("(1+2"), ValueError), "missing ) must raise ValueError"
    assert raises(lambda: ev("1+)"), ValueError), "'1+)' must raise ValueError"
    assert raises(lambda: ev("2 $ 3"), ValueError), "bad char must raise ValueError"
    print("PASS")

elif kind == "h4":
    f = m.shortest_subarray

    def ref(nums, k):
        p = [0]
        for x in nums:
            p.append(p[-1] + x)
        best, dq = len(nums) + 1, deque()
        for i, s in enumerate(p):
            while dq and s - p[dq[0]] >= k:
                best = min(best, i - dq.popleft())
            while dq and p[dq[-1]] >= s:
                dq.pop()
            dq.append(i)
        return best if best <= len(nums) else -1

    fixed = [([2, -1, 2], 3, 3), ([1, 2], 4, -1), ([1], 1, 1), ([5], 6, -1), ([-5], 1, -1),
             ([84, -37, 32, 40, 95], 167, 3), ([17, 85, 93, -45, -21], 150, 2), ([1, -1, 1, -1, 5], 5, 1),
             ([-28, 81, -20, 28, -29], 89, 3), ([0, 0, 0, 7], 7, 1), ([10 ** 9] * 3, 3 * 10 ** 9, 3),
             ([3, -2, 5], 4, 1), ([-1, -1, 10], 9, 1), ([2, -1, 2, -1, 2], 4, 5), ([48, 99, 37, 4, -31], 140, 2)]
    for nums, k, want in fixed:
        got = f(list(nums), k)
        assert got == want, f"shortest_subarray({nums}, {k}) = {got}, want {want}"
    rnd = random.Random(5)
    for _ in range(400):
        n = rnd.randint(1, 30)
        nums = [rnd.randint(-20, 30) for _ in range(n)]
        k = rnd.randint(1, 80)
        got, want = f(list(nums), k), ref(nums, k)
        assert got == want, f"shortest_subarray({nums}, {k}) = {got}, want {want}"
    for seed, (lo, hi, k) in enumerate([(-10 ** 9, 10 ** 9, 10 ** 13), (-5, 6, 10 ** 15), (1, 1, 199_999)]):
        r = random.Random(seed)
        nums = [r.randint(lo, hi) for _ in range(200_000)]
        want = ref(nums, k)
        t = time.perf_counter()
        got = f(list(nums), k)
        dt = time.perf_counter() - t
        assert got == want, f"large case {seed}: got {got}, want {want}"
        assert dt < 3.0, f"large case {seed}: too slow {dt:.1f}s"
    print("PASS")
