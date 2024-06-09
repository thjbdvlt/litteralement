from psycopg.sql import SQL, Identifier
from typing import Any, NamedTuple
from litteralement.lookups.core import Lookup
from litteralement.lookups.core import TryLookup
from litteralement.lookups.core import ComposedKeyLookup
import litteralement.statements


def get_binary_lookup(
    conn,
    tablename,
    colname="nom",
    colid="id",
    lookup_type=Lookup,
):
    """Récupère une table lookup binaire (typiquement: id/nom).

    Args:
        conn (Connection)
        tablename (str)
        colname (str):  la colonne qui fait office de nom.
        colid (str):  la colonne qui fait office d'id.
        lookup_type (Lookup, TryLookup)

    Returns (Lookup, TryLookup)
    """

    query = SQL("select {}, {} from {}").format(
        Identifier(colid), Identifier(colname), Identifier(tablename)
    )
    cur = conn.cursor()
    cur.execute(query)
    d = {i[1]: i[0] for i in cur.fetchall()}
    lookup = lookup_type(keyname=colname, d=d)
    return lookup


def get_multicolumn_lookup(
    conn,
    tablename,
    columns,
    lookup_type=Lookup,
    keyname="COMPOSED_KEY",
    **kwargs,
):
    """Récupère un Lookup COMPOSED_KEY (plusieurs colonnes).

    Args:
        conn (Connection)
        tablename (str)
        columns (list[str])
        lookup_type (Lookup)

    Returns (Lookup)
    """

    query = litteralement.statements.make_multi_column_select(
        tablename=tablename, columns=columns
    )
    cur = conn.cursor()
    cur.execute(query)
    d = {i[1:]: i[0] for i in cur.fetchall()}
    lookup = lookup_type(keyname="COMPOSED_KEY", d=d, **kwargs)
    return lookup


class DatabaseLookup(Lookup):
    """Un Lookup pour les tables ."""

    def __init__(
        self, conn, tablename, colname="nom", colid="id", **kwargs
    ):
        """Instancie un DatabaseLookup.

        Args:
            conn (Connection)
            tablname (str)
            colname (str)
            **kwargs -> passés à Lookup.
        """

        self.conn = conn
        self.tablename = tablename
        self.colname = colname
        self.keyname = colname
        self.colid = colid
        d = self.fetch()
        super().__init__(d=d, keyname=colname, **kwargs)

    def fetch(self):
        """Récupère les données déjà présentes dans la table.

        Returns (Lookup)
        """

        return get_binary_lookup(
            self.conn,
            tablename=self.tablename,
            colid=self.colid,
            colname=self.colname,
            lookup_type=Lookup,
        )

    def copy_to(self):
        """Insère dans la base de données les Items nouveaux.

        Note:
            COPY TO, car plus rapide que INSERT.
        """

        existing = set(self.fetch().as_tuples())
        cur = self.conn.cursor()
        with cur.copy(self._copy_stmt) as copy:
            for i in set(self.as_tuples()) - existing:
                copy.write_row(i)

    @property
    def _copy_stmt(self):
        """Construit un statement COPY."""

        stmt = SQL("copy {} (id, {}) from stdin").format(
            Identifier(self.tablename), Identifier(self.colname)
        )
        return stmt


class TryDatabaseLookup(DatabaseLookup, TryLookup):
    """DatabaseLookup pour les Tables avec peu de valeurs."""

    def __init__(self, *args, **kwargs):
        """Instancie un TryDatabaseLookup."""
        super().__init__(*args, **kwargs)

    def fetch(self):
        """Récupère les données déjà présentes dans la table.

        Returns (Lookup)
        """

        return get_binary_lookup(
            self.conn,
            tablename=self.tablename,
            colid=self.colid,
            colname=self.colname,
            lookup_type=TryLookup,
        )


class MultiColumnLookup(ComposedKeyLookup):
    copy_to = DatabaseLookup.copy_to

    def __init__(self, conn, tablename, columns, colid="id", **kwargs):
        """Instancie un MultiColumnLookup.

        Args:
            conn (Connection)
            tablename (str)
            columns (list[str])
            colid (str)
            **kwargs
        """

        _name = "COMPOSED_KEY"
        self.conn = conn
        self.tablename = tablename
        self.colname = _name
        self.keyname = _name
        self.colid = colid

        self.columns = columns
        fields = [(i, Any) for i in columns]
        self.Key = NamedTuple("Key", fields)
        self.Row = NamedTuple("Row", [("id", int)] + fields)
        d = self.fetch()
        super().__init__(
            fields=columns, keyname=_name, d=d, keyid=colid
        )

    def fetch(self):
        """Récupère les données déjà présentes dans la table.

        Returns (Lookup)
        """

        return get_multicolumn_lookup(
            self.conn,
            tablename=self.tablename,
            columns=[self.colid] + self.columns,
        )

    @property
    def _copy_stmt(self):
        stmt = litteralement.statements.copy_to_multicolumns(
            self.tablename, [self.colid] + self.columns
        )
        return stmt
