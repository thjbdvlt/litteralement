import silex
import psycopg
from litteralement.utils import get_labels_updated, get_feats
import litteralement.pipeline


class Annotater:
    def __init__(self, dbname="litteralement", **kwargs):
        conn = psycopg.connect(dbname=dbname)

        nlp = litteralement.pipeline.load_model(**kwargs)

        dep_labels = nlp.get_pipe("parser").labels
        pos_labels = silex.lexique.POS_NAMES_LOWER
        feats_labels = get_feats(nlp)

        pos = get_labels_updated(conn, "nature", pos_labels.values())
        dep = get_labels_updated(conn, "fonction", dep_labels)
        morph = get_labels_updated(
            conn, "morph", feats_labels, colname="feats"
        )
        lemmas = get_labels_updated(
            conn, "lemme", {}, colname="graphie"
        )

        self.lookup_pos = silex.LookupTable(pos)
        self.lookup_dep = silex.LookupTable(dep)
        self.lookup_morph = silex.LookupTable(morph)
        self.lookup_lemma = silex.LookupTable(lemmas)

        if (
            "include_tokentype" in kwargs
            and kwargs["include_tokentype"] is not False
        ):

            def add_token_attrs(token):
                return {
                    "dep": self.lookup_dep[token.dep_],
                    "tokentype": token._.tokentype,
                }
        else:

            def add_token_attrs(token):
                return {"dep": self.lookup_dep[token.dep_]}

        if (
            "include_viceverser" in kwargs
            and kwargs["include_viceverser"] is not False
        ):

            def add_lex_attrs(token):
                return {
                    "vv_morph": token._.vv_morph,
                    "vv_pos": token._.vv_pos,
                }
        else:

            def add_lex_attrs(token):
                return {}

        self.lexique = silex.Lexique(
            get_pos=lambda token: self.lookup_pos[token.pos_],
            get_lemma=lambda token: self.lookup_lemma[token.lemma_],
            get_morph=lambda token: self.lookup_morph[
                str(token.morph)
            ],
            get_norm=lambda token: token.norm_,
            add_token_attrs=add_token_attrs,
            add_lex_attrs=add_lex_attrs,
        )

    def __call__(self, doc, **kwargs):
        return self.lexique(doc, **kwargs)

    def pipe(self, docs, **kwargs):
        for i in docs:
            yield self(i, **kwargs)
