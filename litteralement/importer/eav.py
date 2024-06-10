import psycopg
import json
from psycopg.sql import SQL, Identifier
from litteralement.statements import make_copy_stmt
from litteralement.statements import qualify
from litteralement.lookups.database import TryDatabaseLookup
from litteralement.lookups.database import MultiColumnLookup


DATA_TABLE = "import._data"
DATA_TEMP_TABLE = "_temp_data"
DATA_TEMP_COLUMNS = ("entites", "relations", "proprietes")


def create_data_temp_table(conn):
    """Crée une table temporaire pour les données à importer.

    Args:
        conn (Connection)
    """

    sql_table = Identifier(DATA_TEMP_TABLE)
    columns = ", ".join([f"{i} jsonb" for i in DATA_TEMP_COLUMNS])
    sql_columns = SQL(columns)
    sql = SQL("create temp table {} ({})").format(
        sql_table, sql_columns
    )
    conn.execute(sql)


def numerise_entite(
    entite,
    dataset,
    lookup_entite,
    lookup_classe,
    lookup_type_relation,
    lookup_type_propriete,
    **kwargs,
):
    """Prépare un dict décrivant une entité.

    Args:
        entite (dict):  le dictionnaire décrivant l'entité.
        dataset (int):  l'identifiant du dataset.

    Returns (dict):  un nouveau dict, avec des foreign keys.
    """

    id_dataset = entite["id"]
    classe = entite["classe"]
    key = lookup_entite.Key(
        **{"dataset": dataset, "id_dataset": id_dataset}
    )
    id_entite = lookup_entite[key]
    proprietes = [
        {
            "type": lookup_type_propriete[k],
            "val": entite[k],
            "entite": id_entite,
        }
        for k in set(entite) - set(["id", "classe"])
    ]
    d = {
        "classe": lookup_classe[classe],
        "id": id_entite,
        "proprietes": proprietes,
    }
    return d


def numerise_relation(
    relation,
    dataset,
    lookup_type_relation,
    lookup_entite,
    lookup_classe,
    **kwargs,
):
    """Remplace les noms et id de dataset par les id de la base de données.

    Args:
        relation (dict)

    Returns (dict)
    """

    type_relation = lookup_type_relation[relation["type"]]
    d = {"type": type_relation}
    for i in ("sujet", "objet"):
        key = lookup_entite.key_from_dict_strict(
            {"dataset": dataset, "id_dataset": relation[i]}
        )
        d[i] = lookup_entite[key]
    return d


def table_val_from_datatype(val):
    """Retourne le nom de la table correspondant au datatype.

    Args:
        val (Any):  la valeur.

    Returns (str):  le nom de la table.
    """

    if isinstance(val, str):
        return "texte"

    elif isinstance(val, int):
        return "prop_int"

    elif isinstance(val, float):
        return "prop_float"

    elif not val:
        return "propriete"

    elif isinstance(val, (dict, list, tuple)):
        return "prop_jsonb"

    return "prop_jsonb"


def numerise_row(data, **kwargs):
    """Numerise un ensemble de données (entités et relations).

    Args:
        data (dict):  les données, avec les clés "entites", "dataset", "relations".

    Returns (tuple):  (entites, relations, proprietes)
    """

    dataset = data["dataset"]
    relations = [
        numerise_relation(i, dataset, **kwargs)
        for i in data["relations"]
    ]
    entites = [
        numerise_entite(i, dataset, **kwargs) for i in data["entites"]
    ]
    proprietes = []
    for i in entites:
        proprietes.extend(i.pop("proprietes"))
    d = {
        "entites": entites,
        "relations": relations,
        "proprietes": proprietes,
    }
    return d


def copy_from_temp(conn, table, columns, source_column):
    """COPY depuis la table temporaire vers une autre table.

    Args:
        conn (Connection)
        table (str):  la table cible.
        columns (list[str]):  les colonnes cibles.
        source_column (str):  la colonne dans la TEMP TABLE.
    """

    cur_send = conn.cursor()
    cur_get = conn.cursor()
    copy_sql = make_copy_stmt(table, columns)
    sql_get = SQL("select distinct {} from {}").format(
        Identifier(source_column), Identifier(DATA_TEMP_TABLE)
    )
    data = (i[0] for i in cur_get.execute(sql_get))
    with cur_send.copy(copy_sql) as copy:
        for row in data:
            for e in row:
                copy.write_row([e[i] for i in columns])


def copy_entites(conn):
    """Copie les entités depuis la table temporaire.

    Args:
        conn (Connection)
    """

    columns = ("id", "classe")
    source_column = "entites"
    table = "entite"
    copy_from_temp(conn, table, columns, source_column)


def copy_relations(conn):
    """Copie les relations depuis la table temporaire.

    Args:
        conn (Connection)
    """

    columns = ("type", "sujet", "objet")
    source_column = "relations"
    table = "relation"
    copy_from_temp(conn, table, columns, source_column)


def insert_une_propriete(cursor, d):
    """Construit un INSERT statement en fonction du type de données.

    Args:
        val (Any): la valeur, qui détermine la table.

    Returns (SQL): le INSERT statement.
    """

    table = table_val_from_datatype(d["val"])
    columns = (
        ("entite", "type")
        if table == "propriete"
        else ("entite", "type", "val")
    )
    if table == 'prop_jsonb':
        d['val'] = json.dumps(d['val'])
    placeholders = ", ".join(["%s" for i in columns])
    stmt = f"insert into {{}} ({{}}) select {placeholders}"
    sql_table = Identifier(table)
    sql_columns = SQL(", ").join([Identifier(i) for i in columns])
    sql_stmt = SQL(stmt).format(sql_table, sql_columns)
    row = [d[i] for i in columns]
    cursor.execute(sql_stmt, row)


def insert_toutes_proprietes(conn):
    """Insère toutes les propriétés depuis la TEMP TABLE.

    Args:
        conn (Connection)
    """
    sql_get = "select distinct proprietes from " + DATA_TEMP_TABLE
    data = (i[0] for i in conn.execute(sql_get))
    cur_send = conn.cursor()
    for row_source in data:
        for d in row_source:
            insert_une_propriete(cur_send, d)


def insert_data(dbname='litteralement'):
    """Insère dans les tables EAV ce qui se trouve dans import._data.

    Args:
        dbname (str)
    """

    conn = psycopg.connect(dbname=dbname)

    create_data_temp_table(conn)

    # récupère l'id actuel de la table "entite".
    curval = conn.execute("select nextval('entite_id_seq')").fetchone()[0]

    # construit les lookups (qui remplissent une fonction de  "join").
    lookup_classe = TryDatabaseLookup(conn, "onto.classe")
    lookup_type_relation = TryDatabaseLookup(conn, "onto.type_relation")
    lookup_type_propriete = TryDatabaseLookup(conn, "onto.type_propriete")
    # le lookup 'entite' est un peu particulier, car il n'est pas utilisé, comme les autres, pour remplir la table "entite" mais pour remplir la table "import._lookup".
    lookup_entite = MultiColumnLookup(
        conn=conn,
        colid="id_entite",
        columns=("dataset", "id_dataset"),
        table="import._lookup_entite",
        start_id=curval,
    )

    # deux curseurs, pour pouvoir continuer à recevoir des données en même temps qu'on en envoie.
    cur_get = conn.cursor()
    cur_send = conn.cursor()

    # récupère les données de la table import._data, dans laquelle se trouve les JSONs avec les données à importer dans le modèle EAV.
    sql_get = SQL("select j from {}").format(qualify(DATA_TABLE))
    data = (i[0] for i in cur_get.execute(sql_get))

    # construit un statement COPY pour mettre les données "numérisées" (dans laquelle les valeurs textuelles comme 'classe' ou 'type de relation' sont remplacées par des ID numériques).
    sql_copy = make_copy_stmt(DATA_TEMP_TABLE, DATA_TEMP_COLUMNS)

    # numérise les données JSON et place les valeurs de "entite", "relation" et "propriete" dans la table temporaire. il n'est pas possible de les mettres directements dans les tables, car il faut d'abord remplir "classe", "type_propriete", "type_relation".
    with cur_send.copy(sql_copy) as copy:
        for d in data:
            num = numerise_row(
                d,
                lookup_entite=lookup_entite,
                lookup_classe=lookup_classe,
                lookup_type_relation=lookup_type_relation,
                lookup_type_propriete=lookup_type_propriete,
            )
            row = [num[i] for i in DATA_TEMP_COLUMNS]
            copy.write_row([json.dumps(i) for i in row])

    # ajoute dans les tables associées les données nouvelles.
    lookup_classe.copy_to()
    lookup_type_relation.copy_to()
    lookup_type_propriete.copy_to()
    lookup_entite.copy_to()

    # ajoute les entités, les relations, les propriétés. les tables "entité" et "relation" sont les plus simples, car chaque ligne a la même structure: j'utilise donc la méthode COPY. la table "propriété", en revanche, est plus compliquée, car le datatype de la valeur (ou l'absence de valeur) de la propriété détermine la table dans laquelle elle doit être placée, les statement INSERT sont donc construit dynamiquement.
    copy_entites(conn)
    copy_relations(conn)
    insert_toutes_proprietes(conn)

    # fin de la fonction: commit et terminer la connexion.
    conn.commit()
    conn.close()
