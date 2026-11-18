"""Rename shared follow-up fields without recreating rows or their targets."""

from django.db import migrations, models


def normalize_relations(apps, schema_editor):
    table = apps.get_model('matching', 'AdviserSearchFollowUp')._meta.db_table
    quote = schema_editor.quote_name
    with schema_editor.connection.cursor() as cursor:
        constraints = schema_editor.connection.introspection.get_constraints(
            cursor, table
        )
    for old, details in constraints.items():
        columns = details['columns']
        if len(columns) != 1 or columns[0] not in {
            'offer_id',
            'candidate_id',
            'job_offer_id',
            'candidate_profile_id',
        }:
            continue
        if details['foreign_key']:
            suffix, kind = 'fk', 'CONSTRAINT'
        elif details['index']:
            suffix = 'unique_idx' if details['unique'] else 'idx'
            kind = 'INDEX'
        elif details['unique']:
            suffix, kind = 'key', 'CONSTRAINT'
        else:
            continue
        new = f'{table}_{columns[0]}_{suffix}'
        if old == new:
            continue
        if len(new) > 63:
            raise RuntimeError('Follow-up schema name exceeds PostgreSQL limit.')
        if kind == 'CONSTRAINT':
            schema_editor.execute(
                f'ALTER TABLE {quote(table)} RENAME CONSTRAINT {quote(old)} TO {quote(new)}'
            )
        else:
            schema_editor.execute(f'ALTER INDEX {quote(old)} RENAME TO {quote(new)}')


class Migration(migrations.Migration):
    dependencies = [('matching', '0013_search_followup_database_names')]
    operations = [
        migrations.RemoveConstraint(
            'advisersearchfollowup', 'matching_advisersearchfollowup_single_target'
        ),
        migrations.RunPython(migrations.RunPython.noop, normalize_relations),
        migrations.RenameField('advisersearchfollowup', 'offer', 'job_offer'),
        migrations.RenameField(
            'advisersearchfollowup', 'candidate', 'candidate_profile'
        ),
        migrations.RenameField('advisersearchfollowup', 'searching', 'is_searching'),
        migrations.AddConstraint(
            'advisersearchfollowup',
            models.CheckConstraint(
                condition=(
                    models.Q(job_offer__isnull=False, candidate_profile__isnull=True)
                    | models.Q(job_offer__isnull=True, candidate_profile__isnull=False)
                ),
                name='matching_advisersearchfollowup_single_target',
            ),
        ),
        migrations.RunPython(normalize_relations, migrations.RunPython.noop),
    ]
