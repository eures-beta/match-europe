"""Rename the review journal in place, including its PostgreSQL objects."""

from django.db import migrations, models
import django.db.models.deletion


def normalize(apps, schema_editor, *, backwards=False):
    old, new = 'candidateofferreviewaction', 'candidateofferreviewevent'
    if backwards:
        old, new = new, old
    table = apps.get_model('matching', new)._meta.db_table
    old_prefix, new_prefix = 'matching_' + old, 'matching_' + new
    quote = schema_editor.quote_name
    connection = schema_editor.connection
    with connection.cursor() as cursor:
        cursor.execute(
            'SELECT conname FROM pg_constraint WHERE conrelid=%s::regclass', [table]
        )
        constraints = [row[0] for row in cursor.fetchall()]
        for name in constraints:
            if name.startswith(old_prefix + '_'):
                target = new_prefix + name[len(old_prefix) :]
                schema_editor.execute(
                    f'ALTER TABLE {quote(table)} RENAME CONSTRAINT {quote(name)} TO {quote(target)}'
                )
        cursor.execute(
            'SELECT c.relname FROM pg_index i JOIN pg_class c ON c.oid=i.indexrelid '
            'WHERE i.indrelid=%s::regclass',
            [table],
        )
        for (name,) in cursor.fetchall():
            if name.startswith(old_prefix + '_'):
                target = new_prefix + name[len(old_prefix) :]
                schema_editor.execute(
                    f'ALTER INDEX {quote(name)} RENAME TO {quote(target)}'
                )
        cursor.execute(
            'SELECT pg_get_serial_sequence(%s, %s)::regclass::oid', [table, 'id']
        )
        sequence_oid = cursor.fetchone()[0]
        cursor.execute(
            'SELECT n.nspname, c.relname FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE c.oid=%s',
            [sequence_oid],
        )
        namespace, name = cursor.fetchone()
        if name.startswith(old_prefix + '_'):
            target = new_prefix + name[len(old_prefix) :]
            schema_editor.execute(
                f'ALTER SEQUENCE {quote(namespace)}.{quote(name)} RENAME TO {quote(target)}'
            )
    # Django renames the content type around RenameModel. Keep the permission
    # IDs and their existing group/user assignments instead of creating doubles.
    apps.get_model('contenttypes', 'ContentType').objects.using(
        connection.alias
    ).filter(app_label='matching', model=old).update(model=new)
    Permission = apps.get_model('auth', 'Permission')
    for verb in ('add', 'change', 'delete', 'view'):
        Permission.objects.using(connection.alias).filter(
            content_type__app_label='matching',
            content_type__model__in=[old, new],
            codename=f'{verb}_{old}',
        ).update(
            codename=f'{verb}_{new}',
            name=f'Can {verb} candidate offer review {"action" if backwards else "event"}',
        )


def forwards(apps, schema_editor):
    normalize(apps, schema_editor)


def backwards(apps, schema_editor):
    normalize(apps, schema_editor, backwards=True)


class Migration(migrations.Migration):
    dependencies = [('matching', '0019_review_database_names')]
    operations = [
        migrations.RunPython(migrations.RunPython.noop, backwards),
        migrations.RenameModel(
            'CandidateOfferReviewAction', 'CandidateOfferReviewEvent'
        ),
        migrations.AlterField(
            model_name='candidateofferreviewevent',
            name='review',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='events',
                to='matching.candidateofferreview',
            ),
        ),
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.RemoveConstraint(
                    'candidateofferreviewevent',
                    'matching_candidateofferreviewaction_version_unique',
                ),
                migrations.AddConstraint(
                    'candidateofferreviewevent',
                    models.UniqueConstraint(
                        fields=['review', 'version'],
                        name='matching_candidateofferreviewevent_version_unique',
                    ),
                ),
            ]
        ),
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]
