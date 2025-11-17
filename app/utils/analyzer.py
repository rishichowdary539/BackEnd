"""
Legacy compatibility helpers that proxy to the reusable finance_analyzer_lib.
Prefer importing FinanceAnalyzer directly for new modules.
"""

from typing import Dict, List

from finance_analyzer_lib import FinanceAnalyzer

_analyzer = FinanceAnalyzer()


def calculate_totals(expenses: List[Dict]) -> float:
    return _analyzer.monthly_total(expenses)


def detect_overspending(expenses: List[Dict], budget_thresholds: Dict[str, float]) -> Dict[str, float]:
    return _analyzer.overspending_categories(expenses, budget_thresholds)


def suggest_budget(expenses: List[Dict]) -> Dict[str, float]:
    return _analyzer.suggest_budget(expenses)


def detect_spikes(expenses: List[Dict]) -> List[Dict]:
    return _analyzer.detect_spending_spikes(expenses)
