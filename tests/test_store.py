import sqlite3

from nexus.store import Store


def test_legacy_mixed_conversation_is_split_without_losing_messages(tmp_path):
    database_path = tmp_path / "legacy.sqlite3"
    with sqlite3.connect(database_path) as db:
        db.executescript(
            """
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE COLLATE NOCASE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user',
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                last_login_at TEXT
            );
            CREATE TABLE conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                model TEXT,
                input_tokens INTEGER NOT NULL DEFAULT 0,
                output_tokens INTEGER NOT NULL DEFAULT 0,
                sources_json TEXT NOT NULL DEFAULT '[]',
                agent_mode TEXT NOT NULL DEFAULT 'general',
                created_at TEXT NOT NULL
            );
            INSERT INTO users
                (id, name, email, password_hash, role, is_active, created_at)
            VALUES
                (1, 'Legacy', 'legacy@example.test', 'hash', 'user', 1,
                 '2026-07-20T10:00:00+00:00');
            INSERT INTO conversations
                (id, user_id, title, created_at, updated_at)
            VALUES
                (1, 1, 'Mixed chat', '2026-07-20T10:00:00+00:00',
                 '2026-07-20T10:05:00+00:00');
            INSERT INTO messages
                (conversation_id, role, content, agent_mode, created_at)
            VALUES
                (1, 'user', 'Nexus question', 'general',
                 '2026-07-20T10:01:00+00:00'),
                (1, 'assistant', 'Nexus answer', 'general',
                 '2026-07-20T10:02:00+00:00'),
                (1, 'user', 'Infra question', 'infra',
                 '2026-07-20T10:03:00+00:00'),
                (1, 'assistant', 'Infra answer', 'infra',
                 '2026-07-20T10:04:00+00:00'),
                (1, 'user', 'Data question', 'data',
                 '2026-07-20T10:05:00+00:00'),
                (1, 'assistant', 'Data answer', 'data',
                 '2026-07-20T10:06:00+00:00');
            """
        )

    store = Store(str(database_path))

    histories = {
        mode: store.list_conversations(1, mode)
        for mode in ("general", "infra", "data")
    }
    assert all(len(items) == 1 for items in histories.values())
    assert {
        mode: histories[mode][0]["agent_mode"]
        for mode in histories
    } == {"general": "general", "infra": "infra", "data": "data"}

    contents_by_mode = {
        mode: [
            message["content"]
            for message in store.get_conversation(
                histories[mode][0]["id"], 1
            )["messages"]
        ]
        for mode in histories
    }
    assert contents_by_mode == {
        "general": ["Nexus question", "Nexus answer"],
        "infra": ["Infra question", "Infra answer"],
        "data": ["Data question", "Data answer"],
    }
    assert sum(len(messages) for messages in contents_by_mode.values()) == 6
