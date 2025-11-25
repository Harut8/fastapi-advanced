"""FastAPI-Advanced: Fast msgspec integration with OpenAPI support."""

__version__ = "2.0.0"

from .core import (
    # Response Classes
    MsgspecJSONResponse,
    # Response Models (msgspec - runtime)
    PaginatedResponse,
    ResponseModel,
    # Response Schemas (Pydantic - OpenAPI documentation)
    PaginatedResponseSchema,
    ResponseModelSchema,
    # Request Body Helper
    as_body,
    # Error Handlers
    decode_error_handler,
    # Utilities
    msgspec_to_pydantic,
    # Response Helpers (recommended)
    paginated_response,
    response,
    # Setup
    setup_msgspec,
    validation_error_handler,
    # Performance Indicators
    _CYTHON_AVAILABLE,
)

__all__ = [
    # Version
    "__version__",
    # Response Models (msgspec - runtime)
    "ResponseModel",
    "PaginatedResponse",
    # Response Schemas (Pydantic - OpenAPI documentation)
    "ResponseModelSchema",
    "PaginatedResponseSchema",
    # Response Classes
    "MsgspecJSONResponse",
    # Request Body
    "as_body",
    # Setup (ONE LINE!)
    "setup_msgspec",
    # Response Helpers (recommended)
    "response",
    "paginated_response",
    # Utilities
    "msgspec_to_pydantic",
    # Error Handlers
    "validation_error_handler",
    "decode_error_handler",
    # Performance Indicators
    "_CYTHON_AVAILABLE",
]
