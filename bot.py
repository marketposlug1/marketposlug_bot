import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

TOKEN = "8283929613:AAGsabwYn_34VBsEwByIFB3F11OMYQcr-X0"
MANAGER_CHAT_ID = -1003098912428  # ID чата менеджера

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Состояния опроса
user_data = {}

# Вопросы
questions = [
    "Ваше ім'я 📝",
    "На який об'єкт потрібно матеріал/інструмент? 🏗️",
    "На коли потрібно? ⏰",
    "Варіанти терміну:"
]

# Варианты ответа на последний вопрос
deadline_buttons = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Терміново до 1 години ⏱️")],
        [KeyboardButton(text="До 18:00 🕕")],
        [KeyboardButton(text="Завтра до 🌤️")]
    ],
    resize_keyboard=True,
    one_time_keyboard=True
)

# Запуск бота
@dp.message(Command("start"))
async def start(message: types.Message):
    user_id = message.from_user.id
    user_data[user_id] = {"step": 0, "answers": []}
    await message.answer("Привіт! Давай заповнимо заявку для матеріалів/інструментів.")
    await message.answer(questions[0])

@dp.message()
async def handle_message(message: types.Message):
    user_id = message.from_user.id
    if user_id not in user_data:
        await message.answer("Натисніть /start щоб почати заповнення заявки.")
        return

    step = user_data[user_id]["step"]
    user_data[user_id]["answers"].append(message.text)

    if step == 0:
        # Переход на следующий вопрос
        user_data[user_id]["step"] += 1
        await message.answer(questions[1])
    elif step == 1:
        user_data[user_id]["step"] += 1
        await message.answer(questions[2])
    elif step == 2:
        user_data[user_id]["step"] += 1
        await message.answer("Оберіть варіант терміну:", reply_markup=deadline_buttons)
    elif step == 3:
        user_data[user_id]["step"] += 1
        user_data[user_id]["answers"].append(message.text)
        # Отправка заявки в чат менеджера
        answers = user_data[user_id]["answers"]
        text = (
            f"Нова заявка від {answers[0]}:\n"
            f"Об'єкт: {answers[1]}\n"
            f"На коли: {answers[2]}\n"
            f"Термін: {answers[3]}"
        )
        await bot.send_message(MANAGER_CHAT_ID, text)
        await message.answer("Дякуємо! Ваша заявка надіслана ✅", reply_markup=types.ReplyKeyboardRemove())
        # Очистка данных пользователя
        user_data.pop(user_id)
