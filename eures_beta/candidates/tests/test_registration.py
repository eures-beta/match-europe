from datetime import timedelta
from io import StringIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import Client, TestCase, override_settings
from django.test import TransactionTestCase
from django.db import close_old_connections, connections
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from django.urls import reverse
from django.utils import timezone

from eures_beta.candidates import registration
from eures_beta.candidates.journey import KEY
from eures_beta.candidates.models import CandidateProfile, CandidateRegistration

User = get_user_model()


def answers(**changes):
    return dict(
        display_name='Fictional candidate',
        desired_occupations='Fictional job',
        desired_countries=['FR'],
        mobility='discuss',
        availability='discuss',
        contract_types=['discuss'],
        working_time=['discuss'],
        schedule_preference='discuss',
        working_conditions=['discuss'],
        salary_preference='discuss',
        **changes,
    )


@override_settings(
    CANDIDATE_REGISTRATION_ENABLED=True,
    DJANGO_ENVIRONMENT='local',
    EMAIL_DELIVERY_ENABLED=False,
    DEMO_MODE=True,
    SHARED_DEMO=True,
)
class CandidateRegistrationTests(TestCase):
    def pending(self, email='candidate@example.invalid'):
        return registration.create_request(email, answers(), 'fr')

    def open_link(self, pending, client=None):
        client = client or self.client
        client.get(
            reverse('candidate_registration_confirm'),
            {'token': registration.token_for(pending)},
            secure=True,
        )
        return client.get(reverse('candidate_registration_confirm'), secure=True)

    def confirm(self, client=None):
        return (client or self.client).post(
            reverse('candidate_registration_confirm'), secure=True
        )

    def test_no_account_until_explicit_post_and_replay_is_rejected(self):
        pending = self.pending()
        token = registration.token_for(pending)
        self.assertEqual(User.objects.count(), 0)
        self.assertEqual(CandidateProfile.objects.count(), 0)
        response = self.open_link(pending)
        self.assertNotContains(response, token)
        self.assertEqual(response['Referrer-Policy'], 'same-origin')
        self.assertEqual(User.objects.count(), 0)
        self.assertEqual(CandidateRegistration.objects.count(), 1)
        self.assertRedirects(
            self.confirm(), reverse('candidate_profile'), fetch_redirect_response=False
        )
        user = User.objects.get()
        profile = user.candidate_profile
        self.assertEqual(user.kind, 'candidate')
        self.assertFalse(user.has_usable_password())
        self.assertIsNotNone(profile.email_verified_at)
        self.assertIsNotNone(profile.notice_read_at)
        self.assertEqual(profile.notice_version, '2026-11-05')
        self.assertEqual(profile.desired_occupations, 'Fictional job')
        self.assertEqual(CandidateRegistration.objects.count(), 0)
        self.client.get(
            reverse('candidate_registration_confirm'), {'token': token}, secure=True
        )
        self.assertContains(self.confirm(), 'invalide')
        self.assertEqual(User.objects.count(), 1)

    def test_expired_tampered_and_missing_tokens_do_not_create_accounts(self):
        pending = self.pending()
        token = registration.token_for(pending)
        for invalid in ('', token + 'tampered', 'x' * 600):
            self.client.get(
                reverse('candidate_registration_confirm'),
                {'token': invalid},
                secure=True,
            )
            self.assertContains(self.confirm(), 'invalide')
        pending.expires_at = timezone.now() - timedelta(seconds=1)
        pending.save()
        self.open_link(pending)
        self.assertContains(self.confirm(), 'invalide')
        self.assertEqual(User.objects.count(), 0)

    def test_confirmation_requires_csrf(self):
        pending = self.pending()
        client = Client(enforce_csrf_checks=True)
        self.open_link(pending, client)
        self.assertEqual(self.confirm(client).status_code, 403)
        self.assertEqual(User.objects.count(), 0)

    def test_profile_creation_failure_rolls_back_account_and_consumption(self):
        pending = self.pending()
        self.open_link(pending)
        with patch.object(
            CandidateProfile, 'save', side_effect=ValidationError('invalid')
        ):
            self.assertContains(self.confirm(), 'invalide')
        self.assertEqual(User.objects.count(), 0)
        self.assertTrue(CandidateRegistration.objects.filter(pk=pending.pk).exists())

    def test_existing_accounts_and_inactive_accounts_are_never_replaced(self):
        for kind, active in (
            ('employer', True),
            ('adviser', True),
            ('candidate', False),
        ):
            email = f'{kind}-{active}@example.invalid'
            user = User.objects.create_user(email=email, kind=kind, is_active=active)
            self.assertIsNone(
                registration.create_request(email.upper(), answers(), 'fr')
            )
            user.refresh_from_db()
            self.assertEqual(user.kind, kind)
            self.assertEqual(user.is_active, active)
        self.assertEqual(CandidateRegistration.objects.count(), 0)
        self.assertEqual(CandidateProfile.objects.count(), 0)

    def test_existing_active_candidate_without_profile_is_reused_after_verification(
        self,
    ):
        existing = User.objects.create_user(
            'candidate@example.invalid', kind='candidate'
        )
        pending = self.pending()
        self.assertIsNone(getattr(existing, 'candidate_profile', None))
        self.open_link(pending)
        self.assertEqual(self.confirm().status_code, 302)
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(CandidateProfile.objects.get().user_id, existing.pk)
        self.assertIsNone(registration.create_request(existing.email, answers(), 'fr'))

    def test_account_created_while_waiting_is_not_overwritten(self):
        pending = self.pending()
        self.open_link(pending)
        user = User.objects.create_user(email=pending.email, kind='employer')
        self.assertContains(self.confirm(), 'invalide')
        user.refresh_from_db()
        self.assertEqual(user.kind, 'employer')
        self.assertEqual(CandidateProfile.objects.count(), 0)

    def test_second_anonymous_request_cannot_replace_pending_answers(self):
        pending = self.pending()
        changed = answers()
        changed['display_name'] = 'Unrelated visitor'
        self.assertIsNone(registration.create_request(pending.email, changed, 'de'))
        pending.refresh_from_db()
        self.assertEqual(pending.answers['display_name'], 'Fictional candidate')
        self.assertEqual(pending.language, 'fr')

    def test_answers_are_revalidated_and_only_model_fields_are_kept(self):
        data = answers()
        data['desired_countries'] = ['INVALID']
        with self.assertRaises(ValidationError):
            registration.create_request('fiction@example.invalid', data, 'fr')
        data = answers()
        data['cv_text'] = 'must not persist'
        data['token'] = 'must not persist'
        pending = registration.create_request('fiction@example.invalid', data, 'fr')
        self.assertNotIn('cv_text', pending.answers)
        self.assertNotIn('token', pending.answers)
        with self.assertRaises(ValidationError):
            registration.create_request('real@example.com', answers(), 'fr')

    def test_pending_admin_only_exposes_metadata(self):
        from django.contrib import admin
        from django.test import RequestFactory

        pending = self.pending()
        operator = User.objects.create_superuser(
            'operator@example.invalid', kind='adviser'
        )
        request = RequestFactory().get('/')
        request.user = operator
        model_admin = admin.site._registry[CandidateRegistration]
        self.assertTrue(model_admin.has_view_permission(request))
        self.assertFalse(model_admin.has_view_permission(request, pending))
        self.assertFalse(model_admin.has_add_permission(request))
        self.assertFalse(model_admin.has_change_permission(request, pending))
        self.assertFalse(model_admin.has_delete_permission(request, pending))
        self.assertEqual(model_admin.list_display, ('id', 'created_at', 'expires_at'))

    def test_profile_is_private_and_edit_does_not_create_another_account(self):
        pending = self.pending()
        self.open_link(pending)
        self.confirm()
        user = User.objects.get()
        self.assertContains(
            self.client.get(reverse('candidate_profile'), secure=True), 'Fictional job'
        )
        outsider = Client()
        self.assertEqual(
            outsider.get(reverse('candidate_profile'), secure=True).status_code, 302
        )
        employer = User.objects.create_user(
            email='employer@example.invalid', kind='employer'
        )
        outsider.force_login(employer)
        self.assertEqual(
            outsider.get(reverse('candidate_profile'), secure=True).status_code, 403
        )
        self.assertEqual(
            outsider.post(reverse('candidate_profile_edit'), secure=True).status_code,
            403,
        )
        self.assertEqual(
            self.client.get(reverse('candidate_profile_edit'), secure=True).status_code,
            405,
        )
        self.client.post(reverse('candidate_profile_edit'), secure=True)
        draft = self.client.session[KEY]
        response = self.client.post(
            '/candidate/prepare/?step=4&lang=fr',
            {
                'action': 'finish',
                'token': draft['token'],
                'display_name': 'Updated fictional name',
                'reviewed': 'on',
                'contact_email': 'other@example.invalid',
            },
            secure=True,
        )
        self.assertRedirects(
            response, reverse('candidate_profile'), fetch_redirect_response=False
        )
        profile = CandidateProfile.objects.get(user=user)
        self.assertEqual(profile.display_name, 'Updated fictional name')
        self.assertEqual(
            User.objects.get(pk=user.pk).email, 'candidate@example.invalid'
        )
        self.assertEqual(CandidateProfile.objects.count(), 1)

    def test_expiry_cleanup_is_dry_run_by_default_and_preserves_valid_requests(self):
        expired = self.pending()
        CandidateRegistration.objects.filter(pk=expired.pk).update(
            expires_at=timezone.now() - timedelta(seconds=1)
        )
        valid = registration.create_request('second@example.invalid', answers(), 'fr')
        # Creation opportunistically removed expired data. Recreate an expired test record.
        expired = CandidateRegistration.objects.create(
            email='expired@example.invalid',
            answers={},
            expires_at=timezone.now() - timedelta(seconds=1),
        )
        output = StringIO()
        call_command('cleanup_candidate_registrations', stdout=output)
        self.assertTrue(CandidateRegistration.objects.filter(pk=expired.pk).exists())
        call_command('cleanup_candidate_registrations', apply=True, stdout=output)
        self.assertFalse(CandidateRegistration.objects.filter(pk=expired.pk).exists())
        self.assertTrue(CandidateRegistration.objects.filter(pk=valid.pk).exists())

    def test_email_simulation_is_private_and_validates_origin(self):
        pending = self.pending()
        output = StringIO()
        with override_settings(DEBUG=True, ALLOWED_HOSTS=['127.0.0.1']):
            call_command(
                'candidate_email',
                pending.email,
                origin='http://127.0.0.1:9035',
                stdout=output,
            )
            self.assertIn('/candidate/registration/confirm/?token=', output.getvalue())
            with self.assertRaises(CommandError):
                call_command(
                    'candidate_email',
                    pending.email,
                    origin='https://attacker.invalid',
                    stdout=StringIO(),
                )
        response = self.client.get(
            reverse('candidate_registration_requested'), secure=True
        )
        self.assertNotContains(response, registration.token_for(pending))
        self.assertNotContains(response, pending.email)

    def test_feature_off_and_production_refuse_all_new_endpoints(self):
        for settings in (
            {'CANDIDATE_REGISTRATION_ENABLED': False},
            {'DJANGO_ENVIRONMENT': 'production'},
            {'EMAIL_DELIVERY_ENABLED': True},
        ):
            with override_settings(**settings):
                for name in (
                    'candidate_registration_requested',
                    'candidate_registration_confirm',
                    'candidate_profile',
                ):
                    self.assertEqual(
                        self.client.get(reverse(name), secure=True).status_code, 404
                    )

    def test_questionnaire_submits_to_pending_instead_of_creating_an_account(self):
        self.client.get('/candidate/prepare/?lang=fr', secure=True)
        for step, data in (
            (1, {'desired_occupations': 'Fictional job', 'desired_countries': ['FR']}),
            (2, {'mobility': 'discuss'}),
            (
                3,
                {
                    'availability': 'discuss',
                    'contract_types': ['discuss'],
                    'working_time': ['discuss'],
                    'schedule_preference': 'discuss',
                    'working_conditions': ['discuss'],
                    'salary_preference': 'discuss',
                },
            ),
            (
                4,
                {
                    'display_name': 'Fictional candidate',
                    'contact_email': 'candidate@example.invalid',
                    'reviewed': 'on',
                },
            ),
        ):
            draft = self.client.session[KEY]
            response = self.client.post(
                f'/candidate/prepare/?step={step}&lang=fr',
                {
                    'token': draft['token'],
                    'action': 'finish' if step == 4 else 'continue',
                    **data,
                },
                secure=True,
            )
            self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('candidate_registration_requested'))
        self.assertEqual(CandidateRegistration.objects.count(), 1)
        self.assertEqual(User.objects.count(), 0)
        self.assertNotIn(KEY, self.client.session)

    def test_registration_pages_and_email_are_translated(self):
        for language, title in (
            ('fr', 'Confirmation du profil candidat'),
            ('en', 'Candidate profile confirmation'),
            ('de', 'Bestätigung des Bewerberprofils'),
        ):
            with self.subTest(language=language):
                response = self.client.get(
                    reverse('candidate_registration_requested'),
                    {'lang': language},
                    secure=True,
                )
                self.assertContains(response, title)
                self.assertContains(response, f'<html lang="{language}">')
        with override_settings(DEBUG=True, ALLOWED_HOSTS=['127.0.0.1']):
            pending = registration.create_request('de@example.invalid', answers(), 'de')
            subject, _body = registration.simulated_email(
                pending, 'http://127.0.0.1:9035'
            )
            self.assertEqual(subject, 'Bestätigen Sie Ihr Bewerberprofil')

    def test_request_limit_and_existing_address_have_the_same_public_outcome(self):
        from eures_beta.users.rate_limits import allow_request
        from django.test import RequestFactory

        request = RequestFactory().post('/', REMOTE_ADDR='192.0.2.1')
        self.assertEqual(
            [allow_request(request, 'limit@example.invalid') for _ in range(6)],
            [True] * 5 + [False],
        )
        response = self.client.get(
            reverse('candidate_registration_requested'), secure=True
        )
        self.assertNotContains(response, 'limit@example.invalid')
        self.assertNotContains(response, 'token=')


@override_settings(
    CANDIDATE_REGISTRATION_ENABLED=True,
    DJANGO_ENVIRONMENT='local',
    EMAIL_DELIVERY_ENABLED=False,
)
class CandidateConfirmationConcurrencyTests(TransactionTestCase):
    def test_two_confirmations_create_exactly_one_account_and_profile(self):
        pending = registration.create_request(
            'concurrent@example.invalid', answers(), 'fr'
        )
        token = registration.token_for(pending)
        barrier = Barrier(2)

        def confirm():
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                user = registration.confirm_registration(token)
                return bool(user)
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: confirm(), range(2)))
        self.assertEqual(sorted(results), [False, True])
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(CandidateProfile.objects.count(), 1)
        self.assertEqual(CandidateRegistration.objects.count(), 0)
