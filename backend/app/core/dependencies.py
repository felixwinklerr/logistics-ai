"""Application dependencies for Romanian Freight Forwarder system"""
from typing import Optional
from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import get_current_user_id
from app.models.users import User
from app.core.logging import get_logger

logger = get_logger(__name__)


async def get_current_user(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Dependency to get the current authenticated user from database
    
    Args:
        user_id: Current user ID from JWT token
        db: Database session
        
    Returns:
        User model object
        
    Raises:
        HTTPException: If user not found or inactive
    """
    try:
        # Get user from database
        stmt = select(User).where(User.id == user_id)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            logger.warning(f"User not found for ID: {user_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        if not user.is_active:
            logger.warning(f"Inactive user attempted access: {user_id}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive"
            )
        
        return user
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching current user {user_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user information"
        )


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Dependency to get the current active user
    
    Args:
        current_user: Current user from get_current_user
        
    Returns:
        Current active user
    """
    return current_user


# Role-based dependencies for Romanian freight forwarding business
async def get_admin_user(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """Dependency for admin-only access"""
    if current_user.role.value != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


async def get_dispatcher_user(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """Dependency for dispatcher-level access"""
    if current_user.role.value not in ["admin", "dispatcher"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Dispatcher access required"
        )
    return current_user


async def get_accountant_user(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """Dependency for accountant-level access"""
    if current_user.role.value not in ["admin", "accountant", "dispatcher"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accountant access required"
        )
    return current_user


async def get_viewer_user(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """Dependency for viewer-level access (all authenticated users)"""
    return current_user
