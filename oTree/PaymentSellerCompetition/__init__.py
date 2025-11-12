from otree.api import *


doc = """
Your app description
"""


class C(BaseConstants):
    NAME_IN_URL = 'payment_buyer'
    PLAYERS_PER_GROUP = None
    NUM_ROUNDS = 1
    BASE_PAY = 2.0  # in Pound


class Subsession(BaseSubsession):
    prolific_url = models.StringField()

    def creating_session(player):
        if "prolific_url" not in player.session.config:
            raise Exception("Prolific URL is missing. Add it to the session config.")
        player.prolific_url = player.session.config["prolific_url"]


class Group(BaseGroup):
    pass


class Player(BasePlayer):
    pass


# PAGES
class YouFinished(Page):
    pass


class ToProlific(Page):
    pass

class Debriefing(Page):
    pass

page_sequence = [Debriefing, YouFinished, ToProlific]

class PlayerBot(Bot):
    def play_round(player):
        # If she fails the attention check she never arrives here
        if player.participant.vars.get('failed_attention', False) is False:
            if player.participant.vars['comprehension_passed'] is False:
                assert "You did not answer the comprehension questions" in player.html
            else:
                assert "You have completed this study in its entirety" in player.html
            yield YouFinished
            yield Submission(ToProlific, check_html=False)

