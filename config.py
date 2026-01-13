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
            "Première centenaire de morts ! La fontaine commence à te manquer ?",
            "100 morts déjà ? Tu testes les respawn timers ?",
            "Centenaire atteint ! La boutique commence à te connaître par cœur"
        ],
        250: [
            "250 morts... La grey screen devient familière",
            "Quarter millénaire de deaths ! C'est un hobby ?",
            "250 visites à la fontaine... T'as une carte VIP ?"
        ],
        500: [
            "500 morts... Tu meurs un peu trop souvent non ?",
            "Demi-millénaire de deaths ! C'est un record ?",
            "500 visites à la fontaine... T'as une carte de fidélité ?"
        ],
        750: [
            "La fontaine, c'est pas ta maison hein !",
            "750 deaths... Tu farm les cooldowns de respawn ?",
            "Trois quarts de millier ! La grey screen te dit bonjour"
        ],
        1000: [
            "1000 morts ! Tu sais que t'es pas obligé de mourir pour base ?",
            "Millénaire achievement unlocked ! La grey screen est ton amie",
            "1000 deaths... Tu joues en mode Permadeath inversé ?"
        ],
        1500: [
            "{player} voit la vie en gris... 1500 morts 💀",
            "1500 morts, c'est presque un art à ce niveau",
            "La fontaine envisage de te facturer un loyer"
        ],
        2000: [
            "Respawn speedrun any% world record ?",
            "2000 deaths ! Tu farm les cooldowns de respawn ?",
            "T'es sponsorisé par la grey screen ?"
        ],
        2500: [
            "Tu nourris tellement l'ennemi qu'ils pourraient te remercier",
            "2500 morts... {player} est généreux avec les kills",
            "Champion de la générosité : 2500 deaths offerts"
        ],
        3000: [
            "3000 MORTS ! {player} a transcendé la mort",
            "Trois millénaires... La mort n'a plus de secrets pour toi",
            "Record historique : 3000 deaths ! Félicitations ?"
        ]
    },
    
    'kills': {
        100: [
            "Première centenaire ! Le début d'une légende ? ⚔️",
            "100 kills ! Ça commence à sentir le smurf",
            "Première centenaire éliminée ! GG"
        ],
        250: [
            "250 kills ! La liste des victimes s'allonge",
            "Quarter millénaire de carnage ! 💀",
            "250 eliminations... Ça devient sérieux"
        ],
        500: [
            "500 kills ! Ça commence à faire mal ! 🔥",
            "Demi-millénaire de carnage ! 💀",
            "500 victimes à ton tableau de chasse"
        ],
        750: [
            "750 kills ! La machine de guerre s'emballe",
            "Trois quarts de millier ! Personne n'est en sécurité",
            "750 eliminations... {player} est incontrôlable"
        ],
        1000: [
            "1000 kills ! Faker tremble devant toi 👑",
            "MILLÉNAIRE ! C'est un massacre",
            "1000 eliminations... Quelqu'un peut l'arrêter ?"
        ],
        1500: [
            "1500 kills ! Machine de guerre activée",
            "La rift a peur de {player} maintenant",
            "Mille cinq cents victimes... C'est plus qu'un jeu"
        ],
        2000: [
            "2000 kills... C'est un carnage ! 🔪",
            "Quelqu'un peut appeler la police ? C'est un massacre",
            "Double millénaire d'eliminations"
        ],
        2500: [
            "2500 KILLS ! {player} est inarrêtable",
            "Deux millénaires et demi de pure domination",
            "La légende vivante : 2500 eliminations"
        ],
        3000: [
            "3000 KILLS ! C'EST PAS HUMAIN ! 👹",
            "Trois millénaires... {player} est immortel",
            "Record légendaire : 3000 eliminations !"
        ]
    },
    
    'games': {
        50: [
            "Demi-centenaire ! Tu commences à accrocher 🎮",
            "50 games ! Bienvenue dans l'addiction",
            "50 parties... Le début d'une belle histoire"
        ],
        100: [
            "100 games ! T'as installé LoL sur ton lit ? 🛏️",
            "Centenaire de games ! Touch grass maybe ?",
            "100 parties... L'herbe te manque pas ?"
        ],
        250: [
            "250 games... Pense à toucher l'herbe de temps en temps 🌱",
            "Quarter millénaire ! Le soleil existe encore tu sais",
            "250 parties... Ta chaise commence à avoir ta forme"
        ],
        500: [
            "500 GAMES ! Quelqu'un peut vérifier si {player} va bien ? 😰",
            "Demi-millénaire ! T'as oublié c'est quoi sortir ?",
            "500 parties... C'est une intervention qu'il te faut"
        ],
        750: [
            "Tu joues plus que tu dors non ? 💤",
            "750 games... {player} a fusionné avec sa chaise",
            "Trois quarts de millier ! La rift est ta vraie maison"
        ],
        1000: [
            "1000 GAMES ! T'as une addiction frérot 😱",
            "MILLÉNAIRE ! Ton lit te reconnaît plus",
            "1000 games... {player} est officiellement perdu"
        ]
    },
    
    'wins': {
        50: [
            "50 victoires ! Winner mentality 💪",
            "Demi-centenaire de wins ! On sent le talent",
            "50W ! Continue comme ça champion"
        ],
        100: [
            "100W ! On sent le smurf là 👀",
            "Centenaire de victoires ! T'es chaud",
            "100 wins ! Arrête de bully les gens"
        ],
        200: [
            "200 wins... Arrête de farmer les golds 🥇",
            "200 victoires ! C'est ton elo ou un smurf ?",
            "Double centenaire ! Respect ✊"
        ],
        300: [
            "Est-ce qu'on peut t'arrêter ? 300 wins",
            "300 victoires ! {player} est intouchable",
            "Trois centenaires de domination !"
        ],
        500: [
            "INARRÊTABLE : 500 victoires ! 🔥",
            "Demi-millénaire de wins ! MVP du serveur",
            "500W ! {player} est une machine"
        ],
        750: [
            "750 WINS ! C'est un monstre",
            "Trois quarts de millier de victoires ! Inhumain",
            "750W... {player} ne connaît que la victoire"
        ],
        1000: [
            "1000 VICTOIRES ! LÉGENDAIRE ! 👑",
            "Millénaire de wins ! Hall of Fame",
            "1000W... {player} est entré dans l'histoire"
        ]
    },
    
    'losses': {
        50: [
            "Ça arrive à tout le monde... 50 fois 😅",
            "50 défaites... On apprend de ses erreurs",
            "Demi-centenaire de L... Le mental tient bon ?"
        ],
        100: [
            "100 défaites, mais on lâche rien ! 💪",
            "Centenaire de losses... Persévérance +100",
            "100L mais toujours là ! Respect pour le mental"
        ],
        200: [
            "200L... Le mental est là ? 😰",
            "Double centenaire de défaites... Ça forge le caractère",
            "200 losses... {player} est incassable mentalement"
        ],
        300: [
            "300 défaites... Tu veux qu'on en parle ?",
            "Trois centenaires de L... Le mental en titane",
            "300 losses et toujours debout ! Respect"
        ],
        500: [
            "500L... {player} est un survivant 💔",
            "Demi-millénaire de defeats... T'es toujours vivant ?",
            "500 défaites... On t'offre une séance de psy ?"
        ],
        750: [
            "750 losses... Le guerrier infatigable",
            "Trois quarts de millier de L... Rien ne te brise",
            "750 défaites... {player} ne connaît pas l'abandon"
        ],
        1000: [
            "1000 DÉFAITES ! Mental d'acier absolu 🗿",
            "Millénaire de losses... Tu es indestructible",
            "1000L... {player} a transcendé la souffrance"
        ]
    },
    
    'win_streak': {
        5: [
            "ON FIRE ! 5 wins d'affilée 🔥",
            "5 WINS STREAK ! Quelqu'un peut l'arrêter ?",
            "Série de 5 victoires ! {player} est chaud bouillant"
        ],
        10: [
            "IMPARABLE ! 10 WINS STREAK 🚀",
            "10 VICTOIRES D'AFFILÉE ! C'EST PAS POSSIBLE",
            "DÉCENNIE DE WINS ! {player} est unstoppable"
        ],
        15: [
            "PHÉNOMÈNE ! Quelqu'un peut l'arrêter ?? 👑",
            "15 WINS STREAK ! C'est un smurf ou quoi ?!",
            "QUINZE VICTOIRES ! {player} vient d'une autre dimension"
        ],
        20: [
            "20 WINS STREAK ! C'EST COMPLÈTEMENT FOU ! 🤯",
            "VINGT VICTOIRES ! {player} est un dieu",
            "RECORD HISTORIQUE : 20 WINS D'AFFILÉE !"
        ]
    },
    
    'lose_streak': {
        5: [
            "Petite série de défaites... ça va passer 😅",
            "5 losses d'affilée... On respire et on reset",
            "Série noire de 5... Prends une pause peut-être ?"
        ],
        10: [
            "10 défaites d'affilée... Respire un coup 😰",
            "10L STREAK... {player} a besoin d'un câlin",
            "Décennie de losses... On est là pour toi"
        ],
        15: [
            "15L... Tu veux qu'on appelle un psy ? 💔",
            "QUINZE DÉFAITES... {player} survit à l'impossible",
            "15 losses streak... Le mental en acier trempé"
        ],
        20: [
            "20 LOSSES STREAK... On t'aime {player} 🫂",
            "VINGT DÉFAITES... Comment t'es encore là ?!",
            "Record de résilience : 20L d'affilée... Respect"
        ]
    },
    
    'champion_games': {
        25: [
            "{player} a trouvé son champion : {champion} ! 🎭",
            "25 games sur {champion}... Ça commence à devenir sérieux",
            "Quarter centenaire sur {champion} !"
        ],
        50: [
            "One-trick {champion} confirmed ! 👤",
            "50 games sur {champion}... C'est ton main maintenant",
            "Demi-centenaire sur {champion} ! Spécialisation"
        ],
        100: [
            "{player} refuse de jouer autre chose que {champion} ! 😤",
            "CENTENAIRE SUR {champion} ! Maîtrise absolue",
            "100 games... {champion} est une extension de {player}"
        ],
        200: [
            "200 GAMES SUR {champion} ! One-trick légendaire",
            "{champion} main niveau Faker",
            "Double centenaire ! {player} = {champion}"
        ],
        300: [
            "300 GAMES SUR {champion} ! C'EST MALADE ! 🤯",
            "Trois centenaires... {player} EST {champion}",
            "Maître suprême de {champion} : 300 parties"
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
