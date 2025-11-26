"""High-performance msgspec integration for FastAPI with OpenAPI support."""

from __future__ import annotations

import logging
import threading
from typing import Any, Generic, TypeVar

import msgspec
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, create_model

from .exceptions import (
    PaginationError,
    ResponseSerializationError,
    SchemaGenerationError,
    TypeConversionError,
)

# Configure logging
logger = logging.getLogger(__name__)

# Try to import Cython-optimized functions, fallback to pure Python
try:
    from fastapi_advanced._speedups import (
        convert_msgspec_type_fast as _convert_type_impl,
    )
    from fastapi_advanced._speedups import (
        create_paginated_dict_fast,
        create_response_dict_fast,
        process_struct_fields_fast,
    )

    _CYTHON_AVAILABLE = True
    logger.info("Using Cython-optimized implementation for maximum performance")
except ImportError as e:
    logger.warning(f"Cython speedups not available, using pure Python fallback: {e}")
    from fastapi_advanced._speedups_fallback import (
        convert_msgspec_type_fast as _convert_type_impl,
    )
    from fastapi_advanced._speedups_fallback import (
        create_paginated_dict_fast,
        create_response_dict_fast,
        process_struct_fields_fast,
    )

    _CYTHON_AVAILABLE = False

T = TypeVar("T")

# ============================================================================
# Core Response Models
# ============================================================================


class ResponseModel(msgspec.Struct, Generic[T], rename="camel"):
    """Standard API response with automatic camelCase conversion."""

    status: str = "ok"
    data: T | None = None
    message: str | None = None


class PaginatedResponse(msgspec.Struct, Generic[T], rename="camel"):
    """Paginated response with metadata."""

    items: list[T]
    current_page: int
    total_pages: int
    total_results: int
    page_size: int
    has_next: bool
    has_previous: bool
    status: str = "ok"
    message: str | None = None


# ============================================================================
# Pydantic Response Schemas (for OpenAPI Documentation)
# ============================================================================


class ResponseModelSchema(BaseModel, Generic[T]):
    """Pydantic schema for OpenAPI docs. Runtime uses msgspec for speed."""

    status: str = "ok"
    data: T | None = None
    message: str | None = None


class PaginatedResponseSchema(BaseModel, Generic[T]):
    """Pydantic schema for OpenAPI docs. Runtime uses msgspec for speed."""

    items: list[T]
    current_page: int
    total_pages: int
    total_results: int
    page_size: int
    has_next: bool
    has_previous: bool
    status: str = "ok"
    message: str | None = None


# ============================================================================
# High-Performance Response Class
# ============================================================================


class MsgspecJSONResponse(JSONResponse):
    """Fast JSON response using msgspec (2-5x faster than standard JSONResponse)."""

    def render(self, content: Any) -> bytes:
        if isinstance(content, msgspec.Struct):
            return msgspec.json.encode(content)

        if hasattr(content, "model_dump"):
            content = content.model_dump()

        return msgspec.json.encode(content)


# ============================================================================
# msgspec → Pydantic Bridge for OpenAPI
# ============================================================================

# Hybrid thread-safety approach:
# - Global registry dict with lock-free reads (atomic in CPython due to GIL)
# - Lock only acquired when adding new items (slow path)
# - Thread-local set for recursion detection (no contention between threads)

_SCHEMA_REGISTRY: dict[type[msgspec.Struct], type[BaseModel]] = {}
_REGISTRY_LOCK = threading.Lock()  # Only used when writing to registry
_THREAD_LOCAL = threading.local()  # Thread-local storage for recursion detection


def _get_processing_set() -> set[type[msgspec.Struct]]:
    """Get the thread-local processing set for recursion detection."""
    if not hasattr(_THREAD_LOCAL, "processing"):
        _THREAD_LOCAL.processing = set()
    return _THREAD_LOCAL.processing


def _msgspec_type_to_python_type(field_type: Any) -> Any:
    """
    Convert msgspec type to Python type annotation with error handling.

    Note: Caching is handled inside the _convert_type_impl function
    since msgspec types are not hashable for @lru_cache.

    Args:
        field_type: msgspec type to convert.

    Returns:
        Python type annotation.

    Raises:
        TypeConversionError: If type conversion fails.
    """
    try:
        return _convert_type_impl(field_type)
    except Exception as e:
        logger.error(f"Type conversion failed for {field_type}: {e}")
        raise TypeConversionError(field_type=field_type, original_error=e) from e


def msgspec_to_pydantic(struct_cls: type[msgspec.Struct]) -> type[BaseModel]:
    """
    Convert msgspec.Struct to Pydantic BaseModel for OpenAPI generation.

    Thread-safe with caching for performance. Supports camelCase field renaming
    when the msgspec.Struct uses rename="camel".

    Args:
        struct_cls: msgspec.Struct class to convert

    Returns:
        Pydantic BaseModel class with same fields

    Raises:
        SchemaGenerationError: If schema generation fails.
        TypeConversionError: If field type conversion fails.

    Example:
        >>> class User(msgspec.Struct, rename="camel"):
        ...     full_name: str
        ...     email: str
        >>> UserSchema = msgspec_to_pydantic(User)
        >>> # OpenAPI will show: {"fullName": "...", "email": "..."}
    """
    # Fast path: lock-free read from cache (atomic in CPython due to GIL)
    cached = _SCHEMA_REGISTRY.get(struct_cls)
    if cached is not None:
        return cached

    # Check for circular reference using thread-local set (no lock needed)
    processing_set = _get_processing_set()
    if struct_cls in processing_set:
        # Return a forward reference string that Pydantic will resolve later
        return f"{struct_cls.__name__}Schema"

    # Mark as "in progress" for recursion detection (thread-local, no lock)
    processing_set.add(struct_cls)

    try:
        # Process struct fields - returns (python_type, default_value, metadata)
        # This may recursively call msgspec_to_pydantic for nested structs
        from pydantic import Field

        raw_field_definitions = process_struct_fields_fast(struct_cls, _msgspec_type_to_python_type)

        if not raw_field_definitions:
            logger.warning(f"No fields found in struct {struct_cls.__name__}")

        # Check if struct uses camelCase renaming
        type_info = msgspec.inspect.type_info(struct_cls)
        uses_camel_case = False

        # Check if any field has a different encode_name (indicates renaming)
        for field in type_info.fields:
            if field.encode_name != field.name:
                uses_camel_case = True
                break

        # Build field_definitions with Field() including metadata and aliases
        field_definitions: dict[str, tuple[Any, Any]] = {}

        for field in type_info.fields:
            python_type, default_value, metadata = raw_field_definitions[field.name]

            # Build Field kwargs from metadata
            field_kwargs: dict[str, Any] = {}

            # Add metadata (description, examples) if present
            if metadata:
                if "description" in metadata:
                    field_kwargs["description"] = metadata["description"]
                if "examples" in metadata:
                    field_kwargs["examples"] = metadata["examples"]

            # Add alias for camelCase if needed
            if uses_camel_case and field.encode_name != field.name:
                field_kwargs["alias"] = field.encode_name

            # Create field definition
            if field_kwargs:
                # Need to use Field() with kwargs
                if default_value is ...:
                    field_definitions[field.name] = (python_type, Field(..., **field_kwargs))
                else:
                    field_definitions[field.name] = (
                        python_type,
                        Field(default=default_value, **field_kwargs),
                    )
            else:
                # No metadata or alias, use simple tuple
                field_definitions[field.name] = (python_type, default_value)

        # Create Config that allows population by field name OR alias
        config_dict = None
        if uses_camel_case:
            config_dict = {
                "populate_by_name": True,  # Allow both snake_case and camelCase
            }

        # Create Pydantic model
        if config_dict:
            from pydantic import ConfigDict

            pydantic_model = create_model(
                f"{struct_cls.__name__}Schema",
                __config__=ConfigDict(**config_dict),
                **field_definitions,
            )
        else:
            pydantic_model = create_model(
                f"{struct_cls.__name__}Schema", __config__=None, **field_definitions
            )

        # Attach original struct reference
        pydantic_model.__msgspec_struct__ = struct_cls  # type: ignore[attr-defined]

        # Slow path: acquire lock only when writing to global registry
        with _REGISTRY_LOCK:
            # Double-check: another thread may have completed while we were processing
            existing = _SCHEMA_REGISTRY.get(struct_cls)
            if existing is not None:
                return existing
            _SCHEMA_REGISTRY[struct_cls] = pydantic_model

        logger.debug(
            f"Successfully generated schema for {struct_cls.__name__} (camelCase: {uses_camel_case})"
        )
        return pydantic_model  # type: ignore[return-value]

    except TypeConversionError:
        # Re-raise type conversion errors with additional context
        raise
    except Exception as e:
        logger.error(f"Failed to generate schema for {struct_cls.__name__}: {e}")
        raise SchemaGenerationError(struct_name=struct_cls.__name__, original_error=e) from e
    finally:
        # Always clean up thread-local processing set
        processing_set.discard(struct_cls)


def as_body(struct_cls: type[T]) -> Any:
    """
    Convert msgspec.Struct to Pydantic for request body validation.

    Provides FastAPI request validation and OpenAPI documentation.

    Usage:
        CreateUserBody = as_body(CreateUser)

        @app.post("/users")
        async def create_user(data: CreateUserBody):
            user = User(name=data.name, email=data.email)
            return response(user)
    """
    return msgspec_to_pydantic(struct_cls)  # type: ignore[arg-type]


# ============================================================================
# Response Helper Functions
# ============================================================================


def response(
    data: Any = None,
    message: str | None = None,
    status: str = "ok",
    status_code: int = 200,
) -> MsgspecJSONResponse:
    """
    Create a standardized API response with msgspec serialization.

    For type-safe usage, this function returns ResponseModelSchema[T]
    at type-check time via the .pyi stub files.

    Args:
        data: The response data (any JSON-serializable object)
        message: Optional message string
        status: Response status (default: "ok")
        status_code: HTTP status code (default: 200)

    Returns:
        MsgspecJSONResponse at runtime, ResponseModelSchema[T] for type checking

    Raises:
        ResponseSerializationError: If the data cannot be serialized.

    Example:
        >>> @app.get("/users/{id}")
        >>> async def get_user(id: int) -> ResponseModelSchema[User]:
        >>>     user = get_user_from_db(id)
        >>>     return response(data=user)
    """
    try:
        response_dict = create_response_dict_fast(
            data=data,
            message=message or "",
            status=status,
        )

        # Create response model
        response_model: ResponseModel[Any] = ResponseModel(**response_dict)

        return MsgspecJSONResponse(
            content=response_model,
            status_code=status_code,
        )
    except msgspec.EncodeError as e:
        logger.error(f"Failed to encode response data: {e}")
        raise ResponseSerializationError(data=data, original_error=e) from e
    except Exception as e:
        logger.error(f"Unexpected error creating response: {e}")
        # Fallback to error response
        error_response: ResponseModel[None] = ResponseModel(
            status="error", data=None, message=f"Failed to create response: {str(e)}"
        )
        return MsgspecJSONResponse(content=error_response, status_code=500)


def paginated_response(
    items: list[Any],
    total_results: int,
    page: int = 1,
    page_size: int = 10,
    message: str | None = None,
    status: str = "ok",
    status_code: int = 200,
) -> MsgspecJSONResponse:
    """
    Create a paginated response with metadata and validation.

    Args:
        items: List of items for the current page.
        total_results: Total number of results across all pages.
        page: Current page number (must be >= 1).
        page_size: Number of items per page (must be >= 1).
        message: Optional message string.
        status: Response status (default: "ok").
        status_code: HTTP status code (default: 200).

    Returns:
        MsgspecJSONResponse with paginated data.

    Raises:
        PaginationError: If pagination parameters are invalid.
        ResponseSerializationError: If the data cannot be serialized.
    """
    # Validate pagination parameters
    if page < 1:
        raise PaginationError(page=page)
    if page_size < 1:
        raise PaginationError(page_size=page_size)
    if total_results < 0:
        raise PaginationError(total_results=total_results)

    # Validate page bounds
    if page_size > 0:
        max_page = max(1, (total_results + page_size - 1) // page_size)
        if page > max_page and total_results > 0:
            logger.warning(
                f"Requested page {page} exceeds max page {max_page} "
                f"(total_results={total_results}, page_size={page_size})"
            )
            # Return empty page instead of error for better UX
            items = []

    try:
        paginated_dict = create_paginated_dict_fast(
            items=items,
            total_results=total_results,
            current_page=page,
            page_size=page_size,
            message=message or "",
            status=status,
        )

        # Create paginated response
        paginated_model: PaginatedResponse[Any] = PaginatedResponse(**paginated_dict)

        return MsgspecJSONResponse(
            content=paginated_model,
            status_code=status_code,
        )
    except msgspec.EncodeError as e:
        logger.error(f"Failed to encode paginated response: {e}")
        raise ResponseSerializationError(data=items, original_error=e) from e
    except Exception as e:
        logger.error(f"Unexpected error creating paginated response: {e}")
        # Fallback to error response
        error_response: ResponseModel[None] = ResponseModel(
            status="error", data=None, message=f"Failed to create paginated response: {str(e)}"
        )
        return MsgspecJSONResponse(content=error_response, status_code=500)


# ============================================================================
# Error Handlers
# ============================================================================


async def validation_error_handler(
    request: Request, exc: msgspec.ValidationError
) -> MsgspecJSONResponse:
    """Handle msgspec validation errors."""
    return MsgspecJSONResponse(
        status_code=422,
        content=ResponseModel(
            status="error",
            data={"detail": [{"loc": ["body"], "msg": str(exc), "type": "validation_error"}]},
            message="Validation error",
        ),
    )


async def decode_error_handler(request: Request, exc: msgspec.DecodeError) -> MsgspecJSONResponse:
    """Handle msgspec JSON decode errors."""
    return MsgspecJSONResponse(
        status_code=400,
        content=ResponseModel(
            status="error",
            data={"detail": f"Invalid JSON: {exc}"},
            message="Invalid JSON format",
        ),
    )


# ============================================================================
# FastAPI Setup
# ============================================================================


def setup_msgspec(app: FastAPI) -> FastAPI:
    """Setup FastAPI app with msgspec integration."""
    app.router.default_response_class = MsgspecJSONResponse  # type: ignore[assignment]
    app.add_exception_handler(msgspec.ValidationError, validation_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(msgspec.DecodeError, decode_error_handler)  # type: ignore[arg-type]
    return app
