"""
msgspec-based models for performance benchmarking.
"""
from datetime import datetime
from typing import Optional

import msgspec


class User(msgspec.Struct, rename="camel"):
    """User model using msgspec.Struct for fast serialization."""

    id: int
    username: str
    email: str
    full_name: Optional[str] = None
    is_active: bool = True
    created_at: datetime = msgspec.field(default_factory=datetime.now)

    def __post_init__(self) -> None:
        """Validate user data after initialization."""
        if not self.username or len(self.username) < 3:
            raise ValueError("Username must be at least 3 characters")
        if not self.email or "@" not in self.email:
            raise ValueError("Invalid email address")


class Address(msgspec.Struct, rename="camel"):
    """Address model for nested structure benchmarking."""

    street: str
    city: str
    state: str
    zip_code: str
    country: str = "USA"


class UserWithAddress(msgspec.Struct, rename="camel"):
    """User with nested address for complex validation benchmarking."""

    id: int
    username: str
    email: str
    address: Address
    full_name: Optional[str] = None
    is_active: bool = True
    created_at: datetime = msgspec.field(default_factory=datetime.now)


class UserCreate(msgspec.Struct, rename="camel"):
    """User creation request model."""

    username: str
    email: str
    full_name: Optional[str] = None
    is_active: bool = True


class UserUpdate(msgspec.Struct, rename="camel"):
    """User update request model."""

    username: Optional[str] = None
    email: Optional[str] = None
    full_name: Optional[str] = None
    is_active: Optional[bool] = None
