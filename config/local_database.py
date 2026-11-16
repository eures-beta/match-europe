"""Explicit local PostgreSQL preparation; never discovers or creates a role."""

import argparse
from dataclasses import dataclass
import os
import sys

import psycopg
from psycopg import sql


class DatabasePreparationError(Exception):
    pass


@dataclass(frozen=True)
class LocalDatabase:
    host: str
    port: int
    user: str
    name: str

    @classmethod
    def from_environment(cls):
        names = ('PGHOST', 'PGPORT', 'PGUSER', 'PGDATABASE')
        missing = [name for name in names if not os.environ.get(name, '').strip()]
        if missing:
            raise DatabasePreparationError(
                'Renseigner dans .env : '
                + ', '.join(missing)
                + '. Voir docs/DEVELOPPEMENT.md ; aucun serveur ou rôle ne sera choisi automatiquement.'
            )
        host, port, user, name = (os.environ[key].strip() for key in names)
        if os.environ.get('DJANGO_ENVIRONMENT', 'local') not in ('local', 'preview'):
            raise DatabasePreparationError(
                'Ces commandes préparent uniquement une base locale de développement ou de recette.'
            )
        if host not in ('localhost', '127.0.0.1', '::1') and not host.startswith('/'):
            raise DatabasePreparationError(
                'PGHOST doit désigner explicitement une instance locale (loopback ou répertoire de socket).'
            )
        try:
            port = int(port)
            if not 1 <= port <= 65535:
                raise ValueError
        except ValueError:
            raise DatabasePreparationError(
                'PGPORT doit être un port compris entre 1 et 65535.'
            ) from None
        if name in ('postgres', 'template0', 'template1') or len(name.encode()) > 58:
            raise DatabasePreparationError(
                'Choisir un PGDATABASE propre au worktree, distinct des bases système et limité à 58 octets (préfixe test_ inclus ensuite).'
            )
        return cls(host, port, user, name)

    def connect(self, database='postgres'):
        # Explicit parameters prevent accidental fallback to another host/user/db.
        # libpq still reads PGPASSWORD/PGPASSFILE and PGSSLMODE normally.
        return psycopg.connect(
            host=self.host,
            port=self.port,
            user=self.user,
            dbname=database,
            connect_timeout=5,
            application_name='match-europe-local-database',
            autocommit=True,
        )

    def inspect(self, connection):
        connection.execute('SET default_transaction_read_only = on')
        role = connection.execute(
            'SELECT current_user, rolcreatedb OR rolsuper FROM pg_catalog.pg_roles WHERE rolname = current_user'
        ).fetchone()
        if not role or role[0] != self.user or not role[1]:
            raise DatabasePreparationError(
                'Le rôle PGUSER configuré doit pouvoir créer sa base de test (CREATEDB). '
                'Faire préparer ce rôle par l’opérateur PostgreSQL ; aucun rôle ni droit ne sera créé automatiquement.'
            )
        database = connection.execute(
            'SELECT pg_get_userbyid(datdba), has_database_privilege(current_user, oid, \'CONNECT\') '
            'FROM pg_catalog.pg_database WHERE datname = %s',
            (self.name,),
        ).fetchone()
        if database and (database[0] != self.user or not database[1]):
            raise DatabasePreparationError(
                'PGDATABASE existe mais n’appartient pas au rôle configuré ou ne lui est pas accessible. '
                'Choisir une base propre à ce worktree ; aucune base existante ne sera modifiée.'
            )
        return database is not None

    def run(self, *, create=False):
        try:
            with self.connect() as connection:
                exists = self.inspect(connection)
                if not exists and not create:
                    raise DatabasePreparationError(
                        'PGDATABASE est absente. Exécuter make db-create, puis make db-check.'
                    )
                if not exists:
                    connection.execute('SET default_transaction_read_only = off')
                    try:
                        connection.execute(
                            sql.SQL('CREATE DATABASE {}').format(
                                sql.Identifier(self.name)
                            )
                        )
                    except psycopg.errors.DuplicateDatabase:
                        # A concurrent preparation may have won; still verify ownership.
                        pass
                    if not self.inspect(connection):
                        raise DatabasePreparationError(
                            'La base n’a pas pu être créée. Vérifier la configuration locale.'
                        )
            with self.connect(self.name) as connection:
                connection.execute('SET default_transaction_read_only = on')
                connection.execute('SELECT 1')
        except psycopg.Error:
            # Never print a DSN, password, server exception or connection string.
            raise DatabasePreparationError(
                'Connexion ou préparation PostgreSQL impossible avec PGHOST/PGPORT/PGUSER configurés. '
                'Vérifier que cette instance est démarrée, que ce rôle existe et que son authentification fonctionne. '
                'Aucun autre serveur ou utilisateur n’a été essayé.'
            ) from None
        print(
            'PostgreSQL local prêt : rôle, CREATEDB, accès et propriété de la base vérifiés.'
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('check', 'create'))
    arguments = parser.parse_args()
    try:
        LocalDatabase.from_environment().run(create=arguments.action == 'create')
    except DatabasePreparationError as error:
        print(f'Préparation PostgreSQL : {error}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
