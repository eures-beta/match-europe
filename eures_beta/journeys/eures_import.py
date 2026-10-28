"""Read one public EURES vacancy, using the JSON resource used by its website.

No browser, authentication, translation service or links from the response are
used. Network access remains with offer_ingestion's bounded, DNS-pinned reader.
"""

import json
import re
from urllib.parse import parse_qs, urlsplit


def read_eures(url, fetch):
    # Imported here to avoid a cycle with the generic reader's small dispatcher.
    from .offer_ingestion import ImportFailure, empty_data, plain

    parsed = urlsplit(url)
    match = re.fullmatch(
        r'/eures/portal/jv-se/jv-details/([A-Za-z0-9_-]+={0,2})/?', parsed.path
    )
    if not match:
        # Handle lengths vary by provider. Only path delimiters are restricted;
        # the public API and returned id establish whether the vacancy exists.
        raise ImportFailure('unreadable_url')
    handle = match.group(1)
    query = parse_qs(parsed.query)
    requested = query.get('jvDisplayLanguage', [''])[0]
    interface = query.get('lang', ['en'])[0]
    interface = interface if re.fullmatch(r'[a-z]{2,3}', interface) else 'en'
    endpoint = (
        'https://europa.eu/eures/api/jv-searchengine/public/jv/id/'
        + handle
        + '?requestLang='
        + interface
    )
    raw, _ = fetch(endpoint, ('application/json',), allow_redirects=False)
    try:
        item = json.loads(raw)
    except (ValueError, RecursionError):
        raise ImportFailure('unreadable_url') from None
    if not isinstance(item, dict) or item.get('id') != handle:
        raise ImportFailure('unreadable_url')
    profiles = item.get('jvProfiles')
    if not isinstance(profiles, dict) or not profiles:
        raise ImportFailure('unreadable_url')
    # Use an existing language version only. Never call automatic translation.
    language = requested if requested in profiles else item.get('preferredLanguage')
    if not isinstance(language, str) or language not in profiles:
        language = next(iter(profiles))
    profile = profiles[language]
    if not isinstance(profile, dict):
        raise ImportFailure('unreadable_url')
    data = empty_data()
    data['title'] = plain(profile.get('title'))[:125]
    description = plain(profile.get('description'))
    if not data['title'] or not description:
        raise ImportFailure('unreadable_url')
    data['extraction'] = 'eures_public'
    data['sourceLanguage'] = language
    employer = profile.get('employer')
    if isinstance(employer, dict):
        data['companyName'] = plain(employer.get('name'))[:100]
    # Only job locations, never the employer/contact's mailing address.
    locations = profile.get('locations')
    if isinstance(locations, list):
        places = []
        for location in locations:
            if isinstance(location, dict):
                parts = [
                    plain(location.get(key))
                    for key in ('postalCode', 'cityName', 'countryCode')
                ]
                if parts[-1]:
                    parts[-1] = parts[-1].upper()
                place = ', '.join(part for part in parts if part)
                if place:
                    places.append(place)
        data['city'] = ' ; '.join(dict.fromkeys(places))[:150]
    # Preserve remuneration text without guessing a salary, hours or contract
    # from prose or interpreting fulltime/directhire as a permanent contract.
    remuneration = profile.get('offeredRemunerationPackage')
    if isinstance(remuneration, dict):
        extra = [plain(remuneration.get('description'))]
        summaries = remuneration.get('benefitsSummaries')
        if isinstance(summaries, list):
            for summary in summaries:
                benefit = (
                    summary.get('otherBenefit') if isinstance(summary, dict) else None
                )
                if isinstance(benefit, dict):
                    extra.append(plain(benefit.get('description')))
        description = '\n\n'.join([description, *(text for text in extra if text)])
    data['description'] = description[:16000]
    return data
