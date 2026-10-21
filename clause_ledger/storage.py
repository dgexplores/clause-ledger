"""SQL storage with per-browser ownership and optimistic review versions."""
import json
import sqlite3
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path


class Storage:
    def __init__(self, path):
        self.path = str(path)
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as connection:
            connection.executescript("""
            CREATE TABLE IF NOT EXISTS documents (
              id TEXT PRIMARY KEY, owner TEXT NOT NULL, title TEXT NOT NULL,
              created_at TEXT NOT NULL, pages TEXT NOT NULL, report TEXT NOT NULL,
              status TEXT NOT NULL DEFAULT 'awaiting_review', version INTEGER NOT NULL DEFAULT 1);
            CREATE INDEX IF NOT EXISTS documents_owner_created ON documents(owner, created_at);
            CREATE TABLE IF NOT EXISTS events (
              id INTEGER PRIMARY KEY, document_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
              created_at TEXT NOT NULL, decision TEXT NOT NULL, reviewer TEXT NOT NULL, note TEXT NOT NULL, version INTEGER NOT NULL);
            """)

    def connect(self):
        conn = sqlite3.connect(self.path, timeout=5)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def create(self, owner, title, pages, report):
        now = datetime.now(timezone.utc)
        with self.connect() as conn:
            conn.execute("DELETE FROM documents WHERE created_at < ?", ((now-timedelta(hours=24)).isoformat(),))
            count = conn.execute("SELECT COUNT(*) FROM documents WHERE owner=?", (owner,)).fetchone()[0]
            total = conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
            if count >= 20 or total >= 1000:
                raise OverflowError("Demo storage is full. Delete a review before adding another.")
            identifier = str(uuid.uuid4())
            conn.execute("INSERT INTO documents(id,owner,title,created_at,pages,report) VALUES(?,?,?,?,?,?)",
                         (identifier, owner, title, now.isoformat(), json.dumps(pages), json.dumps(report)))
        return self.get(owner, identifier)

    def get(self, owner, identifier):
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM documents WHERE id=? AND owner=?", (identifier, owner)).fetchone()
            if row is None:
                return None
            data = dict(row)
            data.pop("owner")
            data["pages"] = json.loads(data["pages"])
            data["report"] = json.loads(data["report"])
            data["events"] = [dict(item) for item in conn.execute("SELECT created_at,decision,reviewer,note,version FROM events WHERE document_id=? ORDER BY id", (identifier,))]
            return data

    def listing(self, owner):
        with self.connect() as conn:
            return [dict(row) for row in conn.execute("SELECT id,title,created_at,status,version FROM documents WHERE owner=? ORDER BY created_at DESC", (owner,))]

    def review(self, owner, identifier, payload):
        with self.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute("SELECT version FROM documents WHERE id=? AND owner=?", (identifier, owner)).fetchone()
            if row is None:
                raise KeyError(identifier)
            if row["version"] != payload.expected_version:
                raise ValueError("The review changed in another tab. Reload before deciding.")
            version = row["version"] + 1
            conn.execute("UPDATE documents SET status=?,version=? WHERE id=? AND owner=?", (payload.decision, version, identifier, owner))
            conn.execute("INSERT INTO events(document_id,created_at,decision,reviewer,note,version) VALUES(?,?,?,?,?,?)", (identifier, datetime.now(timezone.utc).isoformat(), payload.decision, payload.reviewer, payload.note, version))
        return self.get(owner, identifier)

    def delete(self, owner, identifier):
        with self.connect() as conn:
            return conn.execute("DELETE FROM documents WHERE id=? AND owner=?", (identifier, owner)).rowcount > 0
