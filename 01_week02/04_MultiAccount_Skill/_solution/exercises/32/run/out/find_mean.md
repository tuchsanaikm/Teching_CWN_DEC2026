```python
def find_mean(numbers):
    from statistics import mean

    if not numbers:
        raise ValueError("Cannot compute the mean of an empty list")
    return float(mean(numbers))
```