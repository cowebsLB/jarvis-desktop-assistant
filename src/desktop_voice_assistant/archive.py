from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from math import sqrt
from pathlib import Path
from typing import Any

from .config import APP_DIR
from .models import ResearchSource


ARCHIVE_PATH = APP_DIR / "assistant.db"


@dataclass
class ArchiveHit:
    title: str
    url: str
    summary: str
    content: str
    query: str
    fetched_at: str
    stale: bool = False
    age_days: int = 0


class AssistantArchive:
    STALE_AFTER_DAYS = 7

    def __init__(self, path: Path = ARCHIVE_PATH) -> None:
        self.path = path
        APP_DIR.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS web_pages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT NOT NULL UNIQUE,
                    title TEXT NOT NULL,
                    query TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    content TEXT NOT NULL,
                    fetched_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS web_page_embeddings (
                    url TEXT PRIMARY KEY,
                    vector_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(url) REFERENCES web_pages(url) ON DELETE CASCADE
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS task_embeddings (
                    task_id TEXT PRIMARY KEY,
                    vector_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(task_id) REFERENCES tasks(id) ON DELETE CASCADE
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS conversation_turns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_msg TEXT NOT NULL,
                    assistant_msg TEXT NOT NULL,
                    summary TEXT,
                    timestamp TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS conversation_embeddings (
                    turn_id INTEGER PRIMARY KEY,
                    vector_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(turn_id) REFERENCES conversation_turns(id) ON DELETE CASCADE
                )
                """
            )

    def store_sources(self, query: str, sources: list[ResearchSource], page_content: dict[str, str]) -> int:
        if not sources:
            return 0

        stored = 0
        fetched_at = datetime.now(UTC).isoformat()
        with self._connect() as connection:
            for source in sources:
                content = page_content.get(source.url, source.snippet)
                connection.execute(
                    """
                    INSERT INTO web_pages (url, title, query, summary, content, fetched_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(url) DO UPDATE SET
                        title = excluded.title,
                        query = excluded.query,
                        summary = excluded.summary,
                        content = excluded.content,
                        fetched_at = excluded.fetched_at
                    """,
                    (source.url, source.title, query, source.snippet, content, fetched_at),
                )
                stored += 1
        return stored

    def search(self, query: str, limit: int = 3) -> list[ArchiveHit]:
        like = f"%{query.lower()}%"
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT title, url, summary, content, query, fetched_at
                FROM web_pages
                WHERE lower(title) LIKE ?
                   OR lower(summary) LIKE ?
                   OR lower(content) LIKE ?
                   OR lower(query) LIKE ?
                ORDER BY fetched_at DESC
                LIMIT ?
                """,
                (like, like, like, like, limit),
            ).fetchall()
        return [
            self._row_to_hit(row)
            for row in rows
        ]

    def store_embedding(self, url: str, vector: list[float]) -> None:
        updated_at = datetime.now(UTC).isoformat()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO web_page_embeddings (url, vector_json, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(url) DO UPDATE SET
                    vector_json = excluded.vector_json,
                    updated_at = excluded.updated_at
                """,
                (url, json.dumps(vector), updated_at),
            )

    def semantic_search(self, query_vector: list[float], limit: int = 3) -> list[ArchiveHit]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT p.title, p.url, p.summary, p.content, p.query, p.fetched_at, e.vector_json
                FROM web_pages p
                JOIN web_page_embeddings e ON e.url = p.url
                """
            ).fetchall()

        scored: list[tuple[float, ArchiveHit]] = []
        for row in rows:
            vector = json.loads(row["vector_json"])
            score = self._cosine_similarity(query_vector, vector)
            if score <= 0:
                continue
            scored.append(
                (
                    score,
                    self._row_to_hit(row),
                )
            )

        scored.sort(key=lambda item: item[0], reverse=True)
        return [hit for _, hit in scored[:limit]]

    @staticmethod
    def _cosine_similarity(left: list[float], right: list[float]) -> float:
        if not left or not right or len(left) != len(right):
            return 0.0
        numerator = sum(a * b for a, b in zip(left, right, strict=False))
        left_norm = sqrt(sum(a * a for a in left))
        right_norm = sqrt(sum(b * b for b in right))
        if left_norm == 0 or right_norm == 0:
            return 0.0
        return numerator / (left_norm * right_norm)

    @classmethod
    def _row_to_hit(cls, row) -> ArchiveHit:
        fetched_at = row["fetched_at"]
        age_days = cls._age_days(fetched_at)
        return ArchiveHit(
            title=row["title"],
            url=row["url"],
            summary=row["summary"],
            content=row["content"],
            query=row["query"],
            fetched_at=fetched_at,
            stale=age_days >= cls.STALE_AFTER_DAYS,
            age_days=age_days,
        )

    @staticmethod
    def _age_days(fetched_at: str) -> int:
        try:
            fetched = datetime.fromisoformat(fetched_at)
        except ValueError:
            return 9999
        if fetched.tzinfo is None:
            fetched = fetched.replace(tzinfo=UTC)
        delta = datetime.now(UTC) - fetched.astimezone(UTC)
        return max(0, delta.days)

    def sync_tasks(self, tasks: list[dict[str, Any]], embedder = None) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM tasks")
            conn.execute("DELETE FROM task_embeddings")
            for t in tasks:
                conn.execute(
                    "INSERT INTO tasks (id, content, created_at) VALUES (?, ?, ?)",
                    (t["id"], t["content"], t["created_at"])
                )
                if embedder:
                    vector = embedder.embed(t["content"])
                    if vector:
                        conn.execute(
                            "INSERT INTO task_embeddings (task_id, vector_json, updated_at) VALUES (?, ?, ?)",
                            (t["id"], json.dumps(vector), datetime.now(UTC).isoformat())
                        )

    def add_conversation_turn(self, user_msg: str, assistant_msg: str, summary: str | None = None) -> int:
        timestamp = datetime.now(UTC).isoformat()
        with self._connect() as conn:
            cursor = conn.execute(
                "INSERT INTO conversation_turns (user_msg, assistant_msg, summary, timestamp) VALUES (?, ?, ?, ?)",
                (user_msg, assistant_msg, summary or "", timestamp)
            )
            return cursor.lastrowid

    def store_conversation_embedding(self, turn_id: int, vector: list[float]) -> None:
        updated_at = datetime.now(UTC).isoformat()
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO conversation_embeddings (turn_id, vector_json, updated_at) VALUES (?, ?, ?)",
                (turn_id, json.dumps(vector), updated_at)
            )

    def search_local(self, query: str, limit: int = 3, embedder = None) -> list[dict[str, Any]]:
        vector = None
        if embedder:
            vector = embedder.embed(query)
        if vector:
            return self._semantic_search_all(vector, limit=limit)
        return self._full_text_search_all(query, limit=limit)

    def _semantic_search_all(self, query_vector: list[float], limit: int = 3) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        with self._connect() as conn:
            # 1. Web pages
            rows = conn.execute(
                "SELECT p.title, p.url, p.summary, p.content, p.fetched_at, e.vector_json FROM web_pages p JOIN web_page_embeddings e ON e.url = p.url"
            ).fetchall()
            for r in rows:
                score = self._cosine_similarity(query_vector, json.loads(r["vector_json"]))
                if score >= 0.35:
                    results.append({
                        "type": "research",
                        "title": r["title"],
                        "url": r["url"],
                        "summary": r["summary"],
                        "content": r["content"],
                        "score": score,
                        "date": r["fetched_at"]
                    })
            
            # 2. Tasks
            rows = conn.execute(
                "SELECT t.id, t.content, t.created_at, e.vector_json FROM tasks t JOIN task_embeddings e ON e.task_id = t.id"
            ).fetchall()
            for r in rows:
                score = self._cosine_similarity(query_vector, json.loads(r["vector_json"]))
                if score >= 0.35:
                    results.append({
                        "type": "task",
                        "title": "Active Task",
                        "content": r["content"],
                        "score": score,
                        "date": r["created_at"]
                    })
            
            # 3. Conversation turns
            rows = conn.execute(
                "SELECT c.id, c.user_msg, c.assistant_msg, c.summary, c.timestamp, e.vector_json FROM conversation_turns c JOIN conversation_embeddings e ON e.turn_id = c.id"
            ).fetchall()
            for r in rows:
                score = self._cosine_similarity(query_vector, json.loads(r["vector_json"]))
                if score >= 0.35:
                    results.append({
                        "type": "conversation",
                        "title": "Past Conversation",
                        "content": f"User: {r['user_msg']}\nJarvis: {r['assistant_msg']}",
                        "score": score,
                        "date": r["timestamp"]
                    })
                    
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]

    def _full_text_search_all(self, query: str, limit: int = 3) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        like = f"%{query.lower()}%"
        with self._connect() as conn:
            # 1. Web pages
            rows = conn.execute(
                """
                SELECT title, url, summary, content, fetched_at FROM web_pages
                WHERE lower(title) LIKE ? OR lower(summary) LIKE ? OR lower(content) LIKE ?
                ORDER BY fetched_at DESC LIMIT ?
                """,
                (like, like, like, limit)
            ).fetchall()
            for r in rows:
                results.append({
                    "type": "research",
                    "title": r["title"],
                    "url": r["url"],
                    "summary": r["summary"],
                    "content": r["content"],
                    "score": 1.0,
                    "date": r["fetched_at"]
                })
            
            # 2. Tasks
            rows = conn.execute(
                """
                SELECT id, content, created_at FROM tasks
                WHERE lower(content) LIKE ?
                ORDER BY created_at DESC LIMIT ?
                """,
                (like, limit)
            ).fetchall()
            for r in rows:
                results.append({
                    "type": "task",
                    "title": "Active Task",
                    "content": r["content"],
                    "score": 1.0,
                    "date": r["created_at"]
                })
            
            # 3. Conversation turns
            rows = conn.execute(
                """
                SELECT id, user_msg, assistant_msg, timestamp FROM conversation_turns
                WHERE lower(user_msg) LIKE ? OR lower(assistant_msg) LIKE ?
                ORDER BY timestamp DESC LIMIT ?
                """,
                (like, like, limit)
            ).fetchall()
            for r in rows:
                results.append({
                    "type": "conversation",
                    "title": "Past Conversation",
                    "content": f"User: {r['user_msg']}\nJarvis: {r['assistant_msg']}",
                    "score": 1.0,
                    "date": r["timestamp"]
                })
        results.sort(key=lambda x: x["date"], reverse=True)
        return results[:limit]
