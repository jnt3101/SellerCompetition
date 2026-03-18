from otree.api import *

import random


doc = """
Introduction app:
- General instructions, attention checks, comprehension checks
- Roles (seller / buyer) are created here in creating_session
- Players are also assigned to fixed matching groups of size 15 (10 sellers, 5 buyers)
  OR size 3 (2 sellers, 1 buyer)
- The roles and matching_group_id are reused in the main_experiment app
"""


class C(BaseConstants):
    NAME_IN_URL = 'introduction'
    PLAYERS_PER_GROUP = None
    NUM_ROUNDS = 1

    # General intro parameters (not used in grouping logic)
    N_LOTTERIES = 10
    TIME_TO_FINISH = 45  # minutes
    BASE_PAY = 6  # in euro
    EXCHANGE_RATE = 100

    # These constants MUST match the ones in Experiment.C
    EXP_NUM_ROUNDS = 10
    EXP_MAX_PAYOFF_STATES = [100, 120, 140, 160, 180]
    EXP_MID_PROBABILITIES = [0.09, 0.19, 0.29, 0.39, 0.49]


class Subsession(BaseSubsession):
    """
    No Prolific-specific fields anymore.
    """
    pass


class Group(BaseGroup):
    # Group type, not essential in this app anymore.
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

    # Role and indices
    # 'seller' or 'buyer'; assigned in creating_session and kept fixed
    # across all apps (stored in participant.vars['player_role']).
    player_role = models.StringField()

    # Indices within role are not important in this app, but kept for
    # possible diagnostics.
    seller_index = models.IntegerField(initial=0)
    buyer_index = models.IntegerField(initial=0)

    # Shared comprehension checks
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
            [2, "Teilnehmende des Experiments"],
            [3, "Eine Firma mit Gewinnabsicht"],
        ],
        widget=widgets.RadioSelect,
        blank=True,
    )
    seller_comp_3 = models.IntegerField(
        label="",
        choices=[
            [1, "Die maximale Auszahlung der Lotterie, die angeboten wird."],
            [2, "Eine zufällig generierte Zahl."],
            [3, "Der Preis, zu dem die Lotterie verkauft wurde + ihre Anfangsausstattung."],
        ],
        widget=widgets.RadioSelect,
        blank=True,
    )
    seller_comp_4 = models.IntegerField(
        label="",
        choices=[
            [1, "Verkäufer erhalten 50 Münzen und die Lotterie; Käufer erhalten 100 Münzen"],
            [2, "Es gibt keine Anfangsausstattungen."],
            [3, "Beide Rollen erhalten 75 Münzen."],
        ],
        widget=widgets.RadioSelect,
        blank=True,
    )

    comprehension_tries = models.IntegerField(initial=0)

    # Helper to pass exchange rate to templates
    def get_general_instruction_vars(self):
        return {
            'exchange_rate': int(1 / self.session.config['real_world_currency_per_point']),
        }


# --- SESSION CREATION ---


def creating_session(subsession: Subsession):
    """
    At session creation, we assign:
        * fixed matching groups of size 15 (10 sellers, 5 buyers) OR size 3 (2 sellers, 1 buyer)
        * roles 'seller' / 'buyer' within each matching group
    These roles are stored in participant.vars['player_role'] and reused
    in the main_experiment app.
    This guarantees that the Experiment app's grouping logic works correctly
    given the chosen matching group size and composition.
    """
    players = subsession.get_players()
    n_players = len(players)

    # Determine which matching group size to use based on the session size.
    # We support:
    # - 15: 10 sellers + 5 buyers
    # - 3:  2 sellers + 1 buyer
    if n_players % 15 == 0:
        group_size_matching = 15
        roles_template = (['seller'] * 10) + (['buyer'] * 5)
        group_type_value = "10S5B"
    elif n_players % 3 == 0:
        group_size_matching = 3
        roles_template = (['seller'] * 2) + (['buyer'] * 1)
        group_type_value = "2S1B"
    else:
        raise Exception(
            "Total number of participants must be a multiple of 15 (10 sellers, 5 buyers) "
            "or a multiple of 3 (2 sellers, 1 buyer). "
            f"Found {n_players} participants."
        )

    # Store for later pages to avoid hardcoding.
    subsession.session.vars['matching_group_size'] = group_size_matching
    subsession.session.vars['group_type_value'] = group_type_value

    # Sort players by id_in_subsession to get a stable ordering
    players_sorted = sorted(players, key=lambda p: p.id_in_subsession)

    # Assign matching group IDs: blocks of group_size_matching participants
    for idx, p in enumerate(players_sorted):
        mg_id = idx // group_size_matching + 1
        p.participant.vars['matching_group_id'] = mg_id

    # Build matching groups and assign roles inside each group
    matching_groups = {}
    for p in players_sorted:
        mg_id = p.participant.vars['matching_group_id']
        matching_groups.setdefault(mg_id, []).append(p)

    for mg_id, block in matching_groups.items():
        # We require full blocks for this design.
        if len(block) != group_size_matching:
            raise Exception(
                f"Matching group {mg_id} must have exactly {group_size_matching} players. "
                f"Found {len(block)}. Make sure the total number of participants in "
                f"the session is a multiple of {group_size_matching}."
            )

        # Create a role list for this matching group and shuffle it.
        roles = roles_template.copy()
        random.shuffle(roles)

        seller_counter = 0
        buyer_counter = 0

        for p, role in zip(block, roles):
            p.player_role = role
            p.participant.vars['player_role'] = role

            if role == 'seller':
                seller_counter += 1
                p.seller_index = seller_counter
            else:
                buyer_counter += 1
                p.buyer_index = buyer_counter


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
    We no longer need any dynamic grouping logic.
    Assign a fixed group type to avoid None-values later.
    """
    wait_for_all_groups = True
    group_by_arrival_time = False

    @staticmethod
    def after_all_players_arrive(subsession: Subsession):
        group_type_value = subsession.session.vars.get('group_type_value', "2S1B")
        for g in subsession.get_groups():
            g.group_type = group_type_value


class InstructionsIntro(Page):
    """
    Shared instructions page for all participants.
    """
    @staticmethod
    def vars_for_template(player: Player):
        return player.get_general_instruction_vars()


class ComprehensionIntro(Page):
    """
    Shared comprehension questions for all participants.
    Participants can repeat this page until they answer correctly.
    The number of attempts is recorded in comprehension_tries.
    """
    form_model = 'player'
    form_fields = [
        'buyer_comp_1',
        'buyer_comp_2',
        'buyer_comp_3',
        'seller_comp_3',
        'seller_comp_4',
    ]

    @staticmethod
    def error_message(player: Player, values):
        correct = (
            values['buyer_comp_1'] == 2 and
            values['buyer_comp_2'] == 2 and
            values['buyer_comp_3'] == 2 and
            values['seller_comp_3'] == 3 and
            values['seller_comp_4'] == 1
        )

        player.comprehension_tries += 1

        if not correct:
            return "Einige Antworten waren falsch. Bitte versuchen Sie es nochmal."


class YourRole(Page):
    """
    Role reminder page shown after the shared comprehension page.
    """
    @staticmethod
    def vars_for_template(player: Player):
        return {
            'player_role': player.player_role,
        }


class StartExperiment(Page):
    """
    Final page of the introduction.
    Here we generate the participant's lottery sequences
    for the main experiment.
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


page_sequence = [
    GroupingWaitPage,
    Welcome,
    InstructionsIntro,
    ComprehensionIntro,
    YourRole,
    StartExperiment,
]