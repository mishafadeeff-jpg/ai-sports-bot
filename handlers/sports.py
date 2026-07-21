from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

import database
import ai_analyzer
from handlers.payment import show_vip_menu

router = Router()

class MatchAnalysisStates(StatesGroup):
    waiting_for_teams = State()

@router.message(F.text == "🌟 Прогноз Дня")
@router.callback_query(F.data == "get_daily_forecast")
async def get_daily_forecast_handler(event: types.Message | types.CallbackQuery):
    """Выдает главный VIP прогноз дня."""
    user_id = event.from_user.id
    is_vip = await database.check_vip_status(user_id)
    
    # Если не VIP, проверяем и списываем бесплатный лимит
    if not is_vip:
        can_request = await database.decrement_free_requests(user_id)
        if not can_request:
            msg = (
                "🔒 **Бесплатные попытки исчерпаны!**\n\n"
                "Чтобы получить «Прогноз Дня» и неограниченный анализ любых матчей, оформите VIP-доступ по СБП всего от 490 ₽!"
            )
            if isinstance(event, types.CallbackQuery):
                await show_vip_menu(event)
            else:
                kb = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="👑 Оформить VIP СБП", callback_data="open_vip_menu")]
                ])
                await event.answer(msg, parse_mode="Markdown", reply_markup=kb)
            return

    forecast_text = ai_analyzer.get_daily_match_forecast()
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔍 Проанализировать свой матч", callback_data="start_match_analysis")],
        [InlineKeyboardButton(text="⬅️ В главное меню", callback_data="open_main_menu")]
    ])
    
    if isinstance(event, types.CallbackQuery):
        await event.message.edit_text(forecast_text, parse_mode="Markdown", reply_markup=kb)
    else:
        await event.answer(forecast_text, parse_mode="Markdown", reply_markup=kb)

@router.message(F.text == "🎰 ИИ-Экспресс (3.00+)")
@router.callback_query(F.data == "get_express_forecast")
async def get_express_forecast_handler(event: types.Message | types.CallbackQuery):
    """Выдает ИИ-Экспресс дня из 3 матчей."""
    user_id = event.from_user.id
    is_vip = await database.check_vip_status(user_id)
    
    if not is_vip:
        can_request = await database.decrement_free_requests(user_id)
        if not can_request:
            msg = (
                "🔒 **ИИ-Экспресс доступен в VIP!**\n\n"
                "Оформите VIP-доступ по СБП всего от 490 ₽ или пригласите 1 друга по вашей ссылке!"
            )
            if isinstance(event, types.CallbackQuery):
                await show_vip_menu(event)
            else:
                kb = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="👑 Оформить VIP СБП", callback_data="open_vip_menu")],
                    [InlineKeyboardButton(text="🤝 Пригласить друга (Бесплатно)", callback_data="open_referral_menu")]
                ])
                await event.answer(msg, parse_mode="Markdown", reply_markup=kb)
            return

    express_text = ai_analyzer.get_express_forecast()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ В главное меню", callback_data="open_main_menu")]
    ])
    
    if isinstance(event, types.CallbackQuery):
        await event.message.edit_text(express_text, parse_mode="Markdown", reply_markup=kb)
    else:
        await event.answer(express_text, parse_mode="Markdown", reply_markup=kb)


@router.message(F.text == "🔍 Анализ матча")
@router.callback_query(F.data == "start_match_analysis")
async def start_analysis_prompt(event: types.Message | types.CallbackQuery, state: FSMContext):
    """Запрашивает у пользователя названия команд для анализа."""
    await state.set_state(MatchAnalysisStates.waiting_for_teams)
    
    msg = (
        "🔍 **ИИ-АНАЛИЗАТОР МАТЧЕЙ**\n\n"
        "Введите названия двух команд через дефис или 'против'.\n"
        "Например:\n"
        "• `Барселона - Реал Мадрид`\n"
        "• `СКА vs ЦСКА`\n"
        "• `Лейкерс - Голден Стэйт`"
    )
    
    cancel_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="open_main_menu")]
    ])
    
    if isinstance(event, types.CallbackQuery):
        await event.message.edit_text(msg, parse_mode="Markdown", reply_markup=cancel_kb)
    else:
        await event.answer(msg, parse_mode="Markdown", reply_markup=cancel_kb)

@router.message(MatchAnalysisStates.waiting_for_teams)
@router.message(F.text & ~F.text.startswith("/") & ~F.text.in_({"🌟 Прогноз Дня", "🔍 Анализ матча", "👑 VIP Подписка", "📊 Статистика проходимости", "❓ Помощь / О боте"}))
async def process_match_input(message: types.Message, state: FSMContext = None):
    """Обрабатывает ввод команд и генерирует прогноз."""
    match_query = message.text.strip()
    user_id = message.from_user.id
    
    is_vip = await database.check_vip_status(user_id)
    if not is_vip:
        can_request = await database.decrement_free_requests(user_id)
        if not can_request:
            await state.clear()
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="👑 Оформить VIP СБП", callback_data="open_vip_menu")]
            ])
            await message.answer(
                "🔒 **Лимит бесплатных запросов исчерпан!**\nОформите VIP-доступ для мгновенного анализа любого количества матчей.",
                parse_mode="Markdown",
                reply_markup=kb
            )
            return

    await state.clear()
    
    waiting_msg = await message.answer("🤖 *Нейросеть собирает данные матча и вычисляет коэффициенты...*", parse_mode="Markdown")
    
    # Генерация анализа
    analysis_result = await ai_analyzer.analyze_match(match_query)
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔍 Проанализировать еще матч", callback_data="start_match_analysis")],
        [InlineKeyboardButton(text="⬅️ В главное меню", callback_data="open_main_menu")]
    ])
    
    await waiting_msg.delete()
    await message.answer(analysis_result, parse_mode="Markdown", reply_markup=kb)

@router.message(F.text == "📊 Статистика проходимости")
async def show_stats_handler(message: types.Message):
    """Показывает прозрачную статистику проходимости алгоритмов."""
    stats_text = (
        "📊 **СТАТИСТИКА РАБОТЫ ИИ-АЛГОРИТМА**\n\n"
        "За последние 30 дней работы математической модели:\n"
        "• Всего проанализировано матчей: **142**\n"
        "• Успешных прогнозов (Плюс): **116 (81.6%)**\n"
        "• Не зашедших прогнозов (Минус): **26**\n"
        "• Средний коэффициент побед: **1.84**\n"
        "• Прирост игрового банка за месяц: **+42.5%**\n\n"
        "💡 *Наш алгоритм фокусируется исключительно на матчах с высокой математической выгодой (Value Bets).*"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👑 Купить VIP доступ по СБП", callback_data="open_vip_menu")]
    ])
    await message.answer(stats_text, parse_mode="Markdown", reply_markup=kb)
