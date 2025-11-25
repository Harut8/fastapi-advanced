# fastapi-advanced

High-performance FastAPI integration with msgspec for fast serialization and automatic OpenAPI support through a Pydantic bridge.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Why use this?

FastAPI's default Pydantic serialization can be slow for high-throughput applications. This library integrates [msgspec](https://jcristharif.com/msgspec/) to provide significant performance improvements:

- 2-5x faster request parsing and response serialization
- 10-20x faster object creation compared to Pydantic
- Automatic OpenAPI schema generation through Pydantic bridge
- Works seamlessly with standard FastAPI patterns
- Full msgspec features including generics, unions, and tagged unions
- Minimal code changes required from existing Pydantic implementations

## Performance

Benchmarks demonstrate:
- 5x faster serialization compared to Pydantic
- 2.7x faster type conversion with Cython optimizations
- Sub-millisecond response times for typical payloads

See [PERFORMANCE.md](PERFORMANCE.md) for detailed benchmark results.

## Installation

```bash
pip install fastapi-advanced
```

The package includes pre-compiled wheels for macOS, Linux, and Windows (Python 3.10-3.13).

For development installation:

```bash
git clone https://github.com/your-org/fastapi-advanced.git
cd fastapi-advanced
make install-dev

# Optional: Compile Cython extensions for additional performance
make compile-cython
```

## Quick Start

```python
import msgspec
from fastapi import Body, FastAPI
from fastapi_advanced import (
    ResponseModelSchema,
    as_body,
    msgspec_to_pydantic,
    response,
    setup_msgspec,
)

# Create FastAPI app
app = FastAPI(title="My API", version="2.0.0")

# Setup msgspec integration with one line
setup_msgspec(app)

# Define msgspec models (2-5x faster than Pydantic)
class CreateUserRequest(msgspec.Struct):
    username: str
    email: str
    full_name: str | None = None

class User(msgspec.Struct):
    id: int
    username: str
    email: str
    full_name: str | None = None
    is_active: bool = True

# Convert msgspec to Pydantic for OpenAPI schema
UserSchema = msgspec_to_pydantic(User)

# Create endpoints with automatic OpenAPI generation
@app.post("/users", status_code=201)
async def create_user(
    data: as_body(CreateUserRequest) = Body(...)
) -> ResponseModelSchema[UserSchema]:
    """Create a new user."""
    user = User(
        id=1,
        username=data.username,
        email=data.email,
        full_name=data.full_name,
    )
    return response(
        data=user,
        message="User created successfully",
        status_code=201,
    )

@app.get("/users/{user_id}")
async def get_user(user_id: int) -> ResponseModelSchema[UserSchema]:
    """Get a user by ID."""
    user = User(id=user_id, username="alice", email="alice@example.com")
    return response(
        data=user,
        message="User retrieved successfully",
    )
```

Run the application:

```bash
uvicorn example:app --reload
```

Visit http://localhost:8000/docs for interactive API documentation.

## Core Features

### Request Body Parsing

Use the `as_body()` helper to convert msgspec models to Pydantic for OpenAPI documentation while maintaining msgspec performance:

```python
@app.post("/users")
async def create_user(
    data: as_body(CreateUserRequest) = Body(...)
) -> ResponseModelSchema[UserSchema]:
    # FastAPI validates with Pydantic for compatibility
    # Response is serialized with msgspec for performance
    return response(data=data, message="User created")
```

### Standardized Responses

Use the `response()` helper for consistent API responses:

```python
# Success response
return response(
    data=user,
    message="User created successfully",
    status_code=201,
)

# Error response
return response(
    data=None,
    message="User not found",
    status="error",
    status_code=404,
)
```

### Paginated Responses

Use the `paginated_response()` helper for paginated data with automatic metadata:

```python
from fastapi_advanced import PaginatedResponseSchema, paginated_response

@app.get("/users")
async def list_users(
    page: int = 1,
    page_size: int = 10
) -> PaginatedResponseSchema[UserSchema]:
    """List users with pagination."""
    all_users = get_users_from_database()

    # Calculate pagination
    start = (page - 1) * page_size
    end = start + page_size
    page_items = all_users[start:end]

    # Automatic metadata calculation
    return paginated_response(
        items=page_items,
        total_results=len(all_users),
        page=page,
        page_size=page_size,
        message=f"Retrieved {len(page_items)} users",
    )
```

The response includes automatic metadata:
- `current_page`: Current page number
- `total_pages`: Total number of pages
- `total_results`: Total number of items
- `has_next`: Whether there is a next page
- `has_previous`: Whether there is a previous page

### Custom Validation

Add validation logic using `__post_init__`:

```python
class CreateUserRequest(msgspec.Struct):
    username: str
    email: str
    age: int

    def __post_init__(self):
        if len(self.username) < 3:
            raise ValueError("Username must be at least 3 characters")
        if "@" not in self.email:
            raise ValueError("Invalid email format")
        if self.age < 0:
            raise ValueError("Age must be positive")
```

### Automatic Field Renaming

Use the `rename` parameter for automatic case conversion:

```python
class User(msgspec.Struct, rename="camel"):
    user_id: int  # Serialized as "userId"
    full_name: str  # Serialized as "fullName"
    is_active: bool  # Serialized as "isActive"
```

### Nested Structures

Msgspec handles nested structures efficiently:

```python
class Address(msgspec.Struct):
    street: str
    city: str
    country: str = "USA"

class User(msgspec.Struct):
    id: int
    name: str
    address: Address
```

### Tagged Unions

Support for polymorphic data with tagged unions:

```python
class CreditCard(msgspec.Struct, tag="credit_card"):
    card_number: str
    expiry_date: str

class PayPal(msgspec.Struct, tag="paypal"):
    email: str

PaymentMethod = CreditCard | PayPal

class Order(msgspec.Struct):
    id: int
    amount: float
    payment: PaymentMethod
```

### Generic Types

Full support for generic types:

```python
from typing import Generic, TypeVar

T = TypeVar("T")

class Page(msgspec.Struct, Generic[T]):
    items: list[T]
    total: int
    page: int
```

## Migration from Pydantic

Migration from Pydantic is straightforward with minimal code changes.

Before (Pydantic):

```python
from pydantic import BaseModel, Field

class User(BaseModel):
    id: int
    username: str = Field(..., min_length=3)
    email: str
```

After (msgspec):

```python
import msgspec

class User(msgspec.Struct):
    id: int
    username: str
    email: str

    def __post_init__(self):
        if len(self.username) < 3:
            raise ValueError("Username must be at least 3 characters")
```

Migration steps:
1. Replace `BaseModel` with `msgspec.Struct`
2. Convert `Optional[str]` to `str | None`
3. Move `@field_validator` logic to `__post_init__`
4. Add `setup_msgspec(app)` to your application
5. Use `as_body()` for request body parameters

## Project Structure

```
fastapi-advanced/
├── src/
│   └── fastapi_advanced/
│       ├── __init__.py              # Public API exports
│       ├── core.py                  # Core implementation
│       ├── _speedups.pyx            # Cython optimizations
│       └── _speedups_fallback.py    # Pure Python fallback
├── benchmarks/                      # Performance benchmarks
│   ├── apps/                        # Sample applications
│   ├── models/                      # Test models
│   └── profiling/                   # Profiling scripts
├── tests/                           # Test suite
├── example.py                       # Working example application
└── README.md                        # This file
```

## Running Examples

Run the included example application:

```bash
uvicorn example:app --reload
```

Visit the interactive documentation:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Development

Setup development environment:

```bash
make install-dev
```

Common development tasks:

```bash
make check          # Run linting, formatting, and type checks
make test           # Run test suite
make test-cov       # Run tests with coverage report
make compile-cython # Compile Cython extensions
make benchmark      # Run performance benchmarks
```

## API Reference

### Setup Functions

**`setup_msgspec(app: FastAPI) -> FastAPI`**

Configure FastAPI application with msgspec integration. This function:
- Sets `MsgspecJSONResponse` as the default response class
- Registers error handlers for validation and decode errors
- Returns the configured application

### Response Classes

**`MsgspecJSONResponse`**

Fast JSON response class using msgspec serialization (2-5x faster than standard JSONResponse).

### Response Models

**`ResponseModel[T]` (msgspec.Struct)**

Standard API response structure used at runtime for fast serialization.

Fields:
- `status`: Response status (default: "ok")
- `data`: Response data of type T
- `message`: Optional message

**`PaginatedResponse[T]` (msgspec.Struct)**

Paginated response structure with metadata.

Fields:
- `items`: List of items of type T
- `current_page`: Current page number
- `total_pages`: Total number of pages
- `total_results`: Total number of results
- `page_size`: Page size
- `has_next`: Whether there is a next page
- `has_previous`: Whether there is a previous page
- `status`: Response status (default: "ok")
- `message`: Optional message

### Response Schemas

**`ResponseModelSchema[T]` (Pydantic BaseModel)**

Pydantic schema for OpenAPI documentation. Use as return type annotation for automatic schema generation.

**`PaginatedResponseSchema[T]` (Pydantic BaseModel)**

Pydantic schema for paginated responses in OpenAPI documentation.

### Helper Functions

**`as_body(struct_cls: type[T]) -> Any`**

Convert msgspec.Struct to Pydantic model for request body validation and OpenAPI documentation.

**`msgspec_to_pydantic(struct_cls: type[msgspec.Struct]) -> type[BaseModel]`**

Convert msgspec.Struct to Pydantic BaseModel for OpenAPI schema generation. Thread-safe with automatic caching.

**`response(data=None, message=None, status="ok", status_code=200) -> MsgspecJSONResponse`**

Create a standardized API response with msgspec serialization.

**`paginated_response(items, total_results, page=1, page_size=10, message=None, status="ok", status_code=200) -> MsgspecJSONResponse`**

Create a paginated response with automatic metadata calculation.

### Error Handlers

**`validation_error_handler(request: Request, exc: ValidationError) -> MsgspecJSONResponse`**

Handle msgspec validation errors with consistent error format.

**`decode_error_handler(request: Request, exc: DecodeError) -> MsgspecJSONResponse`**

Handle msgspec JSON decode errors with consistent error format.

## How It Works

### Request Flow

1. Client sends JSON request to endpoint
2. FastAPI validates request body using Pydantic (converted from msgspec via `as_body()`)
3. Validated data is passed to your endpoint function
4. On validation error, returns HTTP 422 with error details

### Response Flow

1. Your endpoint returns data using `response()` or `paginated_response()` helper
2. `MsgspecJSONResponse` serializes data with msgspec encoder
3. JSON bytes are sent to client with appropriate status code

### OpenAPI Generation

1. `setup_msgspec()` configures FastAPI to use msgspec response classes
2. Return type annotations use Pydantic schemas (e.g., `ResponseModelSchema[UserSchema]`)
3. FastAPI generates OpenAPI schemas from Pydantic models
4. `msgspec_to_pydantic()` converts msgspec structs to Pydantic models with thread-safe caching
5. Swagger UI and ReDoc display schemas correctly

### Performance Optimization

The library uses a hybrid approach for optimal performance:
- Request parsing: FastAPI/Pydantic (for compatibility)
- Response serialization: msgspec (2-5x faster)
- OpenAPI generation: Pydantic bridge (zero overhead)
- Type conversion: Optional Cython optimizations

## Performance Tips

### Use Frozen Structs

Immutable structs are faster and more memory efficient:

```python
class User(msgspec.Struct, frozen=True):
    id: int
    name: str
```

### Omit Default Values

Reduce JSON payload size by omitting default values:

```python
class Config(msgspec.Struct, omit_defaults=True):
    enabled: bool = True
    timeout: int = 30
```

### Use Array-Like Encoding

For compact encoding of simple structures:

```python
class Point(msgspec.Struct, array_like=True):
    x: float
    y: float

# Serializes as [1.0, 2.0] instead of {"x": 1.0, "y": 2.0}
```

### Field Renaming

Use rename parameter for automatic case conversion:

```python
class User(msgspec.Struct, rename="camel"):
    user_id: int  # Becomes "userId" in JSON
    full_name: str  # Becomes "fullName" in JSON
```

See [PERFORMANCE.md](PERFORMANCE.md) for detailed optimization strategies and benchmark results.

## FAQ

### Is this compatible with FastAPI dependency injection?

Yes, FastAPI's dependency injection system works normally with this library. Dependencies can return msgspec.Struct instances or Pydantic models.

### Can I mix Pydantic and msgspec models?

Yes, but not in the same endpoint. The library uses msgspec for response serialization and Pydantic for request validation (via `as_body()`). You can have some endpoints using pure Pydantic and others using this library.

### Does it work with FastAPI middleware?

Yes, all standard FastAPI middleware works normally. The msgspec integration is transparent at the route level and does not interfere with middleware.

### What about WebSockets and streaming responses?

WebSockets work normally with this library. For streaming responses, msgspec provides `encode_lines()` for efficient line-by-line JSON encoding.

### Can I use Pydantic's Field for validation?

No, msgspec uses a different validation approach. Use `__post_init__` for custom validation logic or `msgspec.field()` for field-level constraints.

### Does it support async validation?

No, msgspec validation is synchronous. If you need async validation (e.g., database lookups), perform it in your endpoint function after parsing.

### How do error responses work?

The library provides automatic error handlers for validation and decode errors. All errors use the consistent `ResponseModel` format with appropriate HTTP status codes.

## Benchmarks

Run performance benchmarks:

```bash
make benchmark        # Comprehensive performance analysis
make benchmark-cython # Compare Cython vs Python implementations
make test-perf        # Performance regression tests
```

See [PERFORMANCE.md](PERFORMANCE.md) and the [benchmarks/](benchmarks/) directory for detailed results and methodology.

## Build System

The project uses modern Python build tools with optional Cython optimizations:

- **Package Manager**: [UV](https://github.com/astral-sh/uv) (10-100x faster than pip)
- **Build Backend**: setuptools with PEP 517 support
- **Performance**: Cython 3.0+ with automatic fallback to pure Python
- **Platforms**: macOS, Linux, Windows (Python 3.10+)

Cython extensions are optional and provide additional performance improvements. The library automatically falls back to pure Python implementations if Cython is not available.

See [PERFORMANCE.md](PERFORMANCE.md) for compilation details and performance comparisons.

## Contributing

Contributions are welcome and appreciated. To contribute:

1. Fork the repository
2. Create a feature branch
3. Make your changes following the code style guidelines
4. Run `make check` to verify code quality
5. Run `make test` to ensure all tests pass
6. Run `make compile-cython` to test Cython extensions
7. Submit a pull request with a clear description

For detailed development instructions and guidelines, see [CONTRIBUTING.md](CONTRIBUTING.md).

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Credits

This project builds on excellent open source tools:

- Built on top of [FastAPI](https://fastapi.tiangolo.com/) by Sebastián Ramírez
- Powered by [msgspec](https://jcristharif.com/msgspec/) by Jim Crist-Harif
- Inspired by the need for high-performance Python APIs in production environments

## Links

- **Documentation**: [GitHub](https://github.com/your-org/fastapi-advanced)
- **Source Code**: [GitHub](https://github.com/your-org/fastapi-advanced)
- **Issue Tracker**: [GitHub Issues](https://github.com/your-org/fastapi-advanced/issues)
- **PyPI**: [fastapi-advanced](https://pypi.org/project/fastapi-advanced/)
- **msgspec Documentation**: [https://jcristharif.com/msgspec/](https://jcristharif.com/msgspec/)
- **FastAPI Documentation**: [https://fastapi.tiangolo.com/](https://fastapi.tiangolo.com/)

---

Built for high-performance Python APIs in production environments.
