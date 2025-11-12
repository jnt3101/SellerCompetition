from otree.api import *


doc = """
Your app description
"""


class C(BaseConstants):
    NAME_IN_URL = 'quiz'
    PLAYERS_PER_GROUP = None
    NUM_ROUNDS = 1


class Subsession(BaseSubsession):
    pass


class Group(BaseGroup):
    pass


class Player(BasePlayer):
    # General Questions
    q_age = models.IntegerField(label='How old are you?', min=16, max=99)
    q_gender = models.StringField(
        label='What is your gender?',
        choices=['Male', 'Female', 'Diverse', 'Prefer not to answer']
    )

    q_study_level = models.StringField(
        choices=[
            "Secondary school not completed",
            "High school graduation",
            "Professional qualification",
            "Bachelor's degree",
            "Master's degree",
            "PhD degree",
            'Prefer not to answer'],
        label='What is your highest level of education')

    q_study_field = models.StringField(label='What do you study? / What is your occupation?')

    q_budget = models.IntegerField(label="How much money do you have available each month (after deducting fixed costs such as rent, insurance, etc., British pound)?",
                                   min=0, max=1000000)


    ### Loot box questions ###
    q_loot_box_what = models.BooleanField(label="Have you ever heard of loot boxes in videogames before?")
    q_videogame_time = models.FloatField(label="How many hours do you spend playing videogames per day on average?",
                                         min=0, max=24)


    q_loot_box_spending = models.FloatField(label="How much did you spend on loot boxes per month during the last year on average? (in British pound)",  #Added time frame
                                            min=0)
    q_loot_box_more_than_planned = models.BooleanField(label="Have you ever spend more than you planned to on loot boxes?")

    ### Self Control survey ###
    q_self_control_1 = models.IntegerField(label="I am good at resisting temptation.",
                                        widget=widgets.RadioSelect(),
                                        choices=[1, 2, 3, 4, 5])
    q_self_control_2 = models.IntegerField(label="I have a hard time breaking bad habits.",
                                        widget=widgets.RadioSelect(),
                                        choices=[1, 2, 3, 4, 5])
    q_self_control_3 = models.IntegerField(label="I am lazy.",
                                        widget=widgets.RadioSelect(),
                                        choices=[1, 2, 3, 4, 5])
    q_self_control_4 = models.IntegerField(label="I say inappropriate things.",
                                        widget=widgets.RadioSelect(),
                                        choices=[1, 2, 3, 4, 5])
    q_self_control_5 = models.IntegerField(label="I do certain things that are bad for me, if they are fun.",
                                        widget=widgets.RadioSelect(),
                                        choices=[1, 2, 3, 4, 5])
    q_self_control_6 = models.IntegerField(label="I refuse things that are bad for me.",
                                        widget=widgets.RadioSelect(),
                                        choices=[1, 2, 3, 4, 5])
    q_self_control_7 = models.IntegerField(label="I wish I had more self-discipline.",
                                        widget=widgets.RadioSelect(),
                                        choices=[1, 2, 3, 4, 5])
    q_self_control_8 = models.IntegerField(label="People would say that I have iron self-discipline.",
                                        widget=widgets.RadioSelect(),
                                        choices=[1, 2, 3, 4, 5])
    q_self_control_9 = models.IntegerField(label="Pleasure and fun sometimes keep me from getting work done.",
                                        widget=widgets.RadioSelect(),
                                        choices=[1, 2, 3, 4, 5])
    q_self_control_10 = models.IntegerField(label="I have trouble concentrating.",
                                        widget=widgets.RadioSelect(),
                                        choices=[1, 2, 3, 4, 5])
    q_self_control_11 = models.IntegerField(label="I am able to work effectively toward long-term goals.",
                                        widget=widgets.RadioSelect(),
                                        choices=[1, 2, 3, 4, 5])
    q_self_control_12 = models.IntegerField(label="Sometimes I can’t stop myself from doing something, even if I know it is wrong.",
                                        widget=widgets.RadioSelect(),
                                        choices=[1, 2, 3, 4, 5])
    q_self_control_13 = models.IntegerField(label="I often act without thinking through all the alternatives.",
                                        widget=widgets.RadioSelect(),
                                        choices=[1, 2, 3, 4, 5])

    ### Problem Gambling Severity Index ###
    q_gambling_1 = models.IntegerField(label="Have you bet more than you could really afford to lose?",
                                        widget=widgets.RadioSelect(),
                                        choices=[(0, "Never"), (1, "Sometimes"), (2, "Most of the time"), (3, "Always")])
    q_gambling_2 = models.IntegerField(label="Have you needed to gamble with larger amounts of money to get the same feeling of excitement?",
                                        widget=widgets.RadioSelect(),
                                        choices=[(0, "Never"), (1, "Sometimes"), (2, "Most of the time"), (3, "Always")])
    q_gambling_3 = models.IntegerField(label="Have you gone back on another day to try to win back the money you lost?",
                                        widget=widgets.RadioSelect(),
                                        choices=[(0, "Never"), (1, "Sometimes"), (2, "Most of the time"), (3, "Always")])
    q_gambling_4 = models.IntegerField(label="Have you borrowed money or sold anything to gamble?",
                                        widget=widgets.RadioSelect(),
                                        choices=[(0, "Never"), (1, "Sometimes"), (2, "Most of the time"), (3, "Always")])
    q_gambling_5 = models.IntegerField(label="Have you felt that you might have a problem with gambling?",
                                        widget=widgets.RadioSelect(),
                                        choices=[(0, "Never"), (1, "Sometimes"), (2, "Most of the time"), (3, "Always")])
    q_gambling_6 = models.IntegerField(label="Have people criticised your betting or told you that you had a gambling problem, whether or not you thought it was true?",
                                        widget=widgets.RadioSelect(),
                                        choices=[(0, "Never"), (1, "Sometimes"), (2, "Most of the time"), (3, "Always")])
    q_gambling_7 = models.IntegerField(label="Have you felt guilty about the way you gamble or what happens when you gamble?",
                                        widget=widgets.RadioSelect(),
                                        choices=[(0, "Never"), (1, "Sometimes"), (2, "Most of the time"), (3, "Always")])
    q_gambling_8 = models.IntegerField(label="Has gambling caused you any health problems, including stress or anxiety?",
                                        widget=widgets.RadioSelect(),
                                        choices=[(0, "Never"), (1, "Sometimes"), (2, "Most of the time"), (3, "Always")])
    q_gambling_9 = models.IntegerField(label="Has your gambling caused any financial problems for you or your household?",
                                        widget=widgets.RadioSelect(),
                                        choices=[(0, "Never"), (1, "Sometimes"), (2, "Most of the time"), (3, "Always")])


class General(Page):
    form_model = 'player'
    form_fields = ['q_age', 'q_gender', 'q_study_level', 'q_study_field',
                   'q_budget']


class Video_1(Page):
    form_model = 'player'
    form_fields = ['q_videogame_time', 'q_loot_box_what']


class Video_2(Page):
    form_model = 'player'
    form_fields = ["q_loot_box_spending", "q_loot_box_more_than_planned"]

    @staticmethod
    def is_displayed(player):
        # Only show if the person knows what a loot box is
        return player.q_loot_box_what == True


class Control(Page):
    form_model = 'player'
    form_fields = ['q_self_control_1', 'q_self_control_2', 'q_self_control_3', 'q_self_control_4',
                   'q_self_control_5', 'q_self_control_6', 'q_self_control_7', 'q_self_control_8',
                   'q_self_control_9', 'q_self_control_10', 'q_self_control_11', 'q_self_control_12',
                   'q_self_control_13']


class Game(Page):
    form_model = 'player'
    form_fields = ['q_gambling_1', 'q_gambling_2', 'q_gambling_3', 'q_gambling_4',
                   'q_gambling_5', 'q_gambling_6', 'q_gambling_7', 'q_gambling_8',
                   'q_gambling_9']


page_sequence = [General, Video_1, Video_2, Control, Game]
