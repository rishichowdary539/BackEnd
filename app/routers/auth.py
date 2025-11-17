from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import OAuth2PasswordRequestForm
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
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    # OAuth2PasswordRequestForm uses form fields: username, password
    user = dynamo.get_user_by_email(form_data.username)
    if not user or not verify_password(form_data.password, user["password_hash"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    access_token = create_access_token(data={"sub": user["user_id"]})
    return {"access_token": access_token, "token_type": "bearer"}
