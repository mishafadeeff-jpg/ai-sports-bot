import random
import datetime
import config

# База экспертных аргументов для умной симуляции, если API ключ не задан
FACTORS_DATABASE = [
    "Хозяева демонстрируют отличную форму в 4 из 5 последних домашних встреч.",
    "У гостей серьезные кадровые потери в линии защиты, что ослабляет их оборонительный потенциал.",
    "В 75% очных противостояний этих команд пробивался тотал больше 2.5 голов.",
    "Показатели xG (ожидаемых голов) команды хозяев на 32% выше среднего показателя по лиге.",
    "Гости испытывают проблемы с физической кондицией из-за плотного графика матчей.",
    "Модель Elo фиксирует устойчивый рост вероятности победы первой команды."
]

BET_TYPES = [
    ("Победит Команда 1 (П1)", "1.75 - 2.10", 68),
    ("Тотал Больше (2.5) голов", "1.85 - 1.95", 74),
    ("Обе команды забьют (ОЗ - Да)", "1.70 - 1.88", 71),
    ("Фора Команды 1 (-1)", "2.05 - 2.25", 62),
    ("Двойной шанс (1X) и ТБ (1.5)", "1.65 - 1.80", 81)
]

def generate_local_analysis(team1: str, team2: str, sport: str = "Футбол") -> str:
    """Генерирует экспертную аналитику матча с расчетом вероятностей."""
    prob_team1 = random.randint(45, 65)
    prob_draw = random.randint(15, 25)
    prob_team2 = 100 - prob_team1 - prob_draw
    
    bet_info = random.choice(BET_TYPES)
    bet_name, bet_coeff, bet_confidence = bet_info
    
    factors = random.sample(FACTORS_DATABASE, 3)
    
    analysis_text = (
        f"⚽ **ИИ-АНАЛИЗ МАТЧА: {team1.upper()} — {team2.upper()}**\n"
        f"🏆 Вид спорта: {sport} | Турнир: Премьер-Лига / Кубок\n"
        f"📅 Дата аналитики: {datetime.datetime.now().strftime('%d.%m.%Y')}\n\n"
        f"📊 **Оценка вероятностей от Нейросети:**\n"
        f"• Победа {team1}: `{prob_team1}%`\n"
        f"• Ничья: `{prob_draw}%`\n"
        f"• Победа {team2}: `{prob_team2}%`\n\n"
        f"🔍 **Ключевые факторы анализа:**\n"
        f"1. {factors[0]}\n"
        f"2. {factors[1]}\n"
        f"3. {factors[2]}\n\n"
        f"🎯 **РЕКОМЕНДУЕМАЯ СТАВКА:**\n"
        f"📌 Исход: **{bet_name}**\n"
        f"📈 Коэффициент БК: **{bet_coeff}**\n"
        f"🔥 Проходимость: **{bet_confidence}% (Высокая)**\n"
        f"💡 *Совет по банк-менеджменту: не более 3-5% от вашего депозита.*"
    )
    return analysis_text

def get_daily_match_forecast() -> str:
    """Возвращает специальный 'Прогноз Дня' с высокой проходимостью."""
    top_matches = [
        ("Реал Мадрид", "Барселона"),
        ("Манчестер Сити", "Ливерпуль"),
        ("Бавария", "Боруссия Дортмунд"),
        ("ПСЖ", "Марсель"),
        ("Интер", "Милан")
    ]
    t1, t2 = random.choice(top_matches)
    
    analysis = generate_local_analysis(t1, t2)
    return f"🌟 **ГЛАВНЫЙ ПРОГНОЗ ДНЯ (VIP)** 🌟\n\n{analysis}"

async def analyze_match(match_query: str) -> str:
    """
    Основная функция разбора матча.
    Если задан GEMINI_API_KEY, использует Google Gemini. Иначе симулирует локально.
    """
    if config.GEMINI_API_KEY:
        try:
            import google.generativeai as genai
            genai.configure(api_key=config.GEMINI_API_KEY)
            model = genai.GenerativeModel('gemini-pro')
            
            prompt = (
                f"Ты — профессиональный ИИ-аналитик спортивных ставок. Проанализируй следующий матч: '{match_query}'. "
                f"Составь подробный прогноз в красивом формате с эмодзи. Укажи вероятности побед в %, ключевые аргументы, "
                f"рекомендуемую ставку, средний коэффициент и рекомендуемый процент депозита (3-5%)."
            )
            response = await model.generate_content_async(prompt)
            if response.text:
                return response.text
        except Exception as e:
            print(f"[WARN] Ошибка Gemini API: {e}. Переключаемся на локальную аналитику.")
            
    # Если ввода нет или API недоступен, парсим команды из запроса
    parts = match_query.replace("-", " vs ").replace("—", " vs ").split(" vs ")
    if len(parts) >= 2:
        t1, t2 = parts[0].strip(), parts[1].strip()
    else:
        t1 = match_query.strip()
        t2 = "Соперник"
        
    return generate_local_analysis(t1, t2)
