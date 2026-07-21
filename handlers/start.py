from aiogram import Router, F, types
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

import database
import config

router = Router()

def get_main_reply_keyboard():
    """Главная нижняя клавиатура быстрого доступа."""
    kb = [
        [KeyboardButton(text="🌟 Прогноз Дня"), KeyboardButton(text="🎰 ИИ-Экспресс (3.00+)")],
        [KeyboardButton(text="🔍 Анализ матча"), KeyboardButton(text="👑 VIP Подписка")],
        [KeyboardButton(text="🤝 Реферальная программа"), KeyboardButton(text="📊 Статистика")],
        [KeyboardButton(text="❓ Помощь / О боте")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_main_inline_keyboard(is_vip: bool):
    """Инлайн клавиатура под главным сообщением."""
    builder = [
        [InlineKeyboardButton(text="🌟 Прогноз Дня (VIP)", callback_data="get_daily_forecast")],
        [InlineKeyboardButton(text="🎰 ИИ-Экспресс Дня (Коэфф 3.00+)", callback_data="get_express_forecast")],
        [InlineKeyboardButton(text="🔍 Проанализировать любой матч", callback_data="start_match_analysis")],
        [InlineKeyboardButton(text="🤝 Получить VIP Бесплатно (За друзей)", callback_data="open_referral_menu")]
    ]
    if not is_vip:
        builder.append([InlineKeyboardButton(text="⚡ Купить VIP-доступ по СБП", callback_data="open_vip_menu")])
    else:
        builder.append([InlineKeyboardButton(text="👑 Ваши VIP привилегии активны", callback_data="open_vip_menu")])
        
    return InlineKeyboardMarkup(inline_keyboard=builder)

@router.message(CommandStart())
async def start_handler(message: types.Message):
    """Обработчик команды /start с поддержкой реферальных ссылок."""
    args = message.text.split()
    referrer_id = 0
    if len(args) > 1 and args[1].startswith("ref_"):
        try:
            referrer_id = int(args[1].replace("ref_", ""))
        except ValueError:
            pass
            
    user = await database.get_or_create_user(
        user_id=message.from_user.id,
        username=message.from_user.username or "",
        full_name=message.from_user.full_name
    )
    
    # Если зашел по реферальной ссылке
    if referrer_id and user.get("is_new"):
        await database.register_referral(new_user_id=message.from_user.id, referrer_id=referrer_id)
        try:
            await message.bot.send_message(
                chat_id=referrer_id,
                text=f"🎉 **Новый реферал!** Пользователь {message.from_user.full_name} зарегистрировался по вашей ссылке! Вам начислено **+2 дня VIP-доступа бесплатно**!",
                parse_mode="Markdown"
            )
        except Exception:
            pass

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

@router.message(F.text == "🤝 Реферальная программа")
@router.callback_query(F.data == "open_referral_menu")
async def referral_menu_handler(event: types.Message | types.CallbackQuery):
    """Показывает реферальную ссылку и количество приглашенных друзей."""
    user_id = event.from_user.id
    ref_info = await database.get_referral_info(user_id)
    bot_info = await event.bot.get_me()
    
    ref_link = f"https://t.me/{bot_info.username}?start=ref_{user_id}"
    
    text = (
        "🤝 **ПАРТНЕРСКАЯ ПРОГРАММА: VIP БЕСПЛАТНО**\n\n"
        "Приглашайте друзей в ИИ-Аналитик и получайте **+2 дня VIP-доступа БЕСПЛАТНО** за каждого нового пользователя!\n\n"
        f"📊 **Ваша статистика:**\n"
        f"• Приглашено друзей: **{ref_info['referral_count']}** чел.\n\n"
        f"🔗 **Ваша личная пригласительная ссылка:**\n"
        f"`{ref_link}`\n\n"
        "💡 *Скопируйте ссылку и отправьте её друзьям или в социальные сети. Как только друг перейдет по ней, вам начислится VIP-доступ!*"
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="open_main_menu")]
    ])
    
    if isinstance(event, types.CallbackQuery):
        await event.message.edit_text(text, parse_mode="Markdown", reply_markup=kb)
    else:
        await event.answer(text, parse_mode="Markdown", reply_markup=kb)

@router.message(F.text == "❓ Помощь / О боте")
async def help_handler(message: types.Message):
    """Справка о боте."""
    help_text = (
        "❓ **КАК РАБОТАЕТ ИИ-АНАЛИТИК?**\n\n"
        "1. **Прогноз Дня:** Вы получаете разбор самого надежного матча дня с глубокой аналитикой от математической модели.\n"
        "2. **ИИ-Экспресс Дня:** Сборка тройника из наиболее надежных исходов с коэфф 3.00+.\n"
        "3. **Поиск по матчу:** Вы можете ввести названия двух команд (например: `Барселона - Реал` или `СКА - ЦСКА`), и нейросеть мгновенно сформирует отчет.\n"
        "4. **Управление банком:** Наш алгоритм никогда не рекомендует ставить весь баланс! Безопасный размер ставки — не более 3-5% от депозита.\n\n"
        "📩 **Поддержка / Вопросы по оплате СБП:** @admin"
    )
    await message.answer(help_text, parse_mode="Markdown")

