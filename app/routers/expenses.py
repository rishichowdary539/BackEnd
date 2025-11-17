from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.core.config import settings
from app.core.security import decode_access_token
from app.db import dynamo
from app.models.expense import ExpenseCreate, ExpenseInDB, ExpensePublic, ExpenseUpdate
from finance_analyzer_lib import FinanceAnalyzer

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")
finance_analyzer = FinanceAnalyzer(settings.BUDGET_THRESHOLDS_JSON)


def get_current_user_id(token: str = Depends(oauth2_scheme)) -> str:
    payload = decode_access_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return user_id


@router.post("/", response_model=ExpensePublic, status_code=status.HTTP_201_CREATED)
def create_expense(expense: ExpenseCreate, user_id: str = Depends(get_current_user_id)):
    expense_db = ExpenseInDB(user_id=user_id, **expense.dict())
    success = dynamo.put_expense(expense_db.dict())
    if not success:
        raise HTTPException(status_code=500, detail="Failed to save expense")
    return ExpensePublic(**expense_db.dict())


@router.get("/monthly/{month}")
def list_monthly_expenses(month: str, user_id: str = Depends(get_current_user_id)):
    """
    month must follow YYYY-MM format. Example: 2025-11
    """
    expenses = dynamo.get_expenses_for_user(user_id, month)
    summary = finance_analyzer.summarize(expenses)

    return {
        "expenses": expenses,
        "summary": summary,
    }


@router.put("/{expense_id}", response_model=ExpensePublic)
def update_expense(
    expense_id: str,
    expense_update: ExpenseUpdate,
    user_id: str = Depends(get_current_user_id),
):
    mutable_fields = {
        k: v for k, v in expense_update.dict(exclude_unset=True).items()
    }
    if not mutable_fields:
        raise HTTPException(status_code=400, detail="No fields to update")

    updated = dynamo.update_expense(user_id, expense_id, mutable_fields)
    if not updated:
        raise HTTPException(status_code=404, detail="Expense not found")

    return ExpensePublic(**updated)


@router.delete("/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_expense(expense_id: str, user_id: str = Depends(get_current_user_id)):
    deleted = dynamo.delete_expense(user_id, expense_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Expense not found")
    return None
