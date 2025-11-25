"""
Benchmark for new Cython optimizations added to core.py.

This script compares the performance of:
1. Field inspection optimization (process_struct_fields_fast)
2. Response model instantiation (create_response_dict_fast)
3. Pagination calculations (calculate_pagination_fast, create_paginated_dict_fast)

Tests both Cython and pure Python implementations for comparison.
"""

import time
from typing import Any

import msgspec

# Import both Cython and fallback implementations
try:
    from fastapi_advanced._speedups import (
        calculate_pagination_fast as calc_fast_cython,
        create_paginated_dict_fast as pag_dict_cython,
        create_response_dict_fast as resp_dict_cython,
        process_struct_fields_fast as fields_cython,
    )

    CYTHON_AVAILABLE = True
except ImportError:
    CYTHON_AVAILABLE = False
    print("WARNING: Cython not available, skipping Cython benchmarks")

from fastapi_advanced._speedups_fallback import (
    calculate_pagination_fast as calc_fast_python,
    create_paginated_dict_fast as pag_dict_python,
    create_response_dict_fast as resp_dict_python,
    process_struct_fields_fast as fields_python,
)


# ============================================================================
# Test Data Structures
# ============================================================================


class SimpleStruct(msgspec.Struct):
    """Simple struct with 3 fields."""

    id: int
    name: str
    active: bool = True


class MediumStruct(msgspec.Struct):
    """Medium struct with 7 fields."""

    id: int
    username: str
    email: str
    age: int
    score: float
    active: bool = True
    tags: list[str] = []


class ComplexStruct(msgspec.Struct):
    """Complex nested struct."""

    id: int
    user: MediumStruct
    metadata: dict[str, Any]
    items: list[SimpleStruct]
    optional_field: str | None = None


def _msgspec_type_to_python_type_mock(field_type: Any) -> Any:
    """Mock type converter for testing."""
    type_name = type(field_type).__name__

    if type_name == "IntType":
        return int
    elif type_name == "StrType":
        return str
    elif type_name == "FloatType":
        return float
    elif type_name == "BoolType":
        return bool
    elif type_name == "ListType":
        return list
    elif type_name == "DictType":
        return dict
    else:
        return Any


# ============================================================================
# Benchmark Functions
# ============================================================================


def benchmark_field_processing(iterations: int = 10000) -> dict[str, float]:
    """Benchmark field processing optimization."""
    print(f"\n{'=' * 80}")
    print("BENCHMARK: Field Processing Optimization")
    print(f"{'=' * 80}")
    print(f"Iterations: {iterations:,}")

    results = {}

    # Test Simple Struct
    print("\n[1] Simple Struct (3 fields)")
    start = time.perf_counter()
    for _ in range(iterations):
        fields_python(SimpleStruct, _msgspec_type_to_python_type_mock)
    python_time = time.perf_counter() - start
    results["simple_python"] = python_time
    print(f"  Python:  {python_time:.4f}s ({iterations / python_time:,.0f} ops/sec)")

    if CYTHON_AVAILABLE:
        start = time.perf_counter()
        for _ in range(iterations):
            fields_cython(SimpleStruct, _msgspec_type_to_python_type_mock)
        cython_time = time.perf_counter() - start
        results["simple_cython"] = cython_time
        speedup = python_time / cython_time
        print(f"  Cython:  {cython_time:.4f}s ({iterations / cython_time:,.0f} ops/sec)")
        print(f"  Speedup: {speedup:.2f}x faster")

    # Test Medium Struct
    print("\n[2] Medium Struct (7 fields)")
    start = time.perf_counter()
    for _ in range(iterations):
        fields_python(MediumStruct, _msgspec_type_to_python_type_mock)
    python_time = time.perf_counter() - start
    results["medium_python"] = python_time
    print(f"  Python:  {python_time:.4f}s ({iterations / python_time:,.0f} ops/sec)")

    if CYTHON_AVAILABLE:
        start = time.perf_counter()
        for _ in range(iterations):
            fields_cython(MediumStruct, _msgspec_type_to_python_type_mock)
        cython_time = time.perf_counter() - start
        results["medium_cython"] = cython_time
        speedup = python_time / cython_time
        print(f"  Cython:  {cython_time:.4f}s ({iterations / cython_time:,.0f} ops/sec)")
        print(f"  Speedup: {speedup:.2f}x faster")

    return results


def benchmark_response_dict(iterations: int = 100000) -> dict[str, float]:
    """Benchmark response dictionary creation."""
    print(f"\n{'=' * 80}")
    print("BENCHMARK: Response Dictionary Creation")
    print(f"{'=' * 80}")
    print(f"Iterations: {iterations:,}")

    results = {}
    data = {"id": 1, "name": "Test", "value": 42.5}

    print("\n[1] Simple Response Dict")
    start = time.perf_counter()
    for _ in range(iterations):
        resp_dict_python(data, "Success", "ok")
    python_time = time.perf_counter() - start
    results["python"] = python_time
    print(f"  Python:  {python_time:.4f}s ({iterations / python_time:,.0f} ops/sec)")

    if CYTHON_AVAILABLE:
        start = time.perf_counter()
        for _ in range(iterations):
            resp_dict_cython(data, "Success", "ok")
        cython_time = time.perf_counter() - start
        results["cython"] = cython_time
        speedup = python_time / cython_time
        print(f"  Cython:  {cython_time:.4f}s ({iterations / cython_time:,.0f} ops/sec)")
        print(f"  Speedup: {speedup:.2f}x faster")

    return results


def benchmark_pagination_calc(iterations: int = 100000) -> dict[str, float]:
    """Benchmark pagination calculations."""
    print(f"\n{'=' * 80}")
    print("BENCHMARK: Pagination Calculations")
    print(f"{'=' * 80}")
    print(f"Iterations: {iterations:,}")

    results = {}

    print("\n[1] Pagination Metadata Calculation")
    start = time.perf_counter()
    for _ in range(iterations):
        calc_fast_python(1000, 10, 3)
    python_time = time.perf_counter() - start
    results["calc_python"] = python_time
    print(f"  Python:  {python_time:.4f}s ({iterations / python_time:,.0f} ops/sec)")

    if CYTHON_AVAILABLE:
        start = time.perf_counter()
        for _ in range(iterations):
            calc_fast_cython(1000, 10, 3)
        cython_time = time.perf_counter() - start
        results["calc_cython"] = cython_time
        speedup = python_time / cython_time
        print(f"  Cython:  {cython_time:.4f}s ({iterations / cython_time:,.0f} ops/sec)")
        print(f"  Speedup: {speedup:.2f}x faster")

    return results


def benchmark_paginated_dict(iterations: int = 50000) -> dict[str, float]:
    """Benchmark paginated response dictionary creation."""
    print(f"\n{'=' * 80}")
    print("BENCHMARK: Paginated Response Dictionary Creation")
    print(f"{'=' * 80}")
    print(f"Iterations: {iterations:,}")

    results = {}
    items = [{"id": i, "name": f"Item {i}"} for i in range(10)]

    print("\n[1] Full Paginated Dict (with metadata calculation)")
    start = time.perf_counter()
    for _ in range(iterations):
        pag_dict_python(items, 1000, 1, 10, "Success", "ok")
    python_time = time.perf_counter() - start
    results["python"] = python_time
    print(f"  Python:  {python_time:.4f}s ({iterations / python_time:,.0f} ops/sec)")

    if CYTHON_AVAILABLE:
        start = time.perf_counter()
        for _ in range(iterations):
            pag_dict_cython(items, 1000, 1, 10, "Success", "ok")
        cython_time = time.perf_counter() - start
        results["cython"] = cython_time
        speedup = python_time / cython_time
        print(f"  Cython:  {cython_time:.4f}s ({iterations / cython_time:,.0f} ops/sec)")
        print(f"  Speedup: {speedup:.2f}x faster")

    return results


def print_summary(all_results: dict[str, dict[str, float]]) -> None:
    """Print summary of all benchmarks."""
    print(f"\n{'=' * 80}")
    print("SUMMARY: Overall Performance Improvements")
    print(f"{'=' * 80}\n")

    if not CYTHON_AVAILABLE:
        print("Cython not available - no speedup data to display")
        return

    print("Optimization                           | Speedup")
    print("-" * 80)

    # Field processing
    if "field_processing" in all_results:
        r = all_results["field_processing"]
        if "simple_cython" in r:
            speedup = r["simple_python"] / r["simple_cython"]
            print(f"Field Processing (Simple Struct)       | {speedup:.2f}x faster")
        if "medium_cython" in r:
            speedup = r["medium_python"] / r["medium_cython"]
            print(f"Field Processing (Medium Struct)       | {speedup:.2f}x faster")

    # Response dict
    if "response_dict" in all_results:
        r = all_results["response_dict"]
        if "cython" in r:
            speedup = r["python"] / r["cython"]
            print(f"Response Dictionary Creation           | {speedup:.2f}x faster")

    # Pagination calc
    if "pagination_calc" in all_results:
        r = all_results["pagination_calc"]
        if "calc_cython" in r:
            speedup = r["calc_python"] / r["calc_cython"]
            print(f"Pagination Metadata Calculation        | {speedup:.2f}x faster")

    # Paginated dict
    if "paginated_dict" in all_results:
        r = all_results["paginated_dict"]
        if "cython" in r:
            speedup = r["python"] / r["cython"]
            print(f"Paginated Dictionary Creation          | {speedup:.2f}x faster")

    print("\n" + "=" * 80)
    print("Expected Overall Impact:")
    print("  - Schema conversion (first time):  1.5-2x faster")
    print("  - Response creation:               1.3-1.8x faster")
    print("  - Pagination responses:            1.2-1.5x faster")
    print("  - Overall API throughput:          10-20% improvement")
    print("=" * 80 + "\n")


# ============================================================================
# Main
# ============================================================================


def main() -> None:
    """Run all benchmarks."""
    print("\n" + "=" * 80)
    print("FASTAPI-ADVANCED: NEW CYTHON OPTIMIZATIONS BENCHMARK")
    print("=" * 80)

    if not CYTHON_AVAILABLE:
        print("\n⚠️  WARNING: Cython extensions not compiled!")
        print("Run 'make compile-cython' to compile extensions for performance comparison.\n")

    all_results = {}

    # Run all benchmarks
    all_results["field_processing"] = benchmark_field_processing(10000)
    all_results["response_dict"] = benchmark_response_dict(100000)
    all_results["pagination_calc"] = benchmark_pagination_calc(100000)
    all_results["paginated_dict"] = benchmark_paginated_dict(50000)

    # Print summary
    print_summary(all_results)


if __name__ == "__main__":
    main()
