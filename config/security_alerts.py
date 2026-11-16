"""Review and apply explicit CodeQL decisions; no Django, shell or automatic triage."""

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

REPOSITORY = 'eures-beta/match-europe'
ROOT = f'repos/{REPOSITORY}/code-scanning/alerts'
REASONS = {'false positive', "won't fix", 'used in tests', 'mitigated'}
STATES = {'open', 'dismissed'}
SNAPSHOT_KEYS = {
    'state',
    'rule_id',
    'path',
    'dismissed_reason',
    'dismissed_comment',
    'commit_sha',
    'ref',
    'start_line',
}
MAX_BYTES = 100_000
MAX_ALERTS = 50


class AlertError(ValueError):
    pass


def gh_api(endpoint, *, method='GET', payload=None):
    command = [
        'gh',
        'api',
        '--hostname',
        'github.com',
        '--method',
        method,
        endpoint,
        '-H',
        'Accept: application/vnd.github+json',
        '-H',
        'X-GitHub-Api-Version: 2026-03-10',
    ]
    if payload is not None:
        command += ['--input', '-']
    try:
        result = subprocess.run(
            command,
            input=json.dumps(payload) if payload is not None else None,
            text=True,
            encoding='utf-8',
            capture_output=True,
            timeout=45,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise AlertError(
            'Commande gh indisponible ou délai dépassé ; aucun réessai automatique.'
        ) from error
    if result.returncode:
        raise AlertError(f'GitHub refuse la requête : {result.stderr[:1500].strip()}')
    try:
        return json.loads(result.stdout)
    except (ValueError, TypeError) as error:
        raise AlertError(
            'Réponse GitHub JSON invalide ; vérifier l’état avant de reprendre.'
        ) from error


def snapshot(alert):
    try:
        return {
            'state': alert['state'],
            'commit_sha': alert['most_recent_instance']['commit_sha'],
            'ref': alert['most_recent_instance']['ref'],
            'start_line': alert['most_recent_instance']['location']['start_line'],
            'rule_id': alert['rule']['id'],
            'path': alert['most_recent_instance']['location']['path'],
            'dismissed_reason': alert.get('dismissed_reason'),
            'dismissed_comment': alert.get('dismissed_comment'),
        }
    except (KeyError, TypeError) as error:
        raise AlertError('Métadonnées GitHub incomplètes.') from error


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise AlertError(f'Clé JSON répétée : {key}.')
        result[key] = value
    return result


def text(value, label, *, maximum=1000):
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise AlertError(
            f'{label} doit être un texte non vide de {maximum} caractères maximum.'
        )
    if any(ord(char) < 32 or ord(char) == 127 for char in value):
        raise AlertError(f'{label} contient un caractère de contrôle.')


def validate(plan):
    if (
        not isinstance(plan, dict)
        or set(plan) != {'repository', 'alerts'}
        or plan['repository'] != REPOSITORY
    ):
        raise AlertError(
            f'Le plan doit cibler uniquement {REPOSITORY}, avec repository et alerts.'
        )
    decisions = plan['alerts']
    if not isinstance(decisions, list) or not 1 <= len(decisions) <= MAX_ALERTS:
        raise AlertError(f'Prévoir entre 1 et {MAX_ALERTS} décisions explicites.')
    seen = set()
    for item in decisions:
        if not isinstance(item, dict) or set(item) != {
            'number',
            'expected',
            'state',
            'reason',
            'comment',
        }:
            raise AlertError(
                'Chaque décision nécessite number, expected, state, reason et comment uniquement.'
            )
        number = item['number']
        if type(number) is not int or number < 1 or number in seen:
            raise AlertError('Numéro d’alerte positif, entier et unique requis.')
        seen.add(number)
        expected = item['expected']
        if not isinstance(expected, dict) or set(expected) != SNAPSHOT_KEYS:
            raise AlertError(
                f'Alerte {number} : recopier le bloc expected de security-alerts.'
            )
        if (
            not isinstance(expected['state'], str)
            or not isinstance(item['state'], str)
            or expected['state'] not in STATES
            or item['state'] not in STATES
        ):
            raise AlertError(
                'Seuls les états open et dismissed sont modifiables ; jamais fixed.'
            )
        text(expected['rule_id'], 'rule_id')
        text(expected['path'], 'path')
        text(expected['commit_sha'], 'commit_sha')
        text(expected['ref'], 'ref')
        if type(expected['start_line']) is not int or expected['start_line'] < 1:
            raise AlertError('Ligne de code attendue invalide.')
        if expected['state'] == 'dismissed':
            if (
                not isinstance(expected['dismissed_reason'], str)
                or expected['dismissed_reason'] not in REASONS
            ):
                raise AlertError('Motif attendu inconnu.')
        elif expected['dismissed_reason'] is not None:
            raise AlertError(
                'Une alerte ouverte ne doit pas avoir de motif attendu de classement.'
            )
        if expected['dismissed_comment'] is not None and not isinstance(
            expected['dismissed_comment'], str
        ):
            raise AlertError('Commentaire attendu invalide.')
        text(item['comment'], 'Justification individuelle', maximum=280)
        if item['state'] == 'dismissed' and (
            not isinstance(item['reason'], str) or item['reason'] not in REASONS
        ):
            raise AlertError('Motif individuel de classement requis.')
        if item['state'] == 'open' and item['reason'] is not None:
            raise AlertError('Une réouverture utilise reason=null.')
    return decisions


def load_plan(filename):
    if not filename:
        raise AlertError('Indiquer FILE=chemin/decisions.json.')
    try:
        with Path(filename).open('rb') as source:
            raw = source.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            raise AlertError('Plan trop volumineux.')
        plan = json.loads(raw, object_pairs_hook=unique_object)
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise AlertError(f'Impossible de lire le plan JSON : {error}.') from error
    validate(plan)
    return plan


def desired(item):
    result = {'state': item['state']}
    if item['state'] == 'dismissed':
        result.update(
            dismissed_reason=item['reason'], dismissed_comment=item['comment']
        )
    return result


def inspect(item, api):
    alert = api(f'{ROOT}/{item["number"]}')
    if not isinstance(alert, dict) or alert.get('number') != item['number']:
        raise AlertError('Numéro inattendu dans la réponse GitHub.')
    current = snapshot(alert)
    expected = item['expected']
    if any(
        current[key] != expected[key]
        for key in ('rule_id', 'path', 'commit_sha', 'ref', 'start_line')
    ):
        raise AlertError(
            f'Alerte {item["number"]} déplacée, code ou règle modifié : revoir le plan.'
        )
    wanted = desired(item)
    done = all(alert.get(key) == value for key, value in wanted.items())
    if not done and current != expected:
        raise AlertError(
            f'Alerte {item["number"]} modifiée depuis la revue : revoir le plan.'
        )
    return current, done


def prepare(plan, api=gh_api):
    decisions = validate(plan)
    changes = []
    for item in decisions:
        current, done = inspect(item, api)
        changes.append(
            {
                'number': item['number'],
                'current': current,
                'desired': desired(item),
                'justification': item['comment'],
                'action': 'déjà appliqué' if done else 'modifier',
            }
        )
    return {'repository': REPOSITORY, 'changes': changes}


def apply(plan, api=gh_api, emit=print):
    # Validate the WHOLE batch before the first PATCH, then recheck each item.
    preview = prepare(plan, api)
    emit(json.dumps({'event': 'plan', **preview}, ensure_ascii=False))
    for item in plan['alerts']:
        _, done = inspect(item, api)
        if done:
            emit(json.dumps({'event': 'unchanged', 'number': item['number']}))
            continue
        alert = api(f'{ROOT}/{item["number"]}', method='PATCH', payload=desired(item))
        if (
            not isinstance(alert, dict)
            or alert.get('number') != item['number']
            or not all(alert.get(key) == value for key, value in desired(item).items())
        ):
            raise AlertError(
                f'Alerte {item["number"]} : résultat non confirmé ; consulter GitHub avant reprise.'
            )
        emit(
            json.dumps(
                {'event': 'applied', 'number': item['number'], 'state': alert['state']}
            )
        )


def list_alerts(api=gh_api):
    alerts = []
    for page in range(1, 11):
        batch = api(f'{ROOT}?per_page=100&page={page}')
        if not isinstance(batch, list):
            raise AlertError('Liste GitHub invalide.')
        for alert in batch:
            if not isinstance(alert, dict) or type(alert.get('number')) is not int:
                raise AlertError('Alerte GitHub invalide.')
            if alert.get('state') in STATES:
                alerts.append(
                    {
                        'number': alert['number'],
                        'expected': snapshot(alert),
                        'state': None,
                        'reason': None,
                        'comment': '',
                    }
                )
        if len(batch) < 100:
            return {'repository': REPOSITORY, 'alerts': alerts}
    raise AlertError('Plus de 1000 alertes : réduire le périmètre avant de continuer.')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=['list', 'plan', 'apply'])
    args = parser.parse_args(argv)
    try:
        if args.operation == 'list':
            result = list_alerts()
        else:
            plan = load_plan(os.environ.get('SECURITY_ALERT_FILE'))
            if args.operation == 'apply':
                apply(plan)
                return 0
            result = prepare(plan)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except AlertError as error:
        print(f'ERREUR : {error}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
