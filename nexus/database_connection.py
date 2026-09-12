"""Admin-configured reporting sources. Credentials never enter prompts or SQLite.

SQL validation is defense in depth, NOT a substitute for SELECT-only database
grants. Every request uses an immutable source snapshot and a fresh connection.
"""
from __future__ import annotations

from contextlib import contextmanager
import json
import os
from pathlib import Path
import re
import ssl
import tempfile
from threading import RLock
import time
import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import URL, create_engine, inspect
from sqlalchemy.pool import NullPool
import sqlglot
from sqlglot import exp
from sqlglot.optimizer.scope import Scope, traverse_scope

from nexus.data_agent import QueryRejected


class ConnectionSettings(BaseModel):
    model_config = ConfigDict(extra='forbid')
    kind: Literal['demo', 'postgresql', 'mysql', 'mariadb', 'mssql', 'oracle', 'sqlite'] = 'demo'
    host: str = Field(default='', max_length=253)
    port: int = Field(default=5432, ge=1, le=65535)
    database: str = Field(default='', max_length=128)
    username: str = Field(default='', max_length=128)
    password: str = Field(default='', max_length=1024, repr=False)
    schema_name: str = Field(default='', max_length=128)
    tables: list[str] = Field(default_factory=list, max_length=50)
    tls: bool = True
    read_only_confirmed: bool = False
    egress_confirmed: bool = False
    revision: int = Field(default=0, ge=0)


class ConnectionConfigurationError(ValueError):
    pass


class DatabaseProfilePayload(ConnectionSettings):
    name: str = Field(min_length=1, max_length=80)


class ConnectionConflict(ConnectionConfigurationError):
    pass


IDENTIFIER = re.compile(r'^[A-Za-z_][A-Za-z0-9_]{0,127}$')
SAFE_FUNCTIONS = {
    'ABS', 'AVG', 'COUNT', 'SUM', 'MIN', 'MAX', 'ROUND', 'CEIL', 'CEILING', 'FLOOR',
    'COALESCE', 'NULLIF', 'IF', 'CASE', 'CAST', 'TRY_CAST', 'LOWER', 'UPPER',
    'LENGTH', 'CHAR_LENGTH', 'TRIM', 'LTRIM', 'RTRIM', 'SUBSTRING', 'CONCAT',
    'EXTRACT', 'DATE', 'DATE_TRUNC', 'TIMESTAMP_TRUNC', 'YEAR', 'MONTH', 'DAY',
    'CURRENT_DATE', 'CURRENT_TIMESTAMP', 'ROW_NUMBER', 'RANK', 'DENSE_RANK',
    'LAG', 'LEAD', 'FIRST_VALUE', 'LAST_VALUE', 'STRFTIME', 'TIME_TO_STR',
}
DIALECTS = {'postgresql': 'postgres', 'mysql': 'mysql', 'mariadb': 'mysql',
            'mssql': 'tsql', 'oracle': 'oracle', 'sqlite': 'sqlite'}


def validate_settings(settings: ConnectionSettings, *, activating=False):
    if settings.kind == 'demo':
        return
    if not settings.read_only_confirmed or not settings.egress_confirmed:
        raise ConnectionConfigurationError('Confirm SELECT-only credentials and permission to send results to the AI provider.')
    if settings.kind == 'sqlite':
        if not re.fullmatch(r'[A-Za-z0-9_-]+\.(?:db|sqlite|sqlite3)', settings.database):
            raise ConnectionConfigurationError('SQLite requires a filename inside NEXUS_EXTERNAL_SQLITE_ROOT, not a path.')
    else:
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9.:-]*', settings.host):
            raise ConnectionConfigurationError('Enter a database hostname or IP, not a connection URL.')
        if not re.fullmatch(r'[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}', settings.database) or not settings.username.strip():
            raise ConnectionConfigurationError('Database/service name and username are required. Use letters, digits, dots, underscores or hyphens.')
        if not settings.tls and os.getenv('NEXUS_DB_ALLOW_INSECURE', '0') != '1':
            raise ConnectionConfigurationError('Verified TLS is required by this deployment.')
    if settings.schema_name and not IDENTIFIER.fullmatch(settings.schema_name):
        raise ConnectionConfigurationError('Use a simple schema identifier.')
    if any(not IDENTIFIER.fullmatch(table) for table in settings.tables):
        raise ConnectionConfigurationError('Use unqualified table names containing letters, digits and underscores.')
    if activating and not settings.tables:
        raise ConnectionConfigurationError('Select at least one reporting table before activating the source.')


def validated_query(sql: str, settings: ConnectionSettings) -> str:
    """Parse and re-render a deliberately small reporting SQL subset, fail closed."""
    if len(sql) > 20000 or re.search(r'--|/\*|\*/|\x00|@', sql):
        raise QueryRejected('SQL comments, variables and oversized statements are not supported.')
    try:
        statements = sqlglot.parse(sql, read=DIALECTS[settings.kind])
    except sqlglot.errors.SqlglotError:
        raise QueryRejected('SQL could not be parsed safely.') from None
    if len(statements) != 1 or not isinstance(statements[0], (exp.Select, exp.Union, exp.Intersect, exp.Except)):
        raise QueryRejected('Only one read-only SELECT/WITH reporting query is allowed.')
    tree = statements[0]
    denied = {'Insert', 'Update', 'Delete', 'Create', 'Drop', 'Alter', 'Command',
              'Into', 'Lock', 'Transaction', 'Copy', 'Merge', 'Execute', 'Grant',
              'Revoke', 'Use', 'Set', 'Pragma', 'TableSample', 'Pivot', 'Unpivot',
              'Parameter', 'SessionParameter', 'WithTableHint'}
    cte_references = set()
    try:
        for query_scope in traverse_scope(tree):
            for node, source in query_scope.selected_sources.values():
                if isinstance(source, Scope) and isinstance(node, exp.Table):
                    cte_references.add(id(node))
    except sqlglot.errors.SqlglotError:
        raise QueryRejected('SQL table scope could not be resolved safely.') from None
    scope = settings.schema_name or {'postgresql': 'public', 'mssql': 'dbo',
                                    'sqlite': 'main', 'oracle': settings.username.upper()}.get(settings.kind, settings.database)
    allowed = set(settings.tables)
    for node in tree.walk():
        if type(node).__name__ in denied:
            raise QueryRejected('SQL contains a non-reporting operation.')
        if isinstance(node, exp.Func):
            name = node.name.upper() if isinstance(node, exp.Anonymous) else node.sql_name()
            if name not in SAFE_FUNCTIONS:
                raise QueryRejected('This SQL function is outside the reporting allowlist.')
        if isinstance(node, exp.Dot) and isinstance(node.expression, exp.Func):
            raise QueryRejected('Schema-qualified functions are not permitted.')
        if isinstance(node, exp.Table):
            if not isinstance(node.this, exp.Identifier) or node.catalog:
                raise QueryRejected('Remote tables and table functions are not permitted.')
            if id(node) in cte_references and not node.db:
                continue
            if node.name not in allowed or (node.db and node.db != scope):
                raise QueryRejected('SQL references a table outside the configured reporting allowlist.')
            # Never depend on a mutable search_path/default schema for table resolution.
            node.set('db', exp.to_identifier(scope, quoted=True))
    if any(with_.args.get('recursive') for with_ in tree.find_all(exp.With)):
        raise QueryRejected('Recursive queries are not supported.')
    # Cap server output too, not only the Python fetch. Respect smaller user limits.
    limit = tree.args.get('limit')
    if limit:
        value = limit.expression
        if not isinstance(value, exp.Literal) or not value.is_int or limit.args.get('limit_options'):
            raise QueryRejected('Use a fixed numeric row limit.')
        tree = tree.limit(min(max(int(value.this), 0), 101))
    else:
        tree = tree.limit(101)
    return tree.sql(dialect=DIALECTS[settings.kind], comments=False)


class ExternalDatabase:
    fictional = False

    def __init__(self, settings: ConnectionSettings, schema_text='', *, sqlite_root: Path):
        self.settings = settings.model_copy(deep=True)
        self.schema_text = schema_text
        self.sqlite_root = sqlite_root
        self.label = f'{settings.kind}: {settings.database}'

    def schema_prompt(self):
        return f'SQL dialect: {DIALECTS[self.settings.kind]}. External data; do not assume currency or fictional values.\n{self.schema_text}'

    def engine(self):
        c = self.settings
        validate_settings(c)
        args = {}
        query = {}
        ca = os.getenv('NEXUS_DB_CA_FILE') or None
        if c.kind == 'sqlite':
            root = self.sqlite_root.resolve(strict=True)
            path = (root / c.database).resolve(strict=True)
            if not path.is_relative_to(root) or not path.is_file():
                raise ConnectionConfigurationError('SQLite file is outside the approved directory.')
            # read-only URI: never create, seed or chmod an external database.
            url = URL.create('sqlite+pysqlite', database=path.as_uri(), query={'mode': 'ro', 'uri': 'true'})
            args = {'timeout': 10}
        elif c.kind == 'postgresql':
            args = {'connect_timeout': 8, 'sslmode': 'verify-full' if c.tls else 'disable'}
            if ca:
                args['sslrootcert'] = ca
            url = URL.create('postgresql+psycopg', username=c.username, password=c.password,
                             host=c.host, port=c.port, database=c.database)
        elif c.kind in {'mysql', 'mariadb'}:
            args = {'connect_timeout': 8, 'read_timeout': 10, 'write_timeout': 10, 'local_infile': False}
            if c.tls:
                args['ssl'] = ssl.create_default_context(cafile=ca)
            url = URL.create('mysql+pymysql', username=c.username, password=c.password,
                             host=c.host, port=c.port, database=c.database)
        elif c.kind == 'mssql':
            query = {'driver': 'ODBC Driver 18 for SQL Server', 'Encrypt': 'yes' if c.tls else 'no',
                     'TrustServerCertificate': 'no', 'ApplicationIntent': 'ReadOnly'}
            args = {'timeout': 8}
            url = URL.create('mssql+pyodbc', username=c.username, password=c.password,
                             host=c.host, port=c.port, database=c.database, query=query)
        elif c.kind == 'oracle':
            args = {'tcp_connect_timeout': 8, 'protocol': 'tcps' if c.tls else 'tcp',
                    'ssl_server_dn_match': True}
            if c.tls:
                args['ssl_context'] = ssl.create_default_context(cafile=ca)
            url = URL.create('oracle+oracledb', username=c.username, password=c.password,
                             host=c.host, port=c.port, query={'service_name': c.database})
        else:
            raise ConnectionConfigurationError('Unsupported external database.')
        return create_engine(url, connect_args=args, poolclass=NullPool, hide_parameters=True)

    @contextmanager
    def connection(self):
        engine = None
        try:
            engine = self.engine()
            with engine.connect() as connection:
                kind = self.settings.kind
                if kind == 'postgresql':
                    connection.exec_driver_sql('SET TRANSACTION READ ONLY')
                    connection.exec_driver_sql('SET LOCAL statement_timeout = 10000')
                    connection.exec_driver_sql('SET LOCAL lock_timeout = 2000')
                    connection.exec_driver_sql('SET LOCAL search_path = pg_catalog')
                elif kind in {'mysql', 'mariadb'}:
                    connection.exec_driver_sql('SET SESSION TRANSACTION READ ONLY')
                    connection.exec_driver_sql('SET SESSION max_statement_time = 10' if kind == 'mariadb'
                                               else 'SET SESSION MAX_EXECUTION_TIME = 10000')
                elif kind == 'sqlite':
                    connection.exec_driver_sql('PRAGMA query_only = ON')
                    raw = connection.connection.driver_connection
                    started = time.monotonic()
                    raw.set_progress_handler(lambda: int(time.monotonic() - started > 10), 1000)
                elif kind == 'mssql':
                    connection.connection.driver_connection.timeout = 10
                    connection.exec_driver_sql('SET LOCK_TIMEOUT 2000')
                elif kind == 'oracle':
                    connection.connection.driver_connection.call_timeout = 10000
                    connection.exec_driver_sql('SET TRANSACTION READ ONLY')
                yield connection
                connection.rollback()
        except (ConnectionConfigurationError, QueryRejected):
            raise
        except Exception:
            # Never return driver exceptions (DSNs, usernames, SQL/data or passwords).
            raise QueryRejected('Database operation failed. Check driver, network, TLS certificate, SELECT grants, schema and timeout.') from None
        finally:
            if engine is not None:
                engine.dispose()

    def inspect_schema(self):
        with self.connection() as connection:
            inspector = inspect(connection)
            schema = self.settings.schema_name or {'postgresql': 'public', 'mssql': 'dbo',
                'sqlite': 'main', 'oracle': self.settings.username.upper()}.get(self.settings.kind, self.settings.database)
            names = sorted(set(inspector.get_table_names(schema=schema) + inspector.get_view_names(schema=schema)))
            eligible = [name for name in names if IDENTIFIER.fullmatch(name)]
            if not set(self.settings.tables).issubset(eligible):
                raise ConnectionConfigurationError('A selected table is missing or inaccessible in this schema.')
            lines = []
            for name in self.settings.tables:
                columns = inspector.get_columns(name, schema=schema)
                if len(columns) > 128:
                    raise ConnectionConfigurationError('Use reporting views with at most 128 columns.')
                lines.append(f'{name}(' + ', '.join(f'{column["name"]} {str(column["type"])[:100]}' for column in columns) + ')')
                if sum(map(len, lines)) > 32000:
                    raise ConnectionConfigurationError('Selected schema is too large. Select fewer reporting views.')
            return {'tables': eligible[:500], 'tables_truncated': len(eligible) > 500,
                    'schema': '\n'.join(lines)}

    def execute(self, sql, **kwargs):
        statement = validated_query(sql, self.settings)
        started = time.monotonic()
        with self.connection() as connection:
            result = connection.execution_options(stream_results=True, max_row_buffer=101).exec_driver_sql(statement)
            columns = list(result.keys())
            if len(columns) > 64 or len(set(columns)) != len(columns):
                raise QueryRejected('Use at most 64 uniquely named result columns.')
            fetched = result.fetchmany(101)
            rows, truncated = [], False
            budget = 64000
            for row in fetched[:100]:
                if budget <= 0:
                    break
                safe = {}
                for key, value in zip(columns, row):
                    if hasattr(value, 'read'):  # Oracle LOB: bounded read, never materialize it all.
                        value = value.read(1, 8001)
                    if isinstance(value, bytes):
                        value = value[:4001].hex()
                    if value is not None and not isinstance(value, (str, int, float, bool)):
                        value = str(value)
                    if isinstance(value, str) and len(value) > 8000:
                        value, truncated = value[:8000] + '…', True
                    size = len(str(value)) + len(key)
                    if size > budget:
                        value, truncated = str(value)[:max(0, budget - len(key))] + '…', True
                    budget -= min(size, max(0, budget))
                    safe[key] = value
                rows.append(safe)
            result.close()
        return {'columns': columns, 'rows': rows, 'row_count': len(rows),
                'truncated': len(fetched) > len(rows), 'cells_truncated': truncated,
                'elapsed_ms': round((time.monotonic() - started) * 1000, 1),
                'executed_sql': statement}


class DatabaseConnections:
    def __init__(self, path: Path, demo, *, sqlite_root: Path):
        self.path, self.demo, self.sqlite_root = path, demo, sqlite_root
        self.lock = RLock()
        self.bound_count = lambda connection_id: 0

    def _read(self):
        if not self.path.exists():
            return {'settings': ConnectionSettings().model_dump(), 'schema': ''}
        try:
            return json.loads(self.path.read_text(encoding='utf-8'))
        except Exception:
            raise ConnectionConfigurationError('Database source configuration cannot be read. Restore its protected backup.') from None

    def public(self):
        with self.lock:
            settings = ConnectionSettings(**self._read()['settings'])
        return {**settings.model_dump(exclude={'password'}), 'password_configured': bool(settings.password)}

    def draft(self, payload):
        current = ConnectionSettings(**self._read()['settings'])
        draft = payload.model_copy(deep=True)
        if draft.revision != current.revision:
            raise ConnectionConflict('Database settings changed. Reload administration before saving.')
        identity = ('kind', 'host', 'port', 'database', 'username')
        if not draft.password and all(getattr(draft, key) == getattr(current, key) for key in identity):
            draft.password = current.password
        if draft.kind not in {'demo', 'sqlite'} and not draft.password:
            raise ConnectionConfigurationError('Enter a password for this database endpoint.')
        validate_settings(draft)
        return draft

    def test(self, payload):
        with self.lock:
            draft = self.draft(payload)
        if draft.kind == 'demo':
            return {'tables': [], 'schema': self.demo.schema_prompt(), 'tables_truncated': False}
        return ExternalDatabase(draft, sqlite_root=self.sqlite_root).inspect_schema()

    def save(self, payload):
        with self.lock:
            draft = self.draft(payload)
        validate_settings(draft, activating=True)
        metadata = self.test(payload)
        with self.lock:
            self.draft(payload)  # Optimistic concurrency check after network work.
            document = self._read()
            self._check_endpoint('legacy', ConnectionSettings(**document['settings']), draft)
            draft.revision += 1
            if draft.kind == 'demo':
                draft = ConnectionSettings(revision=draft.revision)
            document.update(settings=draft.model_dump(), schema=metadata['schema'])
            self._write(document)
        return self.public()

    def _write(self, document):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(prefix='.db-source-', dir=self.path.parent)
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as stream:
                json.dump(document, stream)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.path)
        finally:
            Path(temporary).unlink(missing_ok=True)

    def default_id(self):
        return 'demo' if self.public()['kind'] == 'demo' else 'legacy'

    def _check_endpoint(self, connection_id, current, draft):
        if self.bound_count(connection_id) and any(
            getattr(current, key) != getattr(draft, key) for key in ('kind', 'host', 'port', 'database', 'schema_name')
        ):
            raise ConnectionConflict('Existing chats use this endpoint. Create a new connection for a different database; credentials and table permissions can still be updated.')

    @staticmethod
    def _public_profile(connection_id, document):
        settings = ConnectionSettings(**document['settings'])
        return {**settings.model_dump(exclude={'password'}), 'id': connection_id,
                'name': document['name'], 'schema': document['schema'], 'password_configured': bool(settings.password)}

    def profiles(self):
        with self.lock:
            return [self._public_profile(key, value) for key, value in self._read().get('profiles', {}).items()]

    def choices(self, *, admin):
        choices = [{'id': 'demo', 'name': 'Demo — Synthetic Business DB', 'kind': 'demo'}]
        if admin:
            current = self.public()
            if current['kind'] != 'demo':
                choices.append({'id': 'legacy', 'name': f'Default — {current["database"]}', 'kind': current['kind']})
            choices.extend({'id': p['id'], 'name': p['name'], 'kind': p['kind']} for p in self.profiles())
        return choices

    def _profile_draft(self, payload, connection_id):
        document = self._read()
        profile = document.get('profiles', {}).get(connection_id) if connection_id else None
        if connection_id and not profile:
            raise ConnectionConfigurationError('Database connection no longer exists.')
        current = ConnectionSettings(**profile['settings']) if profile else ConnectionSettings()
        draft = ConnectionSettings(**payload.model_dump(exclude={'name'}))
        if draft.revision != current.revision:
            raise ConnectionConflict('Database connection changed. Reload it before saving.')
        if not draft.password and all(getattr(draft, key) == getattr(current, key)
                                     for key in ('kind', 'host', 'port', 'database', 'username')):
            draft.password = current.password
        if draft.kind == 'demo':
            raise ConnectionConfigurationError('Demo is built in. Choose an external database type for a saved connection.')
        if draft.kind != 'sqlite' and not draft.password:
            raise ConnectionConfigurationError('Enter a password for this database endpoint.')
        validate_settings(draft)
        if connection_id:
            self._check_endpoint(connection_id, current, draft)
        return draft

    def test_profile(self, payload, connection_id=None):
        with self.lock:
            draft = self._profile_draft(payload, connection_id)
        return ExternalDatabase(draft, sqlite_root=self.sqlite_root).inspect_schema()

    def save_profile(self, payload, connection_id=None):
        with self.lock:
            draft = self._profile_draft(payload, connection_id)
        validate_settings(draft, activating=True)
        metadata = ExternalDatabase(draft, sqlite_root=self.sqlite_root).inspect_schema()
        with self.lock:
            self._profile_draft(payload, connection_id)
            document = self._read()
            profiles = document.setdefault('profiles', {})
            if not connection_id and len(profiles) >= 20:
                raise ConnectionConfigurationError('Maximum 20 saved database connections.')
            connection_id = connection_id or uuid.uuid4().hex
            if not payload.name.strip():
                raise ConnectionConfigurationError('A connection name is required.')
            if any(p['name'].casefold() == payload.name.strip().casefold() for key, p in profiles.items() if key != connection_id):
                raise ConnectionConflict('A connection with this name already exists.')
            draft.revision += 1
            profiles[connection_id] = {'name': payload.name.strip(), 'settings': draft.model_dump(), 'schema': metadata['schema']}
            self._write(document)
            return self._public_profile(connection_id, profiles[connection_id])

    def delete_profile(self, connection_id, revision):
        with self.lock:
            document = self._read()
            profile = document.get('profiles', {}).get(connection_id)
            if not profile:
                raise ConnectionConfigurationError('Database connection no longer exists.')
            if profile['settings']['revision'] != revision or self.bound_count(connection_id):
                raise ConnectionConflict('Connection changed or is still used by chats. Retain it or remove those chats first.')
            del document['profiles'][connection_id]
            self._write(document)

    def snapshot(self, connection_id=None):
        with self.lock:
            document = self._read()
            if connection_id == 'demo':
                return self.demo
            if connection_id not in (None, 'legacy'):
                document = document.get('profiles', {}).get(connection_id)
                if not document:
                    raise ConnectionConfigurationError('Database connection is unavailable. No fallback source was used.')
            settings = ConnectionSettings(**document['settings'])
        if settings.kind == 'demo':
            if connection_id == 'legacy':
                raise ConnectionConfigurationError('The previous default database is unavailable. Start a new chat to select a source.')
            return self.demo
        validate_settings(settings, activating=True)
        source = ExternalDatabase(settings, document['schema'], sqlite_root=self.sqlite_root)
        if document.get('name'):
            source.label = f'{document["name"]} ({source.label})'
        return source
