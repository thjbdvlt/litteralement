import csv


def get_idx_list(file=None):
    """Récupère la liste des indexes dans un csv.

    Args:
        file (str):  chemin vers un fichier.

    Returns (list[dict])

    Format du CSV:
        Trois champs requis: table,column,group.
        Le header est optionnel (la fonction l'enlève s'il est là).
    """

    if file is None:
        import os

        # le fichier par défaut
        file = os.path.join(
            os.path.dirname(os.path.realpath(__file__)), "indexes.csv"
        )

    with open(file) as f:
        r = csv.reader(f, delimiter=",")
        # construit un dictionnaire à partir du csv
        idx = [
            {"table": row[0], "column": row[1], "group": row[2]}
            for row in r
        ]

    # enlève le header s'il y en a un
    if idx[0]["table"] == "table" and idx[0]["column"] == "column":
        idx = idx[1:]

    return idx


def create_index(conn, table, column) -> None:
    """Crée un index.

    Args:
        conn (Connection)
        table (str)
        column (str)
    """

    cur = conn.cursor()
    name = "_".join([table, column, "idx"])
    sql = f"create index {name} on {table} ({column})"
    cur.execute(sql)


def drop_index(conn, table, column) -> None:
    """Drop un index.
    Args:
        conn (Connection)
        table (str)
        column (str)
    """

    cur = conn.cursor()
    name = "_".join([table, column, "idx"])
    sql = f"drop index {name}"
    cur.execute(sql)


def filter_idxs(idxs, groups, tables):
    """Filtre les indexes à créer/drop.

    Args:
        idxs (list):  la liste des indexes
        groups (list):  liste de groupes
        tables (list):  liste de tables
    """

    if len(groups) == len(tables) == 0:
        return idxs
    else:
        return [
            i
            for i in idxs
            if i["group"] in groups or i["table"] in tables
        ]
