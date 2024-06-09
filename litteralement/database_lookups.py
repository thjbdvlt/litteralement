from psycopg.sql import SQL, Identifier
from typing import Any
from litteralement.lookups import Lookup
from litteralement.lookups import TryLookup
import litteralement.statements


def get_binary_lookup(
    conn,
    tablename,
    colname="nom",
    lookup_type=Lookup,
):
    """Récupère une table lookup binaire (id/nom).

    Args:
        conn (Connection)
        tablename (str)
        colname (str)
        lookup_type (Lookup, TryLookup)

    Returns (Lookup, TryLookup)
    """

    query = SQL("select id, {} from {}").format(
        Identifier(colname), Identifier(tablename)
    )
    cur = conn.cursor()
    cur.execute(query)
    d = {i[1]: i[0] for i in cur.fetchall()}
    lookup = lookup_type(keyname=colname, d=d)
    return lookup


def get_multicolumn_lookup(
    conn, tablename, columns, lookup_type=Lookup
):
    """Récupère un Lookup multikey (plusieurs colonnes).

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
    lookup = lookup_type(keyname="multikey", d=d)
    return lookup


class ConceptLookup(Lookup):
    """Un Lookup pour les tables CONCEPT (classe, morphologie, ...)."""

    def __init__(self, conn, tablename, colname="nom", **kwargs):
        """Instancie un ConceptLookup.

        Args:
            conn (Connection)
            tablname (str)
            colname (str)
            **kwargs -> passés à Lookup.
        """

        self.conn = conn
        self.tablename = tablename
        self.colname = colname
        d = self.fetch()
        super().__init__(d=d, keyname=colname, **kwargs)

    def fetch(self):
        """Récupère les données déjà présentes dans la table.

        Returns (Lookup)
        """

        return get_binary_lookup(
            self.conn,
            tablename=self.tablename,
            colname=self.colname,
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
        stmt = SQL("copy {} (id, {}) from stdin").format(
            Identifier(self.tablename), Identifier(self.colname)
        )
        return stmt


class TryConceptLookup(ConceptLookup, TryLookup):
    """Concept Lookup pour les Tables avec peu de valeurs."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class MultiColumnLookup(ConceptLookup):
    def __init__(self, conn, tablename, columns, **kwargs):
        self.columns = columns
        super().__init__(conn=conn, tablename=tablename, **kwargs)
        non_id_fields = [(i, Any) for i in columns]
        fields = [("id", int)] + non_id_fields
        self.Item = NamedTuple("Item", fields)
        self.Key = NamedTuple("Key", non_id_fields)

    def fetch(self):
        """Récupère les données déjà présentes dans la table.

        Returns (Lookup)
        """

        return get_multicolumn_lookup(
            self.conn,
            tablename=self.tablename,
            columns=self.columns,
        )

    @property
    def _copy_stmt(self):
        stmt = litteralement.statements.copy_to_multicolumns(
            self.tablename, ["id"] + self.columns
        )
        return stmt

    def as_tuples(self):
        Item = self.Item
        d = self.d
        for k in self.d:
            yield Item(id=d[k], **k._asdict())
