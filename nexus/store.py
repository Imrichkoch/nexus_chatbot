from __future__ import annotations

import hashlib
import json
import os
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterator

import bcrypt

from nexus.rag import chunk_text, fts_query


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def public_user(row: sqlite3.Row | dict[str, Any]) -> dict[str, Any]:
    username = row["username"] if "username" in row.keys() else None
    stored_email = row["email"]
    return {
        "id": row["id"],
        "name": row["name"],
        "username": username,
        "email": None if stored_email.endswith("@nexus.invalid") else stored_email,
        "role": row["role"],
        "is_active": bool(row["is_active"]),
        "created_at": row["created_at"],
        "last_login_at": row["last_login_at"],
    }


class Store:
    def __init__(self, database_path: str):
        self.database_path = database_path
        if database_path != ":memory:":
            Path(database_path).parent.mkdir(parents=True, exist_ok=True)
        self._memory_connection: sqlite3.Connection | None = None
        if database_path == ":memory:":
            self._memory_connection = self._new_connection()
        self.init_schema()

    def _new_connection(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            self.database_path,
            timeout=10,
            check_same_thread=False,
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        return connection

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        if self._memory_connection is not None:
            yield self._memory_connection
            self._memory_connection.commit()
            return
        connection = self._new_connection()
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def init_schema(self) -> None:
        with self.connection() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    username TEXT COLLATE NOCASE,
                    email TEXT NOT NULL UNIQUE COLLATE NOCASE,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'user'
                        CHECK (role IN ('user', 'admin')),
                    is_active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    last_login_at TEXT
                );

                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    token_hash TEXT NOT NULL UNIQUE,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    title TEXT NOT NULL,
                    agent_mode TEXT NOT NULL DEFAULT 'general'
                        CHECK (agent_mode IN ('general', 'infra', 'data')),
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id INTEGER NOT NULL
                        REFERENCES conversations(id) ON DELETE CASCADE,
                    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
                    content TEXT NOT NULL,
                    model TEXT,
                    input_tokens INTEGER NOT NULL DEFAULT 0,
                    output_tokens INTEGER NOT NULL DEFAULT 0,
                    sources_json TEXT NOT NULL DEFAULT '[]',
                    agent_mode TEXT NOT NULL DEFAULT 'general',
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    actor_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
                    action TEXT NOT NULL,
                    target TEXT,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS rag_documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    character_count INTEGER NOT NULL,
                    chunk_count INTEGER NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS rag_chunks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    document_id INTEGER NOT NULL
                        REFERENCES rag_documents(id) ON DELETE CASCADE,
                    chunk_index INTEGER NOT NULL,
                    content TEXT NOT NULL
                );

                CREATE VIRTUAL TABLE IF NOT EXISTS rag_chunks_fts USING fts5(
                    content,
                    content='rag_chunks',
                    content_rowid='id',
                    tokenize='unicode61 remove_diacritics 2'
                );

                CREATE INDEX IF NOT EXISTS idx_sessions_token
                    ON sessions(token_hash);
                CREATE INDEX IF NOT EXISTS idx_conversations_user
                    ON conversations(user_id, updated_at DESC);
                CREATE INDEX IF NOT EXISTS idx_messages_conversation
                    ON messages(conversation_id, id);
                """
            )
            user_columns = {
                row["name"] for row in db.execute("PRAGMA table_info(users)").fetchall()
            }
            if "username" not in user_columns:
                db.execute("ALTER TABLE users ADD COLUMN username TEXT COLLATE NOCASE")
            db.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_users_username_nocase "
                "ON users(username COLLATE NOCASE) WHERE username IS NOT NULL"
            )
            message_columns = {
                row["name"] for row in db.execute("PRAGMA table_info(messages)").fetchall()
            }
            if "sources_json" not in message_columns:
                db.execute(
                    "ALTER TABLE messages ADD COLUMN sources_json TEXT NOT NULL DEFAULT '[]'"
                )
            if "agent_mode" not in message_columns:
                db.execute(
                    "ALTER TABLE messages ADD COLUMN agent_mode TEXT NOT NULL DEFAULT 'general'"
                )
            conversation_columns = {
                row["name"]
                for row in db.execute("PRAGMA table_info(conversations)").fetchall()
            }
            if "agent_mode" not in conversation_columns:
                db.execute(
                    "ALTER TABLE conversations "
                    "ADD COLUMN agent_mode TEXT NOT NULL DEFAULT 'general'"
                )
                self._split_legacy_conversations(db)
            db.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_conversations_user_agent
                ON conversations(user_id, agent_mode, updated_at DESC)
                """
            )
            defaults = {
                "model": os.getenv("NEXUS_DEFAULT_MODEL", "gpt-5.6-luna"),
                "system_prompt": (
                    "Si Nexus, presný a praktický AI asistent. Odpovedaj v jazyku "
                    "používateľa, jasne oddeľ fakty od odhadov a nevymýšľaj si zdroje."
                ),
                "rag_enabled": "0",
                "rag_max_chunks": "4",
                "infra_agent_enabled": "0",
                "infra_agent_admin_only": "1",
                "infra_live_enabled": "1",
                "infra_model": os.getenv(
                    "NEXUS_INFRA_MODEL",
                    os.getenv("NEXUS_DEFAULT_MODEL", "gpt-5.6-luna"),
                ),
                "data_agent_enabled": "1",
                "data_agent_admin_only": "0",
                "data_model": os.getenv(
                    "NEXUS_DATA_MODEL",
                    os.getenv("NEXUS_DEFAULT_MODEL", "gpt-5.6-luna"),
                ),
            }
            for key, value in defaults.items():
                db.execute(
                    """
                    INSERT OR IGNORE INTO settings (key, value, updated_at)
                    VALUES (?, ?, ?)
                    """,
                    (key, value, utc_now()),
                )

    @staticmethod
    def _split_legacy_conversations(db: sqlite3.Connection) -> None:
        """Split old mixed conversations into one conversation per agent."""
        valid_modes = ("general", "infra", "data")
        db.execute(
            """
            UPDATE messages
            SET agent_mode = 'general'
            WHERE agent_mode IS NULL
               OR agent_mode NOT IN ('general', 'infra', 'data')
            """
        )
        conversations = db.execute(
            """
            SELECT id, user_id, title, created_at, updated_at
            FROM conversations
            ORDER BY id
            """
        ).fetchall()
        for conversation in conversations:
            mode_rows = db.execute(
                """
                SELECT agent_mode, MIN(id) AS first_message_id,
                       MIN(created_at) AS first_message_at,
                       MAX(created_at) AS last_message_at
                FROM messages
                WHERE conversation_id = ?
                GROUP BY agent_mode
                ORDER BY first_message_id
                """,
                (conversation["id"],),
            ).fetchall()
            if not mode_rows:
                continue

            modes = {row["agent_mode"]: row for row in mode_rows}
            primary_mode = (
                "general" if "general" in modes else mode_rows[0]["agent_mode"]
            )
            primary = modes[primary_mode]
            db.execute(
                """
                UPDATE conversations
                SET agent_mode = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    primary_mode,
                    primary["last_message_at"] or conversation["updated_at"],
                    conversation["id"],
                ),
            )

            for mode in valid_modes:
                if mode == primary_mode or mode not in modes:
                    continue
                mode_row = modes[mode]
                cursor = db.execute(
                    """
                    INSERT INTO conversations
                        (user_id, title, agent_mode, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        conversation["user_id"],
                        f"{conversation['title']} / {mode.upper()}",
                        mode,
                        mode_row["first_message_at"] or conversation["created_at"],
                        mode_row["last_message_at"] or conversation["updated_at"],
                    ),
                )
                db.execute(
                    """
                    UPDATE messages
                    SET conversation_id = ?
                    WHERE conversation_id = ? AND agent_mode = ?
                    """,
                    (cursor.lastrowid, conversation["id"], mode),
                )

    def create_user(
        self,
        *,
        name: str,
        username: str | None = None,
        email: str,
        password: str,
        role: str = "user",
    ) -> dict[str, Any]:
        password_hash = bcrypt.hashpw(
            password.encode("utf-8"), bcrypt.gensalt(rounds=12)
        ).decode("ascii")
        now = utc_now()
        with self.connection() as db:
            cursor = db.execute(
                """
                INSERT INTO users
                    (name, username, email, password_hash, role, is_active, created_at)
                VALUES (?, ?, ?, ?, ?, 1, ?)
                """,
                (
                    name.strip(),
                    username.strip() if username else None,
                    email.strip().lower(),
                    password_hash,
                    role,
                    now,
                ),
            )
            row = db.execute(
                "SELECT * FROM users WHERE id = ?", (cursor.lastrowid,)
            ).fetchone()
        return public_user(row)

    def create_local_user(
        self,
        *,
        name: str,
        password: str,
        role: str = "user",
    ) -> dict[str, Any]:
        clean_name = name.strip()
        return self.create_user(
            name=clean_name,
            username=clean_name,
            email=f"local-{secrets.token_hex(16)}@nexus.invalid",
            password=password,
            role=role,
        )

    def get_user_by_email(self, email: str) -> dict[str, Any] | None:
        with self.connection() as db:
            row = db.execute(
                "SELECT * FROM users WHERE email = ? COLLATE NOCASE",
                (email.strip(),),
            ).fetchone()
        return dict(row) if row else None

    def get_user_by_identifier(self, identifier: str) -> dict[str, Any] | None:
        with self.connection() as db:
            row = db.execute(
                """
                SELECT * FROM users
                WHERE email = ? COLLATE NOCASE
                   OR username = ? COLLATE NOCASE
                """,
                (identifier.strip(), identifier.strip()),
            ).fetchone()
        return dict(row) if row else None

    def get_user(self, user_id: int) -> dict[str, Any] | None:
        with self.connection() as db:
            row = db.execute(
                "SELECT * FROM users WHERE id = ?", (user_id,)
            ).fetchone()
        return public_user(row) if row else None

    def verify_password(self, user: dict[str, Any], password: str) -> bool:
        return bcrypt.checkpw(
            password.encode("utf-8"), user["password_hash"].encode("ascii")
        )

    def create_session(self, user_id: int, days: int = 7) -> str:
        token = secrets.token_urlsafe(40)
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        now = datetime.now(timezone.utc)
        expires = now + timedelta(days=days)
        with self.connection() as db:
            db.execute("DELETE FROM sessions WHERE expires_at < ?", (utc_now(),))
            db.execute(
                """
                INSERT INTO sessions (user_id, token_hash, created_at, expires_at)
                VALUES (?, ?, ?, ?)
                """,
                (
                    user_id,
                    token_hash,
                    now.isoformat(timespec="seconds"),
                    expires.isoformat(timespec="seconds"),
                ),
            )
            db.execute(
                "UPDATE users SET last_login_at = ? WHERE id = ?",
                (now.isoformat(timespec="seconds"), user_id),
            )
        return token

    def user_for_session(self, token: str | None) -> dict[str, Any] | None:
        if not token:
            return None
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        with self.connection() as db:
            row = db.execute(
                """
                SELECT users.*
                FROM sessions
                JOIN users ON users.id = sessions.user_id
                WHERE sessions.token_hash = ?
                  AND sessions.expires_at >= ?
                  AND users.is_active = 1
                """,
                (token_hash, utc_now()),
            ).fetchone()
        return public_user(row) if row else None

    def delete_session(self, token: str | None) -> None:
        if not token:
            return
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        with self.connection() as db:
            db.execute("DELETE FROM sessions WHERE token_hash = ?", (token_hash,))

    def list_users(self) -> list[dict[str, Any]]:
        with self.connection() as db:
            rows = db.execute(
                "SELECT * FROM users ORDER BY created_at DESC, id DESC"
            ).fetchall()
        return [public_user(row) for row in rows]

    def update_user(
        self,
        user_id: int,
        *,
        role: str | None = None,
        is_active: bool | None = None,
    ) -> dict[str, Any] | None:
        fields: list[str] = []
        values: list[Any] = []
        if role is not None:
            fields.append("role = ?")
            values.append(role)
        if is_active is not None:
            fields.append("is_active = ?")
            values.append(1 if is_active else 0)
        if fields:
            values.append(user_id)
            with self.connection() as db:
                db.execute(
                    f"UPDATE users SET {', '.join(fields)} WHERE id = ?",
                    tuple(values),
                )
        return self.get_user(user_id)

    def create_conversation(
        self,
        user_id: int,
        title: str,
        agent_mode: str = "general",
    ) -> dict[str, Any]:
        now = utc_now()
        with self.connection() as db:
            cursor = db.execute(
                """
                INSERT INTO conversations
                    (user_id, title, agent_mode, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (user_id, title, agent_mode, now, now),
            )
            row = db.execute(
                "SELECT * FROM conversations WHERE id = ?", (cursor.lastrowid,)
            ).fetchone()
        return dict(row)

    def list_conversations(
        self,
        user_id: int,
        agent_mode: str = "general",
    ) -> list[dict[str, Any]]:
        with self.connection() as db:
            rows = db.execute(
                """
                SELECT conversations.*,
                    (SELECT COUNT(*) FROM messages
                     WHERE messages.conversation_id = conversations.id)
                    AS message_count
                FROM conversations
                WHERE user_id = ? AND agent_mode = ?
                ORDER BY updated_at DESC, id DESC
                """,
                (user_id, agent_mode),
            ).fetchall()
        return [dict(row) for row in rows]

    def get_conversation(
        self, conversation_id: int, user_id: int
    ) -> dict[str, Any] | None:
        with self.connection() as db:
            conversation = db.execute(
                """
                SELECT * FROM conversations
                WHERE id = ? AND user_id = ?
                """,
                (conversation_id, user_id),
            ).fetchone()
            if not conversation:
                return None
            messages = db.execute(
                """
                SELECT id, role, content, model, input_tokens, output_tokens,
                       sources_json, agent_mode, created_at
                FROM messages
                WHERE conversation_id = ?
                ORDER BY id
                """,
                (conversation_id,),
            ).fetchall()
        result = dict(conversation)
        result["messages"] = [self._public_message(message) for message in messages]
        return result

    def delete_conversation(self, conversation_id: int, user_id: int) -> bool:
        with self.connection() as db:
            cursor = db.execute(
                "DELETE FROM conversations WHERE id = ? AND user_id = ?",
                (conversation_id, user_id),
            )
        return cursor.rowcount > 0

    def add_message(
        self,
        conversation_id: int,
        *,
        role: str,
        content: str,
        model: str | None = None,
        input_tokens: int = 0,
        output_tokens: int = 0,
        sources: list[dict[str, Any]] | None = None,
        agent_mode: str = "general",
    ) -> dict[str, Any]:
        now = utc_now()
        with self.connection() as db:
            cursor = db.execute(
                """
                INSERT INTO messages
                    (conversation_id, role, content, model,
                     input_tokens, output_tokens, sources_json, agent_mode, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    conversation_id,
                    role,
                    content,
                    model,
                    input_tokens,
                    output_tokens,
                    json.dumps(sources or [], ensure_ascii=False),
                    agent_mode,
                    now,
                ),
            )
            db.execute(
                "UPDATE conversations SET updated_at = ? WHERE id = ?",
                (now, conversation_id),
            )
            row = db.execute(
                """
                SELECT id, role, content, model, input_tokens, output_tokens,
                       sources_json, agent_mode, created_at
                FROM messages WHERE id = ?
                """,
                (cursor.lastrowid,),
            ).fetchone()
        return self._public_message(row)

    def add_exchange(
        self,
        conversation_id: int,
        *,
        user_content: str,
        assistant_content: str,
        model: str | None = None,
        input_tokens: int = 0,
        output_tokens: int = 0,
        sources: list[dict[str, Any]] | None = None,
        agent_mode: str = "general",
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Persist one complete user/assistant turn in a single transaction."""
        now = utc_now()
        with self.connection() as db:
            user_cursor = db.execute(
                """
                INSERT INTO messages
                    (conversation_id, role, content, model,
                     input_tokens, output_tokens, sources_json, agent_mode, created_at)
                VALUES (?, 'user', ?, NULL, 0, 0, '[]', ?, ?)
                """,
                (conversation_id, user_content, agent_mode, now),
            )
            assistant_cursor = db.execute(
                """
                INSERT INTO messages
                    (conversation_id, role, content, model,
                     input_tokens, output_tokens, sources_json, agent_mode, created_at)
                VALUES (?, 'assistant', ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    conversation_id,
                    assistant_content,
                    model,
                    input_tokens,
                    output_tokens,
                    json.dumps(sources or [], ensure_ascii=False),
                    agent_mode,
                    now,
                ),
            )
            db.execute(
                "UPDATE conversations SET updated_at = ? WHERE id = ?",
                (now, conversation_id),
            )
            rows = db.execute(
                """
                SELECT id, role, content, model, input_tokens, output_tokens,
                       sources_json, agent_mode, created_at
                FROM messages
                WHERE id IN (?, ?)
                ORDER BY id
                """,
                (user_cursor.lastrowid, assistant_cursor.lastrowid),
            ).fetchall()
        return self._public_message(rows[0]), self._public_message(rows[1])

    @staticmethod
    def _public_message(row: sqlite3.Row | dict[str, Any]) -> dict[str, Any]:
        message = dict(row)
        message["sources"] = json.loads(message.pop("sources_json", "[]") or "[]")
        return message

    def create_rag_document(self, name: str, content: str) -> dict[str, Any]:
        chunks = chunk_text(content)
        now = utc_now()
        with self.connection() as db:
            cursor = db.execute(
                """
                INSERT INTO rag_documents
                    (name, character_count, chunk_count, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (name, len(content), len(chunks), now),
            )
            document_id = int(cursor.lastrowid)
            for index, chunk in enumerate(chunks, start=1):
                chunk_cursor = db.execute(
                    """
                    INSERT INTO rag_chunks (document_id, chunk_index, content)
                    VALUES (?, ?, ?)
                    """,
                    (document_id, index, chunk),
                )
                db.execute(
                    "INSERT INTO rag_chunks_fts(rowid, content) VALUES (?, ?)",
                    (chunk_cursor.lastrowid, chunk),
                )
            row = db.execute(
                "SELECT * FROM rag_documents WHERE id = ?", (document_id,)
            ).fetchone()
        return dict(row)

    def list_rag_documents(self) -> list[dict[str, Any]]:
        with self.connection() as db:
            rows = db.execute(
                "SELECT * FROM rag_documents ORDER BY created_at DESC, id DESC"
            ).fetchall()
        return [dict(row) for row in rows]

    def delete_rag_document(self, document_id: int) -> bool:
        with self.connection() as db:
            chunk_ids = [
                row["id"]
                for row in db.execute(
                    "SELECT id FROM rag_chunks WHERE document_id = ?", (document_id,)
                ).fetchall()
            ]
            for chunk_id in chunk_ids:
                db.execute(
                    "INSERT INTO rag_chunks_fts(rag_chunks_fts, rowid, content) "
                    "VALUES ('delete', ?, (SELECT content FROM rag_chunks WHERE id = ?))",
                    (chunk_id, chunk_id),
                )
            cursor = db.execute(
                "DELETE FROM rag_documents WHERE id = ?", (document_id,)
            )
        return cursor.rowcount > 0

    def search_rag(self, query: str, limit: int) -> list[dict[str, Any]]:
        match = fts_query(query)
        if not match:
            return []
        with self.connection() as db:
            rows = db.execute(
                """
                SELECT d.name AS document, c.chunk_index, c.content,
                       bm25(rag_chunks_fts) AS score
                FROM rag_chunks_fts
                JOIN rag_chunks c ON c.id = rag_chunks_fts.rowid
                JOIN rag_documents d ON d.id = c.document_id
                WHERE rag_chunks_fts MATCH ?
                ORDER BY score
                LIMIT ?
                """,
                (match, max(1, min(limit, 12))),
            ).fetchall()
        return [dict(row) for row in rows]

    def get_settings(self) -> dict[str, str]:
        with self.connection() as db:
            rows = db.execute("SELECT key, value FROM settings").fetchall()
        return {row["key"]: row["value"] for row in rows}

    def update_settings(self, values: dict[str, str]) -> dict[str, str]:
        with self.connection() as db:
            for key, value in values.items():
                db.execute(
                    """
                    INSERT INTO settings (key, value, updated_at)
                    VALUES (?, ?, ?)
                    ON CONFLICT(key) DO UPDATE SET
                        value = excluded.value,
                        updated_at = excluded.updated_at
                    """,
                    (key, value, utc_now()),
                )
        return self.get_settings()

    def overview(self) -> dict[str, int]:
        with self.connection() as db:
            users_total = db.execute("SELECT COUNT(*) FROM users").fetchone()[0]
            users_active = db.execute(
                "SELECT COUNT(*) FROM users WHERE is_active = 1"
            ).fetchone()[0]
            conversations_total = db.execute(
                "SELECT COUNT(*) FROM conversations"
            ).fetchone()[0]
            messages_total = db.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
            tokens_total = db.execute(
                "SELECT COALESCE(SUM(input_tokens + output_tokens), 0) FROM messages"
            ).fetchone()[0]
        return {
            "users_total": users_total,
            "users_active": users_active,
            "conversations_total": conversations_total,
            "messages_total": messages_total,
            "tokens_total": tokens_total,
        }

    def audit(self, actor_user_id: int, action: str, target: str = "") -> None:
        with self.connection() as db:
            db.execute(
                """
                INSERT INTO audit_log (actor_user_id, action, target, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (actor_user_id, action, target, utc_now()),
            )
