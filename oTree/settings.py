from os import environ

SESSION_CONFIGS = [
    dict(
        name='FULL',
        display_name="FULL",
        app_sequence=['Introduction', 'Experiment', 'Quiz','PaymentSellerCompetition'],
        treatment_list = ['TRANSPARENT', 'CENSORING', 'SAMPLE', 'SAMPLE_CENSORING'],
        num_demo_participants=27,
        use_browser_bots=False,
        prolific_url="https://google.com",
        prolific_attention_link="https://google.com",  # TODO: Replace
        prolific_completion_link="https://google.com",  # TODO: Replace
        prolific_no_consent_link="https://google.com"  # TODO: Replace
    ),
dict(
        name='EXPERIMENT_TEST',
        display_name="EXPERIMENT_TEST",
        app_sequence=['Experiment'],
        treatment_list = ['TRANSPARENT', 'CENSORING', 'SAMPLE', 'SAMPLE_CENSORING'],
        num_demo_participants=51,
        use_browser_bots=False,
        prolific_url="https://google.com",
        prolific_attention_link="https://google.com",  # TODO: Replace
        prolific_completion_link="https://google.com",  # TODO: Replace
        prolific_no_consent_link="https://google.com"  # TODO: Replace
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
