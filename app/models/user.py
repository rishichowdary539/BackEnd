from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from uuid import uuid4
from datetime import datetime


class UserCreate(BaseModel):
    email: EmailStr
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserInDB(BaseModel):
    user_id: str = Field(default_factory=lambda: str(uuid4()))
    email: EmailStr
    password_hash: str
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    profile_image_url: Optional[str] = None


class UserPublic(BaseModel):
    user_id: str
    email: EmailStr
    created_at: str
    profile_image_url: Optional[str] = None
