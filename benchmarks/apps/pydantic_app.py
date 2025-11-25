"""
FastAPI application using pure Pydantic for serialization (comparison baseline).

This benchmark app demonstrates the performance of standard Pydantic
serialization without msgspec optimizations.
"""
from datetime import datetime
from typing import Generic, Optional, TypeVar

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from benchmarks.models.pydantic_models import User, UserCreate, UserUpdate

app = FastAPI(
    title="Pydantic Benchmark API",
    description="FastAPI with standard Pydantic serialization for performance comparison",
    version="1.0.0",
)

# Generic type for response model
T = TypeVar("T")


class ResponseModel(BaseModel, Generic[T]):
    """Standard response wrapper for consistent API responses."""

    status: str = "success"
    data: Optional[T] = None
    message: Optional[str] = None


class PaginationMetadata(BaseModel):
    """Pagination metadata."""

    page: int
    page_size: int = None
    total: int
    total_pages: int = None

    class Config:
        populate_by_name = True
        json_schema_extra = {
            "properties": {
                "page_size": {"alias": "pageSize"},
                "total_pages": {"alias": "totalPages"},
            }
        }


class PaginatedResponseModel(BaseModel):
    """Paginated response with metadata."""

    status: str = "success"
    data: list[User]
    pagination: PaginationMetadata
    message: Optional[str] = None


# In-memory database simulation
users_db: dict[int, User] = {}
next_user_id = 1


@app.get("/", response_model=ResponseModel[dict])
async def health_check() -> ResponseModel[dict]:
    """Health check endpoint."""
    return ResponseModel(
        data={"status": "healthy", "timestamp": datetime.now().isoformat()}
    )


@app.post("/users", response_model=ResponseModel[User], status_code=201)
async def create_user(user_data: UserCreate) -> ResponseModel[User]:
    """Create a new user with Pydantic validation."""
    global next_user_id

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

    return ResponseModel(data=user, message="User created successfully")


@app.get("/users/{user_id}", response_model=ResponseModel[User])
async def get_user(user_id: int) -> ResponseModel[User]:
    """Retrieve a single user by ID."""
    user = users_db.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return ResponseModel(data=user)


@app.get("/users", response_model=PaginatedResponseModel)
async def list_users(page: int = 1, page_size: int = 100) -> PaginatedResponseModel:
    """List users with pagination."""
    all_users = list(users_db.values())
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    users_page = all_users[start_idx:end_idx]

    total_pages = (len(all_users) + page_size - 1) // page_size

    return PaginatedResponseModel(
        data=users_page,
        pagination=PaginationMetadata(
            page=page,
            page_size=page_size,
            total=len(all_users),
            total_pages=total_pages,
        ),
    )


@app.put("/users/{user_id}", response_model=ResponseModel[User])
async def update_user(user_id: int, user_data: UserUpdate) -> ResponseModel[User]:
    """Update an existing user."""
    user = users_db.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Update user with new values
    update_data = user_data.model_dump(exclude_unset=True)
    updated_user = user.model_copy(update=update_data)
    users_db[user_id] = updated_user

    return ResponseModel(data=updated_user, message="User updated successfully")


@app.delete("/users/{user_id}", response_model=ResponseModel[dict])
async def delete_user(user_id: int) -> ResponseModel[dict]:
    """Delete a user by ID."""
    if user_id not in users_db:
        raise HTTPException(status_code=404, detail="User not found")

    del users_db[user_id]
    return ResponseModel(data={"id": user_id}, message="User deleted successfully")


@app.post("/users/seed", response_model=ResponseModel[dict])
async def seed_users(count: int = 100) -> ResponseModel[dict]:
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

    return ResponseModel(
        data={"created": created, "total": len(users_db)},
        message=f"Successfully seeded {created} users",
    )


@app.delete("/users/clear", response_model=ResponseModel[dict])
async def clear_users() -> ResponseModel[dict]:
    """Clear all users from the database."""
    global next_user_id
    count = len(users_db)
    users_db.clear()
    next_user_id = 1
    return ResponseModel(data={"deleted": count}, message="All users cleared")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)
