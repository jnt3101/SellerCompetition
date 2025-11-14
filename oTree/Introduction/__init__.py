from otree.api import *

import random
import requests


doc = """
Introduction app:
- general instructions and checks (no roles yet)
- roles & group types are only set in the main_experiment app
"""


class C(BaseConstants):
    NAME_IN_URL = 'introduction'
    PLAYERS_PER_GROUP = None  # no grouping logic needed here
    NUM_ROUNDS = 1

    # You can still use these constants later in other apps
    N_LOTTERIES = 5
    TIME_TO_FINISH = 15  # Minutes
    BASE_PAY = 2.0  # in Pound
    EXCHANGE_RATE = 13


class Subsession(BaseSubsession):
    # These links must be set in settings.py / SESSION_CONFIGS
    prolific_completion_link = models.StringField()
    prolific_attention_link = models.StringField()
    prolific_no_consent_link = models.StringField()


class Group(BaseGroup):
    pass


class Player(BasePlayer):
    # --- general fields (no roles yet) ---

    prolific_id = models.StringField(label="Your Prolific-ID:")
    recaptcha_token = models.StringField(blank=True)

    # Attention check
    attention_check_daylight = models.StringField(label="")
    attention_check_color = models.StringField(
        choices=['Red', 'Green', 'Blue', 'Yellow'],
        label=""
    )
    failed_both_attention_checks = models.BooleanField(initial=False)

    # --- general comprehension questions (shown to everyone) ---

    comp_1 = models.IntegerField(
        label="",
        choices=[
            [1, "It is possible that I get paid both 30 coins and 80 coins, i.e., I may receive a total amount of 110 coins from this lottery."],
            [2, "I receive EITHER 30 coins OR 80 coins OR 0 coins from this lottery."],
            [3, "I will receive at least some coins with certainty."],
        ],
        widget=widgets.RadioSelect,
    )

    comp_2 = models.IntegerField(
        label="",
        choices=[
            [1, "The probability to receive 30 coins is 60 %."],
            [2, "The probability to receive 30 coins is 40 %."],
            [3, "The probability to receive 30 coins is 0 %."],
        ],
        widget=widgets.RadioSelect,
    )

    comp_3 = models.IntegerField(
        label="",
        choices=[
            [1, "The maximum payoff of the lottery"],
            [2, "A randomly generated number"],
            [3, "The price that the lottery is sold for"],
        ],
        widget=widgets.RadioSelect,
    )

    comp_4 = models.IntegerField(
        label="",
        choices=[
            [1, "The seller will not get a bonus"],
            [2, "The sellers' bonus will match the amount the other participant is willing to pay"],
            [3, "The sellers' bonus will be 25 coins"],
        ],
        widget=widgets.RadioSelect,
    )

    comp_tries = models.IntegerField(initial=0)

    @staticmethod
    def get_general_instruction_vars(player):
        """
        Helper to pass common variables to templates, e.g. exchange rate.
        """
        return {
            'exchange_rate': int(1 / player.session.config['real_world_currency_per_point']),
        }


# --- session creation ---


def creating_session(subsession: Subsession):
    """
    - Set Prolific links from session config
    - No grouping and no roles/treatments are assigned here.
      Grouping & roles are set in the main_experiment app.
    """
    if subsession.round_number == 1:
        expected_fields = [
            "prolific_completion_link",
            "prolific_attention_link",
            "prolific_no_consent_link",
        ]
        for field in expected_fields:
            if field not in subsession.session.config:
                raise Exception(f"You must set a {field} in settings.py / SESSION_CONFIGS")
            setattr(subsession, field, subsession.session.config[field])


# --- PAGES ---


class Welcome(Page):
    """
    Simple welcome page with Prolific ID and reCAPTCHA.
    Shown to all participants.
    """
    form_model = 'player'
    form_fields = ['prolific_id', 'recaptcha_token']

    @staticmethod
    def error_message(player, values):
        token = values.get('recaptcha_token')
        if not token:
            return "Please verify that you are not a robot."

        # TODO: Replace this with your own secret key
        secret_key = '6LfLHCcrAAAAAHR2ZraFCkA-II8Ll0z95DQQ3beT'

        payload = {
            'secret': secret_key,
            'response': token
        }
        r = requests.post('https://www.google.com/recaptcha/api/siteverify', data=payload)
        result = r.json()

        if not result.get('success'):
            return "Invalid reCAPTCHA. Please try again."


class AttentionCheck(Page):
    """
    Same attention check for everybody.
    """
    form_model = 'player'
    form_fields = ['attention_check_daylight', 'attention_check_color']

    @staticmethod
    def before_next_page(player, timeout_happened):
        # Check if text answer is at least 10 words and color is 'Green'
        len_att_check_daylight = len(player.attention_check_daylight.split())
        if len_att_check_daylight >= 10 and player.attention_check_color == 'Green':
            player.failed_both_attention_checks = False
        else:
            player.failed_both_attention_checks = True


class AttentionCheckFail(Page):
    """
    Shown if participant failed the attention check.
    """
    @staticmethod
    def is_displayed(player: Player):
        return player.failed_both_attention_checks

    @staticmethod
    def vars_for_template(player: Player):
        return {
            "prolific_attention_link": player.subsession.prolific_attention_link
        }


class InstructionsGeneral(Page):
    """
    General instructions page (no role-specific information yet).
    """
    @staticmethod
    def vars_for_template(player: Player):
        return player.get_general_instruction_vars(player)


class ComprehensionGeneral(Page):
    """
    General control questions, shown to everybody.
    """
    form_model = 'player'
    form_fields = ['comp_1', 'comp_2', 'comp_3', 'comp_4']

    @staticmethod
    def error_message(player: Player, values):
        correct = (
            values['comp_1'] == 2
            and values['comp_2'] == 2
            and values['comp_3'] == 3
            and values['comp_4'] == 1
        )
        if not correct:
            player.comp_tries += 1
            if player.comp_tries < 2:
                return 'You have answered one or more of the control questions incorrectly. Please try again.'
            # If tries >= 2, they will be redirected to ComprehensionFailGeneral


class ComprehensionFailGeneral(Page):
    """
    Shown if participant answered comprehension questions incorrectly twice.
    """
    @staticmethod
    def is_displayed(player: Player):
        return player.comp_tries >= 2

    @staticmethod
    def vars_for_template(player: Player):
        return {
            "prolific_attention_link": player.subsession.prolific_attention_link
        }


class StartExperiment(Page):
    """
    Last page of the introduction.
    From here you can jump to the main experimental app.
    """
    pass


page_sequence = [
    Welcome,
    AttentionCheck,
    AttentionCheckFail,
    InstructionsGeneral,
    ComprehensionGeneral,
    ComprehensionFailGeneral,
    StartExperiment,
]
