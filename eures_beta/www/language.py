"""Keep the chosen interface language across business pages and Django admin."""

from django.conf import settings
from django.middleware.locale import LocaleMiddleware
from django.utils import translation


class InterfaceLanguageMiddleware(LocaleMiddleware):
    def process_request(self, request):
        super().process_request(request)
        supported = {code for code, label in settings.LANGUAGES}
        explicit = request.GET.get('lang')
        if explicit in supported and 'login_language' in request.session:
            request.session['login_language'] = explicit
        for language in (
            explicit,
            request.session.get('login_language'),
            request.COOKIES.get(settings.LANGUAGE_COOKIE_NAME),
        ):
            if language in supported:
                translation.activate(language)
                request.LANGUAGE_CODE = language
                break

    def process_response(self, request, response):
        response = super().process_response(request, response)
        language = request.LANGUAGE_CODE
        if request.COOKIES.get(settings.LANGUAGE_COOKIE_NAME) != language:
            response.set_cookie(
                settings.LANGUAGE_COOKIE_NAME,
                language,
                max_age=settings.LANGUAGE_COOKIE_AGE,
                path=settings.LANGUAGE_COOKIE_PATH,
                domain=settings.LANGUAGE_COOKIE_DOMAIN,
                secure=settings.LANGUAGE_COOKIE_SECURE,
                httponly=settings.LANGUAGE_COOKIE_HTTPONLY,
                samesite=settings.LANGUAGE_COOKIE_SAMESITE,
            )
        return response
