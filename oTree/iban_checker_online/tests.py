from otree.api import Bot
from . import IBAN


class PlayerBot(Bot):

    def play_round(self):
        yield IBAN, {
            'name': 'Max',
            'surname': 'Mustermann',
            'iban': 'ncc1701',
        }