import json
from psycopg.sql import SQL, Identifier
from litteralement.util.statements import make_copy_stmt
from litteralement.util.statements import qualify
from litteralement.lookups.database import TryDatabaseLookup
from litteralement.lookups.database import MultiColumnLookup


DATA_TABLE = "import._data"
DATA_TEMP_TABLE = "_temp_data"
DATA_TEMP_COLUMNS = ("entites", "relations", "proprietes")


def _create_data_temp_table(conn):
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


def _numerise_entite(
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

    # l'id de l'entité dans le dataset
    id_dataset = entite["id"]

    # le nom de sa classe
    classe = entite["classe"]

    # la 'Key' qui permet d'obtenir, dans la lookup table, l'identifiant de l'entité dans la base de données, est composée de l'id du dataset et de l'id de l'entité dans le dataset.
    key = lookup_entite.Key(
        **{"dataset": dataset, "id_dataset": id_dataset}
    )

    # récupère l'id de l'entité dans la database
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


def _numerise_relation(
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

    # récupère l'id du type de relation.
    type_relation = lookup_type_relation[relation["type"]]

    d = {"type": type_relation}

    # récupère les ids des sujet et objets de la relation.
    for i in ("sujet", "objet"):
        key = lookup_entite.key_from_dict_strict(
            {"dataset": dataset, "id_dataset": relation[i]}
        )
        d[i] = lookup_entite[key]

    return d


def _table_val_from_datatype(val):
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


def _numerise_row(data, **kwargs):
    """Numerise un ensemble de données (entités et relations).

    Args:
        data (dict):  les données, avec les clés "entites", "dataset", "relations".

    Returns (tuple):  (entites, relations, proprietes)
    """

    # l'id du dataset, qui permet de mettre en relations les entités.
    dataset = data["dataset"]

    # récupère les relations.
    relations = [
        _numerise_relation(i, dataset, **kwargs)
        for i in data["relations"]
    ]

    # récupère les relations incomplète dans les entités.
    for i in data["entites"]:
        if "relations" in i:
            entites_relations = []
            for rel in i.pop("relations"):
                rel["sujet"] = i["id"]
                entites_relations.append(rel)
    relations.extend(entites_relations)

    # numérise les entités (trouve les id dans la database).
    entites = [
        _numerise_entite(i, dataset, **kwargs) for i in data["entites"]
    ]

    # récupère les propriétés des entités.
    proprietes = []
    for i in entites:
        proprietes.extend(i.pop("proprietes"))

    # reconstruit le nouveau dict
    d = {
        "entites": entites,
        "relations": relations,
        "proprietes": proprietes,
    }
    return d


def _copy_from_temp(conn, table, columns, source_column):
    """COPY depuis la table temporaire vers une autre table.

    Args:
        conn (Connection)
        table (str):  la table cible.
        columns (list[str]):  les colonnes cibles.
        source_column (str):  la colonne dans la TEMP TABLE.
    """

    # deux curseurs pour envoyer et recevoir simultanément.
    cur_send = conn.cursor()
    cur_get = conn.cursor()

    # construire le statement COPY qui cherche une colonne dans la TEMP TABLE.
    copy_sql = make_copy_stmt(table, columns)
    sql_get = SQL("select distinct {} from {}").format(
        Identifier(source_column), Identifier(DATA_TEMP_TABLE)
    )

    # récupérer les données.
    data = (i[0] for i in cur_get.execute(sql_get))

    # copier les données dans la table.
    with cur_send.copy(copy_sql) as copy:
        for row in data:
            for e in row:
                copy.write_row([e[i] for i in columns])


def _copy_entites(conn):
    """Copie les entités depuis la table temporaire.

    Args:
        conn (Connection)
    """

    columns = ("id", "classe")
    source_column = "entites"
    table = "entite"
    _copy_from_temp(conn, table, columns, source_column)


def _copy_relations(conn):
    """Copie les relations depuis la table temporaire.

    Args:
        conn (Connection)
    """

    columns = ("type", "sujet", "objet")
    source_column = "relations"
    table = "relation"
    _copy_from_temp(conn, table, columns, source_column)


def _insert_une_propriete(cursor, d):
    """Construit un INSERT statement en fonction du type de données.

    Args:
        val (Any): la valeur, qui détermine la table.

    Returns (SQL): le INSERT statement.
    """

    # la table dépend du datatype de la valeur.
    table = _table_val_from_datatype(d["val"])

    # le colonnes dépendent de la table.
    columns = (
        ("entite", "type")
        if table == "propriete"
        else ("entite", "type", "val")
    )

    # si le datatype est JSONB, il faut le sérialiser.
    if table == "prop_jsonb":
        d["val"] = json.dumps(d["val"])

    # le nombre de placeholders dépend du nombre de colonnes.
    placeholders = ", ".join(["%s" for i in columns])

    # construction du statement
    stmt = f"insert into {{}} ({{}}) select {placeholders}"
    sql_table = Identifier(table)
    sql_columns = SQL(", ").join([Identifier(i) for i in columns])
    sql_stmt = SQL(stmt).format(sql_table, sql_columns)

    # la ROW est construite dynamiquement, on fonction du nombre de colonnes.
    row = [d[i] for i in columns]

    # exécute le statement d'insertion
    cursor.execute(sql_stmt, row)


def _insert_toutes_proprietes(conn):
    """Insère toutes les propriétés depuis la TEMP TABLE.

    Args:
        conn (Connection)
    """

    # récupère les propriétés dans la TEMP TABLE.
    sql_get = "select distinct proprietes from " + DATA_TEMP_TABLE
    data = (i[0] for i in conn.execute(sql_get))

    # insérer les propriétés
    cur_send = conn.cursor()
    for row_source in data:
        for d in row_source:
            _insert_une_propriete(cur_send, d)


def importer(conn):
    """Insère dans les tables EAV ce qui se trouve dans import._data.

    Args:
        dbname (str)
    """

    _create_data_temp_table(conn)

    # récupère l'id actuel de la table "entite".
    curval = conn.execute("select nextval('entite_id_seq')").fetchone()[
        0
    ]

    # construit les lookups (qui remplissent une fonction de  "join").
    lookup_classe = TryDatabaseLookup(conn, "onto.classe")
    lookup_type_relation = TryDatabaseLookup(conn, "onto.type_relation")
    lookup_type_propriete = TryDatabaseLookup(
        conn, "onto.type_propriete"
    )
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
            if "dataset" not in d:
                d["dataset"] = conn.execute(
                    "select max(dataset)+1 from import._lookup_entite;"
                )
            num = _numerise_row(
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
    _copy_entites(conn)
    _copy_relations(conn)
    _insert_toutes_proprietes(conn)

    # fin de la fonction: commit et terminer la connexion.
    conn.commit()
