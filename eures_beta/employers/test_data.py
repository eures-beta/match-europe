"""Small reusable fictional offer fixture, never loaded from a migration."""

import uuid
from django.utils import timezone
from .models import Company, CompanyMembership, JobOffer


def seed_test_offers(employer):
    company, _ = Company.objects.get_or_create(name='Fictional test workspace')
    CompanyMembership.objects.get_or_create(company=company, person=employer)
    for key, title, description in (
        (
            'cleaner',
            'Cleaner — fictional offer',
            'Fictional cleaning position for testing only.',
        ),
        (
            'baker',
            'Baker — fictional offer',
            'Fictional bakery position for testing only.',
        ),
    ):
        JobOffer.objects.get_or_create(
            id=uuid.uuid5(uuid.NAMESPACE_URL, 'match-europe.test-offer.' + key),
            defaults={
                'company': company,
                'created_by': employer,
                'session_key': '',
                'email': employer.email,
                'preparation_agreed_at': timezone.now(),
                'source_kind': 'manual',
                'contact': {'email': employer.email},
                'data': {'title': title, 'description': description},
            },
        )
