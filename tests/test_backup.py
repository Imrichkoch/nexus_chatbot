import sqlite3

import pytest

from nexus.backup import copy_database
from nexus.store import Store


def test_backup_restore_preserves_data_and_revokes_copied_sessions(tmp_path):
    source = tmp_path / 'source.sqlite3'
    store = Store(str(source))
    user = store.create_local_user(name='Backup user', password='StrongPassword2026')
    token = store.create_session(user['id'])
    store.create_rag_documents([('knowledge.md', 'Business knowledge for restore.')])
    backup = copy_database(source, tmp_path / 'backup.sqlite3')
    restored = copy_database(backup, tmp_path / 'restored.sqlite3', revoke_sessions=True)
    recovered = Store(str(restored))
    assert recovered.get_user(user['id'])['name'] == 'Backup user'
    assert recovered.search_rag('Business knowledge', 6)
    assert recovered.user_for_session(token) is None
    assert store.user_for_session(token) is not None
    with pytest.raises(FileExistsError):
        copy_database(source, restored)
