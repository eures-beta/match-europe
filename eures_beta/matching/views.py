from django.utils.translation import gettext_noop
from django.contrib import messages
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.translation import gettext as _
from eures_beta.conversations.models import Conversation, Message
from eures_beta.accounts.access_control import require_identity, forbid
from eures_beta.matching.forms import ReviewForm
from eures_beta.candidates.models import Candidate
from eures_beta.offers.models import Offer
from eures_beta.accounts.models import Event, Profile
from eures_beta.employers.models import EmployerImport
from eures_beta.matching.models import Answer, Match
from eures_beta.accounts.services import audit, invite_for
from eures_beta.notifications.services import notify


def allowed_match(user, match):
    if not user.profile.verified:
        return False
    if user.profile.role == 'admin' or user.pk in [
        match.candidate.user_id,
        match.offer.adviser_id,
    ]:
        return True
    return user.pk == match.offer.employer_id and match.state in [
        Match.State.REVIEW,
        Match.State.CLARIFY,
        Match.State.INTRODUCED,
    ]


@require_identity
def dashboard(request):
    user = request.me_user
    role = user.profile.role
    offers = Offer.objects.none()
    matches = Match.objects.none()
    candidate = None
    invitation = None
    if role == 'employer':
        offers = Offer.objects.filter(employer=user)
        matches = Match.objects.filter(
            offer__employer=user, state__in=['review', 'clarify', 'introduced']
        )
    elif role == 'candidate':
        candidate = Candidate.objects.filter(user=user).first()
        matches = Match.objects.filter(candidate__user=user).exclude(state='suggested')
    elif role in ['adviser', 'admin'] and user.profile.verified:
        offers = (
            Offer.objects.all()
            if role == 'admin'
            else Offer.objects.filter(adviser=user)
        )
        matches = Match.objects.filter(offer__in=offers)
        if role == 'adviser':
            invitation = invite_for(user)
    else:
        forbid()
    imports = EmployerImport.objects.none()
    if role in ['adviser', 'admin'] and user.profile.verified:
        imports = (
            EmployerImport.objects.all()
            if role == 'admin'
            else EmployerImport.objects.filter(adviser=user)
        )
    return render(
        request,
        'dashboard.html',
        {
            'imports': imports.select_related('adviser__profile').order_by('-created'),
            'offers': offers.order_by('-created'),
            'matches': matches.select_related('offer', 'candidate'),
            'candidate': candidate,
            'invitation': invitation,
            'email_link': request.session.get('demo_email_link'),
            'events': (
                Event.objects.order_by('-created')[:30] if role == 'admin' else []
            ),
            'people': Profile.objects.select_related('user') if role == 'admin' else [],
        },
    )


@require_identity
def match_detail(request, pk):
    user = request.me_user
    obj = get_object_or_404(
        Match.objects.select_related(
            'candidate__user', 'offer__employer', 'offer__adviser'
        ),
        pk=pk,
    )
    if not allowed_match(user, obj) or (
        user.pk == obj.candidate.user_id and obj.state == Match.State.SUGGESTED
    ):
        forbid()
    is_candidate = user.pk == obj.candidate.user_id
    is_employer = user.pk == obj.offer.employer_id
    is_adviser = user.pk == obj.offer.adviser_id
    if request.method == 'POST':
        action = request.POST.get('action')
        with transaction.atomic():
            obj = Match.objects.select_for_update().get(pk=pk)
            if action == 'invite' and is_adviser and obj.state == Match.State.SUGGESTED:
                obj.state = Match.State.INVITED
                notify(
                    obj.candidate.user,
                    gettext_noop('An offer is waiting for you'),
                    reverse('match', args=[pk]),
                )
            elif (
                action == 'interested'
                and is_candidate
                and obj.state == Match.State.INVITED
            ):
                obj.state = Match.State.ANSWERING
            elif (
                action == 'decline'
                and is_candidate
                and obj.state
                in [Match.State.INVITED, Match.State.ANSWERING, Match.State.CLARIFY]
            ):
                obj.state = Match.State.DECLINED
                notify(
                    obj.offer.adviser,
                    gettext_noop('Candidate response received'),
                    reverse('match', args=[pk]),
                )
            elif (
                action in ['save_answers', 'submit_answers']
                and is_candidate
                and obj.state in [Match.State.ANSWERING, Match.State.CLARIFY]
            ):
                responses = []
                for question in obj.offer.questions.all():
                    choice = request.POST.get(f'choice_{question.pk}', '').strip()
                    text = request.POST.get(f'text_{question.pk}', '').strip()
                    if (choice and choice not in question.choices()) or len(
                        text
                    ) > 4000:
                        return HttpResponse(_('Invalid answer.'), status=400)
                    responses.append((question, choice, text))
                if action == 'submit_answers' and (
                    any(not c and not t for q, c, t in responses)
                    or not request.POST.get('agreement')
                ):
                    messages.error(
                        request,
                        _(
                            'Answer each question or explain what needs clarification, and confirm your agreement to introduction.'
                        ),
                    )
                    return redirect('match', pk=pk)
                for question, choice, text in responses:
                    Answer.objects.update_or_create(
                        match=obj,
                        question=question,
                        defaults={'choice': choice, 'text': text},
                    )
                if action == 'submit_answers':
                    obj.candidate_agreement = True
                    obj.state = Match.State.REVIEW
                    notify(
                        obj.offer.adviser,
                        gettext_noop('Prequalification ready for review'),
                        reverse('match', args=[pk]),
                    )
                    notify(
                        obj.offer.employer,
                        gettext_noop('Prequalification ready for review'),
                        reverse('match', args=[pk]),
                    )
            elif (
                action == 'employer_agree'
                and is_employer
                and obj.state == Match.State.REVIEW
            ):
                if not request.POST.get('agreement'):
                    return HttpResponse(_('Agreement required.'), status=400)
                obj.employer_agreement = True
            elif action == 'clarify' and is_adviser and obj.state == Match.State.REVIEW:
                note = request.POST.get('note', '').strip()[:2000]
                if not note:
                    return HttpResponse(
                        _('Please explain what needs clarification.'), status=400
                    )
                obj.review_note = note
                obj.state = Match.State.CLARIFY
                obj.candidate_agreement = False
                obj.employer_agreement = False
                notify(
                    obj.candidate.user,
                    gettext_noop('Clarification requested'),
                    reverse('match', args=[pk]),
                )
            elif (
                action == 'introduce' and is_adviser and obj.state == Match.State.REVIEW
            ):
                if not obj.candidate_agreement or not obj.employer_agreement:
                    messages.error(
                        request,
                        _(
                            'Both participants must agree before the conversation is opened.'
                        ),
                    )
                    return redirect('match', pk=pk)
                note = request.POST.get('note', '').strip()[:2000]
                if not note:
                    return HttpResponse(_('Write an introduction message.'), status=400)
                conv = Conversation.objects.create(match=obj, opened_by=user)
                Message.objects.create(conversation=conv, sender=user, body=note)
                obj.state = Match.State.INTRODUCED
                for recipient in [obj.candidate.user, obj.offer.employer]:
                    notify(
                        recipient,
                        gettext_noop('Your conversation is open'),
                        reverse('conversation', args=[conv.pk]),
                    )
            else:
                forbid()
            obj.save()
            audit(user, action, obj)
        return redirect('match', pk=pk)
    answers = {a.question_id: a for a in obj.answers.all()}
    questions = [
        {'q': q, 'answer': answers.get(q.pk), 'choices': q.choices()}
        for q in obj.offer.questions.all()
    ]
    return render(
        request,
        'match.html',
        {
            'match': obj,
            'questions': questions,
            'is_candidate': is_candidate,
            'is_employer': is_employer,
            'is_adviser': is_adviser,
            'review_form': ReviewForm(),
        },
    )
