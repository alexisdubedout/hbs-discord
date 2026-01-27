import asyncpg
from config import DATABASE_URL

class Database:
    def __init__(self):
        self.pool = None
        print("🔧 Database instance créée")
    
    async def connect(self):
        """Initialise la connexion à la base de données"""
        if not DATABASE_URL:
            print("⚠️ DATABASE_URL non trouvé")
            return
        
        try:
            print(f"🔄 Tentative de connexion à PostgreSQL...")
            self.pool = await asyncpg.create_pool(DATABASE_URL)
            print(f"✅ Connecté à PostgreSQL")
            print(f"✅ Pool créé: {self.pool is not None}, ID: {id(self.pool)}")
            
            await self.init_tables()
            
            # Vérification finale
            if self.pool is None:
                print("❌ CRITIQUE: Pool est None après création!")
            else:
                print(f"✅ Database complètement initialisée, Pool ID: {id(self.pool)}")
                
        except Exception as e:
            print(f"❌ Erreur de connexion à PostgreSQL: {e}")
            import traceback
            traceback.print_exc()
            self.pool = None
    
    async def init_tables(self):
        """Crée les tables si elles n'existent pas"""
        if not self.pool:
            print("❌ init_tables: pool est None!")
            return
            
        print("🔄 Initialisation des tables...")
        async with self.pool.acquire() as conn:
            # === MIGRATION: Ajouter account_index à linked_accounts ===
            # 1. Vérifier si la colonne existe déjà
            column_exists = await conn.fetchval("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name = 'linked_accounts' 
                    AND column_name = 'account_index'
                )
            """)
            
            if not column_exists:
                print("🔄 Migration: Ajout de account_index à linked_accounts...")
                
                # 2. Supprimer l'ancienne PRIMARY KEY
                await conn.execute("""
                    ALTER TABLE linked_accounts 
                    DROP CONSTRAINT IF EXISTS linked_accounts_pkey
                """)
                
                # 3. Ajouter la colonne account_index avec valeur par défaut 1
                await conn.execute("""
                    ALTER TABLE linked_accounts 
                    ADD COLUMN account_index INTEGER DEFAULT 1
                """)
                
                # 4. Créer la nouvelle PRIMARY KEY composite
                await conn.execute("""
                    ALTER TABLE linked_accounts 
                    ADD PRIMARY KEY (discord_id, account_index)
                """)
                
                print("✅ Migration terminée: account_index ajouté")
            
            # Créer la table si elle n'existe pas (pour les nouvelles installations)
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS linked_accounts (
                    discord_id TEXT NOT NULL,
                    riot_id TEXT NOT NULL,
                    tagline TEXT NOT NULL,
                    puuid TEXT NOT NULL,
                    account_index INTEGER DEFAULT 1,
                    PRIMARY KEY (discord_id, account_index)
                )
            ''')
            
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS notified_users (
                    discord_id TEXT PRIMARY KEY,
                    notified_at TIMESTAMP DEFAULT NOW()
                )
            ''')
            # Migration rank_history pour supporter plusieurs comptes
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS rank_history (
                    discord_id TEXT,
                    puuid TEXT NOT NULL,
                    tier TEXT NOT NULL,
                    rank TEXT NOT NULL,
                    lp INTEGER NOT NULL,
                    timestamp TIMESTAMP DEFAULT NOW(),
                    PRIMARY KEY (discord_id, puuid, timestamp)
                )
            ''')
            
            # Ajouter la colonne puuid si elle n'existe pas (migration)
            puuid_column_exists = await conn.fetchval("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name = 'rank_history' 
                    AND column_name = 'puuid'
                )
            """)
            
            if not puuid_column_exists:
                print("🔄 Migration: Ajout de puuid à rank_history...")
                await conn.execute("ALTER TABLE rank_history ADD COLUMN puuid TEXT")
                print("✅ Migration rank_history terminée")
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
    
    # === FONCTIONS MODIFIÉES POUR MULTI-COMPTES ===
    
    async def get_linked_account(self, discord_id: str, account_index: int = None):
        """
        Récupère un ou plusieurs comptes liés
        Si account_index est None: retourne TOUS les comptes du joueur (liste)
        Si account_index est spécifié: retourne ce compte spécifique (dict ou None)
        """
        if not self.pool:
            return None if account_index else []
        
        async with self.pool.acquire() as conn:
            if account_index is not None:
                # Récupérer un compte spécifique
                row = await conn.fetchrow(
                    'SELECT riot_id, tagline, puuid, account_index FROM linked_accounts WHERE discord_id = $1 AND account_index = $2',
                    discord_id, account_index
                )
                if row:
                    return {
                        'riot_id': row['riot_id'],
                        'tagline': row['tagline'],
                        'puuid': row['puuid'],
                        'account_index': row['account_index']
                    }
                return None
            else:
                # Récupérer tous les comptes
                rows = await conn.fetch(
                    'SELECT riot_id, tagline, puuid, account_index FROM linked_accounts WHERE discord_id = $1 ORDER BY account_index',
                    discord_id
                )
                return [
                    {
                        'riot_id': row['riot_id'],
                        'tagline': row['tagline'],
                        'puuid': row['puuid'],
                        'account_index': row['account_index']
                    }
                    for row in rows
                ]
    
    async def save_linked_account(self, discord_id: str, riot_id: str, tagline: str, puuid: str, account_index: int = 1):
        """
        Sauvegarde un compte lié dans la DB
        account_index par défaut = 1 (premier compte)
        """
        if not self.pool:
            return False
        async with self.pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO linked_accounts (discord_id, riot_id, tagline, puuid, account_index)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (discord_id, account_index) DO UPDATE
                SET riot_id = $2, tagline = $3, puuid = $4
            ''', discord_id, riot_id, tagline, puuid, account_index)
        return True
    
    async def get_next_account_index(self, discord_id: str):
        """Récupère le prochain index de compte disponible (max 3)"""
        if not self.pool:
            return None
        async with self.pool.acquire() as conn:
            max_index = await conn.fetchval(
                'SELECT COALESCE(MAX(account_index), 0) FROM linked_accounts WHERE discord_id = $1',
                discord_id
            )
            next_index = max_index + 1
            return next_index if next_index <= 3 else None
    
    async def get_all_linked_accounts(self):
        """
        Récupère tous les comptes liés
        Retourne un dict groupé par discord_id avec liste de comptes
        """
        if not self.pool:
            return {}
        async with self.pool.acquire() as conn:
            rows = await conn.fetch('SELECT * FROM linked_accounts ORDER BY discord_id, account_index')
            
            # Grouper par discord_id
            result = {}
            for row in rows:
                discord_id = row['discord_id']
                if discord_id not in result:
                    result[discord_id] = []
                result[discord_id].append({
                    'riot_id': row['riot_id'],
                    'tagline': row['tagline'],
                    'puuid': row['puuid'],
                    'account_index': row['account_index']
                })
            
            return result
    
    async def get_all_puuids_for_discord_id(self, discord_id: str):
        """Récupère tous les PUUIDs d'un utilisateur Discord"""
        if not self.pool:
            return []
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                'SELECT puuid FROM linked_accounts WHERE discord_id = $1',
                discord_id
            )
            return [row['puuid'] for row in rows]
    
    # === FONCTIONS STATS MULTI-COMPTES ===
    
    async def get_player_stats_summary_multi(self, puuids: list, queue_filter: str = None):
        """
        Calcule un résumé agrégé des stats pour plusieurs PUUIDs
        Utilisé pour les stats agrégées de tous les comptes d'un joueur
        """
        if not self.pool or not puuids:
            return None
        
        queue_map = {
            'ranked': [420],
            'flex': [440],
            'normal': [400, 430],
            'aram': [450]
        }
        
        async with self.pool.acquire() as conn:
            # Construire la requête avec les PUUIDs
            puuid_placeholders = ','.join(f'${i+1}' for i in range(len(puuids)))
            
            base_query = f'''
                SELECT 
                    COUNT(*) as total_games,
                    SUM(CASE WHEN win THEN 1 ELSE 0 END) as wins,
                    SUM(kills) as total_kills,
                    SUM(deaths) as total_deaths,
                    SUM(assists) as total_assists
                FROM match_stats 
                WHERE puuid IN ({puuid_placeholders})
            '''
            
            cs_vision_query = f'''
                SELECT 
                    AVG(CAST(cs AS FLOAT) / (game_duration / 60.0)) as cs_per_min,
                    AVG(vision_score) as avg_vision_score
                FROM match_stats 
                WHERE puuid IN ({puuid_placeholders}) AND queue_id != 450
            '''
            
            # Ajouter le filtre de queue si nécessaire
            if queue_filter and queue_filter in queue_map:
                queue_ids = queue_map[queue_filter]
                queue_placeholders = ','.join(f'${i+len(puuids)+1}' for i in range(len(queue_ids)))
                base_query += f' AND queue_id IN ({queue_placeholders})'
                
                if queue_filter == 'aram':
                    cs_vision_query = None
                else:
                    cs_vision_query += f' AND queue_id IN ({queue_placeholders})'
                
                row = await conn.fetchrow(base_query, *puuids, *queue_ids)
                if cs_vision_query:
                    cs_vision_row = await conn.fetchrow(cs_vision_query, *puuids, *queue_ids)
                else:
                    cs_vision_row = None
            else:
                row = await conn.fetchrow(base_query, *puuids)
                cs_vision_row = await conn.fetchrow(cs_vision_query, *puuids)
            
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
                
                if cs_vision_row and cs_vision_row['cs_per_min']:
                    result['cs_per_min'] = round(cs_vision_row['cs_per_min'], 1)
                    result['avg_vision_score'] = round(cs_vision_row['avg_vision_score'], 1)
                else:
                    result['cs_per_min'] = None
                    result['avg_vision_score'] = None
                
                return result
            return None
    
    # === RESTE DES FONCTIONS INCHANGÉES ===
    
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
    
    async def get_last_rank(self, discord_id: str, puuid: str = None):
        """Récupère le dernier rang connu pour un compte spécifique"""
        if not self.pool:
            return None
        async with self.pool.acquire() as conn:
            if puuid:
                row = await conn.fetchrow(
                    'SELECT tier, rank, lp FROM rank_history WHERE discord_id = $1 AND puuid = $2 ORDER BY timestamp DESC LIMIT 1',
                    discord_id, puuid
                )
            else:
                # Fallback pour compatibilité (premier compte trouvé)
                row = await conn.fetchrow(
                    'SELECT tier, rank, lp FROM rank_history WHERE discord_id = $1 ORDER BY timestamp DESC LIMIT 1',
                    discord_id
                )
            if row:
                return {'tier': row['tier'], 'rank': row['rank'], 'lp': row['lp']}
            return None
    
    async def save_rank(self, discord_id: str, tier: str, rank: str, lp: int, puuid: str):
        """Sauvegarde un nouveau rang dans l'historique pour un compte spécifique"""
        if not self.pool:
            return
        async with self.pool.acquire() as conn:
            await conn.execute(
                'INSERT INTO rank_history (discord_id, puuid, tier, rank, lp) VALUES ($1, $2, $3, $4, $5)',
                discord_id, puuid, tier, rank, lp
            )
    
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
            print(f"❌ save_match_stats: pool est None! (ID instance: {id(self)})")
            return False
        
        try:
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
        except Exception as e:
            print(f"❌ Erreur save_match_stats: {e}")
            return False
    
    async def get_player_stats(self, puuid: str, queue_filter: str = None):
        """Récupère toutes les stats d'un joueur avec filtre optionnel"""
        if not self.pool:
            return []
        
        queue_map = {
            'ranked': [420],
            'flex': [440],
            'normal': [400, 430],
            'aram': [450]
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
        
        queue_map = {
            'ranked': [420],
            'flex': [440],
            'normal': [400, 430],
            'aram': [450]
        }
        
        async with self.pool.acquire() as conn:
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
            
            cs_vision_query = '''
                SELECT 
                    AVG(CAST(cs AS FLOAT) / (game_duration / 60.0)) as cs_per_min,
                    AVG(vision_score) as avg_vision_score
                FROM match_stats 
                WHERE puuid = $1 AND queue_id != 450
            '''
            
            if queue_filter and queue_filter in queue_map:
                queue_ids = queue_map[queue_filter]
                placeholders = ','.join(f'${i+2}' for i in range(len(queue_ids)))
                base_query += f' AND queue_id IN ({placeholders})'
                
                if queue_filter == 'aram':
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
    
        reached_threshold = max(
            (t for t in thresholds if current_value >= t),
            default=None
        )
    
        if reached_threshold is None:
            return None
    
        async with self.pool.acquire() as conn:
            last_saved = await conn.fetchval(
                '''
                SELECT MAX(milestone_value)
                FROM milestones
                WHERE puuid = $1 AND milestone_type = $2
                AND ($3::TEXT IS NULL OR extra_data = $3)
                ''',
                puuid, milestone_type, extra_data
            )
    
            if last_saved is not None and reached_threshold <= last_saved:
                return None
    
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
        """Calcule la série actuelle (win streak ou lose streak)"""
        if not self.pool:
            return None, 0
        
        async with self.pool.acquire() as conn:
            rows = await conn.fetch('''
                SELECT win FROM match_stats 
                WHERE puuid = $1 
                ORDER BY game_date DESC 
                LIMIT 20
            ''', puuid)
            
            if not rows or len(rows) == 0:
                return None, 0
            
            streak_type = 'win' if rows[0]['win'] else 'lose'
            streak_count = 0
            
            for row in rows:
                if (streak_type == 'win' and row['win']) or (streak_type == 'lose' and not row['win']):
                    streak_count += 1
                else:
                    break
            
            return streak_type, streak_count
    
    async def get_champion_stats(self, puuid: str):
        """Récupère les stats par champion"""
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
