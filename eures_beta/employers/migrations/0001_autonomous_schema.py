"""Consolidated final schema; old migrations remain for partial upgrades.

The historical schema moved between app labels, so this replacement covers the
whole connected application history. Fresh installs create only current tables.
Do not remove the replaced files until all existing environments have migrated.
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
    replaces = [
        ('journeys', '0001_initial'),
        ('journeys', '0002_employerimport'),
        ('journeys', '0003_employerimport_initial_sent_at'),
        ('journeys', '0004_employer_contact_and_adviser'),
        ('journeys', '0005_employer_email_link'),
        ('journeys', '0006_employercompany_employeridentity_and_more'),
        ('journeys', '0007_employer_offer_workspace'),
        ('journeys', '0008_employer_search_simulation'),
        ('journeys', '0009_move_conversations'),
        ('journeys', '0010_delete_notification'),
        ('journeys', '0011_alter_candidate_document_alter_offer_document_and_more'),
        ('journeys', '0012_alter_match_candidate_delete_candidate'),
        ('journeys', '0013_remove_offer_adviser_remove_offer_document_and_more'),
        (
            'journeys',
            '0014_alter_match_offer_alter_answer_question_delete_offer_and_more',
        ),
        ('journeys', '0015_remove_event_actor_remove_profile_adviser_and_more'),
        ('journeys', '0016_remove_employerimport_company_and_more'),
        ('journeys', '0017_remove_answer_unique_answer_and_more'),
        ('journeys', '0018_delete_match'),
        ('accounts', '0001_initial'),
        ('accounts', '0002_remove_legacy_demo_accounts'),
        ('accounts', '0003_verify_retired_tables_empty'),
        ('accounts', '0004_remove_event_actor_remove_profile_adviser_and_more'),
        ('offers', '0001_initial'),
        ('offers', '0002_remove_question_offer_delete_offer_delete_question'),
        ('matching', '0001_initial'),
        ('matching', '0002_remove_answer_unique_answer_and_more'),
        ('conversations', '0001_initial'),
        ('conversations', '0002_alter_conversation_match'),
        (
            'conversations',
            '0003_remove_message_conversation_remove_message_sender_and_more',
        ),
        ('notifications', '0001_initial'),
        ('notifications', '0002_delete_notification'),
        ('documents', '0001_initial'),
        ('documents', '0002_delete_document'),
        ('candidates', '0001_initial'),
        ('candidates', '0002_delete_candidate'),
        ('employers', '0001_initial'),
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
