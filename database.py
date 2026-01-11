import asyncpg
from config import DATABASE_URL

class Database:
    def __init__(self):
        self.pool = None
    
    async def connect(self):
        """Initialise la connexion à la base de données"""
        if DATABASE_URL:
            try:
                self.pool = await asyncpg.create_pool(DATABASE_URL)
                print("✅ Connecté à PostgreSQL")
                await self.init_tables()
            except Exception as e:
                print(f"❌ Erreur de connexion à PostgreSQL: {e}")
        else:
            print("⚠️ DATABASE_URL non trouvé")
    
    async def init_tables(self):
        """Crée les tables si elles n'existent pas"""
        async with self.pool.acquire() as conn:
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS linked_accounts (
                    discord_id TEXT PRIMARY KEY,
                    riot_id TEXT NOT NULL,
                    tagline TEXT NOT NULL,
                    puuid TEXT NOT NULL
                )
            ''')
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS notified_users (
                    discord_id TEXT PRIMARY KEY,
                    notified_at TIMESTAMP DEFAULT NOW()
                )
            ''')
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS rank_history (
                    discord_id TEXT,
                    tier TEXT NOT NULL,
                    rank TEXT NOT NULL,
                    lp INTEGER NOT NULL,
                    timestamp TIMESTAMP DEFAULT NOW(),
                    PRIMARY KEY (discord_id, timestamp)
                )
            ''')
            print("✅ Tables de base de données créées")
    
    async def get_linked_account(self, discord_id: str):
        """Récupère un compte lié depuis la DB"""
        if not self.pool:
            return None
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                'SELECT riot_id, tagline, puuid FROM linked_accounts WHERE discord_id = $1',
                discord_id
            )
            if row:
                return {
                    'riot_id': row['riot_id'],
                    'tagline': row['tagline'],
                    'puuid': row['puuid']
                }
            return None
    
    async def save_linked_account(self, discord_id: str, riot_id: str, tagline: str, puuid: str):
        """Sauvegarde un compte lié dans la DB"""
        if not self.pool:
            return False
        async with self.pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO linked_accounts (discord_id, riot_id, tagline, puuid)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (discord_id) DO UPDATE
                SET riot_id = $2, tagline = $3, puuid = $4
            ''', discord_id, riot_id, tagline, puuid)
        return True
    
    async def get_all_linked_accounts(self):
        """Récupère tous les comptes liés"""
        if not self.pool:
            return {}
        async with self.pool.acquire() as conn:
            rows = await conn.fetch('SELECT * FROM linked_accounts')
            return {
                row['discord_id']: {
                    'riot_id': row['riot_id'],
                    'tagline': row['tagline'],
                    'puuid': row['puuid']
                }
                for row in rows
            }
    
    async def is_user_notified(self, discord_id: str):
        """Vérifie si un utilisateur a déjà été notifié"""
        if not self.pool:
            return False
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                'SELECT 1 FROM notified_users WHERE discord_id = $1',
                discord_id
            )
            return row is not None
    
    async def mark_user_notified(self, discord_id: str):
        """Marque un utilisateur comme notifié"""
        if not self.pool:
            return
        async with self.pool.acquire() as conn:
            await conn.execute(
                'INSERT INTO notified_users (discord_id) VALUES ($1) ON CONFLICT DO NOTHING',
                discord_id
            )
    
    async def get_last_rank(self, discord_id: str):
        """Récupère le dernier rang connu"""
        if not self.pool:
            return None
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                'SELECT tier, rank, lp FROM rank_history WHERE discord_id = $1 ORDER BY timestamp DESC LIMIT 1',
                discord_id
            )
            if row:
                return {'tier': row['tier'], 'rank': row['rank'], 'lp': row['lp']}
            return None
    
    async def save_rank(self, discord_id: str, tier: str, rank: str, lp: int):
        """Sauvegarde un nouveau rang dans l'historique"""
        if not self.pool:
            return
        async with self.pool.acquire() as conn:
            await conn.execute(
                'INSERT INTO rank_history (discord_id, tier, rank, lp) VALUES ($1, $2, $3, $4)',
                discord_id, tier, rank, lp
            )