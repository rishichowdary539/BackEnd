import uuid
from typing import Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Header
from fastapi.security import OAuth2PasswordBearer

from app.core.config import settings
from app.core.security import decode_access_token
from app.db import dynamo
from app.utils import pdf_report
from app.utils.analyzer import FinanceAnalyzer

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")
finance_analyzer = FinanceAnalyzer(settings.BUDGET_THRESHOLDS_JSON)


def get_current_user_id(authorization: Optional[str] = Header(None)) -> str:
    # JWT token authentication
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token required")
    
    token = authorization.replace("Bearer ", "")
    payload = decode_access_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    return user_id


@router.get("/monthly/{month}")
def generate_monthly_report(month: str, user_id: str = Depends(get_current_user_id)) -> Dict:
    """
    Generate report for the given month (e.g., '2025-11'), upload to S3, return insights + download link.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        logger.info(f"Generating monthly report for user_id: {user_id}, month: {month}")
        
        expenses = dynamo.get_expenses_for_user(user_id, month)
        logger.info(f"Found {len(expenses)} expenses for user {user_id} in month {month}")
        
        if not expenses:
            raise HTTPException(status_code=404, detail="No expenses found for this month.")

        # Analyze expenses via the reusable finance_analyzer_lib
        try:
            summary = finance_analyzer.summarize(expenses)
            logger.info(f"Summary generated successfully: total={summary.get('monthly_total', 0)}")
        except Exception as e:
            logger.error(f"Error analyzing expenses: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error analyzing expenses: {str(e)}")

        # Generate report files & upload to S3
        report_id = f"{user_id}_{month}_{uuid.uuid4().hex[:6]}"
        
        try:
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
            logger.info(f"PDF uploaded: {pdf_url}")
        except Exception as e:
            logger.error(f"Error uploading PDF: {str(e)}")
            pdf_url = None
        
        try:
            csv_url = pdf_report.generate_and_upload_csv(user_id, month, expenses, report_id)
            logger.info(f"CSV uploaded: {csv_url}")
        except Exception as e:
            logger.error(f"Error uploading CSV: {str(e)}")
            csv_url = None

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
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error generating report: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
