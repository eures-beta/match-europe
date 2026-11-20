"""Replace textual decision authors and remove duplicated candidate identity."""

import re

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def convert_authors(apps, schema_editor):
    db = schema_editor.connection.alias
    Decision = apps.get_model('matching', 'MatchDecision')
    Review = apps.get_model('matching', 'CandidateOfferReview')
    User = apps.get_model('users', 'User')
    # Prevent concurrent writes between the checks and the removal of old columns.
    schema_editor.execute(
        'LOCK TABLE matching_matchdecision, matching_candidateofferreview, '
        'matching_candidateofferreviewanswer, matching_candidateprofilesharing, '
        'matching_candidateoffermatch IN SHARE ROW EXCLUSIVE MODE'
    )
    if Review.objects.using(db).exclude(requested_by_adviser__kind='adviser').exists():
        raise RuntimeError('Review requester must be an adviser; migration aborted.')
    for name in ('CandidateOfferReviewAnswer', 'CandidateProfileSharing'):
        Model = apps.get_model('matching', name)
        if (
            Model.objects.using(db)
            .exclude(actor_id=models.F('review__match__candidate__user_id'))
            .exists()
        ):
            raise RuntimeError(
                f'{name}: author differs from candidate; migration aborted.'
            )
    for decision in Decision.objects.using(db).all().iterator():
        if decision.actor == 'local_operator':
            continue
        match = re.fullmatch(r'adviser:([1-9][0-9]*)', decision.actor)
        if (
            not match
            or not User.objects.using(db)
            .filter(pk=int(match[1]), kind='adviser')
            .exists()
        ):
            raise RuntimeError(
                f'Decision {decision.pk}: invalid adviser author; migration aborted.'
            )
        Decision.objects.using(db).filter(pk=decision.pk).update(
            by_adviser_id=int(match[1])
        )


def restore_authors(apps, schema_editor):
    db = schema_editor.connection.alias
    Decision = apps.get_model('matching', 'MatchDecision')
    for decision in Decision.objects.using(db).all().iterator():
        actor = (
            f'adviser:{decision.by_adviser_id}'
            if decision.by_adviser_id
            else 'local_operator'
        )
        Decision.objects.using(db).filter(pk=decision.pk).update(actor=actor)
    for name in ('CandidateOfferReviewAnswer', 'CandidateProfileSharing'):
        Model = apps.get_model('matching', name)
        for row in (
            Model.objects.using(db)
            .select_related('review__match__candidate')
            .iterator()
        ):
            Model.objects.using(db).filter(pk=row.pk).update(
                actor_id=row.review.match.candidate.user_id
            )


def rename_requester_objects(apps, schema_editor, *, reverse=False):
    table = apps.get_model('matching', 'CandidateOfferReview')._meta.db_table
    quote = schema_editor.quote_name
    column = 'requested_by_id' if reverse else 'requested_by_adviser_id'
    with schema_editor.connection.cursor() as cursor:
        objects = schema_editor.connection.introspection.get_constraints(cursor, table)
    for name, details in objects.items():
        if details['columns'] != ['requested_by_adviser_id']:
            continue
        if details['foreign_key']:
            new, kind = f'{table}_{column}_fk', 'CONSTRAINT'
        elif details['index']:
            new, kind = f'{table}_{column}_idx', 'INDEX'
        else:
            continue
        if name == new:
            continue
        if kind == 'INDEX':
            schema_editor.execute(f'ALTER INDEX {quote(name)} RENAME TO {quote(new)}')
        else:
            schema_editor.execute(
                f'ALTER TABLE {quote(table)} RENAME CONSTRAINT {quote(name)} TO {quote(new)}'
            )
    # PostgreSQL 18 names NOT NULL constraints; Django omits them above.
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            'SELECT c.conname FROM pg_constraint c '
            'JOIN pg_attribute a ON a.attrelid=c.conrelid AND a.attnum=c.conkey[1] '
            "WHERE c.conrelid=%s::regclass AND c.contype='n' "
            "AND a.attname='requested_by_adviser_id'",
            [table],
        )
        names = cursor.fetchall()
    for (name,) in names:
        new = f'{table}_{column}_not_null'
        if name != new:
            schema_editor.execute(
                f'ALTER TABLE {quote(table)} RENAME CONSTRAINT {quote(name)} TO {quote(new)}'
            )


def restore_requester_objects(apps, schema_editor):
    rename_requester_objects(apps, schema_editor, reverse=True)


GUARDS = """
CREATE FUNCTION matching_matchdecision_check_adviser()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.by_adviser_id IS NULL THEN
        IF TG_OP = 'INSERT' THEN
            RAISE EXCEPTION 'New decision requires an adviser' USING ERRCODE = '23514';
        END IF;
        IF OLD.by_adviser_id IS NOT NULL THEN
            RAISE EXCEPTION 'Decision adviser cannot be removed' USING ERRCODE = '23514';
        END IF;
    ELSIF NOT EXISTS (
        SELECT 1 FROM users_user WHERE id = NEW.by_adviser_id AND kind = 'adviser'
    ) THEN
        RAISE EXCEPTION 'Decision author must be an adviser' USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER matching_matchdecision_adviser_guard
BEFORE INSERT OR UPDATE ON matching_matchdecision
FOR EACH ROW EXECUTE FUNCTION matching_matchdecision_check_adviser();
CREATE FUNCTION matching_candidateofferreview_check_adviser()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM users_user WHERE id = NEW.requested_by_adviser_id AND kind = 'adviser'
    ) THEN
        RAISE EXCEPTION 'Review requester must be an adviser' USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER matching_candidateofferreview_adviser_guard
BEFORE INSERT OR UPDATE ON matching_candidateofferreview
FOR EACH ROW EXECUTE FUNCTION matching_candidateofferreview_check_adviser();
"""

UNGUARD = """
DROP TRIGGER matching_candidateofferreview_adviser_guard ON matching_candidateofferreview;
DROP FUNCTION matching_candidateofferreview_check_adviser();
DROP TRIGGER matching_matchdecision_adviser_guard ON matching_matchdecision;
DROP FUNCTION matching_matchdecision_check_adviser();
"""


class Migration(migrations.Migration):
    dependencies = [
        ('matching', '0021_move_profile_review_suggestion'),
        ('candidates', '0011_immutable_candidate_account'),
    ]
    operations = [
        migrations.AddField(
            model_name='matchdecision',
            name='by_adviser',
            field=models.ForeignKey(
                to=settings.AUTH_USER_MODEL,
                on_delete=django.db.models.deletion.PROTECT,
                null=True,
                blank=True,
                limit_choices_to={'kind': 'adviser'},
            ),
        ),
        migrations.RenameField(
            'candidateofferreview', 'requested_by', 'requested_by_adviser'
        ),
        migrations.AlterField(
            model_name='candidateofferreview',
            name='requested_by_adviser',
            field=models.ForeignKey(
                to=settings.AUTH_USER_MODEL,
                on_delete=django.db.models.deletion.PROTECT,
                limit_choices_to={'kind': 'adviser'},
            ),
        ),
        # Nullable temporarily so rollback can restore populated rows before NOT NULL.
        migrations.AlterField(
            model_name='candidateofferreviewanswer',
            name='actor',
            field=models.ForeignKey(
                to=settings.AUTH_USER_MODEL,
                on_delete=django.db.models.deletion.PROTECT,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name='candidateprofilesharing',
            name='actor',
            field=models.ForeignKey(
                to=settings.AUTH_USER_MODEL,
                on_delete=django.db.models.deletion.PROTECT,
                null=True,
            ),
        ),
        migrations.RunPython(convert_authors, restore_authors),
        migrations.RemoveField('matchdecision', 'actor'),
        migrations.RemoveField('candidateofferreviewanswer', 'actor'),
        migrations.RemoveField('candidateprofilesharing', 'actor'),
        migrations.RunPython(rename_requester_objects, restore_requester_objects),
        migrations.RunSQL(GUARDS, UNGUARD),
    ]
