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

            # Falls die Introduction-App NICHT davor gelaufen ist (z.B. EXPERIMENT_TEST),
            # setzen wir eine Rolle zufällig.
            if 'player_role' not in participant.vars:
                participant.vars['player_role'] = random.choice(['seller', 'buyer'])

            # Falls payoff/prob-Kombinationen fehlen, generieren wir sie.
            if 'payoff_probability_combinations' not in participant.vars:
                base_combos = list(zip(C.MAX_PAYOFF_STATES, C.MID_PROBABILITIES))
                repeats = C.NUM_ROUNDS // len(base_combos) + 1
                combos = (base_combos * repeats)[:C.NUM_ROUNDS]
                participant.vars['payoff_probability_combinations'] = combos

        # Rolle wie im echten Experiment aus participant.vars übernehmen
        role = self.player.participant.vars['player_role']

        # ⚠️ KEIN yield GroupingWaitPage, WaitForSellers, WaitForBuyerAndSetResults,
        #    RoundTransitionWaitPage – das macht oTree intern für Bots.

        # 1) Lottery_decision: nur Seller
        if role == 'seller':
            # Zufällige Präsentations-Reihenfolge 1–4
            order_list = ['1', '2', '3', '4']
            random.shuffle(order_list)
            order_str = ','.join(order_list)

            # Zufällige Wahl der Präsentation
            chosen_lottery = random.choice(C.LOTTERY_CHOICES)

            # In Runde 1: mit Rechtfertigung
            if self.round_number == 1:
                yield Lottery_decision, {
                    'chosen_lottery': chosen_lottery,
                    'justified_lottery': 'Random bot justification text.',
                    'presentation_order': order_str,
                }
            # Ab Runde 2: ohne Rechtfertigung
            else:
                yield Lottery_decision, {
                    'chosen_lottery': chosen_lottery,
                    'presentation_order': order_str,
                }

        # 2) SellerDecision: nur Seller
        if role == 'seller':
            # initialize_round wird im Page-Code aufgerufen und setzt max_payoff
            # Wir nehmen einen zufälligen Preis im Intervall [1, max_payoff]
            # Zur Sicherheit greifen wir immer frisch auf self.player zu:
            max_price = self.player.max_payoff if self.player.max_payoff else 100
            price = random.randint(1, max_price)

            yield SellerDecision, {
                'selling_price_lottery': cu(price),
                'belief_sequence': '0,1,0,1,1',  # Dummy-Sequenz
                'belief': random.randint(0, 100),
            }

        # 3) BuyerDecision: nur Buyer
        if role == 'buyer':
            # Wir greifen NICHT auf group/sellers zu, sondern übermitteln einfach
            # alle potenziell relevanten Felder; oTree ignoriert überzählige Felder.
            yield BuyerDecision, {
                'buyer_belief_sequence_seller1': '1,0,1,1',
                'buyer_belief_seller1': random.randint(0, 100),
                'buyer_belief_sequence_seller2': '0,1,1,0',
                'buyer_belief_seller2': random.randint(0, 100),
                'chosen_lottery_from_seller': random.choice(
                    ['seller1', 'seller2', 'none']
                ),
            }

        # 4) SellerFeedback: nur Seller
        if role == 'seller':
            yield SellerFeedback

        # 5) BuyerFeedback: nur Buyer
        if role == 'buyer':
            yield BuyerFeedback

        # RoundTransitionWaitPage wird automatisch abgewickelt, kein yield nötig.
