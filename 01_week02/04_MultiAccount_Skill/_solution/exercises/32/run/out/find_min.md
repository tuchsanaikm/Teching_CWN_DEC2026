```python
def find_min(numbers):
    if not numbers:
        raise ValueError("numbers must not be empty")

    values = iter(numbers)
    smallest = next(values)
    for value in values:
        if value < smallest:
            smallest = value
    return smallest
```