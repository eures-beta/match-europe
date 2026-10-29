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
        'rome': row.get('rome', []),
        'rome_fiches': row.get('romeFiches', []),
        'rome_unresolved': row.get('romeUnresolved', []),
    }


def suggestions(query, language):
    query = normalize(query)
    if not query:
        return []
    index = search_index(language)
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


def nearby(query, language, excluded=()):
    """Other occupations in an explicitly related ESCO/ISCO family, not an equivalence."""
    jobs = occupation_index()
    # Anchor related jobs to the best match: lower-ranked matches may describe
    # another activity (e.g. bakery manager rather than baker).
    seeds = [jobs[row['uri']] for row in suggestions(query, language)[:1]]
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
