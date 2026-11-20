"""One occupation card only for unambiguous, official primary-title exact links."""

from .catalog import (
    occupation_index,
    catalog,
    DATA_DIR,
    iter_artifact,
    rome_search_catalog,
    normalize,
    present,
    references,
    suggestions,
    nearby,
    serialized_cache,
    looks_like_reference,
    is_rome_reference,
)
from .descriptions import description as rome_description


@serialized_cache(maxsize=1)
def pairs():
    fiches = rome_search_catalog()['fiches']
    jobs = occupation_index()
    candidates = {}
    # Grouping needs only exact links, not a second complete ROME/OGR catalogue
    # and the retained crosswalk. Keep the checksum check on the same file.
    for row in iter_artifact(
        DATA_DIR / 'esco_rome.json', catalog()['manifest'], 'mappings.item'
    ):
        if row['relation'] != 'skos:exactMatch' or row['escoUri'] not in jobs:
            continue
        for code in row['ficheCodes']:
            if code in fiches and normalize(row['label']) == normalize(
                fiches[code]['label']
            ):
                candidates.setdefault(code, {}).setdefault(row['escoUri'], []).append(
                    row
                )
    return {
        code: {'uri': next(iter(targets)), 'mappings': next(iter(targets.values()))}
        for code, targets in candidates.items()
        if len(targets) == 1
    }


@serialized_cache(maxsize=1)
def reverse_pairs():
    result = {}
    for code, pair in pairs().items():
        result.setdefault(pair['uri'], []).append(code)
    return result


def canonical(reference):
    if not isinstance(reference, str):
        raise ValueError('Invalid occupation reference')
    if reference.startswith('esco:'):
        reference = reference[5:]
    if reference in occupation_index():
        return reference
    if (
        reference.startswith('rome:')
        and reference[5:] in rome_search_catalog()['fiches']
    ):
        return pairs().get(reference[5:], {}).get('uri', reference)
    raise ValueError('Unknown occupation reference')


def occupation_references(reference):
    key = canonical(reference)
    if key.startswith('rome:'):
        return [key]
    return ['esco:' + key] + ['rome:' + code for code in reverse_pairs().get(key, [])]


def resolve_reference(reference, language):
    try:
        key = canonical(reference)
    except ValueError:
        return None
    if key.startswith('rome:'):
        code = key[5:]
        row = rome_search_catalog()['fiches'][code]
        text, text_language = rome_description(code, language)
        return {
            'value': reference,
            'groupKey': key,
            'references': [key],
            'label': row['label'],
            'labelLanguage': 'fr',
            'description': text,
            'descriptionLanguage': text_language,
            'version': '26M10',
        }
    job = present(occupation_index()[key], language)
    refs = occupation_references(key)
    text, text_language = job['description'], language
    # Source-language text is preferred to an invented bilingual synthesis.
    if language == 'fr' and len(refs) > 1:
        text, text_language = rome_description(refs[1][5:], language)
    # Preserve the explicitly reviewed description from the successful baker trial.
    from eures_beta.skills import baker_mixed

    if key == baker_mixed.URI and baker_mixed.official_mapping():
        text = baker_mixed.catalogue()['candidateDescription'][language]
    value = reference if reference.startswith(('esco:', 'rome:')) else 'esco:' + key
    return {
        'value': value,
        'groupKey': key,
        'references': refs,
        'label': job['label'],
        'labelLanguage': language,
        'description': text,
        'descriptionLanguage': text_language,
        'version': '1.2.1',
    }


def group_rows(rows):
    result = {}
    for row in rows:
        if row:
            result.setdefault(row['groupKey'], row)
    return list(result.values())


def search_occupations(query, language, *, mode='search', excluded=(), context=''):
    from .catalog import rome_suggestions

    query = query.strip()
    if not 2 <= len(query) <= 150:
        return []
    is_rome = is_rome_reference(query)
    is_ref = looks_like_reference(query)
    esco = (
        []
        if is_rome
        else (
            references(query, language)
            if is_ref or mode == 'reference'
            else (
                nearby(query, language, list(excluded), context)
                if mode == 'near'
                else suggestions(query, language, context)
            )
        )
    )
    return group_rows(
        [resolve_reference('esco:' + row['uri'], language) for row in esco[:20]]
        + [
            resolve_reference('rome:' + row['code'], language)
            for row in rome_suggestions(query, context)
        ]
    )
