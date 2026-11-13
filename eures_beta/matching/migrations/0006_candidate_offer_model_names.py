"""Rename business models without moving tables, rows or granted metadata."""

import django.db.models.deletion
from django.db import migrations, models

RENAMES = (
    ('matchpair', 'candidateoffermatch', 'match pair', 'candidate offer match'),
    (
        'confirmationrequest',
        'candidateofferreview',
        'confirmation request',
        'candidate offer review',
    ),
    (
        'confirmationanswer',
        'candidateofferreviewanswer',
        'confirmation answer',
        'candidate offer review answer',
    ),
    (
        'transmissionagreement',
        'candidateprofilesharing',
        'transmission agreement',
        'candidate profile sharing',
    ),
)


def rename_metadata(apps, schema_editor, reverse=False):
    alias = schema_editor.connection.alias
    ContentType = apps.get_model('contenttypes', 'ContentType')
    Permission = apps.get_model('auth', 'Permission')
    for old, new, old_label, new_label in RENAMES:
        if reverse:
            old, new, old_label, new_label = new, old, new_label, old_label
        types = ContentType.objects.using(alias).filter(
            app_label='matching', model__in=(old, new)
        )
        if types.count() > 1:
            raise RuntimeError(
                'Conflicting matching content types; inspect before migrating.'
            )
        content_type = types.first()
        if content_type is None:
            # On a fresh installation post_migrate creates the final metadata.
            continue
        for action in ('add', 'change', 'delete', 'view'):
            old_code, new_code = f'{action}_{old}', f'{action}_{new}'
            permissions = Permission.objects.using(alias).filter(
                content_type=content_type, codename__in=(old_code, new_code)
            )
            if permissions.count() > 1:
                raise RuntimeError(
                    'Conflicting matching permissions; inspect before migrating.'
                )
            permission = permissions.first()
            if permission is not None:
                permission.codename = new_code
                permission.name = f'Can {action} {new_label}'
                permission.save(using=alias, update_fields=['codename', 'name'])
        content_type.model = new
        content_type.save(using=alias, update_fields=['model'])


def forwards(apps, schema_editor):
    rename_metadata(apps, schema_editor)


def backwards(apps, schema_editor):
    rename_metadata(apps, schema_editor, reverse=True)


class Migration(migrations.Migration):
    dependencies = [
        ('matching', '0005_offer_confirmations'),
        ('contenttypes', '0002_remove_content_type_name'),
        ('auth', '0012_alter_user_first_name_max_length'),
    ]
    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.RenameModel('MatchPair', 'CandidateOfferMatch'),
                migrations.AlterModelTable('candidateoffermatch', 'matching_matchpair'),
                migrations.RenameModel('ConfirmationRequest', 'CandidateOfferReview'),
                migrations.AlterModelTable(
                    'candidateofferreview', 'matching_confirmationrequest'
                ),
                migrations.RenameModel(
                    'ConfirmationAnswer', 'CandidateOfferReviewAnswer'
                ),
                migrations.AlterModelTable(
                    'candidateofferreviewanswer', 'matching_confirmationanswer'
                ),
                migrations.RenameModel(
                    'TransmissionAgreement', 'CandidateProfileSharing'
                ),
                migrations.AlterModelTable(
                    'candidateprofilesharing', 'matching_transmissionagreement'
                ),
                migrations.AlterField(
                    model_name='candidateofferreview',
                    name='pair',
                    field=models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='candidate_offer_review',
                        to='matching.candidateoffermatch',
                    ),
                ),
            ],
        ),
        migrations.RunPython(forwards, backwards),
    ]
