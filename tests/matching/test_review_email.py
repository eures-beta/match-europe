from datetime import timedelta
from io import StringIO
from unittest.mock import patch
import time
from urllib.parse import parse_qs, urlsplit

from django.core import mail
from django.core.exceptions import PermissionDenied
from django.core.management import call_command
from django.db import transaction
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from eures_beta.matching import review_email, offer_review_services
from eures_beta.matching.models import CandidateOfferReview
from eures_beta.users.test_accounts import prepared_user
from eures_beta.www.accounts.return_path import canonical_destination
from eures_beta.www.adviser.matching import pending_pairs, record_review


@override_settings(
    DEMO_ACCOUNTS_ENABLED=True,
    DJANGO_ENVIRONMENT='local',
    EMAIL_DELIVERY_ENABLED=False,
    ALBERT_SIMULATED=True,
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    EMAIL_HOST='smtp.example.invalid',
    DEFAULT_FROM_EMAIL='no-reply@example.invalid',
    LOGIN_EMAIL_ORIGIN='https://testserver',
)
class ReviewEmailTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed_test_accounts', stdout=StringIO())

    def setUp(self):
        self.adviser = prepared_user('adviser')
        self.candidate = prepared_user('candidate-pwa')
        self.match = pending_pairs().get(candidate__user=self.candidate)
        self.client.force_login(self.adviser)

    def validate(self):
        with self.captureOnCommitCallbacks(execute=True):
            record_review(
                self.adviser, self.match, self.match.evaluation_id, 'retained'
            )
        self.review = CandidateOfferReview.objects.get(match=self.match)
        self.destination = reverse('candidate_offer_dialogue', args=[self.review.pk])

    def email_settings(self):
        return self.settings(EMAIL_DELIVERY_ENABLED=True, DEMO_ACCOUNTS_ENABLED=False)

    def link(self):
        return next(
            line
            for line in mail.outbox[-1].body.splitlines()
            if line.startswith('https://') and 'sesame=' in line
        )

    def test_validation_sends_once_after_commit_without_push(self):
        with self.email_settings(), patch('eures_beta.candidates.push.notify') as push:
            self.validate()
            push.assert_not_called()
            self.assertEqual(self.review.email_status, 'sent')
            self.assertIsNotNone(self.review.email_sent_at)
            self.assertEqual(mail.outbox[0].to, [self.candidate.email])
            self.assertFalse(review_email.send(self.review.pk))
            response = self.client.post(
                reverse('adviser_match', args=[self.match.pk]),
                {'action': 'retained', 'evaluation': self.match.evaluation_id},
            )
            self.assertEqual(response.status_code, 404)
            self.assertEqual(len(mail.outbox), 1)
            self.assertFalse(self.review.profile_sharings.exists())

    def test_link_requires_confirmation_and_opens_owned_offer(self):
        with self.email_settings():
            self.validate()
        link = urlsplit(self.link())
        self.assertEqual(parse_qs(link.query)['next'], [self.destination + '?lang=fr'])
        browser = Client(enforce_csrf_checks=True)
        response = browser.get(link.path + '?' + link.query, secure=True)
        self.assertNotIn('_auth_user_id', browser.session)
        page = browser.get(response.url, secure=True)
        self.assertNotContains(page, 'sesame=')
        self.assertEqual(browser.post(response.url, secure=True).status_code, 403)
        csrf = browser.cookies['csrftoken'].value
        confirmed = browser.post(
            response.url,
            {'csrfmiddlewaretoken': csrf},
            secure=True,
            HTTP_ORIGIN='https://testserver',
        )
        self.assertEqual(confirmed.url, self.destination + '?lang=fr')
        self.assertEqual(browser.get(confirmed.url, secure=True).status_code, 200)
        browser.get(link.path + '?' + link.query, secure=True)
        invalid = browser.post(
            reverse('magic_confirm'),
            {'csrfmiddlewaretoken': browser.cookies['csrftoken'].value},
            secure=True,
            HTTP_ORIGIN='https://testserver',
        )
        self.assertContains(invalid, 'invalid', status_code=200)

    def test_missing_configuration_is_visible_and_never_sends(self):
        with patch('eures_beta.matching.review_email.send_mail') as send:
            self.validate()
        send.assert_not_called()
        self.assertEqual(self.review.email_status, 'disabled')
        response = self.client.get(
            reverse('adviser_conversation', args=[self.review.pk]) + '?lang=en'
        )
        self.assertContains(response, 'Email delivery is not configured or enabled')
        self.assertNotContains(response, 'sesame=')

    def test_failed_send_does_not_undo_matching_and_can_be_retried(self):
        with (
            self.email_settings(),
            patch(
                'eures_beta.matching.review_email.send_mail',
                side_effect=OSError('private details'),
            ),
        ):
            self.validate()
        self.match.refresh_from_db()
        self.assertEqual(self.match.decision, 'retained')
        self.assertEqual(self.review.email_status, 'failed')
        follow = reverse('adviser_conversation', args=[self.review.pk])
        self.assertEqual(
            self.client.post(follow, {'action': 'resend'}).status_code, 429
        )
        CandidateOfferReview.objects.filter(pk=self.review.pk).update(
            email_attempted_at=timezone.now() - timedelta(minutes=2)
        )
        with self.email_settings():
            self.assertEqual(
                self.client.post(follow, {'action': 'resend'}).status_code, 200
            )
        self.review.refresh_from_db()
        self.assertEqual(self.review.email_status, 'sent')

    def test_refusal_never_sends(self):
        with self.email_settings(), self.captureOnCommitCallbacks(execute=True):
            record_review(self.adviser, self.match, self.match.evaluation_id, 'refused')
        self.assertFalse(mail.outbox)
        self.assertFalse(CandidateOfferReview.objects.filter(match=self.match).exists())

    def test_rollback_discards_email_callback_and_review(self):
        with self.email_settings(), self.captureOnCommitCallbacks(execute=True):
            with self.assertRaises(RuntimeError), transaction.atomic():
                record_review(
                    self.adviser, self.match, self.match.evaluation_id, 'retained'
                )
                raise RuntimeError('Rollback fictional validation')
        self.assertFalse(mail.outbox)
        self.assertFalse(CandidateOfferReview.objects.filter(match=self.match).exists())

    def test_changing_link_destination_does_not_give_access_to_another_candidate(self):
        with self.email_settings():
            self.validate()
        other = CandidateOfferReview.objects.exclude(pk=self.review.pk).first()
        target = reverse('candidate_offer_dialogue', args=[other.pk])
        query = parse_qs(urlsplit(self.link()).query)
        browser = Client()
        browser.get(
            reverse('magic_confirm'), {'sesame': query['sesame'][0], 'next': target}
        )
        response = browser.post(reverse('magic_confirm'))
        self.assertEqual(response.url, target)
        self.assertEqual(browser.get(target).status_code, 404)

    def test_delivery_for_ordinary_addresses_in_each_environment(self):
        self.validate()
        self.candidate.email = 'candidate@example.org'
        self.candidate.save(update_fields=['email'])
        for environment in ('local', 'preview', 'production'):
            CandidateOfferReview.objects.filter(pk=self.review.pk).update(
                email_status='pending', email_attempted_at=None
            )
            with self.email_settings(), self.settings(DJANGO_ENVIRONMENT=environment):
                self.assertTrue(review_email.send(self.review.pk))
                self.assertEqual(mail.outbox[-1].to, ['candidate@example.org'])

    def test_invalid_recipient_and_wrong_roles_cannot_resend(self):
        self.validate()
        with self.assertRaises(PermissionDenied):
            review_email.send(self.review.pk, adviser=self.candidate)
        self.client.force_login(self.candidate)
        self.assertEqual(
            self.client.post(
                reverse('adviser_conversation', args=[self.review.pk]),
                {'action': 'resend'},
            ).status_code,
            403,
        )
        self.candidate.is_active = False
        self.candidate.save(update_fields=['is_active'])
        with self.email_settings():
            self.assertFalse(review_email.send(self.review.pk, adviser=self.adviser))
        self.assertFalse(mail.outbox)

    def test_only_canonical_dialogue_destinations_are_accepted(self):
        self.validate()
        self.assertEqual(
            canonical_destination(self.destination + '?lang=de'),
            self.destination + '?lang=de',
        )
        for target in (
            'https://evil.invalid' + self.destination,
            '//evil.invalid',
            '/admin/',
            self.destination + '?next=https://evil.invalid',
            self.destination + '#other',
        ):
            self.assertEqual(canonical_destination(target), '')

    def test_translated_email_and_destination_in_each_language(self):
        self.validate()
        for language, subject in [
            ('fr', 'Une offre d’emploi pourrait vous correspondre'),
            ('en', 'An offer of employment might suit you'),
            ('de', 'Ein Stellenangebot könnte zu Ihnen passen'),
        ]:
            self.match.candidate.language = language
            self.match.candidate.save()
            CandidateOfferReview.objects.filter(pk=self.review.pk).update(
                email_status='pending', email_attempted_at=None
            )
            with self.email_settings():
                self.assertTrue(review_email.send(self.review.pk))
            self.assertEqual(mail.outbox[-1].subject, subject)
            self.assertEqual(
                parse_qs(urlsplit(self.link()).query)['next'],
                [self.destination + '?lang=' + language],
            )

    def test_adviser_progress_excludes_missing_conditions_and_stale_answers(self):
        self.validate()
        rows = offer_review_services.review_state(self.review)['rows']
        row = next(row for row in rows if row['kind'] == 'occupation')
        offer_review_services.answer(
            self.candidate, self.review.pk, row['key'], row['fingerprint'], 'yes'
        )
        follow = reverse('adviser_conversation', args=[self.review.pk])
        page = self.client.get(follow)
        self.assertEqual(page.context['reply_count'], 1)
        self.assertEqual(
            page.context['reply_total'], sum(row['askable'] for row in rows)
        )
        self.match.offer.data['title'] = 'Updated fictional offer'
        self.match.offer.save()
        page = self.client.get(follow)
        self.assertEqual(page.context['reply_count'], 0)
        self.assertContains(page, 'scope="col"')

    def test_new_login_email_keeps_dialogue_destination(self):
        self.validate()
        browser = Client()
        browser.get(reverse('magic_login'), {'next': self.destination + '?lang=de'})
        with self.email_settings():
            browser.post(reverse('magic_login'), {'email': self.candidate.email})
        self.assertEqual(
            parse_qs(urlsplit(self.link()).query)['next'],
            [self.destination + '?lang=de'],
        )

    def test_expired_offer_link_can_request_a_new_link_for_the_same_offer(self):
        with self.email_settings():
            self.validate()
        link = urlsplit(self.link())
        browser = Client()
        browser.get(link.path + '?' + link.query)
        with patch('sesame.tokens_v2.time.time', return_value=time.time() + 3601):
            invalid = browser.post(reverse('magic_confirm'))
        self.assertEqual(invalid.status_code, 200)
        self.assertEqual(invalid.context['stage'], 'invalid')
        self.assertNotIn('_auth_user_id', browser.session)
        browser.get(reverse('magic_login'))
        with self.email_settings():
            browser.post(reverse('magic_login'), {'email': self.candidate.email})
        self.assertEqual(
            parse_qs(urlsplit(self.link()).query)['next'],
            [self.destination + '?lang=fr'],
        )
