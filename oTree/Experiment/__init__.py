from otree.api import *

import json
import random

"""
Main interaction app:
- groups formed only here (introduction app has no roles/groups)
- possible group types, used in alternating order:
    * 1 seller + 1 buyer      -> '1S1B'
    * 2 sellers + 1 buyer     -> '2S1B'
    * 2 sellers + 2 buyers    -> '2S2B'
- sellers always have SAMPLE_CENSORING-style options (4 presentations)
- buyers see sellers' lotteries including prices and choose:
    * buy lottery from seller 1
    * buy lottery from seller 2 (if exists)
    * buy no lottery (outside option)
- each buyer can buy at most one lottery
- seller payoff: price of the lottery if (at least) one buyer buys, 0 otherwise
- buyer payoff:
    * if they buy a lottery: outcome of that lottery
    * if they do not buy: lowest price offered by any seller in the group
"""


class C(BaseConstants):
    NAME_IN_URL = 'main_experiment'
    PLAYERS_PER_GROUP = None  # variable group sizes (1S1B, 2S1B, 2S2B)
    NUM_ROUNDS = 5

    # Lottery structure
    MAX_PAYOFF_STATES = [100, 120, 140, 160, 180]
    MID_PROBABILITIES = [0.09, 0.19, 0.29, 0.39, 0.49]

    SAMPLE_SIZE = 400
    DRAWS = 5

    BELIEF_BONUS = 13

    LOTTERY_CHOICES = ['Presentation 1', 'Presentation 2', 'Presentation 3', 'Presentation 4']


# --- lottery helpers --------------------------------------------------------


def create_lottery(q, x):
    """
    Create the lottery that is played in the current round.

    Structure:
    L = ( 0 coins, 1 - q - 0.01 ;
         10 coins, q ;
          x coins, 0.01 )

    where q is the probability for the middle payoff state
    and x is the highest payoff state.
    """
    lottery = {
        0: 1 - q - 0.01,
        10: q,
        x: 0.01,
    }
    return lottery


def sort_lottery(lottery):
    """
    Sorts a lottery by payoff state in an increasing order.
    Args:
        lottery (dict): payoff -> probability
    Returns:
        list of (payoff, probability) sorted by payoff.
    """
    dict_items_sorted = sorted(lottery.items(), key=lambda x: x[0])
    return dict_items_sorted


def draw_lottery_outcome(mid_probability, max_payoff):
    """
    Draw a single outcome from the lottery defined by (q, x).
    """
    current_lottery = create_lottery(q=mid_probability, x=max_payoff)
    outcome = random.choices(
        population=list(current_lottery.keys()),
        weights=list(current_lottery.values()),
        k=1,
    )[0]
    return outcome


# --- models -----------------------------------------------------------------


class Subsession(BaseSubsession):
    pass


class Group(BaseGroup):
    """
    Group-level fields mainly for storing meta information.
    """
    group_type = models.StringField()  # e.g. '1S1B', '2S1B', '2S2B'


class Player(BasePlayer):
    # --- role & indices ------------------------------------------------------

    # 'seller' or 'buyer'; assigned in creating_session of this app
    player_role = models.StringField()
    # index within role in the group (1 or 2)
    seller_index = models.IntegerField(initial=0)
    buyer_index = models.IntegerField(initial=0)

    # --- lottery parameters (per round, for everyone's "own" lottery) -------

    max_payoff = models.IntegerField()
    mid_probability = models.FloatField()

    # --- seller-specific fields ---------------------------------------------

    # price for the seller's lottery
    selling_price_lottery = models.CurrencyField(label="", min=0)

    # belief about highest payoff state (second-order belief about buyers)
    belief = models.IntegerField(label="")
    belief_sequence = models.LongStringField(blank=True)

    # raw sample and displayed subsample (always used, SAMPLE_CENSORING-style)
    all_draws = models.LongStringField()
    subsample = models.LongStringField()

    # lottery presentation choice
    presentation_order = models.StringField()        # encoding order of presentations
    chosen_presentation_id = models.StringField()    # actual presentation ID used

    chosen_lottery = models.StringField(
        choices=C.LOTTERY_CHOICES,
        label="",
    )
    justified_lottery = models.LongStringField(label="")

    # feedback for sellers
    sold = models.BooleanField(initial=False)
    lottery_outcome = models.CurrencyField()

    # --- buyer-specific fields ----------------------------------------------

    # beliefs about the lotteries (if available)
    # belief about lottery from seller 1 (0–100 out of 100 plays)
    buyer_belief_seller1 = models.IntegerField(label="", initial=0)
    buyer_belief_sequence_seller1 = models.LongStringField(blank=True)

    # belief about lottery from seller 2 (only used if there is a second seller)
    buyer_belief_seller2 = models.IntegerField(label="", initial=0)
    buyer_belief_sequence_seller2 = models.LongStringField(blank=True)

    # choice: 'seller1', 'seller2', or 'none'
    chosen_lottery_from_seller = models.StringField(
        choices=[
            ['seller1', 'Buy lottery from seller 1'],
            ['seller2', 'Buy lottery from seller 2'],
            ['none', 'Do not buy a lottery (outside option)'],
        ],
        label="",
    )

    # feedback for buyers
    bought_lottery = models.BooleanField(initial=False)
    chosen_seller_index = models.IntegerField(initial=0)
    buyer_lottery_outcome = models.CurrencyField()
    outside_option_value = models.CurrencyField()

    # --- general helper methods ---------------------------------------------

    def selling_price_lottery_max(player):
        """
        Helper function to determine the maximum possible price for the given
        round dynamically as it differs by lottery.
        """
        return player.max_payoff

    def set_all_draws(player, x):
        player.all_draws = json.dumps(x)

    def get_all_draws(player):
        return json.loads(player.all_draws)

    def set_subsample(player, x):
        player.subsample = json.dumps(x)

    def get_subsample(player):
        return json.loads(player.subsample)

    def draw_sample(player):
        """
        Draw a random sample from the lottery of which a subsample
        will be displayed to the participant (seller).
        SAMPLE_CENSORING-style: always draw a sample and show the top DRAWS outcomes.
        """
        current_lottery_dist = create_lottery(
            q=player.mid_probability,
            x=player.max_payoff,
        )
        total_sample = random.choices(
            population=list(current_lottery_dist.keys()),
            weights=list(current_lottery_dist.values()),
            k=C.SAMPLE_SIZE,
        )

        subsample = sorted(total_sample, reverse=True)[:C.DRAWS]

        player.set_all_draws(total_sample)
        player.set_subsample(subsample)

    def get_general_instruction_vars(player):
        """
        Helper to pass general variables to templates, e.g. exchange rate.
        """
        context = {
            'exchange_rate': int(1 / player.session.config['real_world_currency_per_point']),
            'show_up': player.session.config['participation_fee'],
        }
        return context


# --- session creation -------------------------------------------------------


def creating_session(subsession: Subsession):
    """
    - assign roles and groups only in this app (not in introduction)
    - group pattern alternates across participants:
        1S1B -> 2S1B -> 2S2B -> 1S1B -> ...
    - initialize sequence of lotteries for each participant (in round 1)
    - assign per-round lottery parameters
    - draw samples for all sellers (SAMPLE_CENSORING-style)
    - keep groups fixed across all rounds
    """
    players = subsession.get_players()

    if subsession.round_number == 1:
        # --- determine alternating group structure ---------------------------
        players_sorted = sorted(players, key=lambda p: p.id_in_subsession)

        # patterns in the desired order:
        patterns = [
            ['seller', 'buyer'],                        # 1S1B
            ['seller', 'seller', 'buyer'],              # 2S1B
            ['seller', 'seller', 'buyer', 'buyer'],     # 2S2B
        ]

        group_matrix = []
        idx_global = 0
        pattern_idx = 0
        n_players = len(players_sorted)

        while idx_global < n_players:
            pattern = patterns[pattern_idx]
            size = len(pattern)

            if idx_global + size > n_players:
                raise Exception(
                    "Number of participants is not compatible with the alternating "
                    "pattern [1S1B, 2S1B, 2S2B]. Please adjust the number of "
                    "participants or implement a custom grouping rule."
                )

            group_players = players_sorted[idx_global: idx_global + size]
            idx_global += size

            seller_counter = 0
            buyer_counter = 0
            for role, p in zip(pattern, group_players):
                p.player_role = role
                if role == 'seller':
                    seller_counter += 1
                    p.seller_index = seller_counter
                elif role == 'buyer':
                    buyer_counter += 1
                    p.buyer_index = buyer_counter
                else:
                    raise Exception(f"Unknown role '{role}' in grouping pattern.")

                # store role info for later rounds
                p.participant.vars['player_role'] = p.player_role
                p.participant.vars['seller_index'] = p.seller_index
                p.participant.vars['buyer_index'] = p.buyer_index

            group_matrix.append(group_players)

            # move to next pattern in cycle
            pattern_idx = (pattern_idx + 1) % len(patterns)

        subsession.set_group_matrix(group_matrix)

        # initialize random sequences of lotteries and paid round
        for p in subsession.get_players():
            max_payoff_states_shuffled = C.MAX_PAYOFF_STATES.copy()
            random.shuffle(max_payoff_states_shuffled)

            mid_probabilities_shuffled = C.MID_PROBABILITIES.copy()
            random.shuffle(mid_probabilities_shuffled)

            p.participant.vars['payoff_probability_combinations'] = list(
                zip(max_payoff_states_shuffled, mid_probabilities_shuffled)
            )

            if 'paid_round' not in p.participant.vars:
                p.participant.vars['paid_round'] = random.randint(1, C.NUM_ROUNDS)
    else:
        # keep the same groups in all later rounds
        subsession.group_like_round(1)

    # --- for every round, reload role info and lottery parameters -------------
    for p in subsession.get_players():
        # ensure role & indices are available in every round
        p.player_role = p.participant.vars.get('player_role')
        p.seller_index = p.participant.vars.get('seller_index', 0)
        p.buyer_index = p.participant.vars.get('buyer_index', 0)

        # Lottery parameters for this round
        payoff_prob_combos = p.participant.vars['payoff_probability_combinations']
        p.max_payoff, p.mid_probability = payoff_prob_combos[subsession.round_number - 1]

        # For sellers, draw sample each round (SAMPLE_CENSORING-style)
        if p.player_role == 'seller':
            p.draw_sample()

    # set group_type on each group (e.g. 1S1B, 2S1B, 2S2B)
    for g in subsession.get_groups():
        players_in_group = g.get_players()
        n_sellers = sum(1 for pl in players_in_group if pl.player_role == 'seller')
        n_buyers = sum(1 for pl in players_in_group if pl.player_role == 'buyer')
        g.group_type = f"{n_sellers}S{n_buyers}B"


# --- context helpers for templates -----------------------------------------


def generate_context_for_seller(player: Player):
    """
    Build context dict for a seller to display her own lottery.
    Includes:
    - payoff states
    - probabilities
    - joint upper probability
    - subsample (list of observed outcomes)
    - general instruction variables
    """
    context = dict()

    # Sort the lottery
    current_sorted_lottery = sort_lottery(
        create_lottery(
            q=player.mid_probability,
            x=player.max_payoff,
        )
    )
    sorted_payoffs, sorted_probs = zip(*current_sorted_lottery)

    # Split
    payoff_low, payoff_mid, payoff_high = sorted_payoffs
    prob_low, prob_mid, prob_high = sorted_probs

    prob_upper_joint = prob_mid + prob_high

    context['payoff_low'] = payoff_low
    context['payoff_mid'] = payoff_mid
    context['payoff_high'] = payoff_high

    context['prob_low'] = int(round(prob_low * 100))
    context['prob_mid'] = int(round(prob_mid * 100))
    context['prob_high'] = int(round(prob_high * 100))
    context['prob_upper_joint'] = int(round(prob_upper_joint * 100))

    # SAMPLE_CENSORING-style subsample
    context['subsample'] = player.get_subsample()

    context.update(player.get_general_instruction_vars())
    return context


def generate_context_for_buyer(player: Player):
    """
    Build context dict for the buyer showing all sellers' lotteries in the group.
    Works for both:
    - 1 seller + 1 buyer
    - 2 sellers + 1 buyer
    - 2 sellers + 2 buyers
    """
    group = player.group
    sellers = [p for p in group.get_players() if p.player_role == 'seller']
    sellers.sort(key=lambda p: p.seller_index)

    if len(sellers) not in [1, 2]:
        raise Exception("Each group must contain 1 or 2 sellers.")

    sellers_context = []

    for s in sellers:
        lottery_sorted = sort_lottery(
            create_lottery(q=s.mid_probability, x=s.max_payoff)
        )
        payoffs, probs = zip(*lottery_sorted)
        prob_low, prob_mid, prob_high = probs
        prob_upper_joint = prob_mid + prob_high

        sellers_context.append(
            dict(
                seller_index=s.seller_index,
                payoff_low=payoffs[0],
                payoff_mid=payoffs[1],
                payoff_high=payoffs[2],
                prob_low=int(round(prob_low * 100)),
                prob_mid=int(round(prob_mid * 100)),
                prob_high=int(round(prob_high * 100)),
                prob_upper_joint=int(round(prob_upper_joint * 100)),
                presentation_id=s.chosen_presentation_id,
                subsample=s.get_subsample(),
                price=s.selling_price_lottery,
            )
        )

    context = dict(
        n_sellers=len(sellers),
        sellers=sellers_context,
        group_type=group.group_type,
    )

    context.update(player.get_general_instruction_vars())
    return context


# --- group-level payoff & feedback logic -----------------------------------


def set_trade_and_outcomes(group: Group):
    """
    For each group:
    - read sellers and buyers
    - each buyer chooses at most one seller (or none)
    - if buyer buys from seller i: draw lottery outcome for that buyer
    - seller payoff: price if at least one buyer buys from them, 0 otherwise
    - buyer payoff:
        * lottery outcome if a lottery is bought
        * otherwise: lowest price offered by any seller in the group
    """
    players = group.get_players()
    sellers = [p for p in players if p.player_role == 'seller']
    sellers.sort(key=lambda p: p.seller_index)
    buyers = [p for p in players if p.player_role == 'buyer']
    buyers.sort(key=lambda p: p.buyer_index)

    if len(sellers) not in [1, 2]:
        raise Exception("Each group must contain 1 or 2 sellers.")

    if len(buyers) not in [1, 2]:
        raise Exception("Each group must contain 1 or 2 buyers.")

    # lowest price across all sellers (outside option for buyers who do not buy)
    lowest_price = min(s.selling_price_lottery for s in sellers)

    # reset seller fields
    for s in sellers:
        s.sold = False
        s.lottery_outcome = Currency(0)

    # handle each buyer
    for b in buyers:
        choice = b.chosen_lottery_from_seller

        b.outside_option_value = lowest_price
        b.bought_lottery = False
        b.chosen_seller_index = 0
        b.buyer_lottery_outcome = Currency(0)

        if choice == 'none' or choice is None:
            # outside option
            b.payoff = lowest_price
        else:
            if choice == 'seller1':
                if len(sellers) < 1:
                    raise Exception("Buyer chose seller1 but there is no seller 1 in this group.")
                chosen_seller = sellers[0]
            elif choice == 'seller2':
                if len(sellers) < 2:
                    raise Exception("Buyer chose seller2 but there is no seller 2 in this group.")
                chosen_seller = sellers[1]
            else:
                raise Exception(f"Unexpected choice value: {choice}")

            outcome = draw_lottery_outcome(
                chosen_seller.mid_probability,
                chosen_seller.max_payoff,
            )

            b.bought_lottery = True
            b.chosen_seller_index = chosen_seller.seller_index
            b.buyer_lottery_outcome = outcome
            b.payoff = outcome

            # mark seller as having sold (at least once)
            chosen_seller.sold = True
            # store last observed outcome on seller level (for feedback)
            chosen_seller.lottery_outcome = outcome

    # set seller payoffs: price if sold at least once, 0 otherwise
    for s in sellers:
        if s.sold:
            s.payoff = s.selling_price_lottery
        else:
            s.payoff = Currency(0)


# --- PAGES ------------------------------------------------------------------


class LotteryDecisionBase(Page):
    """
    Base class for pages that show the seller's own lottery.
    """
    form_model = 'player'

    @staticmethod
    def vars_for_template(player: Player):
        return generate_context_for_seller(player)


class Lottery_decision(LotteryDecisionBase):
    """
    Seller chooses a presentation among 4 options (SAMPLE_CENSORING-style).
    All sellers use this page independent of group type.
    """
    form_fields = ['chosen_lottery', 'justified_lottery', 'presentation_order']

    @staticmethod
    def is_displayed(player: Player):
        return player.player_role == 'seller'

    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        # Map the participant's choice to the actual presentation ID
        order_list = player.presentation_order.split(',')
        # Extract the chosen presentation number from 'Presentation N'
        choice_number = int(player.chosen_lottery.split(' ')[1]) - 1  # 0-based index
        chosen_presentation_id = order_list[choice_number]
        player.chosen_presentation_id = chosen_presentation_id


class SellerDecision(LotteryDecisionBase):
    """
    Seller states price and belief for her lottery.
    Shown to all sellers, independent of group type.
    """
    form_fields = ['selling_price_lottery', 'belief_sequence', 'belief']

    @staticmethod
    def is_displayed(player: Player):
        return player.player_role == 'seller'


class WaitForSellers(WaitPage):
    """
    Wait until all sellers have chosen their presentations
    and set price + belief, before showing the buyers' page.
    """
    wait_for_all_groups = False  # group-wise is enough


class BuyerDecision(Page):
    """
    Buyer chooses beliefs about one or two lotteries and
    then chooses whether to buy from seller 1, seller 2 (if exists),
    or not to buy a lottery (outside option).
    """
    form_model = 'player'

    @staticmethod
    def is_displayed(player: Player):
        return player.player_role == 'buyer'

    @staticmethod
    def get_form_fields(player: Player):
        group = player.group
        sellers = [p for p in group.get_players() if p.player_role == 'seller']
        sellers.sort(key=lambda p: p.seller_index)
        n_sellers = len(sellers)

        fields = [
            'buyer_belief_sequence_seller1',
            'buyer_belief_seller1',
        ]
        if n_sellers == 2:
            fields += [
                'buyer_belief_sequence_seller2',
                'buyer_belief_seller2',
            ]
        fields.append('chosen_lottery_from_seller')
        return fields

    @staticmethod
    def vars_for_template(player: Player):
        return generate_context_for_buyer(player)


class WaitForBuyerAndSetResults(WaitPage):
    """
    After all buyers submitted their choices, compute trades & outcomes.
    """
    wait_for_all_groups = False

    @staticmethod
    def after_all_players_arrive(group: Group):
        set_trade_and_outcomes(group)


class SellerFeedback(Page):
    """
    Feedback for sellers:
    - whether lottery was bought by at least one buyer
    - own price
    - (last) outcome drawn among buyers who purchased
    """
    @staticmethod
    def is_displayed(player: Player):
        return player.player_role == 'seller'

    @staticmethod
    def vars_for_template(player: Player):
        return dict(
            sold=player.sold,
            price=player.selling_price_lottery,
            outcome=player.lottery_outcome,
        )


class BuyerFeedback(Page):
    """
    Feedback for buyers:
    - whether they bought a lottery
    - if yes: index of seller and outcome
    - if no: outside option (lowest price)
    """
    @staticmethod
    def is_displayed(player: Player):
        return player.player_role == 'buyer'

    @staticmethod
    def vars_for_template(player: Player):
        return dict(
            bought_lottery=player.bought_lottery,
            chosen_seller_index=player.chosen_seller_index,
            lottery_outcome=player.buyer_lottery_outcome,
            outside_option_value=player.outside_option_value,
        )


class InstructionsSellerExp(Page):
    """
    Role-specific instructions for sellers in the experiment app.
    Shown only in round 1.
    """
    @staticmethod
    def is_displayed(player: Player):
        return player.round_number == 1 and player.player_role == 'seller'

    @staticmethod
    def vars_for_template(player: Player):
        return player.get_general_instruction_vars()


class InstructionsBuyerExp(Page):
    """
    Role-specific instructions for buyers in the experiment app.
    Shown only in round 1.
    """
    @staticmethod
    def is_displayed(player: Player):
        return player.round_number == 1 and player.player_role == 'buyer'

    @staticmethod
    def vars_for_template(player: Player):
        return player.get_general_instruction_vars()


page_sequence = [
    # role-specific instructions (only in round 1)
    InstructionsSellerExp,
    InstructionsBuyerExp,
    # sellers choose how to present the lottery (SAMPLE_CENSORING-style)
    Lottery_decision,
    # sellers set price & belief
    SellerDecision,
    # wait until all sellers are done
    WaitForSellers,
    # buyers: beliefs + choice of lottery / outside option
    BuyerDecision,
    # compute trades & lottery outcomes
    WaitForBuyerAndSetResults,
    # feedback for sellers and buyers
    SellerFeedback,
    BuyerFeedback,
]


