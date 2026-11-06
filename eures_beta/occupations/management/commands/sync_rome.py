from ._sync_catalog import SyncCatalogCommand


class Command(SyncCatalogCommand):
    help = 'Prepare ROME fiches and OGR appellations together from the official XLSX.'
    kind = 'rome'
