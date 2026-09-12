import pytest
from agent.tools import _DISALLOWED_SQL

@pytest.mark.parametrize("sql,should_raise", [
    ("SELECT * FROM transactions WHERE customer_id = 1", False),
    ("DROP TABLE transactions WHERE customer_id=1", True),
    ("SELECT * FROM transactions; DELETE FROM transactions", True),
    ("UPDATE transactions SET amount=0", True)
])
def test_sql_keyword_guard(sql, should_raise):
    assert bool(_DISALLOWED_SQL.search(sql)) == should_raise