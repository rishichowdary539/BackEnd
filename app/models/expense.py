from pydantic import BaseModel, Field
from typing import Optional
from uuid import uuid4
from datetime import datetime


class ExpenseCreate(BaseModel):
    category: str
    amount: float
    description: Optional[str] = ""
    timestamp: Optional[str] = Field(default_factory=lambda: datetime.utcnow().isoformat())


class ExpenseUpdate(BaseModel):
    category: Optional[str]
    amount: Optional[float]
    description: Optional[str]
    timestamp: Optional[str]


class ExpenseInDB(BaseModel):
    user_id: str
    expense_id: str = Field(default_factory=lambda: datetime.utcnow().isoformat())  # ISO timestamp SK
    category: str
    amount: float
    description: Optional[str] = ""
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class ExpensePublic(BaseModel):
    expense_id: str
    category: str
    amount: float
    description: Optional[str] = ""
    timestamp: str
