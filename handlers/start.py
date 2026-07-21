from aiogram import Router, F, types
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

import database
import config

router = Router()

def get_main_reply_keyboard():
    """Главная нижняя клавиатура быстрого доступа."""
    kb = [
        [KeyboardButton(text="🌟 Прогноз Дня"), KeyboardButton(text="🔍 Анализ матча")],
        [KeyboardButton(text="👑 VIP Подписка"), KeyboardButton(text="📊 Статистика проходимости")],
        [KeyboardButton(text="❓ Помощь / О боте")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_main_inline_keyboard(is_vip: bool):
    """Инлайн клавиатура под главным сообщением."""
    builder = [
        [InlineKeyboardButton(text="🌟 Прогноз Дня (VIP)", callback_data="get_daily_forecast")],
        [InlineKeyboardButton(text="🔍 Проанализировать любой матч", callback_data="start_match_analysis")]
    ]
    if not is_vip:
        builder.append([InlineKeyboardButton(text="⚡ Купить VIP-доступ по СБП", callback_data="open_vip_menu")])
    else:
        builder.append([InlineKeyboardButton(text="👑 Ваши VIP привилегии активны", callback_data="open_vip_menu")])
        
    return InlineKeyboardMarkup(inline_keyboard=builder)

@router.message(CommandStart())
async def start_handler(message: types.Message):
    """Обработчик команды /start."""
    user = await database.get_or_create_user(
        user_id=message.from_user.id,
        username=message.from_user.username or "",
        full_name=message.from_user.full_name
    )
    is_vip = await database.check_vip_status(message.from_user.id)
    
    status_text = "👑 **Статус: VIP ПРЕМИУМ**" if is_vip else f"🆓 **Бесплатных анализов:** {user['free_requests_left']} из 2"
    
    welcome_text = (
        f"👋 **Здравствуйте, {message.from_user.first_name}!**\n\n"
        f"🤖 Добро пожаловать в **AI Sports Analyst** — передовую нейросетевую систему прогнозирования спортивных событий.\n\n"
        f"🎯 **Что умеет бот:**\n"
        f"• Вычислять точные математические вероятности исходов\n"
        f"• Анализировать форму команд, очные встречи и xG показатели\n"
        f"• Находить недооцененные коэффициенты (Value Bets)\n"
        f"• Давать советы по управлению вашим депозитом\n\n"
        f"{status_text}\n\n"
        f"Выберите нужное действие в меню ниже или введите названия команд для анализа:"
    )
    
    await message.answer(
        welcome_text,
        parse_mode="Markdown",
        reply_markup=get_main_reply_keyboard()
    )
    
    await message.answer(
        "⚡ **Главное ИИ-меню:**",
        reply_markup=get_main_inline_keyboard(is_vip)
    )

@router.callback_query(F.data == "open_main_menu")
async def open_main_menu_callback(callback: types.CallbackQuery):
    """Возврат в главное меню через инлайн кнопку."""
    is_vip = await database.check_vip_status(callback.from_user.id)
    
    text = "⚡ **Главное меню ИИ-Аналитика:**\nВыберите нужный раздел:"
    await callback.message.edit_text(text, reply_markup=get_main_inline_keyboard(is_vip))

@router.message(F.text == "❓ Помощь / О боте")
async def help_handler(message: types.Message):
    """Справка о боте."""
    help_text = (
        "❓ **КАК РАБОТАЕТ ИИ-АНАЛИТИК?**\n\n"
        "1. **Прогноз Дня:** Вы получаете разбор самого надежного матча дня с глубокой аналитикой от математической модели.\n"
        "2. **Поиск по матчу:** Вы можете ввести названия двух команд (например: `Барселона - Реал` или `СКА - ЦСКА`), и нейросеть мгновенно сформирует отчет.\n"
        "3. **Управление банком:** Наш алгоритм никогда не рекомендует ставить весь баланс! Безопасный размер ставки — не более 3-5% от депозита.\n\n"
        "📩 **Поддержка / Вопросы по оплате СБП:** @admin"
    )
    await message.answer(help_text, parse_mode="Markdown")
