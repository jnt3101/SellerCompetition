from otree.api import *

from itertools import cycle
import random
import requests


doc = """
Introduction app:
- 2 sellers + 1 buyer per group
- sellers in the same group share the same treatment
- unified introduction for both roles (seller & buyer)
"""


class C(BaseConstants):
    NAME_IN_URL = 'introduction'
    PLAYERS_PER_GROUP = 3
    NUM_ROUNDS = 1

    # You can still use these constants later in other apps
    N_LOTTERIES = 5
    TIME_TO_FINISH = 15  # Minutes
    BASE_PAY = 2.0  # in Pound
    ALL_TREATMENTS = ['TRANSPARENT', 'CENSORING', 'SAMPLE', 'SAMPLE_CENSORING']
    EXCHANGE_RATE = 13


class Subsession(BaseSubsession):
    # These links must be set in settings.py / SESSION_CONFIGS
    prolific_completion_link = models.StringField()
    prolific_attention_link = models.StringField()
    prolific_no_consent_link = models.StringField()


class Group(BaseGroup):
    # Optional: store the treatment at group level as well
    treatment = models.StringField()


class Player(BasePlayer):
    # --- role & treatment ---

    # 'seller' or 'buyer'; set in creating_session
    player_role = models.StringField()
    # treatment label; same for both sellers in a group
    treatment = models.StringField()

    # --- general fields (both roles) ---

    prolific_id = models.StringField(label="Your Prolific-ID:")
    recaptcha_token = models.StringField(blank=True)

    # Attention check
    attention_check_daylight = models.StringField(label="")
    attention_check_color = models.StringField(
        choices=['Red', 'Green', 'Blue', 'Yellow'],
        label=""
    )
    failed_both_attention_checks = models.BooleanField(initial=False)

    # --- seller comprehension questions ---

    seller_comp_1 = models.IntegerField(
        label="",
        choices=[
            [1, "It is possible that I get paid both 30 coins and 80 coins, i.e., I may receive a total amount of 110 coins from this lottery."],
            [2, "I receive EITHER 30 coins OR 80 coins OR 0 coins from this lottery."],
            [3, "I will receive at least some coins with certainty."],
        ],
        widget=widgets.RadioSelect,
    )

    seller_comp_2 = models.IntegerField(
        label="",
        choices=[
            [1, "The probability to receive 30 coins is 60 %."],
            [2, "The probability to receive 30 coins is 40 %."],
            [3, "The probability to receive 30 coins is 0 %."],
        ],
        widget=widgets.RadioSelect,
    )

    seller_comp_3 = models.IntegerField(
        label="",
        choices=[
            [1, "The maximum payoff of the lottery you are selling"],
            [2, "A randomly generated number"],
            [3, "The price that you sold the lottery for"],
        ],
        widget=widgets.RadioSelect,
    )

    seller_comp_4 = models.IntegerField(
        label="",
        choices=[
            [1, "You will not get a bonus"],
            [2, "Your bonus will match the amount the buyer is willing to pay"],
            [3, "Your bonus will be 25 coins"],
        ],
        widget=widgets.RadioSelect,
    )

    # --- buyer comprehension questions ---

    buyer_comp_1 = models.IntegerField(
        label="",
        choices=[
            [1, "It is possible that I get paid both 30 coins and 80 coins, i.e., I may receive a total amount of 110 coins from this lottery."],
            [2, "I receive EITHER 30 coins OR 80 coins OR 0 coins from this lottery."],
            [3, "I will receive at least some coins with certainty."],
        ],
        widget=widgets.RadioSelect,
    )

    buyer_comp_2 = models.IntegerField(
        label="",
        choices=[
            [1, "The probability to receive 30 coins is 60 %."],
            [2, "The probability to receive 30 coins is 40 %."],
            [3, "The probability to receive 30 coins is 0 %."],
        ],
        widget=widgets.RadioSelect,
    )

    buyer_comp_3 = models.IntegerField(
        label="",
        choices=[
            [1, "An AI powered algorithm"],
            [2, "Another participant that wants to earn money"],
            [3, "A firm that wants to earn money"],
        ],
        widget=widgets.RadioSelect,
    )

    # Number of attempts for control questions
    seller_comp_tries = models.IntegerField(initial=0)
    buyer_comp_tries = models.IntegerField(initial=0)

    @staticmethod
    def get_general_instruction_vars(player):
        """
        Helper to pass common variables to templates, e.g. exchange rate.
        """
        return {
            'exchange_rate': int(1 / player.session.config['real_world_currency_per_point']),
        }


# --- session creation & matching ---


def creating_session(subsession: Subsession):
    """
    - Set Prolific links from session config
    - Create fixed groups of 3 in arrival/ID order:
      first 3 participants = group 1, next 3 = group 2, etc.
    - In each group: 2 sellers + 1 buyer
    - Sellers in the same group share the same treatment
    """
    if subsession.round_number == 1:
        # 1) Read prolific links from session config and store in subsession
        expected_fields = [
            "prolific_completion_link",
            "prolific_attention_link",
            "prolific_no_consent_link",
        ]
        for field in expected_fields:
            if field not in subsession.session.config:
                raise Exception(f"You must set a {field} in settings.py / SESSION_CONFIGS")
            setattr(subsession, field, subsession.session.config[field])

        # 2) Get all players in a fixed, deterministic order
        #    By default get_players() is already sorted by id_in_subsession,
        #    but we sort explicitly to be safe.
        players = subsession.get_players()
        players.sort(key=lambda p: p.id_in_subsession)

        # 3) Build groups of size 3 (players 1–3, 4–6, 7–9, ...)
        #    This assumes that the total number of participants is a multiple of 3.
        group_matrix = [
            players[i:i + C.PLAYERS_PER_GROUP]
            for i in range(0, len(players), C.PLAYERS_PER_GROUP)
        ]

        # Optional safety check: last group must also have 3 players
        if len(group_matrix[-1]) != C.PLAYERS_PER_GROUP:
            raise Exception(
                f"Number of participants is not divisible by {C.PLAYERS_PER_GROUP}. "
                f"Current last group size: {len(group_matrix[-1])}."
            )

        subsession.set_group_matrix(group_matrix)

        # 4) Prepare treatment cycle
        treatments_to_cycle = subsession.session.config.get(
            'treatment_list',
            C.ALL_TREATMENTS.copy()
        )
        random.shuffle(treatments_to_cycle)
        print("Treatments to cycle:", treatments_to_cycle)
        treatment_cycle = cycle(treatments_to_cycle)

        # 5) For each group: assign roles and treatment
        for group in subsession.get_groups():
            players_in_group = group.get_players()

            # Take next treatment from cycle for the whole group
            group_treatment = next(treatment_cycle)
            group.treatment = group_treatment

            for p in players_in_group:
                # By convention: first two players in the group are sellers, last one is buyer
                if p.id_in_group in [1, 2]:
                    p.player_role = 'seller'
                else:
                    p.player_role = 'buyer'

                p.treatment = group_treatment
                p.participant.vars['player_role'] = p.player_role
                p.participant.vars['treatment'] = group_treatment



# --- PAGES ---


class Welcome(Page):
    """
    Simple welcome page with Prolific ID and reCAPTCHA.
    Shown to all players (both roles).
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
    Same attention check for both roles.
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


class InstructionsSeller(Page):
    """
    Instructions page only for sellers.
    """
    @staticmethod
    def is_displayed(player: Player):
        return player.player_role == 'seller'

    @staticmethod
    def vars_for_template(player: Player):
        # You can use this in the template, e.g. to display the exchange rate
        return player.get_general_instruction_vars(player)


class InstructionsBuyer(Page):
    """
    Instructions page only for buyers.
    """
    @staticmethod
    def is_displayed(player: Player):
        return player.player_role == 'buyer'

    @staticmethod
    def vars_for_template(player: Player):
        return player.get_general_instruction_vars(player)


class ComprehensionSeller(Page):
    """
    Control questions for sellers.
    """
    form_model = 'player'
    form_fields = ['seller_comp_1', 'seller_comp_2', 'seller_comp_3', 'seller_comp_4']

    @staticmethod
    def is_displayed(player: Player):
        return player.player_role == 'seller'

    @staticmethod
    def error_message(player: Player, values):
        correct = (
            values['seller_comp_1'] == 2
            and values['seller_comp_2'] == 2
            and values['seller_comp_3'] == 3
            and values['seller_comp_4'] == 1
        )
        if not correct:
            player.seller_comp_tries += 1
            if player.seller_comp_tries < 2:
                return 'You have answered one or more of the control questions incorrectly. Please try again.'
            # If tries >= 2, they will be redirected to ComprehensionFailSeller


class ComprehensionFailSeller(Page):
    """
    Shown if seller answered comprehension questions incorrectly twice.
    """
    @staticmethod
    def is_displayed(player: Player):
        return player.player_role == 'seller' and player.seller_comp_tries >= 2

    @staticmethod
    def vars_for_template(player: Player):
        return {
            "prolific_attention_link": player.subsession.prolific_attention_link
        }


class ComprehensionBuyer(Page):
    """
    Control questions for buyers.
    """
    form_model = 'player'
    form_fields = ['buyer_comp_1', 'buyer_comp_2', 'buyer_comp_3']

    @staticmethod
    def is_displayed(player: Player):
        return player.player_role == 'buyer'

    @staticmethod
    def error_message(player: Player, values):
        correct = (
            values['buyer_comp_1'] == 2
            and values['buyer_comp_2'] == 2
            and values['buyer_comp_3'] == 2
        )
        if not correct:
            player.buyer_comp_tries += 1
            if player.buyer_comp_tries < 2:
                return 'You have answered one or more of the control questions incorrectly. Please try again.'
            # If tries >= 2, they will be redirected to ComprehensionFailBuyer


class ComprehensionFailBuyer(Page):
    """
    Shown if buyer answered comprehension questions incorrectly twice.
    """
    @staticmethod
    def is_displayed(player: Player):
        return player.player_role == 'buyer' and player.buyer_comp_tries >= 2

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
    InstructionsSeller,
    InstructionsBuyer,
    ComprehensionSeller,
    ComprehensionFailSeller,
    ComprehensionBuyer,
    ComprehensionFailBuyer,
    StartExperiment,
]
