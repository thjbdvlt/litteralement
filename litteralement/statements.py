SELECT_LEXEMES = """select
    x.id,
    l.graphie as lemma,
    x.norme,
    n.nom as pos,
    m.feats as morph
from lexeme x
join lemme l on l.id = x.lemme
join nature n on n.id = x.nature
join morph m on m.id = x.morph;"""

SELECT_LEMMES = """select
    id,
    graphie
from lemme;"""

SELECT_POS = """select
    id,
    nom
from nature;"""

SELECT_DEP = """select
    id,
    nom
from fonction;"""

SELECT_MORPH = """select
    id,
    feats
from morph;"""
