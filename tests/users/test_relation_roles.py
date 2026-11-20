"""Role-specific relations reject bypass writes and keep nonempty migration data."""

from io import StringIO
from django.core import signing
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import connection, IntegrityError, transaction
from django.db.migrations.executor import MigrationExecutor
from django.test import TestCase, TransactionTestCase, override_settings
from eures_beta.employers.models import JobOffer
from eures_beta.invitations.models import Invitation
from eures_beta.matching.models import (
    CandidateOfferReview,
    CandidateSupport,
    JobOfferSupport,
)
from eures_beta.users.models import User

DEMO = dict(
    DEMO_ACCOUNTS_ENABLED=True, DJANGO_ENVIRONMENT='local', EMAIL_DELIVERY_ENABLED=False
)


@override_settings(**DEMO)
class RelationRoleTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed_test_accounts', stdout=StringIO())
        cls.adviser = User.objects.filter(kind='adviser').first()
        cls.employer = User.objects.filter(kind='employer').first()
        cls.candidate = User.objects.filter(kind='candidate').first()
        cls.offer = JobOffer.objects.first()
        cls.review = CandidateOfferReview.objects.select_related(
            'match__candidate'
        ).first()

    def test_owner_is_an_employer_even_when_an_adviser_deposits_the_offer(self):
        self.offer.adviser = self.adviser
        self.offer.save()
        for person in (self.adviser, self.candidate):
            with self.subTest(kind=person.kind):
                with self.assertRaises(IntegrityError), transaction.atomic():
                    JobOffer.objects.filter(pk=self.offer.pk).update(employer=person)
                self.offer.employer = person
                with self.assertRaises(ValidationError):
                    self.offer.save()
        with self.assertRaises(IntegrityError), transaction.atomic():
            JobOffer.objects.filter(pk=self.offer.pk).update(adviser=self.employer)
        self.offer.refresh_from_db()
        self.assertEqual(self.offer.employer.kind, 'employer')
        self.assertEqual(self.offer.adviser, self.adviser)

    def test_support_edits_and_responsibility_are_only_attributed_to_advisers(self):
        rows = [
            (CandidateOfferReview, self.review.pk, 'assigned_to_adviser'),
            (
                JobOfferSupport,
                JobOfferSupport.objects.create(
                    job_offer=self.offer, updated_by_adviser=self.adviser
                ).pk,
                'updated_by_adviser',
            ),
            (
                CandidateSupport,
                CandidateSupport.objects.create(
                    candidate_profile=self.review.match.candidate,
                    updated_by_adviser=self.adviser,
                ).pk,
                'updated_by_adviser',
            ),
        ]
        for model, pk, field in rows:
            model.objects.filter(pk=pk).update(**{field: self.adviser})
            for person in (self.employer, self.candidate):
                with self.subTest(model=model.__name__, kind=person.kind):
                    with self.assertRaises(IntegrityError), transaction.atomic():
                        model.objects.filter(pk=pk).update(**{field: person})
                    instance = model.objects.get(pk=pk)
                    setattr(instance, field, person)
                    with self.assertRaises(ValidationError):
                        instance.save()
        CandidateOfferReview.objects.filter(pk=self.review.pk).update(
            assigned_to_adviser=None
        )

    def test_invitation_sender_is_an_adviser_but_recipient_can_have_any_invited_role(
        self,
    ):
        invitation = Invitation.objects.create(
            email='role-invitation@example.invalid', sender_adviser=self.adviser
        )
        for person in (self.employer, self.candidate):
            with self.subTest(kind=person.kind):
                with self.assertRaises(IntegrityError), transaction.atomic():
                    Invitation.objects.filter(pk=invitation.pk).update(
                        sender_adviser=person
                    )
                with self.assertRaises(IntegrityError), transaction.atomic():
                    Invitation.objects.bulk_create(
                        [
                            Invitation(
                                email='bulk-role@example.invalid', sender_adviser=person
                            )
                        ]
                    )
                with self.assertRaises(ValidationError):
                    Invitation.objects.create(
                        email='save-role@example.invalid', sender_adviser=person
                    )
        for kind in Invitation.RecipientKind.values:
            Invitation.objects.create(
                email=kind + '-role@example.invalid',
                sender_adviser=self.adviser,
                recipient_kind=kind,
            )

    def test_deactivating_an_adviser_preserves_valid_historical_attribution(self):
        invitation = Invitation.objects.create(
            email='historical-role@example.invalid', sender_adviser=self.adviser
        )
        self.adviser.is_active = False
        self.adviser.save(update_fields=['is_active'])
        invitation.save()
        self.assertEqual(invitation.sender_adviser_id, self.adviser.pk)


@override_settings(**DEMO)
class RelationRoleMigrationTests(TransactionTestCase):
    def migrate(self, targets):
        executor = MigrationExecutor(connection)
        executor.migrate(targets)
        return executor.loader.project_state(targets).apps

    def tearDown(self):
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())
        super().tearDown()

    def test_nonempty_round_trip_preserves_rows_and_physical_objects(self):
        call_command('seed_test_accounts', stdout=StringIO())
        adviser = User.objects.filter(kind='adviser').first()
        offer = JobOffer.objects.first()
        review = CandidateOfferReview.objects.first()
        review.assigned_to_adviser = adviser
        review.save()
        JobOfferSupport.objects.create(job_offer=offer, updated_by_adviser=adviser)
        CandidateSupport.objects.create(
            candidate_profile=review.match.candidate, updated_by_adviser=adviser
        )
        Invitation.objects.create(
            email='roundtrip-role@example.invalid', sender_adviser=adviser
        )
        executor = MigrationExecutor(connection)
        targets = [
            key
            for key in executor.loader.disk_migrations
            if key[1].endswith('_explicit_user_relations')
        ]
        self.assertEqual(len(targets), 3)
        before = [
            dependency
            for key in targets
            for dependency in executor.loader.disk_migrations[key].dependencies
        ]
        mappings = [
            ('employers', 'JobOffer', 'created_by', 'employer'),
            ('invitations', 'Invitation', 'sender', 'sender_adviser'),
            ('matching', 'CandidateOfferReview', 'assigned_to', 'assigned_to_adviser'),
            ('matching', 'JobOfferSupport', 'updated_by', 'updated_by_adviser'),
            ('matching', 'CandidateSupport', 'updated_by', 'updated_by_adviser'),
        ]

        def snapshot(apps, modern):
            result = []
            for app, name, old, new in mappings:
                model = apps.get_model(app, name)
                rows = list(model.objects.order_by('pk').values())
                if not modern:
                    for row in rows:
                        row[new + '_id'] = row.pop(old + '_id')
                with connection.cursor() as cursor:
                    cursor.execute('SELECT %s::regclass::oid', [model._meta.db_table])
                    oid = cursor.fetchone()[0]
                    cursor.execute(
                        "SELECT oid FROM pg_constraint WHERE conrelid=%s AND contype IN ('p','f','u') ORDER BY oid",
                        [oid],
                    )
                    constraints = cursor.fetchall()
                    cursor.execute(
                        'SELECT indexrelid FROM pg_index WHERE indrelid=%s ORDER BY indexrelid',
                        [oid],
                    )
                    indexes = cursor.fetchall()
                result.append((rows, oid, constraints, indexes))
            return result

        modern = snapshot(executor.loader.project_state(targets).apps, True)
        old = self.migrate(before)
        old_invitation = old.get_model('invitations', 'Invitation').objects.get(
            email='roundtrip-role@example.invalid'
        )
        token = signing.dumps(
            {'id': str(old_invitation.pk), 'nonce': str(old_invitation.nonce)},
            salt='users.employer-invitation.v1',
        )
        self.assertEqual(snapshot(old, False), modern)
        current = self.migrate(targets)
        from eures_beta.invitations.services import find_invitation

        self.assertEqual(find_invitation(token).pk, old_invitation.pk)
        self.assertEqual(snapshot(current, True), modern)
        with connection.cursor() as cursor:
            for app, name, old_field, new_field in mappings:
                table = current.get_model(app, name)._meta.db_table
                objects = connection.introspection.get_constraints(cursor, table)
                related = [
                    (key, item)
                    for key, item in objects.items()
                    if item['columns'] == [new_field + '_id']
                ]
                self.assertTrue(related)
                for key, item in related:
                    self.assertIn(new_field + '_id', key)
                    self.assertNotIn(old_field + '_id', key)
        self.assertEqual(snapshot(current, True), modern)
        self.assertEqual(snapshot(self.migrate(before), False), modern)
        self.assertEqual(snapshot(self.migrate(targets), True), modern)

    def test_migration_refuses_historical_wrong_roles_without_reassigning_them(self):
        call_command('seed_test_accounts', stdout=StringIO())
        adviser = User.objects.filter(kind='adviser').first()
        candidate = User.objects.filter(kind='candidate').first()
        review = CandidateOfferReview.objects.first()
        invitation = Invitation.objects.create(
            email='invalid-old-role@example.invalid', sender_adviser=adviser
        )
        support = JobOfferSupport.objects.create(
            job_offer=review.match.offer, updated_by_adviser=adviser
        )
        executor = MigrationExecutor(connection)
        targets = [
            key
            for key in executor.loader.disk_migrations
            if key[1].endswith('_explicit_user_relations')
        ]
        before = [
            dep
            for key in targets
            for dep in executor.loader.disk_migrations[key].dependencies
        ]
        for app, name, pk, field in [
            ('invitations', 'Invitation', invitation.pk, 'sender'),
            ('matching', 'JobOfferSupport', support.pk, 'updated_by'),
            ('matching', 'CandidateOfferReview', review.pk, 'assigned_to'),
        ]:
            old = self.migrate(before)
            model = old.get_model(app, name)
            previous = getattr(model.objects.get(pk=pk), field + '_id')
            model.objects.filter(pk=pk).update(**{field + '_id': candidate.pk})
            try:
                with self.subTest(model=name), self.assertRaises(RuntimeError):
                    self.migrate(targets)
                self.assertEqual(
                    getattr(model.objects.get(pk=pk), field + '_id'), candidate.pk
                )
            finally:
                model.objects.filter(pk=pk).update(**{field + '_id': previous})
            self.migrate(targets)
