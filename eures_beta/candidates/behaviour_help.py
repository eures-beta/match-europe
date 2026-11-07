"""Editorial reading aids for existing ESCO declarations; identifiers do not change."""

from django.utils.translation import gettext_lazy as _

GROUPS = {
    'others': _('With other people'),
    'work': _('In my day-to-day work'),
    'change': _('When things change or become difficult'),
}

HELP = {
    'a17286c5-238d-4f0b-bc24-29e9121345de': (
        'others',
        _('Listening to others'),
        _('I listen to the other person and check that I have understood.'),
    ),
    '60c78287-22eb-4103-9c8c-28deaa460da0': (
        'others',
        _('Working as a team'),
        _('I share useful information and help my colleagues when needed.'),
    ),
    '77b636e8-fab3-41a8-8022-1e0a354059dc': (
        'others',
        _('Understanding other people'),
        _('I try to understand how another person feels and take it into account.'),
    ),
    'e37d64dc-0f05-4ee8-b065-bf76f70d8f5c': (
        'others',
        _('Keeping information confidential'),
        _('I do not share private information entrusted to me.'),
    ),
    'bcf002ce-90f8-42e5-ac1b-5dba208639b0': (
        'work',
        _('Being someone people can rely on'),
        _('I keep my commitments and let people know if there is a problem.'),
    ),
    'd9013e0e-e937-43d5-ab71-0e917ee882b8': (
        'work',
        _('Organising my time'),
        _('I plan what I need to do so I can finish on time.'),
    ),
    '6b305973-8993-475f-bd8a-daf037c61401': (
        'work',
        _('Keeping my work organised'),
        _(
            'I organise my documents, equipment and information so I can find them easily.'
        ),
    ),
    'c29aa9d2-4da8-4bdd-831c-8d4a2fb51730': (
        'work',
        _('Working independently'),
        _('I can carry out my tasks on my own and ask for help when needed.'),
    ),
    '83e6510b-ffeb-4aec-959c-4265fd0ff7b7': (
        'work',
        _('Checking my work'),
        _('I check details to spot mistakes or things I may have missed.'),
    ),
    'f83c245f-4aa9-484f-8fd2-4ad65dd82ae5': (
        'work',
        _('Staying alert'),
        _('I pay attention to what is happening and notice unusual situations.'),
    ),
    '49de9958-2aa4-4eef-a89d-fe5d5bcd28c4': (
        'change',
        _('Adapting to change'),
        _('I adjust how I work when instructions or circumstances change.'),
    ),
    '7a147904-22b3-498a-b4d9-7bceeb86b45d': (
        'change',
        _('Staying calm in difficult situations'),
        _(
            'When things become difficult, I try to stay calm and take one thing at a time.'
        ),
    ),
    '001115fb-569f-4ee6-8381-c6807ef2527f': (
        'change',
        _('Taking useful initiatives'),
        _('I suggest ideas or take useful action while respecting the instructions.'),
    ),
}


def for_uri(uri):
    return HELP.get(uri.rsplit('/', 1)[-1])
