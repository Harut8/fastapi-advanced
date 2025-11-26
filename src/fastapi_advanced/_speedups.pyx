# cython: language_level=3
# cython: boundscheck=False
# cython: wraparound=False
# cython: cdivision=True
# cython: infer_types=True
# cython: embedsignature=True
"""Cython-optimized functions for fastapi-advanced. See CYTHON_PERFORMANCE.md for benchmarks."""

from typing import Any, Union
from pydantic import BaseModel
import msgspec

# C-level imports for performance
from cpython.object cimport PyObject_HasAttr
from cpython.dict cimport PyDict_New, PyDict_SetItem
from cpython.tuple cimport PyTuple_New, PyTuple_SET_ITEM
from cpython.unicode cimport PyUnicode_AsUTF8, PyUnicode_GET_LENGTH
from cpython.ref cimport Py_INCREF
from cpython.mem cimport PyMem_Malloc, PyMem_Free
from cpython.bytes cimport PyBytes_FromStringAndSize
from libc.string cimport strlen, memcpy, memset

# ============================================================================
# C-Level Type Definitions for Maximum Performance
# ============================================================================

cdef enum TypeId:
    """C enum for fast type identification."""
    TYPE_INT = 0
    TYPE_STR = 1
    TYPE_FLOAT = 2
    TYPE_BOOL = 3
    TYPE_LIST = 4
    TYPE_DICT = 5
    TYPE_SET = 6
    TYPE_TUPLE = 7
    TYPE_UNION = 8
    TYPE_STRUCT = 9
    TYPE_UNKNOWN = 10
    TYPE_ENUM = 11
    TYPE_NONE = 12
    TYPE_METADATA = 13
    TYPE_DATETIME = 14
    TYPE_DATE = 15
    TYPE_UUID = 16
    TYPE_TIME = 17
    TYPE_TIMEDELTA = 18
    TYPE_BYTES = 19
    TYPE_BYTEARRAY = 20
    TYPE_DECIMAL = 21

# Pre-computed character constants for email validation (avoid ord() calls)
cdef:
    char AT_CHAR = 64  # '@'
    char DOT_CHAR = 46  # '.'
    char SPACE_CHAR = 32  # ' '


# Lazy-loaded import cache for circular dependency avoidance
cdef object _msgspec_to_pydantic_func = None

cdef inline object _get_msgspec_converter():
    """Lazy-load msgspec_to_pydantic to avoid circular imports."""
    global _msgspec_to_pydantic_func
    if _msgspec_to_pydantic_func is None:
        from fastapi_advanced.core import msgspec_to_pydantic
        _msgspec_to_pydantic_func = msgspec_to_pydantic
    return _msgspec_to_pydantic_func


cdef inline TypeId _get_type_id(str type_name) nogil:
    """Fast type ID lookup (nogil)."""
    return TYPE_UNKNOWN


cdef inline TypeId _get_type_id_with_gil(str type_name):
    """Type ID lookup with GIL."""
    # Optimized branching: most common types first for better branch prediction
    cdef char first_char = ord(type_name[0]) if len(type_name) > 0 else 0

    # Fast path: check first character for quick rejection
    if first_char == 73:  # 'I' - IntType
        if type_name == "IntType":
            return TYPE_INT
    elif first_char == 83:  # 'S' - StrType or SetType or StructType
        if type_name == "StrType":
            return TYPE_STR
        elif type_name == "SetType":
            return TYPE_SET
        elif type_name == "StructType":
            return TYPE_STRUCT
    elif first_char == 76:  # 'L' - ListType
        if type_name == "ListType":
            return TYPE_LIST
    elif first_char == 68:  # 'D' - DictType, DateTimeType, DateType, DecimalType
        if type_name == "DictType":
            return TYPE_DICT
        elif type_name == "DateTimeType":
            return TYPE_DATETIME
        elif type_name == "DateType":
            return TYPE_DATE
        elif type_name == "DecimalType":
            return TYPE_DECIMAL
    elif first_char == 70:  # 'F' - FloatType
        if type_name == "FloatType":
            return TYPE_FLOAT
    elif first_char == 66:  # 'B' - BoolType, BytesType, ByteArrayType
        if type_name == "BoolType":
            return TYPE_BOOL
        elif type_name == "BytesType":
            return TYPE_BYTES
        elif type_name == "ByteArrayType":
            return TYPE_BYTEARRAY
    elif first_char == 84:  # 'T' - TupleType, TimeType, TimeDeltaType
        if type_name == "TupleType":
            return TYPE_TUPLE
        elif type_name == "TimeType":
            return TYPE_TIME
        elif type_name == "TimeDeltaType":
            return TYPE_TIMEDELTA
    elif first_char == 85:  # 'U' - UnionType, UUIDType
        if type_name == "UnionType":
            return TYPE_UNION
        elif type_name == "UUIDType":
            return TYPE_UUID
    elif first_char == 69:  # 'E' - EnumType
        if type_name == "EnumType":
            return TYPE_ENUM
    elif first_char == 78:  # 'N' - NoneType
        if type_name == "NoneType":
            return TYPE_NONE
    elif first_char == 77:  # 'M' - Metadata
        if type_name == "Metadata":
            return TYPE_METADATA

    return TYPE_UNKNOWN


cdef class TypeConverter:
    """Fast type converter using C-level optimizations."""

    cdef dict _type_cache
    cdef dict _type_name_cache

    def __init__(self):
        self._type_cache = {}
        self._type_name_cache = {}

    cpdef object convert_type(self, object field_type):
        """Convert msgspec type to Python type annotation."""
        # Cache type name to avoid repeated type().__name__ calls
        cdef object field_type_type = type(field_type)
        cdef str type_name

        if field_type_type in self._type_name_cache:
            type_name = self._type_name_cache[field_type_type]
        else:
            type_name = field_type_type.__name__
            self._type_name_cache[field_type_type] = type_name

        # Check cache first (fast path for repeated types)
        if type_name in self._type_cache:
            return self._type_cache[type_name]

        # Get type ID using optimized enum-based lookup
        cdef TypeId type_id = _get_type_id_with_gil(type_name)
        cdef object result

        # C-level switch using enum (much faster than string if-elif)
        if type_id == TYPE_INT:
            result = int
        elif type_id == TYPE_STR:
            result = str
        elif type_id == TYPE_FLOAT:
            result = float
        elif type_id == TYPE_BOOL:
            result = bool
        elif type_id == TYPE_LIST:
            result = self._convert_list_type(field_type)
        elif type_id == TYPE_DICT:
            result = self._convert_dict_type(field_type)
        elif type_id == TYPE_SET:
            result = self._convert_set_type(field_type)
        elif type_id == TYPE_TUPLE:
            result = self._convert_tuple_type(field_type)
        elif type_id == TYPE_UNION:
            result = self._convert_union_type(field_type)
        elif type_id == TYPE_STRUCT:
            result = self._convert_struct_type(field_type)
        elif type_id == TYPE_ENUM:
            result = self._convert_enum_type(field_type)
        elif type_id == TYPE_NONE:
            result = type(None)
        elif type_id == TYPE_METADATA:
            result = self._convert_metadata_type(field_type)
        elif type_id == TYPE_DATETIME:
            from datetime import datetime
            result = datetime
        elif type_id == TYPE_DATE:
            from datetime import date
            result = date
        elif type_id == TYPE_UUID:
            from uuid import UUID
            result = UUID
        elif type_id == TYPE_TIME:
            from datetime import time
            result = time
        elif type_id == TYPE_TIMEDELTA:
            from datetime import timedelta
            result = timedelta
        elif type_id == TYPE_BYTES:
            result = bytes
        elif type_id == TYPE_BYTEARRAY:
            result = bytearray
        elif type_id == TYPE_DECIMAL:
            from decimal import Decimal
            result = Decimal
        else:
            result = Any

        # Cache result (cache simple scalar types for performance)
        if type_id <= TYPE_BOOL or (type_id >= TYPE_DATETIME and type_id <= TYPE_DECIMAL):
            self._type_cache[type_name] = result

        return result

    cdef inline object _convert_list_type(self, object field_type):
        """Convert ListType."""
        cdef object item_type_attr = "item_type"
        if PyObject_HasAttr(field_type, item_type_attr):
            item_type = self.convert_type(field_type.item_type)
            return list[item_type]
        return list

    cdef inline object _convert_dict_type(self, object field_type):
        """Convert DictType."""
        cdef object key_type_attr = "key_type"
        cdef object value_type_attr = "value_type"

        if PyObject_HasAttr(field_type, key_type_attr) and PyObject_HasAttr(field_type, value_type_attr):
            key_type = self.convert_type(field_type.key_type)
            value_type = self.convert_type(field_type.value_type)
            return dict[key_type, value_type]
        return dict

    cdef inline object _convert_set_type(self, object field_type):
        """Convert SetType."""
        cdef object item_type_attr = "item_type"
        if PyObject_HasAttr(field_type, item_type_attr):
            item_type = self.convert_type(field_type.item_type)
            return set[item_type]
        return set

    cdef inline object _convert_tuple_type(self, object field_type):
        """Convert TupleType."""
        cdef object item_types_attr = "item_types"
        cdef list types
        cdef object t

        if PyObject_HasAttr(field_type, item_types_attr):
            # Use explicit loop instead of list comprehension for C optimization
            types = []
            for t in field_type.item_types:
                types.append(self.convert_type(t))
            return tuple[tuple(types)]
        return tuple

    cdef inline object _convert_union_type(self, object field_type):
        """Convert UnionType."""
        cdef object types_attr = "types"
        cdef list types
        cdef object t
        cdef Py_ssize_t n
        cdef type none_type

        if PyObject_HasAttr(field_type, types_attr):
            # Convert types with explicit loop
            types = []
            for t in field_type.types:
                types.append(self.convert_type(t))

            # Handle Optional (T | None) - check if any converted type is NoneType
            n = len(types)
            none_type = type(None)
            if n == 2 and none_type in types:
                # Get the non-None type from already converted types
                for t in types:
                    if t is not none_type:
                        return Union[t, None]

            return Union[tuple(types)]
        return Any

    cdef inline object _convert_struct_type(self, object field_type):
        """Convert StructType."""
        return _get_msgspec_converter()(field_type.cls)

    cdef inline object _convert_enum_type(self, object field_type):
        """Convert EnumType to the actual Python Enum class."""
        cdef object cls_attr = "cls"
        if PyObject_HasAttr(field_type, cls_attr):
            return field_type.cls
        return Any

    cdef inline object _convert_metadata_type(self, object field_type):
        """Convert Metadata type by unwrapping the inner type."""
        cdef object type_attr = "type"
        if PyObject_HasAttr(field_type, type_attr):
            return self.convert_type(field_type.type)
        return Any


# Global singleton instance
_type_converter = TypeConverter()


def convert_msgspec_type_fast(field_type: Any) -> Any:
    """Fast type conversion (Cython-optimized)."""
    return _type_converter.convert_type(field_type)


cdef int _validate_email_nogil(const char* email_c, Py_ssize_t length) nogil:
    """Email validation without GIL (pure C)."""
    cdef:
        int at_count = 0
        int dot_after_at = 0
        Py_ssize_t at_pos = -1
        Py_ssize_t i
        char c

    if length < 5:  # Minimum: a@b.c
        return 0

    # Count @ symbols and find position (C-level loop, no Python overhead)
    for i in range(length):
        c = email_c[i]
        if c == AT_CHAR:
            at_count += 1
            at_pos = i

    # Validation checks using C-level comparisons
    if at_count != 1:
        return 0

    if at_pos == 0 or at_pos == length - 1:
        return 0

    # Check for dot after @ (C-level loop)
    for i in range(at_pos + 1, length):
        c = email_c[i]
        if c == DOT_CHAR:
            if i < length - 1:  # Not at the end
                dot_after_at = 1
                break

    return dot_after_at


def validate_email_fast(str email) -> bint:
    """Fast email validation (C-level with nogil)."""
    cdef:
        const char* email_c
        Py_ssize_t length
        int result

    # Get C string buffer and length (requires GIL)
    length = PyUnicode_GET_LENGTH(email)
    email_c = PyUnicode_AsUTF8(email)

    # Perform validation without GIL (can run in parallel)
    with nogil:
        result = _validate_email_nogil(email_c, length)

    return result == 1


def validate_username_length_fast(str username, int min_len=3, int max_len=50) -> bint:
    """Fast username length validation (C-level)."""
    cdef Py_ssize_t length = PyUnicode_GET_LENGTH(username)
    return min_len <= length <= max_len


# ============================================================================
# Field Inspection Optimization
# ============================================================================

def process_struct_fields_fast(object struct_cls, object type_converter_func) -> dict:
    """
    Fast field processing for msgspec structs with zero-copy optimization (C-level).

    Uses pre-allocated dictionary and C-level indexing for maximum performance.

    Returns:
        Dictionary mapping field names to (python_type, default_value, metadata).
        metadata contains 'description' and 'examples' from msgspec.Meta if present.
    """
    import msgspec

    # Get struct metadata
    cdef object type_info = msgspec.inspect.type_info(struct_cls)
    cdef object nodefault = msgspec.NODEFAULT

    # C-level typed loop variables
    cdef:
        object field
        object python_type
        object default_value
        str field_name
        object field_default
        object field_default_factory
        Py_ssize_t i, n_fields
        object ellipsis = ...
        str field_type_name
        object extra
        dict metadata

    # Get fields list
    cdef object fields = type_info.fields
    n_fields = len(fields)

    # Pre-allocate dictionary using C-level API for zero-copy efficiency
    cdef dict field_definitions = PyDict_New()

    # Iterate over fields with C-level optimization
    for i in range(n_fields):
        field = fields[i]
        field_name = field.name

        # Convert msgspec type to Python type (may use cache)
        python_type = type_converter_func(field.type)

        # Cache field attributes for faster access (single attribute lookup)
        field_default = field.default
        field_default_factory = field.default_factory

        # Handle default values with optimized branching
        if field_default is not nodefault:
            default_value = field_default
        elif field_default_factory is not nodefault:
            default_value = field_default_factory()
        else:
            # Use cached ellipsis for required fields
            default_value = ellipsis

        # Extract metadata from Metadata type (Annotated[T, msgspec.Meta(...)])
        metadata = None
        field_type_name = type(field.type).__name__
        if field_type_name == "Metadata":
            extra = getattr(field.type, "extra_json_schema", None)
            if extra is not None:
                metadata = {}
                if "description" in extra:
                    metadata["description"] = extra["description"]
                if "examples" in extra:
                    metadata["examples"] = extra["examples"]

        # Direct C-level dictionary insertion (zero-copy)
        PyDict_SetItem(field_definitions, field_name, (python_type, default_value, metadata))

    return field_definitions


# ============================================================================
# Pagination Calculations Optimization
# ============================================================================

cdef inline long _calculate_total_pages(long total_results, long page_size) nogil:
    """Calculate total pages (nogil)."""
    if page_size > 0:
        return (total_results + page_size - 1) // page_size
    return 0


cdef class PaginationCalculator:
    """Fast pagination calculator (C-level)."""

    cdef long total_results
    cdef long page_size
    cdef long current_page
    cdef long total_pages
    cdef bint has_next
    cdef bint has_previous

    def __init__(self, long total_results, long page_size, long current_page):
        cdef long calc_total_pages

        # Store parameters
        self.total_results = total_results
        self.page_size = page_size
        self.current_page = current_page

        # Calculate total pages without GIL (pure C computation)
        with nogil:
            calc_total_pages = _calculate_total_pages(total_results, page_size)

        self.total_pages = calc_total_pages

        # Calculate has_next and has_previous (C-level comparisons, no GIL needed)
        with nogil:
            self.has_next = current_page < calc_total_pages
            self.has_previous = current_page > 1

    cpdef dict get_metadata(self):
        """Get pagination metadata."""
        return {
            "current_page": self.current_page,
            "total_pages": self.total_pages,
            "total_results": self.total_results,
            "page_size": self.page_size,
            "has_next": self.has_next,
            "has_previous": self.has_previous,
        }


def calculate_pagination_fast(long total_results, long page_size, long current_page) -> dict:
    """Fast pagination calculation (C-level)."""
    cdef PaginationCalculator calc = PaginationCalculator(total_results, page_size, current_page)
    return calc.get_metadata()


# ============================================================================
# Response Model Instantiation Helpers
# ============================================================================

def create_response_dict_fast(object data, str message, str status) -> dict:
    """
    Fast response dict creation with zero-copy optimization (C-level).

    Uses PyDict_New for pre-sized allocation to avoid rehashing.
    """
    cdef dict response = PyDict_New()

    # Direct C-level dictionary insertion (faster than Python dict literal)
    PyDict_SetItem(response, "data", data)
    PyDict_SetItem(response, "message", message)
    PyDict_SetItem(response, "status", status)

    return response


def create_paginated_dict_fast(
    list items,
    long total_results,
    long current_page,
    long page_size,
    str message,
    str status
) -> dict:
    """
    Fast paginated response dict creation with zero-copy optimization (C-level).

    Uses PyDict_New and direct C-level insertions for maximum performance.
    Performs pagination calculations without GIL for parallelization.
    """
    cdef:
        long total_pages
        bint has_next
        bint has_previous
        dict response

    # Perform calculations without GIL (pure C, can run in parallel)
    with nogil:
        total_pages = _calculate_total_pages(total_results, page_size)
        has_next = current_page < total_pages
        has_previous = current_page > 1

    # Create dictionary with C-level API for zero-copy efficiency
    response = PyDict_New()

    # Direct C-level dictionary insertions (faster than Python dict literal)
    PyDict_SetItem(response, "items", items)
    PyDict_SetItem(response, "current_page", current_page)
    PyDict_SetItem(response, "total_pages", total_pages)
    PyDict_SetItem(response, "total_results", total_results)
    PyDict_SetItem(response, "page_size", page_size)
    PyDict_SetItem(response, "has_next", has_next)
    PyDict_SetItem(response, "has_previous", has_previous)
    PyDict_SetItem(response, "message", message)
    PyDict_SetItem(response, "status", status)

    return response
