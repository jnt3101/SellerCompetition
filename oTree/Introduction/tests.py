from otree.api import Bot
from . import *


class PlayerBot(Bot):
    def play_round(self):
        # WaitPages nicht explizit yielden.
        # GroupingWaitPage wird automatisch von oTree behandelt.

        # 1) Welcome
        yield Welcome

        # 2) Shared instructions
        yield InstructionsIntro

        # 3) Shared comprehension check mit korrekten Antworten
        yield ComprehensionIntro, {
            'buyer_comp_1': 2,
            'buyer_comp_2': 2,
            'buyer_comp_3': 2,
            'seller_comp_3': 3,
            'seller_comp_4': 1,
        }

        # 4) Role page
        yield YourRole


        # 5) Final page
        yield StartExperiment


