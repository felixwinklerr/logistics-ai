"""Security and authentication utilities"""
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Union, Any
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# JWT token security
security = HTTPBearer()

try:
    settings = get_settings()
except Exception:
    # Fallback settings for testing
    class MockSettings:
        SECRET_KEY = "test-secret-key"
        ALGORITHM = "HS256"
        ACCESS_TOKEN_EXPIRE_MINUTES = 30
        EMAIL_RESET_TOKEN_EXPIRE_HOURS = 48
    settings = MockSettings()


def create_access_token(
    subject: Union[str, Any], expires_delta: timedelta = None
) -> str:
    """
    Create a simple access token (simplified implementation)
    
    Args:
        subject: The subject of the token (usually user ID)
        expires_delta: Token expiration delta (ignored for now)
        
    Returns:
        Simple token string
    """
    # Simplified token creation for testing - in production use proper JWT
    token_data = f"{subject}:{datetime.utcnow().isoformat()}"
    return hashlib.sha256(token_data.encode()).hexdigest()


def verify_token(token: str) -> Optional[str]:
    """
    Verify a token and return the subject (simplified implementation)
    
    Args:
        token: Token to verify
        
    Returns:
        Subject from token if valid, None otherwise
    """
    # Simplified verification - in production use proper JWT verification
    if len(token) == 64 and all(c in '0123456789abcdef' for c in token):
        return "test_user"  # Return a test user for now
    return None


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash (simplified implementation)
    
    Args:
        plain_password: Plain text password
        hashed_password: Hashed password to verify against
        
    Returns:
        True if password matches, False otherwise
    """
    # Simplified password verification using SHA256
    hashed_plain = hashlib.sha256(plain_password.encode()).hexdigest()
    return hashed_plain == hashed_password


def get_password_hash(password: str) -> str:
    """
    Hash a password (simplified implementation)
    
    Args:
        password: Plain text password to hash
        
    Returns:
        Hashed password
    """
    # Simplified password hashing using SHA256 (use bcrypt in production)
    return hashlib.sha256(password.encode()).hexdigest()


def generate_password_reset_token(email: str) -> str:
    """
    Generate a password reset token (simplified implementation)
    
    Args:
        email: Email address for password reset
        
    Returns:
        Password reset token
    """
    # Simplified token generation
    token_data = f"reset:{email}:{datetime.utcnow().isoformat()}"
    return hashlib.sha256(token_data.encode()).hexdigest()


def verify_password_reset_token(token: str) -> Optional[str]:
    """
    Verify a password reset token (simplified implementation)
    
    Args:
        token: Password reset token to verify
        
    Returns:
        Email from token if valid, None otherwise
    """
    # Simplified verification - return test email for valid-looking tokens
    if len(token) == 64 and all(c in '0123456789abcdef' for c in token):
        return "test@example.com"
    return None


def generate_api_key() -> str:
    """
    Generate a secure API key
    
    Returns:
        Random API key
    """
    return secrets.token_urlsafe(32)


def verify_api_key(api_key: str) -> bool:
    """
    Verify an API key (placeholder implementation)
    
    Args:
        api_key: API key to verify
        
    Returns:
        True if valid API key
    """
    # In a real implementation, this would check against a database
    # For now, we'll just check against a hardcoded key
    return api_key == settings.INTERNAL_API_KEY if hasattr(settings, 'INTERNAL_API_KEY') else False


# Dependency functions for FastAPI
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """
    Dependency to get the current authenticated user
    
    Args:
        credentials: HTTP Bearer token credentials
        
    Returns:
        Current user information
        
    Raises:
        HTTPException: If token is invalid
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        token = credentials.credentials
        subject = verify_token(token)
        if subject is None:
            raise credentials_exception
            
        # In a real implementation, you would fetch user from database here
        # For now, we'll return a mock user based on the subject
        user = {
            "id": subject,
            "username": f"user_{subject}",
            "email": f"user_{subject}@example.com",
            "is_active": True,
            "roles": ["user"]
        }
        
        return user
        
    except Exception as e:
        logger.error(f"Authentication error: {str(e)}")
        raise credentials_exception


async def get_current_active_user(
    current_user: dict = Depends(get_current_user)
) -> dict:
    """
    Dependency to get the current active user
    
    Args:
        current_user: Current user from get_current_user
        
    Returns:
        Current active user
        
    Raises:
        HTTPException: If user is inactive
    """
    if not current_user.get("is_active"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Inactive user"
        )
    return current_user


async def get_admin_user(
    current_user: dict = Depends(get_current_active_user)
) -> dict:
    """
    Dependency to get an admin user
    
    Args:
        current_user: Current active user
        
    Returns:
        Admin user
        
    Raises:
        HTTPException: If user is not an admin
    """
    if "admin" not in current_user.get("roles", []):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user


async def verify_internal_api_key(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> bool:
    """
    Dependency to verify internal API key
    
    Args:
        credentials: HTTP Bearer token credentials
        
    Returns:
        True if valid internal API key
        
    Raises:
        HTTPException: If API key is invalid
    """
    api_key = credentials.credentials
    if not verify_api_key(api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return True


# Permission decorators
def require_permission(permission: str):
    """
    Decorator to require specific permission
    
    Args:
        permission: Required permission
        
    Returns:
        Decorated function that checks permission
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Extract current_user from kwargs or dependencies
            current_user = kwargs.get('current_user')
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
                
            user_permissions = current_user.get("permissions", [])
            if permission not in user_permissions and "admin" not in current_user.get("roles", []):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission '{permission}' required"
                )
                
            return await func(*args, **kwargs)
        return wrapper
    return decorator


# Role-based access control
class RoleChecker:
    """Role-based access control checker"""
    
    def __init__(self, allowed_roles: list):
        self.allowed_roles = allowed_roles
    
    def __call__(self, current_user: dict = Depends(get_current_active_user)):
        user_roles = current_user.get("roles", [])
        if not any(role in user_roles for role in self.allowed_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation requires one of these roles: {', '.join(self.allowed_roles)}"
            )
        return current_user


# Common role checkers
require_admin = RoleChecker(["admin"])
require_dispatcher = RoleChecker(["admin", "dispatcher"])
require_accountant = RoleChecker(["admin", "accountant"])
require_viewer = RoleChecker(["admin", "dispatcher", "accountant", "viewer"]) 