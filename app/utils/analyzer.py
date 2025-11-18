from __future__ import annotations

import json
import statistics
from collections import defaultdict
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class CategoryInsight:
    """Represents calculated insights for a single expense category."""

    category: str
    total: float
    average: float
    transaction_count: int
    overspent: bool = False
    suggested_budget: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        # Remove None values for cleaner JSON responses
        return {k: v for k, v in data.items() if v is not None}


class FinanceAnalyzer:
    """
    Cloud-ready analytics helper that encapsulates business logic used by
    FastAPI routes, async tasks, and AWS Lambda functions.
    """

    def __init__(
        self,
        budget_config_path: Optional[str | Path] = None,
        spike_sigma: float = 2.5,
        minimum_spike_amount: float = 250.0,
    ) -> None:
        self._spike_sigma = spike_sigma
        self._minimum_spike_amount = minimum_spike_amount
        self._budget_thresholds = self._load_budget_thresholds(budget_config_path)

    @staticmethod
    def _load_budget_thresholds(path: Optional[str | Path]) -> Dict[str, float]:
        if not path:
            return {}

        budget_file = Path(path)
        if not budget_file.exists():
            return {}

        with budget_file.open() as fp:
            return json.load(fp)

    def load_thresholds(self, overrides: Optional[Dict[str, float]] = None) -> Dict[str, float]:
        merged = dict(self._budget_thresholds)
        if overrides:
            merged.update(overrides)
        return merged

    def monthly_total(self, expenses: List[Dict[str, Any]]) -> float:
        return round(sum(float(exp.get("amount", 0)) for exp in expenses), 2)

    def category_totals(self, expenses: List[Dict[str, Any]]) -> Dict[str, float]:
        totals: Dict[str, float] = defaultdict(float)
        for exp in expenses:
            totals[exp["category"]] += float(exp.get("amount", 0))
        return {cat: round(total, 2) for cat, total in totals.items()}

    def overspending_categories(
        self,
        expenses: List[Dict[str, Any]],
        budget_overrides: Optional[Dict[str, float]] = None,
    ) -> Dict[str, float]:
        thresholds = self.load_thresholds(budget_overrides)
        if not thresholds:
            return {}

        totals = self.category_totals(expenses)
        overspent = {
            cat: amount
            for cat, amount in totals.items()
            if cat in thresholds and amount > thresholds[cat]
        }
        return overspent

    def suggest_budget(
        self,
        expenses: List[Dict[str, Any]],
        buffer_percentage: float = 0.15,
    ) -> Dict[str, float]:
        """
        Suggests a budget using average spend plus a configurable buffer.
        """
        category_spend: Dict[str, List[float]] = defaultdict(list)
        for exp in expenses:
            category_spend[exp["category"]].append(float(exp.get("amount", 0)))

        suggestions = {}
        for category, amounts in category_spend.items():
            avg = statistics.fmean(amounts)
            suggestions[category] = round(avg * (1 + buffer_percentage), 2)
        return suggestions

    def detect_spending_spikes(
        self,
        expenses: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Detect outliers using Z-score heuristics to highlight unusual spends.
        """
        if not expenses:
            return []

        amounts = [float(exp.get("amount", 0)) for exp in expenses]
        mean = statistics.fmean(amounts)
        stdev = statistics.pstdev(amounts)

        anomalies: List[Dict[str, Any]] = []
        for exp in expenses:
            amount = float(exp.get("amount", 0))
            if amount < self._minimum_spike_amount:
                continue
            if stdev == 0:
                z_score = 0
            else:
                z_score = (amount - mean) / stdev
            if z_score >= self._spike_sigma:
                anomalies.append(exp)
        return anomalies

    def summarize(
        self,
        expenses: List[Dict[str, Any]],
        budget_overrides: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        if not expenses:
            return {
                "monthly_total": 0.0,
                "category_totals": {},
                "overspending_categories": {},
                "suggested_budgets": {},
                "spending_spikes": [],
                "insights": [],
            }

        category_map: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for exp in expenses:
            category_map[exp["category"]].append(exp)

        category_totals = {
            category: round(sum(float(item.get("amount", 0)) for item in items), 2)
            for category, items in category_map.items()
        }
        suggestions = self.suggest_budget(expenses)
        overspent = self.overspending_categories(expenses, budget_overrides)

        insights = [
            CategoryInsight(
                category=category,
                total=category_totals[category],
                average=round(category_totals[category] / len(items), 2),
                transaction_count=len(items),
                overspent=category in overspent,
                suggested_budget=suggestions.get(category),
            ).to_dict()
            for category, items in category_map.items()
        ]

        return {
            "monthly_total": self.monthly_total(expenses),
            "category_totals": category_totals,
            "overspending_categories": overspent,
            "suggested_budgets": suggestions,
            "spending_spikes": self.detect_spending_spikes(expenses),
            "insights": insights,
        }
