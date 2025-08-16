import os
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiohttp import web
import threading

# ===== Настройки =====
API_TOKEN = os.getenv("API_TOKEN")   # Токен бота
MANAGER_CHAT_ID = int(os.getenv("MANAGER_CHAT_ID"))  # ID чата для заявок

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# ===== Логика бота =====
@dp.message(commands=["start"])
async def start_handler(message: types.Message):
    await message.answer("Привіт! 👋\nДавайте оформимо заявку.\nВведіть, будь ласка, ваше ім'я:")

    @dp.message()
    async def name_handler(msg: types.Message):
        user_data = {"name": msg.text}

        await msg.answer("На який об'єкт потрібен матеріал/інструмент? 🏗️")

        @dp.message()
        async def object_handler(msg2: types.Message):
            user_data["object"] = msg2.text

            kb = ReplyKeyboardMarkup(
                keyboard=[
                    [KeyboardButton("⏰ Терміново до 1 години")],
                    [KeyboardButton("🕕 До 18:00")],
                    [KeyboardButton("🌤️ Завтра до 12")]
                ],
                resize_keyboard=True,
                one_time_keyboard=True
            )
            await msg2.answer("На коли потрібно? 📅", reply_markup=kb)

            @dp.message()
            async def deadline_handler(msg3: types.Message):
                user_data["deadline"] = msg3.text

                text = (
                    f"📌 Нова заявка:\n\n"
                    f"👤 Ім'я: {user_data['name']}\n"
                    f"🏗️ Об'єкт: {user_data['object']}\n"
                    f"⏳ Термін: {user_data['deadline']}"
                )

                await bot.send_message(MANAGER_CHAT_ID, text)
                await msg3.answer("✅ Ваша заявка прийнята!", reply_markup=ReplyKeyboardRemove())

# ===== Мини веб-сервер для Render =====
async def handle(request):
    return web.Response(text="Bot is alive ✅")

app = web.Application()
app.router.add_get("/", handle)

def run_web():
    web.run_app(app, host="0.0.0.0", port=int(os.getenv("PORT", 10000)))

threading.Thread(target=run_web).start()

# ===== Запуск =====
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
