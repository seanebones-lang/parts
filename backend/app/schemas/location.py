"""
Location schemas for API requests and responses (Pydantic v2).
"""

from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr


class LocationBase(BaseModel):
    """Base location schema."""

    name: str
    address: str
    city: str
    state: str
    zip_code: str
    phone: str
    email: EmailStr
    manager_name: str
    is_active: bool = True


class LocationCreate(LocationBase):
    """Schema for creating a location."""

    pass


class LocationUpdate(BaseModel):
    """Schema for updating a location."""

    name: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    manager_name: Optional[str] = None
    is_active: Optional[bool] = None


class LocationResponse(LocationBase):
    """Schema for location responses."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: str
    updated_at: str
