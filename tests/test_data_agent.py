import sqlite3

import pytest

from nexus.data_agent import QueryRejected, SyntheticDatabase


def test_synthetic_database_is_seeded_with_related_business_data(tmp_path):
    database = SyntheticDatabase(str(tmp_path / "synthetic.sqlite3"))

    result = database.execute(
        """
        SELECT COUNT(DISTINCT c.id) AS customers,
               COUNT(DISTINCT o.id) AS orders,
               ROUND(SUM(oi.quantity * oi.unit_price), 2) AS revenue
        FROM customers c
        JOIN orders o ON o.customer_id = c.id
        JOIN order_items oi ON oi.order_id = o.id
        """
    )

    assert result["columns"] == ["customers", "orders", "revenue"]
    assert result["rows"][0]["customers"] >= 20
    assert result["rows"][0]["orders"] >= 100
    assert result["rows"][0]["revenue"] > 0
    assert "customers" in database.schema_prompt()
    assert "support_tickets" in database.schema_prompt()


@pytest.mark.parametrize(
    "sql",
    [
        "DELETE FROM customers",
        "UPDATE customers SET country = 'XX'",
        "DROP TABLE customers",
        "PRAGMA table_info(customers)",
        "ATTACH DATABASE ':memory:' AS extra",
        "SELECT 1; SELECT 2",
        "SELECT length(randomblob(10000000))",
        "SELECT printf('%10000000s', 'x')",
        "SELECT format('%10000000s', 'x')",
    ],
)
def test_synthetic_database_rejects_non_read_only_or_multiple_statements(
    tmp_path, sql
):
    database = SyntheticDatabase(str(tmp_path / "synthetic.sqlite3"))

    with pytest.raises(QueryRejected):
        database.execute(sql)

    with sqlite3.connect(database.path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM customers").fetchone()[0] >= 20


def test_synthetic_database_caps_report_rows(tmp_path):
    database = SyntheticDatabase(str(tmp_path / "synthetic.sqlite3"))

    result = database.execute(
        "SELECT a.id, b.id FROM orders a CROSS JOIN orders b",
        max_rows=25,
    )

    assert len(result["rows"]) == 25
    assert result["truncated"] is True


def test_synthetic_database_caps_wide_and_oversized_results(tmp_path):
    database = SyntheticDatabase(str(tmp_path / "synthetic.sqlite3"))
    with sqlite3.connect(database.path) as connection:
        connection.execute(
            "UPDATE customers SET company_name = ? WHERE id = 1",
            ("X" * 20_000,),
        )

    result = database.execute(
        "SELECT company_name FROM customers WHERE id = 1",
        max_cell_characters=500,
    )

    assert len(result["rows"][0]["company_name"]) <= 501
    assert result["cells_truncated"] is True

    too_wide = "SELECT " + ", ".join(f"{index} AS c{index}" for index in range(70))
    with pytest.raises(QueryRejected, match="stĺpc"):
        database.execute(too_wide, max_columns=64)
