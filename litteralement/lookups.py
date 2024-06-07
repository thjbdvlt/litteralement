from psycopg.sql import SQL, Identifier
import litteralement.seq
from typing import NamedTuple
import json


class Lookup:
    """Lookup Table sous la forme {nom: id}, avec génération incrémentale d'id."""

    def __init__(self, keyname="nom", d=None):
        """Instancie une table lookup simple: {label: id}.

        Args:
            d (dict):  les données de départ {label: id}.
        """

        self.keyname = keyname
        self.Item = NamedTuple("Item", [("id", int), (keyname, str)])

        if not d:
            d = {}

        if isinstance(d, dict):
            pass
        else:
            d = {i[self.keyname]: i["id"] for i in d}
        for i in d.values():
            if not isinstance(i, int):
                raise TypeError("table values must be of type int.")
        if len(set(d.values())) != len(d.keys()):
            raise ValueError("initial values must be unique.")

        self.d = d
        self.seq = litteralement.seq.Seq()
        self.ersatz = set()
        self._update_sequence()

    def __contains__(self, i):
        return i in self.d

    def __setitem__(self, k, v):
        """Ajoute l'objet dans la table, avec un id.

        Args:
            k:  key.
            v:  value.
        """

        self.d[k] = v

    def __getitem__(self, label):
        """Retourne l'id de l'objet. L'ajoute au besoin.

        Args:
            i:  l'objet.

        Returns (int):  l'id.
        """

        if label in self:
            _id = self.d[label]
        else:
            _id = self.seq.nextval()
            self[label] = _id
        return _id

    def __dict__(self):
        return self.d

    def __call__(self, label):
        """Cherche si l'item est là. Sinon, l'ajoute.

        Args:
            label:  le label.

        Returns (int):  son id.
        """

        return self.__getitem__(label)

    def to_dict(self, reverse=True):
        """Retourne un dictionnaire à partir de la lookup table.

        Args:
            reverse (bool):  si il faut inverser la logique clé-valeur.

        Note:
            Des valeurs ajoutés à l'aide de `add()` peuvent être non-unique. Elles sont enlevées pour ne pas effacer les valeurs initiales. (Et sont donc absente.)
        """

        if reverse is False:
            return self.d
        else:
            x = {}
            for i in set(self.d.keys()) - self.ersatz:
                x[self[i]] = i
            return x

    def __iter__(self):
        """Itère sur les clés.

        Returns (Generator)
        """

        for i in self.d:
            yield {"id": self.d[i], self.keyname: i}

    def as_tuples(self):
        """Retourne les items du Lookup sous forme de tuple (id, nom).

        Le paramètre 'new' conserve une liste des nouveaux élements.
        """
        Item = self.Item
        d = self.d
        for i in d:
            yield Item(d[i], i)

    def add(self, d):
        """Ajoute les éléments d'un dictionnaire s'ils ne s'y trouvent pas déjà.

        Args:
            d (dict):  les éléments du dictionnaire.
        """

        if not isinstance(d, dict):
            raise TypeError("d must be of type dict.")
        values = set(self.d.values())
        for k in d:
            if k not in self:
                v = d[k]
                self[k] = v
                if v in values:
                    self.ersatz.add(k)
        self._update_sequence()

    def _update_sequence(self):
        """Update la valeur courante."""

        self.seq.curval = max(list(self.d.values()) + [self.seq.curval])


class TryLookup(Lookup):
    """Lookup Table pour les fois où les clés sont peu nombreuses."""

    def __getitem__(self, label):
        try:
            return self.d[label]
        except KeyError:
            super().__getitem__(label)


def get_binary_lookup(
    conn, tablename, colname="nom", lookup_type=Lookup
):
    query = SQL("select id, {} from {}").format(
        Identifier(colname), Identifier(tablename)
    )
    cur = conn.cursor()
    cur.execute(query)
    d = {i[1]: i[0] for i in cur.fetchall()}
    lookup = lookup_type(keyname=colname, d=d)
    return lookup


class ConceptLookup(Lookup):
    def __init__(self, conn, tablename, colname="nom", **kwargs):
        self.conn = conn
        self.tablename = tablename
        self.colname = colname
        d = self.fetch()
        super().__init__(d=d, keyname=colname, **kwargs)

    def fetch(self):
        return get_binary_lookup(
            self.conn,
            tablename=self.tablename,
            colname=self.colname,
        )

    def copy_to(self):
        stmt = SQL("copy {} ({}) from stdin").format(
            Identifier(self.tablename), Identifier.self.colname
        )
        existing = set(self.fetch())
        with self.conn.copy(stmt) as copy:
            for i in set(self) - existing:
                copy.write_row((json.dumps(i),))


class TryConceptLookup(ConceptLookup, TryLookup):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


def get_pos_lookup(conn):
    return TryConceptLookup(conn, "nature")


def get_dep_lookup(conn):
    return TryConceptLookup(conn, "fonction")


def get_morph_lookup(conn):
    return TryConceptLookup(conn, "morph", colname="feats")


def get_lemma_lookup(conn):
    return ConceptLookup(conn, "lemme", "graphie")


def get_key_spacy(d):
    return (d["lemma"], d["norm"], d["pos"], d["morph"])
