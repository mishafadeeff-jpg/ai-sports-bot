from aiogram import Router, F, types
from aiogram.filters import Command

import config
import database

router = Router()

def is_admin(user_id: int) -> bool:
    return user_id in config.ADMIN_IDS

@router.message(Command("admin"))
async def admin_panel(message: types.Message):
    """Показывает статистику бота для администратора."""
    if not is_admin(message.from_user.id):
        return
        
    stats = await database.get_stats()
    
    text = (
        "👑 **АДМИН-ПАНЕЛЬ ИИ-АНАЛИТИКИ**\n\n"
        f"👥 Всего пользователей в боте: **{stats['total_users']}**\n"
        f"💎 Активных VIP-подписчиков: **{stats['active_vips']}**\n"
        f"💰 Заработано всего по СБП: **{stats['total_earned']} ₽**\n"
    )
    await message.answer(text, parse_mode="Markdown")

@router.message(Command("admin_vip"))
async def admin_give_vip(message: types.Message):
    """Секретная команда выдачи VIP администратором: /admin_vip <user_id> [дней]"""
    if not is_admin(message.from_user.id):
        return
        
    args = message.text.split()
    if len(args) < 2:
        await message.answer("⚠️ Использование: `/admin_vip <user_id> [дней]`\nНапример: `/admin_vip 860392517 30`", parse_mode="Markdown")
        return
        
    try:
        target_user_id = int(args[1])
        days = int(args[2]) if len(args) > 2 else 3650  # По умолчанию 10 лет
    except ValueError:
        await message.answer("⚠️ Неверный ID или количество дней.")
        return
        
    # Выдаем подписку
    await database.approve_payment(payment_id=-1, days_to_add=days)
    
    # Записываем в базу подписок вручную, если не было платежа
    async with database.aiosqlite.connect(database.DB_PATH) as db:
        import datetime
        expire_date = (datetime.datetime.now() + datetime.timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
        await db.execute(
            "INSERT OR REPLACE INTO subscriptions (user_id, plan_key, expire_at, is_active) VALUES (?, ?, ?, 1)",
            (target_user_id, "forever", expire_date)
        )
        await db.commit()
        
    await message.answer(f"👑 **VIP-доступ успешно выдан!**\n👤 ID: `{target_user_id}`\n📅 Срок: **{days} дней**", parse_mode="Markdown")
    try:
        await message.bot.send_message(
            chat_id=target_user_id,
            text="🎉 **Вам предоставлен VIP-доступ администратором!**\nТеперь все функции и ИИ-анализ доступны без ограничений!",
            parse_mode="Markdown"
        )
    except Exception:
        pass

@router.callback_query(F.data.startswith("admin_approve:"))
async def approve_payment_handler(callback: types.CallbackQuery):
    """Админ нажатием кнопки подтверждает платеж."""
    if not is_admin(callback.from_user.id):
        await callback.answer("У вас нет прав админа.", show_alert=True)
        return
        
    payment_id = int(callback.data.split(":")[1])
    
    # Получаем детали платежа, чтобы узнать тариф
    async with database.aiosqlite.connect(database.DB_PATH) as db:
        async with db.execute("SELECT plan_key FROM payments WHERE id = ?", (payment_id,)) as cursor:
            res = await cursor.fetchone()
            
    if not res:
        await callback.answer("Платеж не найден.", show_alert=True)
        return
        
    plan_key = res[0]
    plan = config.PRICING_PLANS.get(plan_key, {"days": 30, "title": "VIP"})
    days_to_add = plan["days"]
    
    success, target_user_id, expire_date_str = await database.approve_payment(payment_id, days_to_add)
    
    if not success:
        await callback.answer("Ошибка или платеж уже был обработан.", show_alert=True)
        return
        
    await callback.answer("Платеж успешно подтвержден! VIP активирован.", show_alert=True)
    
    # Обновляем подпись в сообщении у админа
    new_caption = callback.message.caption + f"\n\n✅ **ОДОБРЕНО АДМИНОМ!**\nVIP подписка активирована до: `{expire_date_str}`"
    await callback.message.edit_caption(caption=new_caption, parse_mode="Markdown", reply_markup=None)
    
    # Уведомляем пользователя об активации подписки
    user_notify_text = (
        "🎉 **ПОЗДРАВЛЯЕМ! ВАШ ПЛАТЕЖ ПОДТВЕРЖДЕН!** 🎉\n\n"
        f"👑 ВАМ АКТИВИРОВАН ТАРИФ: **{plan['title']}**\n"
        f"📅 Подписка действенна до: **{expire_date_str}**\n\n"
        "Теперь вам доступны неограниченные ИИ-прогнозы любых матчей и эксклюзивные сигналы!"
    )
    try:
        await callback.bot.send_message(chat_id=target_user_id, text=user_notify_text, parse_mode="Markdown")
    except Exception as e:
        print(f"[WARN] Не удалось уведомить пользователя {target_user_id}: {e}")

@router.callback_query(F.data.startswith("admin_reject:"))
async def reject_payment_handler(callback: types.CallbackQuery):
    """Админ отклоняет платеж."""
    if not is_admin(callback.from_user.id):
        await callback.answer("У вас нет прав админа.", show_alert=True)
        return
        
    payment_id = int(callback.data.split(":")[1])
    
    success, target_user_id = await database.reject_payment(payment_id)
    
    if not success:
        await callback.answer("Ошибка или платеж уже был обработан.", show_alert=True)
        return
        
    await callback.answer("Заявка отклонена.", show_alert=True)
    
    # Обновляем подпись у админа
    new_caption = callback.message.caption + "\n\n❌ **ОТКЛОНЕНО АДМИНОМ (Чек не подтвержден).**"
    await callback.message.edit_caption(caption=new_caption, parse_mode="Markdown", reply_markup=None)
    
    # Уведомляем пользователя
    user_notify_text = (
        "❌ **Ваш платеж не был подтвержден.**\n\n"
        "Возможные причины: неверная сумма перевода или нечитаемый чек. Если произошла ошибка, свяжитесь с поддержкой."
    )
    try:
        await callback.bot.send_message(chat_id=target_user_id, text=user_notify_text, parse_mode="Markdown")
    except Exception as e:
        print(f"[WARN] Не удалось уведомить пользователя {target_user_id}: {e}")
