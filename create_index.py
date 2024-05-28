"""create/drop des indexes à partir d'un csv."""

import psycopg
import csv
import argparse


# les arguments en ligne de commande
parser = argparse.ArgumentParser(
    description=""""creer ou drop des indexes à partir d'un csv."""
)
parser.add_argument(
    "-d",
    "--drop",
    help="drop les indexes au lieu de les créer",
    type=bool,
    default=False,
)
parser.add_argument(
    "-g",
    "--groups",
    action="store",
    type=list,
    nargs="*",
    help="les groupe d'index à créer/drop.",
    default=[],
)
parser.add_argument(
    "-f",
    "--file",
    action="store",
    help="le fichier csv avec la liste d'index (table,column)",
    type=str,
    default="./indexes.csv",
)
parser.add_argument(
    "-d",
    "--dbname",
    action="store",
    type=str,
    help="le nom de la base de données.",
    default="onscrire",
)
parser.add_argument(
    "-t",
    "--tables",
    action="store",
    type=list,
    nargs="*",
    help="liste de table pour lesquells créer/remplacer les indexes.",
)


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


def create_index(cur, table, column) -> None:
    """crée un index."""

    name = "_".join([table, column, "idx"])
    sql = f"create index {name} on {table} ({column})"
    cur.execute(sql)
    return


def drop_index(cur, table, column) -> None:
    """drop un index."""

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


if __name__ == "__main":
    # parse les arguments en ligne de commande
    args = parser.parse_args()

    # connection à la base de données
    conn = psycopg.connect(f"dbname={args.dbname}")
    cur = conn.cursor()

    # pick la fonction adaptée (create/drop).
    if args.drop is False:
        fn = drop_index
    else:
        fn = create_index

    # récupère la liste des indexes.
    idxs = get_idx_list(file=args.file)
    # filtre les indexes (groupe, tables).
    idxs = filter_idxs(idxs, groups=args.groups, tables=args.tables)

    # applique la fonction sur chaque index retenu.
    for i in idxs:
        fn(cur=cur, table=i["table"], column=i["column"])
