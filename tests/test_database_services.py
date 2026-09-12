"""Real driver tests, opt-in ONLY for disposable CI databases configured below."""
import os
from pathlib import Path

import pytest
from sqlalchemy import URL, create_engine

from nexus.database_connection import ConnectionSettings, ExternalDatabase


@pytest.mark.skipif(os.getenv('NEXUS_DB_INTEGRATION') != 'disposable-ci', reason='Requires disposable database services')
@pytest.mark.parametrize('kind,port', [('postgresql', 5432), ('mysql', 3306), ('mariadb', 3307)])
def test_real_reporting_driver_and_native_read_only_transaction(kind, port, monkeypatch):
    monkeypatch.setenv('NEXUS_DB_ALLOW_INSECURE', '1')
    driver = 'postgresql+psycopg' if kind == 'postgresql' else 'mysql+pymysql'
    owner = 'postgres' if kind == 'postgresql' else 'root'
    engine = create_engine(URL.create(driver, username=owner, password='ci-owner-only',
                                      host='127.0.0.1', port=port, database='reporting'))
    with engine.connect().execution_options(isolation_level='AUTOCOMMIT') as connection:
        connection.exec_driver_sql('CREATE TABLE revenue (country VARCHAR(10), amount INTEGER)')
        connection.exec_driver_sql("INSERT INTO revenue VALUES ('SK', 120), ('DE', 240)")
        if kind == 'postgresql':
            connection.exec_driver_sql("CREATE USER nexus_reader PASSWORD 'ci-reader-only'")
            connection.exec_driver_sql('GRANT USAGE ON SCHEMA public TO nexus_reader')
            connection.exec_driver_sql('GRANT SELECT ON public.revenue TO nexus_reader')
        else:
            connection.exec_driver_sql("CREATE USER 'nexus_reader'@'%%' IDENTIFIED BY 'ci-reader-only'")
            connection.exec_driver_sql("GRANT SELECT ON reporting.revenue TO 'nexus_reader'@'%%'")
    engine.dispose()
    settings = ConnectionSettings(kind=kind, host='127.0.0.1', port=port,
        database='reporting', username='nexus_reader', password='ci-reader-only',
        tables=['revenue'], tls=False, read_only_confirmed=True, egress_confirmed=True)
    source = ExternalDatabase(settings, sqlite_root=Path('.'))
    assert 'revenue' in source.inspect_schema()['tables']
    result = source.execute('SELECT SUM(amount) AS total FROM revenue')
    assert float(result['rows'][0]['total']) == 360
    # Bypass our parser deliberately: the actual DB session/grants must still deny writes.
    from nexus.data_agent import QueryRejected
    with pytest.raises(QueryRejected):
        with source.connection() as connection:
            connection.exec_driver_sql('DELETE FROM revenue')
    assert source.execute('SELECT COUNT(*) AS n FROM revenue')['rows'][0]['n'] == 2
