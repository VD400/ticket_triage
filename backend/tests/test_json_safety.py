import pytest
from agent.tools import _json_safe
from decimal import Decimal
from datetime import datetime

@pytest.mark.parametrize("data, value", [
    (Decimal(5.78), 5.78),
    (isinstance(_json_safe(datetime.now()), str), True),
    (_json_safe("plain_string") == "plain_string")
])
def test_json_safe_date_decimal(data, value):
    assert data==value