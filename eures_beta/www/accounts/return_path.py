"""A fixed allowlist of employer import destinations, never an arbitrary next URL."""

IMPORT_PATHS = {
    f'/employer/pages/{prefix}{language}.html'
    for prefix in ('import-',)
    for language in ('fr', 'en', 'de')
}


def remember(request):
    destination = request.GET.get('next', '')
    destination = canonical_destination(destination)
    if destination in IMPORT_PATHS:
        request.session['login_return_path'] = destination


def consume(request, default):
    destination = request.session.pop('login_return_path', '')
    destination = canonical_destination(destination)
    return destination if destination in IMPORT_PATHS else default


def canonical_destination(destination):
    from eures_beta.www.public.redirects import EMPLOYER_IMPORT_ALIASES

    aliases = {
        '/employer/pages/' + old: '/employer/pages/' + current
        for old, current in EMPLOYER_IMPORT_ALIASES.items()
    }
    return aliases.get(destination, destination)
