from ._sync_catalog import SyncCatalogCommand


class Command(SyncCatalogCommand):
    help = 'Prepare official ESCO/ROME correspondences and rebuild derived joins.'
    kind = 'mapping'
