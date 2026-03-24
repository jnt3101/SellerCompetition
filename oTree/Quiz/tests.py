from otree.api import Bot
import random

from . import *


class PlayerBot(Bot):
    def play_round(self):
        # 1) General
        yield General, {
            'q_age': random.randint(16, 85),
            'q_gender': random.choice([
                'Männlich',
                'Weiblich',
                'Divers',
                'Möchte ich nicht beantworten',
            ]),
            'q_study_level': random.choice([
                "Kein Schulabschluss",
                "Abitur/Fachabitur",
                "Abgeschlossene Berufsausbildung",
                "Bachelorabschluss",
                "Masterabschluss",
                "Doktorabschluss",
                "Möchte ich nicht beantworten",
            ]),
            'q_study_field': 'Wirtschaftswissenschaften',
            'q_budget': random.randint(0, 5000),
        }

        # 2) Video_1
        knows_lootbox = random.choice([True, False])

        yield Video_1, {
            'q_videogame_time': round(random.uniform(0, 10), 2),
            'q_loot_box_what': knows_lootbox,
        }

        # 3) Video_2 nur falls Lootboxen bekannt sind
        if knows_lootbox:
            yield Video_2, {
                'q_loot_box_spending': round(random.uniform(0, 100), 2),
                'q_loot_box_more_than_planned': random.choice([True, False]),
            }

        # 4) Control
        yield Control, {
            'q_self_control_1': random.randint(1, 5),
            'q_self_control_2': random.randint(1, 5),
            'q_self_control_3': random.randint(1, 5),
            'q_self_control_4': random.randint(1, 5),
            'q_self_control_5': random.randint(1, 5),
            'q_self_control_6': random.randint(1, 5),
            'q_self_control_7': random.randint(1, 5),
            'q_self_control_8': random.randint(1, 5),
            'q_self_control_9': random.randint(1, 5),
            'q_self_control_10': random.randint(1, 5),
            'q_self_control_11': random.randint(1, 5),
            'q_self_control_12': random.randint(1, 5),
            'q_self_control_13': random.randint(1, 5),
        }

        # 5) Game
        yield Game, {
            'q_kfg_1': random.randint(0, 3),
            'q_kfg_2': random.randint(0, 3),
            'q_kfg_3': random.randint(0, 3),
            'q_kfg_4': random.randint(0, 3),
            'q_kfg_5': random.randint(0, 3),
            'q_kfg_6': random.randint(0, 3),
            'q_kfg_7': random.randint(0, 3),
            'q_kfg_8': random.randint(0, 3),
            'q_kfg_9': random.randint(0, 3),
            'q_kfg_10': random.randint(0, 3),
            'q_kfg_11': random.randint(0, 3),
            'q_kfg_12': random.randint(0, 3),
            'q_kfg_13': random.randint(0, 3),
            'q_kfg_14': random.randint(0, 3),
            'q_kfg_15': random.randint(0, 3),
            'q_kfg_16': random.randint(0, 3),
            'q_kfg_17': random.randint(0, 3),
            'q_kfg_18': random.randint(0, 3),
            'q_kfg_19': random.randint(0, 3),
            'q_kfg_20': random.randint(0, 3),
        }

        # 6) BuyerLotteries nur für Käufer
        if self.player.participant.vars.get('player_role') == 'buyer':
            yield BuyerLotteries, {
                'buyer_lottery_ranking': 'Transparent,Sample,Censoring,Sample_Censoring',
                'buyer_lottery_justification': (
                    'Ich bevorzuge diese Reihenfolge, weil mir Transparenz und '
                    'Nachvollziehbarkeit der Informationen besonders wichtig sind.'
                ),
            }