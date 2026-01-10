import discord
from discord import app_commands
from discord.ext import commands
import aiohttp
import json
import random
import os
import asyncpg
from typing import Optional

# Configuration
RIOT_API_KEY = os.getenv('RIOT_API_KEY', 'VOTRE_CLE_API_RIOT')
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN', 'VOTRE_TOKEN_DISCORD')
REGION = 'euw1'
PLATFORM = 'europe'

# Liste complète des champions LoL (à jour patch 14.24)
CHAMPIONS = [
    "Aatrox", "Ahri", "Akali", "Akshan", "Alistar", "Amumu", "Anivia", "Annie", "Aphelios",
    "Ashe", "Aurelion Sol", "Azir", "Bard", "Bel'Veth", "Blitzcrank", "Brand", "Braum", "Briar",
    "Caitlyn", "Camille", "Cassiopeia", "Cho'Gath", "Corki", "Darius", "Diana", "Dr. Mundo",
    "Draven", "Ekko", "Elise", "Evelynn", "Ezreal", "Fiddlesticks", "Fiora", "Fizz", "Galio",
    "Gangplank", "Garen", "Gnar", "Gragas", "Graves", "Gwen", "Hecarim", "Heimerdinger", "Hwei",
    "Illaoi", "Irelia", "Ivern", "Janna", "Jarvan IV", "Jax", "Jayce", "Jhin", "Jinx", "K'Sante",
    "Kai'Sa", "Kalista", "Karma", "Karthus", "Kassadin", "Katarina", "Kayle", "Kayn", "Kennen",
    "Kha'Zix", "Kindred", "Kled", "Kog'Maw", "LeBlanc", "Lee Sin", "Leona", "Lillia", "Lissandra",
    "Lucian", "Lulu", "Lux", "Malphite", "Malzahar", "Maokai", "Master Yi", "Milio", "Miss Fortune",
    "Mordekaiser", "Morgana", "Naafiri", "Nami", "Nasus", "Nautilus", "Neeko", "Nidalee", "Nilah",
    "Nocturne", "Nunu", "Olaf", "Orianna", "Ornn", "Pantheon", "Poppy", "Pyke", "Qiyana", "Quinn",
    "Rakan", "Rammus", "Rek'Sai", "Rell", "Renata Glasc", "Renekton", "Rengar", "Riven", "Rumble",
    "Ryze", "Samira", "Sejuani", "Senna", "Seraphine", "Sett", "Shaco", "Shen", "Shyvana", "Singed",
    "Sion", "Sivir", "Skarner", "Smolder", "Sona", "Soraka", "Swain", "Sylas", "Syndra", "Tahm Kench",
    "Taliyah", "Talon", "Taric", "Teemo", "Thresh", "Tristana", "Trundle", "Tryndamere", "Twisted Fate",
    "Twitch", "Udyr", "Urgot", "Varus", "Vayne", "Veigar", "Vel'Koz", "Vex", "Vi", "Viego", "Viktor",
    "Vladimir", "Volibear", "Warwick", "Wukong", "Xayah", "Xerath", "Xin Zhao", "Yasuo", "Yone",
    "Yorick", "Yuumi", "Zac", "Zed", "Zeri", "Ziggs", "Zilean", "Zoe", "Zyra"
]

ROLES = ["Top", "Jungle", "Mid", "ADC", "Support"]

# Emojis de rang
RANK_EMOJIS = {
    "IRON": "⚫",
    "BRONZE": "🟤",
    "SILVER": "⚪",
    "GOLD": "🟡",
    "PLATINUM": "🔵",
    "EMERALD": "🟢",
    "DIAMOND": "💎",
    "MASTER": "🔮",
    "GRANDMASTER": "🌟",
    "CHALLENGER": "👑",
    "UNRANKED": "❓"
}

class LoLBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.members = True
        intents.voice_states = True
        
        super().__init__(command_prefix="!", intents=intents)
        self.db_pool = None
        
    async def setup_hook(self):
        """Initialise la connexion à la base de données"""
        database_url = os.getenv('DATABASE_URL')
        if database_url:
            try:
                self.db_pool = await asyncpg.create_pool(database_url)
                print("✅ Connecté à PostgreSQL")
                await self.init_database()
            except Exception as e:
                print(f"❌ Erreur de connexion à PostgreSQL: {e}")
        else:
            print("⚠️ DATABASE_URL non trouvé, utilisation de la mémoire (non persistant)")
    
    async def init_database(self):
        """Crée les tables si elles n'existent pas"""
        async with self.db_pool.acquire() as conn:
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
        if not self.db_pool:
            return None
        async with self.db_pool.acquire() as conn:
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
        if not self.db_pool:
            return False
        async with self.db_pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO linked_accounts (discord_id, riot_id, tagline, puuid)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (discord_id) DO UPDATE
                SET riot_id = $2, tagline = $3, puuid = $4
            ''', discord_id, riot_id, tagline, puuid)
        return True
    
    async def get_all_linked_accounts(self):
        """Récupère tous les comptes liés"""
        if not self.db_pool:
            return {}
        async with self.db_pool.acquire() as conn:
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
        if not self.db_pool:
            return False
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                'SELECT 1 FROM notified_users WHERE discord_id = $1',
                discord_id
            )
            return row is not None
    
    async def mark_user_notified(self, discord_id: str):
        """Marque un utilisateur comme notifié"""
        if not self.db_pool:
            return
        async with self.db_pool.acquire() as conn:
            await conn.execute(
                'INSERT INTO notified_users (discord_id) VALUES ($1) ON CONFLICT DO NOTHING',
                discord_id
            )
    
    async def get_last_rank(self, discord_id: str):
        """Récupère le dernier rang connu"""
        if not self.db_pool:
            return None
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                'SELECT tier, rank, lp FROM rank_history WHERE discord_id = $1 ORDER BY timestamp DESC LIMIT 1',
                discord_id
            )
            if row:
                return {'tier': row['tier'], 'rank': row['rank'], 'lp': row['lp']}
            return None
    
    async def save_rank(self, discord_id: str, tier: str, rank: str, lp: int):
        """Sauvegarde un nouveau rang dans l'historique"""
        if not self.db_pool:
            return
        async with self.db_pool.acquire() as conn:
            await conn.execute(
                'INSERT INTO rank_history (discord_id, tier, rank, lp) VALUES ($1, $2, $3, $4)',
                discord_id, tier, rank, lp
            )

bot = LoLBot()

async def send_link_reminder(user: discord.Member):
    """Envoie un DM de rappel pour lier le compte"""
    user_id = str(user.id)
    
    # Vérifier si déjà notifié ou déjà lié
    is_notified = await bot.is_user_notified(user_id)
    linked_account = await bot.get_linked_account(user_id)
    
    if is_notified or linked_account:
        return
    
    try:
        embed = discord.Embed(
            title="🎮 Bienvenue sur le serveur LoL !",
            description="Hey ! Je vois que tu n'as pas encore lié ton compte Riot.",
            color=discord.Color.blue()
        )
        embed.add_field(
            name="Comment faire ?",
            value="Utilise la commande `/link` dans le serveur :\n`/link TonPseudo TAG`\n\nExemple : `/link Faker KR1`",
            inline=False
        )
        embed.add_field(
            name="Pourquoi ?",
            value="Ça permet d'afficher le classement du serveur et de participer aux teams aléatoires !",
            inline=False
        )
        embed.set_footer(text="Ce message est automatique et envoyé une seule fois")
        
        await user.send(embed=embed)
        
        # Marquer comme notifié
        await bot.mark_user_notified(user_id)
        
    except discord.Forbidden:
        # L'utilisateur a bloqué les DMs
        pass
    except Exception as e:
        print(f"Erreur lors de l'envoi du DM à {user.name}: {e}")

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

def get_rank_value(tier: str, rank: str, lp: int):
    """Calcule une valeur numérique pour trier les rangs"""
    tier_values = {
        "IRON": 0, "BRONZE": 1, "SILVER": 2, "GOLD": 3,
        "PLATINUM": 4, "EMERALD": 5, "DIAMOND": 6,
        "MASTER": 7, "GRANDMASTER": 8, "CHALLENGER": 9
    }
    
    rank_values = {"IV": 0, "III": 1, "II": 2, "I": 3}
    
    tier_val = tier_values.get(tier, -1)
    if tier in ["MASTER", "GRANDMASTER", "CHALLENGER"]:
        return tier_val * 1000 + lp
    
    rank_val = rank_values.get(rank, 0)
    return tier_val * 1000 + rank_val * 100 + lp

@bot.event
async def on_ready():
    print(f'{bot.user} est connecté!')
    try:
        synced = await bot.tree.sync()
        print(f"Synchronisé {len(synced)} commandes")
    except Exception as e:
        print(f"Erreur lors de la sync: {e}")

@bot.event
async def on_message(message):
    # Ignorer les messages du bot
    if message.author.bot:
        return
    
    # Vérifier si l'utilisateur n'est pas lié
    user_id = str(message.author.id)
    linked_account = await bot.get_linked_account(user_id)
    is_notified = await bot.is_user_notified(user_id)
    
    if not linked_account and not is_notified:
        await send_link_reminder(message.author)
    
    await bot.process_commands(message)

@bot.event
async def on_voice_state_update(member, before, after):
    # Quelqu'un rejoint un vocal
    if before.channel is None and after.channel is not None:
        user_id = str(member.id)
        linked_account = await bot.get_linked_account(user_id)
        is_notified = await bot.is_user_notified(user_id)
        
        if not linked_account and not is_notified:
            await send_link_reminder(member)

@bot.tree.command(name="say", description="[ADMIN] Fait parler le bot")
@app_commands.describe(
    channel="Le channel où envoyer le message",
    message="Le message à envoyer"
)
async def say(interaction: discord.Interaction, channel: discord.TextChannel, message: str):
    # Vérifier les permissions admin
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Tu n'as pas la permission d'utiliser cette commande.", ephemeral=True)
        return
    
    # Réponse invisible
    await interaction.response.send_message(f"✅ Message envoyé dans {channel.mention}", ephemeral=True)
    
    # Envoyer le message dans le channel
    await channel.send(message)

@bot.tree.command(name="link", description="Lie ton compte Riot à Discord")
@app_commands.describe(
    riot_id="Ton Riot ID (ex: Faker)",
    tagline="Ton tagline (ex: KR1)"
)
async def link(interaction: discord.Interaction, riot_id: str, tagline: str):
    await interaction.response.defer()
    
    account = await get_summoner_by_riot_id(riot_id, tagline)
    if not account:
        await interaction.followup.send("❌ Compte Riot introuvable. Vérifie ton Riot ID et tagline.")
        return
    
    summoner = await get_summoner_data(account['puuid'])
    if not summoner:
        await interaction.followup.send("❌ Erreur lors de la récupération des données.")
        return
    
    user_id = str(interaction.user.id)
    success = await bot.save_linked_account(user_id, riot_id, tagline, account['puuid'])
    
    if success:
        await interaction.followup.send(f"✅ Compte lié avec succès: **{riot_id}#{tagline}**")
    else:
        await interaction.followup.send("❌ Erreur lors de la sauvegarde.")

@bot.tree.command(name="admin_link", description="[ADMIN] Lie un compte Riot pour un autre utilisateur")
@app_commands.describe(
    user="L'utilisateur Discord",
    riot_id="Son Riot ID",
    tagline="Son tagline"
)
async def admin_link(interaction: discord.Interaction, user: discord.Member, riot_id: str, tagline: str):
    # Vérifier si l'utilisateur a les permissions (admin ou gérer le serveur)
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Tu n'as pas la permission d'utiliser cette commande.", ephemeral=True)
        return
    
    await interaction.response.defer()
    
    account = await get_summoner_by_riot_id(riot_id, tagline)
    if not account:
        await interaction.followup.send("❌ Compte Riot introuvable. Vérifie le Riot ID et tagline.")
        return
    
    summoner = await get_summoner_data(account['puuid'])
    if not summoner:
        await interaction.followup.send("❌ Erreur lors de la récupération des données.")
        return
    
    user_id = str(user.id)
    success = await bot.save_linked_account(user_id, riot_id, tagline, account['puuid'])
    
    if success:
        await interaction.followup.send(f"✅ Compte lié pour {user.mention}: **{riot_id}#{tagline}**")
    else:
        await interaction.followup.send("❌ Erreur lors de la sauvegarde.")

@bot.tree.command(name="leaderboard", description="Affiche le classement du serveur")
async def leaderboard(interaction: discord.Interaction):
    await interaction.response.defer()
    
    linked_accounts = await bot.get_all_linked_accounts()
    
    if not linked_accounts:
        await interaction.followup.send("❌ Aucun compte lié pour le moment.")
        return
    
    players_data = []
