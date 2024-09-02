import pkgutil


def get_schema_definition(schema_name: str) -> str:
    """print the schema definition.

    args:
        schema_name (str): the name of the schema to be printed.

    returns (str): the schema definition
    """

    if schema_name not in ("eav", "litteralement"):
        raise ValueError("unknown schema name:", schema_name)
    else:
        return pkgutil.get_data(
            __name__, f"schemas/{schema_name}.sql"
        ).decode()
