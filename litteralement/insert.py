import silex
import tqdm
import orjson
import litteralement.statements


def get_lexemes(conn):
    """Récupérer les lexèmes pour construire un Lookup pour l'annotation.

    Args:
        conn (Connection)

    Returns (Generator)
    """

    cur = conn.cursor()
    cur.execute(litteralement.statements.SELECT_LEXEMES)
    for i in cur:
        yield i


def insert(
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
        isword (callable):  distingue les tokens des mots.
    """

    # deux curseurs: il faut pouvoir envoyer tout en continuant de recevoir
    cur_get = conn.cursor()
    cur_send = conn.cursor()

    # lance la requête qui SELECT les textes.
    cur_get.execute(query)

    # crée des tuples pour process avec spacy en conservant les métadonnées.
    texts = ((record.val, {"id": record.id}) for record in cur_get)
    docs = nlp.pipe(
        texts=texts,
        as_tuples=True,
        batch_size=batch_size,
        n_process=n_process,
        **kwargs,
    )

    # récupérer les lexèmes déjà existants.
    lexemes = get_lexemes(conn)
    lexique = silex.Lexique(lexemes=lexemes)

    # ajouter les lexèmes, pour pouvoir sérialiser moins de choses.
    docs = map(lambda i: (lexique(i[0], i[1]["id"])), docs)

    # sérialiser en JSON
    todb = map(lambda i: (orjson.dumps(i[0]), i[1]), docs)

    # placer les documents dans la table import._document (la méthode 'COPY' est incroyablement plus rapide qu'une insertion normale).
    with cur_send.copy("COPY doc._document (id, j) FROM STDIN") as copy:
        for i in tqdm.tqdm(todb):
            copy.write_row(i)

    # TODO: l'insertion des lexèmes
    with cur_send.copy("COPY import.lexeme (j) FROM STDIN") as copy:
        for i in tqdm.tqdm(orjson.dumps(lexique.lexemes)):
            copy.write_row(i)
        # hoooo mais là yaurait moyen déjà de faire qqch héhé!
        # déjà facile de process les données ici.
    conn.commit()
