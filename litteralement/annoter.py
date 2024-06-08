import tqdm
import json
from litteralement.lang.fr import todict


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
