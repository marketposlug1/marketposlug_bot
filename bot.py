import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
import asyncio
from datetime import datetime
from aiohttp import web

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN = "8283929613:AAGsabwYn_34VBsEwByIFB3F11OMYQcr-X0"
ADMIN_CHAT_ID = -1003098912428
PORT = int(os.getenv('PORT', 8000))
WEBHOOK_URL = os.getenv('WEBHOOK_URL', '')  # Пример: https://yourapp.onrender.com

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
        worker_responses[update.effective_user.id] = {'stage': 'ask_name', 'data': {}, 'timestamp': datetime.now()}
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
        await query.answer()  # Обязательно подтверждаем получение

        user_id = query.from_user.id
        data = query.data

        if user_id not in worker_responses:
            await query.edit_message_text("Сесія втрачена. Будь ласка, надішліть /start щоб почати заново.")
            return

        if data.startswith("deadline_"):
            deadline_map = {
                "deadline_urgent": "Терміново до 1 години 🔴",
                "deadline_today": "До 18:00 🟡",
                "deadline_tomorrow": "Завтра до 12:00 🟢"
            }
            selected_deadline = deadline_map.get(data, "Не вказано")
            worker_responses[user_id]['data']['deadline'] = selected_deadline
            worker_responses[user_id]['stage'] = 'ask_additional'

            await query.edit_message_text(
                f"Ви вибрали: {selected_deadline}\n\n"
                "Додаткова інформація або напишіть 'нема' для завершення:"
            )

    async def send_request(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
        data = worker_responses[user_id]['data']
        timestamp = worker_responses[user_id]['timestamp'].strftime("%Y-%m-%d %H:%M:%S")
        user = update.effective_user

        admin_message = (
            "📬 **Нова заявка на послугу**\n\n"
            f"👤 **Ім'я:** {data.get('name', '-')}\n"
            f"🏗️ **Об'єкт:** {data.get('object', '-')}\n"
            f"🧰 **Матеріал/інструмент:** {data.get('material', '-')}\n"
            f"⏰ **Термін:** {data.get('deadline', '-')}\n"
            f"ℹ️ **Додаткова інформація:** {data.get('additional_info', '-')}\n\n"
            f"🆔 **ID користувача:** {user_id}\n"
            f"📅 **Подано:** {timestamp}\n\n"
            "---\n"
            f"Користувач: {user.first_name} {user.last_name or ''} (@{user.username or 'немає_юзернейма'})"
        )

        try:
            await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=admin_message, parse_mode='Markdown')
            await update.message.reply_text(
                "✅ **Заявка успішно надіслана!**\n\n"
                "Дякуємо! Чекайте на відповідь від адміністратора.",
                parse_mode='Markdown'
            )
            del worker_responses[user_id]
        except Exception as e:
            logger.error(f"Error sending to admin: {e}")
            await update.message.reply_text("❌ Сталася помилка при надсиланні заявки. Спробуйте пізніше.")

    async def run_webhook(self):
        from aiohttp import web

        async def handle_post(request):
            data = await request.json()
            update = Update.de_json(data, self.application.bot)
            await self.application.update_queue.put(update)
            return web.Response(text="OK")

        async def handle_get(request):
            return web.Response(text="Webhook endpoint is working!")

        async def handle_health(request):
            return web.Response(text="OK")

        app = web.Application()
        app.router.add_post('/webhook', handle_post)
        app.router.add_get('/webhook', handle_get)
        app.router.add_get('/health', handle_health)

        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', PORT)
        await site.start()

        webhook_url = f"{WEBHOOK_URL}/webhook"
        await self.application.bot.set_webhook(webhook_url)
        logger.info(f"Webhook set: {webhook_url}")

        await self.application.initialize()
        await self.application.start()

        logger.info("Bot started with webhook")

        while True:
            await asyncio.sleep(3600)

    async def run_polling(self):
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling()
        logger.info("Bot started with polling")
        stop_event = asyncio.Event()

        def stop():
            stop_event.set()

        import signal
        for s in (signal.SIGINT, signal.SIGTERM):
            signal.signal(s, lambda signum, frame: stop())
        await stop_event.wait()

async def main():
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN environment variable is required!")
        return
    if not ADMIN_CHAT_ID:
        logger.error("ADMIN_CHAT_ID environment variable is required!")
        return

    bot = TelegramWorkerBot()

    if WEBHOOK_URL:
        await bot.run_webhook()
    else:
        await bot.run_polling()

if __name__ == '__main__':
    asyncio.run(main())
