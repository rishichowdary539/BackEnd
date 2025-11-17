"""
finance_analyzer_lib
~~~~~~~~~~~~~~~~~~~~

Custom analytics library for the Smart Personal Expense & Budget Tracking
Platform. The FinanceAnalyzer class exposes helper methods that can be reused
by FastAPI routes, background jobs, or serverless functions in order to keep
analytics logic consistent across the stack.
"""

from .analyzer import CategoryInsight, FinanceAnalyzer

__all__ = ["CategoryInsight", "FinanceAnalyzer"]

