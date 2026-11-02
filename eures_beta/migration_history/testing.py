"""Historical schema helpers used only by isolated migration tests."""

from django.db import connection
from django.db.migrations.executor import MigrationExecutor


def pre_retirement_targets():
    executor = MigrationExecutor(connection)
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
    executor = MigrationExecutor(connection)
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
    executor = MigrationExecutor(connection)
    executor.migrate(executor.loader.graph.leaf_nodes())
