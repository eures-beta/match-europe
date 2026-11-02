from django.contrib.auth import authenticate, get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

User = get_user_model()


class UserTests(TestCase):
    def test_email_authentication_uses_django_and_case_insensitive_identifier(self):
        user = User.objects.create_user(
            email='Contact@Example.invalid',
            kind='employer',
            password='fictional-password',
        )
        self.assertEqual(user.email, 'contact@example.invalid')
        self.assertEqual(
            authenticate(
                username='CONTACT@example.invalid', password='fictional-password'
            ),
            user,
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
        for kind in ('', 'candidate', 'admin'):
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
