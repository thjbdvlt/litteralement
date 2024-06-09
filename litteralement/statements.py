from psycopg.sql import SQL, Identifier


def qualify(table):
    """Nom de table et schéma si inclut."""

    if not isinstance(table, str):
        return Identifier(*table)
    elif "." in table:
        return Identifier(*(table.split(".")))
    else:
        return Identifier(table)


def make_multi_column_select(table, columns):
    """Construit un statement SELECT qui récupère plusieurs colonnes.

    Args:
        table (str)
        columns (list)

    Returns (SQL)
    """

    sql_columns = SQL(", ").join([Identifier(i) for i in columns])
    sql_table = qualify(table)
    query = SQL("select {} from {}").format(sql_columns, sql_table)
    return query


def copy_to_multicolumns(table, columns):
    """Construit un statement COPY TO avec plusieurs colonnes.

    Args:
        table (str)
        columns (list)

    Returns (SQL)
    """

    sql_table = qualify(table)
    sql_columns = SQL(", ").join([Identifier(i) for i in columns])
    query = SQL("copy {} ({}) from stdin").format(
        sql_table, sql_columns
    )
    return query
