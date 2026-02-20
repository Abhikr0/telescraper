import os
import asyncio
import logging
from telethon import TelegramClient
from config import settings
from typing import Optional, Callable

logger = logging.getLogger(__name__)

class TelethonManager:
    _instance = None
    _client: Optional[TelegramClient] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TelethonManager, cls).__new__(cls)
        return cls._instance

    async def get_client(self) -> TelegramClient:
        if self._client is None or not self._client.is_connected():
            if not settings.API_ID or not settings.API_HASH:
                raise ValueError("API_ID and API_HASH must be configured in .env")

            session_path = os.path.join(os.getcwd(), "bot_session")
            self._client = TelegramClient(session_path, settings.API_ID, settings.API_HASH)
            await self._client.start(bot_token=settings.BOT_TOKEN)
            logger.info("Telethon client started.")
        return self._client

    async def disconnect(self):
        if self._client and self._client.is_connected():
            await self._client.disconnect()
            self._client = None

    async def upload_file(self, file_path: str, chat_id: int, caption: Optional[str] = None, progress_callback: Optional[Callable] = None):
        client = await self.get_client()
        
        def default_progress(current, total):
            percentage = (current / total) * 100 if total > 0 else 0
            print(f'  - [MTProto] Uploading: {current}/{total} ({percentage:.2f}%)', flush=True)

        cb = progress_callback or default_progress
        
        try:
            from fast_upload import upload_file_parallel
            input_file = await upload_file_parallel(client, file_path, progress_callback=cb)
            sent_message = await client.send_file(
                chat_id, input_file, caption=caption, supports_streaming=True
            )
            return sent_message
        except Exception as e:
            logger.error(f"MTProto upload failed: {e}")
            raise e
