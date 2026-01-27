import discord
from discord.ext import commands, tasks
from config import DISCORD_TOKEN, RANK_EMOJIS
from database import Database
from riot_api import get_ranked_stats, get_match_list, get_match_details, extract_player_stats
import asyncio

class LoLBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.members = True
        intents.voice_states = True
        
        super().__init__(command_prefix="!", intents=intents)
        self.db = Database()
        self.syncing_players = set()
        self.db_ready = False  # Flag pour indiquer que la DB est prête
    
    async def setup_hook(self):
        await self.db.connect()
        self.db_ready = True  # Marquer la DB comme prête
        print("✅ Database prête et flag db_ready activé")
        # Importer commands APRÈS initialisation du bot
        from commands import register_commands
        register_commands(self)

bot = LoLBot()

# === FULL HISTORY SYNC AVEC MILESTONES ===

async def sync_player_full_history(puuid: str, riot_id: str, progress_callback=None):
    """
    Récupère l'historique complet des matchs d'un joueur pour la saison en cours
    """
    # ATTENDRE que la DB soit prête (retry 5 fois avec 2 sec entre chaque)
    print(f"🔍 sync_player_full_history pour {riot_id}")
    print(f"   └─ bot.db existe: {bot.db is not None}")
    if bot.db:
        print(f"   └─ bot.db.pool existe: {bot.db.pool is not None}")
        print(f"   └─ bot.db ID: {id(bot.db)}, pool ID: {id(bot.db.pool) if bot.db.pool else 'None'}")
    
    for attempt in range(5):
        if bot.db and bot.db.pool:
            print(f"✅ DB prête pour {riot_id} après {attempt + 1} tentatives")
            break
        
        print(f"⚠️ Pool DB non prêt pour {riot_id}, tentative {attempt + 1}/5...")
        await asyncio.sleep(2)
    
    # VÉRIFICATION FINALE
    if not bot.db or not bot.db.pool:
        error_msg = f"❌ Database non initialisée pour {riot_id} après 5 tentatives!"
        print(error_msg)
        if progress_callback:
            try:
                await progress_callback(
                    f"❌ Erreur: Base de données non prête.\n"
                    f"Réessaye dans quelques minutes avec `/sync_account`."
                )
            except:
                pass
        return 0
    
    if puuid in bot.syncing_players:
        print(f"⚠️ Sync déjà en cours pour {riot_id}")
        return 0
    
    bot.syncing_players.add(puuid)
    
    try:
        new_matches = 0
        start_index = 0
        batch_size = 100
        total_checked = 0
        
        print(f"\n{'='*70}")
        print(f"🔄 SYNC START: {riot_id}")
        print(f"✅ Pool DB OK: {bot.db.pool is not None}")
        print(f"{'='*70}")
        
        while total_checked < 1000:
            print(f"\n📦 BATCH {start_index // batch_size + 1} - Offset: {start_index}")
            
            if progress_callback:
                try:
                    await progress_callback(
                        f"🔍 Analyse en cours...\n"
                        f"📊 {total_checked} matchs vérifiés\n"
                        f"✅ {new_matches} nouveaux matchs enregistrés"
                    )
                except Exception as e:
                    print(f"⚠️ Erreur callback: {e}")
            
            # Récupérer un batch de matchs
            try:
                match_ids = await get_match_list(puuid, start=start_index, count=batch_size)
                print(f"✅ API Response: {len(match_ids) if match_ids else 0} matchs")
            except Exception as e:
                print(f"❌ ERREUR get_match_list: {e}")
                break
            
            if not match_ids:
                print(f"✅ Fin de l'historique (aucun match trouvé)")
                break
            
            total_checked += len(match_ids)
            print(f"📊 Total vérifié: {total_checked} matchs")
            
            found_old_season = False
            
            for idx, match_id in enumerate(match_ids, 1):
                print(f"\n  [{idx}/{len(match_ids)}] 🔍 Match: {match_id[:20]}...")
                
                # Vérifier à nouveau la DB avant chaque opération critique
                if not bot.db or not bot.db.pool:
                    print(f"  └─ ❌ DB perdue pendant la sync!")
                    return new_matches
                
                try:
                    if await bot.db.match_exists(match_id, puuid):
                        print(f"  └─ ⏭️  Déjà en DB, skip")
                        continue
                except Exception as e:
                    print(f"  └─ ❌ Erreur match_exists: {e}")
                    continue
                
                await asyncio.sleep(0.5)
                
                try:
                    match_data = await get_match_details(match_id)
                    
                    if not match_data:
                        print(f"  └─ ❌ Pas de données")
                        continue
                except Exception as e:
                    print(f"  └─ ❌ Erreur get_match_details: {e}")
                    continue
                
                try:
                    stats = extract_player_stats(match_data, puuid)
                    if not stats:
                        print(f"  └─ ⏭️  Stats non extraites (ancienne saison ou erreur)")
                        found_old_season = True
                        break
                except Exception as e:
                    print(f"  └─ ❌ Erreur extract_player_stats: {e}")
                    continue
                
                try:
                    await bot.db.save_match_stats(match_id, puuid, stats)
                    new_matches += 1
                    print(f"  └─ ✅ SAUVEGARDÉ - {stats['champion']} ({new_matches} total)")
                except Exception as e:
                    print(f"  └─ ❌ Erreur save_match_stats: {e}")
                    import traceback
                    traceback.print_exc()
                    continue
                
                if new_matches > 0 and new_matches % 10 == 0 and progress_callback:
                    try:
                        await progress_callback(
                            f"🔍 Analyse en cours...\n"
                            f"📊 {total_checked} matchs vérifiés\n"
                            f"✅ {new_matches} nouveaux matchs enregistrés"
                        )
                    except:
                        pass
            
            if found_old_season:
                print(f"\n🛑 Arrêt: match d'ancienne saison trouvé")
                break
            
            if len(match_ids) < batch_size:
                print(f"\n✅ Fin de l'historique (batch incomplet: {len(match_ids)}/{batch_size})")
                break
            
            start_index += batch_size
            await asyncio.sleep(2)
        
        print(f"\n{'='*70}")
        print(f"✅ SYNC TERMINÉ: {riot_id}")
        print(f"📊 Total vérifié: {total_checked} matchs")
        print(f"✅ Nouveaux matchs: {new_matches}")
        print(f"{'='*70}\n")
        
        # === VÉRIFICATION DES MILESTONES APRÈS LA SYNCHRO ===
        if new_matches > 0 and bot.db and bot.db.pool:
            print(f"\n🏆 Vérification des milestones pour {riot_id}...")
            
            # Récupérer le discord_id depuis le puuid
            linked_accounts = await bot.db.get_all_linked_accounts()
            discord_id = None
            for did, accounts_list in linked_accounts.items():
                for account_info in accounts_list:
                    if account_info['puuid'] == puuid:
                        discord_id = did
                        break
                if discord_id:
                    break
            
            if not discord_id:
                print(f"⚠️ Discord ID introuvable pour {riot_id}")
                return new_matches
            
            # Récupérer le membre Discord
            member = None
            for guild in bot.guilds:
                member = guild.get_member(int(discord_id))
                if member:
                    break
            
            if not member:
                print(f"⚠️ Membre Discord introuvable pour {riot_id}")
                return new_matches
            
            try:
                from config import get_milestone_message
                
                # Récupérer les stats complètes du joueur
                all_player_stats = await bot.db.get_player_stats_summary(puuid)
                
                if all_player_stats:
                    milestones_to_check = []
                    
                    # 1. Total deaths
                    milestones_to_check.append({
                        'type': 'deaths',
                        'value': all_player_stats['total_deaths'],
                        'extra_data': None
                    })
                    
                    # 2. Total kills
                    milestones_to_check.append({
                        'type': 'kills',
                        'value': all_player_stats['total_kills'],
                        'extra_data': None
                    })
                    
                    # 3. Total games
                    milestones_to_check.append({
                        'type': 'games',
                        'value': all_player_stats['total_games'],
                        'extra_data': None
                    })
                    
                    # 4. Total wins
                    milestones_to_check.append({
                        'type': 'wins',
                        'value': all_player_stats['wins'],
                        'extra_data': None
                    })
                    
                    # 5. Total losses
                    milestones_to_check.append({
                        'type': 'losses',
                        'value': all_player_stats['losses'],
                        'extra_data': None
                    })
                    
                    # 6. Win/Lose streaks
                    streak_type, streak_count = await bot.db.get_current_streak(puuid)
                    if streak_type and streak_count >= 5:
                        streak_milestone_type = 'win_streak' if streak_type == 'win' else 'lose_streak'
                        milestones_to_check.append({
                            'type': streak_milestone_type,
                            'value': streak_count,
                            'extra_data': None
                        })
                    
                    # 7. Champion-specific games
                    champion_stats = await bot.db.get_champion_stats(puuid)
                    for champion, game_count in champion_stats.items():
                        if game_count >= 25:
                            milestones_to_check.append({
                                'type': 'champion_games',
                                'value': game_count,
                                'extra_data': champion
                            })
                    
                    # Vérifier et envoyer tous les milestones
                    milestones_sent = 0
                    for milestone_data in milestones_to_check:
                        extra = milestone_data.get('extra_data')
                        reached = await bot.db.check_and_save_milestone(
                            puuid,
                            milestone_data['type'],
                            milestone_data['value'],
                            extra
                        )
                        
                        if reached:
                            try:
                                player_name = member.display_name
                                custom_message = get_milestone_message(
                                    milestone_data['type'],
                                    reached,
                                    player_name,
                                    extra
                                )
                                
                                if custom_message:
                                    # Créer un titre dynamique selon le type
                                    milestone_titles = {
                                        'deaths': f"💀 {reached} Morts !",
                                        'kills': f"⚔️ {reached} Kills !",
                                        'games': f"🎮 {reached} Games !",
                                        'wins': f"🏆 {reached} Victoires !",
                                        'losses': f"💔 {reached} Défaites",
                                        'win_streak': f"🔥 Série de {reached} Victoires !",
                                        'lose_streak': f"😰 Série de {reached} Défaites",
                                        'champion_games': f"🎭 {reached} Games sur {extra} !"
                                    }
                                    
                                    title = milestone_titles.get(
                                        milestone_data['type'], 
                                        f"🏆 Nouveau Milestone : {reached}"
                                    )
                                    
                                    embed = discord.Embed(
                                        title=title,
                                        description=custom_message,
                                        color=discord.Color.green()
                                    )
                                    embed.timestamp = discord.utils.utcnow()
                                    
                                    await member.send(embed=embed)
                                    milestones_sent += 1
                                    print(f"  └─ 📨 Milestone envoyé: {milestone_data['type']} = {reached}")
                            except discord.Forbidden:
                                print(f"  └─ ❌ Impossible d'envoyer DM à {member.display_name}")
                            except Exception as e:
                                print(f"  └─ ❌ Erreur envoi milestone: {e}")
                    
                    if milestones_sent > 0:
                        print(f"✅ {milestones_sent} milestone(s) envoyé(s)")
                    else:
                        print(f"ℹ️ Aucun nouveau milestone")
                        
            except Exception as e:
                print(f"❌ Erreur vérification milestones: {e}")
                import traceback
                traceback.print_exc()
        
        return new_matches
        
    except Exception as e:
        print(f"\n{'='*70}")
        print(f"❌ SYNC ÉCHOUÉ: {riot_id}")
        print(f"❌ ERREUR GLOBALE: {e}")
        print(f"{'='*70}\n")
        import traceback
        traceback.print_exc()
        return 0
    finally:
        bot.syncing_players.discard(puuid)

# === REMINDER DM ===
async def send_link_reminder(user: discord.Member):
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

# === EVENTS ===
@bot.event
async def on_ready():
    print(f"{bot.user} est connecté !")
    print(f"✅ Database pool: {bot.db.pool is not None}")
    
    try:
        synced = await bot.tree.sync()
        print(f"Synchronisé {len(synced)} commandes")
    except Exception as e:
        print(f"Erreur sync commandes: {e}")
    
    # Attendre 3 secondes pour s'assurer que tout est bien initialisé
    print("⏳ Attente de 3 secondes pour stabilisation...")
    await asyncio.sleep(3)
    
    # Vérifier le pool DB avant de démarrer les tasks
    if bot.db and bot.db.pool:
        print("✅ Démarrage des tâches automatiques...")
        if not check_rank_changes.is_running():
            check_rank_changes.start()
        
        if not sync_match_history.is_running():
            sync_match_history.start()
        
        print("✅ Toutes les tâches sont démarrées")
    else:
        print("⚠️ Pool DB non disponible, tasks non démarrés")

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

# === TASKS 30 MINUTES ===
@tasks.loop(minutes=30)
async def check_rank_changes():
    """Vérifie les changements de rang toutes les 30 minutes"""
    if not bot.db or not bot.db.pool:
        print("⚠️ Pool DB non disponible pour check_rank_changes")
        return

    linked_accounts = await bot.db.get_all_linked_accounts()

    # NOUVELLE STRUCTURE: linked_accounts est maintenant {discord_id: [list of accounts]}
    for discord_id, accounts_list in linked_accounts.items():
        for account_info in accounts_list:  # Boucle sur chaque compte
            try:
                puuid = account_info['puuid']
                riot_id = account_info['riot_id']
                tagline = account_info['tagline']
                
                stats = await get_ranked_stats(puuid)
                if not stats:
                    continue

                tier = stats['tier']
                rank = stats['rank']
                lp = stats['leaguePoints']
                
                # Clé unique pour rank_history basée sur discord_id + puuid
                # ATTENTION: Il faut modifier la table rank_history pour inclure le puuid
                # OU créer une clé composite discord_id + account_index
                
                last_rank = await bot.db.get_last_rank(discord_id, puuid)  # MODIFIÉ
                if not last_rank:
                    await bot.db.save_rank(discord_id, tier, rank, lp, puuid)  # MODIFIÉ
                    continue

                old_tier = last_rank['tier']
                old_rank = last_rank['rank']
                old_lp = last_rank['lp']
                tier_changed = old_tier != tier

                if tier_changed:
                    await bot.db.save_rank(discord_id, tier, rank, lp, puuid)  # MODIFIÉ
                    
                    for guild in bot.guilds:
                        member = guild.get_member(int(discord_id))
                        if not member:
                            continue

                        announcement_channel = None
                        for channel in guild.text_channels:
                            if channel.name.lower() in ['général', 'general', 'annonces', 'announcements', 'lobby', 'tchat']:
                                announcement_channel = channel
                                break
                        if not announcement_channel:
                            announcement_channel = guild.text_channels[0] if guild.text_channels else None

                        if announcement_channel:
                            emoji = RANK_EMOJIS.get(tier, "❓")
                            old_emoji = RANK_EMOJIS.get(old_tier, "❓")
                            if tier in ['MASTER', 'GRANDMASTER', 'CHALLENGER']:
                                rank_str = f"{emoji} **{tier.title()}** - {lp} LP"
                            else:
                                rank_str = f"{emoji} **{tier.title()} {rank}** - {lp} LP"
                            if old_tier in ['MASTER', 'GRANDMASTER', 'CHALLENGER']:
                                old_rank_str = f"{old_emoji} {old_tier.title()}"
                            else:
                                old_rank_str = f"{old_emoji} {old_tier.title()} {old_rank}"

                            tier_values = {
                                "IRON": 0, "BRONZE": 1, "SILVER": 2, "GOLD": 3,
                                "PLATINUM": 4, "EMERALD": 5, "DIAMOND": 6,
                                "MASTER": 7, "GRANDMASTER": 8, "CHALLENGER": 9
                            }
                            is_promotion = tier_values.get(tier, 0) > tier_values.get(old_tier, 0)

                            # MODIFIÉ: Afficher le compte concerné
                            player_name = member.mention if member else f"**{riot_id}#{tagline}**"
                            account_display = f"{riot_id}#{tagline}"
                            
                            embed = discord.Embed(
                                title="🎊 CHANGEMENT DE RANG !" if is_promotion else "📉 Changement de rang",
                                color=discord.Color.gold() if is_promotion else discord.Color.orange(),
                                description=f"{player_name} a changé de pallier !\n*Compte: {account_display}*"
                            )
                            embed.add_field(name="Nouveau rang", value=rank_str, inline=True)
                            embed.set_footer(text="Félicitations ! 🎉" if is_promotion else "Ne lâche rien, tu vas remonter ! 💪")

                            try:
                                await announcement_channel.send(embed=embed)
                            except discord.Forbidden:
                                print(f"Pas la permission d'envoyer dans {announcement_channel.name}")

            except Exception as e:
                print(f"Erreur check_rank_changes pour {account_info.get('riot_id', 'unknown')}: {e}")

@tasks.loop(minutes=30)
async def sync_match_history():
    """Synchronise l'historique des 5 derniers matchs toutes les 30 minutes et envoie les milestones"""
    if not bot.db or not bot.db.pool:
        print("⚠️ Pool DB non disponible pour sync_match_history")
        return
    
    print("🔄 Synchronisation rapide des matchs en cours...")
    linked_accounts = await bot.db.get_all_linked_accounts()
    total_new_matches = 0
    
    from config import get_milestone_message
    
    # MODIFIÉ: Nouvelle structure
    for discord_id, accounts_list in linked_accounts.items():
        for account_info in accounts_list:
            try:
                puuid = account_info['puuid']
                if puuid in bot.syncing_players:
                    continue
                
                match_ids = await get_match_list(puuid, start=0, count=5)
                if not match_ids:
                    continue
                
                # Récupérer le membre Discord pour le DM
                member = None
                for guild in bot.guilds:
                    member = guild.get_member(int(discord_id))
                    if member:
                        break
                
                for match_id in match_ids:
                    if await bot.db.match_exists(match_id, puuid):
                        continue
                    
                    await asyncio.sleep(0.5)
                    match_data = await get_match_details(match_id)
                    if not match_data:
                        continue
                    
                    stats = extract_player_stats(match_data, puuid)
                    if stats:
                        await bot.db.save_match_stats(match_id, puuid, stats)
                        total_new_matches += 1
                        
                        # === CHECK MILESTONES (reste identique) ===
                        if member:
                            all_player_stats = await bot.db.get_player_stats_summary(puuid)
                            
                            if all_player_stats:
                                milestones_to_check = []
                                
                                milestones_to_check.append({'type': 'deaths', 'value': all_player_stats['total_deaths']})
                                milestones_to_check.append({'type': 'kills', 'value': all_player_stats['total_kills']})
                                milestones_to_check.append({'type': 'games', 'value': all_player_stats['total_games']})
                                milestones_to_check.append({'type': 'wins', 'value': all_player_stats['wins']})
                                milestones_to_check.append({'type': 'losses', 'value': all_player_stats['losses']})
                                
                                streak_type, streak_count = await bot.db.get_current_streak(puuid)
                                if streak_type and streak_count >= 5:
                                    streak_milestone_type = 'win_streak' if streak_type == 'win' else 'lose_streak'
                                    milestones_to_check.append({'type': streak_milestone_type, 'value': streak_count})
                                
                                champion_stats = await bot.db.get_champion_stats(puuid)
                                for champion, game_count in champion_stats.items():
                                    if game_count >= 25:
                                        milestones_to_check.append({
                                            'type': 'champion_games',
                                            'value': game_count,
                                            'extra_data': champion
                                        })
                                
                                best_milestone = None
                                best_value = 0
                                
                                for milestone_data in milestones_to_check:
                                    extra = milestone_data.get('extra_data')
                                    reached = await bot.db.check_and_save_milestone(
                                        puuid,
                                        milestone_data['type'],
                                        milestone_data['value'],
                                        extra
                                    )
                                    
                                    if reached and reached > best_value:
                                        best_value = reached
                                        best_milestone = {
                                            'type': milestone_data['type'],
                                            'value': reached,
                                            'extra': extra
                                        }
                                
                                if best_milestone:
                                    try:
                                        player_name = member.display_name
                                        custom_message = get_milestone_message(
                                            best_milestone['type'],
                                            best_milestone['value'],
                                            player_name,
                                            best_milestone.get('extra')
                                        )
                                        
                                        if custom_message:
                                            # Créer un titre dynamique selon le type
                                            milestone_titles = {
                                                'deaths': f"💀 {best_milestone['value']} Morts !",
                                                'kills': f"⚔️ {best_milestone['value']} Kills !",
                                                'games': f"🎮 {best_milestone['value']} Games !",
                                                'wins': f"🏆 {best_milestone['value']} Victoires !",
                                                'losses': f"💔 {best_milestone['value']} Défaites",
                                                'win_streak': f"🔥 Série de {best_milestone['value']} Victoires !",
                                                'lose_streak': f"😰 Série de {best_milestone['value']} Défaites",
                                                'champion_games': f"🎭 {best_milestone['value']} Games sur {best_milestone.get('extra')} !"
                                            }
                                            
                                            title = milestone_titles.get(
                                                best_milestone['type'], 
                                                f"🏆 Nouveau Milestone : {best_milestone['value']}"
                                            )
                                            
                                            embed = discord.Embed(
                                                title=title,
                                                description=custom_message,
                                                color=discord.Color.green()
                                            )
                                            embed.timestamp = discord.utils.utcnow()
                                            
                                            await member.send(embed=embed)
                                    except discord.Forbidden:
                                        print(f"Impossible de DM {member.display_name}")
                                    except Exception as e:
                                        print(f"Erreur en DM milestone pour {member.display_name}: {e}")
                
                await asyncio.sleep(1)
            except Exception as e:
                print(f"Erreur sync_match_history pour {account_info.get('riot_id', 'unknown')}: {e}")
    
    if total_new_matches > 0:
        print(f"✅ {total_new_matches} nouveaux matchs enregistrés")
    else:
        print("✅ Aucun nouveau match")

# === RUN BOT ===
if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
