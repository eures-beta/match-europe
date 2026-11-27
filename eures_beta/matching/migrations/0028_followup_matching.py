"""Attach existing plans to their matching without replacing any history."""

from django.db import migrations, models
import django.db.models.deletion


def attach(apps, schema_editor):
    Plan = apps.get_model('matching', 'IntroductionFollowup')
    plans = Plan.objects.using(schema_editor.connection.alias)
    for row in plans.select_related('review').all().iterator():
        plans.filter(pk=row.pk).update(match_id=row.review.match_id)


def check_rollback(apps, schema_editor):
    Plan = apps.get_model('matching', 'IntroductionFollowup')
    if (
        Plan.objects.using(schema_editor.connection.alias)
        .filter(review__isnull=True)
        .exists()
    ):
        raise RuntimeError(
            'Cannot roll back plans created before a candidate review; preserve these plans first.'
        )


class Migration(migrations.Migration):
    dependencies = [('matching', '0027_followup_database_names')]
    operations = [
        migrations.AddField(
            'introductionfollowup',
            'match',
            models.OneToOneField(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='followup',
                to='matching.candidateoffermatch',
            ),
        ),
        migrations.RunPython(attach, migrations.RunPython.noop),
        migrations.AlterField(
            'introductionfollowup',
            'match',
            models.OneToOneField(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='followup',
                to='matching.candidateoffermatch',
            ),
        ),
        migrations.AlterField(
            'introductionfollowup',
            'review',
            models.OneToOneField(
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='introduction_followup',
                to='matching.candidateofferreview',
            ),
        ),
        migrations.RunPython(migrations.RunPython.noop, check_rollback),
    ]
