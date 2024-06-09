from psycopg.sql import SQL, Identifier
from litteralement.lookups.core import Lookup
from litteralement.lookups.core import TryLookup
from litteralement.lookups.core import ComposedKeyLookup
import litteralement.statements


def get_binary_lookup(
    conn,
    table,
    colname="nom",
    colid="id",
    lookup_type=Lookup,
):
    """Récupère une table lookup binaire (typiquement: id/nom).

    Args:
        conn (Connection)
        table (str)
        colname (str):  la colonne qui fait office de nom.
        colid (str):  la colonne qui fait office d'id.
        lookup_type (Lookup, TryLookup)

    Returns (Lookup, TryLookup)
    """

    sql_table = litteralement.statements.qualify(table)
    query = SQL("select {}, {} from {}").format(
        Identifier(colid), Identifier(colname), sql_table
    )
    cur = conn.cursor()
    cur.execute(query)
    d = {i[1]: i[0] for i in cur.fetchall()}
    lookup = lookup_type(keyname=colname, d=d)
    return lookup


def get_multicolumn_lookup(
    conn,
    table,
    columns,
    colid,
    keyname="COMPOSED_KEY",
    **kwargs,
):
    """Récupère un Lookup COMPOSED_KEY (plusieurs colonnes).

    Args:
        conn (Connection)
        table (str)
        columns (list[str])
        lookup_type (Lookup)

    Returns (Lookup)
    """

    query = litteralement.statements.make_multi_column_select(
        table=table, columns=[colid] + columns
    )
    cur = conn.cursor()
    cur.execute(query)
    d = {i[1:]: i[0] for i in cur.fetchall()}
    lookup = ComposedKeyLookup(
        fields=columns,
        keyname="COMPOSED_KEY",
        d=d,
        keyid=colid,
        **kwargs,
    )
    return lookup


class DatabaseLookup(Lookup):
    """Un Lookup pour les tables ."""

    def __init__(
        self, conn, table, colname="nom", colid="id", **kwargs
    ):
        """Instancie un DatabaseLookup.

        Args:
            conn (Connection)
            table (str)
            colname (str)
            **kwargs -> passés à Lookup.
        """

        self.conn = conn
        self.table = table
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
            table=self.table,
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
            Identifier(self.table), Identifier(self.colname)
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
            table=self.table,
            colid=self.colid,
            colname=self.colname,
            lookup_type=TryLookup,
        )


class MultiColumnLookup(ComposedKeyLookup):
    copy_to = DatabaseLookup.copy_to

    def __init__(self, conn, table, columns, colid="id", **kwargs):
        """Instancie un MultiColumnLookup.

        Args:
            conn (Connection)
            table (str)
            columns (list[str])
            colid (str)
            **kwargs
        """

        self.conn = conn
        self.table = table
        self.colid = colid
        self.columns = columns
        _name = "COMPOSED_KEY"
        self.colname = _name
        self.keyname = _name
        d = self.fetch()
        super().__init__(
            fields=columns, keyname=_name, d=d, keyid=colid
        )

    def fetch(self):
        """Récupère les données déjà présentes dans la table.

        Returns (Lookup)
        """

        return get_multicolumn_lookup(
            conn=self.conn,
            table=self.table,
            columns=self.columns,
            colid=self.colid,
        )

    @property
    def _copy_stmt(self):
        stmt = litteralement.statements.copy_to_multicolumns(
            table=self.table,
            columns=[self.colid] + self.columns,
        )
        return stmt
