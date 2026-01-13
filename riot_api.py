import aiohttp
from config import RIOT_API_KEY, REGION, PLATFORM
from datetime import datetime

async def get_summoner_by_riot_id(riot_id: str, tagline: str):
    """Récupère les infos du compte via Riot ID"""
    url = f"https://{PLATFORM}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{riot_id}/{tagline}"
    headers = {"X-Riot-Token": RIOT_API_KEY}
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as resp:
            if resp.status == 200:
                return await resp.json()
            return None

async def get_summoner_data(puuid: str):
    """Récupère les données du summoner via PUUID"""
    url = f"https://{REGION}.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{puuid}"
    headers = {"X-Riot-Token": RIOT_API_KEY}
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as resp:
            if resp.status == 200:
                return await resp.json()
            elif resp.status == 401:
                print(f"ERREUR API RIOT: Clé invalide ou expirée (401)")
                return None
            elif resp.status == 403:
                print(f"ERREUR API RIOT: Clé non autorisée (403)")
                return None
            else:
                print(f"ERREUR API RIOT: Status {resp.status}")
                return None

async def get_ranked_stats(puuid: str):
    """Récupère les stats ranked du joueur via PUUID"""
    url = f"https://{REGION}.api.riotgames.com/lol/league/v4/entries/by-puuid/{puuid}"
    headers = {"X-Riot-Token": RIOT_API_KEY}
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as resp:
            if resp.status == 200:
                data = await resp.json()
                # Cherche la queue RANKED_SOLO_5x5
                for queue in data:
                    if queue['queueType'] == 'RANKED_SOLO_5x5':
                        return queue
                return None
            return None

async def get_match_list(puuid: str, start: int = 0, count: int = 5):
    """Récupère la liste des IDs des matchs d'un joueur avec pagination"""
    url = f"https://{PLATFORM}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids"
    params = {"start": start, "count": count}
    headers = {"X-Riot-Token": RIOT_API_KEY}
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, params=params) as resp:
            if resp.status == 200:
                return await resp.json()
            else:
                print(f"Erreur récupération matchs pour {puuid}: {resp.status}")
                return []

async def get_match_details(match_id: str):
    """Récupère les détails complets d'un match"""
    url = f"https://{PLATFORM}.api.riotgames.com/lol/match/v5/matches/{match_id}"
    headers = {"X-Riot-Token": RIOT_API_KEY}
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as resp:
            if resp.status == 200:
                return await resp.json()
            else:
                print(f"Erreur récupération détails match {match_id}: {resp.status}")
                return None

def extract_player_stats(match_data: dict, puuid: str):
    """Extrait les stats d'un joueur spécifique depuis les données d'un match"""
    if not match_data:
        return None
    
    try:
        # Convertir le timestamp en datetime (gameCreation est en millisecondes)
        game_timestamp_ms = match_data['info']['gameCreation']
        game_date = datetime.fromtimestamp(game_timestamp_ms / 1000)
        
        # Date de début de saison (8 janvier 2025)
        season_start = datetime(2025, 1, 8, 0, 0, 0)
        
        # Debug
        print(f"  └─ 📅 Timestamp: {game_timestamp_ms} -> Date: {game_date.strftime('%Y-%m-%d %H:%M')}")
        
        # Vérifier si le match est de la saison actuelle AVANT de continuer
        if game_date < season_start:
            print(f"  └─ ⏭️  Match avant le 8 janvier 2025, ignoré")
            return None
        
        # Trouver le participant correspondant au PUUID
        participant = None
        for p in match_data['info']['participants']:
            if p['puuid'] == puuid:
                participant = p
                break
        
        if not participant:
            return None
        
        # Extraire les stats
        stats = {
            'champion': participant['championName'],
            'kills': participant['kills'],
            'deaths': participant['deaths'],
            'assists': participant['assists'],
            'cs': participant['totalMinionsKilled'] + participant['neutralMinionsKilled'],
            'game_duration': match_data['info']['gameDuration'],
            'vision_score': participant['visionScore'],
            'win': participant['win'],
            'queue_id': match_data['info']['queueId'],
            'game_date': game_date  # Utiliser la date déjà convertie
        }
        
        return stats
    
    except Exception as e:
        print(f"Erreur extraction stats: {e}")
        import traceback
        traceback.print_exc()
        return None

