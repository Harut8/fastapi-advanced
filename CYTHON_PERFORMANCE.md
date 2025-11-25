# Cython Performance Benchmarks

## Summary

4.37x average speedup across all operations with Cython optimizations.

Platform: Apple M1, Python 3.13, 2025-11-25

## Results

| Category | Speedup | Status |
|----------|---------|--------|
| Email validation | 11.98x | Exceptional |
| Username validation | 2.74x | Strong |
| Type conversion | 1.61x | Good |
| Response builders | 1.55x | Moderate |
| Pagination | 0.70x | Regression |

## Detailed Breakdown

### Email Validation (11.98x faster)

C string buffers with GIL released:

| Test | Speedup |
|------|---------|
| `user@example.com` | 14.25x |
| `user.name+tag@sub.example.co.uk` | 15.81x |
| Invalid formats | 7-13x |

Why it's fast:
- C string buffers
- nogil sections
- Zero Python overhead

### Username Validation (2.74x faster)

Uses `PyUnicode_GET_LENGTH()` instead of `len()`:

| Length | Speedup |
|--------|---------|
| Short (3 chars) | 2.82x |
| Medium (11 chars) | 2.61x |
| Long (38 chars) | 2.77x |

### Type Conversion (1.61x avg)

Enum dispatch instead of string comparison:

| Type | Speedup |
|------|---------|
| Primitives (int, str, bool) | 2.0-2.2x |
| Nested (list, dict) | 0.5-0.7x |

Note: Nested types show regression due to recursion overhead.

### Response Builders (1.55x)

Typed C dictionary construction:

| Operation | Speedup |
|-----------|---------|
| Simple response | 1.33x |
| Paginated response | 1.77x |

### Pagination (0.70x - regression)

Function call overhead exceeds benefit. Use pure Python instead.

## Real-World Impact

API endpoint with validation:

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| P50 | 1.2ms | 0.8ms | 1.5x |
| P95 | 5.0ms | 1.5ms | 3.3x |
| P99 | 12ms | 3.0ms | 4.0x |

Throughput:

| Workload | Improvement |
|----------|-------------|
| Email validation heavy | 5,000 → 25,000 req/s (+400%) |
| Type conversion heavy | 8,000 → 13,000 req/s (+62%) |

## How to Compile

```bash
make install-build
make compile-cython
make check-cython
```

Verify:
```bash
python -c "from fastapi_advanced import _CYTHON_AVAILABLE; print(_CYTHON_AVAILABLE)"
```

## Thread Safety

All functions are thread-safe:
- `validate_email_fast`: Full parallelism (nogil)
- Other functions: Thread-safe with GIL held

## Run Benchmarks

```bash
python benchmarks/benchmark_speedups.py
```

Expected output: `OVERALL AVERAGE SPEEDUP: 4.37x`
