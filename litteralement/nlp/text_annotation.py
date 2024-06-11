import json
import litteralement.nlp.row_insertions
from tqdm import tqdm


def todict(
    doc,
    isword=lambda token: any((char.isalpha() for char in token.text))
    and not any((token.like_url, token.like_email)),
    add_doc_attrs=lambda doc: {},
    add_token_attrs=lambda token: {},
    add_word_attrs=lambda token: {},
    add_span_attrs=lambda span: {},
):
    """Construit un dict JSON sérialilable à partir d'un Doc.

    Args:
        doc (Doc)

    Optionnels:
        isword (callable)
        add_word_attrs (callable)
        add_token_attrs (callable)
        add_span_attrs (callable)
        add_doc_attrs (callable)

    Returns (dict)
    """

    words = []
    nonwords = []

    for token in doc:
        start_char = token.idx
        end_char = token.idx + len(token.text)
        i = token.i
        d = {"debut": start_char, "fin": end_char, "num": i}
        d.update(add_token_attrs(token))
        if isword(token):
            d.update(
                {
                    "fonction": token.dep_,
                    "noyau": token.head.i,
                    "lexeme": {
                        "nature": token.pos_.lower(),
                        "morph": str(token.morph),
                        "norme": token.norm_,
                        "lemme": token.lemma_,
                    },
                }
            )
            d.update(add_word_attrs(token))
            words.append(d)
        else:
            nonwords.append(d)

    sents = [
        {"debut": i.start_char, "fin": i.end_char} for i in doc.sents
    ]

    spans = []
    for i in doc.spans:
        d = {"debut": i.start_char, "fin": i.end_char}
        d.update(add_span_attrs(i))

    result = {
        "phrases": sents,
        "segments": spans,
        "nonmots": nonwords,
        "mots": words,
    }

    result.update(add_doc_attrs(doc))

    return result


def annoter(
    conn,
    query,
    nlp,
    batch_size=1000,
    n_process=2,
    isword=lambda token: token._.tokentype == "word",
    noinsert=False,
    progress_item_number=200,
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

    # placer les documents dans la table import._document (la méthode 'COPY' est beaucoup plus rapide qu'une insertion normale).
    n = 0
    print("début de l'annotation")
    with cur_send.copy(
        "COPY import._document (j, id) FROM STDIN"
    ) as copy:
        for i in tqdm(docs):
            n += 1
            doc = todict(i[0], isword=isword, **kwargs)
            row = (json.dumps(doc)), i[1]["id"]
            copy.write_row(row)

    # commit les changements
    conn.commit()

    # si le paramètre noinsert est False (défaut), les données sont automatiquement insérées dans les tables.
    if noinsert is False:
        litteralement.nlp.row_insertions.inserer(conn)