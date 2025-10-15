"""
Authentication service with MFA support.
"""

import secrets
import hashlib
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from passlib.context import CryptContext
from jose import JWTError, jwt
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.config import settings
from app.models.user import User
from app.schemas.auth import (
    UserCreate, UserUpdate, LoginRequest, MFASetupRequest, 
    MFAVerifyRequest, PasswordChangeRequest
)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT settings
SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES

# Security scheme
security = HTTPBearer()


class AuthService:
    """Authentication service with MFA support."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        return pwd_context.verify(plain_password, hashed_password)
    
    def get_password_hash(self, password: str) -> str:
        """Hash a password."""
        return pwd_context.hash(password)
    
    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """Create a JWT access token."""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    
    def create_refresh_token(self, user_id: int) -> str:
        """Create a refresh token."""
        data = {
            "sub": str(user_id),
            "type": "refresh",
            "exp": datetime.utcnow() + timedelta(days=30)
        }
        return jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify and decode a JWT token."""
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            return payload
        except JWTError:
            return None
    
    async def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """Authenticate a user with username and password."""
        query = select(User).where(User.username == username)
        result = await self.db.execute(query)
        user = result.scalar_one_or_none()
        
        if not user:
            return None
        
        if user.is_locked():
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail="Account is locked due to too many failed login attempts"
            )
        
        if not self.verify_password(password, user.hashed_password):
            user.increment_login_attempts()
            await self.db.commit()
            return None
        
        # Reset login attempts on successful login
        user.reset_login_attempts()
        user.last_login = datetime.utcnow()
        await self.db.commit()
        
        return user
    
    async def create_user(self, user_data: UserCreate) -> User:
        """Create a new user."""
        # Check if username or email already exists
        existing_user = await self.get_user_by_username_or_email(
            user_data.username, user_data.email
        )
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username or email already registered"
            )
        
        # Create user
        hashed_password = self.get_password_hash(user_data.password)
        user = User(
            username=user_data.username,
            email=user_data.email,
            full_name=user_data.full_name,
            hashed_password=hashed_password,
            role=user_data.role,
            location_id=user_data.location_id
        )
        
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        
        return user
    
    async def get_user_by_username_or_email(self, username: str, email: str) -> Optional[User]:
        """Get user by username or email."""
        query = select(User).where(
            (User.username == username) | (User.email == email)
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID."""
        query = select(User).where(User.id == user_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def setup_mfa(self, user_id: int, password: str) -> Dict[str, Any]:
        """Setup MFA for a user."""
        user = await self.get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        if not self.verify_password(password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid password"
            )
        
        if user.mfa_enabled:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="MFA is already enabled"
            )
        
        # Generate MFA secret and QR code
        secret = user.generate_mfa_secret()
        qr_code = user.generate_mfa_qr_code(user.username)
        backup_codes = user.generate_backup_codes()
        
        await self.db.commit()
        
        return {
            "qr_code": qr_code,
            "secret": secret,
            "backup_codes": backup_codes
        }
    
    async def verify_mfa_setup(self, user_id: int, code: str) -> bool:
        """Verify MFA setup with a code."""
        user = await self.get_user_by_id(user_id)
        if not user:
            return False
        
        if user.verify_mfa_code(code):
            user.mfa_enabled = True
            await self.db.commit()
            return True
        
        return False
    
    async def verify_mfa_login(self, user_id: int, code: str) -> bool:
        """Verify MFA code during login."""
        user = await self.get_user_by_id(user_id)
        if not user:
            return False
        
        # Try MFA code first
        if user.verify_mfa_code(code):
            return True
        
        # Try backup code
        if user.verify_backup_code(code):
            await self.db.commit()
            return True
        
        return False
    
    async def disable_mfa(self, user_id: int, password: str) -> bool:
        """Disable MFA for a user."""
        user = await self.get_user_by_id(user_id)
        if not user:
            return False
        
        if not self.verify_password(password, user.hashed_password):
            return False
        
        user.mfa_enabled = False
        user.mfa_secret = None
        user.backup_codes = None
        
        await self.db.commit()
        return True
    
    async def change_password(self, user_id: int, current_password: str, new_password: str) -> bool:
        """Change user password."""
        user = await self.get_user_by_id(user_id)
        if not user:
            return False
        
        if not self.verify_password(current_password, user.hashed_password):
            return False
        
        user.hashed_password = self.get_password_hash(new_password)
        await self.db.commit()
        return True
    
    async def generate_password_reset_token(self, email: str) -> Optional[str]:
        """Generate password reset token."""
        user = await self.get_user_by_username_or_email("", email)
        if not user:
            return None
        
        # Create reset token
        reset_data = {
            "sub": str(user.id),
            "type": "password_reset",
            "exp": datetime.utcnow() + timedelta(hours=1)
        }
        
        return jwt.encode(reset_data, SECRET_KEY, algorithm=ALGORITHM)
    
    async def reset_password(self, token: str, new_password: str) -> bool:
        """Reset password using token."""
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            if payload.get("type") != "password_reset":
                return False
            
            user_id = int(payload.get("sub"))
            user = await self.get_user_by_id(user_id)
            if not user:
                return False
            
            user.hashed_password = self.get_password_hash(new_password)
            await self.db.commit()
            return True
            
        except JWTError:
            return False


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Get current authenticated user."""
    auth_service = AuthService(db)
    
    token = credentials.credentials
    payload = auth_service.verify_token(token)
    
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = await auth_service.get_user_by_id(int(user_id))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user


async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Get current active user."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user


async def get_current_superuser(current_user: User = Depends(get_current_active_user)) -> User:
    """Get current superuser."""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user
