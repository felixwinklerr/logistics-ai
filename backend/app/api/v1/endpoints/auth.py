"""Authentication endpoints for Romanian Freight Forwarder API"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user_id, security, blacklist_token
from app.services.auth_service import AuthService
from app.schemas.auth import (
    LoginRequest, LoginResponse, RegisterRequest, RegisterResponse,
    RefreshTokenRequest, RefreshTokenResponse, LogoutRequest, LogoutResponse,
    PasswordChangeRequest, SuccessResponse, UserInfo, ErrorResponse
)
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/login",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
    summary="User Login",
    description="Authenticate user with email and password, returns JWT tokens",
    responses={
        401: {"model": ErrorResponse, "description": "Invalid credentials"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    }
)
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db)
) -> LoginResponse:
    """
    Authenticate user and return JWT tokens
    
    - **email**: User email address
    - **password**: User password
    
    Returns JWT access and refresh tokens along with user information
    """
    try:
        auth_service = AuthService(db)
        
        # Authenticate user
        logger.info(f"Login attempt for: {request.email}")
        user = await auth_service.authenticate_user(request.email, request.password)
        if not user:
            logger.warning(f"Authentication failed for: {request.email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
            logger.info(f"User authenticated successfully: {request.email}")
        
        # Create tokens
        try:
            access_token, refresh_token, expires_in = auth_service.create_tokens(user)
            logger.info(f"Tokens created successfully for: {request.email}")
        except Exception as e:
            logger.error(f"Token creation failed for {request.email}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create authentication tokens"
            )
        
# Fix for lines 72-76 in auth.py
        # Convert user to schema
        try:
            user_info = auth_service.user_to_info(user)
            logger.info(f"User info conversion successful for: {request.email}")
        except Exception as e:
            logger.error(f"User info conversion failed for {request.email}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to process user information"
            )
        logger.info(f"Successful login for user: {user.email}")
        
        return LoginResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=expires_in,
            user=user_info
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected login error for {request.email}: {str(e)}")
        logger.error(f"Error type: {type(e).__name__}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Authentication failed: {str(e)}"
        )


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="User Registration",
    description="Register a new user account",
    responses={
        400: {"model": ErrorResponse, "description": "Email already registered or validation error"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    }
)
async def register(
    request: RegisterRequest,
    db: AsyncSession = Depends(get_db)
) -> RegisterResponse:
    """
    Register a new user account
    
    - **email**: User email address (must be unique)
    - **username**: Username (must be unique)
    - **password**: Password (minimum 8 characters with uppercase, lowercase, and digit)
    - **full_name**: Full name (optional)
    - **role**: User role (default: viewer)
    
    Returns user information and JWT tokens for immediate login
    """
    try:
        auth_service = AuthService(db)
        
        # Create user
        user = await auth_service.create_user(
            email=request.email,
            username=request.username,
            password=request.password,
            full_name=request.full_name,
            role=request.role
        )
        
        # Create tokens for immediate login
        access_token, refresh_token, expires_in = auth_service.create_tokens(user)
        
        # Convert user to schema
        user_info = auth_service.user_to_info(user)
        
        logger.info(f"New user registered: {user.email}")
        
        return RegisterResponse(
            message="User registered successfully",
            user=user_info,
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=expires_in
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )


@router.post(
    "/refresh",
    response_model=RefreshTokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Refresh Access Token",
    description="Get a new access token using refresh token",
    responses={
        401: {"model": ErrorResponse, "description": "Invalid refresh token"},
    }
)
async def refresh_token(
    request: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db)
) -> RefreshTokenResponse:
    """
    Get a new access token using refresh token
    
    - **refresh_token**: Valid refresh token
    
    Returns new access token
    """
    try:
        auth_service = AuthService(db)
        
        # Create new access token
        access_token, expires_in = await auth_service.refresh_access_token(
            request.refresh_token
        )
        
        return RefreshTokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=expires_in
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed"
        )


@router.post(
    "/logout",
    response_model=LogoutResponse,
    status_code=status.HTTP_200_OK,
    summary="User Logout",
    description="Logout user and invalidate tokens",
)
async def logout(
    request: LogoutRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> LogoutResponse:
    """
    Logout user and invalidate tokens
    
    - **refresh_token**: Refresh token to invalidate (optional)
    
    Blacklists the current access token and optionally the refresh token
    """
    try:
        auth_service = AuthService(db)
        
        # Get access token from Authorization header
        access_token = credentials.credentials
        
        # Logout user (blacklist tokens)
        await auth_service.logout_user(access_token, request.refresh_token)
        
        return LogoutResponse(message="Logged out successfully")
        
    except Exception as e:
        logger.error(f"Logout error: {str(e)}")
        # Return success even on error to prevent information leakage
        return LogoutResponse(message="Logged out successfully")


@router.get(
    "/me",
    response_model=UserInfo,
    status_code=status.HTTP_200_OK,
    summary="Get Current User",
    description="Get current authenticated user information",
    responses={
        401: {"model": ErrorResponse, "description": "Invalid or expired token"},
        404: {"model": ErrorResponse, "description": "User not found"},
    }
)
async def get_current_user_info(
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
) -> UserInfo:
    """
    Get current authenticated user information
    
    Requires valid JWT access token in Authorization header
    Returns user profile information
    """
    try:
        auth_service = AuthService(db)
        
        # Get user by ID
        user = await auth_service.get_user_by_id(current_user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Convert user to schema
        user_info = auth_service.user_to_info(user)
        
        return user_info
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get current user error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user information"
        )


@router.post(
    "/change-password",
    response_model=SuccessResponse,
    status_code=status.HTTP_200_OK,
    summary="Change Password",
    description="Change user password",
    responses={
        400: {"model": ErrorResponse, "description": "Invalid current password or weak new password"},
        401: {"model": ErrorResponse, "description": "Invalid or expired token"},
        404: {"model": ErrorResponse, "description": "User not found"},
    }
)
async def change_password(
    request: PasswordChangeRequest,
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
) -> SuccessResponse:
    """
    Change user password
    
    - **current_password**: Current password for verification
    - **new_password**: New password (minimum 8 characters with uppercase, lowercase, and digit)
    
    Requires valid JWT access token in Authorization header
    """
    try:
        auth_service = AuthService(db)
        
        # Change password
        await auth_service.change_password(
            user_id=current_user_id,
            current_password=request.current_password,
            new_password=request.new_password
        )
        
        return SuccessResponse(message="Password changed successfully")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password change error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to change password"
        )


# Health check endpoint for authentication service
@router.get(
    "/health",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="Authentication Service Health Check",
    description="Check authentication service health"
)
async def auth_health_check() -> dict:
    """
    Health check for authentication service
    
    Returns service status and timestamp
    """
    from datetime import datetime
    return {
        "service": "authentication",
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }


@router.post(
    "/test-db",
    summary="Test Database Connection for Auth",
    description="Test database connectivity for authentication"
)
async def test_auth_db(
    db: AsyncSession = Depends(get_db)
) -> dict:
    """Test database connection for authentication"""
    try:
        from sqlalchemy import text
        
        # Test basic query
        result = await db.execute(text("SELECT COUNT(*) FROM users"))
        count = result.scalar()
        
        # Test user query
        result = await db.execute(text("SELECT id, email, username FROM users WHERE email = 'dispatcher@romanianfreight.com'"))
        user_row = result.fetchone()
        
        return {
            "db_connection": "working",
            "users_count": count,
            "test_user": {
                "found": user_row is not None,
                "id": str(user_row[0]) if user_row else None,
                "email": user_row[1] if user_row else None,
                "username": user_row[2] if user_row else None
            } if user_row else None
        }
        
    except Exception as e:
        return {
            "db_connection": "failed",
            "error": str(e)
        }


@router.post(
    "/debug-login",
    summary="Debug Login Process",
    description="Debug the login authentication step by step"
)
async def debug_login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db)
) -> dict:
    """Debug login process step by step"""
    try:
        from sqlalchemy import select
        from app.models.users import User
        from app.core.security import verify_password
        
        debug_info = {
            "step_1_request": {
                "email": request.email,
                "password_length": len(request.password)
            }
        }
        
        # Step 1: Find user
        stmt = select(User).where(User.email == request.email)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        
        debug_info["step_2_user_lookup"] = {
            "user_found": user is not None,
            "user_id": str(user.id) if user else None,
            "user_active": user.is_active if user else None,
            "user_verified": user.is_verified if user else None,
            "user_role": user.role.value if user else None
        }
        
        if not user:
            debug_info["result"] = "user_not_found"
            return debug_info
            
        # Step 2: Check if active
        if not user.is_active:
            debug_info["result"] = "user_inactive"
            return debug_info
            
        # Step 3: Verify password
        password_match = verify_password(request.password, user.hashed_password)
        debug_info["step_3_password_check"] = {
            "password_match": password_match,
            "stored_hash_length": len(user.hashed_password),
            "stored_hash_prefix": user.hashed_password[:10] + "..."
        }
        
        if password_match:
            debug_info["result"] = "authentication_successful"
        else:
            debug_info["result"] = "password_mismatch"
            
        return debug_info
        
    except Exception as e:
        return {
            "result": "error",
            "error": str(e),
            "error_type": type(e).__name__
        }


@router.post(
    "/debug-register",
    summary="Debug Registration Process",
    description="Debug the user registration step by step"
)
async def debug_register(
    request: RegisterRequest,
    db: AsyncSession = Depends(get_db)
) -> dict:
    """Debug registration process step by step"""
    try:
        debug_info = {
            "step_1_request": {
                "email": request.email,
                "username": request.username,
                "password_length": len(request.password),
                "role": request.role.value if hasattr(request.role, 'value') else str(request.role)
            }
        }
        
        # Step 1: Check email exists
        from sqlalchemy import select
        from app.models.users import User
        from app.core.security import validate_password, get_password_hash
        
        stmt = select(User).where(User.email == request.email)
        result = await db.execute(stmt)
        existing_email_user = result.scalar_one_or_none()
        
        debug_info["step_2_email_check"] = {
            "email_exists": existing_email_user is not None
        }
        
        if existing_email_user:
            debug_info["result"] = "email_already_exists"
            return debug_info
        
        # Step 2: Check username exists  
        stmt = select(User).where(User.username == request.username)
        result = await db.execute(stmt)
        existing_username_user = result.scalar_one_or_none()
        
        debug_info["step_3_username_check"] = {
            "username_exists": existing_username_user is not None
        }
        
        if existing_username_user:
            debug_info["result"] = "username_already_exists"
            return debug_info
        
        # Step 3: Validate password
        password_valid = validate_password(request.password)
        debug_info["step_4_password_validation"] = {
            "password_valid": password_valid
        }
        
        if not password_valid:
            debug_info["result"] = "password_validation_failed"
            return debug_info
        
        # Step 4: Hash password
        try:
            hashed_password = get_password_hash(request.password)
            debug_info["step_5_password_hash"] = {
                "hash_created": True,
                "hash_length": len(hashed_password)
            }
        except Exception as e:
            debug_info["step_5_password_hash"] = {
                "hash_created": False,
                "error": str(e)
            }
            debug_info["result"] = "password_hash_failed"
            return debug_info
        
        # Step 5: Create user object
        try:
            user = User(
                email=request.email,
                username=request.username,
                hashed_password=hashed_password,
                full_name=request.full_name,
                role=request.role,
                is_active=True,
                is_verified=False
            )
            
            debug_info["step_6_user_creation"] = {
                "user_object_created": True,
                "user_email": user.email,
                "user_role": user.role.value if hasattr(user.role, 'value') else str(user.role)
            }
            
            # Step 6: Save to database
            db.add(user)
            await db.commit()
            await db.refresh(user)
            
            debug_info["step_7_database_save"] = {
                "saved_successfully": True,
                "user_id": str(user.id)
            }
            
            debug_info["result"] = "registration_successful"
            
        except Exception as e:
            await db.rollback()
            debug_info["step_6_user_creation"] = {
                "user_object_created": False,
                "error": str(e),
                "error_type": type(e).__name__
            }
            debug_info["result"] = "user_creation_failed"
            
        return debug_info
        
    except Exception as e:
        return {
            "result": "error",
            "error": str(e),
            "error_type": type(e).__name__
        }
