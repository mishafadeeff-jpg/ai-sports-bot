mport os
from dotenv import load_dotenv

load_dotenv()

# Токен бота Telegram
BOT_TOKEN = os.getenv("BOT_TOKEN", "8791637436:AAHF0JsK6shUlKszTmgrwQ6dYpLT8k_nYHc")

# Telegram ID Главного Админа (получателя чеков)
# Твой ID или ID владельца бота (по умолчанию ставим 8791637436 / demo id, можно будет легко сменить)
ADMIN_IDS = [int(id_str) for id_str in os.getenv("ADMIN_IDS", "860392517,720963162,8791637436").split(",") if id_str.strip()]

# Реквизиты для оплаты по СБП (меняй на свои)
SBP_PHONE = os.getenv("SBP_PHONE", "+7 (922) 929-18-55")
SBP_BANK = os.getenv("SBP_BANK", "Сбербанк")
SBP_RECIPIENT = os.getenv("SBP_RECIPIENT", "Михаил Ф.")

# Тарифные планы (Название, Дни доступа, Цена в рублях)
PRICING_PLANS = {
    "week": {
        "title": "⚡ 1 Неделя VIP",
        "days": 7,
        "price": 490,
        "description": "Полный доступ к ИИ-прогнозам на 7 дней"
    },
    "month": {
        "title": "🔥 1 Месяц VIP",
        "days": 30,
        "price": 990,
        "description": "Выгодный тариф! 30 дней ИИ-аналитики"
    },
    "forever": {
        "title": "👑 Навсегда (VIP Club)",
        "days": 3650,
        "price": 2490,
        "description": "Вечный доступ ко всем прогнозам и лайв-сигналам"
    }
}

# Ключ Google Gemini API (для генерации умных разборов)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
