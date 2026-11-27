"""Keep the match as the single link; reconstruct the derived link on rollback."""

from django.db import migrations


def check_relation(apps, schema_editor):
    alias = schema_editor.connection.alias
    for row in (
        apps.get_model('matching', 'MatchFollowup')
        .objects.using(alias)
        .select_related('review')
        .iterator()
    ):
        if row.review_id and row.review.match_id != row.match_id:
            raise RuntimeError(
                'Resolve the mismatched follow-up review before migration.'
            )


def restore_relation(apps, schema_editor):
    alias = schema_editor.connection.alias
    Followup = apps.get_model('matching', 'MatchFollowup')
    Review = apps.get_model('matching', 'CandidateOfferReview')
    for row in Followup.objects.using(alias).all().iterator():
        review = (
            Review.objects.using(alias)
            .filter(match_id=row.match_id)
            .values_list('pk', flat=True)
            .first()
        )
        Followup.objects.using(alias).filter(pk=row.pk).update(review_id=review)
    table = Followup._meta.db_table
    quote = schema_editor.quote_name
    with schema_editor.connection.cursor() as cursor:
        constraints = schema_editor.connection.introspection.get_constraints(
            cursor, table
        )
    for name, detail in constraints.items():
        if detail['foreign_key'] and detail['columns'] == ['review_id']:
            target = table + '_review_id_fk'
            if name != target:
                schema_editor.execute(
                    f'ALTER TABLE {quote(table)} RENAME CONSTRAINT {quote(name)} TO {quote(target)}'
                )


class Migration(migrations.Migration):
    dependencies = [('matching', '0032_rename_match_followup')]
    operations = [
        migrations.RunPython(check_relation, restore_relation),
        migrations.RemoveField('matchfollowup', 'review'),
    ]
