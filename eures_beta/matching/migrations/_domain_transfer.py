"""Frozen helpers for the matching-domain extraction, independent of live models."""

import hashlib

DOMAIN_MODELS = {
    'introductions': (
        'CandidateOfferReview',
        'CandidateOfferReviewEvent',
        'CandidateOfferReviewAnswer',
        'CandidateProfileSharing',
        'CandidateOfferConversation',
        'CandidateOfferConversationMessage',
        'EmployerCandidateReview',
    ),
    'followup': (
        'JobOfferSupport',
        'CandidateSupport',
        'MatchFollowup',
        'MatchFollowupEvent',
        'MatchConclusion',
        'MatchConclusionEvent',
    ),
}


def move_content_types(apps, schema_editor, *, reverse=False):
    alias = schema_editor.connection.alias
    ContentType = apps.get_model('contenttypes', 'ContentType')
    for app, models in DOMAIN_MODELS.items():
        source, target = (app, 'matching') if reverse else ('matching', app)
        for name in models:
            query = ContentType.objects.using(alias).filter(model=name.lower())
            previous = query.filter(app_label=source).first()
            if previous is None:
                continue
            if query.filter(app_label=target).exists():
                raise RuntimeError(
                    f'Conflicting content types for {name}; refusing to merge permissions.'
                )
            # Keep PKs: grants and admin log entries reference these identities.
            query.filter(pk=previous.pk).update(app_label=target)


def forward_content_types(apps, schema_editor):
    move_content_types(apps, schema_editor)


def backward_content_types(apps, schema_editor):
    move_content_types(apps, schema_editor, reverse=True)


def object_name(table, columns, suffix):
    value = '_'.join([table, *columns, suffix])
    return (
        value
        if len(value) <= 63
        else value[:54] + '_' + hashlib.sha256(value.encode()).hexdigest()[:8]
    )


def normalize_domain(apps, schema_editor, app, *, reverse=False):
    connection = schema_editor.connection
    if connection.vendor != 'postgresql':
        raise RuntimeError('Domain extraction requires PostgreSQL.')
    quote = schema_editor.quote_name
    for name in DOMAIN_MODELS[app]:
        model = apps.get_model(app, name)
        table = model._meta.db_table
        old_table = f'{app if reverse else "matching"}_{name.lower()}'
        target_table = f'{"matching" if reverse else app}_{name.lower()}'
        declared = {}
        for item in (*model._meta.constraints, *model._meta.indexes):
            suffix = item.name.removeprefix(app + '_')
            declared['matching_' + suffix] = app + '_' + suffix
        if reverse:
            declared = {new: old for old, new in declared.items()}
        with connection.cursor() as cursor:
            objects = connection.introspection.get_constraints(cursor, table)
            plan = []
            for old, details in objects.items():
                columns = details['columns']
                if not columns or any(not isinstance(c, str) for c in columns):
                    raise RuntimeError(f'Unexpected schema expression on {table}.')
                if details['primary_key']:
                    kind, suffix, columns = 'CONSTRAINT', 'pkey', []
                elif details['foreign_key']:
                    kind, suffix = 'CONSTRAINT', 'fk'
                elif details['check']:
                    kind, suffix = 'CONSTRAINT', 'check'
                elif details['unique'] and not details['index']:
                    kind, suffix = 'CONSTRAINT', 'key'
                elif details['index']:
                    kind = 'INDEX'
                    suffix = 'unique_idx' if details['unique'] else 'idx'
                    cursor.execute('SELECT pg_get_indexdef(%s::regclass)', [quote(old)])
                    if '_pattern_ops' in cursor.fetchone()[0]:
                        suffix = 'like'
                else:
                    raise RuntimeError(f'Unexpected schema object: {table}.{old}')
                new = declared.get(old, object_name(target_table, columns, suffix))
                # Already renamed declared objects are not renamed a second time.
                if old in declared.values():
                    new = old
                plan.append((kind, old, new))
            cursor.execute(
                'SELECT c.conname, a.attname FROM pg_constraint c '
                'JOIN pg_attribute a ON a.attrelid=c.conrelid '
                'AND a.attnum=c.conkey[1] '
                "WHERE c.conrelid=%s::regclass AND c.contype='n'",
                [quote(table)],
            )
            plan.extend(
                ('CONSTRAINT', old, object_name(target_table, [column], 'not_null'))
                for old, column in cursor.fetchall()
            )
            targets = [new for _, _, new in plan]
            if len(targets) != len(set(targets)):
                raise RuntimeError(f'Ambiguous schema names on {table}.')
            for kind, old, new in plan:
                if old == new:
                    continue
                if kind == 'CONSTRAINT':
                    schema_editor.execute(
                        f'ALTER TABLE {quote(table)} RENAME CONSTRAINT {quote(old)} TO {quote(new)}'
                    )
                else:
                    schema_editor.execute(
                        f'ALTER INDEX {quote(old)} RENAME TO {quote(new)}'
                    )
            for field in model._meta.local_fields:
                cursor.execute(
                    'SELECT n.nspname, c.relname FROM pg_class c '
                    'JOIN pg_namespace n ON n.oid=c.relnamespace '
                    'WHERE c.oid=pg_get_serial_sequence(%s, %s)::regclass',
                    [quote(table), field.column],
                )
                sequence = cursor.fetchone()
                if sequence:
                    namespace, old = sequence
                    new = object_name(target_table, [field.column], 'seq')
                    if old != new:
                        schema_editor.execute(
                            f'ALTER SEQUENCE {quote(namespace)}.{quote(old)} RENAME TO {quote(new)}'
                        )
            cursor.execute(
                'SELECT t.tgname, p.oid, p.proname, pg_get_functiondef(p.oid) '
                'FROM pg_trigger t JOIN pg_proc p ON p.oid=t.tgfoid '
                'WHERE t.tgrelid=%s::regclass AND NOT t.tgisinternal',
                [quote(table)],
            )
            for trigger, oid, function, definition in cursor.fetchall():
                if not function.startswith(old_table + '_'):
                    raise RuntimeError(f'Unexpected role guard on {table}: {function}')
                new_function = function.replace(old_table, target_table, 1)
                new_trigger = trigger.replace(old_table, target_table, 1)
                schema_editor.execute(
                    f'ALTER FUNCTION {quote(function)}() RENAME TO {quote(new_function)}'
                )
                # PostgreSQL tracks trigger references by OID; replacing its body
                # keeps that identity while removing obsolete table names.
                for domain, names in DOMAIN_MODELS.items():
                    for moved in sorted(names, key=len, reverse=True):
                        source = f'{domain if reverse else "matching"}_{moved.lower()}'
                        target = f'{"matching" if reverse else domain}_{moved.lower()}'
                        definition = definition.replace(source, target)
                schema_editor.execute(definition)
                schema_editor.execute(
                    f'ALTER TRIGGER {quote(trigger)} ON {quote(table)} RENAME TO {quote(new_trigger)}'
                )
