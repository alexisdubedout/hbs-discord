import os
import random

# Configuration API
RIOT_API_KEY = os.getenv('RIOT_API_KEY')
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
DATABASE_URL = os.getenv('DATABASE_URL')

# Régions
REGION = 'euw1'
PLATFORM = 'europe'

# Champions LoL (patch 14.24)
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
    
# Configuration des messages de milestones
MILESTONE_MESSAGES = {
    'deaths': {
        100: [
            "100 morts déjà ! La fontaine commence à te manquer ?",
            "Cent morts... Tu testes les respawn timers ?",
            "100 fois mort, la boutique te connaît par ton prénom"
        ],
        250: [
            "250 morts... L'écran gris devient confortable",
            "250 visites à la fontaine, t'as un abonnement ?",
            "À ce rythme-là, la mort te tutoie"
        ],
        500: [
            "500 morts... On commence à s'inquiéter 😅",
            "500 fois au sol, tu fais du tourisme ?",
            "La fontaine te garde une place maintenant"
        ],
        750: [
            "750 morts... Tu joues en noir et blanc ?",
            "La mort te ping maintenant",
            "750 fois tombé, mais toujours debout"
        ],
        1000: [
            "1000 morts ! L'écran gris est ton foyer",
            "1000 fois mort... Tu sais que base c'est pas obligatoire ?",
            "À ce stade, t'as fusionné avec la fontaine"
        ],
        1500: [
            "{player} voit la vie en gris : 1500 morts 💀",
            "1500 morts... c'est presque artistique",
            "La mort te reconnaît au loading"
        ],
        2000: [
            "2000 morts ! Tu nourris toute la faille",
            "Même les sbires ont pitié",
            "2000 fois au sol, respect pour la persévérance"
        ],
        2500: [
            "2500 morts... La générosité incarnée",
            "{player} donne plus que le support",
            "Les ennemis te disent merci"
        ],
        3000: [
            "3000 morts... la mort n'a plus de secrets pour toi",
            "Record atteint : {player} a défié la faucheuse",
            "Tu meurs tellement que c'est devenu un skill"
        ]

    },
    
    'kills': {
        100: [
            "Et de 100 ! Le début d'une légende ? ⚔️",
            "100 kills ! Ça commence à sentir le smurf",
            "100 éliminatons ! GG"
        ],
        250: [
            "250 kills ! La liste des victimes s'allonge",
            "{player} fait un carnage ! 💀",
            "250 eliminations... Ça devient sérieux"
        ],
        500: [
            "500 kills ! Ça commence à faire mal ! 🔥",
            "500 ennemis renvoyés chez eux ! 💀",
            "500 victimes à ton tableau de chasse"
        ],
        750: [
            "750 kills ! La machine de guerre s'emballe",
            "750 kills, la faille tremble devant toi",
            "750 eliminations... {player} est incontrôlable"
        ],
        1000: [
            "1000 kills ! La faille se souviendra de toi 👑",
            "1000 victimes... quelqu'un peut l'arrêter ?",
            "Tu viens de passer un cap légendaire"
        ],
        2000: [
            "2000 kills... c'est un carnage permanent",
            "La file ennemie te craint",
            "2000 fois plus fort que la moyenne"
        ],
        2500: [
            "2500 kills ! Une vraie machine de guerre",
            "{player} ne connaît plus la pitié",
            "Le tableau des scores est en PLS"
        ],
        3000: [
            "3000 kills... C'EST ILLÉGAL 😈",
            "{player} joue à un autre niveau",
            "Légende vivante de la faille"
        ]
    },
    
    'games': {
        50: [
            "50 games ! Tu commences à accrocher 🎮",
            "50 games ! Bienvenue dans l'addiction",
            "50 parties... Le début d'une belle histoire"
        ],
        100: [
            "100 games ! T'as installé LoL sur ton lit ? 🛏️",
            "Centenaire de games ! Touch grass maybe ?",
            "100 parties... L'herbe te manque pas ?"
        ],
        250: [
            "250 games... pense à cligner des yeux 👀",
            "Ta chaise te reconnaît maintenant",
            "La faille, c'est un peu chez toi"
        ],
        500: [
            "500 parties ! On parle plus de hobby là",
            "Tu vis ici non ?",
            "La faille a ton badge"
        ],
        750: [
            "750 games... sommeil optionnel",
            "{player} a fusionné avec son setup",
            "La faille est ton adresse principale"
        ],
        1000: [
            "1000 games... on peut parler d'addiction 😱",
            "Tu vis littéralement sur LoL",
            "{player} est officiellement perdu"
        ]
    },
    
    'wins': {
        50: [
            "50 victoires ! Winner mentality 💪",
            "50 wins, on sent déjà le talent",
            "50W ! Continue comme ça champion"
        ],
        100: [
            "100 wins ! Ça commence à être sérieux 👀",
            "100 victoires ! Le smurf se réveille",
            "100W ! Arrête de bully les gens"
        ],
        200: [
            "200 victoires ! Tu roules sur la soloQ 🥇",
            "200 wins... c'est ton elo ou un smurf ?",
            "200W ! Respect ✊"
        ],
        300: [
            "300 victoires ! Qui peut t'arrêter ?",
            "{player} est intouchable à 300W",
            "300 wins de pure domination"
        ],
        500: [
            "500 VICTOIRES ! INARRÊTABLE 🔥",
            "500W... MVP permanent du serveur",
            "{player} est une machine à gagner"
        ],
        750: [
            "750 wins ! C'est plus humain là",
            "{player} ne connaît que la victoire",
            "750W... la faille te respecte"
        ],
        1000: [
            "1000 VICTOIRES ! LÉGENDE ABSOLUE 👑",
            "Palier historique atteint : 1000W",
            "{player} est entré dans l'histoire de la faille"
        ]
    },

    
    'losses': {
        50: [
            "Ça arrive à tout le monde... 50 fois 😅",
            "50 défaites, on apprend encore",
            "50L... le mental tient bon ?"
        ],
        100: [
            "100 défaites mais toujours là 💪",
            "100L... persévérance +100",
            "Respect pour le mental"
        ],
        200: [
            "200 défaites... le mental est solide 😰",
            "{player} encaisse encore",
            "200L, ça forge le caractère"
        ],
        300: [
            "300 défaites... tu veux qu'on en parle ?",
            "Mental en titane à 300L",
            "Toujours debout malgré tout"
        ],
        500: [
            "500 défaites... {player} est un survivant 💔",
            "Rien ne te fait quitter",
            "500L... respect éternel"
        ],
        750: [
            "750 défaites... le guerrier infatigable",
            "Rien ne te brise",
            "{player} refuse d'abandonner"
        ],
        1000: [
            "1000 DÉFAITES ! Mental d'acier 🗿",
            "Tu as survécu à l'impossible",
            "{player} a transcendé la souffrance"
        ]
    },

    
    'win_streak': {
        5: [
            "ON FIRE ! 5 wins d'affilée 🔥",
            "Série de 5 victoires !",
            "{player} est chaud bouillant"
        ],
        10: [
            "IMPARABLE ! 10 wins d'affilée 🚀",
            "10 victoires sans perdre, c'est fou",
            "{player} roule sur la faille"
        ],
        15: [
            "PHÉNOMÈNE ! 15 wins d'affilée 👑",
            "C'est un smurf ou quoi ?!",
            "{player} vient d'une autre dimension"
        ],
        20: [
            "20 WINS D'AFFILÉE ! C'EST N'IMPORTE QUOI 🤯",
            "{player} est un dieu vivant",
            "Record monstrueux : 20 victoires de suite"
        ]
    },

    
    'lose_streak': {
        5: [
            "Petite série noire... ça va passer 😅",
            "5 défaites d'affilée, on reset",
            "Pause recommandée"
        ],
        10: [
            "10 défaites d'affilée... courage 😰",
            "{player} mérite un câlin",
            "La malédiction est réelle"
        ],
        15: [
            "15 défaites... mental d'acier 💔",
            "{player} survit à tout",
            "Même le jeu s'acharne"
        ],
        20: [
            "20 DÉFAITES D'AFFILÉE... respect 🫂",
            "Comment t'es encore là ?!",
            "Record de résilience absolue"
        ]
    },

    
    'champion_games': {
        25: [
            "{player} commence à maîtriser {champion} 🎭",
            "25 games sur {champion}, ça devient sérieux",
            "{champion} commence à te connaître"
        ],
        50: [
            "Main {champion} confirmé 👤",
            "50 games sur {champion}, plus de doute",
            "{champion} fait partie de ta vie"
        ],
        100: [
            "{player} refuse de jouer autre chose 😤",
            "100 games sur {champion} : maîtrise totale",
            "{champion} est une extension de {player}"
        ],
        200: [
            "200 games sur {champion} ! One-trick légendaire",
            "{champion} main niveau Faker",
            "{player} = {champion}"
        ],
        300: [
            "300 games sur {champion} ! C'EST MALADE 🤯",
            "{player} EST {champion}",
            "Maîtrise absolue : 300 parties"
        ]
    }

}

def get_milestone_message(milestone_type: str, value: int, player_name: str, extra: str = None):
    """Récupère un message aléatoire pour un milestone donné"""
    messages = MILESTONE_MESSAGES.get(milestone_type, {}).get(value, [])
    if not messages:
        return None
    
    message = random.choice(messages)
    
    # Remplacer les placeholders
    message = message.replace('{player}', player_name)
    if extra:
        message = message.replace('{champion}', extra)
    
    return message

