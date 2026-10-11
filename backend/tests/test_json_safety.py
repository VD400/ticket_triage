import pytest
from agent.tools import _json_safe
from decimal import Decimal
from datetime import date, datetime

@pytest.mark.parametrize("data, value", [
    (Decimal("5.78"), 5.78),
    (datetime(2026, 1, 2, 3, 4, 5), "2026-01-02T03:04:05"),
    (date(2026, 1, 2), "2026-01-02"),
    ("plain_string", "plain_string"),
])
def test_json_safe_date_decimal(data, value):
    assert _json_safe(data) == value
