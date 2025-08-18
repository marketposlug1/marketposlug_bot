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
        self.application.add_handler(CommandHandler("webhook_info", self.webhook_info_command))
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
            "Вас вітає Маркет Послуг №1! 🚧\n\n"
            "Залиште заявку для отримання всього, що вам необхідно!\n\n"
            "Напишіть, будь ласка, ваше призвіще 📝"
        )

    async def webhook_info_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            webhook_info = await context.bot.get_webhook_info()
            info_text = (
                f"🔗 **Webhook Info:**\n"
                f"URL: `{webhook_info.url}`\n"
                f"Has Custom Certificate: {webhook_info.has_custom_certificate}\n"
                f"Pending Update Count: {webhook_info.pending_update_count}\n"
                f"Last Error Date: {webhook_info.last_error_date}\n"
                f"Last Error Message: {webhook_info.last_error_message}\n"
                f"Max Connections: {webhook_info.max_connections}"
            )
            await update.message.reply_text(info_text, parse_mode='Markdown')
        except Exception as e:
            await update.message.reply_text(f"Error getting webhook info: {e}")

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "Для початку надішліть /start.\n"
            "Просто відповідайте на запитання, що з'являться.\n"
            "По кнопках обирайте варіанти."
        )

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        text = update.message.text.strip()
        
        logger.info(f"Processing message from user {user_id}: {text}")

        if user_id not in worker_responses:
            await update.message.reply_text("Будь ласка, надішліть /start щоб почати.")
            return

        stage = worker_responses[user_id]['stage']
        data = worker_responses[user_id]['data']

        if stage == 'ask_name':
            data['name'] = text
            worker_responses[user_id]['stage'] = 'ask_object'
            await update.message.reply_text("Адреса об'єкту 🏗️")

        elif stage == 'ask_object':
            data['object'] = text
            worker_responses[user_id]['stage'] = 'ask_material'
            await update.message.reply_text("Який матеріал або інструмент потрібен + кількість (назва з інтернету)? 🧰")

        elif stage == 'ask_material':
            data['material'] = text
            worker_responses[user_id]['stage'] = 'ask_deadline'
            keyboard = [
                [InlineKeyboardButton("🔴 Терміново до 1 години", callback_data="deadline_urgent")],
                [InlineKeyboardButton("🟡 До 18:00", callback_data="deadline_today")],
                [InlineKeyboardButton("🟢 Завтра до 12:00", callback_data="deadline_tomorrow")],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            logger.info(f"Sending keyboard to user {user_id}")
            await update.message.reply_text("Термін доставки оберіть варіант ⏰", reply_markup=reply_markup)

        elif stage == 'ask_additional':
            data['additional_info'] = text
            worker_responses[user_id]['stage'] = 'ready_to_submit'
            
            # Create keyboard with submit button after additional info
            keyboard = [
                [InlineKeyboardButton("📤 Відправити заявку", callback_data="submit_request")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                "Дякуємо за додаткову інформацію! Натисніть кнопку для відправки заявки:",
                reply_markup=reply_markup
            )

    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        user_id = query.from_user.id
        data = query.data
        
        logger.info(f"CALLBACK QUERY - Button clicked by user {user_id}: {data}")
        logger.info(f"CALLBACK QUERY - Full query object: {query}")
        
        # Answer the callback query FIRST to stop loading animation
        try:
            await query.answer()
            logger.info(f"CALLBACK QUERY - Successfully answered callback for user {user_id}")
        except Exception as e:
            logger.error(f"CALLBACK QUERY - Error answering callback: {e}")
            return

        if user_id not in worker_responses:
            logger.warning(f"CALLBACK QUERY - User {user_id} not found in worker_responses")
            try:
                await query.edit_message_text("Сесія втрачена. Почніть заново /start.")
            except Exception as e:
                logger.error(f"CALLBACK QUERY - Error editing message: {e}")
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

            logger.info(f"CALLBACK QUERY - User {user_id} selected deadline: {selected}")

            # Create keyboard with submit button
            keyboard = [
                [InlineKeyboardButton("📤 Відправити заявку", callback_data="submit_request")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            try:
                await query.edit_message_text(
                    f"Ви вибрали: {selected}\n\n"
                    "Напишіть додаткову інформацію або натисніть кнопку для відправки заявки:",
                    reply_markup=reply_markup
                )
                logger.info(f"CALLBACK QUERY - Successfully updated message for user {user_id}")
            except Exception as e:
                logger.error(f"CALLBACK QUERY - Error updating message: {e}")
                # Fallback: send new message if editing fails
                await context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text=f"Ви вибрали: {selected}\n\nНапишіть додаткову інформацію або натисніть кнопку для відправки заявки:",
                    reply_markup=reply_markup
                )

        elif data == "submit_request":
            logger.info(f"CALLBACK QUERY - User {user_id} submitting request")
            
            # If no additional info was provided, set default
            if 'additional_info' not in worker_responses[user_id]['data']:
                worker_responses[user_id]['data']['additional_info'] = "Не вказано"
            
            try:
                # Send request to admin chat
                await self.send_request_from_callback(query, context, user_id)
                
                # Remove user from responses
                del worker_responses[user_id]
                
                await query.edit_message_text("✅ Ваша заявка успішно відправлена. Дякуємо!")
                logger.info(f"CALLBACK QUERY - Successfully submitted request for user {user_id}")
                
            except Exception as e:
                logger.error(f"CALLBACK QUERY - Error submitting request: {e}")
                await query.edit_message_text("❌ Помилка відправки заявки. Спробуйте пізніше.")

    async def send_request_from_callback(self, query, context: ContextTypes.DEFAULT_TYPE, user_id: int):
        """Send request when called from callback query"""
        data = worker_responses[user_id]['data']

        message = (
            f"📢 Нова заявка:\n"
            f"👤 Ім'я: {data.get('name', '-')}\n"
            f"🏗️ Об'єкт: {data.get('object', '-')}\n"
            f"🧰 Матеріал/Інструмент: {data.get('material', '-')}\n"
            f"⏰ Термін: {data.get('deadline', '-')}\n"
            f"ℹ️ Додаткова інформація: {data.get('additional_info', '-')}"
        )

        await context.bot.send_message(ADMIN_CHAT_ID, message)

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
                
                # Enhanced logging for callback queries
                if 'callback_query' in data:
                    logger.info(f"WEBHOOK - Callback query detected: {data['callback_query']}")
                elif 'message' in data:
                    logger.info(f"WEBHOOK - Regular message detected: {data['message']}")
                else:
                    logger.warning(f"WEBHOOK - Unknown update type: {list(data.keys())}")
                
                update = Update.de_json(data, self.application.bot)
                
                if update is None:
                    logger.error("WEBHOOK - Failed to parse update from JSON")
                    return web.Response(text="ERROR: Failed to parse update", status=400)
                
                logger.info(f"WEBHOOK - Successfully parsed update: {update.update_id}")
                
                # Process the update through the application
                await self.application.process_update(update)
                logger.info(f"WEBHOOK - Successfully processed update: {update.update_id}")
                
                return web.Response(text="OK")
            except Exception as e:
                logger.error(f"WEBHOOK - Error processing webhook: {e}", exc_info=True)
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
        
        # Set webhook with better error handling and forced reset
        try:
            # First, delete any existing webhook
            await self.application.bot.delete_webhook(drop_pending_updates=True)
            logger.info("Deleted existing webhook")
            
            # Wait a moment
            await asyncio.sleep(2)
            
            # Set the new webhook
            result = await self.application.bot.set_webhook(
                url=webhook_url,
                drop_pending_updates=True,
                max_connections=40,
                allowed_updates=["message", "callback_query"]
            )
            logger.info(f"Webhook встановлено: {webhook_url}, result: {result}")
            
            # Verify webhook was set
            webhook_info = await self.application.bot.get_webhook_info()
            logger.info(f"Webhook verification: {webhook_info}")
            
        except Exception as e:
            logger.error(f"Error setting webhook: {e}")
            raise
        
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
