from collections import deque


def shortest_subarray(nums, k):
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


def naive_slow(nums, k):  # used only to prove the size test rejects O(n^2)
    pass
