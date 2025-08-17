import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler,
    MessageHandler, CallbackQueryHandler,
    filters, ContextTypes
)
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
WEBHOOK_URL = os.getenv('WEBHOOK_URL', 'https://marketposlug-bot.onrender.com')

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
        user_id = update.effective_user.id
        worker_responses[user_id] = {
            'stage': 'ask_name',
            'data': {},
            'timestamp': datetime.now()
        }
        await update.message.reply_text(
            "Вас вітає Марке Послуг №1! 😊\n\n"
            "Залиште заявку для отримання всього, що вам необхідно!\n\n"
            "Напишіть, будь ласка, ваше ім'я 📝"
        )

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "Для початку надішліть /start.\n"
            "Просто відповідайте на запитання, що з'являться.\n"
            "По кнопках обирайте варіанти."
        )

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        text = update.message.text.strip()

        if user_id not in worker_responses:
            await update.message.reply_text("Будь ласка, надішліть /start щоб почати.")
            return

        stage = worker_responses[user_id]['stage']
        data = worker_responses[user_id]['data']

        if stage == 'ask_name':
            data['name'] = text
            worker_responses[user_id]['stage'] = 'ask_object'
            await update.message.reply_text("На який об'єкт потрібно матеріал/інструмент? 🏗️")

        elif stage == 'ask_object':
            data['object'] = text
            worker_responses[user_id]['stage'] = 'ask_material'
            await update.message.reply_text("Який матеріал/інструмент потрібен? 🧰")

        elif stage == 'ask_material':
            data['material'] = text
            worker_responses[user_id]['stage'] = 'ask_deadline'
            keyboard = [
                [InlineKeyboardButton("🔴 Терміново до 1 години", callback_data="deadline_urgent")],
                [InlineKeyboardButton("🟡 До 18:00", callback_data="deadline_today")],
                [InlineKeyboardButton("🟢 Завтра до 12:00", callback_data="deadline_tomorrow")],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text("На коли це потрібно? ⏰", reply_markup=reply_markup)

        elif stage == 'ask_additional':
            data['additional_info'] = text
            await self.send_request(update, context, user_id)
            del worker_responses[user_id]

    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        user_id = query.from_user.id
        data = query.data
        
        logger.info(f"Button clicked by user {user_id}: {data}")
        
        # Answer the callback query FIRST
        await query.answer()

        if user_id not in worker_responses:
            await query.edit_message_text("Сесія втрачена. Почніть заново /start.")
            return

        if data.startswith("deadline_"):
            deadline_options = {
                "deadline_urgent": "Терміново до 1 години 🔴",
                "deadline_today": "До 18:00 🟡",
                "deadline_tomorrow": "Завтра до 12:00 🟢"
            }
            selected = deadline_options.get(data, "Не вказано")
            worker_responses[user_id]['data']['deadline'] = selected
            worker_responses[user_id]['stage'] = 'ask_additional'

            await query.edit_message_text(
                f"Ви вибрали: {selected}\n\n"
                "Додаткова інформація або напишіть 'нема' для завершення:"
            )

    async def send_request(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
        data = worker_responses[user_id]['data']

        message = (
            f"📢 Нова заявка:\n"
            f"👤 Ім'я: {data.get('name', '-')}\n"
            f"🏗️ Об'єкт: {data.get('object', '-')}\n"
            f"🧰 Матеріал/Інструмент: {data.get('material', '-')}\n"
            f"⏰ Термін: {data.get('deadline', '-')}\n"
            f"ℹ️ Додаткова інформація: {data.get('additional_info', '-')}"
        )

        try:
            await context.bot.send_message(ADMIN_CHAT_ID, message)
            await update.message.reply_text("✅ Ваша заявка успішно відправлена. Дякуємо!")
        except Exception as e:
            logger.error(f"Помилка відправки заявки: {e}")
            await update.message.reply_text("❌ Помилка відправки заявки. Спробуйте пізніше.")

    async def run_webhook(self):
        # Initialize the application first
        await self.application.initialize()
        await self.application.start()
        
        app = web.Application()

        async def handle_post(request):
            try:
                data = await request.json()
                logger.info(f"Received webhook data: {data}")
                update = Update.de_json(data, self.application.bot)
                
                # Process the update through the application
                await self.application.process_update(update)
                
                return web.Response(text="OK")
            except Exception as e:
                logger.error(f"Error processing webhook: {e}")
                return web.Response(text="ERROR", status=500)

        async def handle_get(request):
            return web.Response(text="Webhook працює")

        async def handle_health(request):
            return web.Response(text="OK")

        app.router.add_post('/webhook', handle_post)
        app.router.add_get('/webhook', handle_get)
        app.router.add_get('/health', handle_health)
        app.router.add_get('/', handle_health)  # For UptimeRobot

        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', PORT)
        await site.start()

        webhook_url = f"{WEBHOOK_URL}/webhook"
        await self.application.bot.set_webhook(webhook_url)
        logger.info(f"Webhook встановлено: {webhook_url}")
        logger.info("Бот запущено на webhook")

        # Keep running
        try:
            while True:
                await asyncio.sleep(3600)
        except KeyboardInterrupt:
            logger.info("Bot stopped")
        finally:
            await self.application.stop()
            await self.application.shutdown()

async def main():
    bot = TelegramWorkerBot()
    await bot.run_webhook()

if __name__ == '__main__':
    asyncio.run(main())
