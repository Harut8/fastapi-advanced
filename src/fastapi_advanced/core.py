"""High-performance msgspec integration for FastAPI with OpenAPI support."""

from __future__ import annotations

import logging
import threading
from functools import lru_cache
from typing import Any, Generic, TypeVar

import msgspec
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, create_model

from .exceptions import (
    ConfigurationError,
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

# Thread-safe schema registry
_SCHEMA_REGISTRY: dict[type[msgspec.Struct], type[BaseModel]] = {}
_SCHEMA_LOCK = threading.Lock()


@lru_cache(maxsize=256)
def _msgspec_type_to_python_type(field_type: Any) -> Any:
    """
    Convert msgspec type to Python type annotation with caching.

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
        raise TypeConversionError(
            field_type=field_type,
            original_error=e
        ) from e


def msgspec_to_pydantic(struct_cls: type[msgspec.Struct]) -> type[BaseModel]:
    """
    Convert msgspec.Struct to Pydantic BaseModel for OpenAPI generation.

    Thread-safe with caching for performance.

    Args:
        struct_cls: msgspec.Struct class to convert

    Returns:
        Pydantic BaseModel class with same fields

    Raises:
        SchemaGenerationError: If schema generation fails.
        TypeConversionError: If field type conversion fails.

    Example:
        >>> class User(msgspec.Struct):
        ...     name: str
        ...     email: str
        >>> UserSchema = msgspec_to_pydantic(User)
        >>> # Use in FastAPI: response_model=UserSchema
    """
    # Fast path: check cache without lock
    if struct_cls in _SCHEMA_REGISTRY:
        return _SCHEMA_REGISTRY[struct_cls]

    # Acquire lock for thread safety
    with _SCHEMA_LOCK:
        # Double-check after acquiring lock
        if struct_cls in _SCHEMA_REGISTRY:
            return _SCHEMA_REGISTRY[struct_cls]

        try:
            # Process struct fields
            field_definitions = process_struct_fields_fast(
                struct_cls, _msgspec_type_to_python_type
            )

            if not field_definitions:
                logger.warning(f"No fields found in struct {struct_cls.__name__}")

            # Create Pydantic model
            pydantic_model = create_model(
                f"{struct_cls.__name__}Schema", __config__=None, **field_definitions
            )

            # Attach original struct reference
            pydantic_model.__msgspec_struct__ = struct_cls  # type: ignore

            # Cache the result
            _SCHEMA_REGISTRY[struct_cls] = pydantic_model
            logger.debug(f"Successfully generated schema for {struct_cls.__name__}")
            return pydantic_model

        except TypeConversionError:
            # Re-raise type conversion errors with additional context
            raise
        except Exception as e:
            logger.error(f"Failed to generate schema for {struct_cls.__name__}: {e}")
            raise SchemaGenerationError(
                struct_name=struct_cls.__name__,
                original_error=e
            ) from e


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
    return msgspec_to_pydantic(struct_cls)


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
        response_model = ResponseModel(**response_dict)

        return MsgspecJSONResponse(
            content=response_model,
            status_code=status_code,
        )
    except msgspec.EncodeError as e:
        logger.error(f"Failed to encode response data: {e}")
        raise ResponseSerializationError(
            data=data,
            original_error=e
        ) from e
    except Exception as e:
        logger.error(f"Unexpected error creating response: {e}")
        # Fallback to error response
        error_response = ResponseModel(
            status="error",
            data=None,
            message=f"Failed to create response: {str(e)}"
        )
        return MsgspecJSONResponse(
            content=error_response,
            status_code=500
        )


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
        paginated_model = PaginatedResponse(**paginated_dict)

        return MsgspecJSONResponse(
            content=paginated_model,
            status_code=status_code,
        )
    except msgspec.EncodeError as e:
        logger.error(f"Failed to encode paginated response: {e}")
        raise ResponseSerializationError(
            data=items,
            original_error=e
        ) from e
    except Exception as e:
        logger.error(f"Unexpected error creating paginated response: {e}")
        # Fallback to error response
        error_response = ResponseModel(
            status="error",
            data=None,
            message=f"Failed to create paginated response: {str(e)}"
        )
        return MsgspecJSONResponse(
            content=error_response,
            status_code=500
        )


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
    app.router.default_response_class = MsgspecJSONResponse  # type: ignore
    app.add_exception_handler(msgspec.ValidationError, validation_error_handler)  # type: ignore
    app.add_exception_handler(msgspec.DecodeError, decode_error_handler)  # type: ignore
    return app
