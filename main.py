

import asyncio
import logging
import sys
import os
from dotenv import load_dotenv

# Загружаем данные из config.env
load_dotenv("config.env")

from aiogram import Bot, Dispatcher
from app.handler import router
from database import init_db  # Подключаем функцию запуска базы данных

TOKEN = os.getenv("TOKEN")
if not TOKEN:
    print("Ошибка: Переменная окружения TOKEN не найдена!")
    sys.exit(1) # Завершить работу, если токена нет

bot = Bot(token=TOKEN)

bot = Bot(token=TOKEN)
dp = Dispatcher()

async def main():
    # Инициализируем базу данных перед запуском бота
    await init_db()
    
    dp.include_router(router)
    await dp.start_polling(bot)
    
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print('Exit')


