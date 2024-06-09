import psycopg
from litteralement.lookups.database import TryDatabaseLookup
from litteralement.lookups.database import MultiColumnLookup
from litteralement.lookups.core import Lookup
from litteralement.lookups.core import ComposedKeyLookup


dbname = "litteralement"
conn = psycopg.connect(dbname=dbname)

conn.execute("create temp table _temp_data (j json)")

lookup_import = MultiColumnLookup(
    conn=conn,
    colid="id_entite",
    columns=["dataset", "id_dataset"],
    table=["import", "_lookup_entite"],
)

lookup_classe = TryDatabaseLookup(conn, "classe")
lookup_type_relation = TryDatabaseLookup(conn, "type_relation")
lookup_type_propriete = TryDatabaseLookup(conn, "type_propriete")

lookup_entites_dataset = ""


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
    "entites": [
        {
            "id": 1,
            "dataset": 1,
            "classe": "lieu",
            "nom": "chemin du saule",
        },
        {
            "id": 2,
            "dataset": 1,
            "classe": "arbre",
            "nom": "le joli saule",
            "lueur": 0.4,
            "paroles": {"depuis": "lors"},
        },
    ],
    "relations": [{"sujet": 1, "objet": 2, "type": "passe à côté de"}],
}


def numerise_entite(d):
    _id = d.pop("id")
    dataset = d.pop("dataset")
    classe = d.pop("classe")
    proprietes = [
        {"type": lookup_type_propriete[k], "val": d[k]} for k in d
    ]
    new = {}


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