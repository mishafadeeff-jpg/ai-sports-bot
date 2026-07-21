@echo off
chcp 65001 > NUL
title AI Sports Bot
echo ===================================================
echo   ЗАПУСК TELEGRAM БОТА ИИ-АНАЛИТИКИ СТАВОК НА СПОРТ
echo ===================================================
echo.

cd /d "%~dp0"

echo 1. Установка необходимых библиотек...
pip install aiogram aiosqlite python-dotenv requests google-generativeai

echo.
echo 2. Запуск бота...
python bot.py

pause
