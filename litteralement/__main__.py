"""command line interface."""

import argparse
from .util import tables


def cli_connect(args):
    """connect to a database.

    args:
        args (argparse.Namespace): the command line arguments.

    returns (psycopg.Connection): the connection.
    """

    import psycopg

    conninfo = {
        i: getattr(args, i)
        for i in ("dbname", "host", "port", "user", "password")
    }

    conn = psycopg.connect(**conninfo)
    return conn


def cli_copy(args) -> None:
    """copy from files.

    args:
        args (argparse.Namespace): the command line arguments.
    """

    from . import copy

    conn = cli_connect(args)
    copy.copy_from(conn, args.file, args.jsonl)
    conn.commit()
    conn.close()


def cli_annotate(args) -> None:
    """annotate texts using spacy.

    args:
        args (argparse.Namespace): the command line arguments.
    """

    from .nlp import text_annotation
    import spacy

    conn = cli_connect(args)
    nlp = spacy.load(args.model)
    text_annotation.annoter(
        conn=conn,
        nlp=nlp,
        query=args.query,
        batch_size=args.batch_size,
        n_process=args.n_process,
    )
    conn.commit()
    conn.close()


def cli_schema(args) -> None:
    """print schemas definition to stdout.

    args:
        args (argparse.Namespace): the command line arguments.
    """

    from . import schema

    s = schema.get_schema_definition(args.schema_name)
    return s + schema.make_foreign_key(args.text_table)


# command line argument parser
parser = argparse.ArgumentParser()

# subparsers for subcommands (a subcommand is needed)
subparsers = parser.add_subparsers(required=True)
sub_copy = subparsers.add_parser(
    "copy",
    help=f"copy data from files into the {tables.SCHEMA_EAV} schema tables.",
)
sub_schema = subparsers.add_parser(
    "schema",
    help="print the definition of a schema to STDOUT.",
)
sub_annotate = subparsers.add_parser(
    "annotate",
    help=f"annotate texts using spacy and insert the resulting annotations into the tables of the schema {tables.SCHEMA}",
)
sub_join = subparsers.add_parser(
    "join-schema",
    help='generate the SQL commands to create referencing constraints (for the tables "mot", "token", "phrase", "span" and "segment"). it is only usefull if a database already has the schema "litteralement" and this schema is not referencing the table containing texts.',
)

parser.set_defaults(func=lambda i: None)
sub_copy.set_defaults(func=cli_copy)
sub_annotate.set_defaults(func=cli_annotate)
sub_schema.set_defaults(func=cli_schema)

ARG_TABLE_HELP = 'the table containing texts, referenced by tables "mot", "phrase", "span", "segment" and "token". this is used to create referencing constraint.'
ARG_TABLE_METAVAR = "SCHEMA.TABLE.PK"

# arguments for connection are shared between multiples subcommands.
for p in (sub_annotate, sub_copy):
    conninfo = p.add_argument_group("conninfo")
    conninfo.add_argument(
        "-d", "--dbname", action="store", required=True
    )
    for low, long in (
        ("-p", "--port"),
        ("-H", "--host"),
        ("-U", "--user"),
        ("-P", "--password"),
    ):
        conninfo.add_argument(low, long, action="store", required=False)

# sub-command "copy"
sub_copy.add_argument(
    "file",
    nargs="+",
    help="files to copy data from (JSON/JSONL).",
)
sub_copy.add_argument(
    "-l",
    "--jsonl",
    action="store_true",
    default=False,
    required=False,
    help="use JSONL file format (one objet per line) instead of JSON.",
)

# sub-command "schema"
sub_schema.add_argument(
    "schema-name",
    choices=(tables.SCHEMA_EAV, tables.SCHEMA, "both"),
    nargs="?",
    action="store",
    help="name of the schema to be output.",
    default="both",
)

sub_schema.add_argument(
    "-t",
    "--text-table",
    help=ARG_TABLE_HELP,
    type=str,
    action="store",
    metavar=ARG_TABLE_METAVAR,
)

# sub-command "join"
sub_join.add_argument(
    "table",
    nargs=1,
    metavar=ARG_TABLE_METAVAR,
    help=ARG_TABLE_HELP,
)

# sub-command "annotate"
sub_annotate.add_argument(
    "-q",
    "--query",
    metavar="QUERY",
    action="store",
    required=True,
    help="the SQL SELECT query to get texts. the query must returns two rows: one for the text id (int), and one for the text content (text). the special value 'all' can be used to annotate all unanotated texts in the table \"text\".",
)
sub_annotate.add_argument(
    "-m",
    "--model",
    action="store",
    required=True,
    help="local path or name of the model. e.g. 'fr_core_news_lg' or './path/to/my/model/'.",
)
group_spacy = sub_annotate.add_argument_group("spacy")
group_spacy.add_argument("--n-process", type=int, required=False)
group_spacy.add_argument("--batch-size", type=int, required=False)


def main():
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
