import sqlite3
import json
import os
import time
from typing import Optional

DB_PATH = os.path.join(os.path.dirname(__file__), "chats.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _table_exists(conn: sqlite3.Connection, name: str) -> bool:
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone()
    return row is not None


def _column_exists(conn: sqlite3.Connection, table: str, column: str) -> bool:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return any(r["name"] == column for r in rows)


def init_db():
    with get_connection() as conn:
        if not _table_exists(conn, "chats"):
            conn.execute(
                """
                CREATE TABLE chats (
                    id TEXT,
                    user_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    messages TEXT NOT NULL,
                    turn INTEGER NOT NULL DEFAULT 0,
                    is_final INTEGER NOT NULL DEFAULT 0,
                    started INTEGER NOT NULL DEFAULT 0,
                    updated_at INTEGER NOT NULL,
                    PRIMARY KEY (id, user_id)
                )
                """
            )
            conn.execute("CREATE INDEX idx_chats_user ON chats(user_id, updated_at DESC)")
            conn.commit()
            return

        # Migration: add user_id column if missing
        if not _column_exists(conn, "chats", "user_id"):
            conn.execute("ALTER TABLE chats ADD COLUMN user_id TEXT NOT NULL DEFAULT 'legacy'")
            conn.execute("CREATE INDEX idx_chats_user ON chats(user_id, updated_at DESC)")
            conn.commit()


def save_chat(
    user_id: str,
    chat_id: str,
    title: str,
    messages: list[dict],
    turn: int,
    is_final: bool,
    started: bool,
):
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO chats (id, user_id, title, messages, turn, is_final, started, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id, user_id) DO UPDATE SET
                title = excluded.title,
                messages = excluded.messages,
                turn = excluded.turn,
                is_final = excluded.is_final,
                started = excluded.started,
                updated_at = excluded.updated_at
            """,
            (
                chat_id,
                user_id,
                title,
                json.dumps(messages),
                turn,
                1 if is_final else 0,
                1 if started else 0,
                int(time.time() * 1000),
            ),
        )
        conn.commit()


def get_all_chats(user_id: str):
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM chats WHERE user_id = ? ORDER BY updated_at DESC LIMIT 50",
            (user_id,),
        ).fetchall()
    return [_row_to_dict(row) for row in rows]


def get_chat(user_id: str, chat_id: str) -> Optional[dict]:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM chats WHERE user_id = ? AND id = ?",
            (user_id, chat_id),
        ).fetchone()
    if row is None:
        return None
    return _row_to_dict(row)


def delete_chat(user_id: str, chat_id: str):
    with get_connection() as conn:
        conn.execute(
            "DELETE FROM chats WHERE user_id = ? AND id = ?",
            (user_id, chat_id),
        )
        conn.commit()


def _row_to_dict(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "title": row["title"],
        "messages": json.loads(row["messages"]),
        "turn": row["turn"],
        "isFinal": bool(row["is_final"]),
        "started": bool(row["started"]),
        "updatedAt": row["updated_at"],
    }
