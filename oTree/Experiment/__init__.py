from otree.api import *

import json
import random

"""
Main interaction app:
- Groups are formed already in the introduction app.
- This app reconstructs the same groups in round 1 based on participant.vars,
  and oTree keeps the groups fixed across rounds.
- Roles ('seller' or 'buyer') are assigned in the introduction app and
  stay fixed for all 5 rounds.
- Sellers always have SAMPLE_CENSORING-style options (4 presentations).
- Buyers see the sellers' lotteries including prices and choose:
    * buy lottery from seller 1
    * buy lottery from seller 2 (if exists)
    * buy no lottery (outside option)
- Each buyer can buy at most one lottery.
- Seller payoff: price of the lottery if (at least) one buyer buys, 0 otherwise.
- Buyer payoff:
    * if they buy a lottery: outcome of that lottery
    * if they do not buy: lowest price offered by any seller in the group.
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

    LOTTERY_CHOICES = ['Präsentation 1', 'Präsentation 2', 'Präsentation 3', 'Präsentation 4']


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
    """
    No special logic in creating_session, because groups and roles
    are formed in the introduction app and reconstructed here via
    group_by_arrival_time in round 1.
    """
    pass


class Group(BaseGroup):
    """
    Group-level fields mainly for storing meta information.
    """
    group_type = models.StringField()  # e.g. '1S1B', '2S1B', '2S2B'


class Player(BasePlayer):
    # --- role & indices ------------------------------------------------------

    # 'seller' or 'buyer'; assigned in introduction via group_by_arrival_time
    player_role = models.StringField()
    # index within role in the group (1 or 2)
    seller_index = models.IntegerField(initial=0)
    buyer_index = models.IntegerField(initial=0)

    # --- lottery parameters (per round, for everyone's "own" lottery) -------

    max_payoff = models.IntegerField()
    mid_probability = models.FloatField()

    # Flag to ensure one-time initialization per round
    round_initialized = models.BooleanField(initial=False)

    # --- seller-specific fields ---------------------------------------------

    # price for the seller's lottery (must be >= 1)
    selling_price_lottery = models.CurrencyField(label="", min=1)

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

    # --- flags for automatic (timeout-based) decisions -----------------------
    # These flags remain in the dataset for compatibility, but are no longer
    # used to generate automatic decisions (no timeouts are enforced now).
    auto_lottery_decision = models.BooleanField(initial=False)
    auto_seller_decision = models.BooleanField(initial=False)
    auto_buyer_beliefs = models.BooleanField(initial=False)
    auto_buyer_choice = models.BooleanField(initial=False)

    # --- helper methods ------------------------------------------------------

    def selling_price_lottery_max(self):
        """
        Helper to determine the maximum possible price for the given
        round dynamically (equals the max payoff of the lottery).
        """
        return self.max_payoff

    def set_all_draws(self, x):
        self.all_draws = json.dumps(x)

    def get_all_draws(self):
        return json.loads(self.all_draws)

    def set_subsample(self, x):
        self.subsample = json.dumps(x)

    def get_subsample(self):
        return json.loads(self.subsample)

    def draw_sample(self):
        """
        Draw a random sample from the lottery of which a subsample
        will be displayed to the participant (seller).
        SAMPLE_CENSORING-style: always draw a sample and show the top DRAWS outcomes.
        """
        current_lottery_dist = create_lottery(
            q=self.mid_probability,
            x=self.max_payoff,
        )
        total_sample = random.choices(
            population=list(current_lottery_dist.keys()),
            weights=list(current_lottery_dist.values()),
            k=C.SAMPLE_SIZE,
        )

        subsample = sorted(total_sample, reverse=True)[:C.DRAWS]

        self.set_all_draws(total_sample)
        self.set_subsample(subsample)

    def initialize_round(self):
        """
        Ensure that in every round:
        - role and indices are loaded from participant.vars (determined in introduction app)
        - lottery parameters (max_payoff, mid_probability) are set
        - sellers draw their sample (once per round)
        """
        if self.round_initialized:
            return

        # Always load role & indices from participant.vars.
        self.player_role = self.participant.vars.get('player_role')
        self.seller_index = self.participant.vars.get('seller_index', 0)
        self.buyer_index = self.participant.vars.get('buyer_index', 0)

        # Lottery parameters for this round (sequence stored in introduction app)
        combos = self.participant.vars['payoff_probability_combinations']
        self.max_payoff, self.mid_probability = combos[self.round_number - 1]

        # For sellers, draw sample each round (SAMPLE_CENSORING-style)
        if self.player_role == 'seller':
            self.draw_sample()

        self.round_initialized = True

    def get_general_instruction_vars(self):
        """
        Helper to pass general variables to templates, e.g. exchange rate and show-up fee.
        """
        context = {
            'exchange_rate': int(1 / self.session.config['real_world_currency_per_point']),
            'show_up': self.session.config['participation_fee'],
        }
        return context


# --- session creation -------------------------------------------------------


def creating_session(subsession: Subsession):
    """
    Do not touch roles or groups here.
    - In round 1, grouping is reconstructed via group_by_arrival_time
      using intro_group_id from the introduction app.
    - In later rounds, oTree automatically keeps the same groups as in round 1.
      Roles are reloaded per round from participant.vars in Player.initialize_round().
    """
    pass


# --- dynamic grouping using intro_group_id ----------------------------------


def group_by_arrival_time_method(subsession: Subsession, waiting_players):
    """
    Called when a new player reaches the GroupingWaitPage in round 1.

    We reconstruct the groups that were formed in the introduction app
    using participant.vars['intro_group_id'].

    Logic:
    - For each intro_group_id among waiting_players, check how many players
      in the entire session have that intro_group_id.
    - As soon as all players of one intro_group_id have arrived at this
      GroupingWaitPage, we form that group.
    """
    if subsession.round_number != 1:
        return

    session = subsession.session

    # Group waiting players by their intro_group_id
    by_gid = {}
    for p in waiting_players:
        gid = p.participant.vars.get('intro_group_id')
        if gid is None:
            continue
        by_gid.setdefault(gid, []).append(p)

    # Check for each gid if all members of that intro group have arrived
    for gid, plist in by_gid.items():
        total_for_gid = sum(
            1 for part in session.get_participants()
            if part.vars.get('intro_group_id') == gid
        )
        if len(plist) == total_for_gid and total_for_gid > 0:
            # All members of this intro group have arrived -> form this group
            return plist

    # Otherwise, wait until enough players with the same intro_group_id arrive
    return


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
    # Ensure this round is initialized (role, lottery parameters, sample)
    player.initialize_round()

    context = dict()

    # Sort the lottery
    current_sorted_lottery = sort_lottery(
        create_lottery(
            q=player.mid_probability,
            x=player.max_payoff,
        )
    )
    sorted_payoffs, sorted_probs = zip(*current_sorted_lottery)

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
    Works for:
    - 1 seller + 1 buyer
    - 2 sellers + 1 buyer
    - 2 sellers + 2 buyers
    """
    # Ensure all players in the group are initialized for this round
    for p in player.group.get_players():
        p.initialize_round()

    group = player.group
    sellers = [p for p in group.get_players() if p.player_role == 'seller']
    sellers.sort(key=lambda p: p.seller_index)

    if len(sellers) not in [1, 2]:
        raise Exception("Each group must contain 1 or 2 sellers.")

    # Compute and set group_type each time
    n_sellers = len(sellers)
    n_buyers = sum(1 for pl in group.get_players() if pl.player_role == 'buyer')
    group.group_type = f"{n_sellers}S{n_buyers}B"

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
    # Ensure all players in the group are initialized for this round
    for p in group.get_players():
        p.initialize_round()

    players = group.get_players()
    sellers = [p for p in players if p.player_role == 'seller']
    sellers.sort(key=lambda p: p.seller_index)
    buyers = [p for p in players if p.player_role == 'buyer']
    buyers.sort(key=lambda p: p.buyer_index)

    if len(sellers) not in [1, 2]:
        raise Exception("Each group must contain 1 or 2 sellers.")

    if len(buyers) not in [1, 2]:
        raise Exception("Each group must contain 1 or 2 buyers.")

    # Lowest price across all sellers (outside option for buyers who do not buy)
    lowest_price = min(s.selling_price_lottery for s in sellers)

    # Reset seller fields
    for s in sellers:
        s.sold = False
        s.lottery_outcome = Currency(0)

    # Handle each buyer
    for b in buyers:
        choice = b.chosen_lottery_from_seller

        b.outside_option_value = lowest_price
        b.bought_lottery = False
        b.chosen_seller_index = 0
        b.buyer_lottery_outcome = Currency(0)

        if choice == 'none' or choice is None:
            # Outside option
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

            # Mark seller as having sold (at least once)
            chosen_seller.sold = True
            # Store last observed outcome on seller level (for feedback)
            chosen_seller.lottery_outcome = outcome

    # Set seller payoffs: price if sold at least once, 0 otherwise
    for s in sellers:
        if s.sold:
            s.payoff = s.selling_price_lottery
        else:
            s.payoff = Currency(0)


# --- PAGES ------------------------------------------------------------------


class GroupingWaitPage(WaitPage):
    """
    In round 1: reconstruct groups using intro_group_id from the Introduction app.
    In later rounds: not displayed.
    """
    group_by_arrival_time = True

    @staticmethod
    def is_displayed(player: Player):
        return player.round_number == 1

    @staticmethod
    def after_all_players_arrive(group: Group):
        """
        Once a group is formed and everyone in that group arrived at this page,
        set group_type based on the number of sellers and buyers.
        """
        players_in_group = group.get_players()
        sellers = [p for p in players_in_group if p.participant.vars.get('player_role') == 'seller']
        buyers = [p for p in players_in_group if p.participant.vars.get('player_role') == 'buyer']
        group.group_type = f"{len(sellers)}S{len(buyers)}B"


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
    All sellers use this page, independent of group type.
    No time limit and no automatic randomization on non-response.
    """
    form_fields = ['chosen_lottery', 'justified_lottery', 'presentation_order']

    @staticmethod
    def is_displayed(player: Player):
        player.initialize_round()
        return player.player_role == 'seller'

    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        """
        Map the participant's chosen presentation label to the actual
        presentation ID defined by presentation_order.
        No automatic randomization is applied anymore.
        """
        player.initialize_round()

        # If no presentation order was stored, use a default order
        if not player.presentation_order:
            # Assumption: four presentations, identity order
            player.presentation_order = '1,2,3,4'

        order_list = player.presentation_order.split(',') if player.presentation_order else []

        # Map the participant's choice to the actual presentation ID
        if player.chosen_lottery and order_list:
            try:
                # Extract the chosen presentation number from 'Präsentation N'
                choice_number = int(player.chosen_lottery.split(' ')[1]) - 1  # 0-based index
                player.chosen_presentation_id = order_list[choice_number]
            except Exception:
                # Fallback if something goes wrong
                player.chosen_presentation_id = order_list[0]
        else:
            # Fallback if something is missing; no randomization
            if order_list:
                player.chosen_presentation_id = order_list[0]


class SellerDecision(LotteryDecisionBase):
    """
    Seller states price and belief for her lottery.
    Shown to all sellers, independent of group type.
    No time limit and no automatic randomization on non-response.
    """
    form_fields = ['selling_price_lottery', 'belief_sequence', 'belief']

    @staticmethod
    def is_displayed(player: Player):
        player.initialize_round()
        return player.player_role == 'seller'

    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        """
        Ensure basic consistency of the price.
        No automatic randomization is applied; invalid prices can be
        clamped into [1, max_payoff] if needed.
        """
        player.initialize_round()

        if player.selling_price_lottery is not None:
            # Clamp price into [1, max_payoff] without randomization
            if player.selling_price_lottery < 1:
                player.selling_price_lottery = cu(1)
            elif player.selling_price_lottery > player.max_payoff:
                player.selling_price_lottery = cu(player.max_payoff)


class WaitForSellers(WaitPage):
    """
    Wait until all sellers in each group have chosen their presentations
    and set price + belief, before showing the buyers' page.

    All players in the group pass through this page, as in the working version.
    Buyers effectively "wait for the sellers", sellers typically pass quickly.
    """
    wait_for_all_groups = False  # group-wise is enough


class BuyerDecision(Page):
    """
    Buyer chooses beliefs about one or two lotteries and
    then chooses whether to buy from seller 1, seller 2 (if exists),
    or not to buy a lottery (outside option).
    No time limit and no automatic randomization on non-response.
    """
    form_model = 'player'

    @staticmethod
    def is_displayed(player: Player):
        player.initialize_round()
        return player.player_role == 'buyer'

    @staticmethod
    def get_form_fields(player: Player):
        group = player.group
        # Ensure roles are loaded for group members
        for p in group.get_players():
            p.initialize_round()

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

    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        """
        No automatic randomization is applied anymore.
        Auto flags remain in the data but are not used.
        """
        player.auto_buyer_beliefs = False
        player.auto_buyer_choice = False


class WaitForBuyerAndSetResults(WaitPage):
    """
    After all buyers in each group submitted their choices,
    compute trades & outcomes.
    """
    wait_for_all_groups = False

    @staticmethod
    def after_all_players_arrive(group: Group):
        set_trade_and_outcomes(group)


class SellerFeedback(Page):
    """
    Feedback for sellers:
    - whether their lottery was bought by at least one buyer
    - own price
    - (last) outcome drawn among buyers who purchased
    No time limit.
    """

    @staticmethod
    def is_displayed(player: Player):
        player.initialize_round()
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
    - if no: outside option (lowest price among sellers)
    No time limit.
    """

    @staticmethod
    def is_displayed(player: Player):
        player.initialize_round()
        return player.player_role == 'buyer'

    @staticmethod
    def vars_for_template(player: Player):
        return dict(
            bought_lottery=player.bought_lottery,
            chosen_seller_index=player.chosen_seller_index,
            lottery_outcome=player.buyer_lottery_outcome,
            outside_option_value=player.outside_option_value,
        )


page_sequence = [
    # Reconstruct groups in round 1 using intro_group_id
    GroupingWaitPage,
    # sellers choose how to present the lottery (SAMPLE_CENSORING-style)
    Lottery_decision,
    # sellers set price & belief
    SellerDecision,
    # wait until all sellers are done (group-wise)
    WaitForSellers,
    # buyers: beliefs + choice of lottery / outside option
    BuyerDecision,
    # compute trades & lottery outcomes
    WaitForBuyerAndSetResults,
    # feedback for sellers and buyers
    SellerFeedback,
    BuyerFeedback,
]

