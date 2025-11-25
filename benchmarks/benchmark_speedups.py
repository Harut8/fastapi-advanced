#!/usr/bin/env python3
"""
Comprehensive benchmark suite for Cython speedups.

Compares optimized Cython implementations against pure Python fallbacks
to measure actual performance improvements.
"""

import time
import statistics
from typing import Callable, List, Tuple
import msgspec


# ============================================================================
# Benchmark Infrastructure
# ============================================================================

class BenchmarkResult:
    """Container for benchmark results."""

    def __init__(
        self,
        name: str,
        cython_time: float,
        python_time: float,
        iterations: int,
    ):
        self.name = name
        self.cython_time = cython_time
        self.python_time = python_time
        self.iterations = iterations
        self.speedup = python_time / cython_time if cython_time > 0 else 0

    def __str__(self) -> str:
        return (
            f"{self.name}:\n"
            f"  Cython: {self.cython_time*1000:.3f}ms\n"
            f"  Python: {self.python_time*1000:.3f}ms\n"
            f"  Speedup: {self.speedup:.2f}x"
        )


def benchmark_function(
    func: Callable,
    args: tuple,
    iterations: int = 10000,
    warmup: int = 100,
) -> float:
    """
    Benchmark a function with warmup and multiple iterations.

    Args:
        func: Function to benchmark
        args: Arguments to pass to function
        iterations: Number of benchmark iterations
        warmup: Number of warmup iterations

    Returns:
        Average execution time in seconds
    """
    # Warmup
    for _ in range(warmup):
        func(*args)

    # Benchmark
    times = []
    for _ in range(10):  # 10 runs for statistical stability
        start = time.perf_counter()
        for _ in range(iterations // 10):
            func(*args)
        end = time.perf_counter()
        times.append(end - start)

    return statistics.median(times)


def compare_implementations(
    name: str,
    cython_func: Callable,
    python_func: Callable,
    test_args: tuple,
    iterations: int = 10000,
) -> BenchmarkResult:
    """
    Compare Cython and Python implementations.

    Args:
        name: Benchmark name
        cython_func: Cython-optimized function
        python_func: Pure Python function
        test_args: Arguments to pass to both functions
        iterations: Number of iterations

    Returns:
        BenchmarkResult with timing data
    """
    print(f"Benchmarking: {name}...", end=" ", flush=True)

    cython_time = benchmark_function(cython_func, test_args, iterations)
    python_time = benchmark_function(python_func, test_args, iterations)

    result = BenchmarkResult(name, cython_time, python_time, iterations)
    print(f"{result.speedup:.2f}x speedup")

    return result


# ============================================================================
# Pure Python Fallback Implementations
# ============================================================================

def validate_email_python(email: str) -> bool:
    """Pure Python email validation."""
    at_count = 0
    at_pos = -1

    if len(email) < 5:
        return False

    for i, c in enumerate(email):
        if c == '@':
            at_count += 1
            at_pos = i

    if at_count != 1 or at_pos == 0 or at_pos == len(email) - 1:
        return False

    for i in range(at_pos + 1, len(email)):
        if email[i] == '.':
            if i < len(email) - 1:
                return True

    return False


def validate_username_length_python(
    username: str, min_len: int = 3, max_len: int = 50
) -> bool:
    """Pure Python username length validation."""
    return min_len <= len(username) <= max_len


def calculate_pagination_python(
    total_results: int, page_size: int, current_page: int
) -> dict:
    """Pure Python pagination calculation."""
    if page_size > 0:
        total_pages = (total_results + page_size - 1) // page_size
    else:
        total_pages = 0

    return {
        "current_page": current_page,
        "total_pages": total_pages,
        "total_results": total_results,
        "page_size": page_size,
        "has_next": current_page < total_pages,
        "has_previous": current_page > 1,
    }


def create_response_dict_python(data: object, message: str, status: str) -> dict:
    """Pure Python response dict creation."""
    return {
        "data": data,
        "message": message,
        "status": status,
    }


def create_paginated_dict_python(
    items: list,
    total_results: int,
    current_page: int,
    page_size: int,
    message: str,
    status: str,
) -> dict:
    """Pure Python paginated dict creation."""
    metadata = calculate_pagination_python(total_results, page_size, current_page)
    return {
        "items": items,
        "current_page": metadata["current_page"],
        "total_pages": metadata["total_pages"],
        "total_results": metadata["total_results"],
        "page_size": metadata["page_size"],
        "has_next": metadata["has_next"],
        "has_previous": metadata["has_previous"],
        "message": message,
        "status": status,
    }


class TypeConverterPython:
    """Pure Python type converter."""

    def __init__(self):
        self._type_cache = {}

    def convert_type(self, field_type):
        """Convert msgspec type to Python type."""
        type_name = type(field_type).__name__

        if type_name in self._type_cache:
            return self._type_cache[type_name]

        if type_name == "IntType":
            result = int
        elif type_name == "StrType":
            result = str
        elif type_name == "FloatType":
            result = float
        elif type_name == "BoolType":
            result = bool
        elif type_name == "ListType":
            if hasattr(field_type, "item_type"):
                item_type = self.convert_type(field_type.item_type)
                result = list[item_type]
            else:
                result = list
        elif type_name == "DictType":
            if hasattr(field_type, "key_type") and hasattr(field_type, "value_type"):
                key_type = self.convert_type(field_type.key_type)
                value_type = self.convert_type(field_type.value_type)
                result = dict[key_type, value_type]
            else:
                result = dict
        else:
            result = object

        self._type_cache[type_name] = result
        return result


# ============================================================================
# Benchmark Suites
# ============================================================================

def benchmark_email_validation() -> List[BenchmarkResult]:
    """Benchmark email validation functions."""
    try:
        from fastapi_advanced._speedups import validate_email_fast
    except ImportError:
        print("WARNING: Cython speedups not available, skipping email validation")
        return []

    test_cases = [
        ("valid_simple", "user@example.com"),
        ("valid_complex", "user.name+tag@sub.example.co.uk"),
        ("invalid_no_at", "userexample.com"),
        ("invalid_multiple_at", "user@@example.com"),
        ("invalid_no_dot", "user@examplecom"),
    ]

    results = []
    for name, email in test_cases:
        result = compare_implementations(
            f"Email Validation: {name}",
            validate_email_fast,
            validate_email_python,
            (email,),
            iterations=50000,
        )
        results.append(result)

    return results


def benchmark_username_validation() -> List[BenchmarkResult]:
    """Benchmark username validation functions."""
    try:
        from fastapi_advanced._speedups import validate_username_length_fast
    except ImportError:
        print("WARNING: Cython speedups not available, skipping username validation")
        return []

    test_cases = [
        ("short", "abc"),
        ("medium", "username123"),
        ("long", "very_long_username_with_many_chars_12345"),
    ]

    results = []
    for name, username in test_cases:
        result = compare_implementations(
            f"Username Validation: {name}",
            validate_username_length_fast,
            validate_username_length_python,
            (username,),
            iterations=100000,
        )
        results.append(result)

    return results


def benchmark_pagination() -> List[BenchmarkResult]:
    """Benchmark pagination calculation functions."""
    try:
        from fastapi_advanced._speedups import calculate_pagination_fast
    except ImportError:
        print("WARNING: Cython speedups not available, skipping pagination")
        return []

    test_cases = [
        ("small_dataset", (100, 10, 1)),
        ("medium_dataset", (10000, 25, 50)),
        ("large_dataset", (1000000, 100, 500)),
    ]

    results = []
    for name, args in test_cases:
        result = compare_implementations(
            f"Pagination: {name}",
            calculate_pagination_fast,
            calculate_pagination_python,
            args,
            iterations=50000,
        )
        results.append(result)

    return results


def benchmark_response_builders() -> List[BenchmarkResult]:
    """Benchmark response dictionary builders."""
    try:
        from fastapi_advanced._speedups import (
            create_response_dict_fast,
            create_paginated_dict_fast,
        )
    except ImportError:
        print("WARNING: Cython speedups not available, skipping response builders")
        return []

    results = []

    # Simple response
    result = compare_implementations(
        "Response Dict: simple",
        create_response_dict_fast,
        create_response_dict_python,
        ({"id": 1, "name": "test"}, "Success", "success"),
        iterations=50000,
    )
    results.append(result)

    # Paginated response
    items = [{"id": i, "name": f"item_{i}"} for i in range(10)]
    result = compare_implementations(
        "Response Dict: paginated",
        create_paginated_dict_fast,
        create_paginated_dict_python,
        (items, 1000, 1, 10, "Success", "success"),
        iterations=50000,
    )
    results.append(result)

    return results


def benchmark_type_conversion() -> List[BenchmarkResult]:
    """Benchmark type conversion functions."""
    try:
        from fastapi_advanced._speedups import convert_msgspec_type_fast
    except ImportError:
        print("WARNING: Cython speedups not available, skipping type conversion")
        return []

    # Create test msgspec types
    class SimpleStruct(msgspec.Struct):
        id: int
        name: str
        active: bool

    class ComplexStruct(msgspec.Struct):
        id: int
        tags: list[str]
        metadata: dict[str, int]

    type_info_simple = msgspec.inspect.type_info(SimpleStruct)
    type_info_complex = msgspec.inspect.type_info(ComplexStruct)

    cython_converter = None
    python_converter = TypeConverterPython()

    # Import Cython converter
    try:
        from fastapi_advanced._speedups import TypeConverter
        cython_converter = TypeConverter()
    except ImportError:
        return []

    results = []

    # Benchmark simple types
    for field in type_info_simple.fields:
        result = compare_implementations(
            f"Type Conversion: {field.name} ({type(field.type).__name__})",
            cython_converter.convert_type,
            python_converter.convert_type,
            (field.type,),
            iterations=100000,
        )
        results.append(result)

    # Benchmark complex types
    for field in type_info_complex.fields:
        result = compare_implementations(
            f"Type Conversion: {field.name} ({type(field.type).__name__})",
            cython_converter.convert_type,
            python_converter.convert_type,
            (field.type,),
            iterations=50000,
        )
        results.append(result)

    return results


# ============================================================================
# Main Benchmark Runner
# ============================================================================

def print_summary(all_results: List[BenchmarkResult]) -> None:
    """Print benchmark summary."""
    print("\n" + "=" * 80)
    print("BENCHMARK SUMMARY")
    print("=" * 80)

    if not all_results:
        print("No benchmarks were run.")
        return

    # Group by category
    categories = {}
    for result in all_results:
        category = result.name.split(":")[0]
        if category not in categories:
            categories[category] = []
        categories[category].append(result)

    # Print by category
    for category, results in categories.items():
        print(f"\n{category}")
        print("-" * 80)
        avg_speedup = statistics.mean([r.speedup for r in results])
        min_speedup = min([r.speedup for r in results])
        max_speedup = max([r.speedup for r in results])

        for result in results:
            test_name = result.name.split(": ", 1)[1] if ": " in result.name else result.name
            print(f"  {test_name:40s} {result.speedup:6.2f}x")

        print(f"  {'Average':40s} {avg_speedup:6.2f}x")
        print(f"  {'Range':40s} {min_speedup:.2f}x - {max_speedup:.2f}x")

    # Overall summary
    print("\n" + "=" * 80)
    overall_avg = statistics.mean([r.speedup for r in all_results])
    print(f"OVERALL AVERAGE SPEEDUP: {overall_avg:.2f}x")
    print("=" * 80)


def main():
    """Run all benchmarks."""
    print("=" * 80)
    print("FASTAPI-ADVANCED CYTHON SPEEDUPS BENCHMARK SUITE")
    print("=" * 80)
    print()

    all_results = []

    # Run all benchmark suites
    all_results.extend(benchmark_email_validation())
    all_results.extend(benchmark_username_validation())
    all_results.extend(benchmark_pagination())
    all_results.extend(benchmark_response_builders())
    all_results.extend(benchmark_type_conversion())

    # Print summary
    print_summary(all_results)

    # Return results for programmatic use
    return all_results


if __name__ == "__main__":
    main()
