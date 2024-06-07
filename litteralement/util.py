from psycopg.sql import SQL, Identifier


def make_multi_column_select(tablename, columns):
    """Construit un statement SELECT qui récupère plusieurs colonnes.

    Args:
        tablename (str)
        columns (list)

    Returns (SQL)
    """

    n_columns = len(columns)
    placeholders = " ".join(["{}"] * n_columns)
    query = "select id, {}".format(placeholders)
    query += " from {}"
    query = SQL(query).format(
        *[Identifier(i) for i in columns] + [Identifier(tablename)]
    )
    return query
