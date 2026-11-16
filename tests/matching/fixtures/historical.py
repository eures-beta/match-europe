"""Small frozen rows for historical migration tests; never use the current ORM."""

from django.utils import timezone


def seed_matching(apps):
    def model(*names):
        for name in names:
            try:
                return apps.get_model('matching', name)
            except LookupError:
                pass
        raise LookupError(names)

    User = apps.get_model('users', 'User')
    employer = User.objects.create(
        email='historical-employer@example.invalid', kind='employer'
    )
    candidate = User.objects.create(
        email='historical-candidate@example.invalid', kind='candidate'
    )
    profile = apps.get_model('candidates', 'CandidateProfile').objects.create(
        user=candidate,
        display_name='Fictional candidate',
        language='fr',
        desired_countries=['FR'],
        mobility='discuss',
        availability='discuss',
        contract_types=['permanent'],
        working_time=['full'],
        schedule_preference='discuss',
        working_conditions=['day'],
        salary_preference='discuss',
    )
    Offer = apps.get_model('employers', 'JobOffer')
    values = dict(
        email=employer.email,
        created_by=employer,
        session_key='historical',
        preparation_agreed_at=timezone.now(),
        source_kind='text',
        data={},
    )
    if any(field.name == 'structured_requirements' for field in Offer._meta.fields):
        values['structured_requirements'] = {'country': 'FR'}
    offer = Offer.objects.create(**values)
    match = model('CandidateOfferMatch', 'MatchPair').objects.create(
        candidate=profile, offer=offer
    )
    Evaluation = model('MatchEvaluation', 'Evaluation')
    field = (
        'match'
        if any(field.name == 'match' for field in Evaluation._meta.fields)
        else 'pair'
    )
    Evaluation.objects.create(
        **{field: match}, fingerprint='a' * 64, rules_version='historical', result={}
    )
    return match
