#!/usr/bin/env python3
"""Create four deterministic, entirely fictional SQLite reporting databases."""
from __future__ import annotations

import argparse
import os
import sqlite3
import tempfile
from pathlib import Path


DATABASES = {
    'demo-sales.sqlite3': {
        'schema': '''
            CREATE TABLE customers (id INTEGER PRIMARY KEY, name TEXT, country TEXT, segment TEXT);
            CREATE TABLE sales_reps (id INTEGER PRIMARY KEY, name TEXT, region TEXT);
            CREATE TABLE products (id INTEGER PRIMARY KEY, name TEXT, category TEXT, unit_cost REAL, list_price REAL);
            CREATE TABLE orders (id INTEGER PRIMARY KEY, customer_id INTEGER, sales_rep_id INTEGER, ordered_on TEXT, status TEXT);
            CREATE TABLE order_items (id INTEGER PRIMARY KEY, order_id INTEGER, product_id INTEGER, quantity INTEGER, unit_price REAL);
        ''',
        'rows': {
            'customers': [(i, f'Example Customer {i:02}', ['Slovakia','Czechia','Austria','Germany'][i % 4], ['SMB','Mid-market','Enterprise'][i % 3]) for i in range(1, 25)],
            'sales_reps': [(1,'Alex Novak','Central'),(2,'Taylor Urban','West'),(3,'Robin Marek','North'),(4,'Casey Horak','South')],
            'products': [(1,'Nexa Desk','Hardware',120,219),(2,'Nexa Cloud','Software',18,79),(3,'Nexa Care','Service',35,129),(4,'Nexa Edge','Hardware',210,399),(5,'Nexa Insights','Software',28,149)],
            'orders': [(i, (i % 24) + 1, (i % 4) + 1, f'2026-{((i-1)%8)+1:02}-{((i*3)%27)+1:02}', ['paid','paid','shipped','pending'][i % 4]) for i in range(1, 81)],
            'order_items': [(i, i, (i % 5) + 1, (i % 7) + 1, [219,79,129,399,149][i % 5]) for i in range(1, 81)],
        },
    },
    'demo-finance.sqlite3': {
        'schema': '''
            CREATE TABLE departments (id INTEGER PRIMARY KEY, name TEXT, owner TEXT);
            CREATE TABLE cost_centers (id INTEGER PRIMARY KEY, department_id INTEGER, code TEXT, name TEXT);
            CREATE TABLE monthly_budget (id INTEGER PRIMARY KEY, cost_center_id INTEGER, month TEXT, amount REAL);
            CREATE TABLE monthly_actuals (id INTEGER PRIMARY KEY, cost_center_id INTEGER, month TEXT, amount REAL);
            CREATE TABLE invoices (id INTEGER PRIMARY KEY, vendor TEXT, department_id INTEGER, issued_on TEXT, due_on TEXT, amount REAL, status TEXT);
        ''',
        'rows': {
            'departments': [(1,'Engineering','Morgan Vale'),(2,'Sales','Jamie North'),(3,'Operations','Drew Stone'),(4,'People','Sam Linden')],
            'cost_centers': [(1,1,'ENG-100','Platform'),(2,1,'ENG-200','Applications'),(3,2,'SAL-100','Field Sales'),(4,3,'OPS-100','Facilities'),(5,4,'PPL-100','Talent')],
            'monthly_budget': [(m*5+c, c, f'2026-{m:02}', 18000 + c*4200 + m*350) for m in range(1,9) for c in range(1,6)],
            'monthly_actuals': [(m*5+c, c, f'2026-{m:02}', 16500 + c*4500 + ((m*c)%5)*620) for m in range(1,9) for c in range(1,6)],
            'invoices': [(i, f'Fictional Vendor {(i%12)+1:02}', (i%4)+1, f'2026-{((i-1)%8)+1:02}-05', f'2026-{((i-1)%8)+1:02}-25', 850 + i*137, ['paid','paid','open','overdue'][i%4]) for i in range(1,49)],
        },
    },
    'demo-hr.sqlite3': {
        'schema': '''
            CREATE TABLE departments (id INTEGER PRIMARY KEY, name TEXT, location TEXT);
            CREATE TABLE employees (id INTEGER PRIMARY KEY, employee_code TEXT, name TEXT, department_id INTEGER, job_title TEXT, hired_on TEXT, employment_status TEXT);
            CREATE TABLE attendance_summary (id INTEGER PRIMARY KEY, employee_id INTEGER, month TEXT, work_days INTEGER, absence_days INTEGER);
            CREATE TABLE training_records (id INTEGER PRIMARY KEY, employee_id INTEGER, course TEXT, completed_on TEXT, score INTEGER);
        ''',
        'rows': {
            'departments': [(1,'Engineering','Bratislava'),(2,'Sales','Prague'),(3,'Operations','Vienna'),(4,'People','Remote')],
            'employees': [(i, f'EMP-{1000+i}', f'Demo Employee {i:02}', (i%4)+1, ['Engineer','Account Executive','Operations Analyst','People Partner'][i%4], f'20{19+(i%7)}-{(i%12)+1:02}-15', ['active','active','active','leave'][i%4]) for i in range(1,41)],
            'attendance_summary': [(m*40+i, i, f'2026-{m:02}', 20 + (m%3), (i*m)%4) for m in range(1,9) for i in range(1,41)],
            'training_records': [(i, (i%40)+1, ['Security Basics','Data Privacy','Incident Response','Leadership'][i%4], f'2026-{(i%8)+1:02}-{(i%24)+1:02}', 75+(i%26)) for i in range(1,81)],
        },
    },
    'demo-operations.sqlite3': {
        'schema': '''
            CREATE TABLE sites (id INTEGER PRIMARY KEY, code TEXT, city TEXT, tier TEXT);
            CREATE TABLE assets (id INTEGER PRIMARY KEY, site_id INTEGER, asset_tag TEXT, asset_type TEXT, status TEXT);
            CREATE TABLE incidents (id INTEGER PRIMARY KEY, site_id INTEGER, opened_at TEXT, severity TEXT, category TEXT, resolution_minutes INTEGER, status TEXT);
            CREATE TABLE service_metrics (id INTEGER PRIMARY KEY, site_id INTEGER, day TEXT, availability_percent REAL, requests INTEGER, error_count INTEGER);
            CREATE TABLE maintenance (id INTEGER PRIMARY KEY, asset_id INTEGER, scheduled_on TEXT, completed_on TEXT, result TEXT);
        ''',
        'rows': {
            'sites': [(1,'BTS-1','Bratislava','primary'),(2,'PRG-1','Prague','primary'),(3,'VIE-1','Vienna','edge'),(4,'BER-1','Berlin','edge')],
            'assets': [(i, (i%4)+1, f'ASSET-{2000+i}', ['server','switch','storage','ups'][i%4], ['online','online','maintenance','online'][i%4]) for i in range(1,49)],
            'incidents': [(i, (i%4)+1, f'2026-{((i-1)%8)+1:02}-{(i%27)+1:02}T{(i%24):02}:00:00Z', ['low','medium','high','critical'][i%4], ['network','application','hardware','capacity'][i%4], 12+(i*17)%360, ['resolved','resolved','monitoring'][i%3]) for i in range(1,65)],
            'service_metrics': [(d*4+s, s, f'2026-08-{d:02}', 99.5 + ((d+s)%5)/10, 8000+d*170+s*400, (d*s)%19) for d in range(1,29) for s in range(1,5)],
            'maintenance': [(i, (i%48)+1, f'2026-{(i%8)+1:02}-10', f'2026-{(i%8)+1:02}-10', ['passed','passed','follow-up'][i%3]) for i in range(1,49)],
        },
    },
}


def build_database(destination: Path, definition: dict, replace: bool) -> None:
    if destination.exists() and not replace:
        raise FileExistsError(f'{destination} already exists; use --replace explicitly')
    descriptor, temporary_name = tempfile.mkstemp(prefix=f'.{destination.stem}-', suffix='.sqlite3', dir=destination.parent)
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        database = sqlite3.connect(temporary)
        try:
            database.executescript(definition['schema'])
            for table, rows in definition['rows'].items():
                placeholders = ','.join('?' for _ in rows[0])
                database.executemany(f'INSERT INTO {table} VALUES ({placeholders})', rows)
            database.execute('PRAGMA optimize')
            if database.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                raise RuntimeError(f'Integrity check failed for {destination.name}')
            database.commit()
        finally:
            database.close()
        os.chmod(temporary, 0o640)
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', required=True, type=Path)
    parser.add_argument('--replace', action='store_true')
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for filename, definition in DATABASES.items():
        build_database(args.output_dir / filename, definition, args.replace)
        print(filename)


if __name__ == '__main__':
    main()
