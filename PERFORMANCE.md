# Performance Guide

## Results

Serialization (msgspec vs Pydantic):
```
Payload         | Pydantic  | msgspec   | Speedup
----------------|-----------|-----------|--------
Single object   | 2.8 μs    | 0.1 μs    | 24x
100 objects     | 155 μs    | 6.7 μs    | 23x
5,000 objects   | 8.0 ms    | 0.3 ms    | 27x
```

Type Conversion (Cython vs Python):
```
Model           | Python    | Cython    | Speedup
----------------|-----------|-----------|--------
Simple          | 0.25 μs   | 0.14 μs   | 1.8x
Medium          | 0.21 μs   | 0.08 μs   | 2.5x
Complex         | 0.24 μs   | 0.06 μs   | 3.8x
```

Pagination (optimized vs naive):
```
DB Size         | list()    | islice()  | Speedup
----------------|-----------|-----------|--------
1,000           | 2.0 μs    | 0.8 μs    | 2.7x
10,000          | 28.7 μs   | 0.8 μs    | 34x
1,000,000       | 8.3 ms    | 2.6 μs    | 3,200x
```

## Cython Optimizations

Install from pip to get pre-compiled wheels:
```bash
pip install fastapi-advanced
```

For development:
```bash
make compile-cython
```

Check if enabled:
```python
from fastapi_advanced import _CYTHON_AVAILABLE
print(_CYTHON_AVAILABLE)
```

What's optimized: type conversion, field processing, response creation, pagination.

## Best Practices

Use proper pagination (don't load all records):

```python
import itertools
page = list(itertools.islice(database.values(), start, start + page_size))
```

Optimize struct definitions:

```python
class User(msgspec.Struct, frozen=True):  # immutable
    id: int
    name: str

class Config(msgspec.Struct, omit_defaults=True):  # smaller JSON
    enabled: bool = True

class Point(msgspec.Struct, array_like=True):  # compact encoding
    x: float
    y: float
```

## Benchmarking

```bash
make benchmark
```

## When to Use

Use fastapi-advanced for:
- High-throughput APIs (1000+ req/sec)
- Large payloads or pagination
- Tail latency optimization (P95/P99)

Standard FastAPI is fine for:
- Low traffic (< 100 req/sec)
- Small payloads (< 1KB)

## Troubleshooting

Check if Cython is loaded:
```bash
python -c "from fastapi_advanced import _CYTHON_AVAILABLE; print(_CYTHON_AVAILABLE)"
```

Rebuild if needed:
```bash
make clean-cython
make compile-cython
```
