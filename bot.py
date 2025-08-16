import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = int(os.getenv("CHAT_ID"))

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Клавиатура для выбора срока
keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="⏰ Терміново до 1 години")],
        [KeyboardButton(text="🕕 До 18:00")],
        [KeyboardButton(text="🌤 Завтра до 12")]
    ],
    resize_keyboard=True
)

# Список вопросов
questions = [
    "Ваше ім'я 🖊",
    "На який об'єкт потрібно матеріал/інструмент? 🏗",
    "На коли потрібно? ⏳"
]

# Словарь для хранения ответов
user_answers = {}

@dp.message(Command("start"))
async def start(message: types.Message):
    user_answers[message.from_user.id] = []
    await message.answer("Привіт! Почнемо заповнювати заявку.")
    await message.answer(questions[0])

@dp.message()
async def answer(message: types.Message):
    user_id = message.from_user.id

    if user_id not in user_answers:
        await message.answer("Натисніть /start для початку.")
        return

    user_answers[user_id].append(message.text)

    if len(user_answers[user_id]) < len(questions):
        await message.answer(questions[len(user_answers[user_id])])
    else:
        # Отправка всех ответов в общий чат
        answers_text = "\n".join(
            f"{q} {a}" for q, a in zip(questions, user_answers[user_id])
        )
        await bot.send_message(CHAT_ID, f"Нова заявка:\n\n{answers_text}")
        await message.answer("Дякуємо! Ваша заявка надіслана.")
        user_answers.pop(user_id)
