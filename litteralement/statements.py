from psycopg.sql import SQL, Identifier


def make_multi_column_select(tablename, columns):
    """Construit un statement SELECT qui récupère plusieurs colonnes.

    Args:
        tablename (str)
        columns (list)

    Returns (SQL)
    """

    sql_select = SQL("select ")
    sql_columns = SQL(", ").join([Identifier(i) for i in columns])
    sql_table = SQL("from {}").format(Identifier(tablename))
    query = sql_select + sql_columns + sql_table
    return query


def copy_to_multicolumns(table, columns):
    """Construit un statement COPY TO avec plusieurs colonnes.

    Args:
        tablename (str)
        columns (list)

    Returns (SQL)
    """

    sql_table = Identifier(table)
    sql_columns = SQL(", ").join([Identifier(i) for i in columns])
    query = SQL("copy {} ({}) from stdin").format(
        sql_table, sql_columns
    )
    return query
