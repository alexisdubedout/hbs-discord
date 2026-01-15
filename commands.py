import discord
from discord import app_commands
import random
from config import CHAMPIONS, ROLES, RANK_EMOJIS, get_rank_value
from riot_api import get_summoner_by_riot_id, get_summoner_data, get_ranked_stats

def register_commands(bot):
    """Enregistre toutes les commandes slash"""
    
    @bot.tree.command(name="say", description="[ADMIN] Fait parler le bot")
    @app_commands.describe(
        channel="Le channel où envoyer le message",
        message="Le message à envoyer"
    )
    async def say(interaction: discord.Interaction, channel: discord.TextChannel, message: str):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Tu n'as pas la permission d'utiliser cette commande.", ephemeral=True)
            return
        
        await interaction.response.send_message(f"✅ Message envoyé dans {channel.mention}", ephemeral=True)
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
        success = await bot.db.save_linked_account(user_id, riot_id, tagline, account['puuid'])
        
        if success:
            # Envoyer le message de confirmation
            await interaction.followup.send(
                f"✅ Compte lié avec succès: **{riot_id}#{tagline}**\n"
                f"⏳ Récupération de l'historique en cours... Cela peut prendre quelques minutes."
            )
            
            # Lancer la sync complète en arrière-plan
            from bot import sync_player_full_history
            import asyncio
            
            async def sync_with_updates():
                async def progress(msg):
                    try:
                        await interaction.edit_original_response(
                            content=f"✅ Compte lié: **{riot_id}#{tagline}**\n{msg}"
                        )
                    except:
                        pass
                
                new_matches = await sync_player_full_history(
                    account['puuid'], 
                    f"{riot_id}#{tagline}",
                    progress
                )
                
                try:
                    await interaction.edit_original_response(
                        content=f"✅ Compte lié: **{riot_id}#{tagline}**\n"
                                f"🎉 **{new_matches} matchs** de la saison en cours récupérés !"
                    )
                except:
                    pass
            
            # Lancer la tâche en background
            asyncio.create_task(sync_with_updates())
        else:
            await interaction.followup.send("❌ Erreur lors de la sauvegarde.")
    
    @bot.tree.command(name="admin_link", description="[ADMIN] Lie un compte Riot pour un autre utilisateur")
    @app_commands.describe(
        user="L'utilisateur Discord",
        riot_id="Son Riot ID",
        tagline="Son tagline"
    )
    async def admin_link(interaction: discord.Interaction, user: discord.Member, riot_id: str, tagline: str):
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
        success = await bot.db.save_linked_account(user_id, riot_id, tagline, account['puuid'])
        
        if success:
            await interaction.followup.send(f"✅ Compte lié pour {user.mention}: **{riot_id}#{tagline}**")
        else:
            await interaction.followup.send("❌ Erreur lors de la sauvegarde.")
    
        @bot.tree.command(name="sync_all_history", description="[ADMIN] Récupère l'historique complet de tous les joueurs liés")
        async def sync_all_history(interaction: discord.Interaction):
            if not interaction.user.guild_permissions.administrator:
                await interaction.response.send_message("❌ Tu n'as pas la permission d'utiliser cette commande.", ephemeral=True)
                return
            
            # VÉRIFICATION CRITIQUE DE LA DB
            if not bot.db or not bot.db.pool:
                await interaction.response.send_message(
                    "❌ La base de données n'est pas initialisée. Attends quelques secondes que le bot soit complètement démarré, puis réessaye.",
                    ephemeral=True
                )
                return
            
            await interaction.response.defer()
            
            linked_accounts = await bot.db.get_all_linked_accounts()
            
            if not linked_accounts:
                await interaction.followup.send("❌ Aucun compte lié.")
                return
            
            await interaction.followup.send(
                f"🔄 Début de la synchronisation complète pour {len(linked_accounts)} joueur(s)...\n"
                f"⏳ Cela peut prendre plusieurs minutes. Je te tiens au courant !"
            )
            
            from bot import sync_player_full_history
            import asyncio
            
            total_new_matches = 0
            completed = 0
            
            for discord_id, account_info in linked_accounts.items():
                try:
                    puuid = account_info['puuid']
                    riot_id = account_info['riot_id']
                    tagline = account_info['tagline']
                    
                    # Vérifier combien de matchs sont déjà en DB
                    existing_count = await bot.db.get_match_count(puuid)
                    
                    await interaction.edit_original_response(
                        content=f"🔄 Synchronisation: {completed}/{len(linked_accounts)}\n"
                                f"📥 En cours: **{riot_id}#{tagline}** ({existing_count} matchs déjà en DB)..."
                    )
                    
                    # Sync complète
                    new_matches = await sync_player_full_history(puuid, f"{riot_id}#{tagline}")
                    total_new_matches += new_matches
                    completed += 1
                    
                    await interaction.edit_original_response(
                        content=f"🔄 Synchronisation: {completed}/{len(linked_accounts)}\n"
                                f"✅ **{riot_id}#{tagline}**: +{new_matches} nouveaux matchs\n"
                                f"📊 Total: {total_new_matches} nouveaux matchs"
                    )
                    
                    # Petit délai entre chaque joueur
                    await asyncio.sleep(2)
                    
                except Exception as e:
                    print(f"Erreur sync pour {discord_id}: {e}")
                    continue
            
            await interaction.edit_original_response(
                content=f"✅ **Synchronisation terminée !**\n\n"
                        f"👥 Joueurs traités: {completed}/{len(linked_accounts)}\n"
                        f"🎮 Nouveaux matchs: **{total_new_matches}**\n"
                        f"🎉 Toutes les stats sont maintenant à jour !"
            )
    
    @bot.tree.command(name="leaderboard", description="Affiche le classement du serveur")
    @app_commands.describe(
        critere="Critère de classement"
    )
    @app_commands.choices(critere=[
        app_commands.Choice(name="🏆 Rang SoloQ", value="rank"),
        app_commands.Choice(name="⚔️ Total Kills", value="kills"),
        app_commands.Choice(name="💀 Total Deaths", value="deaths"),
        app_commands.Choice(name="🤝 Total Assists", value="assists"),
        app_commands.Choice(name="📊 KDA Moyen", value="kda"),
        app_commands.Choice(name="📈 Winrate (%)", value="winrate"),
        app_commands.Choice(name="🎮 Nombre de Games", value="games"),
        app_commands.Choice(name="🌾 CS/min Moyen", value="cs"),
        app_commands.Choice(name="👁️ Vision Score Moyen", value="vision")
    ])
    async def leaderboard(interaction: discord.Interaction, critere: str = "rank"):
        await interaction.response.defer()
        
        linked_accounts = await bot.db.get_all_linked_accounts()
        
        if not linked_accounts:
            await interaction.followup.send("❌ Aucun compte lié pour le moment.")
            return
        
        players_data = []
        
        for discord_id, account_info in linked_accounts.items():
            try:
                member = interaction.guild.get_member(int(discord_id))
                if not member:
                    continue
                
                # Récupérer les stats ranked (toujours utiles pour l'affichage)
                ranked_stats = await get_ranked_stats(account_info['puuid'])
                
                # Récupérer les stats de matchs depuis la DB
                match_stats = await bot.db.get_player_stats_summary(account_info['puuid'])
                
                player_info = {
                    'name': f"{account_info['riot_id']}#{account_info['tagline']}",
                    'discord_name': member.display_name,
                    'puuid': account_info['puuid']
                }
                
                # Stats ranked
                if ranked_stats:
                    tier = ranked_stats['tier']
                    rank = ranked_stats['rank']
                    lp = ranked_stats['leaguePoints']
                    wins = ranked_stats['wins']
                    losses = ranked_stats['losses']
                    total = wins + losses
                    winrate_ranked = round((wins / total) * 100, 1) if total > 0 else 0
                    
                    player_info.update({
                        'tier': tier,
                        'rank': rank,
                        'lp': lp,
                        'ranked_wins': wins,
                        'ranked_losses': losses,
                        'ranked_winrate': winrate_ranked,
                        'rank_value': get_rank_value(tier, rank, lp)
                    })
                else:
                    player_info.update({
                        'tier': 'UNRANKED',
                        'rank': '',
                        'lp': 0,
                        'ranked_wins': 0,
                        'ranked_losses': 0,
                        'ranked_winrate': 0,
                        'rank_value': -1
                    })
                
                # Stats de matchs (pour les autres critères)
                if match_stats and match_stats['total_games'] > 0:
                    player_info.update({
                        'total_games': match_stats['total_games'],
                        'wins': match_stats['wins'],
                        'losses': match_stats['losses'],
                        'winrate': match_stats['winrate'],
                        'total_kills': match_stats['total_kills'],
                        'total_deaths': match_stats['total_deaths'],
                        'total_assists': match_stats['total_assists'],
                        'kda': match_stats['kda'],
                        'cs_per_min': match_stats.get('cs_per_min', 0),
                        'avg_vision_score': match_stats.get('avg_vision_score', 0)
                    })
                else:
                    player_info.update({
                        'total_games': 0,
                        'wins': 0,
                        'losses': 0,
                        'winrate': 0,
                        'total_kills': 0,
                        'total_deaths': 0,
                        'total_assists': 0,
                        'kda': 0.0,
                        'cs_per_min': 0,
                        'avg_vision_score': 0
                    })
                
                players_data.append(player_info)
                
            except Exception as e:
                print(f"Erreur pour {discord_id}: {e}")
                continue
        
        if not players_data:
            await interaction.followup.send("❌ Aucune donnée disponible.")
            return
        
        # === TRI SELON LE CRITÈRE ===
        critere_names = {
            'rank': '🏆 Rang SoloQ',
            'kills': '⚔️ Total Kills',
            'deaths': '💀 Total Deaths',
            'assists': '🤝 Total Assists',
            'kda': '📊 KDA Moyen',
            'winrate': '📈 Winrate',
            'games': '🎮 Nombre de Games',
            'cs': '🌾 CS/min Moyen',
            'vision': '👁️ Vision Score Moyen'
        }
        
        # Filtrer les joueurs qui ont des données pour le critère (sauf rank)
        if critere != 'rank':
            players_data = [p for p in players_data if p['total_games'] > 0]
            
            if not players_data:
                await interaction.followup.send(f"❌ Aucune donnée de match disponible pour ce critère.")
                return
        
        # Trier selon le critère
        if critere == 'rank':
            players_data.sort(key=lambda x: x['rank_value'], reverse=True)
        elif critere == 'kills':
            players_data.sort(key=lambda x: x['total_kills'], reverse=True)
        elif critere == 'deaths':
            players_data.sort(key=lambda x: x['total_deaths'], reverse=True)
        elif critere == 'assists':
            players_data.sort(key=lambda x: x['total_assists'], reverse=True)
        elif critere == 'kda':
            players_data.sort(key=lambda x: x['kda'], reverse=True)
        elif critere == 'winrate':
            # Minimum 10 games pour être dans le classement winrate
            players_data = [p for p in players_data if p['total_games'] >= 10]
            if not players_data:
                await interaction.followup.send(f"❌ Aucun joueur n'a assez de games (minimum 10) pour ce classement.")
                return
            players_data.sort(key=lambda x: x['winrate'], reverse=True)
        elif critere == 'games':
            players_data.sort(key=lambda x: x['total_games'], reverse=True)
        elif critere == 'cs':
            # Filtrer les joueurs qui ont des stats de CS (pas ARAM only)
            players_data = [p for p in players_data if p['cs_per_min'] > 0]
            if not players_data:
                await interaction.followup.send(f"❌ Aucune donnée de CS disponible (critère non applicable en ARAM).")
                return
            players_data.sort(key=lambda x: x['cs_per_min'], reverse=True)
        elif critere == 'vision':
            # Filtrer les joueurs qui ont des stats de vision (pas ARAM only)
            players_data = [p for p in players_data if p['avg_vision_score'] > 0]
            if not players_data:
                await interaction.followup.send(f"❌ Aucune donnée de vision disponible (critère non applicable en ARAM).")
                return
            players_data.sort(key=lambda x: x['avg_vision_score'], reverse=True)
        
        # === CRÉATION DE L'EMBED ===
        embed = discord.Embed(
            title=f"🏆 Classement du Serveur",
            color=discord.Color.gold(),
            description=f"**Critère:** {critere_names[critere]}"
        )
        
        # Limiter à 10 joueurs pour éviter un embed trop long
        top_players = players_data[:10]
        
        for i, player in enumerate(top_players, 1):
            # Médailles pour le top 3
            medal = ""
            if i == 1:
                medal = "🥇 "
            elif i == 2:
                medal = "🥈 "
            elif i == 3:
                medal = "🥉 "
            
            # Construire la valeur selon le critère
            if critere == 'rank':
                emoji = RANK_EMOJIS.get(player['tier'], "❓")
                
                if player['tier'] == 'UNRANKED':
                    main_value = f"{emoji} **Unranked**"
                    sub_value = "`Aucune game ranked`"
                elif player['tier'] in ['MASTER', 'GRANDMASTER', 'CHALLENGER']:
                    main_value = f"{emoji} **{player['tier'].title()}** - {player['lp']} LP"
                    sub_value = f"`{player['ranked_wins']}W {player['ranked_losses']}L - {player['ranked_winrate']}% WR`"
                else:
                    main_value = f"{emoji} **{player['tier'].title()} {player['rank']}** - {player['lp']} LP"
                    sub_value = f"`{player['ranked_wins']}W {player['ranked_losses']}L - {player['ranked_winrate']}% WR`"
            
            elif critere == 'kills':
                main_value = f"⚔️ **{player['total_kills']} kills**"
                sub_value = f"`{player['total_games']} games • {round(player['total_kills']/player['total_games'], 1)} kills/game`"
            
            elif critere == 'deaths':
                main_value = f"💀 **{player['total_deaths']} deaths**"
                sub_value = f"`{player['total_games']} games • {round(player['total_deaths']/player['total_games'], 1)} deaths/game`"
            
            elif critere == 'assists':
                main_value = f"🤝 **{player['total_assists']} assists**"
                sub_value = f"`{player['total_games']} games • {round(player['total_assists']/player['total_games'], 1)} assists/game`"
            
            elif critere == 'kda':
                main_value = f"📊 **{player['kda']} KDA**"
                sub_value = f"`{player['total_kills']}/{player['total_deaths']}/{player['total_assists']} • {player['total_games']} games`"
            
            elif critere == 'winrate':
                main_value = f"📈 **{player['winrate']}% WR**"
                sub_value = f"`{player['wins']}W {player['losses']}L • {player['total_games']} games`"
            
            elif critere == 'games':
                main_value = f"🎮 **{player['total_games']} games**"
                sub_value = f"`{player['wins']}W {player['losses']}L • {player['winrate']}% WR`"
            
            elif critere == 'cs':
                main_value = f"🌾 **{player['cs_per_min']} CS/min**"
                sub_value = f"`{player['total_games']} games • KDA: {player['kda']}`"
            
            elif critere == 'vision':
                main_value = f"👁️ **{player['avg_vision_score']} vision/game**"
                sub_value = f"`{player['total_games']} games • KDA: {player['kda']}`"
            
            embed.add_field(
                name=f"{medal}#{i} {player['name']}",
                value=f"{main_value}\n{sub_value}",
                inline=False
            )
        
        # Footer avec info supplémentaire
        footer_text = "Mis à jour le"
        if critere == 'winrate':
            footer_text = "Minimum 10 games • " + footer_text
        elif critere in ['cs', 'vision']:
            footer_text = "Exclut ARAM uniquement • " + footer_text
        
        embed.set_footer(text=footer_text)
        embed.timestamp = discord.utils.utcnow()
        
        await interaction.followup.send(embed=embed)
        
        @bot.tree.command(name="random_teams", description="Génère 2 équipes aléatoires depuis le vocal")
        async def random_teams(interaction: discord.Interaction):
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
            
            random.shuffle(members)
            
            team_size = len(members) // 2
            team1 = members[:team_size]
            team2 = members[team_size:team_size*2]
            
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
            
            embed = discord.Embed(
                title="🎲 Teams Aléatoires",
                color=discord.Color.blue(),
                description=f"Généré depuis **{voice_channel.name}**"
            )
            
            team1_text = ""
            for member, role, champion in team1_assignments:
                team1_text += f"**{role}**: {member.mention} - *{champion}*\n"
            
            embed.add_field(name="🔵 Team Bleue", value=team1_text, inline=True)
            
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
    
    @bot.tree.command(name="stats", description="Affiche les statistiques détaillées d'un joueur")
    @app_commands.describe(
        joueur="Le joueur dont tu veux voir les stats (laisse vide pour toi-même)",
        mode="Filtre par mode de jeu"
    )
    @app_commands.choices(mode=[
        app_commands.Choice(name="Tous les modes", value="all"),
        app_commands.Choice(name="Ranked Solo/Duo", value="ranked"),
        app_commands.Choice(name="Ranked Flex", value="flex"),
        app_commands.Choice(name="Normal", value="normal"),
        app_commands.Choice(name="ARAM", value="aram")
    ])
    async def stats(interaction: discord.Interaction, joueur: discord.Member = None, mode: str = "all"):
        await interaction.response.defer()
        
        # Si aucun joueur spécifié, utiliser l'auteur de la commande
        target_user = joueur if joueur else interaction.user
        user_id = str(target_user.id)
        
        account = await bot.db.get_linked_account(user_id)
        
        if not account:
            if target_user == interaction.user:
                await interaction.followup.send("❌ Tu n'as pas lié ton compte. Utilise `/link` pour le faire !")
            else:
                await interaction.followup.send(f"❌ {target_user.mention} n'a pas lié son compte.")
            return
        
        # Map des noms de modes pour l'affichage
        mode_names = {
            'all': 'Tous les modes',
            'ranked': 'Ranked Solo/Duo',
            'flex': 'Ranked Flex',
            'normal': 'Normal',
            'aram': 'ARAM'
        }
        
        # Récupérer les stats ranked
        ranked_stats = await get_ranked_stats(account['puuid'])
        
        # Récupérer les stats de matchs avec filtre
        queue_filter = None if mode == 'all' else mode
        match_stats = await bot.db.get_player_stats_summary(account['puuid'], queue_filter)
        all_matches = await bot.db.get_player_stats(account['puuid'], queue_filter)
        
        # Créer l'embed
        mode_display = mode_names.get(mode, 'Tous les modes')
        embed = discord.Embed(
            title=f"📊 Statistiques de {target_user.display_name}",
            color=discord.Color.blue(),
            description=f"**{account['riot_id']}#{account['tagline']}**\n*{mode_display}*"
        )
        
        # Ajouter la photo de profil Discord
        embed.set_thumbnail(url=target_user.display_avatar.url)
        
        # === RANG RANKED (toujours affiché) ===
        if ranked_stats:
            tier = ranked_stats['tier']
            rank = ranked_stats['rank']
            lp = ranked_stats['leaguePoints']
            wins = ranked_stats['wins']
            losses = ranked_stats['losses']
            total = wins + losses
            wr = round((wins / total) * 100, 1) if total > 0 else 0
            
            emoji = RANK_EMOJIS.get(tier, "❓")
            
            if tier in ['MASTER', 'GRANDMASTER', 'CHALLENGER']:
                rank_text = f"{emoji} **{tier.title()}** - {lp} LP"
            else:
                rank_text = f"{emoji} **{tier.title()} {rank}** - {lp} LP"
            
            rank_text += f"\n`{wins}W {losses}L - {wr}% WR`"
            
            embed.add_field(
                name="🏆 Rang Ranked Solo/Duo",
                value=rank_text,
                inline=False
            )
        else:
            embed.add_field(
                name="🏆 Rang Ranked Solo/Duo",
                value="❓ **Unranked**\n`Aucune game ranked cette saison`",
                inline=False
            )
        
        # === STATS GÉNÉRALES (FILTRÉES) ===
        if match_stats and match_stats['total_games'] > 0:
            general_text = f"🎮 **Games jouées:** {match_stats['total_games']}\n"
            general_text += f"✅ **Victoires:** {match_stats['wins']} ({match_stats['winrate']}%)\n"
            general_text += f"❌ **Défaites:** {match_stats['losses']}\n"
            
            embed.add_field(
                name="📈 Statistiques Générales",
                value=general_text,
                inline=True
            )
            
            # === STATS DE PERFORMANCE ===
            perf_text = f"⚔️ **KDA:** {match_stats['kda']}\n"
            perf_text += f"🗡️ **Total Kills:** {match_stats['total_kills']}\n"
            perf_text += f"💀 **Total Deaths:** {match_stats['total_deaths']}\n"
            perf_text += f"🤝 **Total Assists:** {match_stats['total_assists']}\n"
            
            embed.add_field(
                name="⚔️ Performance en Combat",
                value=perf_text,
                inline=True
            )
            
            # === FARMING & VISION (sauf ARAM) ===
            if match_stats['cs_per_min'] is not None:
                farm_text = f"🌾 **CS/min:** {match_stats['cs_per_min']}\n"
                farm_text += f"👁️ **Vision/game:** {match_stats['avg_vision_score']}\n"
                
                embed.add_field(
                    name="🌾 Farm & Vision",
                    value=farm_text,
                    inline=True
                )
            
            # === CHAMPIONS LES PLUS JOUÉS ===
            if all_matches:
                # Compter les champions
                champion_counts = {}
                champion_stats = {}
                
                for match in all_matches:
                    champ = match['champion']
                    if champ not in champion_counts:
                        champion_counts[champ] = 0
                        champion_stats[champ] = {'wins': 0, 'total': 0}
                    
                    champion_counts[champ] += 1
                    champion_stats[champ]['total'] += 1
                    if match['win']:
                        champion_stats[champ]['wins'] += 1
                
                # Top 5 champions
                top_champions = sorted(champion_counts.items(), key=lambda x: x[1], reverse=True)[:5]
                
                if top_champions:
                    champ_text = ""
                    for champ, count in top_champions:
                        wr = round((champion_stats[champ]['wins'] / champion_stats[champ]['total']) * 100, 1)
                        champ_text += f"**{champ}**: {count} games ({wr}% WR)\n"
                    
                    embed.add_field(
                        name="🎭 Top Champions",
                        value=champ_text,
                        inline=False
                    )
            
            # === SÉRIES ===
            if len(all_matches) >= 5:
                # Calculer la série actuelle (5 dernières games)
                recent_5 = all_matches[:5]
                recent_wins = sum(1 for m in recent_5 if m['win'])
                recent_losses = 5 - recent_wins
                
                # Calculer la série (streak)
                streak = 0
                streak_type = None
                for match in all_matches:
                    if streak_type is None:
                        streak_type = "win" if match['win'] else "loss"
                        streak = 1
                    elif (streak_type == "win" and match['win']) or (streak_type == "loss" and not match['win']):
                        streak += 1
                    else:
                        break
                
                if streak_type == "win":
                    streak_text = f"🔥 **{streak} victoires d'affilée !**\n"
                else:
                    streak_text = f"💔 **{streak} défaites d'affilée...**\n"
                
                streak_text += f"\n📅 **5 dernières games:** {recent_wins}W - {recent_losses}L"
                
                embed.add_field(
                    name="📊 Forme Récente",
                    value=streak_text,
                    inline=False
                )
        else:
            embed.add_field(
                name="📊 Statistiques",
                value=f"Aucune donnée de match disponible pour le mode sélectionné.\nJoue quelques games et attends la prochaine synchronisation !",
                inline=False
            )
        
        embed.set_footer(text="Synchronisation toutes les 30 min • Utilise les filtres pour voir par mode")
        embed.timestamp = discord.utils.utcnow()
        
        await interaction.followup.send(embed=embed)
    
    @bot.tree.command(name="compare", description="Compare deux joueurs du serveur en détail")
    @app_commands.describe(
        joueur1="Premier joueur à comparer",
        joueur2="Deuxième joueur à comparer"
    )
    async def compare(interaction: discord.Interaction, joueur1: discord.Member, joueur2: discord.Member):
        await interaction.response.defer()
        
        account1 = await bot.db.get_linked_account(str(joueur1.id))
        account2 = await bot.db.get_linked_account(str(joueur2.id))
        
        if not account1:
            await interaction.followup.send(f"❌ {joueur1.mention} n'a pas lié son compte.")
            return
        
        if not account2:
            await interaction.followup.send(f"❌ {joueur2.mention} n'a pas lié son compte.")
            return
        
        # Récupérer les stats ranked
        ranked1 = await get_ranked_stats(account1['puuid'])
        ranked2 = await get_ranked_stats(account2['puuid'])
        
        # Récupérer les stats de matchs depuis la DB
        stats1 = await bot.db.get_player_stats_summary(account1['puuid'])
        stats2 = await bot.db.get_player_stats_summary(account2['puuid'])
        
        embed = discord.Embed(
            title="⚔️ Comparaison Détaillée",
            color=discord.Color.purple(),
            description=f"{joueur1.mention} vs {joueur2.mention}"
        )
        
        # === JOUEUR 1 ===
        player1_text = f"**{account1['riot_id']}#{account1['tagline']}**\n\n"
        
        # Rang
        if ranked1:
            tier1 = ranked1['tier']
            rank1 = ranked1['rank']
            lp1 = ranked1['leaguePoints']
            emoji1 = RANK_EMOJIS.get(tier1, "❓")
            
            if tier1 in ['MASTER', 'GRANDMASTER', 'CHALLENGER']:
                player1_text += f"{emoji1} **{tier1.title()}** - {lp1} LP\n"
            else:
                player1_text += f"{emoji1} **{tier1.title()} {rank1}** - {lp1} LP\n"
        else:
            player1_text += "❓ **Unranked**\n"
        
        player1_text += "\n📊 **Statistiques:**\n"
        
        # Stats de games
        if stats1:
            player1_text += f"🎮 Games: **{stats1['total_games']}** ({stats1['wins']}W/{stats1['losses']}L)\n"
            player1_text += f"📈 WR: **{stats1['winrate']}%**\n"
            player1_text += f"⚔️ KDA: **{stats1['kda']}**\n"
            
            # CS et Vision seulement si disponibles (pas ARAM)
            if stats1.get('cs_per_min'):
                player1_text += f"🌾 CS/min: **{stats1['cs_per_min']}**\n"
            if stats1.get('avg_vision_score'):
                player1_text += f"👁️ Vision: **{stats1['avg_vision_score']}/game**"
        else:
            player1_text += "_Aucune donnée de match disponible_"
        
        embed.add_field(
            name=f"🔵 {joueur1.display_name}",
            value=player1_text,
            inline=True
        )
        
        # === JOUEUR 2 ===
        player2_text = f"**{account2['riot_id']}#{account2['tagline']}**\n\n"
        
        # Rang
        if ranked2:
            tier2 = ranked2['tier']
            rank2 = ranked2['rank']
            lp2 = ranked2['leaguePoints']
            emoji2 = RANK_EMOJIS.get(tier2, "❓")
            
            if tier2 in ['MASTER', 'GRANDMASTER', 'CHALLENGER']:
                player2_text += f"{emoji2} **{tier2.title()}** - {lp2} LP\n"
            else:
                player2_text += f"{emoji2} **{tier2.title()} {rank2}** - {lp2} LP\n"
        else:
            player2_text += "❓ **Unranked**\n"
        
        player2_text += "\n📊 **Statistiques:**\n"
        
        # Stats de games
        if stats2:
            player2_text += f"🎮 Games: **{stats2['total_games']}** ({stats2['wins']}W/{stats2['losses']}L)\n"
            player2_text += f"📈 WR: **{stats2['winrate']}%**\n"
            player2_text += f"⚔️ KDA: **{stats2['kda']}**\n"
            
            # CS et Vision seulement si disponibles (pas ARAM)
            if stats2.get('cs_per_min'):
                player2_text += f"🌾 CS/min: **{stats2['cs_per_min']}**\n"
            if stats2.get('avg_vision_score'):
                player2_text += f"👁️ Vision: **{stats2['avg_vision_score']}/game**"
        else:
            player2_text += "_Aucune donnée de match disponible_"
        
        embed.add_field(
            name=f"🔴 {joueur2.display_name}",
            value=player2_text,
            inline=True
        )
        
        # === VERDICT ===
        verdict_lines = []
        
        # Comparer le rang
        if ranked1 and ranked2:
            rank_val1 = get_rank_value(tier1, rank1, lp1)
            rank_val2 = get_rank_value(tier2, rank2, lp2)
            
            if rank_val1 > rank_val2:
                verdict_lines.append(f"🏆 Rang: {joueur1.mention}")
            elif rank_val2 > rank_val1:
                verdict_lines.append(f"🏆 Rang: {joueur2.mention}")
            else:
                verdict_lines.append("🏆 Rang: Égalité")
        
        # Comparer les stats si disponibles
        if stats1 and stats2:
            # WR
            if stats1['winrate'] > stats2['winrate']:
                verdict_lines.append(f"📈 Meilleur WR: {joueur1.mention} ({stats1['winrate']}%)")
            elif stats2['winrate'] > stats1['winrate']:
                verdict_lines.append(f"📈 Meilleur WR: {joueur2.mention} ({stats2['winrate']}%)")
            
            # KDA
            if stats1['kda'] > stats2['kda']:
                verdict_lines.append(f"⚔️ Meilleur KDA: {joueur1.mention} ({stats1['kda']})")
            elif stats2['kda'] > stats1['kda']:
                verdict_lines.append(f"⚔️ Meilleur KDA: {joueur2.mention} ({stats2['kda']})")
            
            # CS/min (seulement si les deux ont des données)
            if stats1.get('cs_per_min') and stats2.get('cs_per_min'):
                if stats1['cs_per_min'] > stats2['cs_per_min']:
                    verdict_lines.append(f"🌾 Meilleur CS: {joueur1.mention} ({stats1['cs_per_min']}/min)")
                elif stats2['cs_per_min'] > stats1['cs_per_min']:
                    verdict_lines.append(f"🌾 Meilleur CS: {joueur2.mention} ({stats2['cs_per_min']}/min)")
            
            # Vision (seulement si les deux ont des données)
            if stats1.get('avg_vision_score') and stats2.get('avg_vision_score'):
                if stats1['avg_vision_score'] > stats2['avg_vision_score']:
                    verdict_lines.append(f"👁️ Meilleure Vision: {joueur1.mention} ({stats1['avg_vision_score']})")
                elif stats2['avg_vision_score'] > stats1['avg_vision_score']:
                    verdict_lines.append(f"👁️ Meilleure Vision: {joueur2.mention} ({stats2['avg_vision_score']})")
        
        if verdict_lines:
            embed.add_field(
                name="🎯 Verdict",
                value="\n".join(verdict_lines),
                inline=False
            )
        
        embed.set_footer(text="Stats basées sur tous les modes de jeu cette saison")
        embed.timestamp = discord.utils.utcnow()
        
        await interaction.followup.send(embed=embed)



