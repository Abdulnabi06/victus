import json
import logging
import uuid
import time
from typing import Any, Dict, List, Optional

import requests
from pymongo import MongoClient, ASCENDING
from pymongo.collection import Collection
from pymongo.database import Database

from backend.config.settings import settings

logger = logging.getLogger("zyricon-backend.mongodb")

DEFAULT_CONFIG = {
    "model": "ChatGPT v4.0",
    "voice_enabled": "true",
    "voice_speed": "1.0",
    "search_provider": "duckduckgo",
    "automation_mode": "confirm",
}


class MongoDataAPIClient:
    """MongoDB Atlas Data API (HTTPS) client."""

    def __init__(
        self,
        app_id: str,
        api_key: str,
        data_source: str,
        database: str,
    ) -> None:
        self.base_url = f"https://data.mongodb-api.com/app/{app_id}/endpoint/data/v1/action"
        self.headers = {
            "Content-Type": "application/json",
            "api-key": api_key,
        }
        self.data_source = data_source
        self.database = database

    def _request(self, action: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        body = {
            "dataSource": self.data_source,
            "database": self.database,
            **payload,
        }
        response = requests.post(
            f"{self.base_url}/{action}",
            headers=self.headers,
            json=body,
            timeout=30,
        )
        response.raise_for_status()
        return response.json()

    def find_one(self, collection: str, filter_doc: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        result = self._request("findOne", {"collection": collection, "filter": filter_doc})
        return result.get("document")

    def find(
        self,
        collection: str,
        filter_doc: Optional[Dict[str, Any]] = None,
        sort: Optional[Dict[str, int]] = None,
    ) -> List[Dict[str, Any]]:
        payload: Dict[str, Any] = {"collection": collection, "filter": filter_doc or {}}
        if sort:
            payload["sort"] = sort
        result = self._request("find", payload)
        return result.get("documents", [])

    def insert_one(self, collection: str, document: Dict[str, Any]) -> None:
        self._request("insertOne", {"collection": collection, "document": document})

    def update_one(
        self,
        collection: str,
        filter_doc: Dict[str, Any],
        update_doc: Dict[str, Any],
        upsert: bool = False,
    ) -> None:
        self._request(
            "updateOne",
            {
                "collection": collection,
                "filter": filter_doc,
                "update": update_doc,
                "upsert": upsert,
            },
        )

    def ping(self) -> bool:
        try:
            self.find_one("config", {"key": "__ping__"})
            return True
        except Exception as exc:
            logger.error("MongoDB Data API ping failed: %s", exc)
            return False


class MongoDBStore:
    """MongoDB Atlas storage using the native driver or Data API."""

    def __init__(self) -> None:
        self._client: Optional[MongoClient] = None
        self._db: Optional[Database] = None
        self._api: Optional[MongoDataAPIClient] = None
        self._use_api = False
        self._connect()

    def _connect(self) -> None:
        if settings.MONGODB_URI:
            self._client = MongoClient(settings.MONGODB_URI, serverSelectionTimeoutMS=5000)
            self._db = self._client[settings.MONGODB_DATABASE]
            self._ensure_indexes()
            logger.info("Connected to MongoDB Atlas via URI (database: %s)", settings.MONGODB_DATABASE)
            return

        if settings.MONGODB_APP_ID and settings.MONGODB_API_KEY:
            self._api = MongoDataAPIClient(
                app_id=settings.MONGODB_APP_ID,
                api_key=settings.MONGODB_API_KEY,
                data_source=settings.MONGODB_DATA_SOURCE,
                database=settings.MONGODB_DATABASE,
            )
            self._use_api = True
            logger.info(
                "Connected to MongoDB Atlas via Data API (app: %s, database: %s)",
                settings.MONGODB_APP_ID,
                settings.MONGODB_DATABASE,
            )
            return

        raise ValueError(
            "MongoDB Atlas is not configured. Set MONGODB_URI or MONGODB_APP_ID + MONGODB_API_KEY in .env"
        )

    def _ensure_indexes(self) -> None:
        if not self._db:
            return
        self._db.chats.create_index([("updated_at", ASCENDING)])
        self._db.messages.create_index([("chat_id", ASCENDING), ("timestamp", ASCENDING)])
        self._db.config.create_index([("key", ASCENDING)], unique=True)
        self._db.tasks.create_index([("id", ASCENDING)], unique=True)

    def _collection(self, name: str) -> Collection:
        if not self._db:
            raise RuntimeError("MongoDB driver connection is not available")
        return self._db[name]

    def ping(self) -> bool:
        try:
            if self._client is not None:
                self._client.admin.command("ping")
                return True
            if self._api is not None:
                return self._api.ping()
        except Exception as exc:
            logger.error("MongoDB ping failed: %s", exc)
        return False

    def init_db(self) -> None:
        existing = self.get_config()
        if existing:
            return
        self.update_config(DEFAULT_CONFIG)

    # Chat operations
    def create_chat(self, title: str = "New Chat", model: str = "ChatGPT v4.0") -> Dict[str, Any]:
        chat_id = f"chat_{uuid.uuid4().hex[:8]}"
        now = time.time()
        doc = {
            "id": chat_id,
            "title": title,
            "model": model,
            "created_at": now,
            "updated_at": now,
            "archived": False,
        }
        if self._use_api and self._api:
            self._api.insert_one("chats", doc)
        else:
            self._collection("chats").insert_one(doc)
        doc.pop("_id", None)
        return doc

    def get_all_chats(self) -> List[Dict[str, Any]]:
        if self._use_api and self._api:
            rows = self._api.find("chats", sort={"updated_at": -1})
        else:
            rows = list(self._collection("chats").find({}, {"_id": 0}).sort("updated_at", -1))
        return [
            {
                "id": r["id"],
                "title": r["title"],
                "model": r["model"],
                "created_at": r["created_at"],
                "updated_at": r["updated_at"],
                "archived": bool(r.get("archived", False)),
            }
            for r in rows
        ]

    def get_chat_with_messages(self, chat_id: str) -> Optional[Dict[str, Any]]:
        if self._use_api and self._api:
            chat = self._api.find_one("chats", {"id": chat_id})
            if not chat:
                return None
            messages = self._api.find(
                "messages",
                {"chat_id": chat_id},
                sort={"timestamp": 1},
            )
        else:
            chat = self._collection("chats").find_one({"id": chat_id}, {"_id": 0})
            if not chat:
                return None
            messages = list(
                self._collection("messages")
                .find({"chat_id": chat_id}, {"_id": 0})
                .sort("timestamp", ASCENDING)
            )

        parsed_messages = []
        for m in messages:
            tool_calls = m.get("tool_calls")
            if isinstance(tool_calls, str):
                tool_calls = json.loads(tool_calls)
            parsed_messages.append(
                {
                    "id": m["id"],
                    "role": m["role"],
                    "content": m["content"],
                    "timestamp": m["timestamp"],
                    "tool_calls": tool_calls,
                    "tool_output": m.get("tool_output"),
                    "image_url": m.get("image_url"),
                }
            )

        return {
            "id": chat["id"],
            "title": chat["title"],
            "model": chat["model"],
            "created_at": chat["created_at"],
            "updated_at": chat["updated_at"],
            "messages": parsed_messages,
        }

    def add_message(
        self,
        chat_id: str,
        role: str,
        content: str,
        tool_calls: Any = None,
        tool_output: str = None,
        image_url: str = None,
    ) -> Dict[str, Any]:
        msg_id = f"msg_{uuid.uuid4().hex[:8]}"
        now = time.time()
        doc = {
            "id": msg_id,
            "chat_id": chat_id,
            "role": role,
            "content": content,
            "timestamp": now,
            "tool_calls": tool_calls,
            "tool_output": tool_output,
            "image_url": image_url,
        }

        if self._use_api and self._api:
            self._api.insert_one("messages", doc)
            self._api.update_one(
                "chats",
                {"id": chat_id},
                {"$set": {"updated_at": now}},
            )
        else:
            self._collection("messages").insert_one(doc)
            self._collection("chats").update_one({"id": chat_id}, {"$set": {"updated_at": now}})

        return {
            "id": msg_id,
            "chat_id": chat_id,
            "role": role,
            "content": content,
            "timestamp": now,
            "tool_calls": tool_calls,
            "tool_output": tool_output,
            "image_url": image_url,
        }

    # Config operations
    def get_config(self) -> Dict[str, str]:
        if self._use_api and self._api:
            rows = self._api.find("config")
        else:
            rows = list(self._collection("config").find({}, {"_id": 0}))
        return {r["key"]: str(r["value"]) for r in rows}

    def update_config(self, config_dict: Dict[str, str]) -> Dict[str, str]:
        if self._use_api and self._api:
            for key, value in config_dict.items():
                self._api.update_one(
                    "config",
                    {"key": key},
                    {"$set": {"key": key, "value": str(value)}},
                    upsert=True,
                )
        else:
            for key, value in config_dict.items():
                self._collection("config").update_one(
                    {"key": key},
                    {"$set": {"key": key, "value": str(value)}},
                    upsert=True,
                )
        return self.get_config()

    # Task operations
    def save_task(self, task_id: str, name: str, status: str, result: str = None) -> Dict[str, Any]:
        now = time.time()
        doc = {
            "id": task_id,
            "name": name,
            "status": status,
            "result": result,
            "created_at": now,
        }
        if self._use_api and self._api:
            self._api.update_one(
                "tasks",
                {"id": task_id},
                {"$set": doc},
                upsert=True,
            )
        else:
            self._collection("tasks").update_one({"id": task_id}, {"$set": doc}, upsert=True)
        return doc

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        if self._use_api and self._api:
            row = self._api.find_one("tasks", {"id": task_id})
        else:
            row = self._collection("tasks").find_one({"id": task_id}, {"_id": 0})
        if not row:
            return None
        return {
            "id": row["id"],
            "name": row["name"],
            "status": row["status"],
            "result": row.get("result"),
            "created_at": row["created_at"],
        }


_store: Optional[MongoDBStore] = None


def get_mongo_store() -> MongoDBStore:
    global _store
    if _store is None:
        _store = MongoDBStore()
        _store.init_db()
    return _store
