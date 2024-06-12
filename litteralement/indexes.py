"""create/drop des indexes à partir d'un csv."""

import csv


def get_idx_list(file=None):
    """récupère la liste des indexes dansun csv.

    trois champs requis: table,column,group.
    le header est optionnel (la fonction l'enlève s'il est là).
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
    """crée un index."""

    cur = conn.cursor()
    name = "_".join([table, column, "idx"])
    sql = f"create index {name} on {table} ({column})"
    cur.execute(sql)
    return


def drop_index(conn, table, column) -> None:
    """drop un index."""

    cur = conn.cursor()
    name = "_".join([table, column, "idx"])
    sql = f"drop index {name}"
    cur.execute(sql)
    return


def filter_idxs(idxs, groups, tables):
    """filtre les indexes à créer/drop."""

    if len(groups) == len(tables) == 0:
        return idxs
    else:
        [
            i
            for i in idxs
            if i["group"] in groups or i["table"] in tables
        ]
    return
