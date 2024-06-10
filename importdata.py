import psycopg
from litteralement.lookups.database import TryDatabaseLookup
from litteralement.lookups.database import MultiColumnLookup


dbname = "litteralement"
conn = psycopg.connect(dbname=dbname)

conn.execute("create temp table _temp_data (j json)")

curval = conn.execute("select nextval('entite_id_seq')").fetchone()[0]

lookup_import = MultiColumnLookup(
    conn=conn,
    colid="id_entite",
    columns=["dataset", "id_dataset"],
    table="import._lookup_entite",
    start_id=curval,
)
lookup_classe = TryDatabaseLookup(conn, "onto.classe")
lookup_type_relation = TryDatabaseLookup(conn, "onto.type_relation")
lookup_type_propriete = TryDatabaseLookup(conn, "onto.type_propriete")

# importation EAV
# importer les données dans les tables entités, classes, types de proprités/relations, relations, propriétés.

# - classes
# - types propriété
# - types relation
# - entite
# - relation
# - propriétés (toutes les tables)

# reprendre le format d'importation?
# (possible aussi: de mettre dans un dossier et que l'importation se fasse depuis ce dossier)
# ha oui yavait le truc des IDs tout ça.

data = {
    "dataset": 1,
    "entites": [
        {
            "id": 1,
            "classe": "lieu",
            "nom": "chemin du saule",
        },
        {
            "id": 2,
            "classe": "arbre",
            "nom": "le joli saule",
            "lueur": 0.4,
            "est_magique": None,
            "paroles": {"depuis": "lors"},
        },
    ],
    "relations": [{"sujet": 1, "objet": 2, "type": "passe à côté de"}],
}

import orjson

# ou alors je fais ça plus tard?
def table_val_from_datatype(val):
    if isinstance(val, str):
        return 'texte'
    elif isinstance(val, int):
        return 'prop_int'
    elif isinstance(val, float):
        return 'prop_float'
    elif not val:
        return 'propriete'
    elif isinstance(val, (dict, list, tuple)):
        return 'prop_jsonb'
    return 'prop_jsonb'


def numerise_entite(entite, dataset):
    """Prépare un dict décrivant une entité.

    Args:
        entite (dict):  le dictionnaire décrivant l'entité.
        dataset (int):  l'identifiant du dataset.

    Returns (dict):  un nouveau dict, avec des foreign keys.
    """

    id_dataset = entite.pop("id")
    classe = entite.pop("classe")
    proprietes = [
        {"type": lookup_type_propriete[k], "val": entite[k]}
        for k in entite
    ]
    key = lookup_import.Key(
        **{"dataset": dataset, "id_dataset": id_dataset}
    )
    d = {
        "classe": lookup_classe[classe],
        "id": lookup_import[key],
        "proprietes": proprietes,
    }
    return d


numerise_entite(data['entites'][0], data['dataset'])

def numerise_relation(relation):


lookup_import.Key._fields

key = lookup_import.Key(**{"dataset": 1, "id_dataset": 10})

# ok alors j'ai besoin


{"a": 1}.pop("b")  # key error

cur_get = conn.cursor()
cur_send = conn.cursor()

# for row in cur_get.execute("select j from import._data"):

data = data
entites = data["entites"]
for ent in entites:
    classe = ent["classe"]

# ajouter les classes:
# with cur_send.copy("copy ") as copy:
#     copy('...')

conn.close()
