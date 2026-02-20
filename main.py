import logging
import sys
import os
import warnings
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

from config import settings
from coomer_handler import coomer_handler

logging.basicConfig(
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    level=logging.INFO,
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("coomer_uploader")

def main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("📥 Coomer Downloader", callback_data="coomer_menu")]])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in settings.admin_list:
        await update.message.reply_text("⛔ Admin only.")
        return
    await update.message.reply_text("⚙️ *Coomer Uploader Bot*\n\nSelect an option:", parse_mode="Markdown", reply_markup=main_menu_keyboard())

def create_app():
    if not settings.BOT_TOKEN:
        logger.error("BOT_TOKEN not found.")
        sys.exit(1)
    app = ApplicationBuilder().token(settings.BOT_TOKEN).build()
    
    async def post_init(application):
        from telegram import BotCommand
        await application.bot.set_my_commands([
            BotCommand("start", "Show main menu"),
            BotCommand("coomer", "Start Coomer download"),
            BotCommand("cancel", "Cancel operation"),
        ])
    app.post_init = post_init
    app.add_handler(CommandHandler("start", start))
    app.add_handler(coomer_handler)
    return app

if __name__ == "__main__":
    logger.info("Starting Standalone Uploader Bot...")
    create_app().run_polling(drop_pending_updates=True)
