from otree.api import *

import random
import requests


doc = """
Introduction app:
- General instructions, attention checks, comprehension checks
- No roles or grouping here
- Roles and groups are only created in the main_experiment app
"""


class C(BaseConstants):
    NAME_IN_URL = 'introduction'
    PLAYERS_PER_GROUP = None
    NUM_ROUNDS = 1

    # General intro parameters (not used in grouping)
    N_LOTTERIES = 5
    TIME_TO_FINISH = 15  # minutes
    BASE_PAY = 2.0  # in Pound
    EXCHANGE_RATE = 13

    # These constants MUST match the ones in Experiment.C
    EXP_NUM_ROUNDS = 5
    EXP_MAX_PAYOFF_STATES = [100, 120, 140, 160, 180]
    EXP_MID_PROBABILITIES = [0.09, 0.19, 0.29, 0.39, 0.49]


class Subsession(BaseSubsession):
    # These links must be provided in SESSION_CONFIGS
    prolific_completion_link = models.StringField()
    prolific_attention_link = models.StringField()
    prolific_no_consent_link = models.StringField()


class Group(BaseGroup):
    pass


class Player(BasePlayer):

    # --- General fields (no roles yet) ---

    prolific_id = models.StringField(label="Your Prolific-ID:")
    recaptcha_token = models.StringField(blank=True)

    # Attention checks
    attention_check_daylight = models.StringField(label="")
    attention_check_color = models.StringField(
        choices=['Red', 'Green', 'Blue', 'Yellow'],
        label=""
    )
    failed_both_attention_checks = models.BooleanField(initial=False)

    # --- Comprehension checks ---

    comp_1 = models.IntegerField(
        label="",
        choices=[
            [1, "It is possible that I get paid both 30 coins and 80 coins."],
            [2, "I receive either 30 coins OR 80 coins OR 0 coins."],
            [3, "I will receive at least some coins with certainty."],
        ],
        widget=widgets.RadioSelect,
    )

    comp_2 = models.IntegerField(
        label="",
        choices=[
            [1, "The probability to receive 30 coins is 60%."],
            [2, "The probability to receive 30 coins is 40%."],
            [3, "The probability to receive 30 coins is 0%."],
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
            [2, "The seller's bonus will match the amount the other participant is willing to pay"],
            [3, "The seller's bonus will be 25 coins"],
        ],
        widget=widgets.RadioSelect,
    )

    comp_tries = models.IntegerField(initial=0)

    # Helper to pass exchange rate to templates
    def get_general_instruction_vars(self):
        return {
            'exchange_rate': int(1 / self.session.config['real_world_currency_per_point']),
        }


# --- SESSION CREATION ---


def creating_session(subsession: Subsession):
    """
    Load Prolific return links from SESSION_CONFIGS.
    No grouping or role assignment happens here.
    """
    if subsession.round_number == 1:
        required_fields = [
            "prolific_completion_link",
            "prolific_attention_link",
            "prolific_no_consent_link",
        ]
        for field in required_fields:
            if field not in subsession.session.config:
                raise Exception(f"You must set {field} in SESSION_CONFIGS")
            setattr(subsession, field, subsession.session.config[field])


# --- PAGES ---


class Welcome(Page):
    """
    Welcome page where participants enter their Prolific ID
    and complete a reCAPTCHA check.
    """
    form_model = 'player'
    form_fields = ['prolific_id', 'recaptcha_token']

    @staticmethod
    def error_message(player, values):
        token = values.get('recaptcha_token')
        if not token:
            return "Please verify that you are not a robot."

        # IMPORTANT: Replace with your own secret key
        secret_key = '6LfLHCcrAAAAAHR2ZraFCkA-II8Ll0z95DQQ3beT'

        payload = {
            'secret': secret_key,
            'response': token,
        }
        r = requests.post('https://www.google.com/recaptcha/api/siteverify', data=payload)
        result = r.json()

        if not result.get('success'):
            return "Invalid reCAPTCHA. Please try again."


class AttentionCheck(Page):
    """
    Neutral attention check for all participants.
    """
    form_model = 'player'
    form_fields = ['attention_check_daylight', 'attention_check_color']

    @staticmethod
    def before_next_page(player, timeout_happened):
        # Must write at least 10 words AND choose "Green"
        enough_words = len(player.attention_check_daylight.split()) >= 10
        correct_color = player.attention_check_color == 'Green'

        player.failed_both_attention_checks = not (enough_words and correct_color)


class AttentionCheckFail(Page):
    """
    Shown only to participants who fail the attention check.
    """
    @staticmethod
    def is_displayed(player):
        return player.failed_both_attention_checks

    @staticmethod
    def vars_for_template(player):
        return {
            "prolific_attention_link": player.subsession.prolific_attention_link
        }


class InstructionsGeneral(Page):
    """
    General instructions (not role-specific).
    """
    @staticmethod
    def vars_for_template(player):
        return player.get_general_instruction_vars()


class ComprehensionGeneral(Page):
    """
    Comprehension questions shown to all participants.
    """
    form_model = 'player'
    form_fields = ['comp_1', 'comp_2', 'comp_3', 'comp_4']

    @staticmethod
    def error_message(player, values):
        correct = (
            values['comp_1'] == 2 and
            values['comp_2'] == 2 and
            values['comp_3'] == 3 and
            values['comp_4'] == 1
        )

        if not correct:
            player.comp_tries += 1

            if player.comp_tries < 2:
                return "Some answers were incorrect. Please try again."
            # After 2 attempts -> fail page will be shown.


class ComprehensionFailGeneral(Page):
    """
    Shown only if comprehension questions were failed twice.
    """
    @staticmethod
    def is_displayed(player):
        return player.comp_tries >= 2

    @staticmethod
    def vars_for_template(player):
        return {
            "prolific_attention_link": player.subsession.prolific_attention_link
        }


class StartExperiment(Page):
    """
    Final page of the introduction.
    Only here do we generate the participant's lottery sequences
    and the paid round for the main experiment.
    """

    @staticmethod
    def before_next_page(player, timeout_happened):
        participant = player.participant

        # Assign randomized sequence of lottery parameters
        if 'payoff_probability_combinations' not in participant.vars:
            max_states = C.EXP_MAX_PAYOFF_STATES.copy()
            mid_probs = C.EXP_MID_PROBABILITIES.copy()

            random.shuffle(max_states)
            random.shuffle(mid_probs)

            participant.vars['payoff_probability_combinations'] = list(
                zip(max_states, mid_probs)
            )

        # Assign randomly selected round for payment
        if 'paid_round' not in participant.vars:
            participant.vars['paid_round'] = random.randint(1, C.EXP_NUM_ROUNDS)


page_sequence = [
    Welcome,
    AttentionCheck,
    AttentionCheckFail,
    InstructionsGeneral,
    ComprehensionGeneral,
    ComprehensionFailGeneral,
    StartExperiment,
]
