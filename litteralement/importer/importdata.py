from psycopg.sql import SQL, Identifier
from litteralement.statements import make_copy_stmt


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


def insert_propriete(propriete):
    """Insère une propriété.

    Args:
        propriete (dict)
    """

    table = table_val_from_datatype(propriete["val"])
    base_stmt = "insert into {} ({}) values %s"
    query = SQL(base_stmt).format(Identifier(table))
    return query


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
    """Copie les entités depuis la table temporaire.

    Args:
        conn (Connection)
    """

    columns = ("type", "sujet", "objet")
    source_column = "relations"
    table = "relation"
    copy_from_temp(conn, table, columns, source_column)
