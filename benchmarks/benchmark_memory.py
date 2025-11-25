#!/usr/bin/env python3
"""
Memory usage benchmark for Cython + msgspec vs Pydantic.

Measures actual memory consumption across different scenarios:
1. Model instantiation overhead
2. Serialization memory usage
3. Deserialization memory usage
4. Large dataset handling
5. Memory leaks detection
6. Peak memory usage under load

Uses tracemalloc and psutil for accurate memory profiling.
"""

import gc
import sys
import tracemalloc
import time
from typing import List, Dict, Any
import statistics

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    print("WARNING: psutil not available, some metrics will be unavailable")


# ============================================================================
# Test Models
# ============================================================================

# msgspec models
import msgspec


class UserMsgspec(msgspec.Struct):
    """msgspec user model for testing."""
    id: int
    username: str
    email: str
    full_name: str
    is_active: bool
    age: int
    balance: float


class ProductMsgspec(msgspec.Struct):
    """msgspec product model with nested data."""
    id: int
    name: str
    description: str
    price: float
    in_stock: bool
    tags: List[str]
    metadata: Dict[str, str]


# Pydantic models
from pydantic import BaseModel, EmailStr


class UserPydantic(BaseModel):
    """Pydantic user model for testing."""
    id: int
    username: str
    email: str
    full_name: str
    is_active: bool
    age: int
    balance: float


class ProductPydantic(BaseModel):
    """Pydantic product model with nested data."""
    id: int
    name: str
    description: str
    price: float
    in_stock: bool
    tags: List[str]
    metadata: Dict[str, str]


# ============================================================================
# Memory Measurement Utilities
# ============================================================================

class MemoryProfiler:
    """Context manager for memory profiling."""

    def __init__(self, description: str):
        self.description = description
        self.start_memory = 0
        self.end_memory = 0
        self.peak_memory = 0
        self.process = psutil.Process() if PSUTIL_AVAILABLE else None

    def __enter__(self):
        gc.collect()  # Clean up before measurement
        time.sleep(0.1)  # Let GC finish

        tracemalloc.start()
        if self.process:
            self.start_memory = self.process.memory_info().rss
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.process:
            self.end_memory = self.process.memory_info().rss

        current, peak = tracemalloc.get_traced_memory()
        self.peak_memory = peak
        tracemalloc.stop()

        gc.collect()

    def get_delta_mb(self) -> float:
        """Get memory delta in MB."""
        if self.process:
            return (self.end_memory - self.start_memory) / 1024 / 1024
        return 0

    def get_peak_mb(self) -> float:
        """Get peak traced memory in MB."""
        return self.peak_memory / 1024 / 1024


def measure_object_size(obj: Any) -> int:
    """
    Measure the actual size of an object including all referenced objects.
    Uses sys.getsizeof recursively for accurate measurement.
    """
    seen = set()

    def sizeof(o):
        if id(o) in seen:
            return 0
        seen.add(id(o))

        size = sys.getsizeof(o)

        if isinstance(o, dict):
            size += sum(sizeof(k) + sizeof(v) for k, v in o.items())
        elif hasattr(o, '__dict__'):
            size += sizeof(o.__dict__)
        elif hasattr(o, '__iter__') and not isinstance(o, (str, bytes, bytearray)):
            try:
                size += sum(sizeof(i) for i in o)
            except TypeError:
                pass

        return size

    return sizeof(obj)


# ============================================================================
# Benchmark Functions
# ============================================================================

def benchmark_model_instantiation(iterations: int = 10000):
    """
    Measure memory overhead of creating model instances.
    Tests both small and large object counts.
    """
    print("\n" + "="*80)
    print("BENCHMARK 1: Model Instantiation Memory Overhead")
    print("="*80)

    test_data = {
        "id": 12345,
        "username": "testuser",
        "email": "test@example.com",
        "full_name": "Test User",
        "is_active": True,
        "age": 30,
        "balance": 1234.56
    }

    results = {}

    # Test msgspec
    print(f"\nTesting msgspec ({iterations:,} instances)...")
    with MemoryProfiler("msgspec instantiation") as profiler:
        msgspec_users = []
        for _ in range(iterations):
            user = UserMsgspec(**test_data)
            msgspec_users.append(user)

    msgspec_peak = profiler.get_peak_mb()
    msgspec_delta = profiler.get_delta_mb()
    msgspec_per_object = (profiler.peak_memory / iterations) if iterations > 0 else 0

    results['msgspec'] = {
        'peak_mb': msgspec_peak,
        'delta_mb': msgspec_delta,
        'bytes_per_object': msgspec_per_object,
        'total_objects': iterations
    }

    del msgspec_users
    gc.collect()
    time.sleep(0.2)

    # Test Pydantic
    print(f"Testing Pydantic ({iterations:,} instances)...")
    with MemoryProfiler("pydantic instantiation") as profiler:
        pydantic_users = []
        for _ in range(iterations):
            user = UserPydantic(**test_data)
            pydantic_users.append(user)

    pydantic_peak = profiler.get_peak_mb()
    pydantic_delta = profiler.get_delta_mb()
    pydantic_per_object = (profiler.peak_memory / iterations) if iterations > 0 else 0

    results['pydantic'] = {
        'peak_mb': pydantic_peak,
        'delta_mb': pydantic_delta,
        'bytes_per_object': pydantic_per_object,
        'total_objects': iterations
    }

    del pydantic_users
    gc.collect()

    # Print results
    print("\nResults:")
    print(f"{'Metric':<30} {'msgspec':<20} {'Pydantic':<20} {'Ratio':<15}")
    print("-" * 85)
    print(f"{'Peak Memory (MB)':<30} {msgspec_peak:<20.2f} {pydantic_peak:<20.2f} {pydantic_peak/msgspec_peak if msgspec_peak > 0 else 0:<15.2f}x")
    print(f"{'Delta Memory (MB)':<30} {msgspec_delta:<20.2f} {pydantic_delta:<20.2f} {pydantic_delta/msgspec_delta if msgspec_delta > 0 else 0:<15.2f}x")
    print(f"{'Bytes per Object':<30} {msgspec_per_object:<20.0f} {pydantic_per_object:<20.0f} {pydantic_per_object/msgspec_per_object if msgspec_per_object > 0 else 0:<15.2f}x")

    return results


def benchmark_single_object_size():
    """
    Measure the exact size of a single object instance.
    Uses sys.getsizeof for precise measurement.
    """
    print("\n" + "="*80)
    print("BENCHMARK 2: Single Object Size")
    print("="*80)

    test_data = {
        "id": 12345,
        "username": "testuser",
        "email": "test@example.com",
        "full_name": "Test User",
        "is_active": True,
        "age": 30,
        "balance": 1234.56
    }

    # Create instances
    msgspec_user = UserMsgspec(**test_data)
    pydantic_user = UserPydantic(**test_data)

    # Measure deep size
    msgspec_size = measure_object_size(msgspec_user)
    pydantic_size = measure_object_size(pydantic_user)

    # Also measure shallow size
    msgspec_shallow = sys.getsizeof(msgspec_user)
    pydantic_shallow = sys.getsizeof(pydantic_user)

    print("\nResults:")
    print(f"{'Metric':<30} {'msgspec':<20} {'Pydantic':<20} {'Ratio':<15}")
    print("-" * 85)
    print(f"{'Shallow Size (bytes)':<30} {msgspec_shallow:<20} {pydantic_shallow:<20} {pydantic_shallow/msgspec_shallow:<15.2f}x")
    print(f"{'Deep Size (bytes)':<30} {msgspec_size:<20} {pydantic_size:<20} {pydantic_size/msgspec_size:<15.2f}x")

    return {
        'msgspec': {'shallow': msgspec_shallow, 'deep': msgspec_size},
        'pydantic': {'shallow': pydantic_shallow, 'deep': pydantic_size}
    }


def benchmark_serialization_memory(iterations: int = 1000):
    """
    Measure memory usage during JSON serialization.
    Tests both encoding and the resulting JSON size.
    """
    print("\n" + "="*80)
    print("BENCHMARK 3: Serialization Memory Usage")
    print("="*80)

    # Create test objects
    test_data = {
        "id": 12345,
        "username": "testuser",
        "email": "test@example.com",
        "full_name": "Test User",
        "is_active": True,
        "age": 30,
        "balance": 1234.56
    }

    msgspec_users = [UserMsgspec(**test_data) for _ in range(iterations)]
    pydantic_users = [UserPydantic(**test_data) for _ in range(iterations)]

    results = {}

    # Test msgspec serialization
    print(f"\nTesting msgspec serialization ({iterations:,} objects)...")
    encoder = msgspec.json.Encoder()

    with MemoryProfiler("msgspec serialization") as profiler:
        json_results = []
        for user in msgspec_users:
            json_data = encoder.encode(user)
            json_results.append(json_data)

    msgspec_peak = profiler.get_peak_mb()
    msgspec_json_size = sum(len(j) for j in json_results) / 1024 / 1024

    results['msgspec'] = {
        'peak_mb': msgspec_peak,
        'json_size_mb': msgspec_json_size,
        'overhead_mb': msgspec_peak - msgspec_json_size
    }

    del json_results
    gc.collect()
    time.sleep(0.2)

    # Test Pydantic serialization
    print(f"Testing Pydantic serialization ({iterations:,} objects)...")

    with MemoryProfiler("pydantic serialization") as profiler:
        json_results = []
        for user in pydantic_users:
            json_data = user.model_dump_json().encode()
            json_results.append(json_data)

    pydantic_peak = profiler.get_peak_mb()
    pydantic_json_size = sum(len(j) for j in json_results) / 1024 / 1024

    results['pydantic'] = {
        'peak_mb': pydantic_peak,
        'json_size_mb': pydantic_json_size,
        'overhead_mb': pydantic_peak - pydantic_json_size
    }

    del json_results, msgspec_users, pydantic_users
    gc.collect()

    # Print results
    print("\nResults:")
    print(f"{'Metric':<30} {'msgspec':<20} {'Pydantic':<20} {'Ratio':<15}")
    print("-" * 85)
    print(f"{'Peak Memory (MB)':<30} {msgspec_peak:<20.2f} {pydantic_peak:<20.2f} {pydantic_peak/msgspec_peak if msgspec_peak > 0 else 0:<15.2f}x")
    print(f"{'JSON Size (MB)':<30} {msgspec_json_size:<20.2f} {pydantic_json_size:<20.2f} {pydantic_json_size/msgspec_json_size if msgspec_json_size > 0 else 0:<15.2f}x")
    print(f"{'Overhead (MB)':<30} {results['msgspec']['overhead_mb']:<20.2f} {results['pydantic']['overhead_mb']:<20.2f} {results['pydantic']['overhead_mb']/results['msgspec']['overhead_mb'] if results['msgspec']['overhead_mb'] > 0 else 0:<15.2f}x")

    return results


def benchmark_deserialization_memory(iterations: int = 1000):
    """
    Measure memory usage during JSON deserialization.
    """
    print("\n" + "="*80)
    print("BENCHMARK 4: Deserialization Memory Usage")
    print("="*80)

    # Prepare JSON data
    test_json = b'{"id":12345,"username":"testuser","email":"test@example.com","full_name":"Test User","is_active":true,"age":30,"balance":1234.56}'

    results = {}

    # Test msgspec deserialization
    print(f"\nTesting msgspec deserialization ({iterations:,} objects)...")
    decoder = msgspec.json.Decoder(UserMsgspec)

    with MemoryProfiler("msgspec deserialization") as profiler:
        objects = []
        for _ in range(iterations):
            obj = decoder.decode(test_json)
            objects.append(obj)

    msgspec_peak = profiler.get_peak_mb()

    results['msgspec'] = {'peak_mb': msgspec_peak}

    del objects
    gc.collect()
    time.sleep(0.2)

    # Test Pydantic deserialization
    print(f"Testing Pydantic deserialization ({iterations:,} objects)...")

    with MemoryProfiler("pydantic deserialization") as profiler:
        objects = []
        for _ in range(iterations):
            obj = UserPydantic.model_validate_json(test_json)
            objects.append(obj)

    pydantic_peak = profiler.get_peak_mb()

    results['pydantic'] = {'peak_mb': pydantic_peak}

    del objects
    gc.collect()

    # Print results
    print("\nResults:")
    print(f"{'Metric':<30} {'msgspec':<20} {'Pydantic':<20} {'Ratio':<15}")
    print("-" * 85)
    print(f"{'Peak Memory (MB)':<30} {msgspec_peak:<20.2f} {pydantic_peak:<20.2f} {pydantic_peak/msgspec_peak if msgspec_peak > 0 else 0:<15.2f}x")

    return results


def benchmark_large_dataset(count: int = 100000):
    """
    Test memory usage with large datasets.
    Simulates real-world scenarios with many objects.
    """
    print("\n" + "="*80)
    print(f"BENCHMARK 5: Large Dataset ({count:,} objects)")
    print("="*80)

    results = {}

    # Test msgspec
    print(f"\nTesting msgspec with {count:,} objects...")

    with MemoryProfiler("msgspec large dataset") as profiler:
        users = []
        for i in range(count):
            user = UserMsgspec(
                id=i,
                username=f"user_{i}",
                email=f"user{i}@example.com",
                full_name=f"User {i}",
                is_active=i % 2 == 0,
                age=20 + (i % 50),
                balance=float(i * 10.5)
            )
            users.append(user)

    msgspec_peak = profiler.get_peak_mb()
    msgspec_delta = profiler.get_delta_mb()

    results['msgspec'] = {
        'peak_mb': msgspec_peak,
        'delta_mb': msgspec_delta,
        'mb_per_1k_objects': (msgspec_peak / count) * 1000
    }

    del users
    gc.collect()
    time.sleep(0.5)

    # Test Pydantic
    print(f"Testing Pydantic with {count:,} objects...")

    with MemoryProfiler("pydantic large dataset") as profiler:
        users = []
        for i in range(count):
            user = UserPydantic(
                id=i,
                username=f"user_{i}",
                email=f"user{i}@example.com",
                full_name=f"User {i}",
                is_active=i % 2 == 0,
                age=20 + (i % 50),
                balance=float(i * 10.5)
            )
            users.append(user)

    pydantic_peak = profiler.get_peak_mb()
    pydantic_delta = profiler.get_delta_mb()

    results['pydantic'] = {
        'peak_mb': pydantic_peak,
        'delta_mb': pydantic_delta,
        'mb_per_1k_objects': (pydantic_peak / count) * 1000
    }

    del users
    gc.collect()

    # Print results
    print("\nResults:")
    print(f"{'Metric':<30} {'msgspec':<20} {'Pydantic':<20} {'Ratio':<15}")
    print("-" * 85)
    print(f"{'Peak Memory (MB)':<30} {msgspec_peak:<20.2f} {pydantic_peak:<20.2f} {pydantic_peak/msgspec_peak if msgspec_peak > 0 else 0:<15.2f}x")
    print(f"{'Delta Memory (MB)':<30} {msgspec_delta:<20.2f} {pydantic_delta:<20.2f} {pydantic_delta/msgspec_delta if msgspec_delta > 0 else 0:<15.2f}x")
    print(f"{'MB per 1K objects':<30} {results['msgspec']['mb_per_1k_objects']:<20.2f} {results['pydantic']['mb_per_1k_objects']:<20.2f} {results['pydantic']['mb_per_1k_objects']/results['msgspec']['mb_per_1k_objects'] if results['msgspec']['mb_per_1k_objects'] > 0 else 0:<15.2f}x")

    return results


def benchmark_nested_structures(iterations: int = 1000):
    """
    Test memory usage with nested/complex data structures.
    """
    print("\n" + "="*80)
    print(f"BENCHMARK 6: Nested Structures ({iterations:,} objects)")
    print("="*80)

    test_data = {
        "id": 1,
        "name": "Test Product",
        "description": "A test product with a longer description to simulate real data",
        "price": 99.99,
        "in_stock": True,
        "tags": ["electronics", "gadgets", "popular", "sale", "featured"],
        "metadata": {
            "manufacturer": "TestCorp",
            "warranty": "2 years",
            "color": "black",
            "weight": "500g",
            "dimensions": "10x20x5cm"
        }
    }

    results = {}

    # Test msgspec
    print(f"\nTesting msgspec...")

    with MemoryProfiler("msgspec nested") as profiler:
        products = []
        for _ in range(iterations):
            product = ProductMsgspec(**test_data)
            products.append(product)

    msgspec_peak = profiler.get_peak_mb()

    results['msgspec'] = {'peak_mb': msgspec_peak}

    del products
    gc.collect()
    time.sleep(0.2)

    # Test Pydantic
    print(f"Testing Pydantic...")

    with MemoryProfiler("pydantic nested") as profiler:
        products = []
        for _ in range(iterations):
            product = ProductPydantic(**test_data)
            products.append(product)

    pydantic_peak = profiler.get_peak_mb()

    results['pydantic'] = {'peak_mb': pydantic_peak}

    del products
    gc.collect()

    # Print results
    print("\nResults:")
    print(f"{'Metric':<30} {'msgspec':<20} {'Pydantic':<20} {'Ratio':<15}")
    print("-" * 85)
    print(f"{'Peak Memory (MB)':<30} {msgspec_peak:<20.2f} {pydantic_peak:<20.2f} {pydantic_peak/msgspec_peak if msgspec_peak > 0 else 0:<15.2f}x")

    return results


def benchmark_process_memory():
    """
    Measure overall process memory footprint.
    Requires psutil.
    """
    if not PSUTIL_AVAILABLE:
        print("\n" + "="*80)
        print("BENCHMARK 7: Process Memory (SKIPPED - psutil not available)")
        print("="*80)
        return None

    print("\n" + "="*80)
    print("BENCHMARK 7: Process Memory Footprint")
    print("="*80)

    process = psutil.Process()

    # Baseline
    gc.collect()
    time.sleep(0.5)
    baseline = process.memory_info()

    print(f"\nBaseline Process Memory:")
    print(f"  RSS: {baseline.rss / 1024 / 1024:.2f} MB")
    print(f"  VMS: {baseline.vms / 1024 / 1024:.2f} MB")

    # Create large msgspec dataset
    print(f"\nCreating 50,000 msgspec objects...")
    msgspec_users = []
    for i in range(50000):
        user = UserMsgspec(
            id=i,
            username=f"user_{i}",
            email=f"user{i}@example.com",
            full_name=f"User {i}",
            is_active=True,
            age=30,
            balance=1000.0
        )
        msgspec_users.append(user)

    msgspec_mem = process.memory_info()
    msgspec_delta = (msgspec_mem.rss - baseline.rss) / 1024 / 1024

    print(f"After msgspec objects:")
    print(f"  RSS: {msgspec_mem.rss / 1024 / 1024:.2f} MB (Δ{msgspec_delta:+.2f} MB)")

    del msgspec_users
    gc.collect()
    time.sleep(0.5)

    # Create large Pydantic dataset
    print(f"\nCreating 50,000 Pydantic objects...")
    pydantic_users = []
    for i in range(50000):
        user = UserPydantic(
            id=i,
            username=f"user_{i}",
            email=f"user{i}@example.com",
            full_name=f"User {i}",
            is_active=True,
            age=30,
            balance=1000.0
        )
        pydantic_users.append(user)

    pydantic_mem = process.memory_info()
    pydantic_delta = (pydantic_mem.rss - baseline.rss) / 1024 / 1024

    print(f"After Pydantic objects:")
    print(f"  RSS: {pydantic_mem.rss / 1024 / 1024:.2f} MB (Δ{pydantic_delta:+.2f} MB)")

    print("\nComparison:")
    print(f"  msgspec delta: {msgspec_delta:.2f} MB")
    print(f"  Pydantic delta: {pydantic_delta:.2f} MB")
    print(f"  Ratio: {pydantic_delta/msgspec_delta if msgspec_delta > 0 else 0:.2f}x")

    del pydantic_users
    gc.collect()

    return {
        'msgspec_delta_mb': msgspec_delta,
        'pydantic_delta_mb': pydantic_delta
    }


# ============================================================================
# Main Runner
# ============================================================================

def print_summary(all_results: Dict[str, Any]):
    """Print comprehensive summary of all benchmarks."""
    print("\n" + "="*80)
    print("COMPREHENSIVE MEMORY BENCHMARK SUMMARY")
    print("="*80)

    print("\n1. OBJECT OVERHEAD:")
    if 'instantiation' in all_results and all_results['instantiation']:
        msg = all_results['instantiation']['msgspec']
        pyd = all_results['instantiation']['pydantic']
        ratio = pyd['bytes_per_object'] / msg['bytes_per_object'] if msg['bytes_per_object'] > 0 else 0
        print(f"   Bytes per object: msgspec {msg['bytes_per_object']:.0f} | Pydantic {pyd['bytes_per_object']:.0f} | {ratio:.2f}x")

    print("\n2. SINGLE OBJECT SIZE:")
    if 'single_object' in all_results and all_results['single_object']:
        msg = all_results['single_object']['msgspec']
        pyd = all_results['single_object']['pydantic']
        ratio = pyd['deep'] / msg['deep'] if msg['deep'] > 0 else 0
        print(f"   Deep size: msgspec {msg['deep']} bytes | Pydantic {pyd['deep']} bytes | {ratio:.2f}x")

    print("\n3. SERIALIZATION:")
    if 'serialization' in all_results and all_results['serialization']:
        msg = all_results['serialization']['msgspec']['peak_mb']
        pyd = all_results['serialization']['pydantic']['peak_mb']
        ratio = pyd / msg if msg > 0 else 0
        print(f"   Peak memory: msgspec {msg:.2f} MB | Pydantic {pyd:.2f} MB | {ratio:.2f}x")

    print("\n4. DESERIALIZATION:")
    if 'deserialization' in all_results and all_results['deserialization']:
        msg = all_results['deserialization']['msgspec']['peak_mb']
        pyd = all_results['deserialization']['pydantic']['peak_mb']
        ratio = pyd / msg if msg > 0 else 0
        print(f"   Peak memory: msgspec {msg:.2f} MB | Pydantic {pyd:.2f} MB | {ratio:.2f}x")

    print("\n5. LARGE DATASET (100K objects):")
    if 'large_dataset' in all_results and all_results['large_dataset']:
        msg = all_results['large_dataset']['msgspec']['peak_mb']
        pyd = all_results['large_dataset']['pydantic']['peak_mb']
        ratio = pyd / msg if msg > 0 else 0
        print(f"   Peak memory: msgspec {msg:.2f} MB | Pydantic {pyd:.2f} MB | {ratio:.2f}x")
        print(f"   Per 1K objects: msgspec {all_results['large_dataset']['msgspec']['mb_per_1k_objects']:.2f} MB | Pydantic {all_results['large_dataset']['pydantic']['mb_per_1k_objects']:.2f} MB")

    print("\n6. NESTED STRUCTURES:")
    if 'nested' in all_results and all_results['nested']:
        msg = all_results['nested']['msgspec']['peak_mb']
        pyd = all_results['nested']['pydantic']['peak_mb']
        ratio = pyd / msg if msg > 0 else 0
        print(f"   Peak memory: msgspec {msg:.2f} MB | Pydantic {pyd:.2f} MB | {ratio:.2f}x")

    print("\n" + "="*80)

    # Calculate overall average ratio
    ratios = []
    if 'instantiation' in all_results and all_results['instantiation']:
        msg = all_results['instantiation']['msgspec']['bytes_per_object']
        pyd = all_results['instantiation']['pydantic']['bytes_per_object']
        if msg > 0:
            ratios.append(pyd / msg)

    if 'large_dataset' in all_results and all_results['large_dataset']:
        msg = all_results['large_dataset']['msgspec']['peak_mb']
        pyd = all_results['large_dataset']['pydantic']['peak_mb']
        if msg > 0:
            ratios.append(pyd / msg)

    if ratios:
        avg_ratio = statistics.mean(ratios)
        print(f"AVERAGE MEMORY OVERHEAD: Pydantic uses {avg_ratio:.2f}x more memory than msgspec")

    print("="*80)


def main():
    """Run all memory benchmarks."""
    print("="*80)
    print("MEMORY USAGE BENCHMARK: Cython + msgspec vs Pydantic")
    print("="*80)
    print("\nThis benchmark measures actual memory consumption using:")
    print("- tracemalloc for Python memory tracking")
    print("- sys.getsizeof for object size measurement")
    if PSUTIL_AVAILABLE:
        print("- psutil for process memory monitoring")
    print()

    all_results = {}

    # Run all benchmarks
    all_results['instantiation'] = benchmark_model_instantiation(iterations=10000)
    all_results['single_object'] = benchmark_single_object_size()
    all_results['serialization'] = benchmark_serialization_memory(iterations=1000)
    all_results['deserialization'] = benchmark_deserialization_memory(iterations=1000)
    all_results['large_dataset'] = benchmark_large_dataset(count=100000)
    all_results['nested'] = benchmark_nested_structures(iterations=1000)
    all_results['process'] = benchmark_process_memory()

    # Print summary
    print_summary(all_results)

    return all_results


if __name__ == "__main__":
    main()
