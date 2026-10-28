from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.models import User
from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST
from eures_beta.accounts.access_control import forbid
from eures_beta.accounts.forms import AccessForm
from eures_beta.accounts.models import Profile
from eures_beta.accounts.services import adviser_from, consume_token, issue_token


@never_cache
def access(request):
    # This flow displays authentication links in-browser instead of emailing them.
    if not settings.DEMO_MODE:
        raise Http404()
    if request.user.is_authenticated:
        return redirect('dashboard')
    invitation = request.GET.get('invite', '') or request.session.get('invitation', '')
    adviser = adviser_from(invitation)
    if adviser:
        request.session['invitation'] = invitation
    role = request.GET.get('role', '') or request.session.get('start_role', '')
    if role in ['employer', 'candidate']:
        request.session['start_role'] = role
    form = AccessForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        email = form.cleaned_data['email'].strip().lower()
        user = User.objects.filter(username=email).first()
        if not user and adviser and role in ['employer', 'candidate']:
            with transaction.atomic():
                user = User.objects.create_user(username=email, email=email)
                user.set_unusable_password()
                user.save()
                Profile.objects.create(user=user, role=role, adviser=adviser)
            request.session.cycle_key()
            request.session['draft_user'] = user.pk
        if user:
            token = issue_token(user)
            if token:
                # Demo only: link visible exclusively in the requesting browser session.
                request.session['demo_email_link'] = reverse('confirm', args=[token])
        messages.info(
            request,
            _(
                'If this address is eligible, a connection link has been prepared. No email is sent in demonstration mode.'
            ),
        )
        if request.session.get('draft_user'):
            return redirect('upload')
        return redirect('access')
    demo_people = (
        User.objects.filter(
            username__endswith='@example.invalid', profile__verified=True
        )
        .select_related('profile')
        .order_by('pk')
        if settings.DEMO_MODE
        else []
    )
    return render(
        request,
        'access.html',
        {
            'form': form,
            'adviser': adviser,
            'demo_people': demo_people,
            'email_link': request.session.get('demo_email_link'),
        },
    )


@require_POST
def demo_login(request, pk):
    if not settings.DEMO_MODE:
        forbid()
    user = get_object_or_404(
        User, pk=pk, username__endswith='@example.invalid', profile__verified=True
    )
    request.session.flush()
    login(request, user)
    return redirect('dashboard')


@never_cache
def confirm(request, token):
    if not settings.DEMO_MODE:
        raise Http404()
    if request.method == 'POST':
        user = consume_token(token)
        if not user:
            messages.error(
                request,
                _(
                    'This link has expired or has already been used. Request a new link.'
                ),
            )
            return redirect('access')
        request.session.flush()
        login(request, user)
        messages.success(request, _('Email confirmed.'))
        return redirect('dashboard')
    # GET does not consume the token, avoiding email scanner activation.
    return render(request, 'confirm.html')


@require_POST
def sign_out(request):
    logout(request)
    return redirect('access')
