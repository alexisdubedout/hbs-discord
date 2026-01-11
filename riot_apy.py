import aiohttp
from config import RIOT_API_KEY, REGION, PLATFORM

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