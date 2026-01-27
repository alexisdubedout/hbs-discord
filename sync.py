import asyncio
from riot_api import get_match_list, get_match_details, extract_player_stats

async def sync_player_full_history(bot, puuid: str, riot_id: str, progress_callback=None):
    """
    Récupère l'historique complet des matchs d'un joueur pour la saison en cours
    """
    # ATTENDRE que la DB soit prête (retry 5 fois avec 2 sec entre chaque)
    print(f"🔍 sync_player_full_history pour {riot_id}")
    print(f"   └─ bot.db existe: {bot.db is not None}")
    if bot.db:
        print(f"   └─ bot.db.pool existe: {bot.db.pool is not None}")
    
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
                import discord
                
                # Récupérer les stats complètes du joueur
                all_player_stats = await bot.db.get_player_stats_summary(puuid)
                
                if all_player_stats:
                    milestones_to_check = []
                    
                    milestones_to_check.append({
                        'type': 'deaths',
                        'value': all_player_stats['total_deaths'],
                        'extra_data': None
                    })
                    
                    milestones_to_check.append({
                        'type': 'kills',
                        'value': all_player_stats['total_kills'],
                        'extra_data': None
                    })
                    
                    milestones_to_check.append({
                        'type': 'games',
                        'value': all_player_stats['total_games'],
                        'extra_data': None
                    })
                    
                    milestones_to_check.append({
                        'type': 'wins',
                        'value': all_player_stats['wins'],
                        'extra_data': None
                    })
                    
                    milestones_to_check.append({
                        'type': 'losses',
                        'value': all_player_stats['losses'],
                        'extra_data': None
                    })
                    
                    streak_type, streak_count = await bot.db.get_current_streak(puuid)
                    if streak_type and streak_count >= 5:
                        streak_milestone_type = 'win_streak' if streak_type == 'win' else 'lose_streak'
                        milestones_to_check.append({
                            'type': streak_milestone_type,
                            'value': streak_count,
                            'extra_data': None
                        })
                    
                    champion_stats = await bot.db.get_champion_stats(puuid)
                    for champion, game_count in champion_stats.items():
                        if game_count >= 25:
                            milestones_to_check.append({
                                'type': 'champion_games',
                                'value': game_count,
                                'extra_data': champion
                            })
                    
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
