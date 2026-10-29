"""Server validation of employer occupation choices and reference snapshots."""

from eures_beta.occupations.catalog import LANGUAGES, catalog, occupation_index, present


def clean_selection(value, title):
    """Validate an employer's choices; snapshots always come from our local data."""
    if not isinstance(value, dict):
        raise ValueError('Invalid occupation selection')
    language = value.get('language', 'fr')
    uris = value.get('uris', [])
    personal = value.get('personal', '')
    if (
        language not in LANGUAGES
        or value.get('version') != catalog()['manifest']['version']
        or value.get('title') != title
        or not isinstance(uris, list)
        or len(uris) > 35
        or any(
            not isinstance(uri, str) or uri not in occupation_index() for uri in uris
        )
        or not isinstance(personal, str)
        or len(personal) > 2000
    ):
        raise ValueError('Invalid occupation selection')
    uris = list(dict.fromkeys(uris))
    return {
        'version': catalog()['manifest']['version'],
        'title': title,
        'language': language,
        'uris': uris,
        'personal': personal.strip(),
        'jobs': [present(occupation_index()[uri], language) for uri in uris],
    }
