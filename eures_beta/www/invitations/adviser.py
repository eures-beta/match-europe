import csv
import io
import logging
import uuid
from urllib.parse import urlencode, urljoin

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core import signing
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.mail import EmailMultiAlternatives, get_connection
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.templatetags.static import static
from django.urls import reverse
from django.utils import timezone, translation
from django.views.decorators.cache import never_cache
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.http import require_http_methods

from eures_beta.invitations.services import (
    create_invitation,
    invitation_token,
    record_invitation_attempt,
    validate_origin,
)
from eures_beta.invitations.models import Invitation
from eures_beta.invitations.defaults import invitation_expiry
from eures_beta.users.models import User
from eures_beta.www.invitations.forms import RecipientForm
from eures_beta.invitations.permissions import can_invite
from eures_beta.www.accounts.views import email_ready, selected_language

logger = logging.getLogger(__name__)
RecipientKind = Invitation.RecipientKind
SALT = 'users.adviser-invitations.preview'
MAX_ROWS = 10


def csv_recipients(upload):
    if not upload or upload.size > 64 * 1024:
        raise ValidationError('Choisissez un fichier CSV de 64 Ko maximum.')
    try:
        content = upload.read().decode('utf-8-sig')
        header = content.splitlines()[0]
        delimiter = ';' if ';' in header else ','
        reader = csv.DictReader(
            io.StringIO(content, newline=''), delimiter=delimiter, strict=True
        )
        columns = {
            'email': 'email',
            'prenom': 'first_name',
            'prénom': 'first_name',
            'nom': 'last_name',
        }
        names = [columns.get(value.strip().lower()) for value in reader.fieldnames]
        if None in names or len(set(names)) != len(names) or 'email' not in names:
            raise ValidationError(
                'Utilisez les colonnes email, prénom et nom. Seule email est obligatoire.'
            )
        recipients = []
        seen = set()
        errors = []
        for index, row in enumerate(reader, start=2):
            if index > MAX_ROWS + 1:
                raise ValidationError(
                    f'Importez {MAX_ROWS} destinataires au maximum par fichier.'
                )
            if None in row or any(value is None for value in row.values()):
                errors.append(f'Ligne {index} : nombre de colonnes incorrect.')
                continue
            form = RecipientForm(dict(zip(names, row.values())))
            if not form.is_valid():
                errors.append(f'Ligne {index} : adresse e-mail ou nom invalide.')
                continue
            email = form.cleaned_data['email']
            if email in seen:
                errors.append(f'Ligne {index} : adresse e-mail en double.')
                continue
            seen.add(email)
            recipients.append(form.cleaned_data)
        if errors:
            raise ValidationError(errors)
        if not recipients:
            raise ValidationError('Le fichier ne contient aucun destinataire.')
        return recipients
    except (UnicodeDecodeError, csv.Error, IndexError) as error:
        raise ValidationError('Le fichier doit être un CSV au format UTF-8.') from error


def local_outbox_enabled():
    return (
        settings.DEBUG
        and settings.DJANGO_ENVIRONMENT == 'local'
        and not settings.EMAIL_DELIVERY_ENABLED
    )


def render_message(
    recipient_kind,
    recipient,
    origin='',
    link='#',
    reminder=False,
    *,
    adviser,
    language='fr',
):
    with translation.override(
        language if recipient_kind == RecipientKind.EMPLOYER else 'fr'
    ):
        return render_invitation(
            recipient_kind, recipient, origin, link, reminder, adviser
        )


def render_invitation(recipient_kind, recipient, origin, link, reminder, adviser):
    name = ' '.join(
        part for part in (recipient['first_name'], recipient['last_name']) if part
    )
    context = {
        'greeting': (
            (
                translation.gettext('Hello %(name)s,') % {'name': name}
                if name
                else translation.gettext('Hello,')
            )
            if recipient_kind == RecipientKind.EMPLOYER
            else (f'Bonjour {name},' if name else 'Bonjour,')
        ),
        'link': link,
        'privacy': origin + reverse('privacy') if origin else '#',
        'reminder': reminder,
    }
    if recipient_kind == RecipientKind.EMPLOYER:
        context.update(
            adviser_name=adviser.get_full_name(),
            organization_name=adviser.organization_name.strip(),
            partner_logos=[
                (
                    urljoin(origin + '/', static(filename)),
                    label,
                    width,
                )
                for filename, label, width in (
                    (
                        'employer/assets/eures-ela.jpg',
                        'EURES / European Labour Authority',
                        112,
                    ),
                    (
                        'invitations/assets/france-travail-email.png',
                        'France Travail',
                        88,
                    ),
                    ('employer/assets/adem.png', 'ADEM', 34),
                    ('employer/assets/forem.png', 'Le Forem', 80),
                )
            ],
        )
    base = 'invitations/emails/'
    if recipient_kind == RecipientKind.ADVISER:
        stem = base + 'adviser/invitation'
        subject = 'Rejoignez l’équipe de conseillers Match Europe'
        if reminder:
            subject = 'Rappel — ' + subject
    else:
        stem = base + recipient_kind + ('/reminder' if reminder else '/invitation')
        subject = render_to_string(stem + '.subject').strip()
    context['subject'] = subject
    return (
        subject,
        render_to_string(stem + '.txt', context),
        render_to_string(stem + '.html', context),
    )


def deliver(request, invitation, *, reminder=False):
    if local_outbox_enabled():
        origin = validate_origin(
            settings.LOGIN_EMAIL_ORIGIN or request.build_absolute_uri('/')
        )
        connection = get_connection(
            'django.core.mail.backends.filebased.EmailBackend',
            file_path=settings.BASE_DIR / '.runtime' / 'invitation-outbox',
        )
    elif email_ready():
        origin = validate_origin(settings.LOGIN_EMAIL_ORIGIN)
        connection = None
    else:
        return False

    link = (
        origin
        + reverse('invitation_confirm')
        + '?invitation='
        + invitation_token(invitation)
    )
    subject, body, html = render_message(
        invitation.recipient_kind,
        {'first_name': invitation.first_name, 'last_name': invitation.last_name},
        origin,
        link,
        reminder,
        adviser=request.user,
        language=invitation.language,
    )
    message = EmailMultiAlternatives(
        subject,
        body,
        settings.DEFAULT_FROM_EMAIL,
        [invitation.email],
        connection=connection,
    )
    message.attach_alternative(html, 'text/html')
    try:
        return bool(message.send())
    except Exception:
        logger.error(
            'Adviser invitation delivery failed; inspect the mail service privately.'
        )
        return False


def preview_context(request, recipient_kind, recipients, invitation=None):
    previews = []
    for recipient in recipients:
        subject, _, html = render_message(
            recipient_kind,
            recipient,
            reminder=bool(invitation and invitation.email_sent_at),
            adviser=request.user,
            language=invitation.language if invitation else selected_language(request),
        )
        previews.append({'recipient': recipient, 'subject': subject, 'html': html})
    return {
        'previews': previews,
        'preview_recipient_kind': RecipientKind(recipient_kind).label,
        'preview_token': signing.dumps(
            {
                'actor': request.user.pk,
                'recipient_kind': recipient_kind,
                'language': selected_language(request),
                'recipients': recipients,
                'invitation': str(invitation.pk) if invitation else None,
                'nonce': str(invitation.nonce) if invitation else None,
            },
            salt=SALT,
        ),
        'reminder_preview': bool(invitation),
    }


@never_cache
@login_required
@sensitive_post_parameters()
@require_http_methods(['GET', 'POST'])
def invitations_tab(request):
    if not can_invite(request.user):
        raise PermissionDenied

    language = selected_language(request)
    dashboard_url = reverse('dashboard')
    if (
        request.method == 'GET'
        and request.resolver_match.url_name == 'adviser_invitations'
    ):
        params = request.GET.copy()
        params['tab'] = 'invite'
        params['lang'] = language
        return redirect(f'{dashboard_url}?{params.urlencode()}')

    tracking = request.GET.get('view') == 'history'
    create_url = f'{dashboard_url}?{urlencode({"lang": language, "tab": "invite"})}'
    history_url = create_url + '&view=history'
    form = RecipientForm()
    recipient_kind = RecipientKind.EMPLOYER
    mode = 'csv' if request.GET.get('mode') == 'csv' else 'manual'
    context = {}
    errors = []
    if request.method == 'POST':
        action = request.POST.get('action')
        try:
            if action in ('preview', 'import'):
                recipient_kind = request.POST.get('recipient_kind', '')
                if recipient_kind not in RecipientKind.values:
                    raise PermissionDenied
                if action == 'import':
                    mode = 'csv'
                    recipients = csv_recipients(request.FILES.get('csv'))
                else:
                    form = RecipientForm(request.POST)
                    recipients = [form.cleaned_data] if form.is_valid() else []
                if recipients:
                    context.update(preview_context(request, recipient_kind, recipients))
            elif action == 'send':
                payload = signing.loads(
                    request.POST.get('preview', ''), salt=SALT, max_age=900
                )
                if (
                    payload['actor'] != request.user.pk
                    or payload['recipient_kind'] not in RecipientKind.values
                ):
                    raise PermissionDenied
                if payload['invitation']:
                    change_invitation(
                        request,
                        payload['invitation'],
                        resend=True,
                        nonce=payload['nonce'],
                    )
                else:
                    send_batch(request, payload)
                return redirect(history_url if payload['invitation'] else create_url)
            elif action == 'remove':
                change_invitation(request, request.POST.get('invitation'), resend=False)
                return redirect(history_url)
            elif action == 'preview_reminder':
                tracking = True
                invitation = get_object_or_404(
                    Invitation.objects.all(),
                    pk=valid_identifier(request.POST.get('invitation')),
                    accepted_at__isnull=True,
                )
                recipient = {
                    name: getattr(invitation, name)
                    for name in ('first_name', 'last_name', 'email')
                }
                context.update(
                    preview_context(
                        request, invitation.recipient_kind, [recipient], invitation
                    )
                )
            else:
                raise ValidationError('Action inconnue.')
        except signing.BadSignature:
            errors.append('Cet aperçu a expiré. Préparez un nouvel aperçu.')
        except ValidationError as error:
            errors.extend(error.messages)

    if tracking:
        invitations = Invitation.objects.all()
        search = request.GET.get('q', '').strip()[:254]
        if search:
            invitations = invitations.filter(email__icontains=search)
        context.update(
            search=search,
            invitations=Paginator(
                invitations.order_by('-created_at', 'pk'), 20
            ).get_page(request.GET.get('page')),
        )
    context.update(
        {
            'form': form,
            'dashboard_language': language,
            'mode': mode,
            'recipient_kind': recipient_kind,
            'recipient_kinds': RecipientKind.choices,
            'tracking': tracking,
            'create_url': create_url,
            'history_url': history_url,
            'errors': errors,
            'local_outbox': local_outbox_enabled(),
        }
    )
    return render(request, 'invitations/adviser_invitations.html', context)


def send_batch(request, payload):
    sent = 0
    unsent = 0
    for recipient in payload['recipients']:
        try:
            with transaction.atomic():
                invitation = create_invitation(
                    request.user,
                    language=(
                        payload.get('language', 'fr')
                        if payload['recipient_kind'] == RecipientKind.EMPLOYER
                        else 'fr'
                    ),
                    recipient_kind=payload['recipient_kind'],
                    **recipient,
                )
                if deliver(request, invitation):
                    invitation.email_sent_at = timezone.now()
                    invitation.save(update_fields=['email_sent_at'])
                    sent += 1
                else:
                    unsent += 1
        except (ValidationError, IntegrityError) as error:
            reason = (
                error.messages[0]
                if isinstance(error, ValidationError)
                else 'Adresse déjà invitée.'
            )
            messages.error(request, f"{recipient['email']} — {reason}")
    if sent:
        text = (
            f'{sent} e-mail(s) déposé(s) dans la boîte locale.'
            if local_outbox_enabled()
            else f'{sent} e-mail(s) accepté(s) par le service d’envoi.'
        )
        messages.success(request, text)
    if unsent:
        messages.warning(
            request,
            f'{unsent} invitation(s) enregistrée(s), e-mail en attente. Vous pouvez réessayer dans le suivi.',
        )


def valid_identifier(value):
    try:
        return uuid.UUID(value)
    except (TypeError, AttributeError, ValueError) as error:
        raise ValidationError('Invitation introuvable.') from error


@transaction.atomic
def change_invitation(request, identifier, *, resend, nonce=None):
    actor = User.objects.select_for_update().get(pk=request.user.pk)
    if not can_invite(actor):
        raise PermissionDenied
    invitation = get_object_or_404(
        Invitation.objects.select_for_update(),
        pk=valid_identifier(identifier),
        accepted_at__isnull=True,
    )
    if not resend:
        invitation.delete()
        messages.success(request, 'Invitation supprimée. Son lien est révoqué.')
        return
    if str(invitation.nonce) != nonce:
        raise ValidationError('Cette invitation a changé. Préparez un nouvel aperçu.')
    if User.objects.filter(email__iexact=invitation.email).exists():
        raise ValidationError('Un compte existe déjà pour cette adresse.')
    if not invitation.sender.is_active or (
        invitation.recipient_kind == RecipientKind.ADVISER
        and not can_invite(invitation.sender)
    ):
        raise ValidationError(
            'Le compte à l’origine de cette invitation ne peut plus l’envoyer.'
        )
    record_invitation_attempt(actor, timezone.now())
    invitation.nonce = uuid.uuid4()
    invitation.expires_at = invitation_expiry()
    reminder = bool(invitation.email_sent_at)
    if not deliver(request, invitation, reminder=reminder):
        raise ValidationError(
            'L’e-mail n’a pas pu être envoyé. Réessayez depuis le suivi.'
        )
    if reminder:
        invitation.reminder_sent_at = timezone.now()
    else:
        invitation.email_sent_at = timezone.now()
    invitation.save(
        update_fields=['nonce', 'expires_at', 'email_sent_at', 'reminder_sent_at']
    )
    messages.success(
        request,
        (
            'E-mail déposé dans la boîte locale.'
            if local_outbox_enabled()
            else 'E-mail accepté par le service d’envoi.'
        ),
    )
