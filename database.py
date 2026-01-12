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
            # Nouvelle table pour les stats de matchs
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS match_stats (
                    match_id TEXT NOT NULL,
                    puuid TEXT NOT NULL,
                    champion TEXT NOT NULL,
                    kills INTEGER NOT NULL,
                    deaths INTEGER NOT NULL,
                    assists INTEGER NOT NULL,
                    cs INTEGER NOT NULL,
                    game_duration INTEGER NOT NULL,
                    vision_score INTEGER NOT NULL,
                    win BOOLEAN NOT NULL,
                    queue_id INTEGER NOT NULL,
                    game_date TIMESTAMP NOT NULL,
                    PRIMARY KEY (match_id, puuid)
                )
            ''')
            # Index pour accélérer les requêtes
            await conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_match_stats_puuid 
                ON match_stats(puuid)
            ''')
            await conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_match_stats_game_date 
                ON match_stats(game_date DESC)
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
    
    # === NOUVELLES FONCTIONS POUR MATCH_STATS ===
    
    async def match_exists(self, match_id: str, puuid: str):
        """Vérifie si un match existe déjà pour ce joueur"""
        if not self.pool:
            return False
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                'SELECT 1 FROM match_stats WHERE match_id = $1 AND puuid = $2',
                match_id, puuid
            )
            return row is not None
    
    async def save_match_stats(self, match_id: str, puuid: str, stats: dict):
        """Sauvegarde les stats d'un match pour un joueur"""
        if not self.pool:
            return False
        async with self.pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO match_stats 
                (match_id, puuid, champion, kills, deaths, assists, cs, 
                 game_duration, vision_score, win, queue_id, game_date)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                ON CONFLICT (match_id, puuid) DO NOTHING
            ''', 
                match_id, 
                puuid, 
                stats['champion'],
                stats['kills'],
                stats['deaths'],
                stats['assists'],
                stats['cs'],
                stats['game_duration'],
                stats['vision_score'],
                stats['win'],
                stats['queue_id'],
                stats['game_date']
            )
        return True
    
    async def get_player_stats(self, puuid: str):
        """Récupère toutes les stats d'un joueur"""
        if not self.pool:
            return []
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                'SELECT * FROM match_stats WHERE puuid = $1 ORDER BY game_date DESC',
                puuid
            )
            return [dict(row) for row in rows]
    
    async def get_player_stats_summary(self, puuid: str):
        """Calcule un résumé des stats d'un joueur"""
        if not self.pool:
            return None
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow('''
                SELECT 
                    COUNT(*) as total_games,
                    SUM(CASE WHEN win THEN 1 ELSE 0 END) as wins,
                    AVG(kills) as avg_kills,
                    AVG(deaths) as avg_deaths,
                    AVG(assists) as avg_assists,
                    AVG(CAST(cs AS FLOAT) / (game_duration / 60.0)) as cs_per_min,
                    AVG(vision_score) as avg_vision_score
                FROM match_stats 
                WHERE puuid = $1
            ''', puuid)
            
            if row and row['total_games'] > 0:
                return {
                    'total_games': row['total_games'],
                    'wins': row['wins'],
                    'losses': row['total_games'] - row['wins'],
                    'winrate': round((row['wins'] / row['total_games']) * 100, 1),
                    'avg_kills': round(row['avg_kills'], 1),
                    'avg_deaths': round(row['avg_deaths'], 1),
                    'avg_assists': round(row['avg_assists'], 1),
                    'kda': round((row['avg_kills'] + row['avg_assists']) / max(row['avg_deaths'], 1), 2),
                    'cs_per_min': round(row['cs_per_min'], 1),
                    'avg_vision_score': round(row['avg_vision_score'], 1)
                }
            return None
