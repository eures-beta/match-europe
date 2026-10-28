from io import BytesIO
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone
from eures_beta.documents.forms import UploadForm
from eures_beta.offers.models import Offer
from eures_beta.accounts.models import Profile
from eures_beta.matching.models import Match
from eures_beta.offers.services import dispatch_offer


from eures_beta.testing_support import DomainScenario


class OffersTests(DomainScenario):
    def test_offer_and_match_object_permissions(self):
        outsider = User.objects.create_user('other@example.invalid')
        Profile.objects.create(user=outsider, role='employer', verified=True)
        self.client.force_login(outsider)
        self.assertEqual(
            self.client.get(reverse('offer', args=[self.offer.pk])).status_code, 404
        )
        self.assertEqual(
            self.client.post(
                reverse('offer', args=[self.offer.pk]), {'action': 'suggest'}
            ).status_code,
            404,
        )
        self.as_role('candidate')
        self.assertEqual(
            self.client.get(reverse('offer', args=[self.offer.pk])).status_code, 404
        )
        self.assertEqual(
            self.client.get(reverse('match', args=[self.match.pk])).status_code, 404
        )
        self.as_role('employer')
        self.assertEqual(
            self.client.get(reverse('match', args=[self.match.pk])).status_code, 404
        )

    def test_employer_cannot_trigger_suggestions_or_change_validated_offer(self):
        self.as_role('employer')
        for action in ['suggest', 'validate', 'question']:
            self.assertEqual(
                self.client.post(
                    reverse('offer', args=[self.offer.pk]), {'action': action}
                ).status_code,
                404,
            )

    def test_no_dispatch_before_validation_and_email_confirmation(self):
        self.offer.sent_at = None
        self.offer.validated_at = None
        with self.assertRaises(ValueError):
            dispatch_offer(self.offer, self.users['employer'])
        self.offer.validated_at = timezone.now()
        Profile.objects.filter(user=self.users['employer']).update(verified=False)
        self.offer.employer.refresh_from_db()
        with self.assertRaises(ValueError):
            dispatch_offer(self.offer, self.users['employer'])

    def test_pdf_validation(self):
        form = UploadForm(
            {'agreement': True},
            {'document': SimpleUploadedFile('bad.pdf', b'not a PDF')},
        )
        self.assertFalse(form.is_valid())

    def test_employer_pdf_draft_questions_and_validation(self):
        from pypdf import PdfWriter

        self.as_role('employer')
        content = BytesIO()
        writer = PdfWriter()
        writer.add_blank_page(width=595, height=842)
        writer.write(content)
        response = self.client.post(
            reverse('upload'),
            {
                'agreement': 'yes',
                'document': SimpleUploadedFile('fiction.pdf', content.getvalue()),
            },
        )
        self.assertEqual(response.status_code, 302)
        obj = Offer.objects.exclude(pk=self.offer.pk).get()
        self.assertEqual(obj.state, 'draft')
        self.assertFalse(obj.sent_at)
        self.assertEqual(
            self.client.get(reverse('offer', args=[obj.pk])).status_code, 200
        )
        self.client.post(
            reverse('offer', args=[obj.pk]),
            {'action': 'save', 'title': 'Brouillon incomplet'},
        )
        obj.refresh_from_db()
        self.assertEqual(obj.title, 'Brouillon incomplet')
        self.client.post(
            reverse('offer', args=[obj.pk]),
            {
                'action': 'question',
                'text': 'Quand êtes-vous disponible ?',
                'options': 'Lundi|À discuter',
            },
        )
        self.assertEqual(obj.questions.count(), 1)
        self.client.post(
            reverse('offer', args=[obj.pk]),
            {'action': 'validate', 'agreement': 'yes', 'title': 'Brouillon incomplet'},
        )
        obj.refresh_from_db()
        self.assertEqual(obj.state, 'draft')
        fields = {
            'action': 'validate',
            'agreement': 'yes',
            'title': 'Poste fictif',
            'company': 'Société fictive',
            'location': 'Bruxelles',
            'description': 'Description fictive détaillée',
            'cross_border': 'yes',
            'relocation': 'discuss',
        }
        self.client.post(reverse('offer', args=[obj.pk]), fields)
        obj.refresh_from_db()
        self.assertEqual(obj.state, 'synced')
        self.assertIsNotNone(obj.sent_at)
        self.assertEqual(Match.objects.filter(offer=obj).count(), 0)
