import sqlite3
import subprocess
import sys
from pathlib import Path


def test_demo_database_seed_is_complete_and_non_destructive(tmp_path):
    script = Path(__file__).parents[1] / 'deploy' / 'seed_demo_databases.py'
    result = subprocess.run(
        [sys.executable, str(script), '--output-dir', str(tmp_path)],
        capture_output=True, text=True, check=True,
    )
    expected = {
        'demo-sales.sqlite3': {'customers', 'sales_reps', 'products', 'orders', 'order_items'},
        'demo-finance.sqlite3': {'departments', 'cost_centers', 'monthly_budget', 'monthly_actuals', 'invoices'},
        'demo-hr.sqlite3': {'departments', 'employees', 'attendance_summary', 'training_records'},
        'demo-operations.sqlite3': {'sites', 'assets', 'incidents', 'service_metrics', 'maintenance'},
    }
    assert set(result.stdout.splitlines()) == set(expected)
    for filename, tables in expected.items():
        with sqlite3.connect(tmp_path / filename) as database:
            actual = {row[0] for row in database.execute(
                "SELECT name FROM sqlite_master WHERE type='table'")}
            assert actual == tables
            assert database.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
    repeated = subprocess.run(
        [sys.executable, str(script), '--output-dir', str(tmp_path)],
        capture_output=True, text=True,
    )
    assert repeated.returncode != 0
