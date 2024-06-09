import tqdm
import json
from psycopg.sql import SQL
from litteralement.lang.fr import todict
from litteralement.statements import copy_to_multicolumns


def annoter(
    conn,
    query,
    nlp,
    batch_size=1000,
    n_process=2,
    isword=lambda token: token._.tokentype == "word",
    **kwargs,
):
    """Annoter des textes et les insérer dans la base de données.

    Args:
        conn (Connection)
        query (str):  SQL select qui doit retourner (id=int, val=text)
        nlp (Language)

    Optionnel:
        batch_size (int)
        n_process (int)
    """

    # deux curseurs: il faut pouvoir envoyer tout en continuant de recevoir
    cur_get = conn.cursor()
    cur_send = conn.cursor()

    # lance la requête qui SELECT les textes.
    cur_get.execute(query)

    # crée des tuples pour process avec spacy en conservant les métadonnées.
    texts = ((record[1], {"id": record[0]}) for record in cur_get)
    docs = nlp.pipe(
        texts=texts,
        as_tuples=True,
        batch_size=batch_size,
        n_process=n_process,
    )

    # construire des dicts
    docs = map(
        lambda i: (
            todict(i[0], isword=isword, **kwargs),
            i[1]["id"],
        ),
        docs,
    )

    # sérialiser en JSON
    todb = map(lambda i: (json.dumps(i[0]), i[1]), docs)

    # placer les documents dans la table import._document (la méthode 'COPY' est beaucoup plus rapide qu'une insertion normale).
    with cur_send.copy(
        "COPY import._document (j, id) FROM STDIN"
    ) as copy:
        for i in tqdm.tqdm(todb):
            copy.write_row(i)

    conn.commit()


def copy_to_from_temp(conn, table, key, columns):
    """Copier dans les tables depuis la table temporaire.

    Args:
        conn (Connection):  la connection à la base de données.
        table (str):  le nom de la table.
        key (str):  la clé du types d'éléments dans le doc.
        columns (list[str]):  la liste de colonnes (et clés d'éléments.)
    """

    cur_get = conn.cursor()
    cur_send = conn.cursor()
    sql_get = SQL("select _id, j from _temp_doc")
    sql_copy_send = copy_to_multicolumns(table=table, columns=columns)
    docs = cur_get.execute(sql_get)
    with cur_send.copy(sql_copy_send) as copy:
        for i in docs:
            textid = i[0]
            doc = i[1]
            for x in doc[key]:
                row = (x[c] for c in columns)
                copy.write_row((textid) + row)


def copy_to_mot(conn):
    """Ajoute les mots dans la base de données."""

    table = "mot"
    key = "mots"
    columns = ["debut", "fin", "num", "noyau", "lexeme", "fonction"]
    copy_to_from_temp(conn=conn, table=table, key=key, columns=columns)


def copy_to_token(conn):
    """Ajoute les tokens dans la base de données."""

    table = "token"
    key = "nonmots"
    columns = ["debut", "fin", "num"]
    copy_to_from_temp(conn=conn, table=table, key=key, columns=columns)


def copy_to_phrase(conn):
    """Ajoute les phrases dans la base de données."""

    table = "phrase"
    key = "phrase"
    columns = ["debut", "fin"]
    copy_to_from_temp(conn=conn, table=table, key=key, columns=columns)
