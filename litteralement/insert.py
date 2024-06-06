import silex
import psycopg
from utils import get_labels_updated, get_feats
import pipeline


DBNAME = "litteralement"
conn = psycopg.connect(dbname=DBNAME)

nlp = pipeline.nlp

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

# token_underscore = ["tokentype"]
# lexeme_underscore = ["vv_morph", "vv_pos"]

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

conn.close()
