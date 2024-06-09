import json
import psycopg
from psycopg.sql import SQL
from litteralement.statements import copy_to_multicolumns
from litteralement.lookups.database import DatabaseLookup
from litteralement.lookups.database import TryDatabaseLookup
from litteralement.lookups.database import MultiColumnLookup


def _copy_from_temp(conn, table, key, columns):
    """Copier dans les tables depuis la table temporaire.

    Args:
        conn (Connection):  la connection à la base de données.
        table (str):  le nom de la table.
        key (str):  la clé du types d'éléments dans le doc.
        columns (list[str]):  la liste de colonnes (et clés d'éléments.)
    """

    # deux curseurs: un pour recevoir, l'autre pour envoyer (en même temps).
    cur_get = conn.cursor()
    cur_send = conn.cursor()

    # la requête pour prendre depuis les docs (table temporaires).
    sql_get = SQL("select id, j from _temp_doc")

    # construire la requête pour envoyer avec colonnes multiples.
    sql_copy_send = copy_to_multicolumns(
        table=table,
        columns=["texte"] + columns,
    )

    # récupérer les docs.
    docs = cur_get.execute(sql_get)

    # copier les éléments dans la table.
    with cur_send.copy(sql_copy_send) as copy:
        for i in docs:
            textid = i[0]  # l'id du texte, commun à mot/token/phrase
            doc = i[1]  # le doc
            for x in doc[key]:
                # construire des tuples, et les ajouter à l'id du texte.
                row = tuple((x[c] for c in columns))
                copy.write_row((textid,) + row)


def _copy_mot(conn):
    """Ajoute les mots dans la base de données."""

    table = "mot"
    key = "mots"
    columns = ["debut", "fin", "num", "noyau", "lexeme", "fonction"]
    _copy_from_temp(conn=conn, table=table, key=key, columns=columns)


def _copy_token(conn):
    """Ajoute les tokens dans la base de données."""

    table = "token"
    key = "nonmots"
    columns = ["debut", "fin", "num"]
    _copy_from_temp(conn=conn, table=table, key=key, columns=columns)


def _copy_phrase(conn):
    """Ajoute les phrases dans la base de données."""

    table = "phrase"
    key = "phrases"
    columns = ["debut", "fin"]
    _copy_from_temp(conn=conn, table=table, key=key, columns=columns)


def insert(dbname="litteralement"):
    """Ajoute les import._documents dans les tables."""

    # connection
    conn = psycopg.connect(dbname=dbname)

    # créer des tables lookups pour les ids.
    lookup_lemma = DatabaseLookup(
        conn, "nlp", "lemme", colname="graphie"
    )
    lookup_pos = TryDatabaseLookup(conn, "nlp", "nature")
    lookup_dep = TryDatabaseLookup(conn, "nlp", "fonction")
    lookup_morph = TryDatabaseLookup(
        conn, "nlp", "morph", colname="feats"
    )
    lookup_lex = MultiColumnLookup(
        conn=conn,
        table=["nlp", "lexeme"],
        colid="id",
        columns=["lemme", "norme", "nature", "morph"],
    )

    # créer une table temporaire à partir de laquelle exécuter les 'copy', et dans laquelle va aller les mots, tokens, ..., avec les IDs pour remplacer les textes (des POS, DEP, MORPH, etc.).
    conn.execute("create temp table _temp_doc (id int, j jsonb);")

    # deux curseurs: un pour envoyer les données, l'autre pour recevoir: je fais ça en même temps (avec des Generator).
    cur_get = conn.cursor()
    cur_send = conn.cursor()

    def numerize_lex(lex):
        """Numerise les lexèmes.

        Args:
            lex (dict):  le dict décrivant le lexème.

        Returns (int):  l'id du lexème.

        Durant le processus, les POS (nature), DEP (fonction) et LEMMA (lemme) sont aussi analysés. ils sont ajoutés dans leurs tables lookups respectives, à partir desquelles ils seront ajoutés dans la base de données.
        """

        for (
            tag,
            lookup,
        ) in (
            ("nature", lookup_pos),
            ("lemme", lookup_lemma),
            ("morph", lookup_morph),
        ):
            val = lex[tag]
            lex[tag] = lookup[val]
        key = lookup_lex.Key(**lex)
        _id = lookup_lex[key]
        return _id

    def numerize_mot(word):
        """Numérise un mot."""

        dep = lookup_dep[word["fonction"]]
        lex = numerize_lex(word["lexeme"])
        head = word["noyau"]
        word.update(
            {
                "lexeme": lex,
                "fonction": dep,
                "noyau": head,
            }
        )
        return word

    def numerize_doc():
        """Numerize les composants des docs."""

        docs = cur_get.execute(
            "select id, j from import._document limit 1000;"
        )
        with cur_send.copy("copy _temp_doc (id, j) from stdin") as copy:
            for i in docs:
                _id = i[0]
                j = i[1]
                words = j["mots"]
                for word in words:
                    _ = numerize_mot(word)
                copy.write_row(
                    (
                        _id,
                        json.dumps(j),
                    )
                )

    # numériser les docs.
    numerize_doc()

    # ajouter les morphologie, nature, fonctions, lemmes, dans les tables respectives.
    lookup_morph.copy_to()
    lookup_pos.copy_to()
    lookup_dep.copy_to()
    lookup_lemma.copy_to()

    # l'ordre est important: la table 'lexeme' dépend de 'morph', 'pos', 'lemma'. et la table 'mot' dépend de 'dep'.
    lookup_lex.copy_to()

    # copier les mots, tokens, phrases dans les tables respectives.
    _copy_mot(conn)
    _copy_token(conn)
    _copy_phrase(conn)

    # commit et clore la connection: fin de la fonction.
    conn.commit()
    conn.close()
