import pkgutil


def get_schema_definition(schema: str) -> str:
    if schema not in ("eav", "litteralement"):
        raise ValueError("unknown schema name:", schema)
    else:
        return pkgutil.get_data(
            __name__, f"schemas/{schema}.sql"
        ).decode()

