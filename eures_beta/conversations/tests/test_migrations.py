from django.contrib.auth import get_user_model
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class ConversationMigrationTests(TransactionTestCase):
    old_targets = [
        ('journeys', '0008_employer_search_simulation'),
        ('conversations', None),
    ]
    new_targets = [('conversations', '0001_initial')]

    def migrate(self, targets):
        executor = MigrationExecutor(connection)
        executor.migrate(targets)
        # Include the native migrations that remain applied during a partial rollback.
        loader = MigrationExecutor(connection).loader
        return loader.project_state(list(loader.applied_migrations)).apps

    def test_existing_messages_and_permission_assignments_survive_both_directions(self):
        try:
            old = self.migrate(self.old_targets)
            User = old.get_model('auth', 'User')
            user = User.objects.create(
                username='conversation-migration@example.invalid'
            )
            offer = old.get_model('journeys', 'Offer').objects.create(
                employer_id=user.pk, adviser_id=user.pk
            )
            candidate = old.get_model('journeys', 'Candidate').objects.create(
                user_id=user.pk
            )
            match = old.get_model('journeys', 'Match').objects.create(
                offer_id=offer.pk, candidate_id=candidate.pk
            )
            conversation = old.get_model('journeys', 'Conversation').objects.create(
                match_id=match.pk, opened_by_id=user.pk
            )
            message = old.get_model('journeys', 'Message').objects.create(
                conversation_id=conversation.pk,
                sender_id=user.pk,
                body='Fictional saved message',
            )
            content_type, _ = old.get_model(
                'contenttypes', 'ContentType'
            ).objects.get_or_create(app_label='journeys', model='conversation')
            permission, _ = old.get_model('auth', 'Permission').objects.get_or_create(
                content_type_id=content_type.pk,
                codename='view_conversation',
                defaults={'name': 'Can view conversation'},
            )
            user.user_permissions.add(permission)
            tables = set(connection.introspection.table_names())
            conversation_snapshot = list(
                old.get_model('journeys', 'Conversation')
                .objects.order_by('pk')
                .values()
            )
            message_snapshot = list(
                old.get_model('journeys', 'Message').objects.order_by('pk').values()
            )

            new = self.migrate(self.new_targets)
            saved = new.get_model('conversations', 'Message').objects.get(pk=message.pk)
            self.assertEqual(saved.body, message.body)
            self.assertEqual(saved.conversation_id, conversation.pk)
            self.assertEqual(saved.sender_id, user.pk)
            self.assertEqual(
                list(
                    new.get_model('conversations', 'Conversation')
                    .objects.order_by('pk')
                    .values()
                ),
                conversation_snapshot,
            )
            self.assertEqual(
                list(
                    new.get_model('conversations', 'Message')
                    .objects.order_by('pk')
                    .values()
                ),
                message_snapshot,
            )
            self.assertEqual(set(connection.introspection.table_names()), tables)
            self.assertEqual(
                new.get_model('contenttypes', 'ContentType')
                .objects.get(pk=content_type.pk)
                .app_label,
                'conversations',
            )
            self.assertTrue(
                get_user_model()
                .objects.get(pk=user.pk)
                .has_perm('conversations.view_conversation')
            )

            restored = self.migrate(self.old_targets)
            self.assertEqual(
                list(
                    restored.get_model('journeys', 'Conversation')
                    .objects.order_by('pk')
                    .values()
                ),
                conversation_snapshot,
            )
            self.assertEqual(
                list(
                    restored.get_model('journeys', 'Message')
                    .objects.order_by('pk')
                    .values()
                ),
                message_snapshot,
            )
            self.assertEqual(
                restored.get_model('journeys', 'Message')
                .objects.get(pk=message.pk)
                .body,
                message.body,
            )
            self.assertEqual(
                restored.get_model('contenttypes', 'ContentType')
                .objects.get(pk=content_type.pk)
                .app_label,
                'journeys',
            )
            self.assertTrue(
                restored.get_model('auth', 'User')
                .objects.get(pk=user.pk)
                .user_permissions.filter(pk=permission.pk)
                .exists()
            )
        finally:
            self.migrate(self.new_targets)
