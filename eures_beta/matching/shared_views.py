"""Private three-person conversations, separate from the Albert dialogue."""

from django import forms
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.db import transaction
from django.db.models import Exists, F, OuterRef
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone, translation
from django.utils.translation import gettext_lazy as _
from django.views.decorators.cache import never_cache
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.http import require_http_methods

from eures_beta.candidates import preview_push
from eures_beta.users.views import selected_language
from . import access, adviser_opinion, confirmation_services
from .models import (
    CandidateOfferReview,
    CandidateOfferMatch,
    SharedConversation,
    SharedMessage,
)

State = SharedConversation.State
ROLES = {
    'adviser': _('Adviser'),
    'candidate': _('Candidate'),
    'employer': _('Employer'),
}


class MessageForm(forms.Form):
    body = forms.CharField(
        label=_('Message'), max_length=2000, widget=forms.Textarea(attrs={'rows': 3})
    )


PREREQUISITES = _(
    'We verified with the candidate that they meet the prerequisites for the role.'
)


class IntroductionForm(MessageForm):
    prerequisites_verified = forms.BooleanField(
        label=_(
            'I have verified the prerequisites with the candidate. Add this to the message.'
        ),
        required=False,
    )

    def clean(self):
        data = super().clean()
        if data.get('prerequisites_verified') and data.get('body'):
            body = data['body']
            opening, separator, rest = body.partition('\n\n')
            data['body'] = (
                opening
                + '\n\n'
                + str(PREREQUISITES)
                + (separator + rest if rest else '')
            )
            if len(data['body']) > 2000:
                self.add_error(
                    'body',
                    _(
                        'Shorten the message to leave room for the prerequisites sentence.'
                    ),
                )
        return data


def introduction(pair, adviser):
    offer = pair.offer.data
    company = offer.get('companyName') or _('the company')
    return _(
        'Hello, I’m %(adviser)s from Match Europe. I’m putting you in touch about the %(title)s role in %(city)s.\n\n'
        '%(candidate)s, I’d like to introduce %(employer)s, who is recruiting for %(company)s. '
        '%(employer)s, %(candidate)s is interested in the role and would like to speak with you.\n\n'
        'Could you suggest one or two times for an initial conversation? You can reply and ask questions here. '
        'I’m available in this conversation if you need me.'
    ) % {
        'adviser': adviser.get_full_name() or _('your adviser'),
        'title': offer.get('title') or _('job'),
        'city': offer.get('city') or _('the location in the offer'),
        'candidate': pair.candidate.display_name or _('Candidate'),
        'employer': pair.offer.created_by.get_full_name() or company,
        'company': company,
    }


def conversations(user):
    rows = SharedConversation.objects.all()
    if (
        not access.enabled()
        or not user.is_authenticated
        or not user.is_active
        or user.kind not in ROLES
        or (user.kind == 'adviser' and not access.can_view_pairs(user))
    ):
        return rows.none()
    rows = rows.filter(**{user.kind: user}).filter(
        confirmation__pair__offer__created_by_id=F('employer_id'),
        confirmation__pair__candidate__user_id=F('candidate_id'),
    )
    if user.kind == 'employer':
        rows = rows.filter(state=State.OPEN)
    return rows


def listed(user):
    if user.kind not in ROLES:
        return conversations(user)
    read = user.kind + '_read'
    unread = SharedMessage.objects.filter(
        conversation=OuterRef('pk'), pk__gt=OuterRef(read)
    ).exclude(author=user)
    return (
        conversations(user)
        .annotate(unread=Exists(unread))
        .select_related('confirmation__pair__offer')
        .order_by('-pk')
    )


def destination(name, pk, language):
    return reverse(name, args=[pk]) + '?lang=' + language


@never_cache
@login_required
@sensitive_post_parameters()
@require_http_methods(['GET', 'POST'])
def start(request, pk):
    if not access.can_change_pair(request.user):
        raise Http404
    language = selected_language(request)
    with translation.override(language), transaction.atomic():
        confirmation = get_object_or_404(
            CandidateOfferReview.objects.select_related(
                'pair__offer__created_by', 'pair__candidate'
            ),
            pk=pk,
            requested_by=request.user,
            pair__decision='retained',
            pair__candidate__in=access.candidates(),
            pair__offer__in=access.matchable_offers(),
        )
        CandidateOfferMatch.objects.select_for_update().get(pk=confirmation.pair_id)
        confirmation = CandidateOfferReview.objects.select_related(
            'pair__offer__created_by', 'pair__candidate'
        ).get(pk=pk)
        pair = confirmation.pair
        employer = pair.offer.created_by
        if (
            pair.decision != 'retained'
            or not employer
            or employer.kind != 'employer'
            or not employer.is_active
        ):
            raise Http404
        existing = conversations(request.user).filter(confirmation=confirmation).first()
        if existing:
            return redirect(destination('shared_conversation', existing.pk, language))
        if SharedConversation.objects.filter(confirmation=confirmation).exists():
            raise Http404
        if not adviser_opinion.ready(confirmation_services.review(confirmation)):
            raise Http404
        form = IntroductionForm(
            request.POST if request.method == 'POST' else None,
            initial={'body': introduction(pair, request.user)},
        )
        if request.method == 'POST' and form.is_valid():
            thread = SharedConversation.objects.create(
                confirmation=confirmation,
                adviser=request.user,
                candidate_id=pair.candidate.user_id,
                employer=employer,
                introduction=form.cleaned_data['body'],
            )
            if preview_push.available():
                transaction.on_commit(
                    lambda: preview_push.notify_shared(thread, invitation=True)
                )
            return redirect(destination('shared_conversation', thread.pk, language))
        return render(
            request,
            'matching/shared_start.html',
            {'confirmation': confirmation, 'form': form, 'page_language': language},
            status=400 if form.errors else 200,
        )


@never_cache
@login_required
@sensitive_post_parameters()
@require_http_methods(['GET', 'POST'])
def detail(request, pk):
    user = request.user
    language = selected_language(request)
    with translation.override(language), transaction.atomic():
        thread = get_object_or_404(
            conversations(user)
            .select_related(
                'confirmation__pair__offer',
                'confirmation__pair__candidate',
                'adviser',
                'candidate',
                'employer',
            )
            .select_for_update(of=('self',)),
            pk=pk,
        )
        role = user.kind
        can_write = role != 'adviser' or access.can_change_pair(user)
        state = thread.state
        form = MessageForm()
        status = 200
        push_result = ''
        can_resend = (
            role == 'adviser'
            and can_write
            and state == State.REQUESTED
            and preview_push.available()
        )
        if request.method == 'POST':
            if not can_write:
                raise Http404
            action = request.POST.get('action')
            message = None
            if action == 'resend' and can_resend:
                if not cache.add(f'shared-invitation-push:{pk}', True, 30):
                    push_result = _('Wait a moment before resending.')
                    status = 429
                elif preview_push.notify_shared(thread, invitation=True):
                    push_result = _('The push service accepted the notification.')
                else:
                    push_result = _(
                        'The notification could not be sent. Enable notifications again on the candidate’s phone.'
                    )
                    status = 503
            elif (
                role == 'candidate'
                and action in ('approve', 'decline')
                and state == State.REQUESTED
            ):
                thread.state = State.APPROVED if action == 'approve' else State.DECLINED
                thread.consent_at = timezone.now()
                thread.save(update_fields=['state', 'consent_at'])
            elif role == 'adviser' and action == 'open' and state == State.APPROVED:
                thread.state = State.OPEN
                thread.save(update_fields=['state'])
                message = SharedMessage.objects.create(
                    conversation=thread, author=user, body=thread.introduction
                )
            elif action == 'send' and state == State.OPEN:
                form = MessageForm(request.POST)
                if form.is_valid():
                    message = SharedMessage.objects.create(
                        conversation=thread, author=user, body=form.cleaned_data['body']
                    )
                else:
                    status = 400
            else:
                raise Http404
            if message and role != 'candidate' and preview_push.available():
                transaction.on_commit(lambda: preview_push.notify_shared(thread))
            if status == 200 and action != 'resend':
                return redirect(destination('shared_conversation', pk, language))
        messages = []
        if state == State.OPEN:
            participants = {
                thread.adviser_id: (ROLES['adviser'], thread.adviser.get_full_name()),
                thread.candidate_id: (
                    ROLES['candidate'],
                    thread.confirmation.pair.candidate.display_name,
                ),
                thread.employer_id: (
                    ROLES['employer'],
                    thread.employer.get_full_name()
                    or thread.confirmation.pair.offer.data.get('companyName', ''),
                ),
            }
            messages = [
                (message, *participants[message.author_id])
                for message in thread.messages.order_by('pk')
            ]
            if messages:
                field = role + '_read'
                setattr(thread, field, messages[-1][0].pk)
                thread.save(update_fields=[field])
        return render(
            request,
            'matching/shared_conversation.html',
            {
                'thread': thread,
                'messages': messages,
                'form': form,
                'role': role,
                'can_write': can_write,
                'can_resend': can_resend,
                'push_result': push_result,
                'page_language': language,
                'base_template': (
                    'conversation_base.html'
                    if role == 'candidate'
                    else 'public_base.html'
                ),
            },
            status=status,
        )
