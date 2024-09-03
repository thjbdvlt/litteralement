import pkgutil
from .util import tables


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
