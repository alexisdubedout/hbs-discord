# Bot Discord League of Legends

Bot Discord moderne pour gérer un serveur privé LoL avec classement et teams aléatoires.

## 🎮 Fonctionnalités

- **`/link`** - Lie ton compte Riot à Discord
- **`/admin_link`** - [ADMIN] Lie un compte pour quelqu'un d'autre
- **`/leaderboard`** - Affiche le classement SoloQ du serveur
- **`/random_teams`** - Génère 2 équipes aléatoires avec rôles et champions depuis le vocal

## 📋 Prérequis

### 1. Créer une application Discord

1. Va sur [Discord Developer Portal](https://discord.com/developers/applications)
2. Clique sur "New Application"
3. Donne un nom à ton bot
4. Va dans l'onglet "Bot"
5. Clique sur "Reset Token" et copie ton token (garde-le secret !)
6. Active les **Privileged Gateway Intents** :
   - Presence Intent
   - Server Members Intent
   - Message Content Intent

### 2. Inviter le bot sur ton serveur

1. Dans le Developer Portal, va dans "OAuth2" > "URL Generator"
2. Sélectionne les scopes :
   - `bot`
   - `applications.commands`
3. Sélectionne les permissions :
   - Read Messages/View Channels
   - Send Messages
   - Embed Links
   - Read Message History
   - Use Slash Commands
   - Connect (pour voir les vocaux)
4. Copie l'URL générée et ouvre-la dans ton navigateur
5. Sélectionne ton serveur et autorise le bot

### 3. Obtenir une clé API Riot

1. Va sur [Riot Developer Portal](https://developer.riotgames.com/)
2. Connecte-toi avec ton compte Riot
3. Copie ta clé API (elle est valable 24h en mode développement)
4. Pour un bot permanent, demande une clé "Production" (gratuit)

## 🚀 Déploiement sur Railway

### Étape 1 : Préparer les fichiers

1. Crée un compte GitHub si tu n'en as pas
2. Crée un nouveau repository (peut être privé)
3. Upload ces fichiers :
   - `bot.py`
   - `requirements.txt`
   - `README.md`

### Étape 2 : Configurer Railway

1. Va sur [Railway.app](https://railway.app/)
2. Connecte-toi avec GitHub
3. Clique sur "New Project"
4. Sélectionne "Deploy from GitHub repo"
5. Choisis ton repository

### Étape 3 : Variables d'environnement

Dans Railway, va dans ton projet > Variables :

```
DISCORD_TOKEN=ton_token_discord_ici
RIOT_API_KEY=ta_cle_api_riot_ici
```

⚠️ **Ne mets JAMAIS ces tokens directement dans le code !**

### Étape 4 : Lancement

Railway va automatiquement :
1. Détecter que c'est un projet Python
2. Installer les dépendances depuis `requirements.txt`
3. Lancer `bot.py`

Le bot devrait être en ligne en quelques minutes !

## 🏠 Alternative : Hébergement local

Si tu veux l'héberger sur ton PC :

### 1. Installer Python

Télécharge Python 3.10+ depuis [python.org](https://www.python.org/downloads/)

### 2. Installer les dépendances

```bash
pip install -r requirements.txt
```

### 3. Créer un fichier `.env` (optionnel)

Crée un fichier `.env` à la racine :

```
DISCORD_TOKEN=ton_token_discord
RIOT_API_KEY=ta_cle_api_riot
```

Ou modifie directement les variables en haut de `bot.py`.

### 4. Lancer le bot

```bash
python bot.py
```

Le bot restera en ligne tant que le terminal est ouvert.

## 📝 Utilisation

### Pour les joueurs

1. Utilise `/link Pseudo TAG` pour lier ton compte
   - Exemple : `/link Faker KR1`

2. Utilise `/leaderboard` pour voir le classement

3. Rejoins un vocal et utilise `/random_teams` pour générer des équipes

### Pour les admins

- Utilise `/admin_link @joueur Pseudo TAG` pour lier quelqu'un
- Seuls les membres avec permission "Administrateur" peuvent utiliser cette commande

## 🔧 Personnalisation

### Changer la région

Dans `bot.py`, ligne 10-11 :

```python
REGION = 'euw1'  # euw1, na1, kr, etc.
PLATFORM = 'europe'  # europe, americas, asia
```

### Ajouter des champions

La liste est déjà à jour (patch 14.24), mais tu peux modifier `CHAMPIONS` dans le code.

## ❓ Problèmes courants

**Le bot ne répond pas aux commandes**
- Attends 5 minutes après le lancement (sync des commandes)
- Vérifie que les Intents sont activés
- Regarde les logs Railway pour les erreurs

**"Compte Riot introuvable"**
- Vérifie que le Riot ID et le tagline sont corrects
- Format : `/link PseudoRiot TAG` (sans le #)

**Clé API Riot expirée**
- Les clés dev expirent après 24h
- Demande une clé Production sur le Developer Portal

**Le classement ne s'affiche pas**
- Le joueur doit avoir fait au moins 1 game ranked cette saison
- Seule la SoloQ est affichée (pas flex)

## 📊 Limites

- Railway gratuit : ~5$/mois de crédit (largement suffisant)
- API Riot : 20 requêtes/seconde (sauf si clé Production)
- Le bot stocke les comptes liés en local (fichier JSON)

## 🎉 C'est tout !

Le bot est prêt à l'emploi. Bonne chance sur la faille !

---

**Support** : En cas de problème, vérifie les logs Railway ou le terminal.
