"""Readable offer and candidate sheets, using the existing form labels."""

from django.utils import formats
from django.utils.translation import gettext as _, get_language_info
from eures_beta.candidates.registration import profile_answers
from eures_beta.www.candidate.registration import answer_groups
from eures_beta.www.employer.workspace import OfferEditForm
from eures_beta.www.employer.forms import EmployerContactForm
from eures_beta.skills.continuous import summary as skills_summary


def field_row(label, value):
    return {
        'label': label,
        'value': str(value),
        'wide': len(str(value)) > 100 or '\n' in str(value),
    }


def section(key, title, rows):
    return {'key': key, 'title': title, 'rows': rows}


def offer_details(offer, language):
    form = OfferEditForm(offer=offer)
    values = {}
    for field in form:
        if field.name in ('revision', 'occupationSkills'):
            continue
        value = field.value()
        choices = dict(getattr(field.field, 'choices', []))
        if isinstance(value, (list, tuple)):
            value = '\n'.join(str(choices.get(item, item)) for item in value)
        elif choices and value:
            value = choices.get(value, value)
        if value:
            values[field.name] = field_row(field.label, value)
    skills = skills_summary(offer.data.get('occupationSkills'), language)
    if skills:
        values['occupationSkills'] = field_row(_('Skills by occupation'), skills)
    groups = [
        (
            'position',
            _('The position'),
            ['description', 'desiredProfile', 'occupationSkills'],
        ),
        (
            'conditions',
            _('Employment conditions'),
            [
                'clarify_salary',
                'clarify_hours',
                'clarify_startDate',
                'clarify_experience',
                'clarify_frenchLevel',
                'workConditions',
            ],
        ),
        (
            'mobility',
            _('Mobility and arrival'),
            [
                'clarify_commute',
                'permitRequired',
                'permits',
                'permitOther',
                'crossBorder',
                'relocation',
                'arrivalAids',
                'aidOther',
            ],
        ),
    ]
    sections = [
        section(key, title, [values[name] for name in names if name in values])
        for key, title, names in groups
    ]
    contact = [
        field_row(field.label, field.value())
        for field in EmployerContactForm(initial=offer.contact)
        if field.value()
    ]
    sections.append(section('contact', _('Employer contact'), contact))
    return dict(
        record_type=_('Job offer'),
        record_summary=[
            values[key]
            for key in ('companyName', 'city', 'contractType')
            if key in values
        ],
        record_sections=sections,
    )


def candidate_details(profile, language):
    groups = answer_groups(profile_answers(profile), language)
    from eures_beta.candidates.forms import MobilityForm, ConditionsForm

    language_label = MobilityForm().fields['language_skills'].label
    date_label = ConditionsForm().fields['available_from'].label

    def human_value(label, value):
        if label == language_label and profile.language_skills.get('languages'):

            def name(code):
                try:
                    return get_language_info(code)['name_translated']
                except KeyError:
                    return code

            return '\n'.join(
                f"{name(row['code'])} — {row['level']}"
                for row in profile.language_skills['languages']
            )
        if label == date_label and profile.available_from:
            return formats.date_format(profile.available_from, 'SHORT_DATE_FORMAT')
        return value

    sections = [
        section(
            'profile-' + str(index),
            title,
            [field_row(label, human_value(label, value)) for label, value in rows],
        )
        for index, (title, rows) in enumerate(groups[1:], 1)
        if rows
    ]
    # Use questionnaire choices rather than exposing stored country/availability codes.
    from eures_beta.candidates.forms import ProjectForm, ConditionsForm

    project = ProjectForm(language=language)
    conditions = ConditionsForm()
    countries = dict(project.fields['desired_countries'].choices)
    availability = dict(conditions.fields['availability'].choices)
    summary = []
    if profile.desired_occupations:
        summary.append(field_row(_('Occupations sought'), profile.desired_occupations))
    elif profile.project_mode == 'open':
        summary.append(
            field_row(_('Professional project'), _('Open to different occupations'))
        )
    if profile.desired_countries:
        summary.append(
            field_row(
                _('Preferred countries'),
                ', '.join(
                    str(countries.get(code, code)) for code in profile.desired_countries
                ),
            )
        )
    if profile.availability:
        summary.append(
            field_row(
                _('Availability'),
                str(availability.get(profile.availability, profile.availability))
                + (
                    ' · '
                    + formats.date_format(profile.available_from, 'SHORT_DATE_FORMAT')
                    if profile.available_from
                    else ''
                ),
            )
        )
    return dict(
        record_type=_('Candidate profile'),
        record_summary=summary,
        record_sections=sections,
    )
