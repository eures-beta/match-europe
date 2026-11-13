"""Add dialogue after the model renames, preserving previously deployed previews."""

from django.db import migrations, models
from django.db.migrations.recorder import MigrationRecorder

LEGACY = '0006_confirmationanswer_dialogue'
TABLE = 'matching_confirmationanswer'


def legacy_applied(connection):
    return ('matching', LEGACY) in MigrationRecorder(connection).applied_migrations()


def dialogue_column(connection):
    with connection.cursor() as cursor:
        cursor.execute(
            'SELECT format_type(a.atttypid,a.atttypmod), NOT a.attnotnull, '
            'pg_get_expr(d.adbin,d.adrelid), a.attgenerated '
            'FROM pg_attribute a LEFT JOIN pg_attrdef d '
            'ON d.adrelid=a.attrelid AND d.adnum=a.attnum '
            'WHERE a.attrelid=%s::regclass AND a.attname=%s '
            'AND a.attnum>0 AND NOT a.attisdropped',
            [TABLE, 'dialogue'],
        )
        return cursor.fetchone()


def answer_and_field(apps):
    model = apps.get_model('matching', 'CandidateOfferReviewAnswer')
    field = models.JSONField(blank=True, default=dict)
    field.set_attributes_from_name('dialogue')
    return model, field


def forwards(apps, schema_editor):
    connection = schema_editor.connection
    column = dialogue_column(connection)
    legacy = legacy_applied(connection)
    if column is None and not legacy:
        model, field = answer_and_field(apps)
        schema_editor.add_field(model, field)
    elif column != ('jsonb', False, None, '') or not legacy:
        raise RuntimeError('Unexpected dialogue schema: inspect before migrating.')


def backwards(apps, schema_editor):
    connection = schema_editor.connection
    if dialogue_column(connection) != ('jsonb', False, None, ''):
        raise RuntimeError('Unexpected dialogue schema: inspect before migrating.')
    if not legacy_applied(connection):
        model, field = answer_and_field(apps)
        schema_editor.remove_field(model, field)
    # An adopted preview column still belongs to its original recorded migration.


class Migration(migrations.Migration):
    dependencies = [('matching', '0006_candidate_offer_model_names')]
    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddField(
                    model_name='candidateofferreviewanswer',
                    name='dialogue',
                    field=models.JSONField(blank=True, default=dict),
                ),
            ],
            database_operations=[migrations.RunPython(forwards, backwards)],
        ),
    ]
