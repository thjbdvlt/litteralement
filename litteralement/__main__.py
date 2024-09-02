import argparse


if __name__ == "__main__":
    # command line argument parser
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command",
        choices=("schema", "annotate", "copy", "join-schema"),
    )

    # copy
    group_copy = parser.add_argument_group("copy")
    group_copy.add_argument(
        "file",
        nargs="+",
        help="files to copy data from (JSON/JSONL).",
    )
    group_copy.add_argument(
        "-l",
        "--jsonl",
        actions="store_true",
        default=False,
        required=False,
        help="use jsonl file format (one objet per line).",
    )

    # print schema
    group_schema = parser.add_argument_group("print-schema")
    group_schema.add_argument(
        "schema",
        choices=(
            "eav",
            "litteralement",
            "both",
        ),
        nargs=1,
        action="store",
        help='schema to be output: "eav", "litteralement" or both.',
    )
    group_schema.add_argument(
        "-t",
        "--text",
        help='the table containing texts, referenced by tables "mot", "phrase", "span", "segment" and "token". this is used to create referencing constraint.',
        type=str,
        action="store",
        metavar="SCHEMA.TABLE.ID_COLUMN",
    )

    # join-schema
    group_join = parser.add_argument_group("join-schema")
    group_join.add_argument(
        "table",
        nargs=1,
        help='the table containing texts, referenced by tables "mot", "phrase", "span", "segment" and "token". this is used to create referencing constraint.',
    )


# litteralement schema generate
# litteralement schema join
# litteralement annotate ...
# litteralement insert ... [--query QUERY]
