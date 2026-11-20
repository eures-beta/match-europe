"""A complete personal offer no longer needs an establishment to be matchable."""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from eures_beta.employers.models import JobOffer
from eures_beta.matching.access import matchable_offers


class PersonalOfferMatchingTests(TestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user(
            'owner@example.invalid', kind='employer'
        )
        self.offer = JobOffer.objects.create(
            employer=self.owner,
            session_key='',
            preparation_agreed_at=timezone.now(),
            source_kind='manual',
            data={
                'title': 'Baker',
                'companyName': 'Fictional bakery',
                'city': 'Metz',
                'description': 'Fictional job',
                'contractType': 'PERMANENT_CONTRACT',
            },
        )

    def test_complete_offer_is_eligible_without_an_establishment(self):
        self.assertEqual(list(matchable_offers()), [self.offer])
        self.offer.data['city'] = ''
        self.offer.save()
        self.assertFalse(matchable_offers().exists())

    def test_copy_requires_a_confirmed_edit_and_an_active_employer_owner(self):
        self.offer.duplicated_from = self.offer
        self.offer.save()
        self.assertFalse(matchable_offers().exists())
        self.offer.revision += 1
        self.offer.save()
        self.assertEqual(list(matchable_offers()), [self.offer])
        self.owner.is_active = False
        self.owner.save()
        self.assertFalse(matchable_offers().exists())

    def test_unowned_offer_is_never_matchable_even_if_validated(self):
        self.offer.employer = None
        self.offer.validated_at = timezone.now()
        self.offer.save()
        self.assertFalse(matchable_offers().exists())
