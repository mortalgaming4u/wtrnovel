# db.py
import os
import sqlite3
from contextlib import contextmanager

DB_PATH = os.getenv("NOVEL_DB_PATH", "data/novels.db")

SCHEMA = """
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_url TEXT UNIQUE,
    title TEXT,
    author TEXT,
    cover_url TEXT,
    description TEXT,
    status TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS chapters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id INTEGER NOT NULL,
    index_num INTEGER NOT NULL,
    title TEXT,
    content TEXT,
    source_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(book_id, index_num),
    FOREIGN KEY(book_id) REFERENCES books(id) ON DELETE CASCADE
);
"""

def init_db(db_path: str | None = None) -> str:
    path = db_path or DB_PATH
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with sqlite3.connect(path) as conn:
        conn.executescript(SCHEMA)
    return path

@contextmanager
def get_conn(db_path: str | None = None):
    conn = sqlite3.connect(db_path or DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()

# ---------- Books ----------
def upsert_book(conn, *, source_url: str, title: str = "", author: str = "",
                cover_url: str = "", description: str = "", status: str = "") -> int:
    conn.execute("""
        INSERT INTO books (source_url, title, author, cover_url, description, status)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(source_url) DO UPDATE SET
            title=excluded.title,
            author=excluded.author,
            cover_url=excluded.cover_url,
            description=excluded.description,
            status=excluded.status,
            updated_at=CURRENT_TIMESTAMP
    """, (source_url, title, author, cover_url, description, status))
    cur = conn.execute("SELECT id FROM books WHERE source_url=?", (source_url,))
    return cur.fetchone()["id"]

def get_book_by_url(conn, source_url: str):
    cur = conn.execute("SELECT * FROM books WHERE source_url=?", (source_url,))
    return cur.fetchone()

# ---------- Chapters ----------
def chapter_exists(conn, *, book_id: int, index_num: int) -> bool:
    cur = conn.execute("SELECT 1 FROM chapters WHERE book_id=? AND index_num=?", (book_id, index_num))
    return cur.fetchone() is not None

def upsert_chapter(conn, *, book_id: int, index_num: int, title: str, content: str, source_url: str = "") -> int:
    conn.execute("""
        INSERT INTO chapters (book_id, index_num, title, content, source_url)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(book_id, index_num) DO UPDATE SET
            title=excluded.title,
            content=excluded.content,
            source_url=excluded.source_url,
            updated_at=CURRENT_TIMESTAMP
    """, (book_id, index_num, title, content, source_url))
    cur = conn.execute("SELECT id FROM chapters WHERE book_id=? AND index_num=?", (book_id, index_num))
    return cur.fetchone()["id"]

def list_chapter_heads(conn, book_id: int):
    cur = conn.execute("SELECT id, index_num, title FROM chapters WHERE book_id=? ORDER BY index_num ASC", (book_id,))
    return [dict(r) for r in cur.fetchall()]

def count_chapters(conn, book_id: int) -> int:
    cur = conn.execute("SELECT COUNT(*) AS c FROM chapters WHERE book_id=?", (book_id,))
    return int(cur.fetchone()["c"])
