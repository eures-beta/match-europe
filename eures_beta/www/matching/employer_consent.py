"""Private employer consent before the three-person introduction."""

from django import forms
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import OuterRef, Subquery
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone, translation
from django.utils.translation import gettext_lazy as _
from django.views.decorators.cache import never_cache
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.http import require_http_methods

from eures_beta.matching import access, employer_consent, offer_review_services
from eures_beta.matching.models import (
    CandidateOfferReview,
    CandidateProfileSharing,
    EmployerCandidateReview,
)
from eures_beta.www.accounts.views import selected_language
from eures_beta.www.design_system import bootstrap_form
from eures_beta.www.matching.offer_reviews import display_rows


class EmployerReply(forms.Form):
    contact = forms.ChoiceField(
        label=_('Have you already been in contact with this person?'),
        choices=[
            ('', _('Choose an answer')),
            ('no', _('No')),
            ('previous', _('Yes, we were in contact before')),
            ('ongoing', _('Yes, a recruitment process is already underway')),
        ],
    )
    interest = forms.ChoiceField(
        label=_('Would you like to be introduced?'),
        choices=[
            ('', _('Choose an answer')),
            ('yes', _('Yes, introduce us')),
            ('no', _('No')),
        ],
    )

    details = forms.CharField(
        label=_('Details for the adviser'),
        required=False,
        max_length=1000,
        widget=forms.Textarea(attrs={'rows': 3}),
    )

    def __init__(self, questions, ready, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if ready:
            del self.fields['contact']
            del self.fields['details']
            return
        del self.fields['interest']
        for index, question in enumerate(questions):
            self.fields[f'condition_{index}'] = forms.ChoiceField(
                label=employer_consent.question_text(question),
                choices=[
                    ('', _('Choose an answer')),
                    ('accepted', _('This works for the position')),
                    ('clarify', _('I need to clarify or change this condition')),
                    ('blocked', _('This is a requirement for the position')),
                ],
            )

    def replies(self, count):
        return {
            'contact': self.cleaned_data['contact'],
            'details': self.cleaned_data['details'],
            'conditions': [
                self.cleaned_data[f'condition_{index}'] for index in range(count)
            ],
        }


def employer_requests(user):
    if not user.is_authenticated or not user.is_active or user.kind != 'employer':
        return EmployerCandidateReview.objects.none()
    latest = CandidateProfileSharing.objects.filter(
        review_id=OuterRef('agreement__review_id')
    ).order_by('-pk')
    return EmployerCandidateReview.objects.filter(
        employer=user,
        agreement_id=Subquery(latest.values('pk')[:1]),
        agreement__agreed=True,
        agreement__review__match__offer__employer=user,
        agreement__review__match__candidate__in=access.candidates(),
        agreement__review__match__offer__in=access.matchable_offers(),
        agreement__review__match__decision='retained',
    ).select_related('agreement__review__match__offer')


def current_agreement(review):
    state = offer_review_services.review_state(review)
    agreement = employer_consent.eligible_agreement(state)
    if not agreement:
        raise Http404
    return state, agreement


@never_cache
@login_required
@sensitive_post_parameters()
@require_http_methods(['GET', 'POST'])
def prepare(request, pk):
    if not access.can_change_match(request.user):
        raise Http404
    review = get_object_or_404(
        CandidateOfferReview.objects.select_related(
            'match__offer__employer', 'match__candidate'
        ),
        pk=pk,
        match__decision='retained',
        match__candidate__in=access.candidates(),
        match__offer__in=access.matchable_offers(),
    )
    language = selected_language(request)
    with translation.override(language):
        state, agreement = current_agreement(review)
        if not employer_consent.can_prepare(review, state, request.user):
            raise Http404
        employer = review.match.offer.employer
        if not employer or not employer.is_active or employer.kind != 'employer':
            raise Http404
        consent = EmployerCandidateReview.objects.filter(agreement=agreement).first()
        questions = []
        action = request.POST.get('action')
        if not consent and action == 'draft':
            questions = employer_consent.draft_questions(
                display_rows(state['rows'], language), language
            )
        if not consent and action == 'publish':
            with transaction.atomic():
                employer_consent.lock_review_scope(review)
                review.refresh_from_db()
                if review.match.decision != 'retained':
                    raise Http404
                state, current = current_agreement(review)
                if (
                    not employer_consent.can_prepare(review, state, request.user)
                    or current.pk != agreement.pk
                    or review.match.offer.employer_id != employer.pk
                ):
                    raise Http404
                questions = request.session.get(f'employer-consent:{agreement.pk}')
                if questions is None:
                    raise Http404
                EmployerCandidateReview.objects.get_or_create(
                    agreement=agreement,
                    defaults={
                        'requested_by_adviser': request.user,
                        'employer': employer,
                        'questions': questions,
                    },
                )
                return redirect(
                    reverse('prepare_employer_consent', args=[pk]) + '?lang=' + language
                )
        if action == 'draft' and not consent:
            request.session[f'employer-consent:{agreement.pk}'] = questions
        if consent:
            questions = consent.questions
        replies = consent.replies if consent else {}
        condition_labels = {
            'accepted': _('This works for the position'),
            'clarify': _('I need to clarify or change this condition'),
            'blocked': _('This is a requirement for the position'),
        }
        question_rows = [
            (question, condition_labels.get(reply))
            for question, reply in zip(
                questions, replies.get('conditions', []), strict=False
            )
        ]
        if not question_rows:
            question_rows = [(question, None) for question in questions]
        return render(
            request,
            'matching/employer_consent.html',
            {
                'page_language': language,
                'review': review,
                'consent': consent,
                'question_rows': question_rows,
                'drafted': action == 'draft',
                'contact_label': dict(EmployerReply.base_fields['contact'].choices).get(
                    replies.get('contact')
                ),
                'preparing': True,
                'can_start_shared': bool(
                    employer_consent.introduction_consent(review, state, request.user)
                ),
            },
        )


@never_cache
@login_required
@sensitive_post_parameters()
@require_http_methods(['GET', 'POST'])
def respond(request, pk):
    language = selected_language(request)
    with translation.override(language), transaction.atomic():
        consent = get_object_or_404(employer_requests(request.user), pk=pk)
        review = consent.agreement.review
        employer_consent.lock_review_scope(review)
        consent = get_object_or_404(
            employer_requests(request.user).select_for_update(of=('self',)), pk=pk
        )
        review = consent.agreement.review
        state, agreement = current_agreement(review)
        if consent.agreement_id != agreement.pk or not employer_consent.can_prepare(
            review, state, review.assigned_to_adviser
        ):
            raise Http404
        pending = consent.decision == EmployerCandidateReview.Decision.PENDING
        ready = bool(consent.replies)
        form = EmployerReply(
            consent.questions, ready, request.POST if request.method == 'POST' else None
        )
        if request.method == 'POST':
            if not pending:
                raise Http404
            if request.POST.get('stage') != ('decision' if ready else 'conditions'):
                return redirect(
                    reverse('respond_employer_consent', args=[pk]) + '?lang=' + language
                )
            if form.is_valid():
                if ready:
                    consent.replies['interest'] = form.cleaned_data['interest']
                else:
                    consent.replies = form.replies(len(consent.questions))
                consent.decision = employer_consent.decision_for(consent.replies)
                if consent.decision != EmployerCandidateReview.Decision.PENDING:
                    consent.decided_at = timezone.now()
                consent.save(update_fields=['replies', 'decision', 'decided_at'])
                return redirect(
                    reverse('respond_employer_consent', args=[pk]) + '?lang=' + language
                )
        return render(
            request,
            'matching/employer_consent.html',
            {
                'page_language': language,
                'review': review,
                'consent': consent,
                'form': bootstrap_form(form) if pending else None,
                'ready': ready,
                'conditions': (
                    zip(
                        consent.questions,
                        (
                            form[f'condition_{index}']
                            for index in range(len(consent.questions))
                        ),
                    )
                    if pending and not ready
                    else ()
                ),
            },
        )
