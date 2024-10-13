import json
import litteralement.nlp.row_insertions
import litteralement.util.statements
from tqdm import tqdm


def todict(
    doc,
    isword=lambda token: any((char.isalpha() for char in token.text))
    and not any((token.like_url, token.like_email)),
    add_token_attrs=lambda token: {},
    add_word_attrs=lambda token: {},
    add_span_attrs=lambda span: {},
    add_lex_attrs=lambda token: {},
    lex_user_attrs=[],
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

    sents = []
    token_sent_idx = []
    for n_sent, sent in enumerate(doc.sents, 1):
        if len(sent) > 0:
            first_token_start = sent[0].idx
            last_token = sent[-1]
            last_token_end = last_token.idx + len(last_token.text)
            sents.append(
                {
                    "debut": first_token_start + 1,
                    "fin": last_token_end + 1,
                    "n": n_sent,
                }
            )

        for n, token in enumerate(sent, 1):
            token_sent_idx.append(n_sent)
            start_char = token.idx + 1
            end_char = start_char + len(token.text)
            i = token.i
            d = {
                "debut": start_char,
                "fin": end_char,
                "num": n,
                "phrase": token_sent_idx[i],
            }

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
                for i in lex_user_attrs:
                    k = i["name"]
                    fn = i["function"]
                    d["lexeme"][k] = fn(token)
                words.append(d)

            else:
                nonwords.append(d)

    spans = []
    for i in doc.spans:
        d = {
            "debut": i.start_char + 1,
            "fin": i.end_char + 1,
            "attrs": add_span_attrs(i),
        }

    result = {
        "phrases": sents,
        "spans": spans,
        "nonmots": nonwords,
        "mots": words,
    }

    return result


def annoter(
    conn,
    query,
    nlp,
    batch_size=1000,
    n_process=2,
    no_tokentype=False,
    noinsert=False,
    **kwargs,
):
    """Annoter des textes et les insérer dans la base de données.

    Args:
        conn (Connection)
        query (str):  SQL select qui doit retourner (id=int, val=text) ('all' pour tout annoter.)
        nlp (Language)

    Optionnel:
        batch_size (int)
        n_process (int)
        isword (callable):  la fonction qui distingue les mots des autres tokens.
        noinsert (bool):  ne pas insérer le résultat de l'annotation dans les tables.
    """

    if no_tokentype:

        def isword(token):
            return True
    else:
        if "tokentype" not in nlp.pipe_names:
            nlp.add_pipe("tokentype")

        def isword(token):
            return token._.tokentype == "word"

    # deux curseurs: il faut pouvoir envoyer tout en continuant de recevoir
    cur_get = conn.cursor()
    cur_send = conn.cursor()

    if query == "all":
        query = litteralement.util.statements.UNANNOTATED_TEXTS

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

    # placer les documents dans la table litteralement._document (la méthode 'COPY' est beaucoup plus rapide qu'une insertion normale).
    print("début de l'annotation...")
    with cur_send.copy(
        "COPY litteralement._document (j, id) FROM STDIN"
    ) as copy:
        for i in tqdm(docs):
            doc = todict(i[0], isword=isword, **kwargs)
            row = (json.dumps(doc)), i[1]["id"]
            copy.write_row(row)

    # commit les changements
    conn.commit()

    # si le paramètre noinsert est False (défaut), les données sont automatiquement insérées dans les tables.
    if noinsert is False:
        litteralement.nlp.row_insertions.inserer(conn, **kwargs)
