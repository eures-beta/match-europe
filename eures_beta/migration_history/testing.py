"""Historical schema helpers used only by isolated migration tests."""

from django.db import connection
from django.db.migrations.executor import MigrationExecutor as DjangoMigrationExecutor
from django.db.migrations.loader import MigrationLoader


class HistoricalMigrationLoader(MigrationLoader):
    """Exercise original migrations even when the normal loader uses the squash."""

    def load_disk(self):
        super().load_disk()
        self.disk_migrations = {
            key: migration
            for key, migration in self.disk_migrations.items()
            if not migration.replaces
        }

    def build_graph(self):
        super().build_graph()
        # A test database created with the squash also records its name. It is
        # intentionally absent from this original-history-only test graph.
        self.applied_migrations = {
            key: migration
            for key, migration in self.applied_migrations.items()
            if key in self.disk_migrations
        }


class HistoricalMigrationExecutor(DjangoMigrationExecutor):
    def __init__(self, connection, progress_callback=None):
        super().__init__(connection, progress_callback)
        self.loader = HistoricalMigrationLoader(connection)


def pre_retirement_targets():
    executor = HistoricalMigrationExecutor(connection)
    retired = {
        'accounts',
        'candidates',
        'documents',
        'offers',
        'matching',
        'conversations',
        'notifications',
    }
    targets = [
        node for node in executor.loader.graph.leaf_nodes() if node[0] not in retired
    ]
    targets.extend((label, '0001_initial') for label in retired)
    # Conversations had a schema-alignment migration before retirement.
    targets.remove(('conversations', '0001_initial'))
    targets.append(('conversations', '0002_alter_conversation_match'))
    return targets


def restore_current_schema():
    # TransactionTestCase only: remove the test's historical fixtures before the
    # real production guard, which deliberately refuses non-scenario data.
    executor = HistoricalMigrationExecutor(connection)
    executor.migrate(pre_retirement_targets())
    state = executor.loader.project_state(pre_retirement_targets()).apps
    labels = {
        'accounts',
        'candidates',
        'documents',
        'offers',
        'matching',
        'conversations',
        'notifications',
    }
    tables = [
        connection.ops.quote_name(model._meta.db_table)
        for model in state.get_models()
        if model._meta.app_label in labels
    ]
    with connection.cursor() as cursor:
        cursor.execute('TRUNCATE ' + ', '.join(tables) + ' CASCADE')
    state.get_model('auth', 'User').objects.filter(
        username__in=[
            f'{role}@example.invalid'
            for role in ('adviser', 'employer', 'candidate', 'admin')
        ]
    ).delete()
    executor = HistoricalMigrationExecutor(connection)
    executor.migrate(executor.loader.graph.leaf_nodes())
