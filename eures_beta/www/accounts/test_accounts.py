from django.conf import settings
from django.contrib.auth import login as auth_login
from django.http import Http404
from django.shortcuts import redirect, render
from django.utils import translation
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_POST
from eures_beta.users.test_accounts import (
    account_specs,
    enabled,
    fictional_database,
    prepared_user,
)
from eures_beta.www.accounts.views import selected_language
from eures_beta.www.accounts.return_path import consume


def require_test_environment():
    if not enabled() or not fictional_database():
        raise Http404


@never_cache
@require_GET
def account_list(request):
    require_test_environment()
    with translation.override(selected_language(request)):
        accounts = [
            {
                'key': key,
                'label': specification['label'],
                'email': specification['email'],
            }
            for key, specification in account_specs().items()
            if prepared_user(key)
        ]
        return render(
            request,
            'users/test_accounts.html',
            {
                'accounts': accounts,
                'compact_preview': settings.DJANGO_ENVIRONMENT == 'preview',
                'page_language': selected_language(request),
                'account_base': (
                    'conversation_base.html'
                    if settings.DJANGO_ENVIRONMENT == 'preview'
                    else 'users/dashboard.html'
                ),
            },
        )


@never_cache
@require_POST
def sign_in(request):
    require_test_environment()
    user = prepared_user(request.POST.get('account'))
    if user is None:
        raise Http404
    language = selected_language(request)
    destination = consume(request, settings.LOGIN_REDIRECT_URL)
    auth_login(request, user, backend='sesame.backends.ModelBackend')
    from eures_beta.skills.continuous import trial_request

    if trial_request(request) and user.kind == 'employer':
        request.session['employer_verified_email'] = user.email
        request.session['employer_auth_language'] = language
    request.session['login_language'] = language
    request.session.set_expiry(settings.SESSION_COOKIE_AGE)
    return redirect('admin:index' if user.is_superuser else destination)
