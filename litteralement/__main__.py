import argparse
from .util import tables


if __name__ == "__main__":
    # command line argument parser
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command",
        choices=("schema", "annotate", "copy", "join-schema"),
    )

    # subparser for subcommands
    subparsers = parser.add_subparsers()
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
        "join",
        help='generate the SQL commands to create referencing constraints (for the tables "mot", "token", "phrase", "span" and "segment"). it is only usefull if a database already has the schema "litteralement", but that schema is not referencing the table containing texts.',
    )

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
        help="use jsonl file format (one objet per line).",
    )

    # print schema
    sub_schema.add_argument(
        "name",
        choices=(tables.SCHEMA_EAV, tables.SCHEMA, "both"),
        nargs="?",
        action="store",
        help="name of the schema to be output.",
        default="both",
    )
    sub_schema.add_argument(
        "-t",
        "--text-table",
        help='the table containing texts, referenced by tables "mot", "phrase", "span", "segment" and "token". this is used to create referencing constraint.',
        type=str,
        action="store",
        metavar="SCHEMA.TABLE.PK",
    )

    # join-schema
    group_join = parser.add_argument_group("join-schema")
    group_join.add_argument(
        "table",
        nargs=1,
        help='the table containing texts, referenced by tables "mot", "phrase", "span", "segment" and "token". this is used to create referencing constraint.',
    )

    # annotate
    group_annotate = parser.add_argument_group("annotate")

    args = parser.parse_args()
    # print(args)


# litteralement schema generate
# litteralement schema join
# litteralement annotate ...
# litteralement insert ... [--query QUERY]
