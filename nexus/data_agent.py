from __future__ import annotations

import random
import re
import sqlite3
import time
from datetime import date, timedelta
from pathlib import Path
from typing import Any


class QueryRejected(ValueError):
    pass


FORBIDDEN_SQL = re.compile(
    r"\b("
    r"alter|analyze|attach|begin|commit|create|delete|detach|drop|end|"
    r"insert|load_extension|pragma|reindex|release|replace|rollback|savepoint|"
    r"update|vacuum"
    r")\b",
    re.IGNORECASE,
)

DENIED_ACTIONS = {
    value
    for name in (
        "SQLITE_ALTER_TABLE",
        "SQLITE_ANALYZE",
        "SQLITE_ATTACH",
        "SQLITE_CREATE_INDEX",
        "SQLITE_CREATE_TABLE",
        "SQLITE_CREATE_TEMP_INDEX",
        "SQLITE_CREATE_TEMP_TABLE",
        "SQLITE_CREATE_TEMP_TRIGGER",
        "SQLITE_CREATE_TEMP_VIEW",
        "SQLITE_CREATE_TRIGGER",
        "SQLITE_CREATE_VIEW",
        "SQLITE_DELETE",
        "SQLITE_DETACH",
        "SQLITE_DROP_INDEX",
        "SQLITE_DROP_TABLE",
        "SQLITE_DROP_TEMP_INDEX",
        "SQLITE_DROP_TEMP_TABLE",
        "SQLITE_DROP_TEMP_TRIGGER",
        "SQLITE_DROP_TEMP_VIEW",
        "SQLITE_DROP_TRIGGER",
        "SQLITE_DROP_VIEW",
        "SQLITE_INSERT",
        "SQLITE_PRAGMA",
        "SQLITE_REINDEX",
        "SQLITE_TRANSACTION",
        "SQLITE_UPDATE",
    )
    if (value := getattr(sqlite3, name, None)) is not None
}
UNSAFE_FUNCTIONS = {
    "format",
    "load_extension",
    "printf",
    "randomblob",
    "readfile",
    "writefile",
    "zeroblob",
}


class SyntheticDatabase:
    def __init__(self, path: str):
        self.path = str(Path(path))
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._ensure_seeded()

    def _ensure_seeded(self) -> None:
        with sqlite3.connect(self.path) as db:
            existing = db.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='dataset_meta'"
            ).fetchone()
            if existing:
                self._tighten_permissions()
                return
            db.executescript(
                """
                CREATE TABLE dataset_meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                CREATE TABLE customers (
                    id INTEGER PRIMARY KEY,
                    company_name TEXT NOT NULL,
                    country TEXT NOT NULL,
                    segment TEXT NOT NULL,
                    joined_at TEXT NOT NULL,
                    account_manager TEXT NOT NULL
                );
                CREATE TABLE products (
                    id INTEGER PRIMARY KEY,
                    sku TEXT NOT NULL UNIQUE,
                    name TEXT NOT NULL,
                    category TEXT NOT NULL,
                    unit_price REAL NOT NULL,
                    unit_cost REAL NOT NULL
                );
                CREATE TABLE orders (
                    id INTEGER PRIMARY KEY,
                    customer_id INTEGER NOT NULL REFERENCES customers(id),
                    order_date TEXT NOT NULL,
                    status TEXT NOT NULL,
                    channel TEXT NOT NULL,
                    sales_rep TEXT NOT NULL
                );
                CREATE TABLE order_items (
                    id INTEGER PRIMARY KEY,
                    order_id INTEGER NOT NULL REFERENCES orders(id),
                    product_id INTEGER NOT NULL REFERENCES products(id),
                    quantity INTEGER NOT NULL,
                    unit_price REAL NOT NULL,
                    discount_percent REAL NOT NULL
                );
                CREATE TABLE support_tickets (
                    id INTEGER PRIMARY KEY,
                    customer_id INTEGER NOT NULL REFERENCES customers(id),
                    opened_at TEXT NOT NULL,
                    category TEXT NOT NULL,
                    priority TEXT NOT NULL,
                    status TEXT NOT NULL,
                    resolution_hours REAL
                );
                CREATE TABLE monthly_targets (
                    month TEXT PRIMARY KEY,
                    revenue_target REAL NOT NULL,
                    order_target INTEGER NOT NULL,
                    ticket_sla_hours REAL NOT NULL
                );
                CREATE INDEX idx_orders_customer ON orders(customer_id);
                CREATE INDEX idx_orders_date ON orders(order_date);
                CREATE INDEX idx_items_order ON order_items(order_id);
                CREATE INDEX idx_tickets_customer ON support_tickets(customer_id);
                """
            )
            self._seed(db)
        self._tighten_permissions()

    def _tighten_permissions(self) -> None:
        try:
            Path(self.path).chmod(0o640)
        except OSError:
            pass

    @staticmethod
    def _seed(db: sqlite3.Connection) -> None:
        rng = random.Random(20260724)
        db.executemany(
            "INSERT INTO dataset_meta (key, value) VALUES (?, ?)",
            [
                ("dataset", "Nexus Synthetic Commerce"),
                ("fictional", "true"),
                ("currency", "EUR"),
                ("generated_for", "SQL Report Agent demo"),
            ],
        )
        countries = ["Slovensko", "Česko", "Rakúsko", "Nemecko", "Poľsko"]
        segments = ["SMB", "Mid-market", "Enterprise"]
        managers = ["Nina Kováčová", "Martin Novák", "Laura Weiss", "Tomáš Urban"]
        prefixes = [
            "Aurora",
            "BluePeak",
            "Cobalt",
            "Delta",
            "Evergreen",
            "Fusion",
            "Granite",
            "Helix",
            "Ion",
        ]
        suffixes = ["Labs", "Retail", "Systems", "Works"]
        customers = []
        start = date(2023, 1, 1)
        for customer_id in range(1, 37):
            customers.append(
                (
                    customer_id,
                    f"{prefixes[(customer_id - 1) % len(prefixes)]} "
                    f"{suffixes[(customer_id - 1) // len(prefixes)]}",
                    countries[(customer_id * 3) % len(countries)],
                    segments[customer_id % len(segments)],
                    (start + timedelta(days=rng.randint(0, 850))).isoformat(),
                    managers[customer_id % len(managers)],
                )
            )
        db.executemany(
            """
            INSERT INTO customers
                (id, company_name, country, segment, joined_at, account_manager)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            customers,
        )

        product_specs = [
            ("Edge Sensor", "Hardware", 189.0, 92.0),
            ("Nexus Gateway", "Hardware", 449.0, 238.0),
            ("Cloud Basic", "Subscription", 79.0, 14.0),
            ("Cloud Pro", "Subscription", 219.0, 34.0),
            ("Cloud Enterprise", "Subscription", 699.0, 105.0),
            ("Analytics Pack", "Software", 159.0, 22.0),
            ("Security Pack", "Software", 249.0, 38.0),
            ("API Bundle", "Software", 119.0, 16.0),
            ("Onboarding", "Services", 850.0, 410.0),
            ("Architecture Review", "Services", 1250.0, 620.0),
            ("Priority Support", "Services", 499.0, 190.0),
            ("Training Day", "Services", 990.0, 470.0),
            ("Mobile Terminal", "Hardware", 329.0, 174.0),
            ("Backup Module", "Hardware", 139.0, 68.0),
            ("Forecast Add-on", "Software", 189.0, 27.0),
            ("Compliance Add-on", "Software", 279.0, 49.0),
            ("Data Migration", "Services", 1490.0, 720.0),
            ("Custom Dashboard", "Services", 1790.0, 840.0),
        ]
        db.executemany(
            """
            INSERT INTO products
                (id, sku, name, category, unit_price, unit_cost)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                (index, f"NX-{index:03d}", name, category, price, cost)
                for index, (name, category, price, cost) in enumerate(
                    product_specs, start=1
                )
            ],
        )

        order_statuses = ["completed"] * 7 + ["processing", "cancelled", "refunded"]
        channels = ["direct", "partner", "web"]
        sales_reps = ["Eva Horváth", "Peter Malík", "Sofia Berger", "Adam Král"]
        order_start = date(2025, 1, 1)
        item_id = 1
        for order_id in range(1, 221):
            customer_id = rng.randint(1, 36)
            order_day = order_start + timedelta(days=rng.randint(0, 565))
            db.execute(
                """
                INSERT INTO orders
                    (id, customer_id, order_date, status, channel, sales_rep)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    order_id,
                    customer_id,
                    order_day.isoformat(),
                    rng.choice(order_statuses),
                    rng.choice(channels),
                    rng.choice(sales_reps),
                ),
            )
            selected_products = rng.sample(range(1, 19), rng.randint(1, 4))
            for product_id in selected_products:
                price = product_specs[product_id - 1][2]
                discount = rng.choice([0, 0, 0, 5, 10, 15])
                db.execute(
                    """
                    INSERT INTO order_items
                        (id, order_id, product_id, quantity, unit_price,
                         discount_percent)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        item_id,
                        order_id,
                        product_id,
                        rng.randint(1, 6),
                        round(price * (1 - discount / 100), 2),
                        discount,
                    ),
                )
                item_id += 1

        ticket_categories = ["billing", "technical", "onboarding", "delivery"]
        priorities = ["low", "medium", "high", "critical"]
        ticket_statuses = ["resolved"] * 7 + ["open", "waiting"]
        for ticket_id in range(1, 91):
            status = rng.choice(ticket_statuses)
            db.execute(
                """
                INSERT INTO support_tickets
                    (id, customer_id, opened_at, category, priority, status,
                     resolution_hours)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    ticket_id,
                    rng.randint(1, 36),
                    (
                        order_start + timedelta(days=rng.randint(0, 565))
                    ).isoformat(),
                    rng.choice(ticket_categories),
                    rng.choice(priorities),
                    status,
                    round(rng.uniform(1.5, 72), 1)
                    if status == "resolved"
                    else None,
                ),
            )

        month = date(2025, 1, 1)
        for offset in range(19):
            current = date(
                month.year + (month.month - 1 + offset) // 12,
                (month.month - 1 + offset) % 12 + 1,
                1,
            )
            db.execute(
                """
                INSERT INTO monthly_targets
                    (month, revenue_target, order_target, ticket_sla_hours)
                VALUES (?, ?, ?, ?)
                """,
                (
                    current.strftime("%Y-%m"),
                    36000 + offset * 950,
                    11 + offset // 4,
                    24.0,
                ),
            )

    def schema_prompt(self) -> str:
        with sqlite3.connect(self.path) as db:
            tables = [
                row[0]
                for row in db.execute(
                    """
                    SELECT name FROM sqlite_master
                    WHERE type='table' AND name NOT LIKE 'sqlite_%'
                    ORDER BY name
                    """
                ).fetchall()
            ]
            definitions = []
            for table in tables:
                columns = db.execute(f'PRAGMA table_info("{table}")').fetchall()
                definitions.append(
                    f"{table}("
                    + ", ".join(f"{column[1]} {column[2]}" for column in columns)
                    + ")"
                )
        return (
            "Dáta sú úplne fiktívne a mena je EUR.\n"
            + "\n".join(definitions)
            + "\nVzťahy: orders.customer_id -> customers.id; "
            "order_items.order_id -> orders.id; "
            "order_items.product_id -> products.id; "
            "support_tickets.customer_id -> customers.id."
        )

    @staticmethod
    def _validated(sql: str) -> str:
        statement = sql.strip()
        if statement.endswith(";"):
            statement = statement[:-1].rstrip()
        if not re.match(r"^(select|with)\b", statement, re.IGNORECASE):
            raise QueryRejected("Povolené sú iba read-only SELECT alebo WITH dotazy.")
        if ";" in statement:
            raise QueryRejected("Naraz je povolený iba jeden SQL dotaz.")
        if FORBIDDEN_SQL.search(statement):
            raise QueryRejected("SQL obsahuje nepovolenú operáciu.")
        return statement

    def execute(
        self,
        sql: str,
        *,
        max_rows: int = 100,
        max_seconds: float = 1.5,
        max_columns: int = 64,
        max_cell_characters: int = 8_000,
    ) -> dict[str, Any]:
        statement = self._validated(sql)
        max_rows = max(1, min(max_rows, 100))
        max_columns = max(1, min(max_columns, 128))
        max_cell_characters = max(128, min(max_cell_characters, 16_000))
        path = Path(self.path).resolve().as_posix()
        started = time.monotonic()
        try:
            connection = sqlite3.connect(
                f"file:{path}?mode=ro",
                uri=True,
                timeout=max_seconds,
            )
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA query_only = ON")

            def authorizer(
                action: int,
                arg1: str | None,
                arg2: str | None,
                _database: str | None,
                _trigger: str | None,
            ) -> int:
                if action == getattr(sqlite3, "SQLITE_FUNCTION", -1):
                    function_name = (arg2 or arg1 or "").lower()
                    if function_name in UNSAFE_FUNCTIONS:
                        return sqlite3.SQLITE_DENY
                return (
                    sqlite3.SQLITE_DENY
                    if action in DENIED_ACTIONS
                    else sqlite3.SQLITE_OK
                )

            connection.set_authorizer(authorizer)
            connection.set_progress_handler(
                lambda: 1 if time.monotonic() - started > max_seconds else 0,
                1000,
            )
            cursor = connection.execute(statement)
            columns = [description[0] for description in (cursor.description or [])]
            if len(columns) > max_columns:
                raise QueryRejected(
                    f"Dotaz vracia príliš veľa stĺpcov (maximum je {max_columns})."
                )
            fetched = cursor.fetchmany(max_rows + 1)
        except sqlite3.Error as error:
            raise QueryRejected(
                f"Dotaz sa nedá vykonať v syntetickej databáze: {error}"
            ) from error
        finally:
            if "connection" in locals():
                connection.close()
        cells_truncated = False
        rows: list[dict[str, Any]] = []
        for row in fetched[:max_rows]:
            safe_row: dict[str, Any] = {}
            for key, value in dict(row).items():
                if isinstance(value, bytes):
                    value = value.hex()
                if isinstance(value, str) and len(value) > max_cell_characters:
                    value = f"{value[:max_cell_characters]}…"
                    cells_truncated = True
                safe_row[key] = value
            rows.append(safe_row)
        return {
            "columns": columns,
            "rows": rows,
            "row_count": len(rows),
            "truncated": len(fetched) > max_rows,
            "cells_truncated": cells_truncated,
            "elapsed_ms": round((time.monotonic() - started) * 1000, 1),
        }


class DataReportAgent:
    def __init__(self, database: SyntheticDatabase, ai_provider: Any):
        self.database = database
        self.ai_provider = ai_provider

    def answer(
        self,
        *,
        question: str,
        user_id: int,
        model: str,
    ) -> dict[str, Any]:
        direct_sql = bool(re.match(r"^\s*(select|with)\b", question, re.IGNORECASE))
        input_tokens = 0
        output_tokens = 0
        if direct_sql:
            sql = question.strip()
        else:
            generated = self.ai_provider.generate_sql(
                question=question,
                schema=self.database.schema_prompt(),
                user_id=user_id,
                model=model,
                error_context=None,
            )
            sql = generated["sql"]
            input_tokens += int(generated.get("input_tokens", 0))
            output_tokens += int(generated.get("output_tokens", 0))
        try:
            query_result = self.database.execute(sql)
        except QueryRejected as first_error:
            if direct_sql:
                raise
            repaired = self.ai_provider.generate_sql(
                question=question,
                schema=self.database.schema_prompt(),
                user_id=user_id,
                model=model,
                error_context=f"Predchádzajúce SQL: {sql}\nChyba: {first_error}",
            )
            sql = repaired["sql"]
            input_tokens += int(repaired.get("input_tokens", 0))
            output_tokens += int(repaired.get("output_tokens", 0))
            query_result = self.database.execute(sql)

        report = self.ai_provider.create_sql_report(
            question=question,
            sql=sql,
            query_result=query_result,
            user_id=user_id,
            model=model,
        )
        return {
            "text": report["text"],
            "model": report.get("model", model),
            "input_tokens": input_tokens + int(report.get("input_tokens", 0)),
            "output_tokens": output_tokens + int(report.get("output_tokens", 0)),
            "source": {
                "type": "sql",
                "label": "Synthetic Business DB",
                "query": sql,
                "row_count": query_result["row_count"],
                "truncated": query_result["truncated"],
                "cells_truncated": query_result["cells_truncated"],
                "elapsed_ms": query_result["elapsed_ms"],
            },
        }
