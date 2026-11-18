from datetime import date

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase
from django.utils import timezone


class SupportMigrationTests(TransactionTestCase):
    def migrate(self, name):
        executor = MigrationExecutor(connection)
        targets = [('matching', name)]
        executor.migrate(targets)
        return executor.loader.project_state(targets).apps

    def tearDown(self):
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())
        super().tearDown()

    def test_naming_roundtrip_preserves_the_search_and_foreign_keys(self):
        apps = self.migrate('0012_advisersearchfollowup')
        User = apps.get_model('users', 'User')
        employer = User.objects.create(
            email='employer@migration.invalid', kind='employer'
        )
        adviser = User.objects.create(email='adviser@migration.invalid', kind='adviser')
        offer = apps.get_model('employers', 'JobOffer').objects.create(
            created_by=employer,
            preparation_agreed_at=timezone.now(),
            source_kind='manual',
            email=employer.email,
            data={'title': 'Fictional migration offer'},
        )
        row = apps.get_model('matching', 'AdviserSearchFollowUp').objects.create(
            offer=offer,
            updated_by=adviser,
            searching=True,
            follow_up_on=date(2026, 11, 20),
        )
        for name in (
            '0013_search_followup_database_names',
            '0012_advisersearchfollowup',
            '0013_search_followup_database_names',
        ):
            apps = self.migrate(name)
            current = apps.get_model('matching', 'AdviserSearchFollowUp').objects.get(
                pk=row.pk
            )
            self.assertEqual(current.offer_id, offer.pk)
            self.assertEqual(current.updated_by_id, adviser.pk)
            self.assertEqual(current.follow_up_on, row.follow_up_on)
            self.assertTrue(current.searching)

    def test_explicit_field_names_preserve_shared_state_in_both_directions(self):
        apps = self.migrate('0013_search_followup_database_names')
        User = apps.get_model('users', 'User')
        adviser = User.objects.create(email='adviser@rename.invalid', kind='adviser')
        employer = User.objects.create(email='employer@rename.invalid', kind='employer')
        offer = apps.get_model('employers', 'JobOffer').objects.create(
            created_by=employer,
            preparation_agreed_at=timezone.now(),
            source_kind='manual',
            email=employer.email,
            data={'title': 'Fictional offer'},
        )
        old = apps.get_model('matching', 'AdviserSearchFollowUp').objects.create(
            offer=offer,
            updated_by=adviser,
            searching=True,
            follow_up_on=date(2026, 11, 20),
        )
        candidate_user = User.objects.create(
            email='candidate@rename.invalid', kind='candidate'
        )
        profile = apps.get_model('candidates', 'CandidateProfile').objects.create(
            user=candidate_user,
            desired_countries=[],
            contract_types=[],
            working_time=[],
            working_conditions=[],
        )
        candidate_followup = apps.get_model(
            'matching', 'AdviserSearchFollowUp'
        ).objects.create(
            candidate=profile,
            updated_by=adviser,
            searching=False,
        )
        for migration, renamed in [
            ('0014_explicit_search_followup_fields', True),
            ('0013_search_followup_database_names', False),
            ('0014_explicit_search_followup_fields', True),
        ]:
            apps = self.migrate(migration)
            row = apps.get_model('matching', 'AdviserSearchFollowUp').objects.get(
                pk=old.pk
            )
            self.assertEqual(
                getattr(row, 'job_offer_id' if renamed else 'offer_id'), offer.pk
            )
            self.assertTrue(getattr(row, 'is_searching' if renamed else 'searching'))
            self.assertEqual(row.updated_by_id, adviser.pk)
            self.assertEqual(row.follow_up_on, old.follow_up_on)
            self.assertEqual(row.updated_at, old.updated_at)
            other = apps.get_model('matching', 'AdviserSearchFollowUp').objects.get(
                pk=candidate_followup.pk
            )
            self.assertEqual(
                getattr(other, 'candidate_profile_id' if renamed else 'candidate_id'),
                profile.pk,
            )
            self.assertFalse(getattr(other, 'is_searching' if renamed else 'searching'))

    def test_split_support_preserves_both_targets_and_sequence_roundtrip(self):
        apps = self.migrate('0014_explicit_search_followup_fields')
        User = apps.get_model('users', 'User')
        adviser = User.objects.create(email='adviser@support.invalid', kind='adviser')
        employer = User.objects.create(
            email='employer@support.invalid', kind='employer'
        )
        candidate = User.objects.create(
            email='candidate@support.invalid', kind='candidate'
        )
        offer = apps.get_model('employers', 'JobOffer').objects.create(
            created_by=employer,
            preparation_agreed_at=timezone.now(),
            source_kind='manual',
            email=employer.email,
            data={'title': 'Fictional'},
        )
        profile = apps.get_model('candidates', 'CandidateProfile').objects.create(
            user=candidate,
            desired_countries=[],
            contract_types=[],
            working_time=[],
            working_conditions=[],
        )
        Old = apps.get_model('matching', 'AdviserSearchFollowUp')
        offer_support = Old.objects.create(
            id=101,
            job_offer=offer,
            is_searching=True,
            follow_up_on=date(2026, 11, 20),
            updated_by=adviser,
        )
        candidate_support = Old.objects.create(
            id=202,
            candidate_profile=profile,
            is_searching=False,
            follow_up_on=None,
            updated_by=adviser,
        )
        expected = {
            'JobOfferSupport': (offer_support, 'job_offer_id', offer.pk),
            'CandidateSupport': (candidate_support, 'candidate_profile_id', profile.pk),
        }
        for migration, split in [
            ('0015_job_offer_and_candidate_support', True),
            ('0014_explicit_search_followup_fields', False),
            ('0015_job_offer_and_candidate_support', True),
        ]:
            apps = self.migrate(migration)
            for name, (previous, field, target_id) in expected.items():
                model = apps.get_model(
                    'matching', name if split else 'AdviserSearchFollowUp'
                )
                row = model.objects.get(pk=previous.pk)
                self.assertEqual(getattr(row, field), target_id)
                for attr in (
                    'is_searching',
                    'follow_up_on',
                    'updated_by_id',
                    'updated_at',
                ):
                    self.assertEqual(getattr(row, attr), getattr(previous, attr))
                self.assertEqual(
                    model._meta.get_field(field.removesuffix('_id')).null, not split
                )
        # Explicit IDs copied by migration must advance each destination sequence.
        NewOffer = apps.get_model('employers', 'JobOffer')
        second_offer = NewOffer.objects.create(
            created_by_id=employer.pk,
            preparation_agreed_at=timezone.now(),
            source_kind='manual',
            email=employer.email,
            data={'title': 'Second'},
        )
        OfferSupport = apps.get_model('matching', 'JobOfferSupport')
        next_support = OfferSupport.objects.create(
            job_offer=second_offer, updated_by_id=adviser.pk
        )
        self.assertGreater(next_support.pk, offer_support.pk)
        # A post-split ID collision must block rollback atomically, without data loss.
        OfferSupport.objects.filter(pk=next_support.pk).update(id=candidate_support.pk)
        with self.assertRaisesMessage(RuntimeError, 'overlapping IDs'):
            self.migrate('0014_explicit_search_followup_fields')
        self.assertEqual(OfferSupport.objects.count(), 2)
        self.assertEqual(
            apps.get_model('matching', 'CandidateSupport').objects.count(), 1
        )
