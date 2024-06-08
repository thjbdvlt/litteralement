from litteralement.lookups import ConceptLookup
from litteralement.lookups import TryConceptLookup
from litteralement.lookups import MultiColumnLookup


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
        d = {"start_char": start_char, "end_char": end_char, "i": i}
        d.update(add_token_attrs(token))
        if isword(token):
            d.update(
                {
                    "dep": token.dep_,
                    "head": token.head.i,
                    "lex": {
                        "pos": token.pos_.lower(),
                        "morph": str(token.morph),
                        "norm": token.norm_,
                        "lemma": token.lemma_,
                    },
                }
            )
            d.update(add_word_attrs(token))
            words.append(d)
        else:
            nonwords.append(d)

    sents = [
        {"start_char": i.start_char, "end_char": i.end_char}
        for i in doc.sents
    ]

    spans = []
    for i in doc.spans:
        d = {"start_char": i.start_char, "end_char": i.end_char}
        d.update(add_span_attrs(i))

    result = {
        "sents": sents,
        "spans": spans,
        "nonwords": nonwords,
        "words": words,
    }

    result.update(add_doc_attrs(doc))

    return result


def get_pos_lookup_en(conn):
    """Construit un Lookup pour les part-of-speech.

    Args:
        conn (Connection)

    Returns (TryConceptLookup)
    """

    return TryConceptLookup(conn, "pos")


def get_dep_lookup_en(conn):
    """Construit un Lookup pour les dependency labels.

    Args:
        conn (Connection)

    Returns (TryConceptLookup)
    """

    return TryConceptLookup(conn, "dep")


def get_morph_lookup_en(conn):
    """Construit un Lookup pour les morphologies (feats).

    Args:
        conn (Connection)

    Returns (TryConceptLookup)
    """

    return TryConceptLookup(conn, "morph", colname="feats")


def get_lemma_lookup_en(conn):
    """Construit un Lookup pour les lemmes.

    Args:
        conn (Connection)

    Returns (ConceptLookup)
    """

    return ConceptLookup(conn, "lemma", "text")


def get_lexeme_lookup_en(conn):
    return MultiColumnLookup(
        conn, "lex", ["lemma", "norm", "pos", "morph"]
    )
