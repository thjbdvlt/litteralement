from typing import NamedTuple, Any
import litteralement.seq


class Lookup:
    """Lookup Table sous la forme {nom: id}, avec génération incrémentale d'id."""

    def __init__(self, keyname="nom", d=None, keyid="id"):
        """Instancie une table lookup simple: {label: id}.

        Args:
            d (dict):  les données de départ {label: id}.
        """

        self.keyname = keyname
        self.keyid = keyid
        self.Item = NamedTuple("Item", [(keyid, int), (keyname, str)])

        if not d:
            d = {}
        elif not isinstance(d, dict):
            d = {i[self.keyname]: i[keyid] for i in d}

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
        """True si l'item est dans le Lookup.

        Args:
            i (Any):  l'item, qui doit seulement être hashable.

        Returns (bool)
        """

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

    def __call__(self, i):
        """Cherche si l'item est là. Sinon, l'ajoute.

        Args:
            i (Any):  l'item (doit être hashable).

        Returns (int):  son id.
        """

        return self.__getitem__(i)

    def __iter__(self):
        """Liste de dictionnaire.

        Returns (Generator)
        """

        keyid = self.keyid
        for i in self.d:
            yield {keyid: self.d[i], self.keyname: i}

    def to_dict(self, reverse=True):
        """Retourne un dictionnaire à partir de la lookup table.

        Args:
            reverse (bool):  si il faut inverser la logique clé-valeur.

        Note:
            Des valeurs ajoutés à l'aide de `add()` peuvent être non-unique. Elles sont enlevées pour ne pas effacer les valeurs initiales si le paramètre 'reverse' est True, pour éviter que
                [{"REAL_KEY": 1, "alternate_key": 1}]
            devienne
                [{"alternate_key": 1}]
        """

        if reverse is False:
            return self.d
        else:
            x = {}
            for i in set(self.d.keys()) - self.ersatz:
                x[self[i]] = i
            return x

    def as_tuples(self):
        """Retourne les items du Lookup sous forme de tuple (id, nom).

        Returns (Generator[NamedTuple])
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

    def __getitem__(self, i):
        """Méthode alternative: essayer de récupérer la clé.

        Args:
            i (Any):  le label.

        Returns (int):  l'indentifiant.
        """

        try:
            return self.d[i]
        except KeyError:
            return super().__getitem__(i)


class ComposedKeyLookup(Lookup):
    def __init__(
        self, fields, d=None, keyid="id", keyname="COMPOSED_KEY"
    ):
        super().__init__(keyname=keyname, d=d, keyid=keyid)
        self.fields = fields
        tuple_fields = [(i, Any) for i in fields]
        self.Key = NamedTuple("Key", tuple_fields)
        self.Item = NamedTuple(
            "Item", [(self.keyid, int)] + tuple_fields
        )

    def as_tuples(self):
        Item = self.Item
        d = self.d
        for i in d:
            yield Item(*((d[i],) + i))
