"""Versioned occupation reference data, loaded locally with no network access."""

import hashlib
import json
import re
import unicodedata
from difflib import get_close_matches
from functools import lru_cache, wraps
from pathlib import Path
from threading import RLock

import ijson

DATA_DIR = Path(__file__).parent / 'data'
LANGUAGES = ('fr', 'en', 'de')
_LOAD_LOCK = RLock()


def serialized_cache(maxsize):
    """Serialize cache misses as well as publication, including nested loaders.

    lru_cache alone allows concurrent first requests to build several copies.
    """

    def decorate(function):
        cached = lru_cache(maxsize=maxsize)(function)

        @wraps(function)
        def wrapped(*args, **kwargs):
            with _LOAD_LOCK:
                return cached(*args, **kwargs)

        def clear():
            with _LOAD_LOCK:
                cached.cache_clear()

        wrapped.cache_clear = clear
        wrapped.cache_info = cached.cache_info
        return wrapped

    return decorate


def read_artifact(path, manifest):
    """Verify and parse the same open file without full bytes/text copies."""
    with path.open('rb') as source:
        checksum = hashlib.file_digest(source, 'sha256').hexdigest()
        if checksum != manifest['artifacts'][path.name]['sha256']:
            raise ValueError('Occupation catalog checksum mismatch')
        source.seek(0)
        values = ijson.items(source, '', use_float=True)
        value = next(values)
        # Exhaust to validate the complete document, including trailing content.
        if next(values, None) is not None:
            raise ValueError('Unexpected additional catalog document')
        return value


def normalize(value):
    value = unicodedata.normalize('NFKD', value.casefold())
    return re.sub(
        r'[^a-z0-9]+', ' ', ''.join(c for c in value if not unicodedata.combining(c))
    ).strip()


@serialized_cache(maxsize=1)
def catalog():
    manifest = json.loads((DATA_DIR / 'manifest.json').read_text())
    path = DATA_DIR / 'esco.json'
    value = read_artifact(path, manifest)
    if len(value['occupations']) != manifest['counts']['occupations']:
        raise ValueError('Occupation catalog count mismatch')
    return {
        **value,
        'manifest': manifest,
        'romeSource': {'url': manifest['sources'][3]['url']},
        'romeFicheSource': {'url': manifest['sources'][4]['url']},
    }


@serialized_cache(maxsize=1)
def rome_catalog():
    manifest = catalog()['manifest']
    result = {}
    for name in ('rome.json', 'ogr.json', 'esco_rome.json'):
        path = DATA_DIR / name
        result.update(read_artifact(path, manifest))
    return result


@serialized_cache(maxsize=1)
def rome_search_catalog():
    """Independent ROME lookup needs names/codes, never the ESCO crosswalk."""
    manifest = catalog()['manifest']
    result = {}
    for name in ('rome.json', 'ogr.json'):
        result.update(read_artifact(DATA_DIR / name, manifest))
    return result


@serialized_cache(maxsize=1)
def occupation_index():
    return {row['uri']: row for row in catalog()['occupations']}


@serialized_cache(maxsize=3)
def search_index(language):
    if language not in LANGUAGES:
        raise ValueError('Unsupported catalog language')
    index = {}
    for row in catalog()['occupations']:
        for term in [row['labels'][language], *row['aliases'].get(language, [])]:
            key = normalize(term)
            if key:
                uris = index.setdefault(key, [])
                if row['uri'] not in uris:
                    uris.append(row['uri'])
    return index


def present(row, language):
    return {
        'uri': row['uri'],
        'label': row['labels'][language],
        'description': row['descriptions'][language],
        'reference': row['uri'].rsplit('/', 1)[-1],
        'esco_code': row['code'],
        'rome': row.get('rome', []),
        'rome_fiches': row.get('romeFiches', []),
        'rome_unresolved': row.get('romeUnresolved', []),
    }


def references(value, language):
    """Exact local ESCO URI/UUID/code or five-character ROME fiche lookup."""
    value = re.sub(r'^(ESCO|ROME)\s*[:—-]?\s*', '', value.strip(), flags=re.I)
    rows = []
    for row in catalog()['occupations']:
        if value.casefold() in (
            row['uri'].casefold(),
            row['uri'].rsplit('/', 1)[-1].casefold(),
            row['code'].casefold(),
        ) or any(fiche['code'] == value.upper() for fiche in row.get('romeFiches', [])):
            rows.append(present(row, language))
    return sorted(rows, key=lambda row: (normalize(row['label']), row['uri']))


def search_title(value):
    """Ignore recruitment annotations for lookup only; keep the stored title intact."""

    def annotation(match):
        text = match.group()[1:-1].casefold()
        # Preserve the old annotation grammar without nested quantifiers. Spaces
        # count as base characters in that grammar; other parenthetical text stays.
        base = 'mfw dhx'
        if text and text[0] in base and sum(char in base for char in text) >= 2:
            return ' '
        return match.group()

    # One non-overlapping character-class scan. An absent ')' or an invalid
    # character cannot trigger exponential backtracking and monopolize the GIL.
    value = re.sub(r'\([mfw dhx/·, -]*\)', annotation, value, flags=re.I)
    value = re.split(
        r'\s*[-–—|,]\s*(?=(?:CDI|CDD|full[ -]time|part[ -]time|\d+\s*h)\b)',
        value,
        maxsplit=1,
        flags=re.I,
    )[0]
    return normalize(value)


def suggestions(query, language, context=''):
    query = search_title(query)
    if not query:
        return []
    index = search_index(language)
    # A generic title can mean several jobs. Prefer explicit multilingual catalog
    # names present in the offer, rather than guessing a profession from generic
    # words. An exact title remains authoritative; no choice is ever automatic.
    if context and query not in index:
        text = ' ' + normalize(context) + ' '
        matches = {}
        for source_language in LANGUAGES:
            for term, uris in search_index(source_language).items():
                if len(term.split()) >= 3 and f' {term} ' in text:
                    for uri in uris:
                        matches[uri] = max(len(term), matches.get(uri, 0))
        if matches:
            jobs = occupation_index()
            ranked = sorted(matches, key=lambda uri: (-matches[uri], uri))
            return [present(jobs[uri], language) for uri in ranked[:3]]
    scores = {}
    words = query.split()
    for term, uris in index.items():
        score = (
            1000
            if query == term
            else (
                700
                if query in term
                else 600 if all(word in term.split() for word in words) else 0
            )
        )
        if score:
            for uri in uris:
                scores[uri] = max(score, scores.get(uri, 0))
    # A qualified title may have no exact catalog alias (e.g. an electrician
    # specialised in an industry). Offer the explicitly named broader occupation,
    # without treating the unmatched qualification as a code or an equivalence.
    if not scores:
        for term, uris in index.items():
            if len(term) >= 7 and query.startswith(term + ' '):
                for uri in uris:
                    scores[uri] = max(200 + len(term), scores.get(uri, 0))
    # Typo tolerance only when no lexical result exists; never rewrite the user's title.
    if not scores and 4 <= len(query) <= 80:
        for term in get_close_matches(query, index, n=3, cutoff=0.85):
            for uri in index[term]:
                scores[uri] = 100
    jobs = occupation_index()
    ranked = sorted(
        scores,
        key=lambda uri: (-scores[uri], normalize(jobs[uri]['labels'][language]), uri),
    )
    return [present(jobs[uri], language) for uri in ranked[:3]]


def nearby(query, language, excluded=(), context=''):
    """Other occupations in an explicitly related ESCO/ISCO family, not an equivalence."""
    jobs = occupation_index()
    # Anchor related jobs to the best match: lower-ranked matches may describe
    # another activity (e.g. bakery manager rather than baker).
    seeds = [jobs[row['uri']] for row in suggestions(query, language, context)[:1]]
    if not seeds:
        return []
    excluded = set(excluded)
    parents = {parent for row in seeds for parent in row['broader']}
    groups = {row['iscoGroup'] for row in seeds}
    seed_uris = {row['uri'] for row in seeds}
    ranked = []
    for row in jobs.values():
        if row['uri'] in excluded:
            continue
        related = (
            row['uri'] in parents
            or bool(set(row['broader']) & seed_uris)
            or bool(set(row['broader']) & parents)
        )
        score = 2 if related else 1 if row['iscoGroup'] in groups else 0
        if score:
            ranked.append((score, row))
    ranked.sort(
        key=lambda item: (
            -item[0],
            normalize(item[1]['labels'][language]),
            item[1]['uri'],
        )
    )
    return [present(row, language) for _, row in ranked[:3]]


def rome_suggestions(query, context=''):
    """Search French ROME names/codes directly, without the ESCO crosswalk."""
    query = re.sub(r'^ROME\s*[:—-]?\s*', '', query.strip(), flags=re.I)
    data = rome_search_catalog()
    if re.fullmatch(r'[A-Z]\d{4}', query, re.I):
        fiche = data['fiches'].get(query.upper())
        return [{**fiche, 'matched_labels': []}] if fiche else []
    query = search_title(query)
    if not query:
        return []
    scores, labels = {}, {}
    # Context only orders lexical candidates; never crosses ESCO into ROME.
    context_words = {word[:7] for word in normalize(context).split() if len(word) >= 5}
    context_terms = [word[:7] for word in normalize(context).split() if len(word) >= 5]
    for row in data['appellations'].values():
        term = normalize(row['label'])
        names = [normalize(part) for part in row['label'].split('/')]
        score = (
            (1100 if all(len(name.split()) == 1 for name in names) else 1000)
            if query in names
            else (
                700
                if query in term
                else 500 if all(word in term.split() for word in query.split()) else 0
            )
        )
        if not score:
            continue
        if context_words:
            score += 10 * len(
                {word[:7] for word in term.split() if len(word) >= 5} & context_words
            )
            # Prefer a supported activity phrase over dispersed generic words.
            terms = [word[:7] for word in names[-1].split() if len(word) >= 5]
            for first, second in zip(terms, terms[1:]):
                if any(
                    word == first and second in context_terms[i + 1 : i + 3]
                    for i, word in enumerate(context_terms)
                ):
                    score += 5
        for code in row['ficheCodes']:
            scores[code] = max(score, scores.get(code, 0))
            labels.setdefault(code, []).append((score, row['label']))
    ranked = sorted(
        scores,
        key=lambda code: (
            -scores[code],
            normalize(data['fiches'][code]['label']),
            code,
        ),
    )
    return [
        dict(
            data['fiches'][code],
            matched_labels=[
                label
                for _, label in sorted(
                    labels[code], key=lambda item: (-item[0], item[1])
                )[:3]
            ],
        )
        for code in ranked[:3]
    ]
