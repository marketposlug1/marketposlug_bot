import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
import asyncio
from datetime import datetime

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configuration - your actual tokens
BOT_TOKEN = "8283929613:AAGsabwYn_34VBsEwByIFB3F11OMYQcr-X0"
ADMIN_CHAT_ID = "-1003098912428"
PORT = int(os.getenv('PORT', 8000))  # Platform auto-assigns this
WEBHOOK_URL = os.getenv('WEBHOOK_URL', '')  # Platform provides this

# Store worker responses temporarily (in production, use a database)
worker_responses = {}

class TelegramWorkerBot:
    def __init__(self):
        self.application = Application.builder().token(BOT_TOKEN).build()
        self.setup_handlers()
    
    def setup_handlers(self):
        """Setup all bot command and message handlers"""
        # Commands
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        
        # Callback handlers for inline buttons
        self.application.add_handler(CallbackQueryHandler(self.button_callback))
        
        # Message handlers
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user = update.effective_user
        welcome_text = (
            f"👋 Welcome {user.first_name}!\n\n"
            "I'm your work request bot. Here's how to use me:\n\n"
            "📝 Just send me your request and I'll walk you through some questions.\n"
            "📤 Once complete, I'll forward everything to the admin.\n\n"
            "Type anything to get started!"
        )
        await update.message.reply_text(welcome_text)
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_text = (
            "🤖 **Worker Request Bot Help**\n\n"
            "**Commands:**\n"
            "• /start - Start the bot\n"
            "• /help - Show this help message\n\n"
            "**How it works:**\n"
            "1. Send your work request\n"
            "2. Answer the follow-up questions\n"
            "3. I'll send everything to the admin\n\n"
            "Just send me any message to begin!"
        )
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle regular text messages"""
        user_id = update.effective_user.id
        message_text = update.message.text
        
        # Initialize user session if not exists
        if user_id not in worker_responses:
            worker_responses[user_id] = {
                'stage': 'initial_request',
                'data': {},
                'timestamp': datetime.now()
            }
        
        user_session = worker_responses[user_id]
        stage = user_session['stage']
        
        if stage == 'initial_request':
            await self.handle_initial_request(update, context, message_text)
        elif stage == 'priority':
            await self.handle_priority(update, context, message_text)
        elif stage == 'deadline':
            await self.handle_deadline(update, context, message_text)
        elif stage == 'additional_info':
            await self.handle_additional_info(update, context, message_text)
    
    async def handle_initial_request(self, update: Update, context: ContextTypes.DEFAULT_TYPE, message_text: str):
        """Handle the initial work request"""
        user_id = update.effective_user.id
        worker_responses[user_id]['data']['request'] = message_text
        worker_responses[user_id]['stage'] = 'priority'
        
        # Create priority buttons
        keyboard = [
            [InlineKeyboardButton("🔴 High", callback_data="priority_high")],
            [InlineKeyboardButton("🟡 Medium", callback_data="priority_medium")],
            [InlineKeyboardButton("🟢 Low", callback_data="priority_low")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "Got your request! 📝\n\n"
            "What's the priority level?",
            reply_markup=reply_markup
        )
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle inline button clicks"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        data = query.data
        
        if data.startswith("priority_"):
            priority = data.replace("priority_", "").capitalize()
            worker_responses[user_id]['data']['priority'] = priority
            worker_responses[user_id]['stage'] = 'deadline'
            
            await query.edit_message_text(
                f"Priority set to: {priority}\n\n"
                "When do you need this completed? (e.g., 'Today', 'By Friday', 'Next week')"
            )
    
    async def handle_deadline(self, update: Update, context: ContextTypes.DEFAULT_TYPE, message_text: str):
        """Handle deadline information"""
        user_id = update.effective_user.id
        worker_responses[user_id]['data']['deadline'] = message_text
        worker_responses[user_id]['stage'] = 'additional_info'
        
        await update.message.reply_text(
            "⏰ Deadline noted!\n\n"
            "Any additional information or special requirements? (or type 'none' to finish)"
        )
    
    async def handle_additional_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE, message_text: str):
        """Handle additional information and send to admin"""
        user_id = update.effective_user.id
        user = update.effective_user
        
        worker_responses[user_id]['data']['additional_info'] = message_text
        
        # Format the complete request
        data = worker_responses[user_id]['data']
        timestamp = worker_responses[user_id]['timestamp'].strftime("%Y-%m-%d %H:%M:%S")
        
        admin_message = (
            "📬 **New Work Request**\n\n"
            f"👤 **From:** {user.first_name} {user.last_name or ''} (@{user.username or 'no_username'})\n"
            f"🆔 **User ID:** {user_id}\n"
            f"📅 **Submitted:** {timestamp}\n\n"
            f"📝 **Request:** {data['request']}\n\n"
            f"🔹 **Priority:** {data['priority']}\n"
            f"⏰ **Deadline:** {data['deadline']}\n"
            f"ℹ️ **Additional Info:** {data['additional_info']}\n\n"
            "---\n"
            f"Reply to this message to respond to {user.first_name}"
        )
        
        try:
            # Send to admin
            await context.bot.send_message(
                chat_id=ADMIN_CHAT_ID,
                text=admin_message,
                parse_mode='Markdown'
            )
            
            # Confirm to worker
            await update.message.reply_text(
                "✅ **Request Submitted Successfully!**\n\n"
                "Your request has been sent to the admin. "
                "You'll receive a response soon.\n\n"
                "Feel free to send another request anytime!",
                parse_mode='Markdown'
            )
            
            # Clean up session
            del worker_responses[user_id]
            
        except Exception as e:
            logger.error(f"Error sending to admin: {e}")
            await update.message.reply_text(
                "❌ Sorry, there was an error submitting your request. Please try again later."
            )
    
    async def run_webhook(self):
        """Run bot with webhook (for Render deployment)"""
        await self.application.initialize()
        await self.application.start()
        
        # Set webhook
        webhook_url = f"{WEBHOOK_URL}/webhook"
        await self.application.bot.set_webhook(webhook_url)
        
        # Start webhook server
        await self.application.updater.start_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path="/webhook",
            webhook_url=webhook_url
        )
        
        logger.info(f"Bot started with webhook: {webhook_url}")
        
        # Keep running - simplified approach
        import asyncio
        try:
            # Just keep the event loop running
            while True:
                await asyncio.sleep(3600)  # Sleep for 1 hour, repeat
        except KeyboardInterrupt:
            logger.info("Bot stopped")
        finally:
            await self.application.stop()
            await self.application.shutdown()
    
    async def run_polling(self):
        """Run bot with polling (for local development)"""
        await self.application.start()
        await self.application.updater.start_polling()
        
        logger.info("Bot started with polling")
        
        import signal
        import asyncio
        
        # Wait for shutdown signal
        stop_event = asyncio.Event()
        
        def signal_handler():
            stop_event.set()
        
        # Handle shutdown gracefully  
        for sig in [signal.SIGINT, signal.SIGTERM]:
            signal.signal(sig, lambda s, f: signal_handler())
        
        await stop_event.wait()

async def main():
    """Main function to run the bot"""
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN environment variable is required!")
        return
    
    if not ADMIN_CHAT_ID:
        logger.error("ADMIN_CHAT_ID environment variable is required!")
        return
    
    bot = TelegramWorkerBot()
    
    # Use webhook if WEBHOOK_URL is set (production), otherwise polling (development)
    if WEBHOOK_URL:
        await bot.run_webhook()
    else:
        await bot.run_polling()

if __name__ == '__main__':
    asyncio.run(main())
