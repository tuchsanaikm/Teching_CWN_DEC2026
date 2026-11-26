```python
def find_max(numbers):
    if not numbers:
        raise ValueError("find_max() requires a non-empty list")

    values = iter(numbers)
    largest = next(values)
    for value in values:
        if value > largest:
            largest = value
    return largest
```