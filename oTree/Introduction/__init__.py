from otree.api import *

import random


doc = """
Introduction app:
- General instructions, attention checks, comprehension checks
- Roles (seller / buyer) are created here (via group_by_arrival_time)
- Only 2S1B groups are used in this app
- Roles are then reused in the main_experiment app, but groups are NOT kept fixed
"""


class C(BaseConstants):
    NAME_IN_URL = 'introduction'
    PLAYERS_PER_GROUP = None
    NUM_ROUNDS = 1

    # General intro parameters (not used in grouping logic)
    N_LOTTERIES = 5
    TIME_TO_FINISH = 15  # minutes
    BASE_PAY = 2.0  # in Pound
    EXCHANGE_RATE = 13

    # These constants MUST match the ones in Experiment.C
    EXP_NUM_ROUNDS = 5
    EXP_MAX_PAYOFF_STATES = [100, 120, 140, 160, 180]
    EXP_MID_PROBABILITIES = [0.09, 0.19, 0.29, 0.39, 0.49]


class Subsession(BaseSubsession):
    """
    Keine Prolific-spezifischen Felder mehr.
    """
    pass


class Group(BaseGroup):
    # Group type, immer '2S1B' in diesem App (wenn Gruppe vollständig)
    group_type = models.StringField()


class Player(BasePlayer):

    # Attention checks
    attention_check_daylight = models.StringField(label="")
    attention_check_color = models.StringField(
        choices=['Rot', 'Grün', 'Blau', 'Gelb'],
        label=""
    )

    # Count of attention check attempts
    attention_tries = models.IntegerField(initial=0)

    # --- Role & indices (assigned when groups are formed in this app) ---

    # 'seller' or 'buyer'; assigned via group_by_arrival_time
    player_role = models.StringField()
    # index within role in the (temporary) group (1 or 2 for sellers, 1 for buyers)
    seller_index = models.IntegerField(initial=0)
    buyer_index = models.IntegerField(initial=0)

    # --- Role-specific comprehension checks (seller) ---

    seller_comp_1 = models.IntegerField(
        label="",
        choices=[
            [1, "Es ist möglich, dass ich sowohl 30 Münzen als auch 80 Münzen erhalte."],
            [2, "Ich erhalte entweder 30 Münzen ODER 80 Münzen ODER 0 Münzen."],
            [3, "Ich erhalte mit Sicherheit mindestens einige Münzen."],
        ],
        widget=widgets.RadioSelect,
        blank=True,
    )
    seller_comp_2 = models.IntegerField(
        label="",
        choices=[
            [1, "Die Wahrscheinlichkeit, 30 Münzen zu erhalten, beträgt 60 %."],
            [2, "Die Wahrscheinlichkeit, 30 Münzen zu erhalten, beträgt 40 %."],
            [3, "Die Wahrscheinlichkeit, 30 Münzen zu erhalten, beträgt 0 %."],
        ],
        widget=widgets.RadioSelect,
        blank=True,
    )
    seller_comp_3 = models.IntegerField(
        label="",
        choices=[
            [1, "Die maximale Auszahlung der Lotterie, die Sie anbieten."],
            [2, "Eine zufällig generierte Zahl."],
            [3, "Der Preis, zu dem Sie die Lotterie verkauft haben."],
        ],
        widget=widgets.RadioSelect,
        blank=True,
    )
    seller_comp_4 = models.IntegerField(
        label="",
        choices=[
            [1, "Sie erhalten keinen Bonus."],
            [2, "Ihr Bonus entspricht dem Betrag, den der Käufer bereit gewesen wäre zu zahlen."],
            [3, "Ihr Bonus beträgt 25 Münzen."],
        ],
        widget=widgets.RadioSelect,
        blank=True,
    )

    seller_comp_tries = models.IntegerField(initial=0)

    # --- Role-specific comprehension checks (buyer) ---

    buyer_comp_1 = models.IntegerField(
        label="",
        choices=[
            [1, "Es ist möglich, dass ich sowohl 30 Münzen als auch 80 Münzen erhalte."],
            [2, "Ich erhalte entweder 30 Münzen ODER 80 Münzen ODER 0 Münzen."],
            [3, "Ich erhalte mit Sicherheit mindestens einige Münzen."],
        ],
        widget=widgets.RadioSelect,
        blank=True,
    )
    buyer_comp_2 = models.IntegerField(
        label="",
        choices=[
            [1, "Die Wahrscheinlichkeit, 30 Münzen zu erhalten, beträgt 60 %."],
            [2, "Die Wahrscheinlichkeit, 30 Münzen zu erhalten, beträgt 40 %."],
            [3, "Die Wahrscheinlichkeit, 30 Münzen zu erhalten, beträgt 0 %."],
        ],
        widget=widgets.RadioSelect,
        blank=True,
    )
    buyer_comp_3 = models.IntegerField(
        label="",
        choices=[
            [1, "Ein von KI unterstützter Algorithmus"],
            [2, "Ein anderer Teilnehmer des Experiments mit Gewinnabsicht"],
            [3, "Eine Firma mit Gewinnabsicht"],
        ],
        widget=widgets.RadioSelect,
        blank=True,
    )

    buyer_comp_tries = models.IntegerField(initial=0)

    # Helper to pass exchange rate to templates
    def get_general_instruction_vars(self):
        return {
            'exchange_rate': int(1 / self.session.config['real_world_currency_per_point']),
        }


# --- SESSION CREATION ---


def creating_session(subsession: Subsession):
    """
    Keine Prolific-spezifische Logik mehr.
    Grouping und Rollenzuweisung passieren über group_by_arrival_time_method.
    """
    pass


# --- DYNAMIC ROLE ASSIGNMENT & GROUPING (2S1B) ------------------------------


def group_by_arrival_time_method(subsession: Subsession, waiting_players):
    """
    Called when a new player reaches the GroupingWaitPage.

    In this app, we only form 2S1B groups (2 sellers, 1 buyer),
    but these groups are *not* reused in the main experiment.

    Roles are assigned here and stored in participant.vars['player_role'],
    but no persistent group IDs are stored.
    """
    required_players = 3

    # Not enough players yet to form the next 2S1B group
    if len(waiting_players) < required_players:
        return

    # First 3 waiting players form the next temporary group
    group_players = waiting_players[:required_players]

    seller_counter = 0
    buyer_counter = 0

    for i, p in enumerate(group_players):
        # First two players in the group become sellers, third becomes buyer.
        if i < 2:
            role = 'seller'
            seller_counter += 1
            p.seller_index = seller_counter
        else:
            role = 'buyer'
            buyer_counter += 1
            p.buyer_index = buyer_counter

        p.player_role = role

        # Store role in participant.vars for use in the main experiment
        part = p.participant
        part.vars['player_role'] = role
        # Keine intro_group_id, keine persistente Gruppierung.

    return group_players


# --- PAGES ---


class Welcome(Page):
    """
    Welcome page.
    No CAPTCHA is used anymore.
    """
    pass


class AttentionCheck(Page):
    """
    Neutral attention check for all participants.
    Participants must pass this check; they can repeat it as often as needed.
    The number of attempts is recorded in attention_tries.
    """
    form_model = 'player'
    form_fields = ['attention_check_daylight', 'attention_check_color']

    @staticmethod
    def error_message(player, values):
        # Count each submission as an attempt
        player.attention_tries += 1

        enough_words = len(values['attention_check_daylight'].split()) >= 10
        correct_color = values['attention_check_color'] == 'Grün'

        if not (enough_words and correct_color):
            return "Einige Antworten waren falsch. Bitte versuchen Sie es nochmal."


class GroupingWaitPage(WaitPage):
    """
    Roles are assigned via group_by_arrival_time (2 sellers, 1 buyer).
    The concrete groups in this app are temporary and NOT reused in the
    main experiment (there is no intro_group_id anymore).
    """
    group_by_arrival_time = True

    @staticmethod
    def after_all_players_arrive(group: Group):
        """
        Once a temporary group is formed and everyone in that group arrived,
        set group_type based on the number of sellers and buyers.
        (Should always be '2S1B' here.)
        """
        players_in_group = group.get_players()
        sellers = [p for p in players_in_group if p.player_role == 'seller']
        buyers = [p for p in players_in_group if p.player_role == 'buyer']
        group.group_type = f"{len(sellers)}S{len(buyers)}B"


class InstructionsSellerIntro(Page):
    """
    Role-specific instructions for sellers in the introduction app.
    Shown only to participants with role 'seller'.
    """
    @staticmethod
    def is_displayed(player: Player):
        return player.player_role == 'seller'

    @staticmethod
    def vars_for_template(player: Player):
        return player.get_general_instruction_vars()


class InstructionsBuyerIntro(Page):
    """
    Role-specific instructions for buyers in the introduction app.
    Shown only to participants with role 'buyer'.
    """
    @staticmethod
    def is_displayed(player: Player):
        return player.player_role == 'buyer'

    @staticmethod
    def vars_for_template(player: Player):
        return player.get_general_instruction_vars()


class ComprehensionSellerIntro(Page):
    """
    Seller-specific comprehension questions.
    Participants can repeat this page until they answer correctly.
    The number of attempts is recorded in seller_comp_tries.
    """
    form_model = 'player'
    form_fields = ['seller_comp_1', 'seller_comp_2', 'seller_comp_3', 'seller_comp_4']

    @staticmethod
    def is_displayed(player: Player):
        return player.player_role == 'seller'

    @staticmethod
    def error_message(player: Player, values):
        correct = (
            values['seller_comp_1'] == 2 and
            values['seller_comp_2'] == 2 and
            values['seller_comp_3'] == 3 and
            values['seller_comp_4'] == 1
        )

        player.seller_comp_tries += 1

        if not correct:
            return "Einige Antworten waren falsch. Bitte versuchen Sie es nochmal."


class ComprehensionBuyerIntro(Page):
    """
    Buyer-specific comprehension questions.
    Participants can repeat this page until they answer correctly.
    The number of attempts is recorded in buyer_comp_tries.
    """
    form_model = 'player'
    form_fields = ['buyer_comp_1', 'buyer_comp_2', 'buyer_comp_3']

    @staticmethod
    def is_displayed(player: Player):
        return player.player_role == 'buyer'

    @staticmethod
    def error_message(player: Player, values):
        correct = (
            values['buyer_comp_1'] == 2 and
            values['buyer_comp_2'] == 2 and
            values['buyer_comp_3'] == 2
        )

        player.buyer_comp_tries += 1

        if not correct:
            return "Einige Antworten waren falsch. Bitte versuchen Sie es nochmal."


class StartExperiment(Page):
    """
    Final page of the introduction.
    Here we generate the participant's lottery sequences
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
    GroupingWaitPage,
    Welcome,
    AttentionCheck,
    InstructionsSellerIntro,
    InstructionsBuyerIntro,
    ComprehensionSellerIntro,
    ComprehensionBuyerIntro,
    StartExperiment,
]
