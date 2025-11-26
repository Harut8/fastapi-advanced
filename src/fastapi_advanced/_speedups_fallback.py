"""Pure Python fallback for _speedups module (used when Cython not available)."""

import re
from datetime import date, datetime
from typing import Any
from uuid import UUID


class TypeConverter:
    """Pure Python type converter (fallback implementation)."""

    def __init__(self) -> None:
        self._type_cache: dict[str, Any] = {}

    def convert_type(self, field_type: Any) -> Any:
        """Convert msgspec type to Python type annotation."""
        type_name = type(field_type).__name__

        # Check cache first
        if type_name in self._type_cache:
            return self._type_cache[type_name]

        # Type conversion logic (same as Cython version)
        result: Any

        if type_name == "IntType":
            result = int
        elif type_name == "StrType":
            result = str
        elif type_name == "FloatType":
            result = float
        elif type_name == "BoolType":
            result = bool
        elif type_name == "ListType":
            result = self._convert_list_type(field_type)
        elif type_name == "DictType":
            result = self._convert_dict_type(field_type)
        elif type_name == "SetType":
            result = self._convert_set_type(field_type)
        elif type_name == "TupleType":
            result = self._convert_tuple_type(field_type)
        elif type_name == "UnionType":
            result = self._convert_union_type(field_type)
        elif type_name == "StructType":
            result = self._convert_struct_type(field_type)
        elif type_name == "EnumType":
            result = self._convert_enum_type(field_type)
        elif type_name == "NoneType":
            result = type(None)
        elif type_name == "Metadata":
            result = self._convert_metadata_type(field_type)
        elif type_name == "DateTimeType":
            result = datetime
        elif type_name == "DateType":
            result = date
        elif type_name == "UUIDType":
            result = UUID
        elif type_name == "TimeType":
            from datetime import time

            result = time
        elif type_name == "TimeDeltaType":
            from datetime import timedelta

            result = timedelta
        elif type_name == "BytesType":
            result = bytes
        elif type_name == "ByteArrayType":
            result = bytearray
        elif type_name == "DecimalType":
            from decimal import Decimal

            result = Decimal
        else:
            result = Any

        # Cache simple types (not composite types like Union, List, Enum, Struct)
        if type_name in (
            "IntType",
            "StrType",
            "FloatType",
            "BoolType",
            "DateTimeType",
            "DateType",
            "UUIDType",
            "TimeType",
            "TimeDeltaType",
            "BytesType",
            "ByteArrayType",
            "DecimalType",
        ):
            self._type_cache[type_name] = result
        return result

    def _convert_list_type(self, field_type: Any) -> Any:
        """Convert ListType."""
        if hasattr(field_type, "item_type"):
            item_type = self.convert_type(field_type.item_type)
            return list[item_type]  # type: ignore
        return list

    def _convert_dict_type(self, field_type: Any) -> Any:
        """Convert DictType."""
        if hasattr(field_type, "key_type") and hasattr(field_type, "value_type"):
            key_type = self.convert_type(field_type.key_type)
            value_type = self.convert_type(field_type.value_type)
            return dict[key_type, value_type]  # type: ignore
        return dict

    def _convert_set_type(self, field_type: Any) -> Any:
        """Convert SetType."""
        if hasattr(field_type, "item_type"):
            item_type = self.convert_type(field_type.item_type)
            return set[item_type]  # type: ignore
        return set

    def _convert_tuple_type(self, field_type: Any) -> Any:
        """Convert TupleType."""
        if hasattr(field_type, "item_types"):
            types = [self.convert_type(t) for t in field_type.item_types]
            return tuple[tuple(types)]  # type: ignore
        return tuple

    def _convert_union_type(self, field_type: Any) -> Any:
        """Convert UnionType."""
        if hasattr(field_type, "types"):
            types = [self.convert_type(t) for t in field_type.types]
            # Handle Optional (T | None) - check if any converted type is NoneType
            if len(types) == 2 and type(None) in types:
                non_none = [t for t in types if t is not type(None)][0]
                return non_none | None
            # Use | syntax for union types
            result = types[0]
            for t in types[1:]:
                result = result | t
            return result
        return Any

    def _convert_struct_type(self, field_type: Any) -> Any:
        """Convert StructType - return the Pydantic schema for nested structs."""
        from .core import msgspec_to_pydantic

        # Use forward reference string to avoid infinite recursion
        # The actual schema will be resolved by Pydantic at model creation time
        return msgspec_to_pydantic(field_type.cls)

    def _convert_enum_type(self, field_type: Any) -> Any:
        """Convert EnumType to the actual Python Enum class."""
        if hasattr(field_type, "cls"):
            return field_type.cls
        return Any

    def _convert_metadata_type(self, field_type: Any) -> Any:
        """Convert Metadata type by unwrapping the inner type."""
        if hasattr(field_type, "type"):
            return self.convert_type(field_type.type)
        return Any


# Global singleton
_type_converter = TypeConverter()


def convert_msgspec_type_fast(field_type: Any) -> Any:
    """Type conversion function (pure Python fallback)."""
    return _type_converter.convert_type(field_type)


# Simple email regex for validation
_EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")


def validate_email_fast(email: str) -> bool:
    """Email validation (pure Python fallback)."""
    if not email or len(email) < 5:
        return False
    return _EMAIL_REGEX.match(email) is not None


def validate_username_length_fast(username: str, min_len: int = 3, max_len: int = 50) -> bool:
    """Username length validation (pure Python fallback)."""
    length = len(username)
    return min_len <= length <= max_len


# ============================================================================
# Field Inspection Optimization (Pure Python Fallback)
# ============================================================================


def process_struct_fields_fast(
    struct_cls: Any, type_converter_func: Any
) -> dict[str, tuple[Any, Any, dict[str, Any] | None]]:
    """Process msgspec struct fields and convert to Pydantic field definitions.

    Returns:
        Dictionary mapping field names to (python_type, default_value, metadata).
        metadata contains 'description' and 'examples' from msgspec.Meta if present.
    """
    import msgspec

    type_info = msgspec.inspect.type_info(struct_cls)
    field_definitions: dict[str, tuple[Any, Any, dict[str, Any] | None]] = {}

    for field in type_info.fields:  # type: ignore[attr-defined]
        python_type = type_converter_func(field.type)

        if field.default is not msgspec.NODEFAULT:
            default_value = field.default
        elif field.default_factory is not msgspec.NODEFAULT:
            default_value = field.default_factory()
        else:
            default_value = ...

        # Extract metadata from Metadata type (Annotated[T, msgspec.Meta(...)])
        metadata: dict[str, Any] | None = None
        if type(field.type).__name__ == "Metadata":
            extra = getattr(field.type, "extra_json_schema", None)
            if extra:
                metadata = {}
                if "description" in extra:
                    metadata["description"] = extra["description"]
                if "examples" in extra:
                    metadata["examples"] = extra["examples"]

        field_definitions[field.name] = (python_type, default_value, metadata)

    return field_definitions


# ============================================================================
# Pagination Calculations Optimization (Pure Python Fallback)
# ============================================================================


class PaginationCalculator:
    """Pagination metadata calculator (pure Python fallback)."""

    def __init__(self, total_results: int, page_size: int, current_page: int) -> None:
        self.total_results = total_results
        self.page_size = page_size
        self.current_page = current_page

        if page_size > 0:
            self.total_pages = (total_results + page_size - 1) // page_size
        else:
            self.total_pages = 0

        self.has_next = current_page < self.total_pages
        self.has_previous = current_page > 1

    def get_metadata(self) -> dict[str, int | bool]:
        """Get pagination metadata as dictionary."""
        return {
            "current_page": self.current_page,
            "total_pages": self.total_pages,
            "total_results": self.total_results,
            "page_size": self.page_size,
            "has_next": self.has_next,
            "has_previous": self.has_previous,
        }


def calculate_pagination_fast(
    total_results: int, page_size: int, current_page: int
) -> dict[str, int | bool]:
    """Calculate pagination metadata (pure Python fallback)."""
    calc = PaginationCalculator(total_results, page_size, current_page)
    return calc.get_metadata()


# ============================================================================
# Response Model Instantiation Helpers (Pure Python Fallback)
# ============================================================================


def create_response_dict_fast(data: Any, message: str, status: str) -> dict[str, Any]:
    """Create response dictionary (pure Python fallback)."""
    return {
        "data": data,
        "message": message,
        "status": status,
    }


def create_paginated_dict_fast(
    items: list[Any],
    total_results: int,
    current_page: int,
    page_size: int,
    message: str,
    status: str,
) -> dict[str, Any]:
    """Create paginated response dictionary (pure Python fallback)."""
    metadata = calculate_pagination_fast(total_results, page_size, current_page)

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
