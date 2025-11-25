"""Type stubs for fastapi_advanced package - Perfect IDE and mypy support."""

from typing import Any, Generic, TypeVar, overload

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel

__all__ = [
    # Core classes
    "MsgspecJSONResponse",
    "ResponseModel",
    "PaginatedResponse",
    "ResponseModelSchema",
    "PaginatedResponseSchema",
    # Response functions
    "response",
    "paginated_response",
    # Conversion utilities
    "msgspec_to_pydantic",
    "as_body",
    # Setup
    "setup_msgspec",
]

T = TypeVar("T")
_Co = TypeVar("_Co", covariant=True)

# ============================================================================
# Core Response Models
# ============================================================================

class ResponseModel(Generic[T]):
    """Standard API response with automatic camelCase conversion."""

    status: str
    data: T | None
    message: str | None
    def __init__(
        self, status: str = "ok", data: T | None = None, message: str | None = None
    ) -> None: ...

class PaginatedResponse(Generic[T]):
    """Paginated response with metadata."""

    items: list[T]
    current_page: int
    total_pages: int
    total_results: int
    page_size: int
    has_next: bool
    has_previous: bool
    status: str
    message: str | None
    def __init__(
        self,
        items: list[T],
        current_page: int,
        total_pages: int,
        total_results: int,
        page_size: int,
        has_next: bool,
        has_previous: bool,
        status: str = "ok",
        message: str | None = None,
    ) -> None: ...

# ============================================================================
# Pydantic Response Schemas (for OpenAPI and Type Hints)
# ============================================================================

class ResponseModelSchema(BaseModel, Generic[_Co]):
    """Pydantic schema for OpenAPI docs and type hints."""

    status: str
    data: _Co | None
    message: str | None

class PaginatedResponseSchema(BaseModel, Generic[_Co]):
    """Pydantic schema for paginated responses."""

    items: list[_Co]
    current_page: int
    total_pages: int
    total_results: int
    page_size: int
    has_next: bool
    has_previous: bool
    status: str
    message: str | None

# ============================================================================
# Response Classes
# ============================================================================

class MsgspecJSONResponse(JSONResponse):
    """Fast JSON response using msgspec."""
    def render(self, content: Any) -> bytes: ...

# ============================================================================
# Response Functions with Overloads
# ============================================================================

@overload
def response(
    data: T,
    message: str | None = None,
    status: str = "ok",
    status_code: int = 200,
) -> ResponseModelSchema[T]: ...
@overload
def response(
    data: None = None,
    message: str | None = None,
    status: str = "ok",
    status_code: int = 200,
) -> ResponseModelSchema[None]: ...
def paginated_response(
    items: list[T],
    total_results: int,
    page: int = 1,
    page_size: int = 10,
    message: str | None = None,
    status: str = "ok",
    status_code: int = 200,
) -> PaginatedResponseSchema[T]: ...

# ============================================================================
# Conversion Utilities
# ============================================================================

def msgspec_to_pydantic(struct_cls: type[Any]) -> type[BaseModel]: ...
def as_body(struct_cls: type[Any]) -> type[BaseModel]: ...

# ============================================================================
# Setup
# ============================================================================

def setup_msgspec(app: FastAPI) -> FastAPI: ...
