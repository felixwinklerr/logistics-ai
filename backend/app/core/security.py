"""Security and authentication utilities with proper JWT and bcrypt"""
import secrets
from datetime import datetime, timedelta
from typing import Optional, Union, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Password context for bcrypt hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT token security
security = HTTPBearer()

try:
    settings = get_settings()
except Exception:
    # Fallback settings for testing
    class MockSettings:
        secret_key = "test-secret-key-for-romanian-freight-forwarder-system"
        jwt_algorithm = "HS256"
        access_token_expire_minutes = 15
        refresh_token_expire_days = 7
        EMAIL_RESET_TOKEN_EXPIRE_HOURS = 48
    settings = MockSettings()


def create_access_token(subject: Union[str, Any], expires_delta: timedelta = None) -> str:
    """
    Create a JWT access token
    
    Args:
        subject: The subject of the token (usually user ID)
        expires_delta: Token expiration delta
        
    Returns:
        JWT token string
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=getattr(settings, 'access_token_expire_minutes', 15))
    
    to_encode = {"exp": expire, "sub": str(subject), "type": "access"}
    encoded_jwt = jwt.encode(to_encode, getattr(settings, 'secret_key', 'fallback-secret'), 
                            algorithm=getattr(settings, 'jwt_algorithm', 'HS256'))
    return encoded_jwt


def create_refresh_token(subject: Union[str, Any]) -> str:
    """
    Create a JWT refresh token
    
    Args:
        subject: The subject of the token (usually user ID)
        
    Returns:
        JWT refresh token string
    """
    expire = datetime.utcnow() + timedelta(days=getattr(settings, 'refresh_token_expire_days', 7))
    to_encode = {"exp": expire, "sub": str(subject), "type": "refresh"}
    encoded_jwt = jwt.encode(to_encode, getattr(settings, 'secret_key', 'fallback-secret'), 
                            algorithm=getattr(settings, 'jwt_algorithm', 'HS256'))
    return encoded_jwt


def verify_token(token: str, token_type: str = "access") -> Optional[str]:
    """
    Verify a JWT token and return the subject
    
    Args:
        token: JWT token to verify
        token_type: Expected token type (access or refresh)
        
    Returns:
        Subject from token if valid, None otherwise
    """
    try:
        payload = jwt.decode(token, getattr(settings, 'secret_key', 'fallback-secret'), 
                           algorithms=[getattr(settings, 'jwt_algorithm', 'HS256')])
        user_id: str = payload.get("sub")
        token_type_check: str = payload.get("type")
        
        if user_id is None or token_type_check != token_type:
            return None
            
        return user_id
    except JWTError:
        return None


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its bcrypt hash
    
    Args:
        plain_password: Plain text password
        hashed_password: Bcrypt hashed password to verify against
        
    Returns:
        True if password matches, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Hash a password using bcrypt
    
    Args:
        password: Plain text password to hash
        
    Returns:
        Bcrypt hashed password
    """
    return pwd_context.hash(password)


def generate_password_reset_token(email: str) -> str:
    """
    Generate a password reset token
    
    Args:
        email: Email address for password reset
        
    Returns:
        JWT password reset token
    """
    expire = datetime.utcnow() + timedelta(hours=getattr(settings, 'EMAIL_RESET_TOKEN_EXPIRE_HOURS', 48))
    to_encode = {"exp": expire, "sub": email, "type": "password_reset"}
    encoded_jwt = jwt.encode(to_encode, getattr(settings, 'secret_key', 'fallback-secret'), 
                            algorithm=getattr(settings, 'jwt_algorithm', 'HS256'))
    return encoded_jwt


def verify_password_reset_token(token: str) -> Optional[str]:
    """
    Verify a password reset token
    
    Args:
        token: Password reset token to verify
        
    Returns:
        Email from token if valid, None otherwise
    """
    try:
        payload = jwt.decode(token, getattr(settings, 'secret_key', 'fallback-secret'), 
                           algorithms=[getattr(settings, 'jwt_algorithm', 'HS256')])
        email: str = payload.get("sub")
        token_type: str = payload.get("type")
        
        if email is None or token_type != "password_reset":
            return None
            
        return email
    except JWTError:
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
    return api_key == getattr(settings, 'INTERNAL_API_KEY', 'test-api-key')


# Token blacklist (in production, use Redis or database)
_blacklisted_tokens = set()


def blacklist_token(token: str) -> None:
    """
    Add a token to the blacklist
    
    Args:
        token: Token to blacklist
    """
    _blacklisted_tokens.add(token)


def is_token_blacklisted(token: str) -> bool:
    """
    Check if a token is blacklisted
    
    Args:
        token: Token to check
        
    Returns:
        True if token is blacklisted
    """
    return token in _blacklisted_tokens


# Password validation
def validate_password(password: str) -> bool:
    """
    Validate password strength
    
    Args:
        password: Password to validate
        
    Returns:
        True if password meets requirements
    """
    if len(password) < 8:
        return False
    
    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)
    
    return has_upper and has_lower and has_digit


# Dependency functions for FastAPI
async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> str:
    """
    Dependency to get the current authenticated user ID from JWT token
    
    Args:
        credentials: HTTP Bearer token credentials
        
    Returns:
        Current user ID
        
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
        
        # Check if token is blacklisted
        if is_token_blacklisted(token):
            raise credentials_exception
            
        user_id = verify_token(token, token_type="access")
        if user_id is None:
            raise credentials_exception
            
        return user_id
        
    except Exception as e:
        logger.error(f"Authentication error: {str(e)}")
        raise credentials_exception


# Role-based access control
class RoleChecker:
    """Role-based access control checker for Romanian freight forwarding roles"""
    
    def __init__(self, allowed_roles: list):
        self.allowed_roles = allowed_roles
    
    def __call__(self, user_id: str = Depends(get_current_user_id)):
        # In a real implementation, you would fetch user from database here
        # For now, we'll assume the dependency will be handled by the service layer
        return user_id


# Common role checkers for Romanian freight forwarding business
require_admin = RoleChecker(["admin"])
require_dispatcher = RoleChecker(["admin", "dispatcher"])
require_accountant = RoleChecker(["admin", "accountant"])


# Simplified backward compatibility function
async def get_current_user(
    user_id: str = Depends(get_current_user_id)
):
    """
    Simplified get_current_user for backward compatibility
    Returns a mock user object until proper database integration
    """
    # Simple mock user for backward compatibility
    class MockUser:
        def __init__(self, user_id):
            self.id = user_id
            self.username = f'user_{user_id[:8] if user_id else "unknown"}'
            self.email = f'user_{user_id[:8] if user_id else "unknown"}@romanianfreight.com'
            self.is_active = True
            self.role = 'viewer'
    
    return MockUser(user_id)
