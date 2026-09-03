import json
import sqlite3
from datetime import datetime
from pathlib import Path

from config import DATA_DIR, DB_PATH


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS query_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            query TEXT NOT NULL,
            category TEXT,
            response TEXT NOT NULL,
            intent TEXT,
            feedback TEXT,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS pipelines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pipeline_name TEXT NOT NULL,
            status TEXT NOT NULL,
            run_time TEXT,
            duration_minutes REAL,
            error_message TEXT,
            cluster_id TEXT,
            cpu_usage REAL,
            memory_usage REAL,
            dependencies TEXT,
            last_success TEXT
        );
    """)
    conn.commit()

    count = conn.execute("SELECT COUNT(*) FROM pipelines").fetchone()[0]
    if count == 0:
        _load_pipelines_from_json(conn)

    conn.close()


def _load_pipelines_from_json(conn):
    pipelines_path = DATA_DIR / "pipelines.json"
    with open(pipelines_path, encoding="utf-8") as f:
        pipelines = json.load(f)

    for p in pipelines:
        conn.execute(
            """INSERT INTO pipelines
               (pipeline_name, status, run_time, duration_minutes, error_message,
                cluster_id, cpu_usage, memory_usage, dependencies, last_success)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                p["pipeline_name"],
                p["status"],
                p["run_time"],
                p.get("duration_minutes"),
                p.get("error_message"),
                p.get("cluster_id"),
                p.get("cpu_usage"),
                p.get("memory_usage"),
                json.dumps(p.get("dependencies", [])),
                p.get("last_success"),
            ),
        )
    conn.commit()


def log_query(query: str, category: str, response: str, intent: str) -> int:
    conn = get_connection()
    cursor = conn.execute(
        "INSERT INTO query_log (query, category, response, intent, created_at) VALUES (?, ?, ?, ?, ?)",
        (query, category, response, intent, datetime.utcnow().isoformat()),
    )
    conn.commit()
    query_id = int(cursor.lastrowid)
    conn.close()
    return query_id


def save_feedback(query_id: int, feedback: str) -> bool:
    conn = get_connection()
    cursor = conn.execute(
        "UPDATE query_log SET feedback = ? WHERE id = ?",
        (feedback, int(query_id)),
    )
    conn.commit()
    updated = cursor.rowcount > 0
    conn.close()
    return updated


def get_recent_responses(limit: int = 20) -> list[str]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT response FROM query_log ORDER BY id DESC LIMIT ?",
        (limit,),
    ).fetchall()
    conn.close()
    return [row["response"] for row in rows]


def get_query_by_id(query_id: int) -> dict | None:
    conn = get_connection()
    row = conn.execute("SELECT * FROM query_log WHERE id = ?", (int(query_id),)).fetchone()
    conn.close()
    return dict(row) if row else None
