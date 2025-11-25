"""FastAPI-Advanced: Fast msgspec integration with OpenAPI support."""

__version__ = "2.0.0"

from .core import (
    # Performance Indicators
    _CYTHON_AVAILABLE,
    # Response Classes
    MsgspecJSONResponse,
    # Response Models (msgspec - runtime)
    PaginatedResponse,
    # Response Schemas (Pydantic - OpenAPI documentation)
    PaginatedResponseSchema,
    ResponseModel,
    ResponseModelSchema,
    # Request Body Helpers
    as_body,
    # Error Handlers
    decode_error_handler,
    # Utilities
    msgspec_to_pydantic,
    # Response Helpers
    paginated_response,
    response,
    # Setup
    setup_msgspec,
    validation_error_handler,
)
from .exceptions import (
    # Specific Exceptions
    ConfigurationError,
    # Base Exception
    FastAPIAdvancedError,
    PaginationError,
    ResponseSerializationError,
    SchemaGenerationError,
    TypeConversionError,
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
    # Request Body Helpers
    "as_body",  # Pydantic-based (for OpenAPI)
    # Setup
    "setup_msgspec",
    # Response Helpers
    "response",  # Typed response function (generic via stub files)
    "paginated_response",  # For paginated responses
    # Utilities
    "msgspec_to_pydantic",
    # Error Handlers
    "validation_error_handler",
    "decode_error_handler",
    # Performance Indicators
    "_CYTHON_AVAILABLE",
    # Exceptions
    "FastAPIAdvancedError",
    "ConfigurationError",
    "PaginationError",
    "ResponseSerializationError",
    "SchemaGenerationError",
    "TypeConversionError",
]
