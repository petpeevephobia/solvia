"""
Authentication routes for Solvia.
"""
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.auth.models import (
    UserCreate, UserLogin, UserResponse, TokenResponse, 
    PasswordReset, PasswordResetConfirm, EmailVerification
)
from app.auth.utils import (
    get_password_hash, verify_password, create_access_token,
    generate_verification_token, generate_reset_token,
    is_strong_password, send_verification_email
)
from app.database import db
from app.config import settings
import uuid
router = APIRouter(prefix="/auth", tags=["authentication"])
security = HTTPBearer()


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """Get current user from JWT token."""
    from app.auth.utils import verify_token
    
    token = credentials.credentials
    email = verify_token(token)
    if email is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return email


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user: UserCreate):
    """Register a new user."""
    # Validate password strength
    if not is_strong_password(user.password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long and contain uppercase, lowercase, and digit"
        )
    
    # Check if user already exists
    existing_user = db.get_user_by_email(user.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists"
        )
    
    # Hash password and create user
    password_hash = get_password_hash(user.password)
    verification_token = generate_verification_token()
    
    success = db.create_user(user, password_hash, verification_token)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user"
        )

    # Send verification email
    send_verification_email(user.email, verification_token)

    # Generate a user ID (since we don't store it in the current DB structure)
    user_id = str(uuid.uuid4())
    
    return UserResponse(
        id=user_id,
        email=user.email,
        message="User registered successfully. Please check your email to verify your account.",
        created_at=datetime.utcnow().isoformat()
    )


@router.post("/login", response_model=TokenResponse)
async def login(user_credentials: UserLogin):
    """Login user and return access token."""
    # Get user from database
    user = db.get_user_by_email(user_credentials.email)
    print(f"[DEBUG] User from DB: {user}")
    print(f"[DEBUG] Password to check: {user_credentials.password}")
    if user:
        print(f"[DEBUG] Stored hash: {user.password_hash}")
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Verify password
    is_valid = verify_password(user_credentials.password, user.password_hash)
    print(f"[DEBUG] Password valid: {is_valid}")
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Check if email is verified
    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Please verify your email before logging in"
        )
    
    # Update last login
    db.update_last_login(user.email)
    
    # Create access token
    access_token_expires = timedelta(minutes=30)  # 30 minutes
    access_token = create_access_token(data={"sub": user.email}, expires_delta=access_token_expires)
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=access_token_expires.total_seconds()
    )


@router.post("/verify-email")
async def verify_email(verification: EmailVerification):
    """Verify user email with token."""
    # Find user with this verification token
    # Note: This is a simplified implementation
    # In production, you'd want to store tokens with expiration
    
    # For now, we'll need to search through users
    # This is not efficient for production - consider using a separate tokens sheet
    
    # TODO: Implement proper token verification
    # For now, return a placeholder response
    return {"message": "Email verification endpoint - implementation needed"}


@router.post("/forgot-password")
async def forgot_password(reset_request: PasswordReset):
    """Send password reset email."""
    user = db.get_user_by_email(reset_request.email)
    if not user:
        # Don't reveal if email exists or not
        return {"message": "If the email exists, a reset link has been sent"}
    
    # Generate reset token
    reset_token = generate_reset_token()
    success = db.set_reset_token(user.email, reset_token)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process reset request"
        )
    
    # TODO: Send reset email
    return {
        "message": "If the email exists, a reset link has been sent",
        "reset_token": reset_token  # Remove this in production
    }


@router.post("/reset-password")
async def reset_password(reset_confirm: PasswordResetConfirm):
    """Reset password with token."""
    # Validate password strength
    if not is_strong_password(reset_confirm.new_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long and contain uppercase, lowercase, and digit"
        )
    
    # TODO: Implement proper token validation
    # For now, return a placeholder response
    return {"message": "Password reset endpoint - implementation needed"}


@router.post("/logout")
async def logout(current_user: str = Depends(get_current_user)):
    """Logout user (invalidate token)."""
    # In a JWT-based system, logout is typically handled client-side
    # by removing the token. For additional security, you could maintain
    # a blacklist of invalidated tokens.
    
    return {"message": "Successfully logged out"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: str = Depends(get_current_user)):
    """Get current user profile."""
    user = db.get_user_by_email(current_user)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Generate a user ID (since we don't store it in the current DB structure)
    user_id = str(uuid.uuid4())
    
    return UserResponse(
        id=user_id,
        email=user.email,
        is_verified=user.is_verified,
        created_at=user.created_at if user.created_at else None
    )


@router.get("/verify-email")
async def verify_email(token: str, request: Request):
    """Verify user email with token from the verification link."""
    # Find user with this verification token
    user = None
    # Search all users for the token
    all_rows = db.users_sheet.get_all_records()
    row_num = None
    for idx, row in enumerate(all_rows, start=2):  # start=2 to account for header row
        if row.get('verification_token') == token:
            user = row
            row_num = idx
            break
    if not user:
        return {"success": False, "message": "Invalid or expired verification token."}
    # Mark as verified and clear token
    db.users_sheet.update_cell(row_num, 5, "TRUE")  # is_verified
    db.users_sheet.update_cell(row_num, 6, "")      # verification_token
    # Optionally, redirect to a success page or show a message
    return {"success": True, "message": "Your account has been verified! You can now log in."} 