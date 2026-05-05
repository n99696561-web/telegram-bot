import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from openai import OpenAI

# Ключи берутся из переменных окружения (настрой на Render)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

if not TELEGRAM_BOT_TOKEN or not DEEPSEEK_API_KEY:
    raise Exception("Ошибка: не заданы переменные окружения! Добавьте TELEGRAM_BOT_TOKEN и DEEPSEEK_API_KEY на Render")

logging.basicConfig(level=logging.INFO)

client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")
bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("Привет! Я бот на DeepSeek! Задай любой вопрос 🚀")

@dp.message()
async def answer_to_ai(message: types.Message):
    if not message.text:
        await message.answer("Отправьте текст!")
        return
    
    thinking_msg = await message.answer("🤔 Думаю...")
    
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "Ты полезный помощник"},
                {"role": "user", "content": message.text}
            ]
        )
        answer = response.choices[0].message.content
        await thinking_msg.edit_text(answer)
    except Exception as e:
        await thinking_msg.edit_text(f"Ошибка: {e}")

async def main():
    print("✅ Бот запущен на Render!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
