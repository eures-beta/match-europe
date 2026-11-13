from django.db import connection, IntegrityError, transaction
from django.db.migrations.executor import MigrationExecutor
from django.db.migrations.recorder import MigrationRecorder
from django.test import TransactionTestCase


class CandidateProfileMigrationTests(TransactionTestCase):
    def test_occupation_skill_upgrade_preserves_existing_answers(self):
        apps = self.migrate(
            ('candidates', '0005_candidateprofile_acquired_skills_and_more')
        )
        user = apps.get_model('users', 'User').objects.create(
            email='existing@example.invalid', kind='candidate', password='!'
        )
        old = apps.get_model('candidates', 'CandidateProfile').objects.create(
            user_id=user.pk,
            display_name='Fictional preserved name',
            desired_occupations='Preserved project',
        )
        apps = self.migrate(('candidates', '0006_candidateprofile_occupation_skills'))
        profile = apps.get_model('candidates', 'CandidateProfile').objects.get(
            pk=old.pk
        )
        self.assertEqual(profile.occupation_skills, {})
        self.assertEqual(profile.desired_occupations, 'Preserved project')
        self.assertEqual(profile.display_name, 'Fictional preserved name')

    def test_skill_upgrade_preserves_legacy_profiles_and_reverse_keeps_accounts(self):
        old_apps = self.migrate(
            ('candidates', '0003_candidateprofile_email_verified_at_and_more')
        )
        user = old_apps.get_model('users', 'User').objects.create(
            email='legacy-skills@example.invalid', kind='candidate', password='!'
        )
        profile = old_apps.get_model('candidates', 'CandidateProfile').objects.create(
            user_id=user.pk,
            display_name='Preserved fictional candidate',
            desired_occupations='Preserved fictional job',
        )
        apps = self.migrate(
            ('candidates', '0005_candidateprofile_acquired_skills_and_more')
        )
        current = apps.get_model('candidates', 'CandidateProfile').objects.get(
            pk=profile.pk
        )
        self.assertEqual(current.project_mode, 'occupation')
        self.assertEqual(current.acquired_skills, [])
        self.assertEqual(current.learning_activities, [])
        self.assertEqual(current.professional_behaviours, [])
        self.assertEqual(current.skill_catalogue_version, '')
        self.assertEqual(current.desired_occupations, 'Preserved fictional job')
        apps = self.migrate(
            ('candidates', '0003_candidateprofile_email_verified_at_and_more')
        )
        self.assertTrue(
            apps.get_model('users', 'User').objects.filter(pk=user.pk).exists()
        )
        self.assertEqual(
            apps.get_model('candidates', 'CandidateProfile')
            .objects.get(pk=profile.pk)
            .desired_occupations,
            'Preserved fictional job',
        )

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

    def test_pending_answers_and_existing_links_survive_session_migration(self):
        from tests.candidates.test_registration import answers
        from eures_beta.candidates import registration

        apps = self.migrate(
            ('candidates', '0003_candidateprofile_email_verified_at_and_more')
        )
        Pending = apps.get_model('candidates', 'CandidateRegistration')
        old = Pending.objects.create(
            email='pending@example.invalid', answers=answers(), language='de'
        )
        token = registration.token_for(old)
        self.migrate(('candidates', '0004_confirmation_sessions'))
        self.assertNotIn(
            'candidates_candidateregistration', connection.introspection.table_names()
        )
        pending = registration.find_registration(token)
        self.assertEqual(pending.answers, old.answers)
        self.assertEqual(pending.language, 'de')
        self.assertEqual(pending.expires_at, old.expires_at)
        apps = self.migrate(
            ('candidates', '0003_candidateprofile_email_verified_at_and_more')
        )
        restored = apps.get_model('candidates', 'CandidateRegistration').objects.get(
            pk=old.pk
        )
        self.assertEqual(restored.answers, old.answers)
        self.assertEqual(restored.nonce, old.nonce)
        self.migrate(('candidates', '0004_confirmation_sessions'))

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
