import pkgutil
from .util import tables
from psycopg.sql import SQL, Identifier


_fk_stmt = """alter table {schema_li}.{table_li}
add constraint {constraint_name} foreign key (texte)
references {{schema_text}}.{{table_text}} ({{pk_text}});
"""
FK_STMT = ""
for i in tables.FK_TEXT_TABLES:
    FK_STMT += (
        _fk_stmt.format(
            schema_li=tables.SCHEMA,
            table_li=i,
            constraint_name=f"{i}_texte_fk",
        )
        + "\n"
    )


def _get(filename):
    """get the content of a SQL file in the data directory."""

    return pkgutil.get_data(__name__, f"data/{filename}.sql").decode()


def get_schema_definition(name: str) -> str:
    """print the schema definition.

    args:
        schema_name (str): the name of the schema to be printed.

    returns (str): the schema definition
    """

    schemas = (tables.SCHEMA, tables.SCHEMA_EAV)

    if name not in schemas:
        raise ValueError("unknown schema name:", name)
    elif name == "both":
        return "\n\n".join([_get(i) for i in schemas])
    else:
        return _get(name)


def make_foreign_key(text_table='eav.texte.id') -> str:
    """generate the foreign key.

    args:
        text_table (str): SCHEMA.TABLE.PK (e.g. public.texte.id)

    returns (str): the sql statement.
    """

    fk = text_table.strip().split(".")
    try:
        assert len(fk) == 3
    except AssertionError:
        raise ValueError(
            "couldn't parse: ", text_table, "\n\n(SCHEMA.TABLE.PK)"
        )

    fk = [Identifier(i) for i in fk]
    schema, table, pk = fk
    s = SQL(FK_STMT).format(schema=schema, table=table, pk=pk)
    return str(s)
