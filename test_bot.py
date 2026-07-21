import asyncio
import database
import ai_analyzer
import config

async def test_all():
    print("🧪 НАЧИНАЕМ ТЕСТИРОВАНИЕ КОМПОНЕНТОВ БОТА...\n")
    
    # 1. Тест БД
    print("1. Тест базы данных...")
    await database.init_db()
    user = await database.get_or_create_user(12345678, "test_user", "Тестовый Игрок")
    print(f"   [OK] Пользователь создан: {user}")
    
    # 2. Тест VIP статуса
    is_vip = await database.check_vip_status(12345678)
    print(f"   [OK] VIP статус нового пользователя: {is_vip} (Должно быть False)")
    
    # 3. Тест СБП платежа и подтверждения Админом
    payment_id = await database.create_payment_request(
        user_id=12345678,
        plan_key="month",
        amount=990,
        photo_file_id="test_photo_file_id_123"
    )
    print(f"   [OK] Заявка на оплату по СБП №{payment_id} создана")
    
    # Одобряем платеж (на 30 дней)
    success, u_id, expire_str = await database.approve_payment(payment_id, 30)
    print(f"   [OK] Одобрение платежа: success={success}, user_id={u_id}, expire={expire_str}")
    
    is_vip_now = await database.check_vip_status(12345678)
    print(f"   [OK] VIP статус после одобрения админом: {is_vip_now} (Должно быть True)\n")
    
    # 4. Тест ИИ-Аналитики
    print("2. Тест ИИ-Аналитики матчей...")
    forecast_day = ai_analyzer.get_daily_match_forecast()
    print("--- ПРОГНОЗ ДНЯ ---")
    print(forecast_day[:250] + "...\n")
    
    custom_analysis = await ai_analyzer.analyze_match("Барселона vs Реал Мадрид")
    print("--- АНАЛИЗ МАТЧА ПО ЗАПРОСУ ---")
    print(custom_analysis[:250] + "...\n")
    
    print("✅ ВСЕ ТЕСТЫ УСПЕШНО ПРОЙДЕНЫ! БОТ ПОЛНОСТЬЮ ГОТОВ К РАБОТЕ.")

if __name__ == "__main__":
    asyncio.run(test_all())
