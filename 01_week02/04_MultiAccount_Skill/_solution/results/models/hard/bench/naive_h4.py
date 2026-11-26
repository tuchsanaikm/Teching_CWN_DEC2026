def shortest_subarray(nums, k):
    # sliding window (wrong with negatives) - should fail hidden tests
    best, s, lo = len(nums) + 1, 0, 0
    for hi, x in enumerate(nums):
        s += x
        while lo <= hi and s >= k:
            best = min(best, hi - lo + 1)
            s -= nums[lo]
            lo += 1
    return best if best <= len(nums) else -1
