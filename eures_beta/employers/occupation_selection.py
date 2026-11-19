"""Server validation of employer occupation choices and reference snapshots."""

from eures_beta.occupations.catalog import (
    LANGUAGES,
    catalog,
    occupation_index,
    present,
    rome_search_catalog,
)


def clean_selection(value, title):
    """Validate an employer's choices; snapshots always come from our local data."""
    if not isinstance(value, dict):
        raise ValueError('Invalid occupation selection')
    language = value.get('language', 'fr')
    uris = value.get('uris', [])
    personal = value.get('personal', '')
    rome_codes = value.get('rome_codes', [])
    if (
        not isinstance(rome_codes, list)
        or len(rome_codes) > 20
        or any(
            not isinstance(code, str) or code not in rome_search_catalog()['fiches']
            for code in rome_codes
        )
        or language not in LANGUAGES
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
    from eures_beta.occupations import unified

    uris = list(dict.fromkeys(uris))
    common_jobs = unified.group_rows(
        [unified.resolve_reference(uri, language) for uri in uris]
        + [
            unified.resolve_reference('rome:' + code, language)
            for code in dict.fromkeys(rome_codes)
        ]
    )
    return {
        'version': catalog()['manifest']['version'],
        'title': title,
        'language': language,
        'uris': uris,
        'common_jobs': common_jobs,
        'skill_references': [row['groupKey'] for row in common_jobs],
        'personal': personal.strip(),
        'rome_codes': list(dict.fromkeys(rome_codes)),
        'rome_jobs': [
            rome_search_catalog()['fiches'][code] for code in dict.fromkeys(rome_codes)
        ],
        'rome_version': '26M10',
        'jobs': [present(occupation_index()[uri], language) for uri in uris],
    }


def skill_references(selection):
    from eures_beta.occupations.unified import canonical

    references = selection.get('uris', []) + [
        'rome:' + code for code in selection.get('rome_codes', [])
    ]
    result = []
    for reference in references:
        try:
            key = canonical(reference)
        except ValueError:
            continue
        if key not in result:
            result.append(key)
    return result
