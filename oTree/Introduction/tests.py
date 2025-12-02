from otree.api import *
import random

from . import *


class PlayerBot(Bot):

    def play_round(self):
        # ⚠️ WICHTIG:
        # KEIN yield GroupingWaitPage – WaitPages werden von oTree automatisch behandelt.

        # 1) Welcome
        yield Welcome

        # 2) AttentionCheck: alle Spieler
        yield AttentionCheck, {
            'attention_check_daylight': (
                'Dies ist ein längerer Beispielsatz mit deutlich mehr als zehn '
                'Wörtern, damit der Aufmerksamkeitstest sicher bestanden wird.'
            ),
            'attention_check_color': 'Grün',
        }

        # Nach dem AttentionCheck sollte die Rolle durch group_by_arrival_time gesetzt sein
        role = self.player.player_role

        if role == 'seller':
            # 3a) Verkäufer-Instruktionen
            yield InstructionsSellerIntro

            # 4a) Verkäufer-Comprehension mit korrekten Antworten
            yield ComprehensionSellerIntro, {
                'seller_comp_1': 2,
                'seller_comp_2': 2,
                'seller_comp_3': 3,
                'seller_comp_4': 1,
            }

        elif role == 'buyer':
            # 3b) Käufer-Instruktionen
            yield InstructionsBuyerIntro

            # 4b) Käufer-Comprehension mit korrekten Antworten
            yield ComprehensionBuyerIntro, {
                'buyer_comp_1': 2,
                'buyer_comp_2': 2,
                'buyer_comp_3': 2,
            }

        # 5) Letzte Seite: StartExperiment
        yield StartExperiment
