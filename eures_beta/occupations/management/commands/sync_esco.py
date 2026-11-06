from ._sync_catalog import SyncCatalogCommand


class Command(SyncCatalogCommand):
    help = (
        'Prepare the official ESCO occupation export in FR/EN/DE (no database writes).'
    )
    kind = 'esco'
