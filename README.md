# fastapi-advanced

High-performance FastAPI integration with msgspec for fast serialization and automatic OpenAPI support.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Overview

FastAPI's default Pydantic serialization can be a bottleneck in high-throughput applications. This library integrates [msgspec](https://jcristharif.com/msgspec/) to provide significant performance improvements while maintaining full OpenAPI compatibility.

### Key Benefits

- **2-5x faster** request parsing and response serialization
- **10-20x faster** object creation compared to Pydantic
- **Full OpenAPI support** through automatic Pydantic bridge
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
| Serialization | 1.00x | 5.12x | 5.1x faster |
| Deserialization | 1.00x | 3.84x | 3.8x faster |
| Object Creation | 1.00x | 12.45x | 12.4x faster |

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
