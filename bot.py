import discord
from discord.ext import commands, tasks
import config
from database import Database
from riot_api import get_ranked_stats
from commands import register_commands

class LoLBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.members = True
        intents.voice_states = True
        
        super().__init__(command_prefix="!", intents=intents)
        self.db = Database()
    
    async def setup_hook(self):
        await self.db.connect()
        register_commands(self)

bot = LoLBot()

async def send_link_reminder(user: discord.Member):
    """Envoie un DM de rappel pour lier le compte"""
    user_id = str(user.id)
    
    is_notified = await bot.db.is_user_notified(user_id)
    linked_account = await bot.db.get_linked_account(user_id)
    
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
        await bot.db.mark_user_notified(user_id)
        
    except discord.Forbidden:
        pass
    except Exception as e:
        print(f"Erreur DM à {user.name}: {e}")

@bot.event
async def on_ready():
    print(f"{bot.user} est connecté !")
    try:
        synced = await bot.tree.sync()
        print(f"Synchronisé {len(synced)} commandes")
    except Exception as e:
        print(f"Erreur sync commandes: {e}")

    if not check_rank_changes.is_running():
        check_rank_changes.start()

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    
    user_id = str(message.author.id)
    linked_account = await bot.db.get_linked_account(user_id)
    is_notified = await bot.db.is_user_notified(user_id)
    
    if not linked_account and not is_notified:
        await send_link_reminder(message.author)
    
    await bot.process_commands(message)

@bot.event
async def on_voice_state_update(member, before, after):
    if before.channel is None and after.channel is not None:
        user_id = str(member.id)
        linked_account = await bot.db.get_linked_account(user_id)
        is_notified = await bot.db.is_user_notified(user_id)
        
        if not linked_account and not is_notified:
            await send_link_reminder(member)

@tasks.loop(minutes=30)
async def check_rank_changes():
    """Vérifie les changements de rang toutes les 30 minutes"""
    if not bot.db.pool:
        return

    linked_accounts = await bot.db.get_all_linked_accounts()

    for discord_id, account_info in linked_accounts.items():
        try:
            stats = await get_ranked_stats(account_info['puuid'])

            if not stats:
                continue

            tier = stats['tier']
            rank = stats['rank']
            lp = stats['leaguePoints']

            last_rank = await bot.db.get_last_rank(discord_id)

            # Premier enregistrement
            if not last_rank:
                await bot.db.save_rank(discord_id, tier, rank, lp)
                continue

            old_tier = last_rank['tier']
            old_rank = last_rank['rank']
            old_lp = last_rank['lp']

            # Vérifier si changement de pallier (tier)
            tier_changed = old_tier != tier

            if tier_changed:
                await bot.db.save_rank(discord_id, tier, rank, lp)

                # Trouver le salon "général" ou similaire
                for guild in bot.guilds:
                    member = guild.get_member(int(discord_id))
                    if not member:
                        continue

                    # Chercher un salon d'annonces
                    announcement_channel = None
                    for channel in guild.text_channels:
                        if channel.name.lower() in ['général', 'general', 'annonces', 'announcements', 'lobby', 'tchat']:
                            announcement_channel = channel
                            break
                    
                    # Si aucun salon trouvé, utiliser le premier salon textuel disponible
                    if not announcement_channel:
                        announcement_channel = guild.text_channels[0] if guild.text_channels else None

                    if announcement_channel:
                        emoji = config.RANK_EMOJIS.get(tier, "❓")
                        old_emoji = config.RANK_EMOJIS.get(old_tier, "❓")

                        if tier in ['MASTER', 'GRANDMASTER', 'CHALLENGER']:
                            rank_str = f"{emoji} **{tier.title()}** - {lp} LP"
                        else:
                            rank_str = f"{emoji} **{tier.title()} {rank}** - {lp} LP"

                        if old_tier in ['MASTER', 'GRANDMASTER', 'CHALLENGER']:
                            old_rank_str = f"{old_emoji} {old_tier.title()}"
                        else:
                            old_rank_str = f"{old_emoji} {old_tier.title()} {old_rank}"

                        # Déterminer si c'est une montée ou une descente
                        tier_values = {
                            "IRON": 0, "BRONZE": 1, "SILVER": 2, "GOLD": 3,
                            "PLATINUM": 4, "EMERALD": 5, "DIAMOND": 6,
                            "MASTER": 7, "GRANDMASTER": 8, "CHALLENGER": 9
                        }
                        
                        is_promotion = tier_values.get(tier, 0) > tier_values.get(old_tier, 0)

                        embed = discord.Embed(
                            title="🎊 CHANGEMENT DE RANG !" if is_promotion else "📉 Changement de rang",
                            color=discord.Color.gold() if is_promotion else discord.Color.orange(),
                            description=f"{member.mention} a changé de pallier !"
                        )
                        
                        embed.add_field(
                            name="Ancien rang",
                            value=old_rank_str,
                            inline=True
                        )
                        embed.add_field(
                            name="➡️",
                            value="",
                            inline=True
                        )
                        embed.add_field(
                            name="Nouveau rang",
                            value=rank_str,
                            inline=True
                        )

                        if is_promotion:
                            embed.set_footer(text="Félicitations ! 🎉")
                        else:
                            embed.set_footer(text="Ne lâche rien, tu vas remonter ! 💪")

                        embed.timestamp = discord.utils.utcnow()

                        try:
                            await announcement_channel.send(embed=embed)
                        except discord.Forbidden:
                            print(f"Pas la permission d'envoyer dans {announcement_channel.name}")

        except Exception as e:
            print(f"Erreur check_rank_changes pour {discord_id}: {e}")

if __name__ == "__main__":
    bot.run(config.DISCORD_TOKEN)
