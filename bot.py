import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
import asyncio
from datetime import datetime
from aiohttp import web

# Конфиг и логирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN = "8283929613:AAGsabwYn_34VBsEwByIFB3F11OMYQcr-X0"
ADMIN_CHAT_ID = -1003098912428
PORT = int(os.getenv('PORT', 8000))
WEBHOOK_URL = os.getenv('WEBHOOK_URL', '')  # Должен быть https://yourapp.onrender.com

worker_responses = {}

class TelegramWorkerBot:
    def __init__(self):
        self.application = Application.builder().token(BOT_TOKEN).build()
        self.setup_handlers()

    def setup_handlers(self):
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CallbackQueryHandler(self.button_callback))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        welcome_text = (
            "Вас вітає Марке Послуг №1! 😊\n\n"
            "Залиште заявку для отримання всього, що вам необхідно!"
        )
        worker_responses[update.effective_user.id] = {
            'stage': 'ask_name',
            'data': {},
            'timestamp': datetime.now()
        }
        await update.message.reply_text(welcome_text)
        await update.message.reply_text("Напишіть, будь ласка, ваше ім'я 📝")

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        help_text = (
            "🤖 **Worker Request Bot Help**\n\n"
            "**Команди:**\n"
            "• /start - Почати роботу з ботом\n"
            "• /help - Допомога\n\n"
            "**Як це працює:**\n"
            "1. Введіть своє ім'я\n"
            "2. Відповідайте на питання\n"
            "3. Заявка надійде адміністратору\n\n"
            "Просто надсилайте повідомлення, щоб почати!"
        )
        await update.message.reply_text(help_text, parse_mode='Markdown')

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        message_text = update.message.text.strip()

        if user_id not in worker_responses:
            await update.message.reply_text("Будь ласка, надішліть /start, щоб почати.")
            return

        user_session = worker_responses[user_id]
        stage = user_session['stage']

        if stage == 'ask_name':
            user_session['data']['name'] = message_text
            user_session['stage'] = 'ask_object'
            await update.message.reply_text("Ваше ім'я прийнято! 😊\n\nНа який об’єкт потрібно матеріал/інструмент? 🏗️")

        elif stage == 'ask_object':
            user_session['data']['object'] = message_text
            user_session['stage'] = 'ask_material'
            await update.message.reply_text("Який матеріал/інструмент потрібен? 🧰")

        elif stage == 'ask_material':
            user_session['data']['material'] = message_text
            user_session['stage'] = 'ask_deadline'

            keyboard = [
                [InlineKeyboardButton("🔴 Терміново до 1 години", callback_data="deadline_urgent")],
                [InlineKeyboardButton("🟡 До 18:00", callback_data="deadline_today")],
                [InlineKeyboardButton("🟢 Завтра до 12:00", callback_data="deadline_tomorrow")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text("На коли це потрібно? ⏰", reply_markup=reply_markup)

        elif stage == 'ask_additional':
            user_session['data']['additional_info'] = message_text
            await self.send_request(update, context, user_id)

    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()

        user_id = query.from_user.id
        data = query.data

        if user_id not in worker_responses:
            await query.edit_message_text("Сесія втрачена. Будь ласка, надішліть /start щоб почати заново.")
            return

        if data.startswith("deadline_"):
            deadline_map = {
                "deadline_urgent": "Терміново до 1 години 🔴",
                "deadline_today": "До 18:00 🟡",
