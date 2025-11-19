from fastapi import APIRouter, HTTPException, status, Depends, Header
from typing import Optional
from app.models.user import UserCreate, UserLogin, UserInDB, UserPublic
from app.core.security import get_password_hash, verify_password, create_access_token, decode_access_token
from app.db import dynamo
from uuid import uuid4

router = APIRouter()


def get_current_user_id(authorization: Optional[str] = Header(None)) -> str:
    """Extract user_id from JWT token"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token required")
    
    token = authorization.replace("Bearer ", "")
    payload = decode_access_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return user_id


@router.post("/register", response_model=UserPublic)
def register(user: UserCreate):
    # Check if user already exists
    existing = dynamo.get_user_by_email(user.email)
    if existing:
        raise HTTPException(status_code=400, detail="User already exists")

    user_db = UserInDB(
        user_id=str(uuid4()),
        email=user.email,
        password_hash=get_password_hash(user.password)
    )

    success = dynamo.put_user(user_db.dict())
    if not success:
        raise HTTPException(status_code=500, detail="Error saving user")

    # Initialize default budget thresholds for this new user
    dynamo.initialize_default_budget_thresholds(user_db.user_id)
    
    # Initialize default scheduler settings for this new user
    dynamo.initialize_default_scheduler_settings(user_db.user_id)

    return UserPublic(**user_db.dict())


@router.get("/me", response_model=UserPublic)
def get_current_user(user_id: str = Depends(get_current_user_id)):
    """Get current user profile"""
    user = dynamo.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    return UserPublic(
        user_id=user["user_id"],
        email=user["email"],
        created_at=user.get("created_at", ""),
        profile_image_url=user.get("profile_image_url")
    )


@router.post("/login")
def login(login_data: UserLogin):
    # Accept JSON body with email and password
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        logger.info(f"Login attempt for email: {login_data.email}")
        user = dynamo.get_user_by_email(login_data.email)
        
        if not user:
            logger.warning(f"User not found: {login_data.email}")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
        
        if not verify_password(login_data.password, user["password_hash"]):
            logger.warning(f"Invalid password for user: {login_data.email}")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

        access_token = create_access_token(data={"sub": user["user_id"]})
        logger.info(f"Login successful for user: {login_data.email}")
        
        # Return token and user info
        user_public = UserPublic(
            user_id=user["user_id"],
            email=user["email"],
            created_at=user.get("created_at", ""),
            profile_image_url=user.get("profile_image_url")
        )
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": user_public.dict()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Login failed: {str(e)}")
