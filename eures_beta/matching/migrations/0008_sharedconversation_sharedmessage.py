"""Create shared conversations after model renames, adopting only verified previews."""

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
from django.db.migrations.recorder import MigrationRecorder
from django.db.migrations.state import ProjectState

CREATE_MODELS = [
    migrations.CreateModel(
        name='SharedConversation',
        fields=[
            (
                'id',
                models.BigAutoField(
                    auto_created=True,
                    primary_key=True,
                    serialize=False,
                    verbose_name='ID',
                ),
            ),
            (
                'state',
                models.CharField(
                    choices=[
                        ('requested', 'Requested'),
                        ('approved', 'Approved'),
                        ('declined', 'Declined'),
                        ('open', 'Open'),
                    ],
                    default='requested',
                    max_length=12,
                ),
            ),
            ('introduction', models.TextField(max_length=2000)),
            ('consent_at', models.DateTimeField(blank=True, null=True)),
            ('adviser_read', models.PositiveBigIntegerField(default=0)),
            ('candidate_read', models.PositiveBigIntegerField(default=0)),
            ('employer_read', models.PositiveBigIntegerField(default=0)),
            (
                'adviser',
                models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='+',
                    to=settings.AUTH_USER_MODEL,
                ),
            ),
            (
                'candidate',
                models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='+',
                    to=settings.AUTH_USER_MODEL,
                ),
            ),
            (
                'confirmation',
                models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='shared_conversation',
                    to='matching.candidateofferreview',
                ),
            ),
            (
                'employer',
                models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='+',
                    to=settings.AUTH_USER_MODEL,
                ),
            ),
        ],
    ),
    migrations.CreateModel(
        name='SharedMessage',
        fields=[
            (
                'id',
                models.BigAutoField(
                    auto_created=True,
                    primary_key=True,
                    serialize=False,
                    verbose_name='ID',
                ),
            ),
            ('body', models.TextField(max_length=2000)),
            ('created_at', models.DateTimeField(auto_now_add=True)),
            (
                'author',
                models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    to=settings.AUTH_USER_MODEL,
                ),
            ),
            (
                'conversation',
                models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='messages',
                    to='matching.sharedconversation',
                ),
            ),
        ],
    ),
]

LEGACY = '0007_sharedconversation_sharedmessage'


def conversation_models(apps):
    state = ProjectState.from_apps(apps)
    for operation in CREATE_MODELS:
        operation.state_forwards('matching', state)
    return [
        state.apps.get_model('matching', operation.name) for operation in CREATE_MODELS
    ]


def legacy_applied(connection):
    return ('matching', LEGACY) in MigrationRecorder(connection).applied_migrations()


def validate_schema(connection, model):
    """Adopt only the complete, structurally equivalent PostgreSQL schema."""
    table = model._meta.db_table
    expected_columns = []
    for field in model._meta.local_fields:
        data_type = field.db_type(connection).replace('varchar(', 'character varying(')
        data_type = data_type.replace('timestamptz', 'timestamp with time zone')
        identity = 'd' if isinstance(field, models.AutoField) else ''
        expected_columns.append(
            (field.column, data_type, field.null, identity, None, False)
        )
    with connection.cursor() as cursor:
        cursor.execute(
            'SELECT a.attname, format_type(a.atttypid,a.atttypmod), NOT a.attnotnull, '
            'a.attidentity, pg_get_expr(d.adbin,d.adrelid), '
            'a.attcollation <> t.typcollation '
            'FROM pg_attribute a JOIN pg_type t ON t.oid=a.atttypid '
            'LEFT JOIN pg_attrdef d ON d.adrelid=a.attrelid AND d.adnum=a.attnum '
            'WHERE a.attrelid=%s::regclass AND a.attnum>0 AND NOT a.attisdropped '
            'ORDER BY a.attnum',
            [table],
        )
        columns = cursor.fetchall()
        constraints = connection.introspection.get_constraints(cursor, table)
        cursor.execute(
            'SELECT EXISTS (SELECT 1 FROM pg_constraint c '
            'JOIN pg_class r ON r.oid=c.confrelid '
            'JOIN pg_namespace n ON n.oid=r.relnamespace '
            "WHERE c.conrelid=%s::regclass AND c.contype='f' AND "
            "(NOT c.convalidated OR NOT c.condeferrable OR NOT c.condeferred "
            "OR c.confdeltype<>'a' OR c.confupdtype<>'a' OR n.nspname<>'public'))",
            [table],
        )
        invalid_fk = cursor.fetchone()[0]
        cursor.execute(
            'SELECT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid=%s::regclass '
            "AND ((contype IN ('p','u') AND "
            '(condeferrable OR condeferred OR NOT convalidated)) '
            "OR contype NOT IN ('p','u','f','n','c')))",
            [table],
        )
        invalid_constraint = cursor.fetchone()[0]
        cursor.execute(
            'SELECT EXISTS (SELECT 1 FROM pg_index i '
            'JOIN pg_class r ON r.oid=i.indexrelid JOIN pg_am a ON a.oid=r.relam '
            'WHERE i.indrelid=%s::regclass AND (NOT i.indisvalid OR NOT i.indisready '
            "OR i.indpred IS NOT NULL OR i.indexprs IS NOT NULL OR a.amname<>'btree' "
            'OR i.indnatts<>i.indnkeyatts))',
            [table],
        )
        invalid_index = cursor.fetchone()[0]
    expected_checks = sorted(
        'CHECK ' + field.column + ' >= 0'
        for field in model._meta.local_fields
        if isinstance(field, models.PositiveBigIntegerField)
    )
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT pg_get_constraintdef(oid), convalidated, connoinherit "
            "FROM pg_constraint WHERE conrelid=%s::regclass AND contype='c'",
            [table],
        )
        checks = cursor.fetchall()
    actual_checks = sorted(
        ' '.join(definition.replace('"', '').replace('(', '').replace(')', '').split())
        for definition, _, _ in checks
    )
    if any(not validated or noinherit for _, validated, noinherit in checks):
        raise RuntimeError('Invalid shared conversation check constraint.')
    actual_pk = sorted(
        tuple(c['columns']) for c in constraints.values() if c['primary_key']
    )
    actual_unique = sorted(
        tuple(c['columns'])
        for c in constraints.values()
        if c['unique'] and not c['primary_key']
    )
    actual_fk = sorted(
        (tuple(c['columns']), c['foreign_key'])
        for c in constraints.values()
        if c['foreign_key']
    )
    actual_index = sorted(
        tuple(c['columns'])
        for c in constraints.values()
        if c['index'] and not c['unique'] and not c['primary_key']
    )
    fields = model._meta.local_fields
    expected_pk = [(model._meta.pk.column,)]
    expected_unique = sorted(
        (f.column,) for f in fields if f.unique and not f.primary_key
    )
    expected_fk = sorted(
        ((f.column,), (f.remote_field.model._meta.db_table, f.target_field.column))
        for f in fields
        if f.remote_field and f.db_constraint
    )
    expected_index = sorted((f.column,) for f in fields if f.db_index and not f.unique)
    if (
        columns != expected_columns
        or actual_pk != expected_pk
        or actual_unique != expected_unique
        or actual_fk != expected_fk
        or actual_index != expected_index
        or invalid_fk
        or invalid_constraint
        or invalid_index
        or actual_checks != expected_checks
    ):
        raise RuntimeError(
            f'Legacy shared conversation schema mismatch: {table}; inspect before migrating.'
        )


def forwards(apps, schema_editor):
    connection = schema_editor.connection
    models_to_create = conversation_models(apps)
    expected = {model._meta.db_table for model in models_to_create}
    present = expected & set(connection.introspection.table_names())
    legacy = legacy_applied(connection)
    if not present and not legacy:
        for model in models_to_create:
            schema_editor.create_model(model)
        return
    if present != expected or not legacy:
        raise RuntimeError(
            'Unexpected shared conversation schema: inspect before migrating.'
        )
    for model in models_to_create:
        validate_schema(connection, model)


def backwards(apps, schema_editor):
    models_to_remove = conversation_models(apps)
    if legacy_applied(schema_editor.connection):
        for model in models_to_remove:
            validate_schema(schema_editor.connection, model)
        return
    for model in reversed(models_to_remove):
        schema_editor.delete_model(model)


class Migration(migrations.Migration):
    dependencies = [
        ('matching', '0007_candidate_offer_review_answer_dialogue'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]
    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=CREATE_MODELS,
            database_operations=[migrations.RunPython(forwards, backwards)],
        ),
    ]
