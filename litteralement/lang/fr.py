ENG_TO_FRENCH = {
    "dep": "fonction",
    "pos": "nature",
    "lex": "lexeme",
    "start_char": "debut",
    "end_char": "fin",
    "lemma": "lemme",
    "i": "num",
    "head": "noyau",
    "norm": "norme",
    "morph": "morph",
    "sents": "phrase",
    "span": "segment",
    "token": "token",
    "words": "mots",
    "word": "mot",
}


def translate_keys(d, table=ENG_TO_FRENCH):
    """Traduit les keys d'un dict.

    Args:
        d (dict):  le dict.
        table (dict):  la table de traduction

    Returns (dict):  le dict, traduit.
    """

    return {table[k]: d[k] for k in d}


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
