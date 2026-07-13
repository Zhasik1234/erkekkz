import aiosqlite

DB_NAME = "bot.db"

async def init_db():
    """Создает таблицы при запуске бота, если их еще нет"""
    async with aiosqlite.connect(DB_NAME) as db:
        # Таблица блокировок
        await db.execute('''
            CREATE TABLE IF NOT EXISTS banned_users (
                user_id INTEGER PRIMARY KEY
            )
        ''')
        # Таблица покупок
        await db.execute('''
            CREATE TABLE IF NOT EXISTS purchases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                username TEXT,
                sub_type TEXT,
                purchase_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        await db.commit()

# --- ФУНКЦИИ БЛОКИРОВОК ---
async def get_banned_users() -> set:
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute('SELECT user_id FROM banned_users') as cursor:
            rows = await cursor.fetchall()
            return set(row[0] for row in rows)

async def ban_user_id(user_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('INSERT OR IGNORE INTO banned_users (user_id) VALUES (?)', (user_id,))
        await db.commit()

async def unban_user_id(user_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('DELETE FROM banned_users WHERE user_id = ?', (user_id,))
        await db.commit()

# --- ФУНКЦИИ ПОКУПОК ---
async def add_purchase(user_id: int, username: str, sub_type: str):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            'INSERT INTO purchases (user_id, username, sub_type) VALUES (?, ?, ?)',
            (user_id, username, sub_type)
        )
        await db.commit()

async def get_recent_purchases(limit: int = 10):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
            'SELECT user_id, username, sub_type, date(purchase_date) FROM purchases ORDER BY id DESC LIMIT ?', 
            (limit,)
        ) as cursor:
            return await cursor.fetchall()
        
        