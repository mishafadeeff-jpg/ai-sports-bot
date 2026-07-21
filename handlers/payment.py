from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

import config
import database

router = Router()

class PaymentStates(StatesGroup):
    waiting_for_receipt = State()

def get_tariffs_keyboard():
    """Клавиатура выбора тарифов."""
    builder = []
    for key, plan in config.PRICING_PLANS.items():
        builder.append([
            InlineKeyboardButton(
                text=f"{plan['title']} — {plan['price']} ₽",
                callback_data=f"buy_plan:{key}"
            )
        ])
    builder.append([InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="open_main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=builder)

@router.callback_query(F.data == "open_vip_menu")
async def show_vip_menu(callback: types.CallbackQuery):
    """Показывает экран покупки VIP-подписки."""
    is_vip = await database.check_vip_status(callback.from_user.id)
    
    text = (
        "👑 **ИИ-АНАЛИТИКА VIP: ОФОРМЛЕНИЕ ПОДПИСКИ**\n\n"
        "Получите полный неограниченный доступ к спортивным прогнозам нейросети!\n\n"
        "✨ **Что входит в VIP-доступ:**\n"
        "• Неограниченное число ИИ-анализов любых матчей\n"
        "• Ежедневный «Главный Прогноз Дня» с проходимостью до 85%\n"
        "• Расчет выгоды коэффициентов и советы по банк-менеджменту\n"
        "• Закрытый чат с лайв-сигналами от алгоритма\n\n"
    )
    if is_vip:
        text += "✅ **У вас уже активирован VIP-доступ!** Вы можете продлить его ниже:\n\n"
    else:
        text += "👇 **Выберите подходящий тариф:**"
        
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=get_tariffs_keyboard())

@router.callback_query(F.data.startswith("buy_plan:"))
async def process_plan_selection(callback: types.CallbackQuery, state: FSMContext):
    """Обрабатывает выбор конкретного тарифа и выводит реквизиты СБП."""
    plan_key = callback.data.split(":")[1]
    plan = config.PRICING_PLANS.get(plan_key)
    
    if not plan:
        await callback.answer("Ошибка: тариф не найден.", show_alert=True)
        return
        
    await state.update_data(selected_plan_key=plan_key)
    await state.set_state(PaymentStates.waiting_for_receipt)
    
    payment_text = (
        f"💳 **ОПЛАТА ТАРИФА: {plan['title']}**\n"
        f"Сумма к оплате: **{plan['price']} ₽**\n\n"
        f"📌 **РЕКВИЗИТЫ ДЛЯ ПЕРЕВОДА ПО СБП:**\n"
        f"📱 Номер телефона: `{config.SBP_PHONE}`\n"
        f"🏦 Банк: **{config.SBP_BANK}**\n"
        f"👤 Получатель: **{config.SBP_RECIPIENT}**\n\n"
        f"⚠️ **ИНСТРУКЦИЯ:**\n"
        f"1. Переведите ровно **{plan['price']} ₽** по указанному номеру.\n"
        f"2. Сделайте скриншот или фото чека об оплате.\n"
        f"3. **Отправьте изображение чека прямо сюда в чат.**\n\n"
        f"⏳ *После отправки чека администратор проверит платеж и активирует VIP-доступ в течение 2-5 минут.*"
    )
    
    cancel_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отменить покупку", callback_data="cancel_payment")]
    ])
    
    await callback.message.edit_text(payment_text, parse_mode="Markdown", reply_markup=cancel_kb)

@router.callback_query(F.data == "cancel_payment")
async def cancel_payment_handler(callback: types.CallbackQuery, state: FSMContext):
    """Отмена процесса оплаты."""
    await state.clear()
    await callback.answer("Покупка отменена.")
    await show_vip_menu(callback)

@router.message(PaymentStates.waiting_for_receipt, F.photo)
async def process_receipt_photo(message: types.Message, state: FSMContext):
    """Принимает фото чека и пересылает его Админам для подтверждения."""
    data = await state.get_data()
    plan_key = data.get("selected_plan_key")
    plan = config.PRICING_PLANS.get(plan_key)
    
    if not plan:
        await message.answer("Ошибка сессии. Пожалуйста, выберите тариф заново.")
        await state.clear()
        return
        
    photo_file_id = message.photo[-1].file_id
    user_id = message.from_user.id
    username = message.from_user.username or "без username"
    full_name = message.from_user.full_name
    
    # Записываем платеж в БД со статусом pending
    payment_id = await database.create_payment_request(
        user_id=user_id,
        plan_key=plan_key,
        amount=plan['price'],
        photo_file_id=photo_file_id
    )
    
    await state.clear()
    
    # Уведомляем пользователя
    await message.answer(
        "✅ **Чек успешно получен!**\n\n"
        "Заявка отправлена администратору на проверку. Как только платеж будет подтвержден, вам придет уведомление и активируется VIP-доступ.",
        parse_mode="Markdown"
    )
    
    # Пересылаем чек Админам с кнопками Одобрить/Отклонить
    admin_kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"admin_approve:{payment_id}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"admin_reject:{payment_id}")
        ]
    ])
    
    admin_msg_text = (
        f"📥 **НОВАЯ ЗАЯВКА НА ОПЛАТУ №{payment_id}**\n\n"
        f"👤 Пользователь: {full_name} (@{username})\n"
        f"🆔 ID: `{user_id}`\n"
        f"📦 Тариф: **{plan['title']}**\n"
        f"💰 Сумма: **{plan['price']} ₽**\n"
        f"📅 Время: {message.date.strftime('%d.%m.%Y %H:%M')}"
    )
    
    for admin_id in config.ADMIN_IDS:
        try:
            await message.bot.send_photo(
                chat_id=admin_id,
                photo=photo_file_id,
                caption=admin_msg_text,
                parse_mode="Markdown",
                reply_markup=admin_kb
            )
        except Exception as e:
            print(f"[ERROR] Не удалось отправить уведомление админу {admin_id}: {e}")

@router.message(PaymentStates.waiting_for_receipt)
async def process_invalid_receipt(message: types.Message):
    """Если отправил не фото."""
    await message.answer("Пожалуйста, отправьте именно **изображение/фото чека** (скриншот экрана оплаты).", parse_mode="Markdown")
