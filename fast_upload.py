import os
import asyncio
import hashlib
import math
from typing import Optional, Callable
import logging
from telethon import TelegramClient, utils
from telethon.tl import types, functions

logger = logging.getLogger(__name__)

async def upload_file_parallel(
    client: TelegramClient,
    file_path: str,
    progress_callback: Optional[Callable[[int, int], None]] = None
):
    file_size = os.path.getsize(file_path)
    chunk_size = 512 * 1024
    total_chunks = math.ceil(file_size / chunk_size)
    is_big = file_size > 10 * 1024 * 1024
    
    import struct
    file_id = struct.unpack('<q', os.urandom(8))[0]
    
    concurrency = min(8, total_chunks)
    semaphore = asyncio.Semaphore(concurrency)
    uploaded_size = 0
    
    async def upload_chunk(chunk_index, chunk_data):
        nonlocal uploaded_size
        async with semaphore:
            try:
                if is_big:
                    request = functions.upload.SaveBigFilePartRequest(
                        file_id=file_id, file_part=chunk_index,
                        file_total_parts=total_chunks, bytes=chunk_data
                    )
                else:
                    request = functions.upload.SaveFilePartRequest(
                        file_id=file_id, file_part=chunk_index, bytes=chunk_data
                    )
                await client(request)
                uploaded_size += len(chunk_data)
                if progress_callback:
                    if asyncio.iscoroutinefunction(progress_callback):
                        await progress_callback(uploaded_size, file_size)
                    else: progress_callback(uploaded_size, file_size)
            except Exception as e:
                logger.error(f"Error uploading chunk {chunk_index}: {e}")
                raise

    tasks = []
    with open(file_path, 'rb') as f:
        for i in range(total_chunks):
            chunk_data = f.read(chunk_size)
            tasks.append(upload_chunk(i, chunk_data))
    
    await asyncio.gather(*tasks)
    
    if is_big:
        return types.InputFileBig(id=file_id, parts=total_chunks, name=os.path.basename(file_path))
    else:
        md5_hash = hashlib.md5()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                md5_hash.update(chunk)
        return types.InputFile(id=file_id, parts=total_chunks, name=os.path.basename(file_path), md5_checksum=md5_hash.hexdigest())
