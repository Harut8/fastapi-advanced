"""Custom exceptions for FastAPI Advanced library with detailed error context."""

from __future__ import annotations

from typing import Any


class FastAPIAdvancedError(Exception):
    """Base exception for all FastAPI Advanced errors."""

    def __init__(self, message: str, context: dict[str, Any] | None = None) -> None:
        """
        Initialize the exception with a message and optional context.

        Args:
            message: The error message.
            context: Additional context information for debugging.
        """
        super().__init__(message)
        self.message = message
        self.context = context or {}

    def __str__(self) -> str:
        """Return a formatted error message with context."""
        if self.context:
            context_str = ", ".join(f"{k}={v}" for k, v in self.context.items())
            return f"{self.message} (context: {context_str})"
        return self.message


class TypeConversionError(FastAPIAdvancedError):
    """Raised when type conversion fails."""

    def __init__(
        self,
        field_type: Any,
        field_name: str | None = None,
        original_error: Exception | None = None,
    ) -> None:
        """
        Initialize type conversion error.

        Args:
            field_type: The type that failed to convert.
            field_name: Optional field name where conversion failed.
            original_error: The original exception that caused the failure.
        """
        message = f"Failed to convert type: {field_type}"
        if field_name:
            message = f"Failed to convert type for field '{field_name}': {field_type}"

        context = {"field_type": str(field_type)}
        if field_name:
            context["field_name"] = field_name
        if original_error:
            context["original_error"] = str(original_error)

        super().__init__(message, context)
        self.field_type = field_type
        self.field_name = field_name
        self.original_error = original_error


class SchemaGenerationError(FastAPIAdvancedError):
    """Raised when Pydantic schema generation fails."""

    def __init__(self, struct_name: str, original_error: Exception | None = None) -> None:
        """
        Initialize schema generation error.

        Args:
            struct_name: Name of the msgspec struct that failed.
            original_error: The original exception that caused the failure.
        """
        message = f"Failed to generate Pydantic schema for struct: {struct_name}"
        context = {"struct_name": struct_name}
        if original_error:
            context["original_error"] = str(original_error)
            message += f" - {original_error}"

        super().__init__(message, context)
        self.struct_name = struct_name
        self.original_error = original_error


class PaginationError(FastAPIAdvancedError):
    """Raised when pagination parameters are invalid."""

    def __init__(
        self,
        page: int | None = None,
        page_size: int | None = None,
        total_results: int | None = None,
        message: str | None = None,
    ) -> None:
        """
        Initialize pagination error.

        Args:
            page: The invalid page number.
            page_size: The invalid page size.
            total_results: The total results count.
            message: Custom error message.
        """
        if message is None:
            issues = []
            if page is not None and page < 1:
                issues.append(f"page must be >= 1, got {page}")
            if page_size is not None and page_size < 1:
                issues.append(f"page_size must be >= 1, got {page_size}")
            if total_results is not None and total_results < 0:
                issues.append(f"total_results must be >= 0, got {total_results}")

            if issues:
                message = "Invalid pagination parameters: " + "; ".join(issues)
            else:
                message = "Invalid pagination parameters"

        context = {}
        if page is not None:
            context["page"] = page
        if page_size is not None:
            context["page_size"] = page_size
        if total_results is not None:
            context["total_results"] = total_results

        super().__init__(message, context)
        self.page = page
        self.page_size = page_size
        self.total_results = total_results


class ResponseSerializationError(FastAPIAdvancedError):
    """Raised when response serialization fails."""

    def __init__(self, data: Any, original_error: Exception | None = None) -> None:
        """
        Initialize response serialization error.

        Args:
            data: The data that failed to serialize.
            original_error: The original exception that caused the failure.
        """
        message = f"Failed to serialize response data of type: {type(data).__name__}"
        context = {"data_type": type(data).__name__}

        if original_error:
            context["original_error"] = str(original_error)
            message += f" - {original_error}"

        # Add helpful suggestions
        if hasattr(data, "__dict__"):
            message += ". Consider implementing a msgspec.Struct or using a dictionary."

        super().__init__(message, context)
        self.data = data
        self.original_error = original_error


class ConfigurationError(FastAPIAdvancedError):
    """Raised when there's a configuration issue."""

    def __init__(self, message: str, suggestion: str | None = None) -> None:
        """
        Initialize configuration error.

        Args:
            message: The error message.
            suggestion: Optional suggestion for fixing the issue.
        """
        if suggestion:
            message = f"{message}. Suggestion: {suggestion}"

        super().__init__(message)
        self.suggestion = suggestion
