"""Authentication routes."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import timedelta, datetime
import logging
import bcrypt
from src.core.database import get_async_db
from src.data.models import User
from src.core.config import settings
from jose import jwt

router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])
logger = logging.getLogger(__name__)

def hash_password(password: str) -> str:
    """Hash a password."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(password: str, hashed: str) -> bool:
    """Verify a password."""
    return bcrypt.checkpw(password.encode(), hashed.encode())

def create_access_token(user_id: int, expires_delta: timedelta = None):
    """Create JWT access token."""
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    
    to_encode = {"sub": str(user_id), "exp": expire}
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt


@router.post("/login")
async def login(username: str, password: str, db: AsyncSession = Depends(get_async_db)):
    """User login endpoint.
    
    Args:
        username: Username
        password: Password
        
    Returns:
        Access token and refresh token
    """
    # Find user in database
    stmt = select(User).where(User.username == username)
    result = await db.execute(stmt)
    user = result.scalars().first()
    
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Create tokens
    access_token = create_access_token(user.id)
    
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": settings.access_token_expire_minutes * 60,
    }


@router.post("/register")
async def register(username: str, email: str, password: str, db: AsyncSession = Depends(get_async_db)):
    """User registration endpoint.
    
    Args:
        username: Username
        email: Email address
        password: Password
        
    Returns:
        User data
    """
    # Check if user already exists
    stmt = select(User).where((User.username == username) | (User.email == email))
    result = await db.execute(stmt)
    existing_user = result.scalars().first()
    
    if existing_user:
        raise HTTPException(status_code=400, detail="User already exists")
    
    # Create new user
    hashed_password = hash_password(password)
    user = User(
        username=username,
        email=email,
        hashed_password=hashed_password,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "created_at": user.created_at.isoformat(),
    }


@router.post("/refresh")
async def refresh_token(refresh_token: str):
    """Refresh access token.
    
    Args:
        refresh_token: Refresh token
        
    Returns:
        New access token
    """
    try:
        payload = jwt.decode(refresh_token, settings.secret_key, algorithms=[settings.algorithm])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        new_token = create_access_token(int(user_id))
        return {
            "access_token": new_token,
            "token_type": "bearer",
            "expires_in": settings.access_token_expire_minutes * 60,
        }
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid token")


@router.post("/logout")
async def logout():
    """User logout endpoint - token invalidation handled on client side."""
    return {"message": "Logged out successfully"}


@router.get("/me")
async def get_current_user(authorization: str = None, db: AsyncSession = Depends(get_async_db)):
    """Get current user information.
    
    Returns:
        Current user data
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = authorization.replace("Bearer ", "")
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        stmt = select(User).where(User.id == int(user_id))
        result = await db.execute(stmt)
        user = result.scalars().first()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        return {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "created_at": user.created_at.isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid token")
