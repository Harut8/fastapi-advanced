"""
FastAPI + msgspec Example - Production-Ready High-Performance API

Clean Generic Typing Pattern with Perfect IDE/mypy Support

Key Features:
- response() with generic typing via stub files
- msgspec for 2-5x faster serialization
- Pydantic only for OpenAPI documentation
- Perfect IDE autocomplete and mypy --strict passing
- TYPE_CHECKING pattern eliminates type: ignore comments

Run:
    uvicorn example:app --reload

Docs:
    http://localhost:8000/docs
"""

from typing import TYPE_CHECKING

import msgspec
from fastapi import FastAPI

from src.fastapi_advanced import (
    PaginatedResponseSchema,
    ResponseModelSchema,
    as_body,
    msgspec_to_pydantic,
    paginated_response,
    response,
    setup_msgspec,
)

# ============================================================================
# Models - msgspec Structs (2-5x faster than Pydantic)
# ============================================================================


class CreateUserRequest(msgspec.Struct, rename="camel"):  # type: ignore[call-arg, misc]
    """User creation request with automatic camelCase conversion."""

    username: str
    email: str
    full_name: str | None = None


class User(msgspec.Struct, rename="camel"):  # type: ignore[call-arg, misc]
    """User model with automatic camelCase conversion."""

    id: int
    username: str
    email: str
    full_name: str | None = None
    is_active: bool = True


# ============================================================================
# Pydantic Schemas - For OpenAPI Documentation ONLY
# ============================================================================

# Convert msgspec models to Pydantic for type annotations
# TYPE_CHECKING pattern eliminates type: ignore comments in function signatures
if TYPE_CHECKING:
    UserSchema = User
    CreateUserRequestBody = CreateUserRequest
else:
    UserSchema = msgspec_to_pydantic(User)
    CreateUserRequestBody = as_body(CreateUserRequest)

# ============================================================================
# App Setup
# ============================================================================

app = FastAPI(
    title="FastAPI + msgspec v2.0",
    version="2.0.0",
    description="Production-ready high-performance API with msgspec integration",
)

# Setup msgspec integration
setup_msgspec(app)

# In-memory database
users_db: dict[int, User] = {}
next_id = 1


# ============================================================================
# Routes - Clean Generic Typing Pattern
# ============================================================================


@app.get("/")
async def root() -> ResponseModelSchema[dict[str, str]]:
    """Health check endpoint."""
    return response(
        data={"status": "healthy", "version": "2.0.0"},
        message="FastAPI + msgspec v2.0 is running",
    )


@app.post("/users", status_code=201)
async def create_user(
    data: CreateUserRequestBody,
) -> ResponseModelSchema[UserSchema]:
    """
    Create a new user.

    Perfect typing pattern:
    - Return type: ResponseModelSchema[UserSchema] (Pydantic for OpenAPI)
    - Runtime: response() returns msgspec (2-5x faster)
    - IDE: Full autocomplete and type inference
    - mypy: Passes strict checks
    """
    global next_id

    user = User(
        id=next_id,
        username=data.username,
        email=data.email,
        full_name=data.full_name,
        is_active=True,
    )

    users_db[next_id] = user
    next_id += 1

    return response(
        data=user,
        message=f"User '{user.username}' created successfully",
        status_code=201,
    )


@app.get("/users/{user_id}")
async def get_user(user_id: int) -> ResponseModelSchema[UserSchema | None]:
    """Get a user by ID."""
    if user_id not in users_db:
        return response(
            data=None,
            message=f"User {user_id} not found",
            status="error",
            status_code=404,
        )

    return response(
        data=users_db[user_id],
        message="User retrieved successfully",
    )


@app.get("/users")
async def list_users(page: int = 1, page_size: int = 10) -> PaginatedResponseSchema[UserSchema]:
    """
    List users with pagination.

    Uses paginated_response() for automatic metadata calculation.
    """
    all_users = list(users_db.values())
    total_results = len(all_users)

    start = (page - 1) * page_size
    end = start + page_size
    page_items = all_users[start:end]

    return paginated_response(
        items=page_items,
        total_results=total_results,
        page=page,
        page_size=page_size,
        message=f"Retrieved {len(page_items)} users",
    )


@app.delete("/users/{user_id}", response_model=None)
async def delete_user(user_id: int) -> ResponseModelSchema[dict[str, int | str] | None]:
    """Delete a user."""
    if user_id not in users_db:
        return response(
            data=None,
            message=f"User {user_id} not found",
            status="error",
            status_code=404,
        )

    deleted_user = users_db.pop(user_id)

    return response(
        data={"id": deleted_user.id, "username": deleted_user.username},
        message=f"User {user_id} deleted successfully",
    )


@app.put("/users/{user_id}")
async def update_user(
    user_id: int,
    data: CreateUserRequestBody,
) -> ResponseModelSchema[UserSchema | None]:
    """Update a user."""
    if user_id not in users_db:
        return response(
            data=None,
            message=f"User {user_id} not found",
            status="error",
            status_code=404,
        )

    updated_user = User(
        id=user_id,
        username=data.username,
        email=data.email,
        full_name=data.full_name,
        is_active=users_db[user_id].is_active,
    )

    users_db[user_id] = updated_user

    return response(
        data=updated_user,
        message=f"User {user_id} updated successfully",
    )


# ============================================================================
# Startup - Add Sample Data
# ============================================================================


@app.on_event("startup")
async def startup() -> None:
    """Add sample data on startup."""
    global next_id

    sample_users = [
        User(id=1, username="alice", email="alice@example.com", full_name="Alice Smith"),
        User(id=2, username="bob", email="bob@example.com", full_name="Bob Jones"),
        User(id=3, username="charlie", email="charlie@example.com", full_name="Charlie Brown"),
    ]

    for user in sample_users:
        users_db[user.id] = user

    next_id = 4

    print("\n" + "=" * 70)
    print("🚀 FastAPI + msgspec v2.0 - Production-Ready High-Performance API")
    print("=" * 70)
    print("✨ Clean Typing Pattern:")
    print("   • Use response() with generic typing via stub files")
    print("   • ResponseModelSchema[UserSchema] in return annotations")
    print("   • Perfect IDE autocomplete + mypy --strict passing")
    print("   • msgspec for runtime (2-5x faster)")
    print("   • Pydantic only for OpenAPI docs")
    print("")
    print("📊 Performance:")
    print("   • 2-5x faster request parsing (msgspec)")
    print("   • 2-5x faster response serialization (msgspec)")
    print("   • Zero overhead for OpenAPI generation")
    print("")
    print("📖 Documentation:")
    print("   • OpenAPI docs: http://localhost:8000/docs")
    print("   • ReDoc: http://localhost:8000/redoc")
    print("")
    print("🎯 Sample Users Loaded:")
    for user in sample_users:
        print(f"   • {user.username} ({user.email})")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
