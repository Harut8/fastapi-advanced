"""
Pydantic-based models for performance comparison benchmarking.
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


class User(BaseModel):
    """User model using Pydantic BaseModel for comparison."""

    id: int
    username: str = Field(..., min_length=3)
    email: EmailStr
    full_name: Optional[str] = None
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.now)

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": 1,
                "username": "johndoe",
                "email": "john@example.com",
                "fullName": "John Doe",
                "isActive": True,
            }
        }
    }

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        """Validate username length."""
        if len(v) < 3:
            raise ValueError("Username must be at least 3 characters")
        return v


class Address(BaseModel):
    """Address model for nested structure benchmarking."""

    street: str
    city: str
    state: str
    zip_code: str = Field(..., alias="zipCode")
    country: str = "USA"

    model_config = {"populate_by_name": True}


class UserWithAddress(BaseModel):
    """User with nested address for complex validation benchmarking."""

    id: int
    username: str = Field(..., min_length=3)
    email: EmailStr
    address: Address
    full_name: Optional[str] = Field(None, alias="fullName")
    is_active: bool = Field(True, alias="isActive")
    created_at: datetime = Field(default_factory=datetime.now, alias="createdAt")

    model_config = {"populate_by_name": True}


class UserCreate(BaseModel):
    """User creation request model."""

    username: str = Field(..., min_length=3)
    email: EmailStr
    full_name: Optional[str] = Field(None, alias="fullName")
    is_active: bool = Field(True, alias="isActive")

    model_config = {"populate_by_name": True}


class UserUpdate(BaseModel):
    """User update request model."""

    username: Optional[str] = Field(None, min_length=3)
    email: Optional[EmailStr] = None
    full_name: Optional[str] = Field(None, alias="fullName")
    is_active: Optional[bool] = Field(None, alias="isActive")

    model_config = {"populate_by_name": True}
