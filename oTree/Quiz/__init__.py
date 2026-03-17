from otree.api import *


doc = """
Your app description
"""


class C(BaseConstants):
    NAME_IN_URL = 'quiz'
    PLAYERS_PER_GROUP = None
    NUM_ROUNDS = 1

    PROB_LOW = 70
    PROB_MID = 29
    PROB_HIGH = 1
    PROB_UPPER_JOINT = PROB_MID + PROB_HIGH

    PAYOFF_LOW = 0
    PAYOFF_MID = 10
    PAYOFF_HIGH = 140

    SUBSAMPLE = [140, 140, 140, 140, 10]


class Subsession(BaseSubsession):
    pass


class Group(BaseGroup):
    pass


class Player(BasePlayer):
    buyer_lottery_favorite = models.StringField(
        choices=['Transparent', 'Sample', 'Censoring', 'Sample_Censoring'],
        blank=False
    )

    # Justification for preference
    buyer_lottery_justification = models.LongStringField(
        label="Bitte begründen Sie Ihre Entscheidung kurz:",
        blank=False,
    )

    # General Questions
    q_age = models.IntegerField(label='Wie alt sind Sie?', min=16, max=99)
    q_gender = models.StringField(
        label='Welchem Geschlecht fühlen Sie sich zugehörig?',
        choices=['Männlich', 'Weiblich', 'Divers', 'Möchte ich nicht beantworten']
    )

    q_study_level = models.StringField(
        choices=[
            "Kein Schulabschluss",
            "Abitur/Fachabitur",
            "Abgeschlossene Berufsausbildung",
            "Bachelorabschluss",
            "Masterabschluss",
            "Doktorabschluss",
            'Möchte ich nicht beantworten'],
        label='Was ist ihr höchster Bildungsabschluss?')

    q_study_field = models.StringField(label='Welches Fach studieren Sie?')

    q_budget = models.IntegerField(label="Wie viel Geld haben Sie monatlich (nach Abzug aller Fixkosten wie Miete etc.) zur freien Verfügung?",
                                   min=0, max=1000000)


    ### Loot box questions ###
    q_loot_box_what = models.BooleanField(
        label="Haben Sie schon mal von Lootboxen in Videospielen gehört?",
        choices=[
            [True, "Ja"],
            [False, "Nein"],
        ],
    )

    q_videogame_time = models.FloatField(label="Wie viele Stunden verbringen Sie durchschnittlich pro Tag mit Videospielen?",
                                         min=0, max=24)


    q_loot_box_spending = models.FloatField(label="Wie viel haben Sie im letzten Jahr monatlich durchschnittlich für Lootboxen ausgegeben?",  #Added time frame
                                            min=0)
    q_loot_box_more_than_planned = models.BooleanField(
        label="Haben Sie schon mal mehr Geld für Lootboxen ausgegeben, als Sie eigentlich geplant hatten?",
        choices=[
            [True, "Ja"],
            [False, "Nein"],
        ],
    )

    ### Self Control Scale Tangney et al (2004) ###
    ### German Translation: Betrams und Dickhäuser (2009) ###
    q_self_control_1 = models.IntegerField(label="Ich bin gut darin, Versuchungen zu widerstehen.",
                                        widget=widgets.RadioSelect(),
                                        choices=[1, 2, 3, 4, 5])
    q_self_control_2 = models.IntegerField(label="Es fällt mir schwer, schlechte Gewohnheiten abzulegen.",
                                        widget=widgets.RadioSelect(),
                                        choices=[1, 2, 3, 4, 5])
    q_self_control_3 = models.IntegerField(label="Ich bin faul.",
                                        widget=widgets.RadioSelect(),
                                        choices=[1, 2, 3, 4, 5])
    q_self_control_4 = models.IntegerField(label="Ich sage unangemessene Dinge.",
                                        widget=widgets.RadioSelect(),
                                        choices=[1, 2, 3, 4, 5])
    q_self_control_5 = models.IntegerField(label="Ich tue manchmal Dinge, die schlecht für mich sind,wenn sie mir Spaß machen.",
                                        widget=widgets.RadioSelect(),
                                        choices=[1, 2, 3, 4, 5])
    q_self_control_6 = models.IntegerField(label="Ich wünschte, ich hätte mehr Selbstdisziplin.",
                                        widget=widgets.RadioSelect(),
                                        choices=[1, 2, 3, 4, 5])
    q_self_control_7 = models.IntegerField(label="Angenehme Aktivitäten und Vergnügen hindern michmanchmal daran, meine Arbeit zu machen. ",
                                        widget=widgets.RadioSelect(),
                                        choices=[1, 2, 3, 4, 5])
    q_self_control_8 = models.IntegerField(label="Es fällt mir schwer, mich zu konzentrieren.",
                                        widget=widgets.RadioSelect(),
                                        choices=[1, 2, 3, 4, 5])
    q_self_control_9 = models.IntegerField(label="Ich kann effektiv auf langfristige Ziele hinarbeiten.",
                                        widget=widgets.RadioSelect(),
                                        choices=[1, 2, 3, 4, 5])
    q_self_control_10 = models.IntegerField(label="Manchmal kann ich mich selbst nicht daran hindern,etwas zu tun, obwohl ich weiß, dass es falsch ist.",
                                        widget=widgets.RadioSelect(),
                                        choices=[1, 2, 3, 4, 5])
    q_self_control_11 = models.IntegerField(label="Ich handle oft ohne alle Alternativen durchdacht zu haben.",
                                        widget=widgets.RadioSelect(),
                                        choices=[1, 2, 3, 4, 5])
    q_self_control_12 = models.IntegerField(label="Ich lehne Dinge ab, die schlecht für mich sind.",
                                        widget=widgets.RadioSelect(),
                                        choices=[1, 2, 3, 4, 5])
    q_self_control_13 = models.IntegerField(label="Andere würden sagen, dass ich eine eiserneSelbstdisziplin habe.",
                                        widget=widgets.RadioSelect(),
                                        choices=[1, 2, 3, 4, 5])

    ### Kurzfragebogen zum Glücksspielverhalten (KFG)  ###
    ### Source:  Petry, J. (1996) Psychotherapie der Glücksspielsucht, Weinheim: Psychologie Verlags Union ###
    q_kfg_1 = models.IntegerField(
        label="Ich habe meistens gespielt, um Verluste wieder auszugleichen.",
        widget=widgets.RadioSelect(),
        choices=[(0, "trifft gar nicht zu"), (1, "trifft eher nicht zu"), (2, "trifft eher zu"), (3, "trifft genau zu")]
    )

    q_kfg_2 = models.IntegerField(
        label="Ich kann mein Spielen nicht mehr kontrollieren.",
        widget=widgets.RadioSelect(),
        choices=[(0, "trifft gar nicht zu"), (1, "trifft eher nicht zu"), (2, "trifft eher zu"), (3, "trifft genau zu")]
    )

    q_kfg_3 = models.IntegerField(
        label="Meine Angehörigen oder Freunde dürfen nicht wissen, wieviel ich verspiele.",
        widget=widgets.RadioSelect(),
        choices=[(0, "trifft gar nicht zu"), (1, "trifft eher nicht zu"), (2, "trifft eher zu"), (3, "trifft genau zu")]
    )

    q_kfg_4 = models.IntegerField(
        label="Im Vergleich zum Spielen erscheint mir der Alltag langweilig.",
        widget=widgets.RadioSelect(),
        choices=[(0, "trifft gar nicht zu"), (1, "trifft eher nicht zu"), (2, "trifft eher zu"), (3, "trifft genau zu")]
    )

    q_kfg_5 = models.IntegerField(
        label="Nach dem Spielen habe ich oft ein schlechtes Gewissen.",
        widget=widgets.RadioSelect(),
        choices=[(0, "trifft gar nicht zu"), (1, "trifft eher nicht zu"), (2, "trifft eher zu"), (3, "trifft genau zu")]
    )

    q_kfg_6 = models.IntegerField(
        label="Ich benutze Vorwände, um spielen zu können.",
        widget=widgets.RadioSelect(),
        choices=[(0, "trifft gar nicht zu"), (1, "trifft eher nicht zu"), (2, "trifft eher zu"), (3, "trifft genau zu")]
    )

    q_kfg_7 = models.IntegerField(
        label="Ich schaffe es nicht, das Spielen längere Zeit einzustellen.",
        widget=widgets.RadioSelect(),
        choices=[(0, "trifft gar nicht zu"), (1, "trifft eher nicht zu"), (2, "trifft eher zu"), (3, "trifft genau zu")]
    )

    q_kfg_8 = models.IntegerField(
        label="Ich spiele fast täglich um Geld.",
        widget=widgets.RadioSelect(),
        choices=[(0, "trifft gar nicht zu"), (1, "trifft eher nicht zu"), (2, "trifft eher zu"), (3, "trifft genau zu")]
    )

    q_kfg_9 = models.IntegerField(
        label="Durch mein Spielen habe ich berufliche Schwierigkeiten.",
        widget=widgets.RadioSelect(),
        choices=[(0, "trifft gar nicht zu"), (1, "trifft eher nicht zu"), (2, "trifft eher zu"), (3, "trifft genau zu")]
    )

    q_kfg_10 = models.IntegerField(
        label="Beim Spielen suche ich Nervenkitzel.",
        widget=widgets.RadioSelect(),
        choices=[(0, "trifft gar nicht zu"), (1, "trifft eher nicht zu"), (2, "trifft eher zu"), (3, "trifft genau zu")]
    )

    q_kfg_11 = models.IntegerField(
        label="Ich denke ständig ans Spielen.",
        widget=widgets.RadioSelect(),
        choices=[(0, "trifft gar nicht zu"), (1, "trifft eher nicht zu"), (2, "trifft eher zu"), (3, "trifft genau zu")]
    )

    q_kfg_12 = models.IntegerField(
        label="Um mein Spiel zu finanzieren, habe ich oft unrechtmäßig Geld besorgt.",
        widget=widgets.RadioSelect(),
        choices=[(0, "trifft gar nicht zu"), (1, "trifft eher nicht zu"), (2, "trifft eher zu"), (3, "trifft genau zu")]
    )

    q_kfg_13 = models.IntegerField(
        label="Den größten Teil meiner Freizeit spiele ich.",
        widget=widgets.RadioSelect(),
        choices=[(0, "trifft gar nicht zu"), (1, "trifft eher nicht zu"), (2, "trifft eher zu"), (3, "trifft genau zu")]
    )

    q_kfg_14 = models.IntegerField(
        label="Ich habe schon fremdes bzw. geliehenes Geld verspielt.",
        widget=widgets.RadioSelect(),
        choices=[(0, "trifft gar nicht zu"), (1, "trifft eher nicht zu"), (2, "trifft eher zu"), (3, "trifft genau zu")]
    )

    q_kfg_15 = models.IntegerField(
        label="Ich war wegen meiner Spielprobleme schon in Behandlung.",
        widget=widgets.RadioSelect(),
        choices=[(0, "trifft gar nicht zu"), (1, "trifft eher nicht zu"), (2, "trifft eher zu"), (3, "trifft genau zu")]
    )

    q_kfg_16 = models.IntegerField(
        label="Ich habe schon häufig mit dem Spielen aufhören müssen, weil ich kein Geld mehr hatte.",
        widget=widgets.RadioSelect(),
        choices=[(0, "trifft gar nicht zu"), (1, "trifft eher nicht zu"), (2, "trifft eher zu"), (3, "trifft genau zu")]
    )

    q_kfg_17 = models.IntegerField(
        label="Weil ich so viel spiele, habe ich viele Freunde verloren.",
        widget=widgets.RadioSelect(),
        choices=[(0, "trifft gar nicht zu"), (1, "trifft eher nicht zu"), (2, "trifft eher zu"), (3, "trifft genau zu")]
    )

    q_kfg_18 = models.IntegerField(
        label="Um spielen zu können, leihe ich mir häufig Geld.",
        widget=widgets.RadioSelect(),
        choices=[(0, "trifft gar nicht zu"), (1, "trifft eher nicht zu"), (2, "trifft eher zu"), (3, "trifft genau zu")]
    )

    q_kfg_19 = models.IntegerField(
        label="In meiner Phantasie bin ich der große Gewinner.",
        widget=widgets.RadioSelect(),
        choices=[(0, "trifft gar nicht zu"), (1, "trifft eher nicht zu"), (2, "trifft eher zu"), (3, "trifft genau zu")]
    )

    q_kfg_20 = models.IntegerField(
        label="Wegen des Spielens war ich schon oft so verzweifelt, dass ich mir das Leben nehmen wollte.",
        widget=widgets.RadioSelect(),
        choices=[(0, "trifft gar nicht zu"), (1, "trifft eher nicht zu"), (2, "trifft eher zu"), (3, "trifft genau zu")]
    )


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
    form_fields = [
        'q_kfg_1', 'q_kfg_2', 'q_kfg_3', 'q_kfg_4', 'q_kfg_5',
        'q_kfg_6', 'q_kfg_7', 'q_kfg_8', 'q_kfg_9', 'q_kfg_10',
        'q_kfg_11', 'q_kfg_12', 'q_kfg_13', 'q_kfg_14', 'q_kfg_15',
        'q_kfg_16', 'q_kfg_17', 'q_kfg_18', 'q_kfg_19', 'q_kfg_20'
    ]

class BuyerLotteries(Page):
    form_model = 'player'
    form_fields = ['buyer_lottery_favorite', 'buyer_lottery_justification']

    @staticmethod
    def is_displayed(player: Player):
        return player.participant.vars.get('player_role') == 'buyer'

    @staticmethod
    def vars_for_template(player: Player):
        return dict(
            prob_low=C.PROB_LOW,
            prob_mid=C.PROB_MID,
            prob_high=C.PROB_HIGH,
            prob_upper_joint=C.PROB_UPPER_JOINT,
            payoff_low=C.PAYOFF_LOW,
            payoff_mid=C.PAYOFF_MID,
            payoff_high=C.PAYOFF_HIGH,
            subsample=C.SUBSAMPLE,
        )

    @staticmethod
    def error_message(player: Player, values):
        favorite = values.get('buyer_lottery_favorite', '').strip()

        valid_ids = {
            'Transparent',
            'Sample',
            'Censoring',
            'Sample_Censoring',
        }

        if not favorite:
            return 'Bitte wählen Sie eine Präsentation aus.'

        if favorite not in valid_ids:
            return 'Bitte wählen Sie eine gültige Präsentation aus.'

        justification = values.get('buyer_lottery_justification', '').strip()
        if not justification:
            return 'Bitte geben Sie eine kurze Begründung an.'

class Debriefing(Page):
    pass

page_sequence = [General, Video_1, Video_2, Control, Game, BuyerLotteries]
