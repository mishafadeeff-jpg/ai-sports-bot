import asyncio
import logging
import os
import uvicorn
from fastapi import FastAPI
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

import config
import database
from handlers import start, sports, payment, admin

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Создаем веб-приложение FastAPI для Render
app = FastAPI()

@app.get("/")
async def health_check():
    return {"status": "ok", "bot": "AI Sports Analytics Bot is Running 24/7"}

async def start_telegram_bot():
    """Асинхронный запуск Telegram бота."""
    print("==========================================")
    print("[START] ЗАПУСК БОТА ИИ-АНАЛИТИКИ СТАВОК НА СПОРТ...")
    print("==========================================")
    
    # 1. Инициализация базы данных
    await database.init_db()
    print("[OK] База данных SQLite успешно инициализирована.")
    
    # 2. Инициализация Bot и Dispatcher
    bot = Bot(token=config.BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    
    # 3. Подключение роутеров
    dp.include_router(start.router)
    dp.include_router(sports.router)
    dp.include_router(payment.router)
    dp.include_router(admin.router)
    
    # 4. Пропускаем накопленные апдейты и запускаем бот
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        print(f"[OK] Бот запущен на Render! Админы: {config.ADMIN_IDS}")
        await dp.start_polling(bot)
    except Exception as e:
        print(f"[ERROR] Ошибка запуска бота: {e}")

@app.on_event("startup")
async def on_startup():
    # Запускаем фоновую задачу бота при старте сервера FastAPI
    asyncio.create_task(start_telegram_bot())

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run("bot:app", host="0.0.0.0", port=port)
