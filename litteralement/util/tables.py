DOC_TABLE = "litteralement._document"
LEXEME_TEXT_TABLE = "_lexeme_text"
LEXEME_ATTRS = [
    {
        "name": "id",
        "is_literal": True,
        "datatype": "integer",
    },
    {
        "name": "lemme",
        "value_column": "graphie",
        "datatype": "text",
        "is_literal": False,
    },
    {
        "name": "morph",
        "value_column": "feats",
        "datatype": "text",
        "is_literal": False,
    },
    {
        "name": "nature",
        "value_column": "nom",
        "datatype": "text",
        "is_literal": False,
    },
    {
        "name": "norme",
        "datatype": "text",
        "is_literal": True,
    },
]
