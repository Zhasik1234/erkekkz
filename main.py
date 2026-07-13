# import asyncio
# import logging
# import sys
# from os import getenv


# from aiogram import Bot, Dispatcher, html, types, BaseMiddleware
# from aiogram.client.default import DefaultBotProperties
# from aiogram.enums import ParseMode
# from config import TOKEN
# from app.handler import router
# from aiogram.types import FSInputFile


# bot = Bot(token=TOKEN)
# dp = Dispatcher()

# async def main():
#     dp.include_router(router)
#     await dp.start_polling(bot)
    
    
# if __name__ == "__main__":
#     logging.basicConfig(level=logging.INFO)
#     try:
#         asyncio.run(main())
#     except KeyboardInterrupt:
#         print('Exit')



# import asyncio
# import logging
# import sys
# import os
# from dotenv import load_dotenv

# # Загружаем данные из config.env до импортов, использующих переменные
# load_dotenv("config.env")

# from aiogram import Bot, Dispatcher, html, types, BaseMiddleware
# from aiogram.client.default import DefaultBotProperties
# from aiogram.enums import ParseMode
# from aiogram.types import FSInputFile

# from app.handler import router

# TOKEN = os.getenv("TOKEN")

# bot = Bot(token=TOKEN)
# dp = Dispatcher()

# async def main():
#     dp.include_router(router)
#     await dp.start_polling(bot)
    
# if __name__ == "__main__":
#     logging.basicConfig(level=logging.INFO)
#     try:
#         asyncio.run(main())
#     except KeyboardInterrupt:
#         print('Exit')



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