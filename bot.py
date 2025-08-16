from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
import asyncio

API_TOKEN = "8283929613:AAGsabwYn_34VBsEwByIFB3F11OMYQcr-X0"  # Твой токен бота
MANAGER_CHAT_ID = -1003098912428  # ID закрытого чата для заявок

bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Описание состояний для FSM
class Form(StatesGroup):
    name = State()
    object_name = State()
    material_tool = State()
    date_needed = State()

# Стартовая команда - начинает опрос
@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await message.answer("Ваше ім'я 🖊️")
    await Form.name.set()

# Получение имени
@dp.message(Form.name)
async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("На який об'єкт потрібно матеріал/інструмент? 🏗️")
    await Form.object_name.set()

# Получение объекта
@dp.message(Form.object_name)
async def process_object(message: types.Message, state: FSMContext):
    await state.update_data(object_name=message.text)
    await message.answer("Який матеріал або інструмент потрібен? 🔧")
    await Form.material_tool.set()

# Получение материала/инструмента
@dp.message(Form.material_tool)
async def process_material_tool(message: types.Message, state: FSMContext):
    await state.update_data(material_tool=message.text)
    await message.answer(
        "На коли потрібно? ⏰\n"
        "⚡ Терміново до 1 години\n"
        "🕕 До 18:00\n"
        "🌤️ Завтра до 12"
    )
    await Form.date_needed.set()

# Получение времени и отправка заявки в закрытый чат
@dp.message(Form.date_needed)
async def process_date_needed(message: types.Message, state: FSMContext):
    data = await state.get_data()
    text = (
        f"Нова заявка:\n"
        f"Ім'я: {data['name']}\n"
        f"Об'єкт: {data['object_name']}\n"
        f"Матеріал/Інструмент: {data['material_tool']}\n"
        f"На коли: {message.text}"
    )
    await bot.send_message(MANAGER_CHAT_ID, text)
    await message.answer("Заявка відправлена ✅")
    await state.clear()

# Запуск бота
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

