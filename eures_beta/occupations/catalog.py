"""Versioned occupation reference data, loaded locally with no network access."""

import gzip
import hashlib
import json
import re
import unicodedata
from difflib import get_close_matches
from functools import lru_cache
from pathlib import Path

DATA_DIR = Path(__file__).parent / 'data'
LANGUAGES = ('fr', 'en', 'de')


def normalize(value):
    value = unicodedata.normalize('NFKD', value.casefold())
    return re.sub(
        r'[^a-z0-9]+', ' ', ''.join(c for c in value if not unicodedata.combining(c))
    ).strip()


@lru_cache(maxsize=1)
def catalog():
    manifest = json.loads((DATA_DIR / 'manifest.json').read_text())
    path = DATA_DIR / 'occupations.json.gz'
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != manifest['artifacts'][path.name]['sha256']:
        raise ValueError('Occupation catalog checksum mismatch')
    value = json.loads(gzip.decompress(raw))
    if len(value['occupations']) != manifest['counts']['occupations']:
        raise ValueError('Occupation catalog count mismatch')
    return {
        **value,
        'manifest': manifest,
        'romeSource': {'url': manifest['sources'][3]['url']},
        'romeFicheSource': {'url': manifest['sources'][4]['url']},
    }


@lru_cache(maxsize=1)
def rome_catalog():
    manifest = catalog()['manifest']
    path = DATA_DIR / 'rome.json.gz'
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != manifest['artifacts'][path.name]['sha256']:
        raise ValueError('ROME catalog checksum mismatch')
    return json.loads(gzip.decompress(raw))


@lru_cache(maxsize=1)
def occupation_index():
    return {row['uri']: row for row in catalog()['occupations']}


@lru_cache(maxsize=3)
def search_index(language):
    if language not in LANGUAGES:
        raise ValueError('Unsupported catalog language')
    index = {}
    for row in catalog()['occupations']:
        for term in [row['labels'][language], *row['aliases'].get(language, [])]:
            key = normalize(term)
            if key:
                index.setdefault(key, set()).add(row['uri'])
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
    value = re.sub(r'\((?:[mfw dhx]+[/·, -]*){2,}\)', ' ', value, flags=re.I)
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


def rome_suggestions(query):
    """Search French ROME names/codes directly, without the ESCO crosswalk."""
    query = re.sub(r'^ROME\s*[:—-]?\s*', '', query.strip(), flags=re.I)
    data = rome_catalog()
    if re.fullmatch(r'[A-Z]\d{4}', query, re.I):
        fiche = data['fiches'].get(query.upper())
        return [{**fiche, 'matched_labels': []}] if fiche else []
    query = search_title(query)
    if not query:
        return []
    scores, labels = {}, {}
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
