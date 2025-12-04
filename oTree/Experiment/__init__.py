from otree.api import *

import json
import random

"""
Main interaction app:
- Roles ('seller' or 'buyer') are assigned in the introduction app and
  stay fixed for all 10 rounds.
- In EACH round, new groups of type 2S1B (2 sellers, 1 buyer) are formed
  dynamically from the pool of players via group_by_arrival_time.
- There is no persistent grouping across rounds anymore.
- At the end of each round, all players wait for each other before
  proceeding to the next round, so that regrouping uses the entire pool.
- Sellers always have SAMPLE_CENSORING-style options (4 presentations).
- Buyers see the sellers' lotteries including prices and choose:
    * buy lottery from seller 1
    * buy lottery from seller 2
    * buy no lottery (outside option)
- Each buyer can buy at most one lottery.
- Seller payoff: price of the lottery if (at least) one buyer buys, 0 otherwise.
- Buyer payoff:
    * if they buy a lottery: outcome of that lottery
    * if they do not buy: lowest price offered by any seller in the group.
"""


class C(BaseConstants):
    NAME_IN_URL = 'main_experiment'
    PLAYERS_PER_GROUP = None  # variable group sizes through dynamic grouping (2S1B)

    # CHANGED: number of rounds increased from 5 to 10
    # EN: The experiment now runs for 10 rounds instead of 5.
    NUM_ROUNDS = 10

    # General intro parameters (not used in grouping logic)
    N_LOTTERIES = 10
    TIME_TO_FINISH = 15  # minutes
    BASE_PAY = 6  # in euro
    EXCHANGE_RATE = 13

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
    No special logic in creating_session, because roles are formed in the
    introduction app. In this app, groups of type 2S1B are formed dynamically
    in each round via group_by_arrival_time.
    """
    pass


class Group(BaseGroup):
    """
    Group-level fields mainly for storing meta information.
    """
    group_type = models.StringField()  # e.g. '2S1B'


class Player(BasePlayer):
    # --- role & indices ------------------------------------------------------

    # 'seller' or 'buyer'; assigned in introduction and kept fixed over rounds
    player_role = models.StringField()
    # index within role in the *current group* (1 or 2 for sellers, 1 for buyers)
    seller_index = models.IntegerField(initial=0)
    buyer_index = models.IntegerField(initial=0)

    # --- lottery parameters (per round, for everyone's "own" lottery) -------
    # Für Buyer werden hier nur Defaults gesetzt, die nicht verwendet werden.
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

    # EN: Text justification for the chosen lottery presentation.
    #     It will only be asked in round 1 (see Lottery_decision.get_form_fields).
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

    # --- bonus payment tracking ---------------------------------------------

    # NEW: per-round bonus payment
    # EN: Stores the bonus payment earned in this round for each player.
    bonus_payment = models.CurrencyField(initial=0)

    # NEW: total bonus payment across all rounds
    # EN: After the last round, this field stores the sum of all per-round bonus payments.
    total_bonus_payment = models.CurrencyField(initial=0)

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

        Wird ausschließlich für Seller aufgerufen.
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
        - role is loaded from participant.vars (determined in introduction app)
        - lottery parameters are set ONLY for sellers
        - sellers draw their sample (once per round)

        Buyers do not get their own lottery and no sample draws.
        The fields max_payoff/mid_probability are only set to harmless
        default values for buyers to keep the model consistent.

        EN (lottery sequence logic):
        - We have 5 different high payoffs and 5 different mid probabilities.
        - There are 10 rounds.
        - Rounds 1–5: generated "as before":
            * Take a copy of MAX_PAYOFF_STATES, shuffle it.
            * Take a copy of MID_PROBABILITIES, shuffle it independently.
            * Zip the 2 shuffled lists to get 5 random (x, q) pairs.
        - Rounds 6–10: RESET and do the same again for a new block of 5 rounds.
        - Technically, we construct blocks of length 5 using this procedure
          and concatenate the blocks to obtain a sequence of length 10.
        """
        if self.round_initialized:
            return

        participant = self.participant

        # Load role from participant.vars (role is fixed across all rounds)
        self.player_role = participant.vars.get('player_role')

        # --- Build / ensure the per-round lottery parameter sequence --------
        combos = participant.vars.get('payoff_probability_combinations')

        # EN:
        # We expect a list of (max_payoff, mid_prob) pairs of length C.NUM_ROUNDS.
        # If it is missing or has the wrong length (e.g., only 5 from the intro app),
        # we (re)create it here using the "blockwise, independently shuffled" rule.
        if not combos or len(combos) != C.NUM_ROUNDS:

            full_sequence = []

            block_size = len(C.MAX_PAYOFF_STATES)  # should be 5
            n_blocks = C.NUM_ROUNDS // block_size
            remainder = C.NUM_ROUNDS % block_size

            # EN:
            # For each full block:
            # - shuffle MAX_PAYOFF_STATES independently of MID_PROBABILITIES
            # - zip the shuffled lists to get random (x, q) pairs
            for _ in range(n_blocks):
                max_states = C.MAX_PAYOFF_STATES.copy()
                mid_probs = C.MID_PROBABILITIES.copy()
                random.shuffle(max_states)
                random.shuffle(mid_probs)
                block = list(zip(max_states, mid_probs))
                full_sequence.extend(block)

            # EN:
            # If NUM_ROUNDS is not a multiple of 5, add a partial block.
            # (Not needed for 10 rounds, but kept general.)
            if remainder:
                max_states = C.MAX_PAYOFF_STATES.copy()
                mid_probs = C.MID_PROBABILITIES.copy()
                random.shuffle(max_states)
                random.shuffle(mid_probs)
                block = list(zip(max_states, mid_probs))
                full_sequence.extend(block[:remainder])

            combos = full_sequence
            participant.vars['payoff_probability_combinations'] = combos

        # Pick the combination for THIS round (1-based round_number).
        max_payoff, mid_prob = combos[self.round_number - 1]

        if self.player_role == 'seller':
            # EN: Sellers get their own lottery and sample draw.
            self.max_payoff = max_payoff
            self.mid_probability = mid_prob
            self.draw_sample()
        else:
            # EN: Buyers do not have their own lottery.
            # We only set benign default values that are never used.
            self.max_payoff = 0
            self.mid_probability = 0.0

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
    - Roles are assigned in the introduction app and stored in participant.vars['player_role'].
    - In every round, grouping is done dynamically via group_by_arrival_time
      to form 2S1B groups from the pool of sellers and buyers.
    """
    pass


# --- dynamic grouping: always 2S1B, every round -----------------------------


def group_by_arrival_time_method(subsession: Subsession, waiting_players):
    """
    Called when a new player reaches the GroupingWaitPage in each round.

    We dynamically form 2S1B groups (2 sellers, 1 buyer) based on roles
    stored in participant.vars['player_role'].

    Logic:
    - Among waiting_players, we check if there are at least 2 sellers
      and at least 1 buyer.
    - If yes, we form a group from the earliest-arrived players that can
      make up exactly 2 sellers and 1 buyer.
    - Roles are fixed across rounds; we do NOT change participant.vars here.
    """
    # Separate waiting players by role (from participant.vars, which is fixed)
    sellers_waiting = [p for p in waiting_players if p.participant.vars.get('player_role') == 'seller']
    buyers_waiting = [p for p in waiting_players if p.participant.vars.get('player_role') == 'buyer']

    if len(sellers_waiting) < 2 or len(buyers_waiting) < 1:
        # Not enough players yet to form a 2S1B group
        return

    group_players = []
    seller_needed = 2
    buyer_needed = 1

    # Go through waiting_players in arrival order and pick the first 2 sellers and 1 buyer
    for p in waiting_players:
        role = p.participant.vars.get('player_role')
        if role == 'seller' and seller_needed > 0:
            group_players.append(p)
            seller_needed -= 1
        elif role == 'buyer' and buyer_needed > 0:
            group_players.append(p)
            buyer_needed -= 1

        if seller_needed == 0 and buyer_needed == 0:
            break

    if seller_needed == 0 and buyer_needed == 0:
        # Assign model-level roles and indices for THIS round's group
        seller_index = 0
        buyer_index = 0
        for p in group_players:
            p.player_role = p.participant.vars.get('player_role')
            if p.player_role == 'seller':
                seller_index += 1
                p.seller_index = seller_index
            else:
                buyer_index += 1
                p.buyer_index = buyer_index
        return group_players

    # Otherwise: wait for more players
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
    - 2 sellers + 1 buyer (only group type used here).
    """
    # Ensure all players in the group are initialized for this round
    for p in player.group.get_players():
        p.initialize_round()

    group = player.group
    sellers = [p for p in group.get_players() if p.player_role == 'seller']
    sellers.sort(key=lambda p: p.seller_index)

    if len(sellers) != 2:
        raise Exception("Each group must contain exactly 2 sellers in this design.")

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

    NEW (bonus logic):
    - For each player, bonus_payment is set equal to the payoff in that round.
    - In the last round, total_bonus_payment is computed as the sum of
      bonus_payment across all rounds for that player.
    """
    # Ensure all players in the group are initialized for this round
    for p in group.get_players():
        p.initialize_round()

    players = group.get_players()
    sellers = [p for p in players if p.player_role == 'seller']
    sellers.sort(key=lambda p: p.seller_index)
    buyers = [p for p in players if p.player_role == 'buyer']
    buyers.sort(key=lambda p: p.buyer_index)

    if len(sellers) != 2:
        raise Exception("Each group must contain exactly 2 sellers in this design.")

    if len(buyers) != 1:
        raise Exception("Each group must contain exactly 1 buyer in this design.")

    # Lowest price across all sellers (outside option for buyers who do not buy)
    lowest_price = min(s.selling_price_lottery for s in sellers)

    # Reset seller fields
    for s in sellers:
        s.sold = False
        s.lottery_outcome = Currency(0)

    # Handle each buyer (here exactly one)
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
                chosen_seller = sellers[0]
            elif choice == 'seller2':
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

    # NEW: store bonus payment per round and compute running total each round
    # EN: We interpret the round's payoff as the bonus payment and store it.
    for p in players:
        p.bonus_payment = p.payoff

    # EN: After every round, compute the cumulative total bonus across all rounds so far.
    #     This means total_bonus_payment in round t equals the sum of bonus_payment from
    #     rounds 1..t for that participant.
    for p in players:
        total = sum(r.bonus_payment for r in p.in_all_rounds())
        p.total_bonus_payment = total


# --- PAGES ------------------------------------------------------------------


class GroupingWaitPage(WaitPage):
    """
    In every round: form new 2S1B groups dynamically from the pool
    of sellers and buyers using group_by_arrival_time.
    """
    group_by_arrival_time = True

    @staticmethod
    def after_all_players_arrive(group: Group):
        """
        Once a group is formed and everyone in that group arrived at this page,
        set group_type based on the number of sellers and buyers.
        (Should always be '2S1B' here.)
        """
        players_in_group = group.get_players()
        sellers = [p for p in players_in_group if p.player_role == 'seller']
        buyers = [p for p in players_in_group if p.player_role == 'buyer']
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
    All sellers use this page, independent of group type (always 2S1B here).
    No time limit and no automatic randomization on non-response.

    CHANGED:
    - The lottery justification (justified_lottery) is now only asked in round 1.
      In later rounds, sellers choose the presentation without giving a justification.
    """

    # CHANGED: we now dynamically choose form fields depending on the round
    # (instead of a fixed 'form_fields' list).
    @staticmethod
    def get_form_fields(player: Player):
        """
        EN:
        - In round 1, we ask for:
            chosen_lottery, justified_lottery, presentation_order.
        - In rounds 2–10, we only ask for:
            chosen_lottery, presentation_order.
        """
        fields = ['chosen_lottery', 'presentation_order']
        if player.round_number == 1:
            # Insert justification between choice and order for nicer display order
            fields.insert(1, 'justified_lottery')
        return fields

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

    All players in the group pass through this page.
    """
    wait_for_all_groups = False  # group-wise is enough


class BuyerDecision(Page):
    """
    Buyer chooses beliefs about the two lotteries and
    then chooses whether to buy from seller 1, seller 2,
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


class RoundTransitionWaitPage(WaitPage):
    """
    At the end of each round, wait for ALL players in the session
    before proceeding to the next round. This ensures that the dynamic
    regrouping in the next round uses the full pool of participants.
    """
    wait_for_all_groups = True

    @staticmethod
    def is_displayed(player: Player):
        # Can be shown in every round (also in the last round it just ends).
        return True


page_sequence = [
    # In every round: form new 2S1B groups dynamically
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
    # end-of-round global wait, so next round's grouping uses full pool
    RoundTransitionWaitPage,
]

