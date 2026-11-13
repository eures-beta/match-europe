import logging

from django.conf import settings
from django.contrib.auth import login as auth_login
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.mail import send_mail
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.shortcuts import redirect, render
from django.utils import timezone, translation
from django.utils.translation import gettext as _
from django.views.decorators.cache import never_cache
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.http import require_http_methods

from .forms import InvitationForm
from .services import create_invitation, find_invitation, invitation_message
from .models import Invitation
from eures_beta.users.models import User
from .permissions import can_invite
from eures_beta.users.views import email_ready, selected_language

logger = logging.getLogger(__name__)


@never_cache
@login_required
@sensitive_post_parameters('email')
@require_http_methods(['GET', 'POST'])
def invite(request):
    if not can_invite(request.user):
        raise PermissionDenied
    with translation.override(selected_language(request)):
        form = InvitationForm(
            request.POST if request.method == 'POST' else None,
            initial={'language': selected_language(request)},
        )
        invitation = None
        sent = False
        if request.method == 'POST' and form.is_valid():
            try:
                invitation = create_invitation(request.user, **form.cleaned_data)
            except ValidationError as error:
                form.add_error(None, error)
            except IntegrityError:
                form.add_error(
                    'email',
                    _(
                        'An account or invitation already exists for this email address.'
                    ),
                )
            if invitation and email_ready():
                try:
                    subject, body = invitation_message(
                        invitation, settings.LOGIN_EMAIL_ORIGIN
                    )
                    sent = bool(
                        send_mail(
                            subject,
                            body,
                            settings.DEFAULT_FROM_EMAIL,
                            [invitation.email],
                        )
                    )
                    if sent:
                        invitation.email_sent_at = timezone.now()
                        invitation.save(update_fields=['email_sent_at'])
                except Exception:
                    logger.error(
                        'Employer invitation email delivery failed; inspect the mail service privately.'
                    )
        return render(
            request,
            'invitations/invite_employer.html',
            {'form': form, 'invitation': invitation, 'sent': sent},
        )


def adviser_dashboard(request):
    if not can_invite(request.user):
        raise PermissionDenied

    employers = Paginator(
        User.objects.filter(kind=User.Kind.EMPLOYER).order_by('email'), 25
    ).get_page(request.GET.get('employers_page'))
    invitations = Paginator(
        Invitation.objects.filter(
            accepted_at__isnull=True, recipient_kind=Invitation.RecipientKind.EMPLOYER
        ).order_by('-created_at'),
        25,
    ).get_page(request.GET.get('invitations_page'))
    return render(
        request,
        'invitations/adviser_dashboard.html',
        {'employers': employers, 'invitations': invitations},
    )


def confirmation_page(request, stage, invitation=None):
    with translation.override(selected_language(request)):
        response = render(
            request,
            'invitations/accept_invitation.html',
            {'stage': stage, 'invitation': invitation},
        )
    response['Referrer-Policy'] = 'same-origin'
    return response


@never_cache
@require_http_methods(['GET', 'POST'])
def confirm(request):
    if request.method == 'GET':
        if 'invitation' in request.GET:
            token = request.GET['invitation']
            request.session.pop('employer_invitation_token', None)
            invitation = find_invitation(token) if len(token) <= 512 else None
            if invitation:
                request.session['employer_invitation_token'] = token
                request.session['login_language'] = invitation.language
            response = redirect('invitation_confirm')
            response['Referrer-Policy'] = 'no-referrer'
            return response
        token = request.session.get('employer_invitation_token')
        invitation = find_invitation(token) if token else None
        return confirmation_page(
            request, 'confirm' if invitation else 'invalid', invitation
        )
    token = request.session.pop('employer_invitation_token', '')
    language = selected_language(request)
    if not token:
        return confirmation_page(request, 'invalid')
    try:
        with transaction.atomic():
            invitation = find_invitation(token, lock=True)
            if (
                not invitation
                or User.objects.filter(email__iexact=invitation.email).exists()
            ):
                return confirmation_page(request, 'invalid')
            if (
                invitation.recipient_kind == Invitation.RecipientKind.ADVISER
                and not can_invite(invitation.sender)
            ):
                return confirmation_page(request, 'invalid')
            recipient = User.objects.create_user(
                email=invitation.email,
                kind=invitation.recipient_kind,
                first_name=invitation.first_name,
                last_name=invitation.last_name,
            )
            invitation.accepted_at = timezone.now()
            invitation.recipient = recipient
            invitation.save(update_fields=['accepted_at', 'recipient'])
            auth_login(request, recipient, backend='sesame.backends.ModelBackend')
            request.session['login_language'] = language
            if invitation.recipient_kind == Invitation.RecipientKind.EMPLOYER:
                request.session['employer_welcome'] = True
            request.session.set_expiry(settings.SESSION_COOKIE_AGE)
    except IntegrityError:
        return confirmation_page(request, 'invalid')
    if invitation.recipient_kind == Invitation.RecipientKind.CANDIDATE:
        return redirect("candidate_prepare")
    return redirect(settings.LOGIN_REDIRECT_URL)
