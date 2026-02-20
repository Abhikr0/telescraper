import uuid
import asyncio
from datetime import datetime
from typing import Optional, List, Dict, Any
from supabase import create_client, Client
from config import settings

class Database:
    def __init__(self):
        self.supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

    async def add_media(self, title: str, file_id: str, message_id: int, file_size: int):
        data = {
            "id": str(uuid.uuid4()),
            "title": title,
            "file_id": file_id,
            "message_id": message_id,
            "file_size": file_size,
            "upload_date": datetime.utcnow().isoformat()
        }
        return await asyncio.to_thread(self.supabase.table("media").insert(data).execute)

db = Database()
