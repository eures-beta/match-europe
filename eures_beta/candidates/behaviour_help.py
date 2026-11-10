"""Candidate-friendly wording for existing ESCO professional behaviours.

Readable keys identify the editorial entries below. The esco_id remains the
external reference saved in candidate answers; never replace it with our key.
The corresponding ESCO page is https://data.europa.eu/esco/skill/<esco_id>.
Labels and examples are editorial aids, not official ESCO definitions.
"""

from dataclasses import dataclass

from django.utils.functional import Promise
from django.utils.translation import gettext_lazy as _


@dataclass(frozen=True)
class BehaviourHelp:
    esco_id: str
    group: str
    label: Promise
    description: Promise


GROUPS = {
    'others': _('With other people'),
    'work': _('In my day-to-day work'),
    'change': _('When things change or become difficult'),
}

# Keys describe the behaviour; esco_id links it to the versioned ESCO catalogue.
BEHAVIOURS = {
    'listening': BehaviourHelp(
        esco_id='a17286c5-238d-4f0b-bc24-29e9121345de',
        group='others',
        label=_('Listening to others'),
        description=_('I listen to the other person and check that I have understood.'),
    ),
    'teamwork': BehaviourHelp(
        esco_id='60c78287-22eb-4103-9c8c-28deaa460da0',
        group='others',
        label=_('Working as a team'),
        description=_('I share useful information and help my colleagues when needed.'),
    ),
    'empathy': BehaviourHelp(
        esco_id='77b636e8-fab3-41a8-8022-1e0a354059dc',
        group='others',
        label=_('Understanding other people'),
        description=_(
            'I try to understand how another person feels and take it into account.'
        ),
    ),
    'confidentiality': BehaviourHelp(
        esco_id='e37d64dc-0f05-4ee8-b065-bf76f70d8f5c',
        group='others',
        label=_('Keeping information confidential'),
        description=_('I do not share private information entrusted to me.'),
    ),
    'reliability': BehaviourHelp(
        esco_id='bcf002ce-90f8-42e5-ac1b-5dba208639b0',
        group='work',
        label=_('Being someone people can rely on'),
        description=_(
            'I keep my commitments and let people know if there is a problem.'
        ),
    ),
    'time_management': BehaviourHelp(
        esco_id='d9013e0e-e937-43d5-ab71-0e917ee882b8',
        group='work',
        label=_('Organising my time'),
        description=_('I plan what I need to do so I can finish on time.'),
    ),
    'organisation': BehaviourHelp(
        esco_id='6b305973-8993-475f-bd8a-daf037c61401',
        group='work',
        label=_('Keeping my work organised'),
        description=_(
            'I organise my documents, equipment and information so I can find them easily.'
        ),
    ),
    'independence': BehaviourHelp(
        esco_id='c29aa9d2-4da8-4bdd-831c-8d4a2fb51730',
        group='work',
        label=_('Working independently'),
        description=_(
            'I can carry out my tasks on my own and ask for help when needed.'
        ),
    ),
    'attention_to_detail': BehaviourHelp(
        esco_id='83e6510b-ffeb-4aec-959c-4265fd0ff7b7',
        group='work',
        label=_('Checking my work'),
        description=_('I check details to spot mistakes or things I may have missed.'),
    ),
    'alertness': BehaviourHelp(
        esco_id='f83c245f-4aa9-484f-8fd2-4ad65dd82ae5',
        group='work',
        label=_('Staying alert'),
        description=_(
            'I pay attention to what is happening and notice unusual situations.'
        ),
    ),
    'adaptability': BehaviourHelp(
        esco_id='49de9958-2aa4-4eef-a89d-fe5d5bcd28c4',
        group='change',
        label=_('Adapting to change'),
        description=_('I adjust how I work when instructions or circumstances change.'),
    ),
    'staying_calm': BehaviourHelp(
        esco_id='7a147904-22b3-498a-b4d9-7bceeb86b45d',
        group='change',
        label=_('Staying calm in difficult situations'),
        description=_(
            'When things become difficult, I try to stay calm and take one thing at a time.'
        ),
    ),
    'initiative': BehaviourHelp(
        esco_id='001115fb-569f-4ee6-8381-c6807ef2527f',
        group='change',
        label=_('Taking useful initiatives'),
        description=_(
            'I suggest ideas or take useful action while respecting the instructions.'
        ),
    ),
}

_BY_ESCO_ID = {item.esco_id: item for item in BEHAVIOURS.values()}


def for_uri(uri):
    """Find the reading aid for a complete ESCO URI, keeping external IDs stable."""
    return _BY_ESCO_ID.get(uri.rsplit('/', 1)[-1])
