from otree.api import *
import random

from . import *


class PlayerBot(Bot):

    def play_round(self):
        # Wir greifen NIE auf player.group zu und cachen player nicht über yields hinweg,
        # um DetachedInstanceError zu vermeiden.

        # --- INITIALISIERUNG FÜR BOTS (nur in Runde 1) ----------------------
        if self.round_number == 1:
            participant = self.player.participant

            # Falls die Introduction-App NICHT davor gelaufen ist,
            # setzen wir Rollen so, dass jede 10er Matching-Gruppe
            # genau 5 Seller und 5 Buyer enthält.
            if 'player_role' not in participant.vars:
                position_in_block_of_10 = (self.player.id_in_subsession - 1) % 10

                if position_in_block_of_10 < 5:
                    participant.vars['player_role'] = 'seller'
                else:
                    participant.vars['player_role'] = 'buyer'

            # Falls payoff/prob-Kombinationen fehlen, generieren wir sie.
            if 'payoff_probability_combinations' not in participant.vars:
                full_sequence = []

                block_size = len(C.MAX_PAYOFF_STATES)
                n_blocks = C.NUM_ROUNDS // block_size
                remainder = C.NUM_ROUNDS % block_size

                for _ in range(n_blocks):
                    max_states = C.MAX_PAYOFF_STATES.copy()
                    mid_probs = C.MID_PROBABILITIES.copy()
                    random.shuffle(max_states)
                    random.shuffle(mid_probs)
                    full_sequence.extend(list(zip(max_states, mid_probs)))

                if remainder:
                    max_states = C.MAX_PAYOFF_STATES.copy()
                    mid_probs = C.MID_PROBABILITIES.copy()
                    random.shuffle(max_states)
                    random.shuffle(mid_probs)
                    full_sequence.extend(list(zip(max_states, mid_probs))[:remainder])

                participant.vars['payoff_probability_combinations'] = full_sequence

        # Rolle wie im echten Experiment aus participant.vars übernehmen
        role = self.player.participant.vars['player_role']

        # ⚠️ KEIN yield GroupingWaitPage, WaitForSellers,
        #    WaitForBuyerAndSetResults oder RoundTransitionWaitPage –
        #    das macht oTree intern für Bots.

        # 1) Lottery_decision: nur Seller
        if role == 'seller':
            order_list = ['1', '2', '3', '4']
            random.shuffle(order_list)
            order_str = ','.join(order_list)

            chosen_lottery = random.choice(C.LOTTERY_CHOICES)

            if self.round_number == 1:
                yield Lottery_decision, {
                    'chosen_lottery': chosen_lottery,
                    'justified_lottery': 'Random bot justification text.',
                    'presentation_order': order_str,
                }
            else:
                yield Lottery_decision, {
                    'chosen_lottery': chosen_lottery,
                    'presentation_order': order_str,
                }

        # 2) SellerDecision: nur Seller
        if role == 'seller':
            price = random.randint(1, 100)

            yield SellerDecision, {
                'selling_price_lottery': cu(price),
                'belief_sequence': '0,1,0,1,1',
                'belief': random.randint(0, 100),
            }

        # 3) BuyerDecision: nur Buyer
        if role == 'buyer':
            yield BuyerDecision, {
                'buyer_belief_sequence_seller1': '1,0,1,1',
                'buyer_belief_seller1': random.randint(0, 100),
                'chosen_lottery_from_seller': random.choice(
                    ['seller1', 'none']
                ),
            }

        # 4) SellerFeedback: nur Seller
        if role == 'seller':
            yield SellerFeedback

        # 5) BuyerFeedback: nur Buyer
        if role == 'buyer':
            yield BuyerFeedback
