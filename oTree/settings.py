from os import environ

SESSION_CONFIGS = [
    dict(
        name='FULL',
        display_name="FULL",
        app_sequence=['Introduction', 'Experiment', 'Quiz'],
        num_demo_participants=3,
        use_browser_bots=False,
    ),
dict(
        name='EXPERIMENT_TEST',
        display_name="EXPERIMENT_TEST",
        app_sequence=['Experiment'],
        num_demo_participants=9,
        use_browser_bots=True,
    ),
dict(
        name='Quiz_TEST',
        display_name="Quiz_TEST",
        app_sequence=['Quiz'],
        num_demo_participants=9,
        use_browser_bots=False,
    ),
]

# if you set a property in SESSION_CONFIG_DEFAULTS, it will be inherited by all configs
# in SESSION_CONFIGS, except those that explicitly override it.
# the session config can be accessed from methods in your apps as self.session.config,
# e.g. self.session.config['participation_fee']

SESSION_CONFIG_DEFAULTS = dict(
    real_world_currency_per_point=1/13, participation_fee=2, doc=""
)

ROOMS = [
    dict(
        name='DICELAB',
        display_name='DICELAB',
        #participant_label_file='dicelab_otree_labels.txt',
        #use_secure_urls=True
        )
]

PARTICIPANT_FIELDS = []
SESSION_FIELDS = []

# ISO-639 code
# for example: de, fr, ja, ko, zh-hans
LANGUAGE_CODE = 'en'

# e.g. EUR, GBP, CNY, JPY
REAL_WORLD_CURRENCY_CODE = 'GBP'
USE_POINTS = True
POINTS_CUSTOM_NAME = 'Münzen'

ADMIN_USERNAME = 'admin'
# for security, best to set admin password in an environment variable
ADMIN_PASSWORD = environ.get('OTREE_ADMIN_PASSWORD')

DEMO_PAGE_INTRO_HTML = """ """

SECRET_KEY = '1321473717467'
