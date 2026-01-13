from otree.api import *
import random

from . import *


class PlayerBot(Bot):

    def play_round(self):

        # ------------------------------------------------------
        # Page 1: General
        # ------------------------------------------------------
        yield General, {
            'q_age': random.randint(16, 85),
            'q_gender': random.choice(
                ['Männlich', 'Weiblich', 'Divers', 'Möchte ich nicht beantworten']
            ),
            'q_study_level': random.choice([
                "Kein Schulabschluss",
                "Abitur/Fachabitur",
                "Abgeschlossene Berufsausbildung",
                "Bachelorabschluss",
                "Masterabschluss",
                "Doktorabschluss",
                "Möchte ich nicht beantworten",
            ]),
            'q_study_field': "Random field / profession",
            'q_budget': random.randint(0, 3000),
        }

        # ------------------------------------------------------
        # Page 2: Video_1
        # ------------------------------------------------------
        knows_lootbox = random.choice([True, False])

        yield Video_1, {
            'q_videogame_time': round(random.uniform(0, 8), 2),
            'q_loot_box_what': knows_lootbox,
        }

        # ------------------------------------------------------
        # Page 3: Video_2 (ONLY if q_loot_box_what == True)
        # ------------------------------------------------------
        if knows_lootbox:
            yield Video_2, {
                'q_loot_box_spending': round(random.uniform(0, 50), 2),
                'q_loot_box_more_than_planned': random.choice([True, False]),
            }

        # ------------------------------------------------------
        # Page 4: Control (Self-Control Scale 1–5)
        # ------------------------------------------------------
        yield Control, {
            f'q_self_control_{i}': random.randint(1, 5)
            for i in range(1, 14)
        }

        # ------------------------------------------------------
        # Page 5: Game (Gambling Index 0–3)
        # ------------------------------------------------------
        yield Game, {
            f'q_kfg_{i}': random.choice([0, 1, 2, 3])
            for i in range(1, 21)
        }

        # ------------------------------------------------------
        # Page 6: Debriefing
        # ------------------------------------------------------
        yield Debriefing
