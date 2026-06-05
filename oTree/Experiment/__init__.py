from otree.api import *

import json
import random

"""
Main interaction app:

- Participants are pre-assigned roles ('seller' or 'buyer') in the
  introduction app and this role stays fixed for all 10 rounds.

- Participants are divided into fixed "matching groups" of size 15:
    * 10 sellers
    * 5 buyers
  These matching groups remain constant across all rounds.

  OR (small-session mode):

- Participants are divided into fixed "matching groups" of size 3:
    * 2 sellers
    * 1 buyer

- In EACH round:
    * if matching groups are size 15: within every matching group, we form 5 small groups of size 3 (2S1B)
    * if matching groups are size 3: each matching group is itself exactly one 2S1B group

  The composition of these 2S1B groups is newly randomized in every round,
  but always restricted to players within the same matching group.

- There is no group_by_arrival_time anymore. Grouping is done in
  creating_session for each round.

- At the end of each round, all players wait for each other before
  proceeding to the next round, so that regrouping uses the entire pool
  within each matching group.

- Sellers always have SAMPLE_CENSORING-style options (4 presentations).
- Buyers see the sellers' lotteries including prices and choose:
    * buy lottery from seller 1
    * buy lottery from seller 2
    * buy no lottery (outside option)

- Each buyer can buy at most one lottery.

NEW COIN LOGIC:
- Buyers receive 1000 coins ONCE in round 1.
- Sellers receive 750 coins ONCE in round 1.
- These coins are carried over across rounds as a running balance.

- Seller balance:
    * previous balance + price of the lottery if sold
    * previous balance if not sold
- Buyer balance:
    * if they buy a lottery: previous balance - price + outcome of that lottery
    * if they do not buy: previous balance

- Only the final balance at the end of round 10 is paid via oTree payoff.
- bonus_payment stores the round-specific balance change in euros for display/export.
- total_bonus_payment stores the current total balance converted into euros.
"""


class C(BaseConstants):
    NAME_IN_URL = 'main_experiment'

    # EN: Groups in the experiment are always 2 sellers + 1 buyer.
    #     Matching groups of size 15 (10S + 5B) or size 3 (2S + 1B) are handled in creating_session.
    PLAYERS_PER_GROUP = 3

    # EN: The experiment now runs for 10 rounds.
    NUM_ROUNDS = 10

    # General intro parameters (not used in grouping logic)
    N_LOTTERIES = 10
    TIME_TO_FINISH = 45  # minutes
    BASE_PAY = 6  # in euro
    EXCHANGE_RATE = 100

    # NEW: one-time initial endowments in round 1
    BUYER_INITIAL_ENDOWMENT = 1000
    SELLER_INITIAL_ENDOWMENT = 750
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


def map_shared_random_draws_to_lottery(shared_random_draws, mid_probability, max_payoff):
    """
    Convert one group-level sequence of random numbers into lottery outcomes
    for a specific seller's lottery.

    The same random numbers are used for both sellers in a 2S1B group.
    This means jackpot positions are identical for both sellers, because the
    jackpot probability is always 0.01. The jackpot value itself can still
    differ across sellers because it is seller.max_payoff.

    Mapping rule for each random number u in [0, 1):
    - u < 0.01                  -> jackpot payoff x
    - 0.01 <= u < 0.01 + q      -> middle payoff 10
    - otherwise                 -> payoff 0
    """
    outcomes = []
    jackpot_cutoff = 0.01
    middle_cutoff = 0.01 + mid_probability

    for u in shared_random_draws:
        if u < jackpot_cutoff:
            outcomes.append(max_payoff)
        elif u < middle_cutoff:
            outcomes.append(10)
        else:
            outcomes.append(0)

    return outcomes


def initialize_group_draws(group):
    """
    Generate the sample only once per 2S1B group and round.

    Instead of drawing a separate random sample for every seller, this function
    draws one shared group-level sequence of C.SAMPLE_SIZE random numbers.
    Each seller then maps that same sequence to her own lottery parameters.

    Consequence:
    - both sellers have jackpot outcomes at exactly the same draw positions;
    - therefore the SAMPLE_CENSORING subsample sorted by highest outcomes
      contains the same number of displayed jackpots for both sellers;
    - no seller has to be reduced to the smaller jackpot count afterwards.
    """
    # Do nothing if this group already received its shared sample in this round.
    if group.shared_draws_initialized:
        return

    # Initialize roles, balances and lottery parameters first. Important:
    # Player.initialize_round() no longer draws individual seller samples.
    for p in group.get_players():
        p.initialize_round()

    sellers = [p for p in group.get_players() if p.player_role == 'seller']
    sellers.sort(key=lambda p: p.seller_index)

    if len(sellers) != 2:
        raise Exception("Each group must contain exactly 2 sellers in this design.")

    # The only actual sample draw for the group in this round.
    shared_random_draws = [random.random() for _ in range(C.SAMPLE_SIZE)]
    group.set_shared_random_draws(shared_random_draws)

    for s in sellers:
        total_sample = map_shared_random_draws_to_lottery(
            shared_random_draws=shared_random_draws,
            mid_probability=s.mid_probability,
            max_payoff=s.max_payoff,
        )
        subsample = sorted(total_sample, reverse=True)[:C.DRAWS]

        # Keep seller-level fields populated for templates and data export.
        # These are not independently drawn samples; they are deterministic
        # mappings of the one group-level shared_random_draws sequence.
        s.set_all_draws(total_sample)
        s.set_subsample(subsample)

    group.shared_draws_initialized = True


# --- models -----------------------------------------------------------------


class Subsession(BaseSubsession):
    """
    No special logic in the model itself. Grouping logic is implemented
    in the module-level creating_session function.

    Design:
    - Fixed matching groups of size 15 (10 sellers, 5 buyers) OR size 3 (2 sellers, 1 buyer).
    - In each round, within each matching group, players are rematched into
      2S1B groups (or remain a single 2S1B group in the size-3 mode).
    """
    pass


class Group(BaseGroup):
    """
    Group-level fields mainly for storing meta information.
    """
    group_type = models.StringField(initial="2S1B")  # e.g. '2S1B'

    # NEW:
    # One shared random-number sequence per 2S1B group and round.
    # Sellers do not draw independent all_draws anymore; instead their
    # seller-level all_draws are deterministic mappings of this shared sequence.
    shared_random_draws = models.LongStringField(blank=True)
    shared_draws_initialized = models.BooleanField(initial=False)

    def set_shared_random_draws(self, x):
        self.shared_random_draws = json.dumps(x)

    def get_shared_random_draws(self):
        return json.loads(self.shared_random_draws)


class Player(BasePlayer):
    # --- role & indices ------------------------------------------------------

    # 'seller' or 'buyer'; assigned in introduction and kept fixed over rounds
    player_role = models.StringField()
    # index within role in the *current group* (1 or 2 for sellers, 1 for buyers)
    seller_index = models.IntegerField(blank=True)
    buyer_index = models.IntegerField(blank=True)

    # --- running balance fields ----------------------------------------------

    # balance at the start of the round
    starting_balance = models.CurrencyField(initial=0)

    # balance at the end of the round
    ending_balance = models.CurrencyField(initial=0)

    # --- lottery parameters (per round, for everyone's "own" lottery) -------
    # EN: For buyers, only default values are set here, which are not used.
    max_payoff = models.IntegerField()
    mid_probability = models.FloatField()

    # Flag to ensure one-time initialization per round
    round_initialized = models.BooleanField(initial=False)

    # --- seller-specific fields ---------------------------------------------

    # NEW: price for the seller's lottery must be between 1 and 100
    selling_price_lottery = models.CurrencyField(label="", min=1, max=C.MAX_PRICE)

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
    sold = models.BooleanField(blank=True)
    lottery_outcome = models.CurrencyField()

    # --- buyer-specific fields ----------------------------------------------

    # beliefs about the lotteries (if available)
    # belief about lottery from seller 1 (0–100 out of 100 plays)
    buyer_belief_seller1 = models.IntegerField(label="", blank=True)
    buyer_belief_sequence_seller1 = models.LongStringField(blank=True)

    # belief about lottery from seller 2 (only used if there is a second seller)
    buyer_belief_seller2 = models.IntegerField(label="", blank=True)
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
    bought_lottery = models.BooleanField(blank=True)
    chosen_seller_index = models.IntegerField(blank=True)
    chosen_lottery_price = models.CurrencyField(blank=True)
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

    # EN: Kept for compatibility in the data export. Since all rounds are
    # bonus-relevant again, this field is not used for payment logic.
    paid_lottery_round = models.IntegerField(initial=0)

    # EN: Stores the bonus payment of the current round in euros.
    bonus_payment = models.FloatField(initial=0)

    # EN: Stores the current total balance converted into euros.
    total_bonus_payment = models.FloatField(initial=0)

    # Full payment including participation fee
    payoff_plus_participation_fee = models.FloatField(initial=0)

    # --- helper methods ------------------------------------------------------

    def selling_price_lottery_max(self):
        """
        NEW: maximum possible price is fixed at 100.
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

    def draw_sample_from_shared_random_draws(self, shared_random_draws):
        """
        Build this seller's all_draws and displayed subsample from the
        group-level shared random-number sequence.

        This method does NOT draw random numbers itself. The actual draw happens
        once per group in initialize_group_draws(group).
        """
        total_sample = map_shared_random_draws_to_lottery(
            shared_random_draws=shared_random_draws,
            mid_probability=self.mid_probability,
            max_payoff=self.max_payoff,
        )
        subsample = sorted(total_sample, reverse=True)[:C.DRAWS]

        self.set_all_draws(total_sample)
        self.set_subsample(subsample)

    def initialize_round(self):
        """
        Ensure that in every round:
        - role is loaded from participant.vars (determined in introduction app)
        - starting / ending balance is initialized
        - lottery parameters are set ONLY for sellers
        - sellers do not draw individual samples; samples are created once per group

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

        Balance logic:
        - Round 1:
            * buyers start with 1000 coins
            * sellers start with 750 coins
        - From round 2 onwards:
            * starting_balance equals previous round's ending_balance
        """
        if self.round_initialized:
            return

        participant = self.participant

        # Load role from participant.vars (role is fixed across all rounds)
        self.player_role = participant.vars.get('player_role')

        # EN: Kept for compatibility in data export; no paid-round logic is used.
        self.paid_lottery_round = 0

        # --- Initialize running balance --------------------------------------
        if self.round_number == 1:
            if self.player_role == 'buyer':
                self.starting_balance = cu(C.BUYER_INITIAL_ENDOWMENT)
            elif self.player_role == 'seller':
                self.starting_balance = cu(C.SELLER_INITIAL_ENDOWMENT)
            else:
                self.starting_balance = cu(0)
        else:
            self.starting_balance = self.in_round(self.round_number - 1).ending_balance

        # default until round result is computed
        self.ending_balance = self.starting_balance

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
            # EN: Sellers get their own lottery parameters.
            # The sample itself is generated once per group in initialize_group_draws(group).
            self.max_payoff = max_payoff
            self.mid_probability = mid_prob
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
            'starting_balance': self.starting_balance,
            'ending_balance': self.ending_balance,
        }
        return context


# --- session creation & grouping --------------------------------------------


def _create_groups_within_matching_groups(subsession: Subsession):
    """
    Helper that, for the given subsession (round), creates 2S1B groups
    within each fixed matching group.

    Supported matching group modes:
    - size 15: 10 sellers + 5 buyers -> create 5 groups of 2S1B
    - size 3:  2 sellers + 1 buyer  -> create 1 group of 2S1B

    For each matching group:
    - randomize sellers and buyers separately
    - build groups:
        * size-15: [seller[2*i], seller[2*i+1], buyer[i]] for i=0..4
        * size-3:  [seller[0], seller[1], buyer[0]]
    """
    players = subsession.get_players()

    group_size_matching = subsession.session.vars.get('matching_group_size')
    if group_size_matching not in (15, 3):
        raise Exception(
            "matching_group_size is missing or invalid. "
            "It should be assigned in creating_session in round 1."
        )

    # Group players by matching_group_id
    matching_groups = {}
    for p in players:
        mg_id = p.participant.vars.get('matching_group_id')
        if mg_id is None:
            raise Exception(
                "matching_group_id is missing on participant. "
                "It should be assigned in round 1 of this app."
            )
        matching_groups.setdefault(mg_id, []).append(p)

    group_matrix = []

    for mg_id in sorted(matching_groups.keys()):
        block_players = matching_groups[mg_id]

        sellers = [p for p in block_players if p.participant.vars.get('player_role') == 'seller']
        buyers = [p for p in block_players if p.participant.vars.get('player_role') == 'buyer']

        if group_size_matching == 15:
            # EN: Strict check for exactly 10 sellers and 5 buyers.
            if len(sellers) != 10 or len(buyers) != 5:
                raise Exception(
                    f"Matching group {mg_id} must consist of exactly 10 sellers and 5 buyers. "
                    f"Found {len(sellers)} sellers and {len(buyers)} buyers. "
                    f"Check the role assignment and participant count."
                )

            random.shuffle(sellers)
            random.shuffle(buyers)

            # Create 5 groups of [seller, seller, buyer]
            for i in range(5):
                g_players = [sellers[2 * i], sellers[2 * i + 1], buyers[i]]
                group_matrix.append(g_players)

        elif group_size_matching == 3:
            # EN: Strict check for exactly 2 sellers and 1 buyer.
            if len(sellers) != 2 or len(buyers) != 1:
                raise Exception(
                    f"Matching group {mg_id} must consist of exactly 2 sellers and 1 buyer. "
                    f"Found {len(sellers)} sellers and {len(buyers)} buyers. "
                    f"Check the role assignment and participant count."
                )

            random.shuffle(sellers)
            random.shuffle(buyers)

            # Create exactly 1 group of [seller, seller, buyer]
            group_matrix.append([sellers[0], sellers[1], buyers[0]])

    # Apply the group matrix to the subsession
    subsession.set_group_matrix(group_matrix)

    # Set model-level role information and indices for this round
    for group in subsession.get_groups():
        seller_idx = 0
        buyer_idx = 0
        for p in group.get_players():
            # Copy role from participant.vars
            p.player_role = p.participant.vars.get('player_role')
            if p.player_role == 'seller':
                seller_idx += 1
                p.seller_index = seller_idx
            elif p.player_role == 'buyer':
                buyer_idx += 1
                p.buyer_index = buyer_idx


def creating_session(subsession: Subsession):
    """
    Grouping logic for the entire app.

    Round 1:
        - Assign a fixed matching_group_id to each participant.
          Depending on the total number of participants, use one of:
              * matching groups of size 15 (10 sellers, 5 buyers)
              * matching groups of size 3  (2 sellers, 1 buyer)
          Participants are sorted by id_in_subsession and divided into
          consecutive blocks of that matching group size.
        - For the current round, create 2S1B groups within each matching group.

    Rounds 2–10:
        - Reuse matching_group_id from participant.vars.
        - Within each matching group, randomize again and create new 2S1B
          groups for that round.

    Requirements:
        - Total number of participants should be a multiple of 15 or a multiple of 3.
        - Roles come from participant.vars['player_role'], which is assigned
          in the introduction app.
    """
    players = subsession.get_players()
    n_players = len(players)

    # EN: Determine which matching group size to use based on the session size.
    # We support:
    # - 15: 10 sellers + 5 buyers
    # - 3:  2 sellers + 1 buyer
    if subsession.round_number == 1:
        if n_players % 15 == 0:
            group_size_matching = 15
            group_type_value = "2S1B"
        elif n_players % 3 == 0:
            group_size_matching = 3
            group_type_value = "2S1B"
        else:
            raise Exception(
                "Total number of participants must be a multiple of 15 (10 sellers, 5 buyers) "
                "or a multiple of 3 (2 sellers, 1 buyer). "
                f"Found {n_players} participants."
            )

        # EN: Store for later pages to avoid hardcoding.
        subsession.session.vars['matching_group_size'] = group_size_matching
        subsession.session.vars['group_type_value'] = group_type_value

        # Assign matching_group_id based on position in the sorted list of players
        players_sorted = sorted(players, key=lambda p: p.id_in_subsession)
        for idx, p in enumerate(players_sorted):
            matching_group_id = idx // group_size_matching + 1
            p.participant.vars['matching_group_id'] = matching_group_id

    # For the current round, create 2S1B groups within each matching group
    _create_groups_within_matching_groups(subsession)


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
    # Ensure this round is initialized and that the group-level shared sample exists.
    player.initialize_round()
    initialize_group_draws(player.group)

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
    # Ensure all players in the group are initialized and that the group-level shared sample exists.
    for p in player.group.get_players():
        p.initialize_round()
    initialize_group_draws(player.group)

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

    Running-balance logic:
    - buyer and sellers start the round with starting_balance
    - end-of-round balances are stored in ending_balance
    - balances are carried forward to the next round

    Bonus logic:
    - All rounds are bonus-relevant.
    - bonus_payment is stored in every round in euros.
    - total_bonus_payment equals the current total balance in euros.
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

    # Reset seller fields
    for s in sellers:
        s.sold = False
        s.lottery_outcome = Currency(0)
        s.ending_balance = s.starting_balance

    # Handle each buyer (here exactly one)
    for b in buyers:
        choice = b.chosen_lottery_from_seller

        b.outside_option_value = b.starting_balance
        b.bought_lottery = False
        b.chosen_seller_index = 0
        b.chosen_lottery_price = Currency(0)
        b.buyer_lottery_outcome = Currency(0)
        b.ending_balance = b.starting_balance

        if choice == 'none' or choice is None:
            # Buyer keeps previous balance
            b.ending_balance = b.starting_balance
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
            b.chosen_lottery_price = chosen_seller.selling_price_lottery
            b.buyer_lottery_outcome = cu(outcome)

            # Buyer balance: previous balance - price + outcome
            b.ending_balance = (
                b.starting_balance
                - chosen_seller.selling_price_lottery
                + cu(outcome)
            )

            # Mark seller as having sold
            chosen_seller.sold = True
            # Store observed outcome on seller level (for feedback only)
            chosen_seller.lottery_outcome = cu(outcome)

    # Set seller balances: previous balance + price if sold, else unchanged
    for s in sellers:
        if s.sold:
            s.ending_balance = s.starting_balance + s.selling_price_lottery
        else:
            s.ending_balance = s.starting_balance

    # IMPORTANT PAYOFF LOGIC:
    # oTree automatically sums player.payoff over all rounds.
    # Therefore, do NOT set p.payoff = p.ending_balance in every round,
    # otherwise the accumulated balances of all rounds are added together.
    #
    # Desired behavior:
    # - rounds 1 to 9: payoff is 0
    # - round 10: payoff is the final coin balance
    #
    # With real_world_currency_per_point = 0.01, this means:
    # 100 coins = 1 euro.
    for p in players:
        if p.round_number == C.NUM_ROUNDS:
            p.payoff = p.ending_balance
        else:
            p.payoff = cu(0)

    # EN: Store round-specific bonus/change in euros for display/export only.
    # This is NOT used by oTree for payment.
    for p in players:
        if p.round_number == 1:
            # In round 1, this includes the initial endowment
            p.bonus_payment = float(p.ending_balance) / C.EXCHANGE_RATE
        else:
            # In later rounds, show the net change of this round in euros
            p.bonus_payment = float(p.ending_balance - p.starting_balance) / C.EXCHANGE_RATE

    # EN: total bonus equals the current total balance converted to euros.
    # This is for display/export. The actual oTree payment is p.payoff above.
    for p in players:
        p.total_bonus_payment = float(p.ending_balance) / C.EXCHANGE_RATE

        # Store final payout incl. participation fee after round 10 for display/export
        if p.round_number == C.NUM_ROUNDS:
            p.payoff_plus_participation_fee = C.BASE_PAY + p.total_bonus_payment
            p.participant.vars['payoff_plus_participation_fee'] = p.payoff_plus_participation_fee


# --- PAGES ------------------------------------------------------------------


class GroupingWaitPage(WaitPage):
    """
    In every round, groups already exist because grouping is done in creating_session.
    We here simply set group_type to a stable string '2S1B'.
    """
    wait_for_all_groups = True

    @staticmethod
    def after_all_players_arrive(subsession: Subsession):
        group_type_value = subsession.session.vars.get('group_type_value', "2S1B")
        for g in subsession.get_groups():
            g.group_type = group_type_value

            # NEW:
            # Before sellers and buyers see the lotteries in this round,
            # generate exactly one shared sample for this 2S1B group.
            initialize_group_draws(g)


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

    The lottery justification (justified_lottery) is only asked in round 1.
    In later rounds, sellers choose the presentation without giving a justification.
    """

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
        clamped into [1, 100] if needed.
        """
        player.initialize_round()

        if player.selling_price_lottery is not None:
            # NEW: clamp price into [1, 100]
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
    - shows both lotteries in the group
    - marks own lottery and other seller's lottery
    - shows what the buyer did
    - explains the effect on own balance
    No time limit.
    """

    @staticmethod
    def is_displayed(player: Player):
        player.initialize_round()
        return player.player_role == 'seller'

    @staticmethod
    def vars_for_template(player: Player):
        # Ensure all players in the group are initialized
        for p in player.group.get_players():
            p.initialize_round()

        group = player.group

        sellers = [p for p in group.get_players() if p.player_role == 'seller']
        sellers.sort(key=lambda p: p.seller_index)

        buyers = [p for p in group.get_players() if p.player_role == 'buyer']
        buyers.sort(key=lambda p: p.buyer_index)

        if len(sellers) != 2:
            raise Exception("Each group must contain exactly 2 sellers in this design.")

        if len(buyers) != 1:
            raise Exception("Each group must contain exactly 1 buyer in this design.")

        buyer = buyers[0]

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
                    is_own_lottery=(s.id_in_group == player.id_in_group),
                    was_bought=s.sold,

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

                    outcome=s.lottery_outcome,
                )
            )

        if buyer.chosen_lottery_from_seller == 'seller1':
            buyer_choice_text = "Der Käufer hat Lotterie 1 gekauft."
            bought_lottery_number = 1
        elif buyer.chosen_lottery_from_seller == 'seller2':
            buyer_choice_text = "Der Käufer hat Lotterie 2 gekauft."
            bought_lottery_number = 2
        else:
            buyer_choice_text = "Der Käufer hat keine Lotterie gekauft."
            bought_lottery_number = 0

        return dict(
            sellers=sellers_context,
            own_seller_index=player.seller_index,

            sold=player.sold,
            price=player.selling_price_lottery,
            outcome=player.lottery_outcome,

            buyer_choice=buyer.chosen_lottery_from_seller,
            buyer_choice_text=buyer_choice_text,
            bought_lottery_number=bought_lottery_number,

            starting_balance=player.starting_balance,
            ending_balance=player.ending_balance,

            paid_round='alle Runden',
            is_paid_round=True,
            round_payoff=player.payoff,
            round_bonus_euro=player.bonus_payment,
            total_bonus_euro=player.total_bonus_payment,
        )


class BuyerFeedback(Page):
    """
    Feedback for buyers:
    - whether they bought a lottery
    - if yes: index of seller, price, and outcome
    - if no: current balance remains unchanged
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
            starting_balance=player.starting_balance,
            ending_balance=player.ending_balance,
            paid_round='alle Runden',
            is_paid_round=True,
            round_payoff=player.payoff,
            round_bonus_euro=player.bonus_payment,
            total_bonus_euro=player.total_bonus_payment,
        )


class RoundTransitionWaitPage(WaitPage):
    """
    At the end of each round, wait for ALL players in the session
    before proceeding to the next round. This ensures that the dynamic
    regrouping in the next round uses the full pool of participants
    within each matching group.
    """
    wait_for_all_groups = True

    @staticmethod
    def is_displayed(player: Player):
        # Can be shown in every round (also in the last round it just ends).
        return True


page_sequence = [
    # In every round: groups 2S1B are already formed in creating_session
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