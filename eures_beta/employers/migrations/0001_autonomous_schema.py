"""Autonomous current schema, after the separately deployed transition.

Existing databases must already have recorded this migration before history
is removed. Fresh databases create only the current business tables.
"""

import uuid
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def require_fresh_schema(apps, schema_editor):
    """Existing installations must have recorded this baseline before cleanup."""
    current_tables = {
        'journeys_employercompany',
        'journeys_employeridentity',
        'journeys_employermembership',
        'journeys_employerimport',
        'journeys_employeremaillink',
        'journeys_employersearchoperation',
        'journeys_employersearchevent',
    }
    if current_tables.intersection(
        schema_editor.connection.introspection.table_names()
    ):
        raise RuntimeError(
            'Existing employer tables without the autonomous migration marker. '
            'Deploy the transition release and run migrate before removing migration history. '
            'Do not use --fake or reset the database.'
        )


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('contenttypes', '0002_remove_content_type_name'),
    ]
    operations = [
        migrations.RunPython(require_fresh_schema, migrations.RunPython.noop),
        migrations.CreateModel(
            name='EmployerCompany',
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
                ('name', models.CharField(max_length=100)),
                ('created', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'db_table': 'journeys_employercompany',
            },
        ),
        migrations.CreateModel(
            name='EmployerIdentity',
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
                ('email', models.EmailField(max_length=254, unique=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'db_table': 'journeys_employeridentity',
            },
        ),
        migrations.CreateModel(
            name='EmployerImport',
            fields=[
                (
                    'id',
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    'search_started_at',
                    models.DateTimeField(blank=True, editable=False, null=True),
                ),
                ('session_key', models.CharField(db_index=True, max_length=64)),
                ('email', models.EmailField(max_length=254)),
                ('contact', models.JSONField(default=dict)),
                ('preparation_agreed_at', models.DateTimeField()),
                ('source_kind', models.CharField(max_length=10)),
                ('source_url', models.URLField(blank=True, max_length=2048)),
                ('data', models.JSONField(default=dict)),
                ('validated_at', models.DateTimeField(null=True)),
                ('initial_sent_at', models.DateTimeField(null=True)),
                ('synced_at', models.DateTimeField(null=True)),
                ('sandbox_response', models.JSONField(default=dict)),
                ('revision', models.PositiveIntegerField(default=1)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
                (
                    'adviser',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name='advised_imports',
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    'company',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name='imports',
                        to='employers.employercompany',
                    ),
                ),
                (
                    'created_by',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name='created_imports',
                        to='employers.employeridentity',
                    ),
                ),
                (
                    'duplicated_from',
                    models.ForeignKey(
                        blank=True,
                        editable=False,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name='duplicates',
                        to='employers.employerimport',
                    ),
                ),
            ],
            options={
                'db_table': 'journeys_employerimport',
            },
        ),
        migrations.CreateModel(
            name='EmployerEmailLink',
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
                ('email', models.EmailField(max_length=254)),
                ('digest', models.CharField(max_length=64, unique=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('expires', models.DateTimeField()),
                ('used', models.BooleanField(default=False)),
                (
                    'pending_import',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        to='employers.employerimport',
                    ),
                ),
            ],
            options={
                'db_table': 'journeys_employeremaillink',
            },
        ),
        migrations.CreateModel(
            name='EmployerSearchOperation',
            fields=[
                (
                    'id',
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ('revision', models.PositiveIntegerField()),
                (
                    'state',
                    models.CharField(
                        choices=[
                            ('pending', 'Pending'),
                            ('uncertain', 'Uncertain'),
                            ('failed', 'Failed'),
                            ('started', 'Started'),
                        ],
                        max_length=12,
                    ),
                ),
                ('scenario', models.CharField(editable=False, max_length=24)),
                ('created', models.DateTimeField(auto_now_add=True)),
                (
                    'resolved_at',
                    models.DateTimeField(editable=False, null=True),
                ),
                (
                    'offer',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name='search_operations',
                        to='employers.employerimport',
                    ),
                ),
                (
                    'requested_by',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        to='employers.employeridentity',
                    ),
                ),
            ],
            options={
                'db_table': 'journeys_employersearchoperation',
            },
        ),
        migrations.CreateModel(
            name='EmployerSearchEvent',
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
                ('state', models.CharField(max_length=12)),
                ('created', models.DateTimeField(auto_now_add=True)),
                (
                    'actor',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        to='employers.employeridentity',
                    ),
                ),
                (
                    'operation',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name='events',
                        to='employers.employersearchoperation',
                    ),
                ),
            ],
            options={
                'db_table': 'journeys_employersearchevent',
            },
        ),
        migrations.CreateModel(
            name='EmployerMembership',
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
                ('active', models.BooleanField(default=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                (
                    'company',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name='memberships',
                        to='employers.employercompany',
                    ),
                ),
                (
                    'person',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name='memberships',
                        to='employers.employeridentity',
                    ),
                ),
            ],
            options={
                'db_table': 'journeys_employermembership',
                'constraints': [
                    models.UniqueConstraint(
                        fields=('company', 'person'),
                        name='unique_employer_membership',
                    )
                ],
            },
        ),
        migrations.AddConstraint(
            model_name='employersearchoperation',
            constraint=models.UniqueConstraint(
                fields=('offer', 'revision'),
                name='unique_search_offer_revision',
            ),
        ),
    ]
