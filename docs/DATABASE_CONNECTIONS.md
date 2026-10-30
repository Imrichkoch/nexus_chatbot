# External reporting databases

Administration → **A5 / SQL Report Agent → Database connection** manages the
default connection and up to 20 additional named connections. The built-in
fictional SQLite demo remains available independently. Each Data chat is pinned
to one source; separate chats can query different databases concurrently.
Selecting another database in the composer starts a new chat draft, without
changing existing history. Reports record the source ID, revision, label and SQL.

## Supported connectors

| GUI type | Driver | Connection details |
| --- | --- | --- |
| PostgreSQL | SQLAlchemy + psycopg 3 | Host, port (usually 5432), database, reader, schema (default `public`) |
| MySQL | SQLAlchemy + PyMySQL | Host, port (usually 3306), database, reader |
| MariaDB | SQLAlchemy + PyMySQL | Host, port (usually 3306), database, reader; MariaDB-specific statement timeout |
| Microsoft SQL Server | SQLAlchemy + pyodbc | Host, port (usually 1433), database, reader, schema (default `dbo`) |
| Oracle | SQLAlchemy + python-oracledb Thin | Host, listener port, **service name**, reader, schema (default reader name) |
| SQLite (external) | SQLAlchemy + Python sqlite3 | Existing filename in the operator-approved directory; never seeded or created by Nexus |

SQL Server additionally requires **Microsoft ODBC Driver 18 for SQL Server** on
the application host/image. The Python dependency and unixODBC runtime do not
install this vendor driver. Install it using Microsoft's instructions for the
target OS and configure the OS trust store for its database certificate.
Oracle Thin does not require Instant Client; older Oracle versions, wallet/mTLS,
SSPI/Kerberos and cloud-specific authentication are not exposed in this form.

This is multi-database SQL support, not a promise to connect to every database.
MongoDB, Redis, Elasticsearch, arbitrary ODBC DSNs, arbitrary SQLAlchemy plugins
and unknown dialects are not accepted. Add and test a dedicated adapter before
enabling another backend. Server-version compatibility and enterprise TLS must
be verified on the actual target; SQLite, PostgreSQL, MySQL and MariaDB have
integration coverage. SQL Server and Oracle need target-system acceptance tests.

## Setup workflow

1. A database administrator creates a **dedicated SELECT-only account** with
   access only to approved reporting tables/views. No administrator, owner,
   superuser, file-access, DDL/DML or arbitrary routine-execution grants. Prefer a
   reporting replica or curated views. Do not connect to Nexus's own account/chat DB.
2. Ensure the **Nexus server**, not just the browser, can reach the database. Apply
   a database egress allowlist at the network layer. Restrict database ingress to
   the application host and install the corporate certificate chain.
3. In A5 choose **New connection**, give it a unique name, select the type and
   enter connection details. Confirm read-only grants
   and organizational approval to send schema/results to the configured AI provider.
4. **Test and list tables** inspects metadata using a temporary connection. It
   neither saves settings nor sends data to the model. It lists up to 500 eligible
   table/view names in the chosen schema; it does not verify every possible grant.
5. Enter up to 50 allowed unqualified table/view names, separated by commas. Simple
   ASCII identifiers are supported; expose views for unusual identifiers. Selected
   metadata is capped at 32,000 characters. Only selected tables enter the prompt.
6. **Save connection** repeats connection/metadata validation, then atomically
   stores the named profile. Failed validation leaves saved configuration unchanged.
   The backward-compatible **Default connection** uses **Save and activate**.
7. Select the saved database in Data chat and ask for a report or enter a SELECT query. The planner uses the
   selected dialect. External reports are not labeled fictional. Verify an approved
   query and a blocked write before onboarding administrators.
8. Select **Demo** in the chat source selector to start a fictional-data chat.
   This does not remove other saved connections or their credentials.

External sources are **admin-only**, enforced in the API even when the demo Data
agent was enabled for ordinary users. Ordinary users see only the demo source;
external chat histories are also restricted to administrators. There is no
per-user database identity, row-level authorization mapping or cross-database JOIN.

## Chat binding and connection lifecycle

`conversations.database_connection_id` stores an immutable source binding. At
startup, older unbound Data chats are assigned the current default source once.
An unknown or unavailable source is rejected, never silently replaced with demo.
Named profiles have stable IDs and independent optimistic revisions. Each request
captures its own settings/schema snapshot, so concurrent chats cannot overwrite
one another's selected source. Connections are opened on demand, not kept open
merely because a profile is saved.

Deleting a profile or changing its endpoint (type, host, port, database or schema)
is blocked while any chat references it. Create a new profile for another endpoint.
Credentials and approved table lists can still be updated; new requests use the
new revision. Removing a connection never deletes a remote database. Existing
chat content is not rewritten when configuration changes.

## Credentials, TLS and persistence

`NEXUS_DB_CONNECTION_PATH` defaults to `database-connection.json` beside the primary
application database. It contains connection metadata, cached selected schema and
the password, and is atomically replaced with mode `0600`. It is not encrypted at
rest: protect the host, volume and backups with the corporate secret/storage policy.
Neither API responses nor prompts contain its password. Driver errors are redacted.
Blank password retains the saved secret **only for the same endpoint and user**;
changing host, port, type, database or user requires a fresh password.
An optimistic revision check prevents one administrator silently overwriting another.
Named profiles live in the same protected JSON document under `profiles`; updates
preserve the legacy default settings and all other profiles atomically.

Back up this file separately from SQLite, encrypted and access-restricted. The
reference systemd release helper includes its default path in release backups.
For custom paths, update the organization's backup procedure. After a rollback
to code predating external connectors, Data uses the demo database; verify the
active source explicitly. In-flight requests keep their original source snapshot.

Verified TLS is the default. `NEXUS_DB_CA_FILE` can specify a corporate PEM CA for
PostgreSQL, MySQL/MariaDB and Oracle. SQL Server uses the ODBC/OS certificate trust
configuration. A TLS failure is never retried over plaintext. The server-side
`NEXUS_DB_ALLOW_INSECURE=1` permits the GUI TLS checkbox to be disabled **only for
operator-approved isolated tests**; do not enable it for company credentials.

For SQLite, put a separate approved database in `NEXUS_EXTERNAL_SQLITE_ROOT`
(default `external-databases` beside the application DB). Enter a filename such
as `reporting.sqlite3`, not a filesystem path or URI. Path traversal and symlink
escapes are rejected. Mount this directory read-only in containers; ensure the
service can read it. The application opens it using SQLite `mode=ro` and
`query_only`; it never creates or modifies that file. Do not place Nexus's main
database, secrets or unrelated databases in this directory.

## Query controls and limitations

The external path parses and re-renders SQL using SQLGlot in the selected dialect.
Only a single SELECT/WITH/set query is accepted. Mutation nodes, SELECT INTO,
locks, recursive queries, comments/hints, variables, remote tables, table functions
and functions outside a small reporting allowlist are rejected. Base tables are
checked against the allowlist and explicitly schema-qualified. The query is capped
to 101 server rows to detect truncation; at most 100 rows and 64 unique columns are
returned. Cells and aggregate report text are bounded; truncation is surfaced in
report metadata. The stored methodology is the SQL actually executed, including
the enforced row cap.

Each operation creates and closes a fresh connection. PostgreSQL, MySQL/MariaDB
and Oracle receive read-only transaction settings; SQLite uses a read-only file.
SQL Server has **no equivalent general read-only transaction**: its SELECT-only
grants are essential. `ApplicationIntent=ReadOnly` is a routing hint, not security.
PostgreSQL/MySQL/MariaDB use statement timeouts; SQL Server uses the driver's query
timeout, SQLite a progress interrupt, and Oracle a per-call timeout. These are not
a universal hard deadline for an entire network operation. Configure database
resource governors, connection limits and reporting views with bounded cell sizes.
SQL validation cannot guarantee the absence of side effects from database-owned
views, operators or routines: least-privileged grants remain mandatory.

The app does not sample row data during schema inspection. It sends selected
column/type metadata during SQL planning and bounded query results during report
generation. Apply your provider approval, retention, regional processing and data
classification policies before activating a source. Chat history retains reports.

## Adapter reference documentation

- [SQLAlchemy engine configuration](https://docs.sqlalchemy.org/en/20/core/engines.html)
- [SQL Server dialect and ODBC setup](https://docs.sqlalchemy.org/en/20/dialects/mssql.html)
- [PostgreSQL read-only transactions](https://www.postgresql.org/docs/current/sql-set-transaction.html)
- [MariaDB query timeouts](https://mariadb.com/docs/server/ha-and-performance/optimization-and-tuning/query-optimizations/query-limits-and-timeouts)
- [Oracle Python driver](https://python-oracledb.readthedocs.io/en/latest/)
