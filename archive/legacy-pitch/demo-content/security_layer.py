"""
Security Layer - Lester's Multi-Location Access Control
JWT authentication and role-based access for 7-10 Chicago locations
"""

import json
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from functools import wraps

# JWT functionality
try:
    import jwt
    JWT_AVAILABLE = True
except ImportError:
    JWT_AVAILABLE = False
    print("⚠️ JWT not available - install with: pip install PyJWT")

# Flask integration
try:
    from flask import request, jsonify
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False
    print("⚠️ Flask not available - JWT will work in standalone mode")

# Security configuration
SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'lester_parts_rag_secret_key_2025')
ALGORITHM = 'HS256'
ACCESS_TOKEN_EXPIRE_MINUTES = 480  # 8 hours for dealership shifts

# Role definitions
ROLES = {
    "tech": {
        "permissions": ["read_parts", "query_inventory"],
        "locations": ["all"],  # Can query all locations
        "description": "Field technician - parts lookup only"
    },
    "manager": {
        "permissions": ["read_parts", "query_inventory", "update_inventory", "view_analytics"],
        "locations": ["all"],
        "description": "Location manager - full access to assigned locations"
    },
    "admin": {
        "permissions": ["read_parts", "query_inventory", "update_inventory", "view_analytics", "manage_users", "system_config"],
        "locations": ["all"],
        "description": "System administrator - full access"
    },
    "location_tech": {
        "permissions": ["read_parts", "query_inventory"],
        "locations": [],  # Assigned per user
        "description": "Location-specific technician"
    }
}

# Chicago locations
CHICAGO_LOCATIONS = [
    "Chicago North",
    "O'Hare Auto", 
    "Logan Square Motors",
    "Wrigley Dealership",
    "South Side Parts",
    "Loop Luxury Autos",
    "West Town Wheels"
]

# Mock user database
MOCK_USERS = {
    "tech_john": {
        "username": "tech_john",
        "password": "parts123",  # In production, use hashed passwords
        "role": "tech",
        "locations": ["all"],
        "full_name": "John Smith",
        "location_assignment": "Chicago North"
    },
    "manager_sarah": {
        "username": "manager_sarah", 
        "password": "manage456",
        "role": "manager",
        "locations": ["Chicago North", "O'Hare Auto"],
        "full_name": "Sarah Johnson",
        "location_assignment": "Chicago North"
    },
    "admin_mike": {
        "username": "admin_mike",
        "password": "admin789",
        "role": "admin", 
        "locations": ["all"],
        "full_name": "Mike Chen",
        "location_assignment": "System"
    },
    "tech_lisa": {
        "username": "tech_lisa",
        "password": "tech321",
        "role": "location_tech",
        "locations": ["O'Hare Auto"],
        "full_name": "Lisa Rodriguez",
        "location_assignment": "O'Hare Auto"
    }
}

class SecurityManager:
    """Security manager for JWT authentication and authorization"""
    
    def __init__(self):
        self.secret_key = SECRET_KEY
        self.algorithm = ALGORITHM
        self.token_expire_minutes = ACCESS_TOKEN_EXPIRE_MINUTES
    
    def create_access_token(self, data: Dict, expires_delta: Optional[timedelta] = None) -> str:
        """Create JWT access token"""
        if not JWT_AVAILABLE:
            return self.create_mock_token(data)
        
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=self.token_expire_minutes)
        
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt
    
    def create_mock_token(self, data: Dict) -> str:
        """Create mock token when JWT not available"""
        mock_token = {
            "sub": data.get("sub", "user"),
            "role": data.get("role", "tech"),
            "locations": data.get("locations", ["all"]),
            "exp": int(time.time()) + (self.token_expire_minutes * 60),
            "iat": int(time.time())
        }
        return json.dumps(mock_token)
    
    def verify_token(self, token: str) -> Optional[Dict]:
        """Verify JWT token and return user data"""
        if not JWT_AVAILABLE:
            return self.verify_mock_token(token)
        
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            username = payload.get("sub")
            if username is None:
                return None
            return payload
        except jwt.PyJWTError:
            return None
    
    def verify_mock_token(self, token: str) -> Optional[Dict]:
        """Verify mock token when JWT not available"""
        try:
            payload = json.loads(token)
            if payload.get("exp", 0) < int(time.time()):
                return None  # Token expired
            return payload
        except (json.JSONDecodeError, KeyError):
            return None
    
    def authenticate_user(self, username: str, password: str) -> Optional[Dict]:
        """Authenticate user and return user data"""
        user = MOCK_USERS.get(username)
        if not user or user["password"] != password:
            return None
        
        return {
            "sub": username,
            "role": user["role"],
            "locations": user["locations"],
            "full_name": user["full_name"],
            "location_assignment": user["location_assignment"]
        }
    
    def check_permission(self, user_data: Dict, required_permission: str) -> bool:
        """Check if user has required permission"""
        user_role = user_data.get("role")
        if not user_role:
            return False
        
        role_permissions = ROLES.get(user_role, {}).get("permissions", [])
        return required_permission in role_permissions
    
    def check_location_access(self, user_data: Dict, requested_location: str) -> bool:
        """Check if user has access to requested location"""
        user_locations = user_data.get("locations", [])
        
        # Admin and managers have access to all locations
        if "all" in user_locations:
            return True
        
        # Check specific location access
        return requested_location in user_locations
    
    def filter_results_by_location(self, results: List[Dict], user_data: Dict) -> List[Dict]:
        """Filter results based on user's location access"""
        user_locations = user_data.get("locations", [])
        
        # Admin and managers see all results
        if "all" in user_locations:
            return results
        
        # Filter results to user's accessible locations
        filtered_results = []
        for result in results:
            result_location = result.get("location", "")
            if result_location in user_locations:
                filtered_results.append(result)
        
        return filtered_results

# Global security manager
security_manager = SecurityManager()

def require_auth(permission: str = "read_parts"):
    """Decorator for requiring authentication and permission"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not FLASK_AVAILABLE:
                # Standalone mode - skip auth
                return f(*args, **kwargs)
            
            # Get token from Authorization header
            auth_header = request.headers.get('Authorization')
            if not auth_header or not auth_header.startswith('Bearer '):
                return jsonify({"error": "Missing or invalid authorization header"}), 401
            
            token = auth_header.split(' ')[1]
            user_data = security_manager.verify_token(token)
            
            if not user_data:
                return jsonify({"error": "Invalid or expired token"}), 401
            
            # Check permission
            if not security_manager.check_permission(user_data, permission):
                return jsonify({"error": f"Insufficient permissions. Required: {permission}"}), 403
            
            # Add user data to request context
            request.user_data = user_data
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def create_flask_security_routes(app):
    """Add security routes to Flask app"""
    if not FLASK_AVAILABLE:
        return
    
    @app.route('/auth/login', methods=['POST'])
    def login():
        """Login endpoint"""
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return jsonify({"error": "Username and password required"}), 400
        
        user_data = security_manager.authenticate_user(username, password)
        if not user_data:
            return jsonify({"error": "Invalid credentials"}), 401
        
        access_token = security_manager.create_access_token(user_data)
        
        return jsonify({
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "username": user_data["sub"],
                "role": user_data["role"],
                "full_name": user_data["full_name"],
                "location_assignment": user_data["location_assignment"]
            }
        })
    
    @app.route('/auth/me', methods=['GET'])
    @require_auth("read_parts")
    def get_current_user():
        """Get current user info"""
        return jsonify({
            "user": request.user_data
        })
    
    @app.route('/auth/roles', methods=['GET'])
    @require_auth("read_parts")
    def get_roles():
        """Get available roles and permissions"""
        return jsonify({
            "roles": ROLES,
            "locations": CHICAGO_LOCATIONS
        })

def demo_security():
    """Demo security functionality"""
    print("🔐 Lester's Security Layer Demo")
    print("=" * 50)
    
    # Test authentication
    print("🔑 Testing authentication...")
    user_data = security_manager.authenticate_user("tech_john", "parts123")
    if user_data:
        print(f"✅ Login successful: {user_data['full_name']} ({user_data['role']})")
        
        # Create token
        token = security_manager.create_access_token(user_data)
        print(f"🎫 Token created: {token[:50]}...")
        
        # Verify token
        verified_data = security_manager.verify_token(token)
        if verified_data:
            print(f"✅ Token verified: {verified_data['sub']}")
            
            # Check permissions
            can_read = security_manager.check_permission(verified_data, "read_parts")
            can_admin = security_manager.check_permission(verified_data, "manage_users")
            
            print(f"📖 Can read parts: {can_read}")
            print(f"⚙️ Can manage users: {can_admin}")
            
            # Check location access
            can_access_ohare = security_manager.check_location_access(verified_data, "O'Hare Auto")
            print(f"🏢 Can access O'Hare: {can_access_ohare}")
        else:
            print("❌ Token verification failed")
    else:
        print("❌ Authentication failed")
    
    print("\n👥 Available users for demo:")
    for username, user in MOCK_USERS.items():
        print(f"  - {username}: {user['full_name']} ({user['role']}) - {user['location_assignment']}")
    
    print(f"\n🏢 Chicago locations: {', '.join(CHICAGO_LOCATIONS)}")
    print(f"🔑 JWT available: {JWT_AVAILABLE}")
    print(f"🌐 Flask available: {FLASK_AVAILABLE}")

if __name__ == "__main__":
    demo_security()
