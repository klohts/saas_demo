import sqlite3
import os
import secrets
from datetime import datetime

class ClientManager:
    def __init__(self, db_path="./data/clients.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

    def _conn(self):
        return sqlite3.connect(self.db_path)

    def init_db(self):
        conn = self._conn()
        cur = conn.cursor()
        cur.execute("""
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            api_key TEXT UNIQUE,
            plan TEXT,
            quota_limit INTEGER,
            quota_used INTEGER DEFAULT 0,
            created_at TEXT
        )
        """)
        conn.commit()
        conn.close()

    def generate_api_key(self):
        return secrets.token_urlsafe(24)

    def create_client(self, name, plan, quota_limit=None):
        api_key = self.generate_api_key()
        created_at = datetime.utcnow().isoformat()
        if quota_limit is None:
            defaults = {"Free": 50, "Pro": 1000, "Enterprise": -1}
            quota_limit = defaults.get(plan, 50)
        conn = self._conn()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO clients (name, api_key, plan, quota_limit, created_at) VALUES (?, ?, ?, ?, ?)",
            (name, api_key, plan, quota_limit, created_at)
        )
        conn.commit()
        client_id = cur.lastrowid
        conn.close()
        return self.get_client_by_id(client_id)

    def get_client_by_id(self, client_id):
        conn = self._conn()
        cur = conn.cursor()
        cur.execute("SELECT id, name, api_key, plan, quota_limit, quota_used, created_at FROM clients WHERE id = ?", (client_id,))
        row = cur.fetchone()
        conn.close()
        if not row:
            return None
        keys = ["id","name","api_key","plan","quota_limit","quota_used","created_at"]
        return dict(zip(keys, row))

    def get_client_by_api(self, api_key):
        conn = self._conn()
        cur = conn.cursor()
        cur.execute("SELECT id, name, api_key, plan, quota_limit, quota_used, created_at FROM clients WHERE api_key = ?", (api_key,))
        row = cur.fetchone()
        conn.close()
        if not row:
            return None
        keys = ["id","name","api_key","plan","quota_limit","quota_used","created_at"]
        return dict(zip(keys, row))

    def get_client_by_name(self, name):
        conn = self._conn()
        cur = conn.cursor()
        cur.execute("SELECT id, name, api_key, plan, quota_limit, quota_used, created_at FROM clients WHERE name = ?", (name,))
        row = cur.fetchone()
        conn.close()
        if not row:
            return None
        keys = ["id","name","api_key","plan","quota_limit","quota_used","created_at"]
        return dict(zip(keys, row))

    def list_clients(self):
        conn = self._conn()
        cur = conn.cursor()
        cur.execute("SELECT id, name, api_key, plan, quota_limit, quota_used, created_at FROM clients ORDER BY id DESC")
        rows = cur.fetchall()
        conn.close()
        keys = ["id","name","api_key","plan","quota_limit","quota_used","created_at"]
        return [dict(zip(keys, r)) for r in rows]

    def increment_usage(self, api_key, amount=1):
        conn = self._conn()
        cur = conn.cursor()
        cur.execute("UPDATE clients SET quota_used = quota_used + ? WHERE api_key = ?", (amount, api_key))
        conn.commit()
        conn.close()
