from otree.api import *

import json
import random

"""
Main interaction app:

- Participants are pre-assigned roles ('seller' or 'buyer') in the
  introduction app and this role stays fixed for all 10 rounds.

- In EACH round, players are newly matched across the complete session
  into groups of size 2:
    * 1 seller
    * 1 buyer

- There are no fixed matching groups anymore.
  Every round uses the full pool of sellers and buyers in the session.

- There is no group_by_arrival_time anymore. Grouping is done in
  creating_session for each round.

- At the end of each round, all players wait for each other before
  proceeding to the next round, so that regrouping in the next round
  uses the entire session.

- Sellers always have SAMPLE_CENSORING-style options (4 presentations).
- Buyers see the seller's lottery including the price and choose:
    * buy the lottery
    * buy no lottery (outside option)

- Each buyer can buy at most one lottery.

- Seller payoff:
    * seller endowment + price of the lottery if sold
    * seller endowment if not sold
- Buyer payoff:
    * if they buy a lottery: endowment - price + outcome of that lottery
    * if they do not buy: endowment

- All rounds count toward the total bonus.
- bonus_payment stores the round-specific bonus in euros.
- total_bonus_payment stores the sum of all round bonuses in euros.
"""


class C(BaseConstants):
    NAME_IN_URL = 'main_experiment_1s1b'

    # Groups in the experiment are always 1 seller + 1 buyer.
    PLAYERS_PER_GROUP = 2

    # The experiment runs for 10 rounds.
    NUM_ROUNDS = 10

    # General intro parameters (not used in grouping logic)
    N_LOTTERIES = 10
    TIME_TO_FINISH = 45  # minutes
    BASE_PAY = 6  # in euro
    EXCHANGE_RATE = 100

    # Buyer and seller endowments / outside option and fixed price cap
    BUYER_ENDOWMENT = 100
    SELLER_ENDOWMENT = 50
    MAX_PRICE = 100

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
    No special logic in the model itself. Grouping logic is implemented
    in the module-level creating_session function.

    Design:
    - In each round, the entire session is rematched into 1S1B groups.
    - Roles remain fixed over rounds and come from the introduction app.
    """
    pass


class Group(BaseGroup):
    """
    Group-level fields mainly for storing meta information.
    """
    group_type = models.StringField(initial="1S1B")


class Player(BasePlayer):
    # --- role & indices ------------------------------------------------------

    # 'seller' or 'buyer'; assigned in introduction and kept fixed over rounds
    player_role = models.StringField()

    # index within role in the current group (always 1 in 1S1B)
    seller_index = models.IntegerField(initial=0)
    buyer_index = models.IntegerField(initial=0)

    # --- lottery parameters (per round, for everyone's "own" lottery) -------
    # For buyers, only default values are set here, which are not used.
    max_payoff = models.IntegerField()
    mid_probability = models.FloatField()

    # Flag to ensure one-time initialization per round
    round_initialized = models.BooleanField(initial=False)

    # --- seller-specific fields ---------------------------------------------

    # price for the seller's lottery must be between 1 and 100
    selling_price_lottery = models.CurrencyField(label="", min=1, max=C.MAX_PRICE)

    # belief about highest payoff state (second-order belief about buyers)
    belief = models.IntegerField(label="")
    belief_sequence = models.LongStringField(blank=True)

    # raw sample and displayed subsample (always used, SAMPLE_CENSORING-style)
    all_draws = models.LongStringField()
    subsample = models.LongStringField()

    # lottery presentation choice
    presentation_order = models.StringField()
    chosen_presentation_id = models.StringField()

    chosen_lottery = models.StringField(
        choices=C.LOTTERY_CHOICES,
        label="",
    )

    # Text justification for the chosen lottery presentation.
    # It will only be asked in round 1 (see Lottery_decision.get_form_fields).
    justified_lottery = models.LongStringField(label="")

    # feedback for sellers
    sold = models.BooleanField(blank=True)
    lottery_outcome = models.CurrencyField()

    # --- buyer-specific fields ----------------------------------------------

    # belief about the seller's lottery (0–100 out of 100 plays)
    buyer_belief_seller1 = models.IntegerField(label="", blank=True)
    buyer_belief_sequence_seller1 = models.LongStringField(blank=True)

    # choice: 'seller1' or 'none'
    chosen_lottery_from_seller = models.StringField(
        choices=[
            ['seller1', 'Buy lottery'],
            ['none', 'Do not buy a lottery (outside option)'],
        ],
        label="",
    )

    # feedback for buyers
    bought_lottery = models.BooleanField(initial=False)
    chosen_seller_index = models.IntegerField(initial=0)
    chosen_lottery_price = models.CurrencyField(initial=0)
    buyer_lottery_outcome = models.CurrencyField()
    outside_option_value = models.CurrencyField()

    # --- flags for automatic (timeout-based) decisions -----------------------
    # These flags remain in the dataset for compatibility, but are no longer
    # used to generate automatic decisions (no timeouts are enforced now).
    auto_lottery_decision = models.BooleanField(blank=True)
    auto_seller_decision = models.BooleanField(blank=True)
    auto_buyer_beliefs = models.BooleanField(blank=True)
    auto_buyer_choice = models.BooleanField(blank=True)

    # --- bonus payment tracking ---------------------------------------------

    # Kept for compatibility in the data export. Since all rounds are
    # bonus-relevant again, this field is not used for payment logic.
    paid_lottery_round = models.IntegerField(initial=0)

    # Stores the bonus payment of the current round in euros.
    bonus_payment = models.FloatField(initial=0)

    # Stores the sum of bonus payments across all rounds in euros.
    total_bonus_payment = models.FloatField(initial=0)

    # Full payment including participation fee
    payoff_plus_participation_fee = models.FloatField(initial=0)

    # --- helper methods ------------------------------------------------------

    def selling_price_lottery_max(self):
        """
        Maximum possible price is fixed at 100.
        """
        return C.MAX_PRICE

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

        This is only called for sellers.
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

        Lottery sequence logic:
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

        # Kept for compatibility in data export; no paid-round logic is used.
        self.paid_lottery_round = 0

        # --- Build / ensure the per-round lottery parameter sequence --------
        combos = participant.vars.get('payoff_probability_combinations')

        # We expect a list of (max_payoff, mid_prob) pairs of length C.NUM_ROUNDS.
        # If it is missing or has the wrong length (e.g., only 5 from the intro app),
        # we (re)create it here using the "blockwise, independently shuffled" rule.
        if not combos or len(combos) != C.NUM_ROUNDS:

            full_sequence = []

            block_size = len(C.MAX_PAYOFF_STATES)  # should be 5
            n_blocks = C.NUM_ROUNDS // block_size
            remainder = C.NUM_ROUNDS % block_size

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

            # If NUM_ROUNDS is not a multiple of 5, add a partial block.
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
            # Sellers get their own lottery and sample draw.
            self.max_payoff = max_payoff
            self.mid_probability = mid_prob
            self.draw_sample()
        else:
            # Buyers do not have their own lottery.
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


# --- session creation & grouping --------------------------------------------


def _create_groups_for_full_session(subsession: Subsession):
    """
    Create 1S1B groups using the full session pool.

    In every round:
    - collect all sellers in the session
    - collect all buyers in the session
    - shuffle sellers and buyers separately
    - pair seller[i] with buyer[i]

    Requirement:
    - the session must contain exactly as many sellers as buyers
    """
    players = subsession.get_players()

    sellers = [p for p in players if p.participant.vars.get('player_role') == 'seller']
    buyers = [p for p in players if p.participant.vars.get('player_role') == 'buyer']

    if len(sellers) != len(buyers):
        raise Exception(
            "The session must contain exactly as many sellers as buyers "
            f"for 1S1B matching. Found {len(sellers)} sellers and {len(buyers)} buyers."
        )

    random.shuffle(sellers)
    random.shuffle(buyers)

    group_matrix = []
    for seller, buyer in zip(sellers, buyers):
        group_matrix.append([seller, buyer])

    subsession.set_group_matrix(group_matrix)

    # Set model-level role information and indices for this round
    for group in subsession.get_groups():
        for p in group.get_players():
            p.player_role = p.participant.vars.get('player_role')
            if p.player_role == 'seller':
                p.seller_index = 1
                p.buyer_index = 0
            elif p.player_role == 'buyer':
                p.buyer_index = 1
                p.seller_index = 0
        group.group_type = "1S1B"


def creating_session(subsession: Subsession):
    """
    Grouping logic for the entire app.

    In every round:
        - Reuse the fixed role from participant.vars['player_role'].
        - Form new 1S1B groups using the complete session pool.
        - There are no fixed matching groups anymore.

    Requirement:
        - The total number of sellers must equal the total number of buyers.
    """
    players = subsession.get_players()
    sellers = [p for p in players if p.participant.vars.get('player_role') == 'seller']
    buyers = [p for p in players if p.participant.vars.get('player_role') == 'buyer']

    if len(sellers) != len(buyers):
        raise Exception(
            "The session must contain exactly as many sellers as buyers "
            f"for 1S1B matching. Found {len(sellers)} sellers and {len(buyers)} buyers."
        )

    subsession.session.vars['group_type_value'] = "1S1B"

    _create_groups_for_full_session(subsession)


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
    Build context dict for the buyer showing the seller's lottery in the group.
    Works for:
    - 1 seller + 1 buyer
    """
    # Ensure all players in the group are initialized for this round
    for p in player.group.get_players():
        p.initialize_round()

    group = player.group
    sellers = [p for p in group.get_players() if p.player_role == 'seller']
    sellers.sort(key=lambda p: p.seller_index)

    if len(sellers) != 1:
        raise Exception("Each group must contain exactly 1 seller in this design.")

    seller = sellers[0]

    lottery_sorted = sort_lottery(
        create_lottery(q=seller.mid_probability, x=seller.max_payoff)
    )
    payoffs, probs = zip(*lottery_sorted)
    prob_low, prob_mid, prob_high = probs
    prob_upper_joint = prob_mid + prob_high

    group.group_type = "1S1B"

    context = dict(
        n_sellers=1,
        sellers=[
            dict(
                seller_index=seller.seller_index,
                payoff_low=payoffs[0],
                payoff_mid=payoffs[1],
                payoff_high=payoffs[2],
                prob_low=int(round(prob_low * 100)),
                prob_mid=int(round(prob_mid * 100)),
                prob_high=int(round(prob_high * 100)),
                prob_upper_joint=int(round(prob_upper_joint * 100)),
                presentation_id=seller.chosen_presentation_id,
                subsample=seller.get_subsample(),
                price=seller.selling_price_lottery,
            )
        ],
        group_type=group.group_type,
    )

    context.update(player.get_general_instruction_vars())
    return context


# --- group-level payoff & feedback logic -----------------------------------


def set_trade_and_outcomes(group: Group):
    """
    For each group:
    - read seller and buyer
    - buyer chooses whether to buy from the seller or not
    - if buyer buys: draw lottery outcome for that buyer
    - seller payoff:
        * seller endowment + price if sold
        * seller endowment if not sold
    - buyer payoff:
        * if they buy a lottery: endowment - price + outcome
        * otherwise: endowment

    Bonus logic:
    - All rounds are bonus-relevant.
    - bonus_payment is set in every round to payoff / exchange rate.
    - total_bonus_payment is the sum across all rounds.
    """
    # Ensure all players in the group are initialized for this round
    for p in group.get_players():
        p.initialize_round()

    players = group.get_players()
    sellers = [p for p in players if p.player_role == 'seller']
    buyers = [p for p in players if p.player_role == 'buyer']

    if len(sellers) != 1:
        raise Exception("Each group must contain exactly 1 seller in this design.")

    if len(buyers) != 1:
        raise Exception("Each group must contain exactly 1 buyer in this design.")

    seller = sellers[0]
    buyer = buyers[0]

    outside_option = cu(C.BUYER_ENDOWMENT)
    seller_endowment = cu(C.SELLER_ENDOWMENT)

    # Reset fields
    seller.sold = False
    seller.lottery_outcome = cu(0)

    buyer.outside_option_value = outside_option
    buyer.bought_lottery = False
    buyer.chosen_seller_index = 0
    buyer.chosen_lottery_price = cu(0)
    buyer.buyer_lottery_outcome = cu(0)

    choice = buyer.chosen_lottery_from_seller

    if choice == 'seller1':
        outcome = draw_lottery_outcome(
            seller.mid_probability,
            seller.max_payoff,
        )

        buyer.bought_lottery = True
        buyer.chosen_seller_index = seller.seller_index
        buyer.chosen_lottery_price = seller.selling_price_lottery
        buyer.buyer_lottery_outcome = cu(outcome)
        buyer.payoff = outside_option - seller.selling_price_lottery + cu(outcome)

        seller.sold = True
        seller.lottery_outcome = cu(outcome)
        seller.payoff = seller_endowment + seller.selling_price_lottery
    else:
        buyer.payoff = outside_option
        seller.payoff = seller_endowment

    # All rounds count toward bonus; store round bonus in euros.
    for p in players:
        p.bonus_payment = float(p.payoff) / C.EXCHANGE_RATE

    # total bonus equals the cumulative sum across all rounds.
    for p in players:
        total = sum(r.bonus_payment for r in p.in_all_rounds())
        p.total_bonus_payment = total

        # Store final payout incl. participation fee after round 10
        if p.round_number == C.NUM_ROUNDS:
            p.payoff_plus_participation_fee = C.BASE_PAY + p.total_bonus_payment
            p.participant.vars['payoff_plus_participation_fee'] = p.payoff_plus_participation_fee


# --- PAGES ------------------------------------------------------------------


class GroupingWaitPage(WaitPage):
    """
    In every round, groups already exist because grouping is done in creating_session.
    We here simply set group_type to a stable string '1S1B'.
    """
    wait_for_all_groups = True

    @staticmethod
    def after_all_players_arrive(subsession: Subsession):
        group_type_value = subsession.session.vars.get('group_type_value', "1S1B")
        for g in subsession.get_groups():
            g.group_type = group_type_value


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
    No time limit and no automatic randomization on non-response.

    The lottery justification (justified_lottery) is only asked in round 1.
    In later rounds, sellers choose the presentation without giving a justification.
    """

    @staticmethod
    def get_form_fields(player: Player):
        """
        - In round 1, we ask for:
            chosen_lottery, justified_lottery, presentation_order.
        - In rounds 2–10, we only ask for:
            chosen_lottery, presentation_order.
        """
        fields = ['chosen_lottery', 'presentation_order']
        if player.round_number == 1:
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
                choice_number = int(player.chosen_lottery.split(' ')[1]) - 1
                player.chosen_presentation_id = order_list[choice_number]
            except Exception:
                player.chosen_presentation_id = order_list[0]
        else:
            if order_list:
                player.chosen_presentation_id = order_list[0]


class SellerDecision(LotteryDecisionBase):
    """
    Seller states price and belief for her lottery.
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
        clamped into [1, 100] if needed.
        """
        player.initialize_round()

        if player.selling_price_lottery is not None:
            if player.selling_price_lottery < 1:
                player.selling_price_lottery = cu(1)
            elif player.selling_price_lottery > C.MAX_PRICE:
                player.selling_price_lottery = cu(C.MAX_PRICE)


class WaitForSellers(WaitPage):
    """
    Wait until all sellers in each group have chosen their presentations
    and set price + belief, before showing the buyers' page.

    All players in the group pass through this page.
    """
    wait_for_all_groups = False


class BuyerDecision(Page):
    """
    Buyer chooses belief about the seller's lottery and
    then chooses whether to buy it or not.
    No time limit and no automatic randomization on non-response.
    """
    form_model = 'player'

    @staticmethod
    def is_displayed(player: Player):
        player.initialize_round()
        return player.player_role == 'buyer'

    @staticmethod
    def get_form_fields(player: Player):
        return [
            'buyer_belief_sequence_seller1',
            'buyer_belief_seller1',
            'chosen_lottery_from_seller',
        ]

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
    - whether their lottery was bought
    - own price
    - outcome drawn if purchased
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
            paid_round='alle Runden',
            is_paid_round=True,
            round_payoff=player.payoff,
            round_bonus_euro=player.bonus_payment,
        )


class BuyerFeedback(Page):
    """
    Feedback for buyers:
    - whether they bought a lottery
    - if yes: seller index, price, and outcome
    - if no: outside option
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
            chosen_lottery_price=player.chosen_lottery_price,
            lottery_outcome=player.buyer_lottery_outcome,
            outside_option_value=player.outside_option_value,
            paid_round='alle Runden',
            is_paid_round=True,
            round_payoff=player.payoff,
            round_bonus_euro=player.bonus_payment,
        )


class RoundTransitionWaitPage(WaitPage):
    """
    At the end of each round, wait for ALL players in the session
    before proceeding to the next round. This ensures that the dynamic
    regrouping in the next round uses the full pool of participants
    from the whole session.
    """
    wait_for_all_groups = True

    @staticmethod
    def is_displayed(player: Player):
        return True


page_sequence = [
    # In every round: groups 1S1B are already formed in creating_session
    GroupingWaitPage,
    # sellers choose how to present the lottery
    Lottery_decision,
    # sellers set price & belief
    SellerDecision,
    # wait until seller in each group is done
    WaitForSellers,
    # buyer: belief + choice of lottery / outside option
    BuyerDecision,
    # compute trades & lottery outcomes
    WaitForBuyerAndSetResults,
    # feedback for seller and buyer
    SellerFeedback,
    BuyerFeedback,
    # end-of-round global wait, so next round's grouping uses full pool
    RoundTransitionWaitPage,
]