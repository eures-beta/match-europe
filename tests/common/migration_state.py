"""Stage coordinated schema renames before testing earlier migration history."""


def historical_targets(targets):
    """Keep database and historical app state on the same pre-harmonization graph."""
    result = dict(
        [
            ('users', '0009_move_invitation_to_own_app'),
            ('invitations', '0002_complete_move'),
            ('employers', '0007_remove_retired_employer_models'),
            ('candidates', '0008_rename_candidate_push_subscription'),
            ('skills', '0002_move_content_type'),
        ]
    )
    result.update(targets)
    return list(result.items())


def prepare_historical(connection):
    # Unapply the coordinated rename first. A single backward plan crossing
    # unrelated app histories can expose a later app state to older RunPython.
    from django.db.migrations.executor import MigrationExecutor

    executor = MigrationExecutor(connection)
    if (
        'employers',
        '0010_remove_joboffer_email_and_more',
    ) in executor.loader.applied_migrations:
        # Restore removed offer columns before older cross-app RunPython code
        # introspects their sequences. The later candidates/matching move changes
        # Django's combined rollback order; stage this independent branch first.
        executor.migrate([('employers', '0008_harmonize_model_names')])
        executor = MigrationExecutor(connection)
    if ('matching', '0010_harmonize_model_names') in executor.loader.applied_migrations:
        executor.migrate(
            historical_targets([('matching', '0008_sharedconversation_sharedmessage')])
        )
