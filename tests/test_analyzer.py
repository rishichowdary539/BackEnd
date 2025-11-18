from app.utils.analyzer import FinanceAnalyzer

sample_expenses = [
    {"category": "Food", "amount": 250.0, "timestamp": "2025-11-01T12:00:00Z"},
    {"category": "Rent", "amount": 1000.0, "timestamp": "2025-11-02T12:00:00Z"},
    {"category": "Food", "amount": 150.0, "timestamp": "2025-11-03T12:00:00Z"},
    {"category": "Shopping", "amount": 1200.0, "timestamp": "2025-11-04T12:00:00Z"},
]

budget_thresholds = {
    "Food": 300.0,
    "Rent": 900.0,
    "Shopping": 500.0
}


def test_calculate_totals():
    analyzer = FinanceAnalyzer()
    assert analyzer.monthly_total(sample_expenses) == 2600.0


def test_detect_overspending():
    analyzer = FinanceAnalyzer()
    result = analyzer.overspending_categories(sample_expenses, budget_thresholds)
    assert result == {"Food": 400.0, "Rent": 1000.0, "Shopping": 1200.0}


def test_suggest_budget():
    analyzer = FinanceAnalyzer()
    result = analyzer.suggest_budget(sample_expenses, buffer_percentage=0.0)
    assert result["Food"] == 200.0  # (250 + 150) / 2
    assert result["Rent"] == 1000.0
    assert result["Shopping"] == 1200.0


def test_detect_spikes():
    analyzer = FinanceAnalyzer(spike_sigma=0.5, minimum_spike_amount=900)
    result = analyzer.detect_spending_spikes(sample_expenses)
    categories = {item["category"] for item in result}
    assert categories == {"Rent", "Shopping"}
