from django.contrib import messages
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.translation import gettext as _
from eures_beta.accounts.access_control import require_identity, forbid
from eures_beta.journeys.views import allowed_offer
from eures_beta.journeys.forms import OfferForm, QuestionForm
from eures_beta.accounts.services import audit
from eures_beta.journeys.services import dispatch_offer, suggest_candidates
from eures_beta.offers.models import Offer, Question


@require_identity
def offer(request, pk):
    user = request.me_user
    obj = get_object_or_404(Offer, pk=pk)
    if not allowed_offer(user, obj):
        forbid()
    editable = obj.employer_id == user.pk and obj.state == Offer.State.DRAFT
    form = OfferForm(
        (
            request.POST
            if request.method == 'POST'
            and request.POST.get('action') in ['save', 'validate']
            else None
        ),
        instance=obj,
        complete=request.POST.get('action') == 'validate',
    )
    question_form = QuestionForm(
        request.POST
        if request.method == 'POST' and request.POST.get('action') == 'question'
        else None
    )
    if request.method == 'POST':
        action = request.POST.get('action')
        if action in ['save', 'validate', 'question', 'remove_question']:
            if not editable:
                forbid()
            if action == 'question' and question_form.is_valid():
                q = question_form.save(commit=False)
                q.offer = obj
                q.position = obj.questions.count()
                q.save()
                audit(user, 'question_added', q)
                return redirect('offer', pk=pk)
            if action == 'remove_question':
                get_object_or_404(
                    Question, pk=request.POST.get('question'), offer=obj
                ).delete()
                return redirect('offer', pk=pk)
            if action in ['save', 'validate'] and form.is_valid():
                with transaction.atomic():
                    obj = form.save()
                    if action == 'validate':
                        if not request.POST.get('agreement'):
                            form.add_error(
                                None,
                                _(
                                    'Please confirm that the offer and questions are ready for matching.'
                                ),
                            )
                        else:
                            obj.validated_at = timezone.now()
                            obj.state = (
                                Offer.State.PENDING
                                if not user.profile.verified
                                else Offer.State.READY
                            )
                            obj.save()
                            audit(user, 'offer_validated', obj)
                            if user.profile.verified:
                                dispatch_offer(obj, user)
                            return redirect('offer', pk=pk)
                    else:
                        messages.success(request, _('Draft saved.'))
                        return redirect('offer', pk=pk)
        elif action == 'suggest':
            if user.pk != obj.adviser_id and user.profile.role != 'admin':
                forbid()
            try:
                suggest_candidates(obj, user)
            except ValueError as exc:
                messages.error(request, str(exc))
            return redirect('offer', pk=pk)
        else:
            forbid()
    visible_matches = (
        obj.matches.select_related('candidate')
        if user.pk == obj.adviser_id or user.profile.role == 'admin'
        else []
    )
    return render(
        request,
        'offer.html',
        {
            'offer': obj,
            'form': form,
            'question_form': question_form,
            'editable': editable,
            'matches': visible_matches,
            'email_link': request.session.get('demo_email_link'),
        },
    )
