from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase
from django.utils import translation

from eures_beta.matching.employer_consent import (
    decision_for,
    draft_questions,
    eligible_agreement,
)
from eures_beta.matching.models import EmployerOfferConsent
from eures_beta.www.matching.employer_consent import EmployerReply


class EmployerConsentTests(SimpleTestCase):
    def test_requires_the_current_candidate_agreement(self):
        self.assertIsNone(eligible_agreement({'agreement': None}))
        self.assertIsNone(
            eligible_agreement({'agreement': SimpleNamespace(agreed=False)})
        )
        agreement = SimpleNamespace(agreed=True)
        self.assertIs(eligible_agreement({'agreement': agreement}), agreement)

    def test_condition_answers_precede_the_explicit_decision(self):
        form = EmployerReply(
            [{}],
            False,
            {'contact': 'previous', 'condition_0': 'accepted', 'interest': 'yes'},
        )
        self.assertNotIn('interest', form.fields)
        self.assertTrue(form.is_valid(), form.errors)
        replies = form.replies(1)
        self.assertEqual(decision_for(replies), EmployerOfferConsent.Decision.PENDING)
        self.assertEqual(
            decision_for(dict(replies, interest='yes')),
            EmployerOfferConsent.Decision.ACCEPTED,
        )
        self.assertEqual(
            decision_for(dict(replies, conditions=['clarify'], interest='yes')),
            EmployerOfferConsent.Decision.CLARIFY,
        )
        self.assertEqual(
            decision_for(dict(replies, conditions=['blocked'], interest='yes')),
            EmployerOfferConsent.Decision.DECLINED,
        )

    @patch('eures_beta.matching.dialogue_albert.complete')
    def test_albert_only_receives_the_conditions_to_clarify(self, complete):
        complete.return_value = {'questions': ['Is B1 sufficient?']}
        row = dict(
            askable=True,
            label='German',
            expected='B2',
            answer_label='Under conditions',
            declared=[('German', 'B1')],
            answer=SimpleNamespace(value='conditional'),
        )
        draft = draft_questions(
            [row, dict(row, answer=SimpleNamespace(value='yes'))], 'en'
        )
        self.assertEqual(len(draft), 1)
        self.assertEqual(draft[0]['wording'], 'Is B1 sufficient?')
        self.assertEqual(
            complete.call_args.args[1]['differences'],
            [{key: value for key, value in draft[0].items() if key != 'wording'}],
        )

    def test_employer_screen_uses_the_localized_conversation_layout(self):
        from django.template.loader import render_to_string

        with translation.override('fr'):
            html = render_to_string(
                'matching/employer_consent.html',
                {
                    'page_language': 'fr',
                    'review': {
                        'match': {'candidate': {'display_name': 'Camille Exemple'}}
                    },
                    'form': EmployerReply([], True),
                    'ready': True,
                },
            )
        self.assertIn('conversation-screen', html)
        self.assertIn('Camille Exemple', html)
        self.assertIn('Oui, je souhaite être mis en relation', html)
        self.assertNotIn('Avez-vous déjà été en contact', html)
