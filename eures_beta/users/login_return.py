"""A fixed allowlist of employer import destinations, never an arbitrary next URL."""

IMPORT_PATHS = {
    f'/employer/pages/{prefix}{language}.html'
    for prefix in ('import-', 'import-v2-')
    for language in ('fr', 'en', 'de')
}


def remember(request):
    destination = request.GET.get('next', '')
    if destination in IMPORT_PATHS:
        request.session['login_return_path'] = destination


def consume(request, default):
    destination = request.session.pop('login_return_path', '')
    return destination if destination in IMPORT_PATHS else default
