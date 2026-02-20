import os
import asyncio
import logging
from telegram import Update, ReplyKeyboardRemove
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)
from scraper import CoomerScraper
from db import db
from config import settings
from telethon_util import TelethonManager

logger = logging.getLogger(__name__)

ASK_URL, ASK_PAGE, ASK_CONCURRENCY = range(3)

async def start_coomer_flow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    target = query.message if query else update.message
    if query: await query.answer()
    await target.reply_text(
        "📥 *Coomer.st Parallel Downloader*\n\nEnter the Coomer.st profile URL:",
        parse_mode="Markdown"
    )
    return ASK_URL

async def receive_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    if "coomer.st" not in url:
        await update.message.reply_text("❌ Invalid URL.")
        return ASK_URL
    context.user_data["coomer_url"] = url
    await update.message.reply_text("✅ URL saved.\nEnter page range (e.g. 1, 1-5, all):", parse_mode="Markdown")
    return ASK_PAGE

async def receive_page(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().lower()
    start_page = 1
    max_pages = 1
    if text == "all": max_pages = None
    elif "-" in text:
        try:
            a, b = text.split("-")
            start_page, max_pages = int(a), int(b) - int(a) + 1
        except ValueError: pass
    else:
        try: start_page = int(text)
        except ValueError: pass
    context.user_data["start_page"], context.user_data["max_pages"] = start_page, max_pages
    await update.message.reply_text("✅ Range saved.\nEnter concurrency (1-10):", parse_mode="Markdown")
    return ASK_CONCURRENCY

async def receive_concurrency(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try: concurrency = max(1, min(10, int(update.message.text.strip())))
    except ValueError: concurrency = 3
    context.user_data["concurrency"] = concurrency
    
    msg = await update.message.reply_text("🚀 Starting Job...", parse_mode="Markdown")
    asyncio.create_task(run_worker_process(
        update.effective_chat.id, msg.message_id,
        context.user_data["coomer_url"], context.user_data["start_page"],
        context.user_data["max_pages"], concurrency, context.application.bot
    ))
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Cancelled.")
    return ConversationHandler.END

async def run_worker_process(chat_id, message_id, url, start_page, max_pages, concurrency, bot):
    scraper = CoomerScraper()
    telethon = TelethonManager()
    try:
        videos = await scraper.get_all_videos(url, start_offset=(start_page - 1) * 50, max_pages=max_pages)
        if not videos:
            await bot.edit_message_text(chat_id=chat_id, message_id=message_id, text="⚠️ No videos found.")
            return

        queue = asyncio.Queue()
        for v in videos: queue.put_nowait(v)
        temp_dir = "temp_videos_standalone"
        os.makedirs(temp_dir, exist_ok=True)
        progress = {"total": len(videos), "done": 0, "success": 0, "failed": 0}

        async def worker():
            while not queue.empty():
                video = await queue.get()
                clean_name = "".join(c for c in video["name"] if c.isalnum() or c in (' ', '.', '-', '_')).strip()
                if not clean_name.lower().endswith(".mp4"): clean_name += ".mp4"
                temp_path = os.path.join(temp_dir, clean_name)
                try:
                    if await scraper.download_video(video["url"], temp_path):
                        caption = (video.get("description") or video["name"])[:1024]
                        size_mb = os.path.getsize(temp_path) / (1024 * 1024)
                        if size_mb > 2000: progress["failed"] += 1; continue
                        
                        sent_msg = await telethon.upload_file(temp_path, settings.STORAGE_CHANNEL_ID, caption=caption)
                        if sent_msg:
                            await db.add_media(title=caption, file_id="mtproto", message_id=sent_msg.id, file_size=os.path.getsize(temp_path))
                            progress["success"] += 1
                        else: progress["failed"] += 1
                    else: progress["failed"] += 1
                except Exception as e:
                    logger.error(f"Worker error: {e}")
                    progress["failed"] += 1
                finally:
                    if os.path.exists(temp_path): os.remove(temp_path)
                    progress["done"] += 1; queue.task_done()

        await asyncio.gather(*[worker() for _ in range(concurrency)])
        await bot.send_message(chat_id, f"🏁 Done! {progress['success']} uploaded, {progress['failed']} failed.")
    except Exception as e:
        logger.error(f"Global error: {e}")
        await bot.send_message(chat_id, f"❌ Error: {e}")
    finally:
        await scraper.close(); await telethon.disconnect()

coomer_handler = ConversationHandler(
    entry_points=[CommandHandler("coomer", start_coomer_flow), CallbackQueryHandler(start_coomer_flow, pattern="^coomer_menu$")],
    states={ASK_URL: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_url)], ASK_PAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_page)], ASK_CONCURRENCY: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_concurrency)]},
    fallbacks=[CommandHandler("cancel", cancel)],
    per_message=False, allow_reentry=True,
)
