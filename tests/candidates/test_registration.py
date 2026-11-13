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
from sesame.utils import get_token

from eures_beta.candidates import registration
from eures_beta.candidates.forms import KEY
from eures_beta.candidates.models import CandidateProfile
from eures_beta.candidates import pending as pending_store
from django.contrib.sessions.models import Session

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
    DJANGO_ENVIRONMENT='local',
    EMAIL_DELIVERY_ENABLED=False,
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
        self.assertEqual(
            Session.objects.filter(
                session_key__startswith=pending_store.PREFIX
            ).count(),
            1,
        )
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
        self.assertEqual(
            Session.objects.filter(
                session_key__startswith=pending_store.PREFIX
            ).count(),
            0,
        )
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
        Session.objects.filter(
            session_key=pending_store.session_key(pending.pk)
        ).update(expire_date=pending.expires_at)
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
        self.assertTrue(
            bool(registration.find_registration(registration.token_for(pending)))
        )

    def test_existing_accounts_are_only_explained_after_email_verification(self):
        for kind, active in (
            ('employer', True),
            ('adviser', True),
            ('candidate', False),
        ):
            user = User.objects.create_user(
                email=f'{kind}-{active}@example.invalid', kind=kind, is_active=active
            )
            pending = self.pending(user.email)
            self.open_link(pending)
            response = self.confirm()
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.context['stage'], 'role')
            self.assertNotIn('_auth_user_id', self.client.session)
            self.assertEqual(
                self.client.session[KEY]['data']['display_name'], 'Fictional candidate'
            )
            user.refresh_from_db()
            self.assertEqual(user.kind, kind)
            self.assertEqual(user.is_active, active)
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
        self.assertIsNotNone(
            registration.create_request(existing.email, answers(), 'fr')
        )

    def test_account_created_while_waiting_is_not_overwritten(self):
        pending = self.pending()
        self.open_link(pending)
        user = User.objects.create_user(email=pending.email, kind='employer')
        self.assertEqual(self.confirm().status_code, 200)
        user.refresh_from_db()
        self.assertEqual(user.kind, 'employer')
        self.assertEqual(CandidateProfile.objects.count(), 0)

    def test_second_anonymous_request_cannot_replace_pending_answers(self):
        pending = self.pending()
        changed = answers()
        changed['display_name'] = 'Unrelated visitor'
        second = registration.create_request(pending.email, changed, 'de')
        self.assertNotEqual(second.pk, pending.pk)
        pending = registration.find_registration(registration.token_for(pending))
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
        self.assertIsNotNone(
            registration.create_request('candidate@example.test', answers(), 'fr')
        )

    def test_pending_answers_are_not_registered_in_admin(self):
        from django.contrib import admin

        self.pending()
        model_admin = admin.site._registry[Session]
        self.assertNotIn('session_data', model_admin.list_display)
        self.assertFalse(
            model_admin.has_view_permission(
                type(
                    'Request',
                    (),
                    {
                        'user': User.objects.create_superuser(
                            'audit@example.invalid', kind='adviser'
                        )
                    },
                )(),
                Session.objects.filter(
                    session_key__startswith=pending_store.PREFIX
                ).first(),
            )
        )

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
        mobile = Client()
        mobile.get(reverse('magic_confirm'), {'sesame': get_token(user)}, secure=True)
        restored = mobile.post(reverse('magic_confirm'), secure=True, follow=True)
        self.assertEqual(restored.request['PATH_INFO'], reverse('candidate_profile'))
        self.assertContains(restored, 'data-install-pwa-handoff')
        self.assertContains(restored, 'data-install-pwa-phone')
        secured_profile = mobile.get(reverse('candidate_profile'), secure=True)
        self.assertContains(
            secured_profile, 'https://testserver/candidate/install-pwa/?lang='
        )
        self.assertContains(restored, 'Fictional candidate')
        self.assertContains(restored, 'rel="manifest"')

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

    def test_anonymous_entry_and_retrieval_are_both_available(self):
        response = self.client.get('/candidate/?lang=en', secure=True)
        self.assertContains(response, 'Retrieve or edit my profile')
        self.assertContains(response, '/candidate/prepare/')
        self.assertContains(response, reverse('magic_login'))
        self.assertEqual(
            self.client.get('/candidate/prepare/', secure=True).status_code, 200
        )
        self.assertEqual(User.objects.count(), 0)

    def existing_profile(self):
        pending = self.pending()
        self.open_link(pending)
        self.confirm()
        return User.objects.get()

    def test_cross_device_confirmation_compares_without_overwriting(self):
        user = self.existing_profile()
        original = CandidateProfile.objects.get(user=user)
        self.client.logout()
        changed = answers()
        changed['display_name'] = 'New reviewed name'
        pending = registration.create_request(user.email, changed, 'en')
        other_device = Client()
        self.open_link(pending, other_device)
        self.assertRedirects(
            self.confirm(other_device),
            reverse('candidate_profile_compare'),
            fetch_redirect_response=False,
        )
        original.refresh_from_db()
        self.assertEqual(original.display_name, 'Fictional candidate')
        comparison = other_device.get(reverse('candidate_profile_compare'), secure=True)
        self.assertContains(comparison, 'Fictional candidate')
        self.assertContains(comparison, 'New reviewed name')
        # An explicit protected POST is required; a GET never changes a profile.
        response = other_device.post(
            reverse('candidate_profile_compare'),
            {'action': 'replace', 'version': comparison.context['version']},
            secure=True,
        )
        self.assertEqual(response.status_code, 302)
        original.refresh_from_db()
        self.assertEqual(original.display_name, 'New reviewed name')
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(CandidateProfile.objects.count(), 1)
        self.assertNotIn('candidate_profile_proposal', other_device.session)

    def test_keep_existing_profile_and_reject_changed_version(self):
        user = self.existing_profile()
        changed = answers()
        changed['display_name'] = 'Proposed name'
        pending = registration.create_request(user.email, changed, 'fr')
        self.open_link(pending)
        self.confirm()
        comparison = self.client.get(reverse('candidate_profile_compare'), secure=True)
        registration.update_profile(user, answers(), 'de')
        # Another tab refreshing the comparison must not validate the old tab.
        self.client.get(reverse('candidate_profile_compare'), secure=True)
        response = self.client.post(
            reverse('candidate_profile_compare'),
            {'action': 'replace', 'version': comparison.context['version']},
            secure=True,
        )
        self.assertEqual(response.context['stage'], 'changed')
        self.assertEqual(user.candidate_profile.display_name, 'Fictional candidate')
        self.client.post(
            reverse('candidate_profile_compare'), {'action': 'keep'}, secure=True
        )
        self.assertNotIn('candidate_profile_proposal', self.client.session)

    def test_comparison_cannot_be_reused_by_another_account_or_after_expiry(self):
        user = self.existing_profile()
        pending = self.pending(user.email)
        self.open_link(pending)
        self.confirm()
        proposal = self.client.session['candidate_profile_proposal']
        proposal['expires_at'] = 0
        session = self.client.session
        session['candidate_profile_proposal'] = proposal
        session.save()
        response = self.client.post(
            reverse('candidate_profile_compare'), {'action': 'replace'}, secure=True
        )
        self.assertContains(response, 'invalide')
        self.assertNotIn('candidate_profile_proposal', self.client.session)

    def test_comparison_is_bound_to_verified_user_and_requires_csrf(self):
        user = self.existing_profile()
        pending = self.pending(user.email)
        self.open_link(pending)
        self.confirm()
        proposal = self.client.session['candidate_profile_proposal']
        other = User.objects.create_user(
            'other-candidate@example.invalid', kind='candidate'
        )
        CandidateProfile.objects.create(
            user=other, language='fr', **registration.validated_answers(answers(), 'fr')
        )
        self.client.force_login(other)
        session = self.client.session
        session['candidate_profile_proposal'] = proposal
        session.save()
        self.assertContains(
            self.client.get(reverse('candidate_profile_compare'), secure=True),
            'invalide',
        )
        self.assertNotIn('candidate_profile_proposal', self.client.session)
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(user)
        session = csrf_client.session
        session['candidate_profile_proposal'] = proposal
        session.save()
        response = csrf_client.post(
            reverse('candidate_profile_compare'), {'action': 'replace'}, secure=True
        )
        self.assertEqual(response.status_code, 403)

    def test_link_contains_no_browser_session_key_or_answers(self):
        from django.core import signing

        self.client.get('/candidate/prepare/', secure=True)
        pending = self.pending()
        payload = signing.loads(registration.token_for(pending), salt=registration.SALT)
        self.assertEqual(set(payload), {'id', 'nonce'})
        self.assertNotIn(self.client.session.session_key, str(payload))
        row = Session.objects.get(session_key=pending_store.session_key(pending.pk))
        self.assertNotIn('_auth_user_id', row.get_decoded())

    def test_expiry_cleanup_preserves_browser_sessions_and_valid_requests(self):
        expired = self.pending()
        Session.objects.filter(
            session_key=pending_store.session_key(expired.pk)
        ).update(expire_date=timezone.now() - timedelta(seconds=1))
        valid = self.pending('second@example.invalid')
        expired = self.pending('expired@example.invalid')
        Session.objects.filter(
            session_key=pending_store.session_key(expired.pk)
        ).update(expire_date=timezone.now() - timedelta(seconds=1))
        self.client.get('/candidate/prepare/', secure=True)
        browser_key = self.client.session.session_key
        output = StringIO()
        call_command('cleanup_candidate_registrations', stdout=output)
        self.assertTrue(
            Session.objects.filter(
                session_key=pending_store.session_key(expired.pk)
            ).exists()
        )
        call_command('cleanup_candidate_registrations', apply=True, stdout=output)
        self.assertFalse(
            Session.objects.filter(
                session_key=pending_store.session_key(expired.pk)
            ).exists()
        )
        self.assertIsNotNone(
            registration.find_registration(registration.token_for(valid))
        )
        self.assertTrue(Session.objects.filter(session_key=browser_key).exists())

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

    def test_confirmation_request_page_does_not_depend_on_email_transport(self):
        for language in ('fr', 'en', 'de'):
            reference = None
            for environment in ('local', 'preview', 'production'):
                for enabled in (False, True):
                    with (
                        self.subTest(
                            language=language, environment=environment, enabled=enabled
                        ),
                        override_settings(
                            DJANGO_ENVIRONMENT=environment,
                            LOGIN_EMAIL_ENABLED=enabled,
                            EMAIL_DELIVERY_ENABLED=enabled,
                            TEST_ACCOUNTS_ENABLED=False,
                        ),
                    ):
                        response = Client().get(
                            reverse('candidate_registration_requested'),
                            {'lang': language},
                            secure=True,
                        )
                        if reference is None:
                            reference = response.content
                        self.assertEqual(response.content, reference)

    def test_registration_and_confirmation_work_in_every_environment(self):
        for environment in ('local', 'preview', 'production'):
            with (
                self.subTest(environment=environment),
                override_settings(DJANGO_ENVIRONMENT=environment),
            ):
                self.client = Client()
                self.assertEqual(
                    self.client.get('/candidate/', secure=True).status_code, 200
                )
                self.assertEqual(
                    self.client.get('/candidate/prepare/', secure=True).status_code, 200
                )
                pending = self.pending(f'{environment}@example.test')
                self.open_link(pending)
                self.assertEqual(self.confirm().status_code, 302)
                self.assertEqual(
                    self.client.get(
                        reverse('candidate_profile'), secure=True
                    ).status_code,
                    200,
                )
                self.assertTrue(
                    User.objects.filter(email=pending.email, kind='candidate').exists()
                )

    def test_confirmation_delivery_uses_protected_shared_policy(self):
        pending = self.pending()
        with patch('eures_beta.candidates.registration.send_mail') as send:
            for environment in ('local', 'preview'):
                with override_settings(DJANGO_ENVIRONMENT=environment):
                    self.assertFalse(registration.send_confirmation(pending))
            send.assert_not_called()
        with override_settings(
            DJANGO_ENVIRONMENT='production',
            EMAIL_DELIVERY_ENABLED=True,
            LOGIN_EMAIL_ENABLED=True,
            LOGIN_EMAIL_ORIGIN='https://testserver',
            ALLOWED_HOSTS=['testserver'],
            EMAIL_HOST='smtp.example.invalid',
            DEFAULT_FROM_EMAIL='noreply@example.invalid',
            EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
        ):
            from django.core import mail

            self.assertTrue(registration.send_confirmation(pending))
            self.assertEqual(mail.outbox[-1].to, [pending.email])
            self.assertIn(
                'https://testserver/candidate/registration/confirm/?token=',
                mail.outbox[-1].body,
            )
            self.assertEqual(User.objects.count(), 0)
            with patch(
                'eures_beta.candidates.registration.send_mail',
                side_effect=RuntimeError(pending.email),
            ):
                with self.assertLogs(
                    'eures_beta.candidates.registration', level='ERROR'
                ) as logs:
                    self.assertFalse(registration.send_confirmation(pending))
                self.assertNotIn(pending.email, ''.join(logs.output))
                self.assertTrue(
                    bool(
                        registration.find_registration(registration.token_for(pending))
                    )
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
        self.assertEqual(
            Session.objects.filter(
                session_key__startswith=pending_store.PREFIX
            ).count(),
            1,
        )
        self.assertEqual(User.objects.count(), 0)
        self.assertIn(KEY, self.client.session)

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
            subject, _body = registration.confirmation_message(
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
        self.assertEqual(
            Session.objects.filter(
                session_key__startswith=pending_store.PREFIX
            ).count(),
            0,
        )
