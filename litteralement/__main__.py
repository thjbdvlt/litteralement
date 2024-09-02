import argparse
from . import sql


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command",
        choices=("generate-schema", "join-schema", "annotate", "copy"),
    )
    parser.add_argument(
        "-s",
        "--schema",
        type=str,
        choices=("litteralement", "eav"),
        nargs=2,
    )
    parser.add_argument(
        "-t",
        "--text",
        type=str,
        nargs="?",
    )
    schema = sql.get_schema_definition()

# litteralement schema generate
# litteralement schema join
# litteralement annotate ...
# litteralement insert ... [--query QUERY]
