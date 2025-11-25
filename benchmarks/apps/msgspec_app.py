"""FastAPI application using msgspec for high-performance serialization.

This benchmark demonstrates the correct usage pattern for fastapi-advanced:
- msgspec.Struct for runtime performance
- TYPE_CHECKING pattern for clean type annotations
- Proper generic typing with ResponseModelSchema
- No unnecessary type: ignore comments
"""

from datetime import datetime
from typing import TYPE_CHECKING

from fastapi import Body, FastAPI

from benchmarks.models.msgspec_models import User, UserCreate, UserUpdate
from fastapi_advanced import (
    _CYTHON_AVAILABLE,
    PaginatedResponseSchema,
    ResponseModelSchema,
    as_body,
    msgspec_to_pydantic,
    paginated_response,
    response,
    setup_msgspec,
)

app = FastAPI(
    title="Msgspec Benchmark API",
    description="FastAPI with msgspec serialization for performance benchmarking",
    version="1.0.0",
)

print(f"Cython optimizations: {'enabled' if _CYTHON_AVAILABLE else 'disabled'}")

setup_msgspec(app)

# Convert msgspec models to Pydantic for type annotations
if TYPE_CHECKING:
    UserSchema = User
    UserCreateBody = UserCreate
    UserUpdateBody = UserUpdate
else:
    UserSchema = msgspec_to_pydantic(User)
    UserCreateBody = as_body(UserCreate)
    UserUpdateBody = as_body(UserUpdate)

# In-memory database
users_db: dict[int, User] = {}
next_user_id = 1


@app.get("/")
async def health_check() -> ResponseModelSchema[dict[str, str]]:
    """Health check endpoint."""
    return response(
        data={"status": "healthy", "timestamp": datetime.now().isoformat()}
    )


@app.post("/users", status_code=201)
async def create_user(
    user_data: UserCreateBody = Body(...)
) -> ResponseModelSchema[UserSchema]:
    """Create a new user with msgspec validation."""
    global next_user_id

    try:
        user = User(
            id=next_user_id,
            username=user_data.username,
            email=user_data.email,
            full_name=user_data.full_name,
            is_active=user_data.is_active,
            created_at=datetime.now(),
        )
        users_db[next_user_id] = user
        next_user_id += 1
        return response(
            data=user,
            message="User created successfully",
            status_code=201,
        )
    except ValueError as e:
        return response(
            data=None,
            message=str(e),
            status="error",
            status_code=400,
        )


@app.get("/users/{user_id}")
async def get_user(user_id: int) -> ResponseModelSchema[UserSchema]:
    """Retrieve a single user by ID."""
    user = users_db.get(user_id)
    if not user:
        return response(
            data=None,
            message="User not found",
            status="error",
            status_code=404,
        )
    return response(data=user)


@app.get("/users")
async def list_users(
    page: int = 1,
    page_size: int = 100
) -> PaginatedResponseSchema[UserSchema]:
    """List users with pagination."""
    all_users = list(users_db.values())
    total_results = len(all_users)

    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    users_page = all_users[start_idx:end_idx]

    return paginated_response(
        items=users_page,
        total_results=total_results,
        page=page,
        page_size=page_size,
    )


@app.put("/users/{user_id}")
async def update_user(
    user_id: int,
    user_data: UserUpdateBody = Body(...)
) -> ResponseModelSchema[UserSchema]:
    """Update an existing user."""
    user = users_db.get(user_id)
    if not user:
        return response(
            data=None,
            message="User not found",
            status="error",
            status_code=404,
        )

    try:
        updated_user = User(
            id=user.id,
            username=user_data.username if user_data.username else user.username,
            email=user_data.email if user_data.email else user.email,
            full_name=(
                user_data.full_name
                if user_data.full_name is not None
                else user.full_name
            ),
            is_active=(
                user_data.is_active
                if user_data.is_active is not None
                else user.is_active
            ),
            created_at=user.created_at,
        )
        users_db[user_id] = updated_user
        return response(data=updated_user, message="User updated successfully")
    except ValueError as e:
        return response(
            data=None,
            message=str(e),
            status="error",
            status_code=400,
        )


@app.delete("/users/{user_id}")
async def delete_user(user_id: int) -> ResponseModelSchema[dict[str, int] | None]:
    """Delete a user by ID."""
    if user_id not in users_db:
        return response(
            data=None,
            message="User not found",
            status="error",
            status_code=404,
        )

    del users_db[user_id]
    return response(data={"id": user_id}, message="User deleted successfully")


@app.post("/users/seed")
async def seed_users(count: int = 100) -> ResponseModelSchema[dict[str, int]]:
    """Seed the database with test users for benchmarking."""
    global next_user_id

    created = 0
    for i in range(count):
        user = User(
            id=next_user_id,
            username=f"user_{next_user_id}",
            email=f"user{next_user_id}@example.com",
            full_name=f"Test User {next_user_id}",
            is_active=True,
            created_at=datetime.now(),
        )
        users_db[next_user_id] = user
        next_user_id += 1
        created += 1

    return response(
        data={"created": created, "total": len(users_db)},
        message=f"Successfully seeded {created} users",
    )


@app.delete("/users/clear")
async def clear_users() -> ResponseModelSchema[dict[str, int]]:
    """Clear all users from the database."""
    global next_user_id
    count = len(users_db)
    users_db.clear()
    next_user_id = 1
    return response(data={"deleted": count}, message="All users cleared")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
