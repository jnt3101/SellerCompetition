from otree.api import *
import string
import re
import pandas as pd
from pathlib import Path
import datetime



def chain(*iterables):
    # chain('ABC', 'DEF') --> A B C D E F
    for it in iterables:
        for element in it:
            yield element


_LETTERS = chain(enumerate(string.digits + string.ascii_uppercase),
                 enumerate(string.ascii_lowercase, 10))
LETTERS = {ord(d): str(i) for i, d in _LETTERS}

passphrase = 'ncc1701'

class C(BaseConstants):
    NAME_IN_URL = 'BankDetailsOnline'
    PLAYERS_PER_GROUP = None
    NUM_ROUNDS = 1


class Subsession(BaseSubsession):
    pass

class Group(BaseGroup):
    pass

class Player(BasePlayer):
    name = models.StringField(label='Vorname')
    surname = models.StringField(label='Nachname')
    iban = models.StringField(label='IBAN')


# PAGES
class IBAN(Page):
    form_model = 'player'
    form_fields = ['name', 'surname', 'iban',]

    @staticmethod
    def before_next_page(player, timeout_happened):


        print(player.session.code)

        participant_id = []
        # session_code = []
        # time_stamp = []
        # total_payoff = []
        # name = []
        # surname = []
        # iban = []
        #
        participant_id.append(player.participant.id)
        # session_code.append(player.session.code)
        # time_stamp = datetime.datetime.fromtimestamp(time.time()).strftime('%x %X')
        # name.append(player.name)
        # surname.append(player.surname)
        # iban.append(player.iban)
        # total_payoff.append(0)
        # player.participant.iban = '[REDACTED]'
        # player.participant.name = '[REDACTED]'
        # player.participant.surname = '[REDACTED]'

        # Gather all info anonymously
        df = pd.DataFrame({'id': participant_id,
                           'session': player.session.code,
                           'time_stamp': datetime.datetime.fromtimestamp(datetime.datetime.now().timestamp()).strftime('%x %X'),
                           'name': player.name,
                           'surname': player.surname,
                           'iban': player.iban,
                           'payoff': 0})

        # Save info
        session_code = player.session.code
        name = "".join([str(session_code), "_payout_data.csv"])

        if not Path(name).is_file(): # if file does not already exist
            df.to_csv(name, index=False) # Saving to current working directory
        else:
            df.to_csv(name, header=False, mode='a', index=False) # append existing file

        # delete private data from database
        player.name = '[DELETED]'
        player.surname = '[DELETED]'
        player.iban = '[DELETED]'



class IBANWaitPage(WaitPage):
    #wait_for_all_groups = True
    after_all_players_arrive = 'export_variables'
    pass

def _number_iban(iban):
    return (iban[4:] + iban[:4]).translate(LETTERS)


def generate_iban_check_digits(iban):
    number_iban = _number_iban(iban[:2] + '00' + iban[4:])
    return '{:0>2}'.format(98 - (int(number_iban) % 97))


def valid_iban(iban):
    return int(_number_iban(iban)) % 97 == 1


def iban_error_message(player, my_iban):
    my_iban = my_iban.replace(" ", "")
    pattern = r'[^a-zA-Z0-9]'
    if re.search(pattern, my_iban):
        return 'Geben sie bitte eine gültige IBAN ein.'
    elif my_iban == passphrase:
        pass
    elif generate_iban_check_digits(my_iban) == my_iban[2:4] and valid_iban(my_iban):
        print('IBAN valid \n')
    else:
        return 'Geben sie bitte eine gültige IBAN ein.'


page_sequence = [IBAN]
