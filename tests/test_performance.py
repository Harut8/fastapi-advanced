"""
Performance regression tests for fastapi-advanced.

These tests ensure that Cython optimizations provide expected performance
improvements over pure Python implementations. Tests are marked with @pytest.mark.benchmark
and can be run separately with: pytest -m benchmark

Performance requirements:
- Cython type conversion: At least 1.5x faster than Python fallback
- Complex type conversion: At least 2x faster than Python fallback
"""

import time
from typing import Any

import msgspec
import pytest

from fastapi_advanced import _CYTHON_AVAILABLE
from fastapi_advanced._speedups_fallback import convert_msgspec_type_fast as python_convert

# Only import Cython version if available
if _CYTHON_AVAILABLE:
    from fastapi_advanced._speedups import convert_msgspec_type_fast as cython_convert
else:
    cython_convert = None


class SimpleModel(msgspec.Struct):
    """Simple model with 3 fields for testing."""

    id: int
    name: str
    active: bool


class MediumModel(msgspec.Struct):
    """Medium complexity model with 7 fields."""

    id: int
    name: str
    email: str
    age: int
    score: float
    active: bool
    tags: list[str]


class ComplexModel(msgspec.Struct):
    """Complex nested model."""

    id: int
    name: str
    metadata: dict[str, Any]
    items: list[MediumModel]
    optional_field: str | None = None


def benchmark_type_conversion(
    convert_func: Any, model_class: type, iterations: int = 10000
) -> float:
    """
    Benchmark type conversion function.

    Args:
        convert_func: The conversion function to benchmark
        model_class: The msgspec model class to convert
        iterations: Number of iterations to run

    Returns:
        Time in seconds for all iterations
    """
    # Get msgspec type info
    type_info = msgspec.structs.fields(model_class)

    # Benchmark
    start = time.perf_counter()
    for _ in range(iterations):
        for field in type_info:
            convert_func(field.type)
    end = time.perf_counter()

    return end - start


@pytest.mark.benchmark
@pytest.mark.skipif(not _CYTHON_AVAILABLE, reason="Cython extensions not available")
def test_cython_simple_model_performance():
    """Test Cython performance on simple model (3 fields)."""
    iterations = 10000

    python_time = benchmark_type_conversion(python_convert, SimpleModel, iterations)
    cython_time = benchmark_type_conversion(cython_convert, SimpleModel, iterations)

    speedup = python_time / cython_time

    print(f"\n{'=' * 60}")
    print(f"Simple Model Performance (3 fields, {iterations} iterations)")
    print(f"{'=' * 60}")
    print(f"Python time:  {python_time * 1000:.2f} ms")
    print(f"Cython time:  {cython_time * 1000:.2f} ms")
    print(f"Speedup:      {speedup:.2f}x")
    print(f"{'=' * 60}")

    # Assert Cython is at least 1.5x faster
    assert speedup >= 1.5, f"Cython speedup ({speedup:.2f}x) is less than required 1.5x"


@pytest.mark.benchmark
@pytest.mark.skipif(not _CYTHON_AVAILABLE, reason="Cython extensions not available")
def test_cython_medium_model_performance():
    """Test Cython performance on medium model (7 fields)."""
    iterations = 10000

    python_time = benchmark_type_conversion(python_convert, MediumModel, iterations)
    cython_time = benchmark_type_conversion(cython_convert, MediumModel, iterations)

    speedup = python_time / cython_time

    print(f"\n{'=' * 60}")
    print(f"Medium Model Performance (7 fields, {iterations} iterations)")
    print(f"{'=' * 60}")
    print(f"Python time:  {python_time * 1000:.2f} ms")
    print(f"Cython time:  {cython_time * 1000:.2f} ms")
    print(f"Speedup:      {speedup:.2f}x")
    print(f"{'=' * 60}")

    # Assert Cython is at least 2x faster
    assert speedup >= 2.0, f"Cython speedup ({speedup:.2f}x) is less than required 2.0x"


@pytest.mark.benchmark
@pytest.mark.skipif(not _CYTHON_AVAILABLE, reason="Cython extensions not available")
def test_cython_complex_model_performance():
    """Test Cython performance on complex nested model."""
    iterations = 10000

    python_time = benchmark_type_conversion(python_convert, ComplexModel, iterations)
    cython_time = benchmark_type_conversion(cython_convert, ComplexModel, iterations)

    speedup = python_time / cython_time

    print(f"\n{'=' * 60}")
    print(f"Complex Model Performance (nested, {iterations} iterations)")
    print(f"{'=' * 60}")
    print(f"Python time:  {python_time * 1000:.2f} ms")
    print(f"Cython time:  {cython_time * 1000:.2f} ms")
    print(f"Speedup:      {speedup:.2f}x")
    print(f"{'=' * 60}")

    # Assert Cython is at least 2x faster for complex models
    assert speedup >= 2.0, f"Cython speedup ({speedup:.2f}x) is less than required 2.0x"


@pytest.mark.benchmark
def test_python_fallback_available():
    """Test that pure Python fallback is always available."""
    # This should never fail - fallback must always work
    # Use msgspec.inspect to get proper type objects (not raw Python types)
    type_info = msgspec.inspect.type_info(SimpleModel)
    # First field is 'id: int' - its type should be IntType
    int_field_type = type_info.fields[0].type
    result = python_convert(int_field_type)
    assert result is int


@pytest.mark.benchmark
def test_overall_average_speedup():
    """Test that overall average speedup meets requirements."""
    if not _CYTHON_AVAILABLE:
        pytest.skip("Cython extensions not available")

    iterations = 10000

    # Benchmark all models
    models = [SimpleModel, MediumModel, ComplexModel]
    speedups = []

    for model in models:
        python_time = benchmark_type_conversion(python_convert, model, iterations)
        cython_time = benchmark_type_conversion(cython_convert, model, iterations)
        speedups.append(python_time / cython_time)

    avg_speedup = sum(speedups) / len(speedups)

    print(f"\n{'=' * 60}")
    print("Overall Average Performance")
    print(f"{'=' * 60}")
    print(f"Simple model:   {speedups[0]:.2f}x")
    print(f"Medium model:   {speedups[1]:.2f}x")
    print(f"Complex model:  {speedups[2]:.2f}x")
    print(f"Average:        {avg_speedup:.2f}x")
    print(f"{'=' * 60}")

    # Assert average speedup is at least 2x
    assert avg_speedup >= 2.0, (
        f"Average Cython speedup ({avg_speedup:.2f}x) is less than required 2.0x"
    )


@pytest.mark.benchmark
@pytest.mark.skipif(not _CYTHON_AVAILABLE, reason="Cython extensions not available")
def test_cython_correctness():
    """Test that Cython produces same results as Python implementation."""
    # Test various msgspec types
    test_types = [
        int,
        str,
        float,
        bool,
        bytes,
    ]

    for test_type in test_types:
        python_result = python_convert(test_type)
        cython_result = cython_convert(test_type)
        assert python_result == cython_result, (
            f"Cython result differs from Python for type {test_type}"
        )


if __name__ == "__main__":
    # Run benchmarks directly
    print("\n" + "=" * 70)
    print("PERFORMANCE REGRESSION TESTS")
    print("=" * 70)

    if not _CYTHON_AVAILABLE:
        print("\n⚠ WARNING: Cython extensions not available!")
        print("Install and compile Cython for performance tests:")
        print("  make install-build")
        print("  make compile-cython")
        print("=" * 70 + "\n")
        exit(1)

    print("\n✓ Cython extensions available, running benchmarks...\n")

    # Run tests
    pytest.main([__file__, "-v", "-m", "benchmark", "--tb=short"])
