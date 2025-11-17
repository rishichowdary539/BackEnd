import uuid
from typing import Dict

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer

from app.core.config import settings
from app.core.security import decode_access_token
from app.db import dynamo
from app.utils import pdf_report
from finance_analyzer_lib import FinanceAnalyzer

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")
finance_analyzer = FinanceAnalyzer(settings.BUDGET_THRESHOLDS_JSON)


def get_current_user_id(token: str = Depends(oauth2_scheme)) -> str:
    payload = decode_access_token(token)
    return payload.get("sub")


@router.get("/monthly/{month}")
def generate_monthly_report(month: str, user_id: str = Depends(get_current_user_id)) -> Dict:
    """
    Generate report for the given month (e.g., '2025-11'), upload to S3, return insights + download link.
    """
    expenses = dynamo.get_expenses_for_user(user_id, month)
    if not expenses:
        raise HTTPException(status_code=404, detail="No expenses found for this month.")

    # Analyze expenses via the reusable finance_analyzer_lib
    summary = finance_analyzer.summarize(expenses)

    # Generate report files & upload to S3
    report_id = f"{user_id}_{month}_{uuid.uuid4().hex[:6]}"
    pdf_url = pdf_report.generate_and_upload_pdf(
        user_id=user_id,
        month=month,
        expenses=expenses,
        total=summary["monthly_total"],
        overspending=summary["overspending_categories"],
        suggested=summary["suggested_budgets"],
        spikes=summary["spending_spikes"],
        report_id=report_id,
    )
    csv_url = pdf_report.generate_and_upload_csv(user_id, month, expenses, report_id)

    return {
        "month": month,
        "total_spent": summary["monthly_total"],
        "overspending_categories": summary["overspending_categories"],
        "suggested_budgets": summary["suggested_budgets"],
        "spending_spikes": summary["spending_spikes"],
        "insights": summary["insights"],
        "pdf_report_url": pdf_url,
        "csv_report_url": csv_url,
    }
