"""Fixed Authentication service for Romanian Freight Forwarder system"""
from typing import Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status
import uuid

from app.models.users import User, UserRole
from app.schemas.auth import (
    LoginRequest, RegisterRequest, UserInfo, 
    PasswordChangeRequest, PasswordResetRequest
)
from app.core.security import (
    verify_password, get_password_hash, 
    create_access_token, create_refresh_token,
    verify_token, blacklist_token,
    validate_password, get_settings
)
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


class AuthService:
    """Authentication service handling user authentication and management"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def authenticate_user(self, email: str, password: str) -> Optional[User]:
        """
        Authenticate a user with email and password
        
        Args:
            email: User email address
            password: Plain text password
            
        Returns:
            User object if authentication successful, None otherwise
        """
        try:
            logger.info(f"Attempting to authenticate user: {email}")
            
            # Find user by email - simplified query
            stmt = select(User).where(User.email == email)
            result = await self.db.execute(stmt)
            user = result.scalar_one_or_none()
            
            if not user:
                logger.warning(f"Authentication failed: User not found for email {email}")
                return None
            
            logger.info(f"User found: {user.email}, checking password...")
            
            # Check if user is active
            if not user.is_active:
                logger.warning(f"Authentication failed: Inactive user {email}")
                return None
            
            # Verify password
            logger.info(f"Verifying password for user {email}")
            if not verify_password(password, user.hashed_password):
                logger.warning(f"Authentication failed: Invalid password for {email}")
                return None
            
            logger.info(f"Password verified successfully for {email}")
            
            # Update last login
            user.last_login = datetime.utcnow()
            await self.db.commit()
            
            logger.info(f"User {email} authenticated successfully")
            return user
            
        except Exception as e:
            logger.error(f"Authentication error for {email}: {str(e)}")
            await self.db.rollback()
            return None
    
    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """
        Get user by ID
        
        Args:
            user_id: User ID
            
        Returns:
            User object if found, None otherwise
        """
        try:
            stmt = select(User).where(User.id == user_id)
            result = await self.db.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error fetching user {user_id}: {str(e)}")
            return None
    
    async def get_user_by_email(self, email: str) -> Optional[User]:
        """
        Get user by email
        
        Args:
            email: User email address
            
        Returns:
            User object if found, None otherwise
        """
        try:
            stmt = select(User).where(User.email == email)
            result = await self.db.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error fetching user by email {email}: {str(e)}")
            return None
    
    async def create_user(
        self, 
        email: str, 
        username: str, 
        password: str, 
        full_name: Optional[str] = None,
        role: str = "viewer"
    ) -> User:
        """
        Create a new user
        
        Args:
            email: User email address
            username: Username
            password: Plain text password
            full_name: Full name (optional)
            role: User role as string
            
        Returns:
            Created User object
            
        Raises:
            HTTPException: If user creation fails
        """
        try:
            # Check if email already exists
            stmt = select(User).where(User.email == email)
            result = await self.db.execute(stmt)
            if result.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already registered"
                )
            
            # Check if username already exists
            stmt = select(User).where(User.username == username)
            result = await self.db.execute(stmt)
            if result.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Username already taken"
                )
            
            # Validate password strength
            if not validate_password(password):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Password must be at least 8 characters long and contain uppercase, lowercase, and digit"
                )
            
            # Validate role value
            valid_roles = ["admin", "dispatcher", "accountant", "viewer"]
            if role not in valid_roles:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid role. Must be one of: {', '.join(valid_roles)}"
                )
            
            # Create new user
            hashed_password = get_password_hash(password)
            user = User(
                email=email,
                username=username,
                hashed_password=hashed_password,
                full_name=full_name,
                role=role,
                is_active=True,
                is_verified=False  # Email verification can be implemented later
            )
            
            self.db.add(user)
            await self.db.commit()
            await self.db.refresh(user)
            
            logger.info(f"User created successfully: {email} ({username})")
            return user
            
        except HTTPException:
            await self.db.rollback()
            raise
        except Exception as e:
            await self.db.rollback()
            logger.error(f"User creation error for {email}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create user"
            )
    
    def create_tokens(self, user: User) -> Tuple[str, str, int]:
        """
        Create access and refresh tokens for a user
        
        Args:
            user: User object
            
        Returns:
            Tuple of (access_token, refresh_token, expires_in_seconds)
        """
        try:
            # Use hardcoded values as fallback if settings fail
            try:
                access_token_minutes = settings.access_token_expire_minutes
            except AttributeError:
                access_token_minutes = 15  # Default fallback
                
            access_token_expires = timedelta(minutes=access_token_minutes)
            
            # Create tokens
            access_token = create_access_token(
                subject=str(user.id),
                expires_delta=access_token_expires
            )
            refresh_token = create_refresh_token(subject=str(user.id))
            
            expires_in = access_token_minutes * 60  # Convert to seconds
            
            return access_token, refresh_token, expires_in
            
        except Exception as e:
            logger.error(f"Token creation error: {str(e)}")
            raise
    
    def user_to_info(self, user: User) -> UserInfo:
        """
        Convert User model to UserInfo schema
        
        Args:
            user: User model instance
            
        Returns:
            UserInfo schema instance
        """
        return UserInfo(
            id=user.id,
            email=user.email,
            username=user.username,
            is_active=user.is_active,
            created_at=user.created_at,
            updated_at=user.updated_at
        )
