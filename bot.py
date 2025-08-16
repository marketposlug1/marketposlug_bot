import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
import asyncio

logging.basicConfig(level=logging.INFO)

TOKEN = "8283929613:AAGsabwYn_34VBsEwByIFB3F11OMYQcr-X0"
MANAGER_CHAT_ID = -1003098912428  # Ваш чат менеджера

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Данные пользователей
user_data = {}

# Вопросы
questions = [
    "Ваше ім'я 📝",
    "На який об'єкт потрібно матеріал/інструмент? 🏗️",
    "На коли потрібно? ⏰",
]

# Кнопки для последнего вопроса
deadline_buttons = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Терміново до 1 години ⏱️")],
        [KeyboardButton(text="До 18:00 🕕")],
        [KeyboardButton(text="Завтра до 🌤️")]
    ],
    resize_keyboard=True,
    one_time_keyboard=True
)

# /start
@dp.message(Command("start"))
async def start(message: types.Message):
    user_id = message.from_user.id
    user_data[user_id] = {"step": 0, "answers": []}
    await message.answer("Привіт! Давай заповнимо заявку для матеріалів/інструментів.")
    await message.answer(questions[0])

# Основной обработчик
@dp.message()
async def handle_message(message: types.Message):
    user_id = message.from_user.id
    if user_id not in user_data:
        await message.answer("Натисніть /start щоб почати заповнення заявки.")
        return

    step = user_data[user_id]["step"]
    user_data[user_id]["answers"].append(message.text)

    if step == 0:
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
        answers = user_data[user_id]["answers"]
        text = (
            f"Нова заявка від {answers[0]}:\n"
            f"Об'єкт: {answers[1]}\n"
            f"На коли: {answers[2]}\n"
            f"Термін: {answers[3]}"
        )
        await bot.send_message(MANAGER_CHAT_ID, text)
        await message.answer("Дякуємо! Ваша заявка надіслана ✅", reply_markup=ReplyKeyboardRemove())
        user_data.pop(user_id)

if __name__ == "__main__":
    import asyncio
    from aiogram import executor

    asyncio.run(dp.start_polling(bot))
