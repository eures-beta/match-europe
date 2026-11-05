from django.db import connection, IntegrityError, transaction
from django.db.migrations.executor import MigrationExecutor
from django.db.migrations.recorder import MigrationRecorder
from django.test import TransactionTestCase


class CandidateProfileMigrationTests(TransactionTestCase):
    def test_registration_upgrade_keeps_existing_profiles_unverified(self):
        apps = self.migrate(('candidates', '0001_initial'))
        User = apps.get_model('users', 'User')
        user = User.objects.create(
            email='old-profile@example.invalid', kind='candidate', password='!'
        )
        Profile = apps.get_model('candidates', 'CandidateProfile')
        old = Profile.objects.create(
            user_id=user.pk, display_name='Preserved fictional name'
        )
        apps = self.migrate(
            ('candidates', '0003_candidateprofile_email_verified_at_and_more')
        )
        current = apps.get_model('candidates', 'CandidateProfile').objects.get(
            pk=old.pk
        )
        self.assertEqual(current.display_name, 'Preserved fictional name')
        self.assertIsNone(current.email_verified_at)
        self.assertIsNone(current.notice_read_at)
        self.assertEqual(current.notice_version, '')
        self.assertEqual(
            apps.get_model('candidates', 'CandidateRegistration').objects.count(), 0
        )
        self.migrate(('candidates', '0001_initial'))
        self.assertNotIn(
            'candidates_candidateregistration', connection.introspection.table_names()
        )
        self.assertEqual(
            User.objects.get(pk=user.pk).email, 'old-profile@example.invalid'
        )

    def migrate(self, target):
        executor = MigrationExecutor(connection)
        executor.migrate([target])
        executor = MigrationExecutor(connection)
        return executor.loader.project_state(
            list(executor.loader.applied_migrations)
        ).apps

    def tearDown(self):
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())
        super().tearDown()

    def test_add_and_reverse_empty_table_preserves_accounts(self):
        apps = self.migrate(('candidates', None))
        User = apps.get_model('users', 'User')
        account = User.objects.create(
            email='migration@example.test', kind='candidate', password='!'
        )
        original = list(User.objects.filter(pk=account.pk).values())
        apps = self.migrate(('candidates', '0001_initial'))
        Profile = apps.get_model('candidates', 'CandidateProfile')
        self.assertEqual(Profile.objects.count(), 0)
        self.assertEqual(list(User.objects.filter(pk=account.pk).values()), original)
        employer = User.objects.create(
            email='employer-migration@example.test', kind='employer', password='!'
        )
        with self.assertRaises(IntegrityError), transaction.atomic():
            Profile.objects.create(user_id=employer.pk)
        self.migrate(('candidates', None))
        self.assertNotIn(
            'candidates_candidateprofile', connection.introspection.table_names()
        )
        self.assertEqual(list(User.objects.filter(pk=account.pk).values()), original)

    def test_retired_initial_migration_does_not_skip_profile_creation(self):
        apps = self.migrate(('candidates', None))
        User = apps.get_model('users', 'User')
        account = User.objects.create(
            email='historical@example.invalid', kind='candidate', password='!'
        )
        original = list(User.objects.filter(pk=account.pk).values())
        recorder = MigrationRecorder(connection)
        # The retired prototype used these names, then deleted its tables.
        recorder.record_applied('candidates', '0001_initial')
        recorder.record_applied('candidates', '0002_delete_candidate')
        try:
            executor = MigrationExecutor(connection)
            executor.migrate(executor.loader.graph.leaf_nodes())
            apps = executor.loader.project_state().apps
            Profile = apps.get_model('candidates', 'CandidateProfile')
            self.assertEqual(Profile.objects.count(), 0)
            self.assertEqual(
                list(User.objects.filter(pk=account.pk).values()), original
            )
            employer = User.objects.create(
                email='historical-employer@example.invalid',
                kind='employer',
                password='!',
            )
            with self.assertRaises(IntegrityError), transaction.atomic():
                Profile.objects.create(user_id=employer.pk)
        finally:
            recorder.record_unapplied('candidates', '0002_delete_candidate')
            # Restore even on the intentionally failing pre-fix revision.
            if (
                'candidates_candidateprofile'
                not in connection.introspection.table_names()
            ):
                recorder.record_unapplied('candidates', '0001_initial')
                executor = MigrationExecutor(connection)
                executor.migrate(executor.loader.graph.leaf_nodes())

    def test_existing_profile_is_preserved_by_reconciliation_and_its_reverse(self):
        apps = self.migrate(('candidates', '0001_initial'))
        User = apps.get_model('users', 'User')
        account = User.objects.create(
            email='preserved@example.invalid', kind='candidate', password='!'
        )
        Profile = apps.get_model('candidates', 'CandidateProfile')
        profile = Profile.objects.create(user_id=account.pk, display_name='Fictional')
        original = list(Profile.objects.filter(pk=profile.pk).values())
        self.migrate(('candidates', '0002_ensure_candidate_profile_schema'))
        self.assertEqual(list(Profile.objects.filter(pk=profile.pk).values()), original)
        self.migrate(('candidates', '0001_initial'))
        self.assertEqual(list(Profile.objects.filter(pk=profile.pk).values()), original)
