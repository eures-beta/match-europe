"""Human-readable, read-only employer offer information for active advisers."""

from django.utils import formats, timezone
from django.utils.translation import gettext as _

from eures_beta.skills.continuous import summary as skills_summary
from eures_beta.candidates.forms import (
    ConditionsForm,
    ProjectForm,
    SCHEDULE_DAYS,
    SCHEDULE_PERIODS,
)
from eures_beta.users.admin_base import redact
from eures_beta.www.employer.forms import EmployerContactForm
from eures_beta.www.employer.workspace import OfferEditForm


def offer_details(offer, language):
    fields = []
    for field in OfferEditForm(offer=offer):
        if field.name in ('revision', 'title', 'occupationSkills'):
            continue
        value = field.value()
        choices = dict(getattr(field.field, 'choices', []))
        if isinstance(value, (list, tuple)):
            value = ', '.join(str(choices.get(item, item)) for item in value)
        elif choices and value:
            value = choices.get(value, value)
        fields.append((field.label, value or _('Not provided')))

    occupation = offer.data.get('occupation', {})
    references = [job.get('label', '') for job in occupation.get('jobs', [])]
    fields.extend(
        [
            (
                _('Occupation references'),
                '\n'.join(filter(None, references)) or _('Not provided'),
            ),
            (
                _('ROME codes'),
                ', '.join(occupation.get('rome_codes', [])) or _('Not provided'),
            ),
            (
                _('Personal job description'),
                occupation.get('personal') or _('Not provided'),
            ),
            (
                _('Skills by occupation'),
                skills_summary(offer.data.get('occupationSkills'), language)
                or _('Not provided'),
            ),
        ]
    )
    contact = [
        (
            _('Account email'),
            offer.created_by.email if offer.created_by_id else _('Not provided'),
        )
    ]
    contact.extend(
        (field.label, field.value() or _('Not provided'))
        for field in EmployerContactForm(initial=offer.contact)
        if field.name != 'email'
    )
    metadata = [
        (_('Telephone confirmation'), offer.phone_confirmed_on or _('Not provided')),
        (
            _('Confirmation recorded by'),
            (offer.adviser.email if offer.adviser else _('Not provided')),
        ),
        (_('Confirmed revision'), offer.phone_confirmed_revision or _('Not provided')),
        (_('Offer reference'), str(offer.pk)),
        (
            _('Company workspace'),
            offer.company.name if offer.company else _('Not provided'),
        ),
        (
            _('Created by'),
            offer.created_by.email if offer.created_by else _('Not provided'),
        ),
        (_('Adviser'), offer.adviser.email if offer.adviser else _('Not provided')),
        (
            _('Source'),
            {
                'manual': _('Manual entry'),
                'pdf': _('PDF import'),
                'url': _('URL import'),
            }.get(offer.source_kind, _('Not provided')),
        ),
        (_('Source URL'), redact(offer.source_url) or _('Not provided')),
        (_('Revision'), offer.revision),
    ]
    for label, value in [
        (_('Created'), offer.created),
        (_('Updated'), offer.updated),
        (_('Preparation agreed'), offer.preparation_agreed_at),
        (_('Validated'), offer.validated_at),
        (_('Search started'), offer.search_started_at),
        (_('Initial transmission'), offer.initial_sent_at),
        (_('Last synchronisation'), offer.synced_at),
    ]:
        metadata.append(
            (
                label,
                (
                    formats.date_format(timezone.localtime(value), 'DATETIME_FORMAT')
                    if value
                    else _('Not provided')
                ),
            )
        )
    groups = [(_('Contact'), contact), (_('Job and working conditions'), fields)]
    questions = [
        (
            question['question'],
            _('Required') if question.get('mandatory') else _('Optional'),
        )
        for question in offer.data.get('questions', [])
    ]
    if questions:
        groups.append((_('Questions for candidates'), questions))
    requirements = structured_details(offer.structured_requirements)
    if requirements:
        groups.append((_('Explicit matching requirements'), requirements))
    groups.append((_('Tracking'), metadata))
    return groups


def structured_details(requirements):
    rows = []
    conditions = ConditionsForm().fields
    countries = dict(ProjectForm.base_fields['desired_countries'].choices)
    days, periods = dict(SCHEDULE_DAYS), dict(SCHEDULE_PERIODS)
    for key, label in [
        ('country', _('Country')),
        ('latest_start', _('Latest start date')),
        ('mandatory_permits', _('Required licences')),
    ]:
        value = requirements.get(key)
        if value:
            if isinstance(value, list):
                value = ', '.join(value)
            rows.append((label, countries.get(value, value)))
    for key, label in [
        ('start_mandatory', _('Start date required')),
        ('schedule_mandatory', _('Schedule required')),
    ]:
        if key in requirements:
            rows.append((label, _('Yes') if requirements[key] else _('No')))
    if requirements.get('languages'):
        rows.append(
            (
                _('Languages and levels'),
                ', '.join(
                    row['code'].upper() + ' ' + row['level']
                    for row in requirements['languages']
                ),
            )
        )
    if requirements.get('schedule'):
        rows.append(
            (
                _('Working hours'),
                '\n'.join(
                    str(days[day]) + ' — ' + str(periods[period])
                    for slot in requirements['schedule']
                    for day, period in [slot.split(':')]
                ),
            )
        )
    salary = requirements.get('salary')
    if salary:
        rows.append(
            (
                _('Maximum salary'),
                ' '.join(
                    [
                        str(salary['maximum']),
                        salary['currency'],
                        str(
                            dict(conditions['salary_period'].choices)[salary['period']]
                        ),
                        str(dict(conditions['salary_basis'].choices)[salary['basis']]),
                    ]
                ),
            )
        )
    return rows
