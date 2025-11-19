"""
Notifications Router
Provides threshold-based notifications for budget overspending, spending spikes, and warnings
"""
from typing import Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Header

from app.core.config import settings
from app.core.security import decode_access_token
from app.db import dynamo
from app.utils.analyzer import FinanceAnalyzer

router = APIRouter()
finance_analyzer = FinanceAnalyzer(settings.BUDGET_THRESHOLDS_JSON)


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


def generate_notifications(expenses: List[Dict], summary: Dict, month: str, user_id: str) -> List[Dict]:
    """
    Generate user-friendly notifications based on spending patterns and thresholds.
    Returns list of notification objects with type, message, and severity.
    Uses thresholds from DynamoDB for the specific user (loaded via finance_analyzer).
    """
    notifications = []
    # Load thresholds from DB for this user (analyzer loads from DB first, then falls back to file)
    thresholds = finance_analyzer.load_thresholds(user_id=user_id)
    
    if not expenses:
        return notifications
    
    # Get category totals and overspending
    category_totals = summary.get("category_totals", {})
    overspending = summary.get("overspending_categories", {})
    spending_spikes = summary.get("spending_spikes", [])
    monthly_total = summary.get("monthly_total", 0)
    
    # 1. Budget Exceeded Notifications (Critical)
    for category, spent_amount in overspending.items():
        threshold = thresholds.get(category, 0)
        over_amount = spent_amount - threshold
        percentage_over = ((spent_amount / threshold) - 1) * 100 if threshold > 0 else 0
        
        notifications.append({
            "id": f"overspend_{category}_{month}",
            "type": "budget_exceeded",
            "severity": "danger",
            "title": f"Budget Exceeded: {category}",
            "message": f"You've exceeded your {category} budget by €{over_amount:.2f} ({percentage_over:.1f}% over limit). Budget: €{threshold:.2f}, Spent: €{spent_amount:.2f}",
            "category": category,
            "amount": spent_amount,
            "threshold": threshold,
            "over_amount": over_amount,
        })
    
    # 2. Approaching Budget Threshold (Warning - 80% of budget)
    for category, threshold in thresholds.items():
        if category in overspending:
            continue  # Skip if already exceeded
        
        spent = category_totals.get(category, 0)
        if spent > 0:
            percentage = (spent / threshold) * 100 if threshold > 0 else 0
            if percentage >= 80 and percentage < 100:
                remaining = threshold - spent
                notifications.append({
                    "id": f"approaching_{category}_{month}",
                    "type": "approaching_budget",
                    "severity": "warning",
                    "title": f"Approaching Budget Limit: {category}",
                    "message": f"You've used {percentage:.1f}% of your {category} budget. Only €{remaining:.2f} remaining out of €{threshold:.2f}.",
                    "category": category,
                    "amount": spent,
                    "threshold": threshold,
                    "percentage": percentage,
                })
    
    # 3. Spending Spike Notifications (Warning)
    if spending_spikes:
        spike_count = len(spending_spikes)
        total_spike_amount = sum(float(spike.get("amount", 0)) for spike in spending_spikes)
        
        if spike_count == 1:
            spike = spending_spikes[0]
            notifications.append({
                "id": f"spike_{spike.get('expense_id', 'unknown')}",
                "type": "spending_spike",
                "severity": "warning",
                "title": "Unusual Spending Detected",
                "message": f"Large expense detected: €{spike.get('amount', 0):.2f} in {spike.get('category', 'Unknown')} category on {spike.get('timestamp', 'unknown date')}. This is significantly higher than your average spending.",
                "category": spike.get("category"),
                "amount": spike.get("amount"),
            })
        else:
            notifications.append({
                "id": f"spikes_{month}",
                "type": "spending_spikes",
                "severity": "warning",
                "title": "Multiple Unusual Expenses Detected",
                "message": f"You have {spike_count} unusual expenses this month totaling €{total_spike_amount:.2f}. Review your spending patterns.",
                "count": spike_count,
                "total_amount": total_spike_amount,
            })
    
    # 4. High Monthly Total Warning (Info)
    total_threshold = sum(thresholds.values()) if thresholds else 0
    if total_threshold > 0 and monthly_total > 0:
        monthly_percentage = (monthly_total / total_threshold) * 100
        if monthly_percentage >= 90:
            notifications.append({
                "id": f"high_monthly_{month}",
                "type": "high_monthly_total",
                "severity": "info",
                "title": "High Monthly Spending",
                "message": f"Your total spending this month is €{monthly_total:.2f}, which is {monthly_percentage:.1f}% of your combined budget limits. Consider reviewing your expenses.",
                "total": monthly_total,
                "percentage": monthly_percentage,
            })
    
    # 5. Good Progress Notification (Success - if spending is reasonable)
    if not overspending and monthly_total > 0:
        all_categories_under_70 = all(
            (category_totals.get(cat, 0) / thresholds.get(cat, 1)) * 100 < 70
            for cat in thresholds.keys()
            if thresholds.get(cat, 0) > 0
        )
        if all_categories_under_70 and len(category_totals) > 0:
            notifications.append({
                "id": f"good_progress_{month}",
                "type": "good_progress",
                "severity": "success",
                "title": "Great Budget Management!",
                "message": f"You're doing well! All categories are under 70% of their budget limits. Keep up the good work!",
            })
    
    return notifications


@router.get("/{month}")
def get_notifications(month: str, user_id: str = Depends(get_current_user_id)) -> Dict:
    """
    Get notifications for a specific month based on spending patterns and thresholds.
    month must follow YYYY-MM format. Example: 2025-11
    """
    expenses = dynamo.get_expenses_for_user(user_id, month)
    # Load user's thresholds for analysis
    thresholds = finance_analyzer.load_thresholds(user_id=user_id)
    summary = finance_analyzer.summarize(expenses, budget_overrides=thresholds)
    
    notifications = generate_notifications(expenses, summary, month, user_id)
    
    # Count by severity
    severity_counts = {
        "danger": len([n for n in notifications if n["severity"] == "danger"]),
        "warning": len([n for n in notifications if n["severity"] == "warning"]),
        "info": len([n for n in notifications if n["severity"] == "info"]),
        "success": len([n for n in notifications if n["severity"] == "success"]),
    }
    
    return {
        "month": month,
        "notifications": notifications,
        "count": len(notifications),
        "severity_counts": severity_counts,
    }


@router.get("/")
def get_current_month_notifications(user_id: str = Depends(get_current_user_id)) -> Dict:
    """
    Get notifications for the current month.
    """
    from datetime import datetime
    current_month = datetime.utcnow().strftime("%Y-%m")
    return get_notifications(current_month, user_id)

