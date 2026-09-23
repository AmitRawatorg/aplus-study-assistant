"""SQLite persistence for A+ Study Assistant."""

from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


DATA_DIR = Path(os.getenv("STUDY_ASSISTANT_DATA_DIR", ".study_assistant"))
DATABASE_PATH = DATA_DIR / "study_assistant.db"


@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    """Open a short-lived SQLite connection with rows accessible by name."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()


def init_db() -> None:
    """Create the local tables used by the app."""
    with get_connection() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
                content TEXT NOT NULL,
                source TEXT NOT NULL DEFAULT 'general',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (username) REFERENCES users(username)
            );
            """
        )


def get_user(username: str) -> sqlite3.Row | None:
    with get_connection() as connection:
        return connection.execute(
            "SELECT username, name, password_hash FROM users WHERE username = ?",
            (username.strip().lower(),),
        ).fetchone()


def create_user(username: str, name: str, password_hash: str) -> bool:
    """Create a user, returning False when the username already exists."""
    try:
        with get_connection() as connection:
            connection.execute(
                "INSERT INTO users (username, name, password_hash) VALUES (?, ?, ?)",
                (username.strip().lower(), name.strip(), password_hash),
            )
        return True
    except sqlite3.IntegrityError:
        return False


def save_message(username: str, role: str, content: str, source: str = "general") -> None:
    with get_connection() as connection:
        connection.execute(
            "INSERT INTO messages (username, role, content, source) VALUES (?, ?, ?, ?)",
            (username.strip().lower(), role, content, source),
        )


def get_messages(username: str, limit: int = 100) -> list[sqlite3.Row]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT role, content, source, created_at
            FROM messages
            WHERE username = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (username.strip().lower(), limit),
        ).fetchall()
    return list(reversed(rows))
