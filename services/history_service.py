import datetime
import json
import os
import sqlite3


class MessageHistory:
    """Persistencia local de mensajes recibidos para la vista de antiguos."""

    def __init__(self, app_data_dir):
        self.path = os.path.join(app_data_dir, "IT_Messenger_History.sqlite3")
        self._initialize()

    def _connect(self):
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self):
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    received_at TEXT NOT NULL,
                    sender TEXT NOT NULL,
                    payload TEXT NOT NULL
                )
                """
            )

    def save(self, sender, message):
        if not isinstance(message, dict):
            return

        message_id = message.get("id") or self._fallback_id(sender, message)
        payload = dict(message)
        payload["id"] = message_id
        received_at = message.get("created_at") or datetime.datetime.now().isoformat(timespec="seconds")
        payload["created_at"] = received_at

        with self._connect() as connection:
            connection.execute(
                "INSERT OR IGNORE INTO messages (id, received_at, sender, payload) VALUES (?, ?, ?, ?)",
                (message_id, received_at, sender, json.dumps(payload, ensure_ascii=False))
            )

    def older_than(self, hours):
        threshold = datetime.datetime.now() - datetime.timedelta(hours=hours)
        rows = []
        with self._connect() as connection:
            for row in connection.execute(
                "SELECT payload FROM messages ORDER BY received_at ASC"
            ):
                try:
                    payload = json.loads(row["payload"])
                    created_at = self.parse_datetime(payload.get("created_at"))
                    if created_at is not None and created_at <= threshold:
                        rows.append(payload)
                except (TypeError, ValueError, json.JSONDecodeError):
                    continue
        return rows

    @staticmethod
    def parse_datetime(value):
        if isinstance(value, datetime.datetime):
            return value.replace(tzinfo=None)
        if not value:
            return None
        try:
            return datetime.datetime.fromisoformat(str(value).replace("Z", "+00:00")).replace(tzinfo=None)
        except ValueError:
            return None

    @staticmethod
    def _fallback_id(sender, message):
        return f"legacy:{sender}:{message.get('created_at')}:{message.get('text', '')}"
