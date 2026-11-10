"""Existing offer requirements survive consolidation and rollback."""

from io import StringIO

from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TestCase, TransactionTestCase, override_settings

from eures_beta.employers.models import JobOffer


@override_settings(
    MATCHING_ENABLED=True,
    TEST_ACCOUNTS_ENABLED=True,
    DJANGO_ENVIRONMENT='local',
    EMAIL_DELIVERY_ENABLED=False,
    LOGIN_EMAIL_ENABLED=False,
    SHARED_DEMO=False,
)
class OfferRequirementsMigrationTests(TransactionTestCase):
    def migrate(self, name):
        executor = MigrationExecutor(connection)
        targets = [
            ('matching', name),
            ('employers', '0006_joboffer_structured_requirements'),
        ]
        executor.migrate(targets)
        return executor.loader.project_state(targets).apps

    def tearDown(self):
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())
        super().tearDown()

    def prepare(self):
        apps = self.migrate('0003_rename_match_decision')
        call_command('seed_matching_trial', stdout=StringIO())
        Offer = apps.get_model('employers', 'JobOffer')
        offer = Offer.objects.first()
        payload = offer.structured_requirements
        updated = offer.updated
        Offer.objects.filter(pk=offer.pk).update(structured_requirements={})
        apps.get_model('matching', 'OfferRequirements').objects.create(
            offer_id=offer.pk, data=payload
        )
        return apps, offer.pk, payload, updated

    def test_forward_reverse_preserve_requirements_offer_and_matching_links(self):
        apps, pk, payload, updated = self.prepare()
        pair_ids = list(
            apps.get_model('matching', 'MatchPair').objects.values_list('pk', flat=True)
        )
        apps = self.migrate('0004_merge_offer_requirements')
        offer = apps.get_model('employers', 'JobOffer').objects.get(pk=pk)
        self.assertEqual(offer.structured_requirements, payload)
        self.assertEqual(offer.updated, updated)
        self.assertNotIn(
            'matching_offerrequirements', connection.introspection.table_names()
        )
        self.assertEqual(
            list(
                apps.get_model('matching', 'MatchPair').objects.values_list(
                    'pk', flat=True
                )
            ),
            pair_ids,
        )
        apps = self.migrate('0003_rename_match_decision')
        self.assertEqual(
            apps.get_model('matching', 'OfferRequirements')
            .objects.get(offer_id=pk)
            .data,
            payload,
        )
        apps = self.migrate('0004_merge_offer_requirements')
        self.assertEqual(
            apps.get_model('employers', 'JobOffer')
            .objects.get(pk=pk)
            .structured_requirements,
            payload,
        )

    def test_conflicting_existing_values_are_not_overwritten(self):
        apps, pk, payload, _ = self.prepare()
        Offer = apps.get_model('employers', 'JobOffer')
        Offer.objects.filter(pk=pk).update(structured_requirements={'country': 'DE'})
        try:
            with self.assertRaisesMessage(RuntimeError, 'Conflicting requirements'):
                self.migrate('0004_merge_offer_requirements')
            self.assertEqual(
                Offer.objects.get(pk=pk).structured_requirements, {'country': 'DE'}
            )
            self.assertEqual(
                apps.get_model('matching', 'OfferRequirements')
                .objects.get(offer_id=pk)
                .data,
                payload,
            )
        finally:
            Offer.objects.filter(pk=pk).update(structured_requirements={})


class RequirementValidationTests(TestCase):
    def test_invalid_requirements_are_rejected_on_save_before_database_write(self):
        with self.assertRaises(ValidationError):
            JobOffer(structured_requirements={'start_mandatory': 'false'}).save()
        self.assertEqual(JobOffer.objects.count(), 0)
