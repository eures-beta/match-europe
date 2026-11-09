from io import StringIO
from html.parser import HTMLParser
from unittest.mock import patch
from datetime import timedelta
from django.core.management import call_command
from django.core.exceptions import PermissionDenied
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.utils import timezone
from django.utils import translation
from django.contrib.auth.models import Permission
from eures_beta.users.models import User
from eures_beta.matching import confirmation_services as service
from eures_beta.matching.models import (
    MatchPair,
    ConfirmationAnswer,
    TransmissionAgreement,
)
from eures_beta.matching.services import StaleEvaluation


@override_settings(
    MATCHING_ENABLED=True,
    TEST_ACCOUNTS_ENABLED=True,
    DJANGO_ENVIRONMENT='local',
    EMAIL_DELIVERY_ENABLED=False,
    LOGIN_EMAIL_ENABLED=False,
)
class ConfirmationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed_matching_trial', stdout=StringIO())
        cls.adviser = User.objects.create(email='adviser@matching-trial.invalid', kind='adviser')
        cls.adviser.user_permissions.add(*Permission.objects.filter(
            content_type__app_label='matching',
            codename__in=('view_matchpair', 'change_matchpair'),
        ))

    def setUp(self):
        self.pair = MatchPair.objects.select_related('candidate__user', 'offer').get(
            candidate__user__email='compatible@matching-trial.invalid'
        )
        self.user = self.pair.candidate.user
        self.request = service.request_confirmation(self.adviser, self.pair.pk)
        self.client.force_login(self.user)
        self.url = reverse('candidate_offer_confirmation', args=[self.request.pk])

    def row(self, kind):
        return next(
            row for row in service.questions(self.request) if row['kind'] == kind
        )

    def answer(self, row, value='yes', detail='', **kwargs):
        return service.answer(
            self.user,
            self.request.pk,
            row['key'],
            row['fingerprint'],
            value,
            detail,
            **kwargs,
        )

    def complete(self):
        for row in service.questions(self.request):
            if row['askable']:
                self.answer(row)
        return service.review(self.request)

    def test_matching_saturday_still_requires_explicit_confirmation(self):
        row = self.row('schedule')
        self.assertIn('saturday:morning', row['presented']['expected']['slots'])
        self.assertTrue(row['askable'])
        self.assertFalse(ConfirmationAnswer.objects.exists())
        page = self.client.get(self.url, {'question': row['key'], 'lang': 'en'})
        self.assertContains(page, 'Saturday')
        self.assertContains(page, self.pair.offer.data['title'])
        self.assertContains(page, 'Is this still correct')
        event = self.answer(row)
        self.assertEqual(event.actor, self.user)
        self.assertEqual(event.presented, row['presented'])
        self.assertFalse(TransmissionAgreement.objects.exists())

    def test_offer_missing_information_is_not_a_candidate_question(self):
        type(self.pair.offer).objects.filter(pk=self.pair.offer_id).update(structured_requirements={})
        row = self.row('languages')
        self.assertFalse(row['askable'])
        with self.assertRaises(StaleEvaluation):
            self.answer(row)
        self.assertTrue(service.review(self.request)['unresolved'])

    def test_edit_prefills_current_answer_and_rejects_concurrent_overwrite(self):
        row = self.row('schedule')
        event = self.answer(row, 'conditional', 'Alternate Saturdays')
        for language in ('fr', 'en', 'de'):
            page = self.client.get(self.url, {'question': row['key'], 'lang': language})
            form = page.context['form']
            self.assertEqual(form['value'].value(), 'conditional')
            self.assertEqual(form['detail'].value(), 'Alternate Saturdays')
            self.assertEqual(form['previous'].value(), event.pk)
        self.answer(row, 'no', previous=event.pk)
        response = self.client.post(
            self.url + '?question=' + row['key'],
            dict(
                action='answer',
                key=row['key'],
                fingerprint=row['fingerprint'],
                previous=event.pk,
                value='conditional',
                detail='Old page',
            ),
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(self.request.answers.order_by('-pk').first().value, 'no')

    def test_stale_answer_is_not_prefilled_as_a_current_confirmation(self):
        row = self.row('schedule')
        event = self.answer(row)
        self.pair.candidate.schedule_strict = not self.pair.candidate.schedule_strict
        self.pair.candidate.save()
        page = self.client.get(self.url, {'question': row['key']})
        self.assertIsNone(page.context['form']['value'].value())
        self.assertFalse(page.context['form']['detail'].value())
        self.assertEqual(page.context['form']['previous'].value(), event.pk)

    def test_error_summary_uses_labels_and_unique_ids_in_all_languages(self):
        class Elements(HTMLParser):
            def __init__(self):
                super().__init__()
                self.ids = []

            def handle_starttag(self, tag, attrs):
                self.ids.extend(value for key, value in attrs if key == 'id')

        row = self.row('schedule')
        for action in ('answer', 'agree'):
            if action == 'agree':
                self.assertFalse(self.request.answers.exists())
                self.complete()
            for language in ('fr', 'en', 'de'):
                data = dict(action=action, fingerprint=row['fingerprint'], previous=0)
                if action == 'answer':
                    data.update(key=row['key'], value='conditional', detail='')
                query = '?lang=' + language
                if action == 'answer':
                    query += '&question=' + row['key']
                page = self.client.post(self.url + query, data)
                self.assertEqual(page.status_code, 400)
                parser = Elements()
                parser.feed(page.content.decode())
                self.assertEqual(len(parser.ids), len(set(parser.ids)))
                form = page.context['form' if action == 'answer' else 'agreement_form']
                field = form['detail' if action == 'answer' else 'agreed']
                with translation.override(language):
                    self.assertContains(page, str(field.label), status_code=400)
                target = (
                    field.auto_id + '_0' if field.use_fieldset else field.id_for_label
                )
                self.assertIn(target, parser.ids)
                self.assertContains(page, f'href="#{target}"', status_code=400)
                self.assertNotContains(page, '<li>detail', status_code=400)
                if action == 'answer':
                    self.assertEqual(form['value'].value(), 'conditional')
        self.assertFalse(self.request.agreements.exists())

    def test_reservations_refusals_and_general_changes_do_not_write_profile_or_decision(
        self,
    ):
        before = self.pair.candidate.updated_at
        row = self.row('schedule')
        last = 0
        for value, detail in [
            ('conditional', 'Except Saturday afternoon'),
            ('no', ''),
            ('changed', 'No longer available on Saturdays'),
            ('clarify', 'What are the exact hours?'),
        ]:
            event = self.answer(row, value, detail, previous=last)
            last = event.pk
            self.assertTrue(service.review(self.request)['unresolved'])
        self.pair.candidate.refresh_from_db()
        self.pair.refresh_from_db()
        self.assertEqual(self.pair.candidate.updated_at, before)
        self.assertEqual(self.pair.decision, 'pending')
        self.assertEqual(self.request.answers.count(), 4)
        self.assertFalse(TransmissionAgreement.objects.exists())

    def test_ambiguous_or_incomplete_answer_is_rejected(self):
        row = self.row('schedule')
        for value, detail in [
            ('maybe', ''),
            ('conditional', ''),
            ('changed', ''),
            ('clarify', ''),
            ('yes', 'x' * 2001),
        ]:
            with self.assertRaises(ValueError):
                self.answer(row, value, detail)
        self.assertFalse(self.request.answers.exists())

    def test_changed_schedule_invalidates_only_relevant_confirmation(self):
        self.complete()
        req = type(self.pair.offer).objects.get(pk=self.pair.offer_id)
        req.structured_requirements['schedule'] = ['saturday:afternoon']
        req.save()
        state = service.review(self.request)
        rows = {row['kind']: row for row in state['rows']}
        self.assertIsNone(rows['schedule']['answer'])
        self.assertTrue(rows['schedule']['stale'])
        self.assertIsNotNone(rows['contract']['answer'])
        self.assertIsNotNone(rows['mobility']['answer'])

    def test_profile_change_invalidates_only_affected_fields(self):
        self.complete()
        self.pair.candidate.contract_types = ['fixed']
        self.pair.candidate.save()
        rows = {row['kind']: row for row in service.review(self.request)['rows']}
        self.assertIsNone(rows['contract']['answer'])
        self.assertIsNotNone(rows['schedule']['answer'])

    def test_relative_availability_is_reconfirmed_next_day(self):
        self.answer(self.row('availability'))
        with patch(
            'eures_beta.matching.confirmation_services.timezone.localdate',
            return_value=timezone.localdate() + timedelta(days=1),
        ):
            row = next(
                row
                for row in service.review(self.request)['rows']
                if row['kind'] == 'availability'
            )
        self.assertTrue(row['stale'])

    def test_stale_page_and_concurrent_different_answers_are_rejected(self):
        row = self.row('schedule')
        event = self.answer(row)
        with self.assertRaises(StaleEvaluation):
            self.answer(row, 'no')
        self.assertEqual(self.answer(row).pk, event.pk)
        req = type(self.pair.offer).objects.get(pk=self.pair.offer_id)
        req.structured_requirements['schedule'] = ['saturday:afternoon']
        req.save()
        with self.assertRaises(StaleEvaluation):
            self.answer(row, previous=event.pk)
        self.assertEqual(self.request.answers.count(), 1)

    def test_agreement_is_separate_explicit_and_revocable(self):
        with self.assertRaises(ValueError):
            state = service.review(self.request)
            service.agree(self.user, self.request.pk, state['fingerprint'], True)
        state = self.complete()
        self.assertIsNone(state['agreement'])
        first = service.agree(self.user, self.request.pk, state['fingerprint'], True)
        self.assertEqual(
            service.agree(self.user, self.request.pk, state['fingerprint'], True).pk,
            first.pk,
        )
        service.agree(
            self.user, self.request.pk, state['fingerprint'], False, previous=first.pk
        )
        self.assertFalse(service.review(self.request)['agreement'].agreed)
        self.assertEqual(self.request.agreements.count(), 2)

    def test_changed_offer_invalidates_transmission_permission_even_for_unscored_text(
        self,
    ):
        state = self.complete()
        service.agree(self.user, self.request.pk, state['fingerprint'], True)
        self.pair.offer.data['description'] += ' Changed conditions.'
        self.pair.offer.save()
        fresh = service.review(self.request)
        self.assertIsNone(fresh['agreement'])
        with self.assertRaises(StaleEvaluation):
            service.agree(self.user, self.request.pk, state['fingerprint'], True)

    def test_candidate_cannot_access_another_candidate_request_or_act_as_adviser(self):
        other = MatchPair.objects.get(
            candidate__user__email='unknown@matching-trial.invalid'
        )
        other_request = service.request_confirmation(self.adviser, other.pk)
        self.assertEqual(
            self.client.get(
                reverse('candidate_offer_confirmation', args=[other_request.pk])
            ).status_code,
            404,
        )
        with self.assertRaises(PermissionDenied):
            service.request_confirmation(self.user, self.pair.pk)
        self.client.force_login(self.adviser)
        self.assertEqual(self.client.get(self.url).status_code, 404)

    def test_profile_verification_revocation_removes_candidate_access(self):
        self.pair.candidate.email_verified_at = None
        self.pair.candidate.save(update_fields=['email_verified_at'])
        self.assertEqual(self.client.get(self.url).status_code, 404)

    def test_offer_validation_revocation_removes_candidate_access(self):
        self.pair.offer.validated_at = None
        self.pair.offer.save(update_fields=['validated_at'])
        self.assertEqual(self.client.get(self.url).status_code, 404)

    def test_adviser_must_have_current_decision_right(self):
        self.adviser.user_permissions.remove(Permission.objects.get(
            content_type__app_label='matching', codename='change_matchpair',
        ))
        self.adviser.refresh_from_db()
        self.adviser = User.objects.get(pk=self.adviser.pk)
        with self.assertRaises(PermissionDenied):
            service.request_confirmation(self.adviser, self.pair.pk)

    def test_get_and_missing_csrf_never_write(self):
        self.client.get(self.url, {'action': 'answer', 'value': 'yes'})
        strict = Client(enforce_csrf_checks=True)
        strict.force_login(self.user)
        self.assertEqual(strict.post(self.url, {'action': 'answer'}).status_code, 403)
        self.assertFalse(self.request.answers.exists())
        self.assertFalse(self.request.agreements.exists())

    def test_real_addresses_and_remote_confirmation_in_every_environment(self):
        self.user.email = 'candidate@example.org'
        self.user.save(update_fields=['email'])
        for environment in ('local', 'preview', 'production'):
            with (
                self.subTest(environment=environment),
                override_settings(
                    DJANGO_ENVIRONMENT=environment, EMAIL_DELIVERY_ENABLED=True
                ),
            ):
                self.assertEqual(
                    self.client.get(self.url, REMOTE_ADDR='192.0.2.1').status_code, 200
                )
                row = self.row('schedule')
                response = self.client.post(
                    self.url,
                    {
                        'action': 'answer',
                        'key': row['key'],
                        'fingerprint': row['fingerprint'],
                        'previous': (
                            self.request.answers.order_by('-pk').first().pk
                            if self.request.answers.exists()
                            else 0
                        ),
                        'value': 'yes',
                    },
                    REMOTE_ADDR='192.0.2.1',
                )
                self.assertEqual(response.status_code, 302)
        with override_settings(MATCHING_ENABLED=False):
            self.assertEqual(self.client.get(self.url).status_code, 404)

    def test_complete_browser_journey_no_external_calls(self):
        with (
            patch('django.core.mail.send_mail') as mail,
            patch('requests.sessions.Session.request') as external,
        ):
            for row in service.questions(self.request):
                if row['askable']:
                    response = self.client.post(
                        self.url,
                        {
                            'action': 'answer',
                            'key': row['key'],
                            'fingerprint': row['fingerprint'],
                            'previous': 0,
                            'value': 'yes',
                        },
                    )
                    self.assertEqual(response.status_code, 302)
            page = self.client.get(self.url, {'lang': 'en'})
            self.assertContains(page, 'Separate transmission permission')
            fingerprint = page.context['state']['fingerprint']
            self.assertEqual(
                self.client.post(
                    self.url,
                    {
                        'action': 'agree',
                        'fingerprint': fingerprint,
                        'agreed': 'yes',
                        'previous': 0,
                    },
                ).status_code,
                302,
            )
        mail.assert_not_called()
        external.assert_not_called()

    def test_answers_escaped_and_private_trilingual_pages(self):
        self.answer(self.row('schedule'), 'conditional', '<script>alert(1)</script>')
        for language in ('fr', 'en', 'de'):
            page = self.client.get(self.url, {'lang': language})
            self.assertEqual(page.status_code, 200)
            self.assertContains(page, '&lt;script&gt;')
            self.assertNotContains(page, '<script>alert(1)</script>')
            self.assertIn('no-store', page['Cache-Control'])
            self.assertNotContains(page, self.pair.offer.email)

    def test_saturday_morning_and_afternoon_have_independent_answers(self):
        req = type(self.pair.offer).objects.get(pk=self.pair.offer_id)
        req.structured_requirements['schedule'] = ['saturday:morning', 'saturday:afternoon']
        req.save()
        rows = [
            row for row in service.questions(self.request) if row['kind'] == 'schedule'
        ]
        self.assertEqual(len(rows), 2)
        self.answer(rows[0])
        self.answer(rows[1], 'conditional', 'Only on alternate weeks')
        state = service.review(self.request)
        answers = [
            row['answer'].value for row in state['rows'] if row['kind'] == 'schedule'
        ]
        self.assertEqual(answers, ['yes', 'conditional'])
        self.assertTrue(state['unresolved'])

    def test_adviser_summary_displays_current_answers_and_never_profile_contacts(self):
        self.answer(self.row('schedule'), 'conditional', 'Only on alternate weeks')
        self.client.force_login(self.adviser)
        page = self.client.get(
            reverse('matching_detail', args=[self.pair.pk]), {'lang': 'en'}
        )
        self.assertContains(page, 'Only on alternate weeks')
        self.assertContains(page, 'No current permission')
        self.assertNotContains(page, self.user.email)

    def test_stale_consent_form_cannot_overwrite_a_later_refusal(self):
        state = self.complete()
        yes = service.agree(self.user, self.request.pk, state['fingerprint'], True)
        no = service.agree(
            self.user, self.request.pk, state['fingerprint'], False, previous=yes.pk
        )
        with self.assertRaises(StaleEvaluation):
            service.agree(
                self.user, self.request.pk, state['fingerprint'], True, previous=yes.pk
            )
        self.assertFalse(service.review(self.request)['agreement'].agreed)

    def test_profile_content_change_invalidates_transmission_permission(self):
        state = self.complete()
        service.agree(self.user, self.request.pk, state['fingerprint'], True)
        self.pair.candidate.display_name = 'Changed fictional name'
        self.pair.candidate.save()
        self.request.pair.candidate.refresh_from_db()
        self.assertIsNone(service.review(self.request)['agreement'])
