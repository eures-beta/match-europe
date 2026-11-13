from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class SkillsMoveTests(TransactionTestCase):
    def test_existing_suggestion_and_content_type_survive_transfer_and_reverse(self):
        executor = MigrationExecutor(connection)
        latest = executor.loader.graph.leaf_nodes()
        before = [
            ('occupations', '0001_initial'),
            ('contenttypes', '0002_remove_content_type_name'),
        ]
        try:
            executor.migrate(before)
            apps = executor.loader.project_state(before).apps
            Old = apps.get_model('occupations', 'OccupationSkillSuggestion')
            row = Old.objects.create(
                occupation_uri='fictional:job',
                source_version='fixture',
                method='fixture',
                skill_uris=['fictional:skill'],
                status='ready',
            )
            CT = apps.get_model('contenttypes', 'ContentType')
            CT.objects.filter(
                app_label='skills', model='occupationskillsuggestion'
            ).delete()
            ct, _ = CT.objects.get_or_create(
                app_label='occupations', model='occupationskillsuggestion'
            )
            ct_id = ct.pk
            executor = MigrationExecutor(connection)
            executor.migrate(latest)
            apps = executor.loader.project_state(latest).apps
            New = apps.get_model('skills', 'OccupationSkillSuggestion')
            self.assertEqual(New.objects.get(pk=row.pk).skill_uris, ['fictional:skill'])
            self.assertEqual(
                apps.get_model('contenttypes', 'ContentType')
                .objects.get(pk=ct_id)
                .app_label,
                'skills',
            )
            executor = MigrationExecutor(connection)
            executor.migrate(before)
            apps = executor.loader.project_state(before).apps
            self.assertEqual(
                apps.get_model('occupations', 'OccupationSkillSuggestion')
                .objects.get(pk=row.pk)
                .status,
                'ready',
            )
        finally:
            MigrationExecutor(connection).migrate(latest)
