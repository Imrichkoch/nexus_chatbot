# Fictional Data-agent databases

`deploy/seed_demo_databases.py` creates four deterministic SQLite reporting
databases containing no real people, customers, credentials or operational data:

| Connection | File | Reporting areas |
| --- | --- | --- |
| Demo Sales & CRM | `demo-sales.sqlite3` | customers, representatives, products, orders and line items |
| Demo Finance | `demo-finance.sqlite3` | departments, cost centres, budgets, actuals and invoices |
| Demo HR | `demo-hr.sqlite3` | fictional employees, attendance and training |
| Demo Operations | `demo-operations.sqlite3` | sites, assets, incidents, service metrics and maintenance |

Create them inside the approved external SQLite directory as the Nexus service
account:

```bash
sudo -u nexuschat /opt/nexuschat/.venv/bin/python \
  /opt/nexuschat/deploy/seed_demo_databases.py \
  --output-dir /opt/nexuschat/data/external-databases
```

The default mode refuses to replace an existing file. `--replace` is deliberately
explicit and should be used only after checking that no retained chat depends on
the old fictional dataset. Each database is built in a temporary file, receives
an SQLite integrity check, and is atomically moved into place with mode `0640`.

In Administration A5, create one named SQLite connection per file, select only
the tables listed above, and confirm read-only/data-egress controls. Testing or
saving a profile never modifies the database; Nexus opens these files with
SQLite `mode=ro` and `query_only` enabled. Keep the word **Demo** in connection
names so users do not mistake synthetic reports for company records.
