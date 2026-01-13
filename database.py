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
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS milestones (
                    id SERIAL PRIMARY KEY,
                    puuid TEXT NOT NULL,
                    milestone_type TEXT NOT NULL,
                    milestone_value INTEGER NOT NULL,
                    reached_at TIMESTAMP DEFAULT NOW(),
                    extra_data TEXT,
                    UNIQUE(puuid, milestone_type, milestone_value, extra_data)
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
            await conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_match_stats_queue 
                ON match_stats(queue_id)
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
        """Sauvegarde les stats d'un match pour un joueur avec logs de debug"""
        if not self.pool:
            print("❌ DEBUG: pool est None!")
            return False
        
        print(f"🔍 DEBUG: Tentative d'insertion - match_id={match_id[:20]}..., champion={stats.get('champion')}")
        
        try:
            async with self.pool.acquire() as conn:
                print(f"🔍 DEBUG: Connexion acquise")
                
                result = await conn.execute('''
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
                
                print(f"✅ DEBUG: Execute terminé - result={result}")
                
                # Vérifier si l'insertion a vraiment eu lieu
                check = await conn.fetchval(
                    'SELECT COUNT(*) FROM match_stats WHERE match_id = $1 AND puuid = $2',
                    match_id, puuid
                )
                print(f"✅ DEBUG: Vérification - {check} ligne(s) trouvée(s)")
                
                if check == 0:
                    print(f"⚠️ DEBUG: CONFLIT! La ligne n'a pas été insérée (déjà existante?)")
                
            print(f"✅ DEBUG: Connexion relâchée")
            return True
            
        except Exception as e:
            print(f"❌ DEBUG: ERREUR dans save_match_stats: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def get_player_stats(self, puuid: str, queue_filter: str = None):
        """Récupère toutes les stats d'un joueur avec filtre optionnel"""
        if not self.pool:
            return []
        
        # Map des filtres vers les queue IDs
        queue_map = {
            'ranked': [420],  # Ranked Solo/Duo
            'flex': [440],    # Ranked Flex
            'normal': [400, 430],  # Normal Draft + Blind
            'aram': [450]     # ARAM
        }
        
        async with self.pool.acquire() as conn:
            if queue_filter and queue_filter in queue_map:
                queue_ids = queue_map[queue_filter]
                placeholders = ','.join(f'${i+2}' for i in range(len(queue_ids)))
                query = f'SELECT * FROM match_stats WHERE puuid = $1 AND queue_id IN ({placeholders}) ORDER BY game_date DESC'
                rows = await conn.fetch(query, puuid, *queue_ids)
            else:
                rows = await conn.fetch(
                    'SELECT * FROM match_stats WHERE puuid = $1 ORDER BY game_date DESC',
                    puuid
                )
            return [dict(row) for row in rows]
    
    async def get_player_stats_summary(self, puuid: str, queue_filter: str = None):
        """Calcule un résumé des stats d'un joueur avec filtre optionnel"""
        if not self.pool:
            return None
        
        # Map des filtres vers les queue IDs
        queue_map = {
            'ranked': [420],
            'flex': [440],
            'normal': [400, 430],
            'aram': [450]
        }
        
        async with self.pool.acquire() as conn:
            # Requête de base
            base_query = '''
                SELECT 
                    COUNT(*) as total_games,
                    SUM(CASE WHEN win THEN 1 ELSE 0 END) as wins,
                    SUM(kills) as total_kills,
                    SUM(deaths) as total_deaths,
                    SUM(assists) as total_assists
                FROM match_stats 
                WHERE puuid = $1
            '''
            
            # Requête pour CS et Vision (exclure ARAM)
            cs_vision_query = '''
                SELECT 
                    AVG(CAST(cs AS FLOAT) / (game_duration / 60.0)) as cs_per_min,
                    AVG(vision_score) as avg_vision_score
                FROM match_stats 
                WHERE puuid = $1 AND queue_id != 450
            '''
            
            # Ajouter le filtre si nécessaire
            if queue_filter and queue_filter in queue_map:
                queue_ids = queue_map[queue_filter]
                placeholders = ','.join(f'${i+2}' for i in range(len(queue_ids)))
                base_query += f' AND queue_id IN ({placeholders})'
                
                # Pour CS/Vision, on ajoute aussi le filtre mais on garde l'exclusion ARAM
                if queue_filter == 'aram':
                    # Si on filtre sur ARAM, on ne calcule pas CS/Vision
                    cs_vision_query = None
                else:
                    cs_vision_query += f' AND queue_id IN ({placeholders})'
                
                row = await conn.fetchrow(base_query, puuid, *queue_ids)
                if cs_vision_query:
                    cs_vision_row = await conn.fetchrow(cs_vision_query, puuid, *queue_ids)
                else:
                    cs_vision_row = None
            else:
                row = await conn.fetchrow(base_query, puuid)
                cs_vision_row = await conn.fetchrow(cs_vision_query, puuid)
            
            if row and row['total_games'] > 0:
                total_deaths = row['total_deaths'] if row['total_deaths'] > 0 else 1
                
                result = {
                    'total_games': row['total_games'],
                    'wins': row['wins'],
                    'losses': row['total_games'] - row['wins'],
                    'winrate': round((row['wins'] / row['total_games']) * 100, 1),
                    'total_kills': row['total_kills'],
                    'total_deaths': row['total_deaths'],
                    'total_assists': row['total_assists'],
                    'kda': round((row['total_kills'] + row['total_assists']) / total_deaths, 2)
                }
                
                # Ajouter CS et Vision si disponibles
                if cs_vision_row and cs_vision_row['cs_per_min']:
                    result['cs_per_min'] = round(cs_vision_row['cs_per_min'], 1)
                    result['avg_vision_score'] = round(cs_vision_row['avg_vision_score'], 1)
                else:
                    result['cs_per_min'] = None
                    result['avg_vision_score'] = None
                
                return result
            return None
    
    async def get_match_count(self, puuid: str):
        """Compte le nombre de matchs stockés pour un joueur"""
        if not self.pool:
            return 0
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                'SELECT COUNT(*) as count FROM match_stats WHERE puuid = $1',
                puuid
            )
            return row['count'] if row else 0

    # === FONCTIONS POUR MILESTONES ===
    
    async def check_and_save_milestone(
        self,
        puuid: str,
        milestone_type: str,
        current_value: int,
        extra_data: str = None
    ):
        if not self.pool:
            return None
    
        THRESHOLDS = {
            'deaths': [100, 250, 500, 750, 1000, 1500, 2000, 2500, 3000],
            'kills': [100, 250, 500, 750, 1000, 1500, 2000, 2500, 3000],
            'games': [50, 100, 250, 500, 750, 1000],
            'wins': [50, 100, 200, 300, 500, 750, 1000],
            'losses': [50, 100, 200, 300, 500, 750, 1000],
            'win_streak': [5, 10, 15, 20],
            'lose_streak': [5, 10, 15, 20],
            'champion_games': [25, 50, 100, 200, 300]
        }
    
        thresholds = THRESHOLDS.get(milestone_type, [])
        if not thresholds:
            return None
    
        # 🥇 plus haut palier atteignable
        reached_threshold = max(
            (t for t in thresholds if current_value >= t),
            default=None
        )
    
        if reached_threshold is None:
            return None
    
        async with self.pool.acquire() as conn:
            # 🔎 dernier milestone enregistré
            last_saved = await conn.fetchval(
                '''
                SELECT MAX(milestone_value)
                FROM milestones
                WHERE puuid = $1 AND milestone_type = $2
                AND ($3::TEXT IS NULL OR extra_data = $3)
                ''',
                puuid, milestone_type, extra_data
            )
    
            # 🚫 déjà au même niveau ou plus haut → rien à faire
            if last_saved is not None and reached_threshold <= last_saved:
                return None
    
            # 💾 sauvegarde uniquement le meilleur
            await conn.execute(
                '''
                INSERT INTO milestones (puuid, milestone_type, milestone_value, extra_data)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT DO NOTHING
                ''',
                puuid, milestone_type, reached_threshold, extra_data
            )
    
            return reached_threshold
    
    async def get_current_streak(self, puuid: str):
        """
        Calcule la série actuelle (win streak ou lose streak)
        Retourne ('win', count) ou ('lose', count) ou (None, 0)
        """
        if not self.pool:
            return None, 0
        
        async with self.pool.acquire() as conn:
            # Récupérer les 20 derniers matchs triés par date
            rows = await conn.fetch('''
                SELECT win FROM match_stats 
                WHERE puuid = $1 
                ORDER BY game_date DESC 
                LIMIT 20
            ''', puuid)
            
            if not rows or len(rows) == 0:
                return None, 0
            
            # Calculer la série actuelle
            streak_type = 'win' if rows[0]['win'] else 'lose'
            streak_count = 0
            
            for row in rows:
                if (streak_type == 'win' and row['win']) or (streak_type == 'lose' and not row['win']):
                    streak_count += 1
                else:
                    break
            
            return streak_type, streak_count
    
    async def get_champion_stats(self, puuid: str):
        """
        Récupère les stats par champion
        Retourne dict {champion: game_count}
        """
        if not self.pool:
            return {}
        
        async with self.pool.acquire() as conn:
            rows = await conn.fetch('''
                SELECT champion, COUNT(*) as game_count
                FROM match_stats
                WHERE puuid = $1
                GROUP BY champion
                ORDER BY game_count DESC
            ''', puuid)
            
            return {row['champion']: row['game_count'] for row in rows}





