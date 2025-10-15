"""
Authentication API endpoints with MFA support.
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.auth_service import AuthService, get_current_active_user, get_current_superuser
from app.schemas.auth import (
    UserCreate, UserUpdate, UserResponse, LoginRequest, LoginResponse,
    MFASetupRequest, MFASetupResponse, MFAVerifyRequest, MFAVerifyResponse,
    PasswordChangeRequest, PasswordResetRequest, PasswordResetConfirm,
    TokenRefreshRequest, TokenRefreshResponse
)
from app.models.user import User

router = APIRouter()


@router.post("/register", response_model=UserResponse)
async def register(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    """Register a new user."""
    auth_service = AuthService(db)
    user = await auth_service.create_user(user_data)
    return user


@router.post("/login", response_model=LoginResponse)
async def login(
    login_data: LoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """Login with username/password and optional MFA."""
    auth_service = AuthService(db)
    
    # Authenticate user
    user = await auth_service.authenticate_user(login_data.username, login_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )
    
    # Check if MFA is required
    if user.mfa_enabled:
        if not login_data.mfa_code:
            raise HTTPException(
                status_code=status.HTTP_202_ACCEPTED,
                detail="MFA code required",
                headers={"X-MFA-Required": "true"}
            )
        
        # Verify MFA code
        if not await auth_service.verify_mfa_login(user.id, login_data.mfa_code):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid MFA code"
            )
    
    # Create access token
    access_token = auth_service.create_access_token(data={"sub": str(user.id)})
    refresh_token = auth_service.create_refresh_token(user.id)
    
    return LoginResponse(
        access_token=access_token,
        expires_in=1800,  # 30 minutes
        user=user,
        mfa_required=user.mfa_enabled
    )


@router.post("/refresh", response_model=TokenRefreshResponse)
async def refresh_token(
    refresh_data: TokenRefreshRequest,
    db: AsyncSession = Depends(get_db)
):
    """Refresh access token."""
    auth_service = AuthService(db)
    
    payload = auth_service.verify_token(refresh_data.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    user_id = int(payload.get("sub"))
    user = await auth_service.get_user_by_id(user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )
    
    # Create new access token
    access_token = auth_service.create_access_token(data={"sub": str(user.id)})
    
    return TokenRefreshResponse(
        access_token=access_token,
        expires_in=1800
    )


@router.post("/setup-mfa", response_model=MFASetupResponse)
async def setup_mfa(
    mfa_data: MFASetupRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Setup MFA for current user."""
    auth_service = AuthService(db)
    
    result = await auth_service.setup_mfa(current_user.id, mfa_data.password)
    
    return MFASetupResponse(
        qr_code=result["qr_code"],
        secret=result["secret"],
        backup_codes=result["backup_codes"]
    )


@router.post("/verify-mfa-setup", response_model=MFAVerifyResponse)
async def verify_mfa_setup(
    verify_data: MFAVerifyRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Verify MFA setup with a code."""
    auth_service = AuthService(db)
    
    success = await auth_service.verify_mfa_setup(current_user.id, verify_data.code)
    
    return MFAVerifyResponse(
        success=success,
        message="MFA enabled successfully" if success else "Invalid MFA code"
    )


@router.post("/disable-mfa", response_model=MFAVerifyResponse)
async def disable_mfa(
    password_data: MFASetupRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Disable MFA for current user."""
    auth_service = AuthService(db)
    
    success = await auth_service.disable_mfa(current_user.id, password_data.password)
    
    return MFAVerifyResponse(
        success=success,
        message="MFA disabled successfully" if success else "Invalid password"
    )


@router.post("/change-password")
async def change_password(
    password_data: PasswordChangeRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Change user password."""
    auth_service = AuthService(db)
    
    success = await auth_service.change_password(
        current_user.id, 
        password_data.current_password, 
        password_data.new_password
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid current password"
        )
    
    return {"message": "Password changed successfully"}


@router.post("/forgot-password")
async def forgot_password(
    reset_data: PasswordResetRequest,
    db: AsyncSession = Depends(get_db)
):
    """Request password reset."""
    auth_service = AuthService(db)
    
    token = await auth_service.generate_password_reset_token(reset_data.email)
    
    if token:
        # In production, send email with reset link
        # For now, just return success
        return {"message": "Password reset email sent"}
    else:
        # Don't reveal if email exists or not
        return {"message": "If the email exists, a password reset email has been sent"}


@router.post("/reset-password")
async def reset_password(
    reset_data: PasswordResetConfirm,
    db: AsyncSession = Depends(get_db)
):
    """Reset password using token."""
    auth_service = AuthService(db)
    
    success = await auth_service.reset_password(reset_data.token, reset_data.new_password)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )
    
    return {"message": "Password reset successfully"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
):
    """Get current user information."""
    return current_user


@router.put("/me", response_model=UserResponse)
async def update_current_user(
    user_data: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Update current user information."""
    # Update user fields
    for field, value in user_data.dict(exclude_unset=True).items():
        setattr(current_user, field, value)
    
    await db.commit()
    await db.refresh(current_user)
    
    return current_user


@router.get("/users", response_model=List[UserResponse])
async def get_users(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    """Get all users (admin only)."""
    auth_service = AuthService(db)
    
    # This would need to be implemented in AuthService
    # For now, return empty list
    return []


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    """Delete a user (admin only)."""
    auth_service = AuthService(db)
    
    user = await auth_service.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )
    
    await db.delete(user)
    await db.commit()
    
    return {"message": "User deleted successfully"}
