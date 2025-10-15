"""
User model with MFA support.
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models.base import TimestampMixin
import pyotp
import qrcode
import io
import base64


class User(TimestampMixin):
    """User model with MFA support."""
    
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=False)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    
    # MFA fields
    mfa_enabled = Column(Boolean, default=False)
    mfa_secret = Column(String(32), nullable=True)  # TOTP secret
    backup_codes = Column(Text, nullable=True)  # JSON string of backup codes
    
    # Session management
    last_login = Column(DateTime(timezone=True), nullable=True)
    login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime(timezone=True), nullable=True)
    
    # Location association
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=True)
    location = relationship("Location", back_populates="users")
    
    # User roles/permissions
    role = Column(String(50), default="user")  # user, manager, admin, superuser
    
    def generate_mfa_secret(self) -> str:
        """Generate a new MFA secret."""
        secret = pyotp.random_base32()
        self.mfa_secret = secret
        return secret
    
    def generate_mfa_qr_code(self, username: str) -> str:
        """Generate QR code for MFA setup."""
        if not self.mfa_secret:
            self.generate_mfa_secret()
        
        totp_uri = pyotp.totp.TOTP(self.mfa_secret).provisioning_uri(
            name=username,
            issuer_name="Dealership Parts System"
        )
        
        # Generate QR code
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(totp_uri)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to base64 string
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        img_str = base64.b64encode(buffer.getvalue()).decode()
        
        return f"data:image/png;base64,{img_str}"
    
    def verify_mfa_code(self, code: str) -> bool:
        """Verify MFA code."""
        if not self.mfa_secret:
            return False
        
        totp = pyotp.TOTP(self.mfa_secret)
        return totp.verify(code, valid_window=1)
    
    def generate_backup_codes(self, count: int = 10) -> list:
        """Generate backup codes for MFA."""
        import secrets
        codes = [secrets.token_hex(4).upper() for _ in range(count)]
        self.backup_codes = ",".join(codes)
        return codes
    
    def verify_backup_code(self, code: str) -> bool:
        """Verify backup code and remove it if valid."""
        if not self.backup_codes:
            return False
        
        codes = self.backup_codes.split(",")
        if code.upper() in codes:
            codes.remove(code.upper())
            self.backup_codes = ",".join(codes) if codes else None
            return True
        return False
    
    def is_locked(self) -> bool:
        """Check if account is locked."""
        if self.locked_until and self.locked_until > func.now():
            return True
        return False
    
    def increment_login_attempts(self):
        """Increment failed login attempts."""
        self.login_attempts += 1
        if self.login_attempts >= 5:
            # Lock account for 30 minutes
            from datetime import datetime, timedelta
            self.locked_until = datetime.utcnow() + timedelta(minutes=30)
    
    def reset_login_attempts(self):
        """Reset failed login attempts."""
        self.login_attempts = 0
        self.locked_until = None
