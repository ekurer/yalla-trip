import json
import aiosqlite
from .interfaces import StateStore
from .models import ConversationState
from .logger import get_logger
from .config import settings

logger = get_logger(__name__)

__all__ = ["SQLiteStateStore"]


class SQLiteStateStore(StateStore):
    def __init__(self, db_path: str = settings.DB_PATH):
        self.db_path = db_path

    async def init_db(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    data TEXT
                )
                """
            )
            await db.commit()

    async def load(self, session_id: str) -> ConversationState:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT data FROM sessions WHERE session_id = ?", (session_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    try:
                        data = json.loads(row[0])
                        return ConversationState(**data)
                    except json.JSONDecodeError:
                        logger.error("failed_to_decode_state", session_id=session_id)
                        return ConversationState()
                return ConversationState()

    async def save(self, session_id: str, state: ConversationState):
        data = state.model_dump_json()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT OR REPLACE INTO sessions (session_id, data) VALUES (?, ?)",
                (session_id, data),
            )
            await db.commit()
