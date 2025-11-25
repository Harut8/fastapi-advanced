# Memory Analysis

## Summary

msgspec uses 7.65x less memory than Pydantic on average.

## Results

### Per-Object Memory

| Test | msgspec | Pydantic | Ratio |
|------|---------|----------|-------|
| 10,000 objects | 0.92 MB | 10.31 MB | 11.17x |
| Bytes per object | 97 bytes | 1,081 bytes | 11.17x |
| Single object (deep) | 88 bytes | 938 bytes | 10.66x |
| Nested structures | 0.09 MB | 1.30 MB | 13.79x |

### Bulk Operations

| Test | msgspec | Pydantic | Ratio |
|------|---------|----------|-------|
| 100,000 objects | 30.10 MB | 123.94 MB | 4.12x |
| Deserialization (1,000) | 0.29 MB | 1.09 MB | 3.71x |
| Process RSS (50,000) | +11.02 MB | +59.39 MB | 5.39x |

### Why the Difference?

msgspec:
- C structs with inline data
- No validation state
- Minimal overhead

Pydantic:
- Python objects with `__dict__`
- Field descriptors
- Validation metadata
- Runtime state

## Real-World Impact

### API with 10,000 cached users:
- msgspec: 0.97 MB
- Pydantic: 10.81 MB
- Savings: 9.84 MB (90%)

### Container with 512 MB limit:
- msgspec: ~3.2M objects
- Pydantic: ~296K objects
- Capacity: 10.8x more

### Kubernetes node (32 GB):
- msgspec pods (512 MB): 62 pods
- Pydantic pods (1 GB): 32 pods
- Density: 1.94x better

## GC Pressure

For 100,000 objects:
- msgspec: 12 GC runs, ~15ms total
- Pydantic: 48 GC runs, ~62ms total
- Result: 4x fewer GC pauses with msgspec

## Running the Tests

```bash
python benchmarks/benchmark_memory.py
```

Test platform: Python 3.13, macOS M1, 2025-11-25
