import json
import tqdm
from psycopg.sql import SQL, Identifier
from . import util


def _copy_from_json(copy, files) -> None:
    """copy from JSON files.

    args:
        copy: the copy object (cursor.copy).
        files: the list of files

    returns (None)
    """

    for file in tqdm.tqdm(files):
        with open(file, "r") as f:
            array = json.load(f)
        for obj in array:
            row = (json.dumps(obj, ensure_ascii=False),)
            copy.write_row(row)


def _copy_from_json_l(copy, files) -> None:
    """copy from JSONL files (one JSON object per line).

    args:
        copy: the copy object (cursor.copy).
        files: the list of files

    returns (None)
    """

    for file in tqdm.tqdm(files):
        with open(file, "r") as f:
            for line in f:
                row = (line.strip(),)
                copy.write_row(row)


def copy_from(conn, files, jsonl=False, noinsert=False):
    """copy from JSON/JSONL files into the database.

    args:
        conninfo (str): the connection strings.
        files (list): list of files.
        jsonl: whether files are JSONL instead of JSON.

    `jsonl` is faster, because files are not parsed.

    returns (None)
    """

    cur = conn.cursor()

    # make the statement
    stmt = "copy {schema}.{table} (j) from stdin"
    stmt = SQL(stmt)
    table = Identifier(util.tables.TABLE_IMPORT)
    schema = Identifier(util.tables.SCHEMA_IMPORT)
    stmt = stmt.format(schema=schema, table=table)

    # copy files (JSON/JSONL)
    with cur.copy(stmt) as copy:
        if jsonl:
            _copy_from_json_l(copy, files)
        else:
            _copy_from_json(copy, files)

    # if argument noinsert is set to True (or not None), then don't insert data in the EAV tables.
    if noinsert:
        return

    # call the procedure that insert data from import table to EAV tables.
    stmt = "call {schema}.importer();"
    stmt = SQL(stmt)
    stmt = stmt.format(schema=schema)
    cur.execute(stmt)
    return
