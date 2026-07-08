from os import environ

SESSION_CONFIGS = [
    dict(
        name='FULL_2S1B',
        display_name="FULL_2S1B",
        app_sequence=['Introduction', 'Experiment', 'Quiz', 'payment'],
        num_demo_participants=15,
        expShortName="SCL", # Replace with your values
        expId=30, # Replace with your values
        sessId=0000000000, # Replace with your values
        use_browser_bots=False,
    ),
dict(
        name='FULL_BOTS',
        display_name="FULL_BOTS",
        app_sequence=['Introduction', 'Experiment', 'Quiz', 'payment'],
        num_demo_participants=15,
        expShortName="TestExp", # Replace with your values
        expId=0000000000, # Replace with your values
        sessId=0000000000, # Replace with your values
        use_browser_bots=True,
    ),
dict(
        name='FULL_1S1B',
        display_name="FULL_1S1B",
        app_sequence=['Introduction_1S1B', 'Experiment_1S1B', 'Quiz', 'payment'],
        num_demo_participants=2,
        expShortName="SCL", # Replace with your values
        expId=30, # Replace with your values
        sessId=0000000000, # Replace with your values
        use_browser_bots=False,
    ),
dict(
        name='FULL_1S1B_BONN',
        display_name="FULL_1S1B_BONN",
        app_sequence=['iban_checker_online','Introduction_1S1B', 'Experiment_1S1B', 'Quiz'],
        num_demo_participants=2,
        use_browser_bots=False,
        iban_timeout_seconds=10000
    ),
dict(
        name='FULL_2S1B_BONN',
        display_name="FULL_2S1B_BONN",
        app_sequence=['iban_checker_online','Introduction', 'Experiment', 'Quiz'],
        num_demo_participants=15,
        iban_timeout_seconds=10000,
        use_browser_bots=False,
    ),
dict(
        name='1S1BBots',
        display_name="1S1BBOTS",
        app_sequence=['Introduction_1S1B', 'Experiment_1S1B'],
        num_demo_participants=2,
        expShortName="TestExp", # Replace with your values
        expId=0000000000, # Replace with your values
        sessId=0000000000, # Replace with your values
        use_browser_bots=True,
    ),
]

# if you set a property in SESSION_CONFIG_DEFAULTS, it will be inherited by all configs
# in SESSION_CONFIGS, except those that explicitly override it.
# the session config can be accessed from methods in your apps as self.session.config,
# e.g. self.session.config['participation_fee']

SESSION_CONFIG_DEFAULTS = dict(
    real_world_currency_per_point=1/100, participation_fee=6, doc=""
)

ROOMS = [
    dict(
        name='lab',
        display_name='Lab Experiment',
        participant_label_file='_rooms/lab.txt',
    ),
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
REAL_WORLD_CURRENCY_CODE = 'EUR'
USE_POINTS = True
POINTS_CUSTOM_NAME = 'Münzen'

ADMIN_USERNAME = 'admin'
# for security, best to set admin password in an environment variable
ADMIN_PASSWORD = environ.get('OTREE_ADMIN_PASSWORD')

DEMO_PAGE_INTRO_HTML = """ """

SECRET_KEY = '1321473717467'
