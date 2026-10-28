from django.utils.translation import gettext_noop
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from eures_beta.accounts.access_control import forbid, require_identity
from eures_beta.accounts.services import audit
from eures_beta.notifications.services import notify

from eures_beta.conversations.forms import MessageForm
from eures_beta.conversations.models import Conversation, Message
from eures_beta.conversations.permissions import conversation_allowed


@require_identity
def conversation(request, pk):
    obj = get_object_or_404(
        Conversation.objects.select_related(
            'match__candidate__user', 'match__offer__employer', 'match__offer__adviser'
        ),
        pk=pk,
    )
    user = request.me_user
    if not conversation_allowed(user, obj):
        forbid()
    form = MessageForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        msg = Message.objects.create(
            conversation=obj, sender=user, body=form.cleaned_data['body']
        )
        audit(user, 'message_sent', msg)
        for recipient in [
            obj.match.candidate.user,
            obj.match.offer.employer,
            obj.match.offer.adviser,
        ]:
            if recipient.pk != user.pk:
                notify(
                    recipient,
                    gettext_noop('New message'),
                    reverse('conversation', args=[pk]),
                )
        return redirect('conversation', pk=pk)
    return render(
        request,
        'conversations/detail.html',
        {
            'conversation': obj,
            'form': form,
            'chat_messages': obj.messages.select_related('sender__profile'),
        },
    )


@require_identity
def conversation_feed(request, pk):
    obj = get_object_or_404(Conversation, pk=pk)
    if not conversation_allowed(request.me_user, obj):
        forbid()
    return JsonResponse(
        {
            'count': obj.messages.count(),
            'latest': obj.messages.order_by('-pk').values_list('pk', flat=True).first(),
        }
    )
