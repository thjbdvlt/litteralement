from spacy.language import Language
import spacy


@Language.component("sent_on_newline")
def newline_is_new_sentence(doc):
    for token in doc:
        if token.text == "\n":
            token.is_sent_start = True
    return doc


def load(
    model="fr_core_news_lg",
    include_presque={},
    include_tokentype={},
    include_viceverser_lemmatizer={},
    include_quelquhui={},
    include_sent_on_newline=True,
    **kwargs,
):
    nlp = spacy.load(model, **kwargs)
    if include_presque is not False:
        import presque

        nlp.add_pipe(
            "presque_normalizer", first=True, config=include_presque
        )
    if include_quelquhui is not False:
        import quelquhui

        nlp.tokenizer = quelquhui.Toquenizer(
            vocab=nlp.vocab, **include_quelquhui
        )
    if include_tokentype is not False:
        import tokentype

        nlp.add_pipe(
            "tokentype", after="tokentype", config=include_tokentype
        )

    if include_sent_on_newline is not False:
        nlp.add_pipe("sent_on_newline", after="tokentype")

    if include_viceverser_lemmatizer is not False:
        import viceverser

        nlp.add_pipe(
            "viceverser_lemmatizer",
            after="morphologizer",
            config=include_viceverser_lemmatizer,
        )
    return nlp


def load_default():
    model = "fr_core_news_lg"
    exclude_disable = ["ner", "lemmatizer"]
    presque_config = dict(
        exc={
            "iel": "elle",
            "ielle": "elle",
            "ielles": "elles",
            "iels": "elles",
            "celleux": "ceux",
            "cellui": "celui",
            "elleux": "elles",
            "ellui": "elle",
            "yel": "elle",
        }
    )

    abbrev = [
        r"(?:p\.)?ex\.",
        "env",
        "etc",
        r"cf\.",
        r"pp",
        "chap",
        r"c\.?-?[àa]\.?-?d",
        r"r[eé]f",
        r"[eé]ds?",
        r"trads?",
        "m[aà]j",
        r"mme?s?",
        r"mrs?",
        r"mlles?",
        "dr",
    ]

    nlp = load(
        model=model,
        exclude=exclude_disable,
        disable=exclude_disable,
        include_presque=presque_config,
        include_quelquhui={"abbrev": abbrev},
        include_tokentype=True,
        include_sent_on_newline=True,
        include_viceverser_lemmatizer=True,
    )
    return nlp
