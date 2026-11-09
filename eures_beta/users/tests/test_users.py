from django.contrib.auth import authenticate, get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

User = get_user_model()


class UserTests(TestCase):
    def test_email_is_normalised_and_password_authentication_is_disabled(self):
        user = User.objects.create_user(
            email='Contact@Example.invalid',
            kind='employer',
            password='fictional-password',
        )
        self.assertEqual(user.email, 'contact@example.invalid')
        self.assertIsNone(
            authenticate(
                username='CONTACT@example.invalid', password='fictional-password'
            ),
        )
        self.assertFalse(hasattr(user, 'profile'))
        self.assertFalse(hasattr(user, 'username') and user.username is not None)

    def test_case_insensitive_unique_email_is_enforced_in_database(self):
        User.objects.create_user(email='contact@example.invalid', kind='employer')
        with self.assertRaises(IntegrityError), transaction.atomic():
            User.objects.bulk_create(
                [User(email='CONTACT@example.invalid', kind='adviser')]
            )

    def test_kind_is_required_and_limited_even_without_model_validation(self):
        for kind in ('', 'admin', 'unknown'):
            with (
                self.subTest(kind=kind),
                self.assertRaises(IntegrityError),
                transaction.atomic(),
            ):
                User.objects.bulk_create(
                    [User(email='role@example.invalid', kind=kind)]
                )
        with self.assertRaises(TypeError):
            User.objects.create_user(email='missing@example.invalid')

    def test_candidate_is_supported_by_manager_and_database_without_privileges(self):
        user = User.objects.create_user(
            email='Candidate@Example.invalid', kind='candidate'
        )
        self.assertEqual(user.email, 'candidate@example.invalid')
        self.assertFalse(user.has_usable_password())
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertFalse(user.groups.exists())
        self.assertFalse(user.user_permissions.exists())
        User.objects.bulk_create(
            [User(email='direct-candidate@example.invalid', kind='candidate')]
        )
        self.assertEqual(User.objects.filter(kind='candidate').count(), 2)

    def test_candidate_kind_cannot_change_or_replace_an_existing_kind(self):
        candidate = User.objects.create_user(
            email='candidate@example.invalid', kind='candidate'
        )
        employer = User.objects.create_user(
            email='employer@example.invalid', kind='employer'
        )
        for user, target in ((candidate, 'employer'), (employer, 'candidate')):
            with self.subTest(source=user.kind, target=target):
                user.kind = target
                with self.assertRaises(ValidationError):
                    user.save()
                with self.assertRaises(IntegrityError), transaction.atomic():
                    User.objects.filter(pk=user.pk).update(kind=target)
                user.refresh_from_db()
                self.assertNotEqual(user.kind, target)

    def test_candidate_cannot_use_employer_workspace_or_adviser_invitations(self):
        from django.test import RequestFactory
        from eures_beta.employers.employer_ownership import identity

        user = User.objects.create_user(
            email='candidate@example.invalid', kind='candidate'
        )
        request = RequestFactory().get('/')
        request.user = user
        self.assertIsNone(identity(request))
        self.client.force_login(user)
        self.assertEqual(
            self.client.get('/accounts/employers/invite/').status_code, 403
        )

    def test_candidate_dashboard_does_not_enter_employer_workspace(self):
        from unittest.mock import patch

        user = User.objects.create_user(
            email='candidate@example.invalid', kind='candidate'
        )
        self.client.force_login(user)
        with patch('eures_beta.employers.dashboard.employer_dashboard') as employer:
            response = self.client.get('/accounts/dashboard/')
        employer.assert_not_called()
        self.assertRedirects(
            response, '/candidate/start/', fetch_redirect_response=False
        )

    def test_candidate_label_is_translated(self):
        from django.utils.translation import override

        for language, label in [
            ('fr', 'Candidat'),
            ('en', 'Candidate'),
            ('de', 'Kandidat'),
        ]:
            with self.subTest(language=language), override(language):
                self.assertEqual(str(User.Kind.CANDIDATE.label), label)

    def test_kind_is_immutable_for_save_and_bulk_update(self):
        user = User.objects.create_user(email='role@example.invalid', kind='employer')
        user.kind = 'adviser'
        with self.assertRaises(ValidationError):
            user.save()
        with self.assertRaises(IntegrityError), transaction.atomic():
            User.objects.filter(pk=user.pk).update(kind='adviser')
        user.refresh_from_db()
        self.assertEqual(user.kind, 'employer')

    def test_default_password_is_unusable_and_privileges_are_separate(self):
        user = User.objects.create_user(email='role@example.invalid', kind='adviser')
        self.assertFalse(user.has_usable_password())
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_kind_labels_are_translated(self):
        from django.utils.translation import override

        for language, label in [
            ('fr', 'Conseiller'),
            ('en', 'Adviser'),
            ('de', 'Berater'),
        ]:
            with self.subTest(language=language), override(language):
                self.assertEqual(str(User.Kind.ADVISER.label), label)

    def test_adviser_cannot_use_employer_workspace(self):
        from eures_beta.employers.employer_ownership import identity
        from django.test import RequestFactory

        user = User.objects.create_user(email='adviser@example.invalid', kind='adviser')
        request = RequestFactory().get('/')
        request.user = user
        self.assertIsNone(identity(request))
        user.is_active = False
        user.save()
        self.assertIsNone(authenticate(username=user.email, password='unused'))
