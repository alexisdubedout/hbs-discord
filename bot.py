import discord
from discord import app_commands
from discord.ext import commands
import aiohttp
import json
import random
import os
from typing import Optional

# Configuration
RIOT_API_KEY = os.getenv('RIOT_API_KEY', 'VOTRE_CLE_API_RIOT')
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN', 'VOTRE_TOKEN_DISCORD')
REGION = 'euw1'
PLATFORM = 'europe'

# Fichiers de stockage
LINKED_ACCOUNTS_FILE = 'linked_accounts.json'
NOTIFIED_USERS_FILE = 'notified_users.json'

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
        self.linked_accounts = self.load_linked_accounts()
        self.notified_users = self.load_notified_users()
        
    def load_linked_accounts(self):
        try:
            with open(LINKED_ACCOUNTS_FILE, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
    
    def save_linked_accounts(self):
        with open(LINKED_ACCOUNTS_FILE, 'w') as f:
            json.dump(self.linked_accounts, f, indent=4)
    
    def load_notified_users(self):
        try:
            with open(NOTIFIED_USERS_FILE, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return []
    
    def save_notified_users(self):
        with open(NOTIFIED_USERS_FILE, 'w') as f:
            json.dump(self.notified_users, f, indent=4)

bot = LoLBot()

async def send_link_reminder(user: discord.Member):
    """Envoie un DM de rappel pour lier le compte"""
    user_id = str(user.id)
    
    # Vérifier si déjà notifié ou déjà lié
    if user_id in bot.notified_users or user_id in bot.linked_accounts:
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
        bot.notified_users.append(user_id)
        bot.save_notified_users()
        
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

async def get_ranked_stats(summoner_id: str):
    """Récupère les stats ranked du joueur"""
    url = f"https://{REGION}.api.riotgames.com/lol/league/v4/entries/by-summoner/{summoner_id}"
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
    if user_id not in bot.linked_accounts and user_id not in bot.notified_users:
        await send_link_reminder(message.author)
    
    await bot.process_commands(message)

@bot.event
async def on_voice_state_update(member, before, after):
    # Quelqu'un rejoint un vocal
    if before.channel is None and after.channel is not None:
        user_id = str(member.id)
        if user_id not in bot.linked_accounts and user_id not in bot.notified_users:
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
    bot.linked_accounts[user_id] = {
        "riot_id": riot_id,
        "tagline": tagline,
        "puuid": account['puuid']
    }
    bot.save_linked_accounts()
    
    # Retirer des utilisateurs notifiés s'il y était
    if user_id in bot.notified_users:
        bot.notified_users.remove(user_id)
        bot.save_notified_users()
    
    await interaction.followup.send(f"✅ Compte lié avec succès: **{riot_id}#{tagline}**")

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
    bot.linked_accounts[user_id] = {
        "riot_id": riot_id,
        "tagline": tagline,
        "puuid": account['puuid']
    }
    bot.save_linked_accounts()
    
    # Retirer des utilisateurs notifiés s'il y était
    if user_id in bot.notified_users:
        bot.notified_users.remove(user_id)
        bot.save_notified_users()
    
    await interaction.followup.send(f"✅ Compte lié pour {user.mention}: **{riot_id}#{tagline}**")

@bot.tree.command(name="leaderboard", description="Affiche le classement du serveur")
async def leaderboard(interaction: discord.Interaction):
    await interaction.response.defer()
    
    if not bot.linked_accounts:
        await interaction.followup.send("❌ Aucun compte lié pour le moment.")
        return
    
    players_data = []
    
    for discord_id, account_info in bot.linked_accounts.items():
        try:
            member = interaction.guild.get_member(int(discord_id))
            if not member:
                continue
            
            summoner = await get_summoner_data(account_info['puuid'])
            if not summoner:
                print(f"Impossible de récupérer les données pour {member.display_name} (PUUID: {account_info['puuid'][:20]}...)")
                continue
            
            print(f"DEBUG - Summoner data pour {member.display_name}: {summoner}")
            
            if 'id' not in summoner:
                print(f"ERREUR: 'id' manquant dans la réponse API pour {member.display_name}")
                continue
            
            ranked_stats = await get_ranked_stats(summoner['id'])
            
            if ranked_stats:
                tier = ranked_stats['tier']
                rank = ranked_stats['rank']
                lp = ranked_stats['leaguePoints']
                wins = ranked_stats['wins']
                losses = ranked_stats['losses']
                total = wins + losses
                winrate = round((wins / total) * 100, 1) if total > 0 else 0
                
                rank_value = get_rank_value(tier, rank, lp)
                
                players_data.append({
                    'name': member.display_name,
                    'riot_id': f"{account_info['riot_id']}#{account_info['tagline']}",
                    'tier': tier,
                    'rank': rank,
                    'lp': lp,
                    'wins': wins,
                    'losses': losses,
                    'winrate': winrate,
                    'rank_value': rank_value
                })
            else:
                players_data.append({
                    'name': member.display_name,
                    'riot_id': f"{account_info['riot_id']}#{account_info['tagline']}",
                    'tier': 'UNRANKED',
                    'rank': '',
                    'lp': 0,
                    'wins': 0,
                    'losses': 0,
                    'winrate': 0,
                    'rank_value': -1
                })
        except KeyError as e:
            print(f"Erreur KeyError pour {discord_id}: clé manquante = {e}")
            print(f"Données disponibles: {summoner.keys() if summoner else 'summoner is None'}")
            continue
        except Exception as e:
            print(f"Erreur générale pour {discord_id}: {type(e).__name__} - {e}")
            continue
    
    if not players_data:
        await interaction.followup.send("❌ Aucune donnée disponible.")
        return
    
    # Trier par rang
    players_data.sort(key=lambda x: x['rank_value'], reverse=True)
    
    # Créer l'embed
    embed = discord.Embed(
        title="🏆 Classement du Serveur",
        color=discord.Color.gold(),
        description="Classement SoloQ des joueurs du serveur"
    )
    
    for i, player in enumerate(players_data, 1):
        emoji = RANK_EMOJIS.get(player['tier'], "❓")
        
        if player['tier'] == 'UNRANKED':
            rank_str = f"{emoji} **Unranked**"
        elif player['tier'] in ['MASTER', 'GRANDMASTER', 'CHALLENGER']:
            rank_str = f"{emoji} **{player['tier'].title()}** - {player['lp']} LP"
        else:
            rank_str = f"{emoji} **{player['tier'].title()} {player['rank']}** - {player['lp']} LP"
        
        value = f"{rank_str}\n`{player['wins']}W {player['losses']}L - {player['winrate']}% WR`"
        
        embed.add_field(
            name=f"#{i} {player['name']}",
            value=value,
            inline=False
        )
    
    embed.set_footer(text=f"Mis à jour le")
    embed.timestamp = discord.utils.utcnow()
    
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="random_teams", description="Génère 2 équipes aléatoires depuis le vocal")
async def random_teams(interaction: discord.Interaction):
    # Vérifier si l'utilisateur est dans un vocal
    if not interaction.user.voice:
        await interaction.response.send_message("❌ Tu dois être dans un channel vocal!", ephemeral=True)
        return
    
    voice_channel = interaction.user.voice.channel
    members = [m for m in voice_channel.members if not m.bot]
    
    if len(members) < 2:
        await interaction.response.send_message("❌ Pas assez de joueurs dans le vocal!", ephemeral=True)
        return
    
    if len(members) > 10:
        await interaction.response.send_message("❌ Trop de joueurs dans le vocal (max 10)!", ephemeral=True)
        return
    
    await interaction.response.defer()
    
    # Mélanger les joueurs
    random.shuffle(members)
    
    # Diviser en 2 équipes
    team_size = len(members) // 2
    team1 = members[:team_size]
    team2 = members[team_size:team_size*2]
    
    # Assigner rôles et champions
    roles_pool = ROLES.copy()
    random.shuffle(roles_pool)
    
    def assign_team(team):
        assignments = []
        available_roles = roles_pool.copy()
        for member in team:
            if available_roles:
                role = available_roles.pop(0)
            else:
                role = random.choice(ROLES)
            champion = random.choice(CHAMPIONS)
            assignments.append((member, role, champion))
        return assignments
    
    team1_assignments = assign_team(team1)
    team2_assignments = assign_team(team2)
    
    # Créer l'embed
    embed = discord.Embed(
        title="🎲 Teams Aléatoires",
        color=discord.Color.blue(),
        description=f"Généré depuis **{voice_channel.name}**"
    )
    
    # Team 1
    team1_text = ""
    for member, role, champion in team1_assignments:
        team1_text += f"**{role}**: {member.mention} - *{champion}*\n"
    
    embed.add_field(name="🔵 Team Bleue", value=team1_text, inline=True)
    
    # Team 2
    team2_text = ""
    for member, role, champion in team2_assignments:
        team2_text += f"**{role}**: {member.mention} - *{champion}*\n"
    
    embed.add_field(name="🔴 Team Rouge", value=team2_text, inline=True)
    
    if len(members) % 2 != 0:
        leftover = members[-1]
        embed.add_field(
            name="⚪ Joueur supplémentaire",
            value=f"{leftover.mention}",
            inline=False
        )
    
    embed.set_footer(text="Good luck, have fun!")
    embed.timestamp = discord.utils.utcnow()
    
    await interaction.followup.send(embed=embed)

# Lancer le bot
if __name__ == "__main__":
    # Debug : vérifier que le token est bien chargé
    if not DISCORD_TOKEN or DISCORD_TOKEN == 'VOTRE_TOKEN_DISCORD':
        print("ERREUR: Token Discord non trouvé dans les variables d'environnement!")
        print("Vérifiez que DISCORD_TOKEN est bien défini dans Railway")
        exit(1)
    
    print(f"Token Discord chargé (premiers caractères): {DISCORD_TOKEN[:20]}...")
    print(f"Longueur du token Discord: {len(DISCORD_TOKEN)}")
    
    # Debug : vérifier la clé Riot
    if not RIOT_API_KEY or RIOT_API_KEY == 'VOTRE_CLE_API_RIOT':
        print("ERREUR: Clé API Riot non trouvée dans les variables d'environnement!")
        print("Vérifiez que RIOT_API_KEY est bien défini dans Railway")
        exit(1)
    
    print(f"Clé Riot chargée (premiers caractères): {RIOT_API_KEY[:15]}...")
    print(f"Longueur de la clé Riot: {len(RIOT_API_KEY)}")
    
    bot.run(DISCORD_TOKEN)
