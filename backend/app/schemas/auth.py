"""
Authentication schemas for MFA support.
"""

from typing import Optional, List
from pydantic import BaseModel, EmailStr, validator
from datetime import datetime


class UserBase(BaseModel):
    """Base user schema."""
    username: str
    email: EmailStr
    full_name: str
    role: str = "user"
    location_id: Optional[int] = None


class UserCreate(UserBase):
    """Schema for creating a user."""
    password: str
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        return v


class UserUpdate(BaseModel):
    """Schema for updating a user."""
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    role: Optional[str] = None
    location_id: Optional[int] = None
    is_active: Optional[bool] = None


class UserResponse(UserBase):
    """Schema for user responses."""
    id: int
    is_active: bool
    is_superuser: bool
    mfa_enabled: bool
    last_login: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class LoginRequest(BaseModel):
    """Schema for login request."""
    username: str
    password: str
    mfa_code: Optional[str] = None


class LoginResponse(BaseModel):
    """Schema for login response."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse
    mfa_required: bool = False


class MFASetupRequest(BaseModel):
    """Schema for MFA setup request."""
    password: str


class MFASetupResponse(BaseModel):
    """Schema for MFA setup response."""
    qr_code: str
    secret: str
    backup_codes: List[str]


class MFAVerifyRequest(BaseModel):
    """Schema for MFA verification request."""
    code: str


class MFAVerifyResponse(BaseModel):
    """Schema for MFA verification response."""
    success: bool
    message: str


class PasswordChangeRequest(BaseModel):
    """Schema for password change request."""
    current_password: str
    new_password: str
    
    @validator('new_password')
    def validate_new_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        return v


class PasswordResetRequest(BaseModel):
    """Schema for password reset request."""
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Schema for password reset confirmation."""
    token: str
    new_password: str
    
    @validator('new_password')
    def validate_new_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        return v


class SessionInfo(BaseModel):
    """Schema for session information."""
    user_id: int
    username: str
    role: str
    location_id: Optional[int]
    login_time: datetime
    last_activity: datetime
    ip_address: str
    user_agent: str


class TokenRefreshRequest(BaseModel):
    """Schema for token refresh request."""
    refresh_token: str


class TokenRefreshResponse(BaseModel):
    """Schema for token refresh response."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
