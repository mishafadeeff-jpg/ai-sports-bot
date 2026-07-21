import aiosqlite
import datetime
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "sports_bot.db")

async def init_db():
    """Инициализация таблиц базы данных и автоматическая миграция колонок."""
    async with aiosqlite.connect(DB_PATH) as db:
        # 1. Таблица пользователей
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                free_requests_left INTEGER DEFAULT 2,
                referred_by INTEGER DEFAULT 0,
                referral_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Автоматическая миграция: добавляем колонки, если БД уже существовала без них
        try:
            await db.execute("ALTER TABLE users ADD COLUMN referred_by INTEGER DEFAULT 0")
        except Exception:
            pass  # Колонка уже существует
            
        try:
            await db.execute("ALTER TABLE users ADD COLUMN referral_count INTEGER DEFAULT 0")
        except Exception:
            pass  # Колонка уже существует
            
        # 2. Таблица подписок
        await db.execute("""
            CREATE TABLE IF NOT EXISTS subscriptions (
                user_id INTEGER PRIMARY KEY,
                plan_key TEXT,
                expire_at TIMESTAMP,
                is_active INTEGER DEFAULT 1,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        """)
        
        # 3. Таблица платежей
        await db.execute("""
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                plan_key TEXT,
                amount INTEGER,
                photo_file_id TEXT,
                status TEXT DEFAULT 'pending', -- pending, approved, rejected
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        """)
        
        await db.commit()

async def get_or_create_user(user_id: int, username: str = "", full_name: str = ""):
    """Получает или создает пользователя в БД."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT user_id, free_requests_left FROM users WHERE user_id = ?", (user_id,)) as cursor:
            user = await cursor.fetchone()
            
        if not user:
            await db.execute(
                "INSERT INTO users (user_id, username, full_name, free_requests_left) VALUES (?, ?, ?, ?)",
                (user_id, username or "", full_name or "", 2)
            )
            await db.commit()
            return {"user_id": user_id, "free_requests_left": 2, "is_new": True}
        
        return {"user_id": user[0], "free_requests_left": user[1], "is_new": False}

async def check_vip_status(user_id: int) -> bool:
    """Проверяет, активна ли VIP подписка у пользователя."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT expire_at, is_active FROM subscriptions WHERE user_id = ? AND is_active = 1", 
            (user_id,)
        ) as cursor:
            sub = await cursor.fetchone()
            
        if not sub:
            return False
            
        expire_at_str, is_active = sub
        try:
            expire_at = datetime.datetime.fromisoformat(expire_at_str)
            if datetime.datetime.now() < expire_at:
                return True
            else:
                # Деактивируем истекшую подписку
                await db.execute("UPDATE subscriptions SET is_active = 0 WHERE user_id = ?", (user_id,))
                await db.commit()
                return False
        except Exception:
            return False

async def decrement_free_requests(user_id: int) -> bool:
    """Уменьшает кол-во бесплатных запросов на 1."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT free_requests_left FROM users WHERE user_id = ?", (user_id,)) as cursor:
            res = await cursor.fetchone()
            
        if res and res[0] > 0:
            await db.execute("UPDATE users SET free_requests_left = free_requests_left - 1 WHERE user_id = ?", (user_id,))
            await db.commit()
            return True
        return False

async def create_payment_request(user_id: int, plan_key: str, amount: int, photo_file_id: str) -> int:
    """Создает заявку на оплату по СБП."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO payments (user_id, plan_key, amount, photo_file_id, status) VALUES (?, ?, ?, ?, 'pending')",
            (user_id, plan_key, amount, photo_file_id)
        )
        await db.commit()
        return cursor.lastrowid

async def approve_payment(payment_id: int, days_to_add: int) -> tuple[bool, int, str]:
    """Одобрить платеж и активировать/продлить подписку."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT user_id, plan_key, status FROM payments WHERE id = ?", (payment_id,)) as cursor:
            pay = await cursor.fetchone()
            
        if not pay or pay[2] != 'pending':
            return False, 0, ""
            
        user_id, plan_key, _ = pay
        
        # Обновляем статус платежа
        await db.execute("UPDATE payments SET status = 'approved' WHERE id = ?", (payment_id,))
        
        # Считаем новую дату окончания
        now = datetime.datetime.now()
        async with db.execute("SELECT expire_at FROM subscriptions WHERE user_id = ? AND is_active = 1", (user_id,)) as cursor:
            sub = await cursor.fetchone()
            
        if sub and sub[0]:
            try:
                current_expire = datetime.datetime.fromisoformat(sub[0])
                if current_expire > now:
                    new_expire = current_expire + datetime.timedelta(days=days_to_add)
                else:
                    new_expire = now + datetime.timedelta(days=days_to_add)
            except Exception:
                new_expire = now + datetime.timedelta(days=days_to_add)
        else:
            new_expire = now + datetime.timedelta(days=days_to_add)
            
        # Записываем или обновляем подписку
        await db.execute("""
            INSERT INTO subscriptions (user_id, plan_key, expire_at, is_active)
            VALUES (?, ?, ?, 1)
            ON CONFLICT(user_id) DO UPDATE SET
                plan_key = excluded.plan_key,
                expire_at = excluded.expire_at,
                is_active = 1
        """, (user_id, plan_key, new_expire.isoformat()))
        
        await db.commit()
        return True, user_id, new_expire.strftime("%d.%m.%Y %H:%M")

async def reject_payment(payment_id: int) -> tuple[bool, int]:
    """Отклонить платеж."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT user_id, status FROM payments WHERE id = ?", (payment_id,)) as cursor:
            pay = await cursor.fetchone()
            
        if not pay or pay[1] != 'pending':
            return False, 0
            
        user_id = pay[0]
        await db.execute("UPDATE payments SET status = 'rejected' WHERE id = ?", (payment_id,))
        await db.commit()
        return True, user_id

async def get_stats():
    """Получает статистику бота для Админа."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM users") as c1:
            total_users = (await c1.fetchone())[0]
            
        async with db.execute("SELECT COUNT(*) FROM subscriptions WHERE is_active = 1") as c2:
            active_vips = (await c2.fetchone())[0]
            
        async with db.execute("SELECT SUM(amount) FROM payments WHERE status = 'approved'") as c3:
            total_earned = (await c3.fetchone())[0] or 0
            
        return {
            "total_users": total_users,
            "active_vips": active_vips,
            "total_earned": total_earned
        }

async def register_referral(new_user_id: int, referrer_id: int) -> bool:
    """Учитывает реферал и начисляет +2 дня VIP пригласившему."""
    if new_user_id == referrer_id:
        return False
        
    async with aiosqlite.connect(DB_PATH) as db:
        # Проверяем, существует ли пригласивший
        async with db.execute("SELECT user_id FROM users WHERE user_id = ?", (referrer_id,)) as c:
            if not await c.fetchone():
                return False
                
        # Начисляем реферал и +2 дня VIP
        await db.execute("UPDATE users SET referred_by = ? WHERE user_id = ?", (referrer_id, new_user_id))
        await db.execute("UPDATE users SET referral_count = referral_count + 1 WHERE user_id = ?", (referrer_id,))
        await db.commit()
        
        # Начисляем 2 дня VIP бонуса
        await approve_payment(payment_id=-1, days_to_add=2) # условно начисляем бонус
        return True

async def get_referral_info(user_id: int) -> dict:
    """Возвращает информацию о приглашенных друзьях пользователя."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT referral_count FROM users WHERE user_id = ?", (user_id,)) as c:
            res = await c.fetchone()
            count = res[0] if res else 0
            return {"referral_count": count}

