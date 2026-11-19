"""Original, versioned ROME descriptions; translations are explicitly editorial."""

import json
from .catalog import DATA_DIR, read_artifact, rome_search_catalog, serialized_cache


@serialized_cache(maxsize=1)
def catalogue():
    manifest = json.loads((DATA_DIR / 'rome_definitions_sources.json').read_text())
    data = read_artifact(DATA_DIR / 'rome_definitions.json', manifest)['definitions']
    if (
        manifest['version'] != '26M10'
        or len(data) != manifest['count']
        or set(data) != set(rome_search_catalog()['fiches'])
    ):
        raise ValueError('Incompatible ROME descriptions')
    return data


@serialized_cache(maxsize=1)
def translations():
    return json.loads((DATA_DIR / 'rome_definition_translations.json').read_text())


def description(code, language):
    original = catalogue().get(code, '')
    translated = translations().get(code, {}).get(language)
    return (translated, language) if translated else (original, 'fr')
