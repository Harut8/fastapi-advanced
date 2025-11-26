# fastapi-advanced

High-performance FastAPI integration with msgspec for fast serialization and automatic OpenAPI support.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Overview

FastAPI's default Pydantic serialization can be a bottleneck in high-throughput applications. This library integrates [msgspec](https://jcristharif.com/msgspec/) for fast response serialization while maintaining full OpenAPI compatibility through Pydantic for request validation.

### Key Benefits

- **2-5x faster** response serialization with msgspec
- **10-20x faster** object creation compared to Pydantic
- **Full OpenAPI support** - Pydantic for requests, msgspec for responses
- **Type-safe** with perfect mypy strict compliance
- **Minimal changes** from existing Pydantic implementations
- **Production-ready** with Cython optimizations available

## Installation

```bash
pip install fastapi-advanced
```

Pre-compiled wheels are available for macOS, Linux, and Windows (Python 3.10-3.13).

### Development Installation

```bash
git clone https://github.com/your-org/fastapi-advanced.git
cd fastapi-advanced
make install-dev

# Optional: Enable Cython optimizations
make compile-cython
```

## Quick Start

```python
from typing import TYPE_CHECKING

import msgspec
from fastapi import FastAPI

from fastapi_advanced import (
    PaginatedResponseSchema,
    ResponseModelSchema,
    as_body,
    msgspec_to_pydantic,
    paginated_response,
    response,
    setup_msgspec,
)

app = FastAPI(title="My API", version="1.0.0")
setup_msgspec(app)

# Define models with msgspec for runtime performance
class User(msgspec.Struct):
    id: int
    username: str
    email: str
    is_active: bool = True

# Convert to Pydantic for type annotations (OpenAPI generation)
if TYPE_CHECKING:
    UserSchema = User
else:
    UserSchema = msgspec_to_pydantic(User)

# Create endpoints with proper typing
@app.get("/users/{user_id}")
async def get_user(user_id: int) -> ResponseModelSchema[UserSchema]:
    """Get user by ID with type-safe responses."""
    user = User(id=user_id, username="alice", email="alice@example.com")
    return response(data=user, message="User retrieved successfully")

@app.get("/users")
async def list_users(
    page: int = 1,
    page_size: int = 10
) -> PaginatedResponseSchema[UserSchema]:
    """List users with automatic pagination metadata."""
    users = [User(id=i, username=f"user{i}", email=f"user{i}@example.com") for i in range(50)]

    start = (page - 1) * page_size
    end = start + page_size
    page_items = users[start:end]

    return paginated_response(
        items=page_items,
        total_results=len(users),
        page=page,
        page_size=page_size,
    )
```

Run the application:

```bash
uvicorn example:app --reload
```

## Usage Patterns

### Type-Safe Schema Conversion

Use the `TYPE_CHECKING` pattern to eliminate type warnings while maintaining runtime performance:

```python
from typing import TYPE_CHECKING

import msgspec
from fastapi_advanced import msgspec_to_pydantic

class User(msgspec.Struct):
    id: int
    name: str
    email: str

if TYPE_CHECKING:
    # Type checker sees the msgspec Struct type
    UserSchema = User
else:
    # Runtime uses Pydantic for OpenAPI
    UserSchema = msgspec_to_pydantic(User)

# No type: ignore needed in function signatures
@app.get("/users")
async def get_users() -> ResponseModelSchema[UserSchema]:
    users = User(id=1, name="Alice", email="alice@example.com")
    return response(data=users)
```

### Request Body Validation

Use `as_body()` for request body schemas with OpenAPI documentation:

```python
class CreateUserRequest(msgspec.Struct):
    username: str
    email: str
    full_name: str | None = None

CreateUserRequestBody = as_body(CreateUserRequest)

@app.post("/users", status_code=201)
async def create_user(
    data: CreateUserRequestBody,
) -> ResponseModelSchema[UserSchema]:
    user = User(id=1, username=data.username, email=data.email)
    return response(data=user, status_code=201)
```

### Standard Responses

All responses follow a consistent structure:

```python
# Success response
return response(
    data=user,
    message="Operation successful",
    status_code=200,
)

# Error response
return response(
    data=None,
    message="Resource not found",
    status="error",
    status_code=404,
)
```

Response structure:
```json
{
  "status": "ok",
  "data": {...},
  "message": "Operation successful"
}
```

### Paginated Responses

Automatic pagination metadata calculation:

```python
@app.get("/items")
async def list_items(
    page: int = 1,
    page_size: int = 20
) -> PaginatedResponseSchema[ItemSchema]:
    all_items = get_all_items()

    start = (page - 1) * page_size
    end = start + page_size
    page_items = all_items[start:end]

    return paginated_response(
        items=page_items,
        total_results=len(all_items),
        page=page,
        page_size=page_size,
    )
```

Response includes:
- `items`: List of items for the current page
- `current_page`: Current page number
- `total_pages`: Total number of pages
- `total_results`: Total number of items
- `page_size`: Items per page
- `has_next`: Boolean indicating if next page exists
- `has_previous`: Boolean indicating if previous page exists

### Custom Validation

Add custom validation with `__post_init__`:

```python
class CreateUserRequest(msgspec.Struct):
    username: str
    email: str
    age: int

    def __post_init__(self) -> None:
        if len(self.username) < 3:
            raise ValueError("Username must be at least 3 characters")
        if not "@" in self.email:
            raise ValueError("Invalid email format")
        if self.age < 0 or self.age > 150:
            raise ValueError("Age must be between 0 and 150")
```

### Field Name Conversion

Automatic camelCase conversion for JSON responses:

```python
class User(msgspec.Struct, rename="camel"):
    id: int
    full_name: str
    email_address: str
    is_active: bool

# JSON output:
# {
#   "id": 1,
#   "fullName": "John Doe",
#   "emailAddress": "john@example.com",
#   "isActive": true
# }
```

## Advanced Features

### Enum Support

Enums are fully supported in OpenAPI documentation. When you use Python enums in your msgspec structs, the generated OpenAPI schema will show all valid enum values and validate input accordingly.

```python
from enum import Enum

class UserRole(Enum):
    ADMIN = "admin"
    MODERATOR = "moderator"
    USER = "user"

class User(msgspec.Struct, rename="camel"):
    id: int
    username: str
    role: UserRole

# OpenAPI will show:
# {
#   "role": {
#     "type": "string",
#     "enum": ["admin", "moderator", "user"]
#   }
# }
```

Invalid enum values in requests will return a 422 validation error.

### Field Metadata (Description and Examples)

You can add descriptions and examples to your fields using `msgspec.Meta`. These will appear in the OpenAPI documentation.

```python
from typing import Annotated

class Address(msgspec.Struct, rename="camel", kw_only=True):
    street: Annotated[
        str,
        msgspec.Meta(
            description="Street address including number",
            examples=["123 Main St", "456 Oak Avenue"],
        ),
    ]
    city: Annotated[
        str,
        msgspec.Meta(
            description="City name",
            examples=["New York", "Los Angeles"],
        ),
    ]
    postal_code: Annotated[
        str | None,
        msgspec.Meta(
            description="Postal or ZIP code",
            examples=["10001", "90210"],
        ),
    ] = None
```

The OpenAPI schema will include:

```json
{
  "street": {
    "type": "string",
    "description": "Street address including number",
    "examples": ["123 Main St", "456 Oak Avenue"]
  }
}
```

### DateTime, Date, and UUID Types

The library automatically generates proper OpenAPI format annotations for common Python types. This means your API documentation will show the correct data format expectations.

```python
from datetime import date, datetime
from uuid import UUID

class Event(msgspec.Struct, rename="camel"):
    id: UUID
    name: str
    start_time: datetime
    end_date: date | None = None
```

OpenAPI will show proper format annotations:

```json
{
  "id": {"type": "string", "format": "uuid"},
  "startTime": {"type": "string", "format": "date-time"},
  "endDate": {"type": "string", "format": "date"}
}
```

Supported types and their OpenAPI formats:

| Python Type | OpenAPI Format |
|-------------|----------------|
| `datetime` | `date-time` |
| `date` | `date` |
| `time` | `time` |
| `timedelta` | `duration` |
| `UUID` | `uuid` |
| `bytes` | `binary` |
| `Decimal` | `decimal` |

### Tagged Unions

Support for discriminated unions:

```python
from typing import Literal

class Circle(msgspec.Struct, tag="circle"):
    type: Literal["circle"]
    radius: float

class Rectangle(msgspec.Struct, tag="rectangle"):
    type: Literal["rectangle"]
    width: float
    height: float

Shape = Circle | Rectangle

class Drawing(msgspec.Struct):
    shapes: list[Shape]

# Automatic discrimination based on "type" field
```

### Nested Structs

You can nest msgspec structs within each other. The library handles nested schema generation automatically.

```python
class Address(msgspec.Struct, rename="camel"):
    street: str
    city: str
    country: str

class SocialLinks(msgspec.Struct, rename="camel"):
    twitter: str | None = None
    linkedin: str | None = None

class UserProfile(msgspec.Struct, rename="camel"):
    id: int
    username: str
    address: Address | None = None
    social_links: SocialLinks | None = None
```

All nested structs are converted to their corresponding Pydantic schemas for OpenAPI documentation.

### Thread Safety

The schema conversion is thread-safe. The library uses a reentrant lock to handle concurrent schema generation in multi-threaded environments like production ASGI servers. This means:

- Multiple requests can safely trigger schema conversion simultaneously
- Nested structs are handled correctly without deadlocks
- Circular references between structs are detected and handled with forward references

The schema registry caches converted schemas, so each struct is only converted once regardless of how many threads access it.

### Optional Cython Optimizations

Enable additional performance improvements:

```bash
make compile-cython
```

Provides 2-3x faster type conversion operations. The library automatically falls back to pure Python if Cython extensions are not available.

## Performance

Benchmark results (see `PERFORMANCE.md` for details):

| Operation | Pydantic | fastapi-advanced | Improvement |
|-----------|----------|------------------|-------------|
| Response Serialization | 1.00x | 5.12x | 5.1x faster |
| Object Creation | 1.00x | 12.45x | 12.4x faster |
| Type Conversion | 1.00x | 2.0-3.0x | 2-3x faster (with Cython) |

**Note**: Request validation uses Pydantic (for OpenAPI docs). Response serialization uses msgspec (for performance).

## Type Checking

Full mypy strict compliance:

```bash
make typecheck
```

The library uses stub files (`.pyi`) to provide perfect type inference without runtime overhead.

## Testing

```bash
# Run all tests
make test

# Run with coverage
make test-cov

# Run performance benchmarks
make benchmark
```

## Migration Guide

### From Pure Pydantic

1. Replace Pydantic models with msgspec Structs:
```python
# Before
from pydantic import BaseModel

class User(BaseModel):
    id: int
    name: str

# After
import msgspec

class User(msgspec.Struct):
    id: int
    name: str
```

2. Add schema conversion:
```python
from typing import TYPE_CHECKING
from fastapi_advanced import msgspec_to_pydantic

if TYPE_CHECKING:
    UserSchema = User
else:
    UserSchema = msgspec_to_pydantic(User)
```

3. Update return types:
```python
# Before
@app.get("/users")
async def get_users() -> list[User]:
    return [User(id=1, name="Alice")]

# After
@app.get("/users")
async def get_users() -> ResponseModelSchema[list[UserSchema]]:
    users = [User(id=1, name="Alice")]
    return response(data=users)
```

4. Setup msgspec integration:
```python
from fastapi_advanced import setup_msgspec

app = FastAPI()
setup_msgspec(app)  # One line!
```

## API Reference

### Core Functions

- `setup_msgspec(app: FastAPI) -> FastAPI`: Initialize msgspec integration
- `response(data, message, status, status_code) -> ResponseModelSchema[T]`: Create standard response
- `paginated_response(items, total_results, page, page_size, ...) -> PaginatedResponseSchema[T]`: Create paginated response
- `msgspec_to_pydantic(struct_cls) -> type[BaseModel]`: Convert msgspec Struct to Pydantic model
- `as_body(struct_cls) -> type[BaseModel]`: Convert msgspec Struct for request body

### Response Models

- `ResponseModelSchema[T]`: Type-safe response wrapper (Pydantic for OpenAPI)
- `PaginatedResponseSchema[T]`: Type-safe paginated response wrapper
- `ResponseModel[T]`: Runtime response model (msgspec)
- `PaginatedResponse[T]`: Runtime paginated response model (msgspec)

### Response Classes

- `MsgspecJSONResponse`: FastAPI JSONResponse subclass using msgspec serialization

## Contributing

Contributions are welcome. Please ensure:

1. Code passes all checks: `make check`
2. Tests pass: `make test`
3. Type checking passes: `make typecheck`
4. Code is formatted: `make format`

## License

MIT License - see LICENSE file for details.

## Acknowledgments

Built on top of:
- [FastAPI](https://fastapi.tiangolo.com/) - Modern web framework
- [msgspec](https://jcristharif.com/msgspec/) - Fast serialization library
- [Pydantic](https://pydantic-docs.helpmanual.io/) - Data validation
