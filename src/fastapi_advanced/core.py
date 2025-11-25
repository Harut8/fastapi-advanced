"""High-performance msgspec integration for FastAPI with OpenAPI support."""

from __future__ import annotations

import threading
from typing import Any, Generic, TypeVar

import msgspec
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, create_model

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
except ImportError:
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


def _msgspec_type_to_python_type(field_type: Any) -> Any:
    """Convert msgspec type to Python type annotation."""
    return _convert_type_impl(field_type)


def msgspec_to_pydantic(struct_cls: type[msgspec.Struct]) -> type[BaseModel]:
    """
    Convert msgspec.Struct to Pydantic BaseModel for OpenAPI generation.

    Thread-safe with caching for performance.

    Args:
        struct_cls: msgspec.Struct class to convert

    Returns:
        Pydantic BaseModel class with same fields

    Example:
        >>> class User(msgspec.Struct):
        ...     name: str
        ...     email: str
        >>> UserSchema = msgspec_to_pydantic(User)
        >>> # Use in FastAPI: response_model=UserSchema
    """
    if struct_cls in _SCHEMA_REGISTRY:
        return _SCHEMA_REGISTRY[struct_cls]

    with _SCHEMA_LOCK:
        if struct_cls in _SCHEMA_REGISTRY:
            return _SCHEMA_REGISTRY[struct_cls]

        field_definitions = process_struct_fields_fast(struct_cls, _msgspec_type_to_python_type)

        pydantic_model = create_model(
            f"{struct_cls.__name__}Schema", __config__=None, **field_definitions
        )

        pydantic_model.__msgspec_struct__ = struct_cls  # type: ignore

        _SCHEMA_REGISTRY[struct_cls] = pydantic_model
        return pydantic_model


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

    Example:
        >>> @app.get("/users/{id}")
        >>> async def get_user(id: int) -> ResponseModelSchema[User]:
        >>>     user = get_user_from_db(id)
        >>>     return response(data=user)
    """
    response_dict = create_response_dict_fast(
        data=data,
        message=message or "",
        status=status,
    )
    return MsgspecJSONResponse(
        content=ResponseModel(**response_dict),
        status_code=status_code,
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
    """Create a paginated response with metadata."""
    paginated_dict = create_paginated_dict_fast(
        items=items,
        total_results=total_results,
        current_page=page,
        page_size=page_size,
        message=message or "",
        status=status,
    )

    return MsgspecJSONResponse(
        content=PaginatedResponse(**paginated_dict),
        status_code=status_code,
    )


# ============================================================================
# Request Body Parsing with msgspec
# ============================================================================

# Cache msgspec decoders for performance (avoid recreating on every request)
_decoder_cache: dict[type[Any], msgspec.json.Decoder[Any]] = {}
_decoder_cache_lock = threading.Lock()


def _get_decoder(struct_type: type[T]) -> msgspec.json.Decoder[T]:
    """Get cached decoder for the given struct type."""
    if struct_type not in _decoder_cache:
        with _decoder_cache_lock:
            # Double-check inside lock
            if struct_type not in _decoder_cache:
                _decoder_cache[struct_type] = msgspec.json.Decoder(struct_type)
    return _decoder_cache[struct_type]


async def parse_body(request: Request, struct_type: type[T]) -> T:
    """
    Parse request body with msgspec (2-5x faster than Pydantic).

    Automatically handles validation errors via setup_msgspec() error handlers.

    Usage:
        user = await parse_body(request, User)
    """
    body = await request.body()
    decoder = _get_decoder(struct_type)
    return decoder.decode(body)


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
