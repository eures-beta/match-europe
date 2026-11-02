"""Preserve employer ownership while replacing the duplicate identity model."""

from django.contrib.auth.hashers import make_password
from django.db import migrations, models
from django.db.models.deletion import PROTECT

RELATIONS = [
    ('EmployerMembership', 'person'),
    ('EmployerImport', 'created_by'),
    ('EmployerSearchOperation', 'requested_by'),
    ('EmployerSearchEvent', 'actor'),
]


def transfer(apps, schema_editor):
    alias = schema_editor.connection.alias
    User = apps.get_model('users', 'User')
    Identity = apps.get_model('employers', 'EmployerIdentity')
    schema_editor.execute(
        'LOCK TABLE journeys_employeridentity IN ACCESS EXCLUSIVE MODE'
    )
    seen = set()
    for person in Identity.objects.using(alias).order_by('pk'):
        email = person.email.strip().lower()
        if not email or email in seen:
            raise RuntimeError('Conflicting identity emails; inspect before migrating.')
        seen.add(email)
        existing = User.objects.using(alias).filter(pk=person.pk).first()
        if existing and (existing.email != email or existing.kind != 'employer'):
            raise RuntimeError(
                'Conflicting user identifiers; inspect before migrating.'
            )
        if (
            User.objects.using(alias)
            .filter(email__iexact=email)
            .exclude(pk=person.pk)
            .exists()
        ):
            raise RuntimeError('Conflicting identity emails; inspect before migrating.')
        if not existing:
            User.objects.using(alias).create(
                pk=person.pk,
                email=email,
                kind='employer',
                date_joined=person.created,
                password=make_password(None),
            )
    from django.core.management.color import no_style

    for sql in schema_editor.connection.ops.sequence_reset_sql(no_style(), [User]):
        schema_editor.execute(sql)


def reverse_transfer(apps, schema_editor):
    alias = schema_editor.connection.alias
    User = apps.get_model('users', 'User')
    Identity = apps.get_model('employers', 'EmployerIdentity')
    for user in User.objects.using(alias).filter(kind='employer'):
        Identity.objects.using(alias).create(pk=user.pk, email=user.email)
        Identity.objects.using(alias).filter(pk=user.pk).update(
            created=user.date_joined
        )


class Migration(migrations.Migration):
    dependencies = [
        ('users', '0002_kind_immutable'),
        ('employers', '0001_initial'),
        ('admin', '0003_logentry_add_action_flag_choices'),
    ]
    operations = (
        [migrations.RunPython(transfer, migrations.RunPython.noop)]
        + [
            migrations.AlterField(
                model_name=model.lower(),
                name=field,
                field=models.ForeignKey(
                    to='users.User',
                    on_delete=PROTECT,
                    null=(field == 'created_by'),
                    blank=(field == 'created_by'),
                    **(
                        {'related_name': 'memberships'}
                        if field == 'person'
                        else (
                            {'related_name': 'created_imports'}
                            if field == 'created_by'
                            else {}
                        )
                    ),
                ),
            )
            for model, field in RELATIONS
        ]
        + [
            migrations.RunPython(migrations.RunPython.noop, reverse_transfer),
            migrations.DeleteModel(name='EmployerIdentity'),
        ]
    )
