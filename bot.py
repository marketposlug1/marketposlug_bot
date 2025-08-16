import os
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from aiogram.filters import Text
from aiogram import F
import asyncio

# Получаем токен и ID менеджера из переменных окружения
API_TOKEN = os.getenv("API_TOKEN")
MANAGER_CHAT_ID = int(os.getenv("MANAGER_CHAT_ID"))

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# Вопросы и клавиатура
async def start_handler(message: types.Message):
    await message.answer("Привет! Давай оформим заявку на материал или инструмент. 😊\nВаше имя:")
    dp.register_message_handler(name_handler, state=None)

async def name_handler(message: types.Message):
    message.user_data = {"name": message.text}
    await message.answer("На какой объект нужно материал/инструмент? 🏗️")
    dp.register_message_handler(object_handler, state=None)

async def object_handler(message: types.Message):
    message.user_data["object"] = message.text

    # Создаём клавиатуру с вариантами сроков
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton("Терміново до 1 години ⏰")],
            [KeyboardButton("До 18:00 🕕")],
            [KeyboardButton("Завтра до 12 🌤️")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await message.answer("На коли потрібно?", reply_markup=kb)
    dp.register_message_handler(deadline_handler, state=None)

async def deadline_handler(message: types.Message):
    message.user_data["deadline"] = message.text

    # Отправляем заявку менеджеру
    text = f"Нова заявка:\n\n" \
           f"Ім'я: {message.user_data['name']}\n" \
           f"Об'єкт: {message.user_data['object']}\n" \
           f"Термін: {message.user_data['deadline']}"
    await bot.send_message(MANAGER_CHAT_ID, text)
    await message.answer("Ваша заявка прийнята! ✅", reply_markup=types.ReplyKeyboardRemove())

# Регистрируем старт
dp.message.register(start_handler, commands=["start"])

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
