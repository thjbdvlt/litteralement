from spacy.language import Language
import spacy
import silex
from litteralement.utils import get_labels_updated, get_feats


@Language.component("sent_on_newline")
def newline_is_new_sentence(doc):
    """Ajoute des sentence boundaries sur les nouvelles lignes.

    Args:
        doc (Doc)
    Returns (Doc)
    """

    for token in doc:
        if token.text == "\n":
            token.is_sent_start = True
    return doc


def load_model(
    model="fr_core_news_lg",
    include_presque={},
    include_tokentype={},
    include_viceverser_lemmatizer={},
    include_quelquhui={},
    include_sent_on_newline=True,
    **kwargs,
):
    """Charge un modèle.

    Returns (Language):  le modèle pour analyser avec spacy.
    """

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


def load_model_default():
    """Charge le modèle avec les paramètres par défaut.

    Returns (Language):  un modèle pour l'analyse avec spacy.
    """

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

    nlp = load_model(
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


def load_silex(conn, nlp, **kwargs):
    # récupérer les labels du modèle.
    dep_labels = nlp.get_pipe("parser").labels
    pos_labels = silex.lexique.POS_NAMES_LOWER
    feats_labels = get_feats(nlp)

    # récupérer les valeurs existantes dans la base de données:
    # - pos (nature)
    pos = get_labels_updated(conn, "nature", pos_labels.values())
    # - dep (fonction)
    dep = get_labels_updated(conn, "fonction", dep_labels)
    # - morph (morphologie au format FEATS)
    morph = get_labels_updated(
        conn, "morph", feats_labels, colname="feats"
    )
    # - lemmes
    lemmas = get_labels_updated(conn, "lemme", {}, colname="graphie")

    # construire les objets de lookup qui incrémentent automatiquement les ids.
    lookup_pos = silex.LookupTable(pos)
    lookup_dep = silex.LookupTable(dep)
    lookup_morph = silex.LookupTable(morph)
    lookup_lemma = silex.LookupTable(lemmas)

    lexique = silex.Lexique(
        get_pos=lambda token: lookup_pos[token.pos_],
        get_lemma=lambda token: lookup_lemma[token.lemma_],
        get_morph=lambda token: lookup_morph[str(token.morph)],
        get_norm=lambda token: token.norm_,
        add_token_attrs=lambda token: {
            "dep": lookup_dep[token.dep_],
            "tokentype": token._.tokentype,
        },
        add_lex_attrs=lambda token: {
            "vv_morph": token._.vv_morph,
            "vv_pos": token._.vv_pos,
        },
    )
    return lexique
