from fastapi import APIRouter, HTTPException, status
from app.models.user import UserCreate, UserLogin, UserInDB, UserPublic
from app.core.security import get_password_hash, verify_password, create_access_token
from app.db import dynamo
from uuid import uuid4

router = APIRouter()


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

    return UserPublic(**user_db.dict())


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
        return {"access_token": access_token, "token_type": "bearer"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Login failed: {str(e)}")
