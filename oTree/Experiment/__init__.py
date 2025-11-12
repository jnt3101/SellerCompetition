from otree.api import *

import json
import random

"""
Main interaction app:
- groups of 3: 2 sellers + 1 buyer
- sellers choose lottery presentation, price, and belief
- buyer states willingness to pay (WTP) for both sellers' lotteries
- trades if WTP >= price
- feedback each round for both sides
"""


class C(BaseConstants):
    NAME_IN_URL = 'main_experiment'
    PLAYERS_PER_GROUP = 3
    NUM_ROUNDS = 5

    # Lottery structure as in your seller example
    MAX_PAYOFF_STATES = [100, 120, 140, 160, 180]
    MID_PROBABILITIES = [0.09, 0.19, 0.29, 0.39, 0.49]

    SAMPLE_SIZE = 400
    DRAWS = 5
    ALL_TREATMENTS = ['TRANSPARENT', 'CENSORING', 'SAMPLE', 'SAMPLE_CENSORING']

    BELIEF_BONUS = 13

    LOTTERY_CHOICES = ['Presentation 1', 'Presentation 2', 'Presentation 3', 'Presentation 4']
    LOTTERY_CHOICES2 = ['Presentation 1', 'Presentation 2']


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
    Group-level fields mainly for storing trade & outcome info.
    """

    # For seller 1
    s1_traded = models.BooleanField(initial=False)
    s1_price = models.CurrencyField()
    s1_wtp = models.CurrencyField()
    s1_outcome = models.CurrencyField()

    # For seller 2
    s2_traded = models.BooleanField(initial=False)
    s2_price = models.CurrencyField()
    s2_wtp = models.CurrencyField()
    s2_outcome = models.CurrencyField()


class Player(BasePlayer):
    # --- role & treatment ----------------------------------------------------

    # 'seller' or 'buyer'; taken from participant.vars in creating_session
    player_role = models.StringField()
    # treatment: 'TRANSPARENT', 'CENSORING', 'SAMPLE', 'SAMPLE_CENSORING'
    treatment = models.StringField()

    # --- lottery parameters (per round, for everyone's "own" lottery) -------

    max_payoff = models.IntegerField()
    mid_probability = models.FloatField()

    # --- seller-specific fields ---------------------------------------------

    # price for the seller's lottery
    selling_price_lottery = models.CurrencyField(label="", min=0)

    # belief about highest payoff state (can be interpreted as probability in %)
    belief = models.IntegerField(label="")
    belief_sequence = models.LongStringField(blank=True)

    # raw sample and displayed subsample for SAMPLE treatments
    all_draws = models.LongStringField()
    subsample = models.LongStringField()

    # lottery presentation choice
    presentation_order = models.StringField()     # encoding order of presentations
    chosen_presentation_id = models.StringField()  # actual presentation ID used

    chosen_lottery = models.StringField(
        choices=C.LOTTERY_CHOICES,
        label="",
    )
    chosen_lottery2 = models.StringField(
        choices=C.LOTTERY_CHOICES2,
        label="",
    )
    justified_lottery = models.LongStringField(label="")

    # feedback for sellers
    sold = models.BooleanField(initial=False)
    buyer_wtp = models.CurrencyField()
    lottery_outcome = models.CurrencyField()

    # --- buyer-specific fields ----------------------------------------------

    # WTP of buyer for seller 1 and seller 2
    wtp_seller1 = models.CurrencyField(label="", min=0)
    wtp_seller2 = models.CurrencyField(label="", min=0)

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
        Only used in SAMPLE and SAMPLE_CENSORING treatments.
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

        if player.treatment in ['SAMPLE', 'SAMPLE_CENSORING']:
            subsample = sorted(total_sample, reverse=True)[:C.DRAWS]
        else:
            raise Exception(f'There is no sampling in the treatment {player.treatment}.')

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
    - read player_role and treatment from participant.vars (set in introduction app)
    - initialize sequence of lotteries for each participant (in round 1)
    - assign per-round lottery parameters
    - draw samples for SAMPLE treatments
    """
    players = subsession.get_players()

    if subsession.round_number == 1:
        for p in players:
            # --- role: taken from introduction app if available ---------------
            role = p.participant.vars.get('player_role')
            if role in ['seller', 'buyer']:
                p.player_role = role
            else:
                # Fallback: first two in group are sellers, last one is buyer
                if p.id_in_group in [1, 2]:
                    p.player_role = 'seller'
                else:
                    p.player_role = 'buyer'

            # --- treatment: taken from introduction if available --------------
            if 'treatment' not in p.participant.vars:
                # If not set yet, randomly assign (but note: no group-balancing here)
                p.participant.vars['treatment'] = random.choice(C.ALL_TREATMENTS)
            p.treatment = p.participant.vars['treatment']

            # Create random shuffles of payoff states...
            max_payoff_states_shuffled = C.MAX_PAYOFF_STATES.copy()
            random.shuffle(max_payoff_states_shuffled)

            # ...and probabilities.
            mid_probabilities_shuffled = C.MID_PROBABILITIES.copy()
            random.shuffle(mid_probabilities_shuffled)

            # Store zipped combinations across rounds
            p.participant.vars['payoff_probability_combinations'] = list(
                zip(max_payoff_states_shuffled, mid_probabilities_shuffled)
            )

            # Optionally, you can also pick a paid round for final payoff
            if 'paid_round' not in p.participant.vars:
                p.participant.vars['paid_round'] = random.randint(1, C.NUM_ROUNDS)

    # --- IMPORTANT: for every round, reload role & treatment from participant.vars
    for p in players:
        # Ensure we have role and treatment in every round
        role = p.participant.vars.get('player_role')
        if role in ['seller', 'buyer']:
            p.player_role = role
        else:
            # Fallback again, just in case someone runs this app ohne Introduction
            if p.id_in_group in [1, 2]:
                p.player_role = 'seller'
            else:
                p.player_role = 'buyer'

        # Treatment from participant.vars (or random fallback)
        treatment = p.participant.vars.get('treatment')
        if treatment not in C.ALL_TREATMENTS:
            treatment = random.choice(C.ALL_TREATMENTS)
            p.participant.vars['treatment'] = treatment
        p.treatment = treatment

        # Lottery parameters for this round
        payoff_prob_combos = p.participant.vars['payoff_probability_combinations']
        p.max_payoff, p.mid_probability = payoff_prob_combos[subsession.round_number - 1]

        # For SAMPLE treatments, draw sample (only relevant for sellers)
        if p.player_role == 'seller' and p.treatment in ['SAMPLE', 'SAMPLE_CENSORING']:
            p.draw_sample()

        # For TRANSPARENT treatment, the presentation is fixed
        if p.player_role == 'seller' and p.treatment == 'TRANSPARENT':
            p.chosen_presentation_id = 'Transparent'


# --- context helper for templates ------------------------------------------


def generate_context_for_seller(player: Player):
    """
    Build context dict for a seller to display her own lottery.
    Includes:
    - payoff states
    - probabilities
    - joint upper probability
    - subsample if available
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

    if player.treatment in ['SAMPLE', 'SAMPLE_CENSORING']:
        extend_dict = {
            'subsample': player.get_subsample(),
        }
        context.update(extend_dict)

    context.update(player.get_general_instruction_vars())
    return context


def generate_context_for_buyer(player: Player):
    """
    Build context dict for the buyer showing both sellers' lotteries.
    """
    group = player.group
    sellers = [p for p in group.get_players() if p.player_role == 'seller']
    sellers.sort(key=lambda p: p.id_in_group)  # ensure consistent order

    if len(sellers) != 2:
        raise Exception("Each group must contain exactly 2 sellers.")

    s1, s2 = sellers

    # build context for seller 1
    s1_lottery_sorted = sort_lottery(
        create_lottery(q=s1.mid_probability, x=s1.max_payoff)
    )
    s1_payoffs, s1_probs = zip(*s1_lottery_sorted)
    s1_prob_low, s1_prob_mid, s1_prob_high = s1_probs
    s1_prob_upper_joint = s1_prob_mid + s1_prob_high

    # build context for seller 2
    s2_lottery_sorted = sort_lottery(
        create_lottery(q=s2.mid_probability, x=s2.max_payoff)
    )
    s2_payoffs, s2_probs = zip(*s2_lottery_sorted)
    s2_prob_low, s2_prob_mid, s2_prob_high = s2_probs
    s2_prob_upper_joint = s2_prob_mid + s2_prob_high

    context = dict(
        # seller 1 lottery
        s1_payoff_low=s1_payoffs[0],
        s1_payoff_mid=s1_payoffs[1],
        s1_payoff_high=s1_payoffs[2],
        s1_prob_low=int(round(s1_prob_low * 100)),
        s1_prob_mid=int(round(s1_prob_mid * 100)),
        s1_prob_high=int(round(s1_prob_high * 100)),
        s1_prob_upper_joint=int(round(s1_prob_upper_joint * 100)),
        s1_presentation_id=s1.chosen_presentation_id,
        # seller 2 lottery
        s2_payoff_low=s2_payoffs[0],
        s2_payoff_mid=s2_payoffs[1],
        s2_payoff_high=s2_payoffs[2],
        s2_prob_low=int(round(s2_prob_low * 100)),
        s2_prob_mid=int(round(s2_prob_mid * 100)),
        s2_prob_high=int(round(s2_prob_high * 100)),
        s2_prob_upper_joint=int(round(s2_prob_upper_joint * 100)),
        s2_presentation_id=s2.chosen_presentation_id,
    )

    # include subsamples if the chosen presentation is sample-based
    if s1.chosen_presentation_id in ['Sample', 'Sample_Censoring'] and s1.subsample:
        context['s1_subsample'] = s1.get_subsample()
    else:
        context['s1_subsample'] = []

    if s2.chosen_presentation_id in ['Sample', 'Sample_Censoring'] and s2.subsample:
        context['s2_subsample'] = s2.get_subsample()
    else:
        context['s2_subsample'] = []

    context.update(player.get_general_instruction_vars())
    return context


# --- group-level payoff & feedback logic -----------------------------------


def set_trade_and_outcomes(group: Group):
    """
    For each group:
    - read sellers and buyer data
    - determine for each seller if trade occurs (WTP >= price)
    - if trade: draw lottery outcome
    - store all info in Group and Player models
    """
    players = group.get_players()
    sellers = [p for p in players if p.player_role == 'seller']
    sellers.sort(key=lambda p: p.id_in_group)
    buyers = [p for p in players if p.player_role == 'buyer']

    if len(sellers) != 2 or len(buyers) != 1:
        raise Exception("Group must consist of exactly 2 sellers and 1 buyer.")

    s1, s2 = sellers
    buyer = buyers[0]

    # prices
    price1 = s1.selling_price_lottery
    price2 = s2.selling_price_lottery

    # buyer's WTP for each seller
    wtp1 = buyer.wtp_seller1
    wtp2 = buyer.wtp_seller2

    # trade conditions: WTP >= price (independent for each lottery)
    traded1 = wtp1 >= price1
    traded2 = wtp2 >= price2

    # draw outcomes if traded, else 0
    outcome1 = draw_lottery_outcome(s1.mid_probability, s1.max_payoff) if traded1 else Currency(0)
    outcome2 = draw_lottery_outcome(s2.mid_probability, s2.max_payoff) if traded2 else Currency(0)

    # store in group
    group.s1_traded = traded1
    group.s1_price = price1
    group.s1_wtp = wtp1
    group.s1_outcome = outcome1

    group.s2_traded = traded2
    group.s2_price = price2
    group.s2_wtp = wtp2
    group.s2_outcome = outcome2

    # store in sellers for per-player feedback
    s1.sold = traded1
    s1.buyer_wtp = wtp1
    s1.lottery_outcome = outcome1
    s2.sold = traded2
    s2.buyer_wtp = wtp2
    s2.lottery_outcome = outcome2

    # simple payoff rule:
    # sellers earn the price if sold, 0 otherwise
    s1.payoff = price1 if traded1 else Currency(0)
    s2.payoff = price2 if traded2 else Currency(0)

    # buyer's payoff is sum of outcomes of all lotteries he actually bought
    buyer.payoff = outcome1 + outcome2


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
    Seller chooses a presentation among 4 options.
    Only used in SAMPLE_CENSORING treatment.
    """
    form_fields = ['chosen_lottery', 'justified_lottery', 'presentation_order']

    @staticmethod
    def is_displayed(player: Player):
        return player.player_role == 'seller' and player.treatment == 'SAMPLE_CENSORING'

    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        # Map the participant's choice to the actual presentation ID
        order_list = player.presentation_order.split(',')
        # Extract the chosen presentation number from 'Presentation N'
        choice_number = int(player.chosen_lottery.split(' ')[1]) - 1  # 0-based index
        chosen_presentation_id = order_list[choice_number]
        player.chosen_presentation_id = chosen_presentation_id


class Lottery_decision2(LotteryDecisionBase):
    """
    Seller chooses a presentation among 2 options.
    Used in SAMPLE and CENSORING treatments.
    """
    form_fields = ['chosen_lottery2', 'justified_lottery', 'presentation_order']

    @staticmethod
    def is_displayed(player: Player):
        return player.player_role == 'seller' and player.treatment in ['SAMPLE', 'CENSORING']

    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        order_list = player.presentation_order.split(',')
        choice_number = int(player.chosen_lottery2.split(' ')[1]) - 1
        chosen_presentation_id = order_list[choice_number]
        player.chosen_presentation_id = chosen_presentation_id


class SellerDecision(LotteryDecisionBase):
    """
    Seller states price and belief for her lottery.
    Shown to all sellers, independent of treatment.
    """
    form_fields = ['selling_price_lottery', 'belief_sequence', 'belief']

    @staticmethod
    def is_displayed(player: Player):
        return player.player_role == 'seller'


class WaitForSellers(WaitPage):
    """
    Wait until both sellers have chosen their presentations
    and set price + belief, before showing the buyer's page.
    """
    wait_for_all_groups = False  # group-wise is enough


class BuyerDecision(Page):
    """
    Buyer states WTP for the lotteries of both sellers.
    """
    form_model = 'player'
    form_fields = ['wtp_seller1', 'wtp_seller2']

    @staticmethod
    def is_displayed(player: Player):
        return player.player_role == 'buyer'

    @staticmethod
    def vars_for_template(player: Player):
        return generate_context_for_buyer(player)


class WaitForBuyerAndSetResults(WaitPage):
    """
    After buyer submitted WTPs, compute trades & outcomes for this group.
    """
    wait_for_all_groups = False

    @staticmethod
    def after_all_players_arrive(group: Group):
        set_trade_and_outcomes(group)


class SellerFeedback(Page):
    """
    Feedback for sellers:
    - whether lottery was bought
    - buyer's WTP
    - own price
    - outcome (if sold)
    """
    @staticmethod
    def is_displayed(player: Player):
        return player.player_role == 'seller'

    @staticmethod
    def vars_for_template(player: Player):
        return dict(
            sold=player.sold,
            buyer_wtp=player.buyer_wtp,
            price=player.selling_price_lottery,
            outcome=player.lottery_outcome,
        )


class BuyerFeedback(Page):
    """
    Feedback for buyer:
    - own WTPs for both lotteries
    - seller prices
    - trade decisions
    - lottery outcomes (for traded lotteries)
    """
    @staticmethod
    def is_displayed(player: Player):
        return player.player_role == 'buyer'

    @staticmethod
    def vars_for_template(player: Player):
        group = player.group
        return dict(
            s1_traded=group.s1_traded,
            s1_price=group.s1_price,
            s1_wtp=group.s1_wtp,
            s1_outcome=group.s1_outcome,
            s2_traded=group.s2_traded,
            s2_price=group.s2_price,
            s2_wtp=group.s2_wtp,
            s2_outcome=group.s2_outcome,
        )


page_sequence = [
    # sellers choose how to present the lottery (depending on treatment)
    Lottery_decision,
    Lottery_decision2,
    # sellers set price & belief
    SellerDecision,
    # wait until both sellers are done
    WaitForSellers,
    # buyer states WTP for both lotteries
    BuyerDecision,
    # compute trades & lottery outcomes
    WaitForBuyerAndSetResults,
    # feedback for sellers and buyer
    SellerFeedback,
    BuyerFeedback,
]
