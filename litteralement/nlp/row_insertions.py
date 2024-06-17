import json
from psycopg.sql import SQL, Identifier
import litteralement.util.statements
from litteralement.util.statements import select_values_fk
from litteralement.lookups.database import DatabaseLookup
from litteralement.lookups.database import TryDatabaseLookup
from litteralement.lookups.database import MultiColumnLookup


LEXEME_TEXT_TABLE = "_lexeme_text"

TOKEN = {
    "table": "nlp.token",
    "key": "nonmots",
    "columns": ["debut", "fin", "num"],
}
MOT = {
    "table": "nlp.mot",
    "key": "mots",
    "columns": ["debut", "fin", "num", "noyau", "lexeme", "fonction"],
}
PHRASE = {
    "table": "nlp.phrase",
    "key": "phrases",
    "columns": ["debut", "fin"],
}
SPAN = {
    "table": "nlp.span",
    "key": "spans",
    "columns": ["debut", "fin"],
}

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


def _copy_from_temp(conn, table, key, columns):
    """Copier dans les tables depuis la table temporaire.

    Args:
        conn (Connection):  la connection à la base de données.
        table (str):  le nom de la table.
        key (str):  la clé du types d'éléments dans le doc.
        columns (list[str]):  la liste de colonnes (et clés d'éléments.)
    """

    # deux curseurs: un pour recevoir, l'autre pour envoyer (en même temps).
    cur_get = conn.cursor()
    cur_send = conn.cursor()

    # la requête pour prendre depuis les docs (table temporaires).
    sql_get = SQL("select id, j from _temp_doc")

    # construire la requête pour envoyer avec colonnes multiples.
    sql_copy_send = litteralement.util.statements.copy_to_multicolumns(
        table=table,
        columns=["texte"] + columns,
    )

    # récupérer les docs.
    docs = cur_get.execute(sql_get)

    # copier les éléments dans la table.
    with cur_send.copy(sql_copy_send) as copy:
        for i in docs:
            textid = i[0]  # l'id du texte, commun à mot/token/phrase
            doc = i[1]  # le doc
            for x in doc[key]:
                # construire des tuples, et les ajouter à l'id du texte.
                row = tuple((x[c] for c in columns))
                copy.write_row((textid,) + row)


def _inserer_lookups(conn, add_word_attrs=[], add_span_attrs=[]):
    """Ajoute les import._documents dans les tables.

    Args:
        conn (Connection)
    """

    # créer des tables lookups pour les ids.
    lookup_lemma = DatabaseLookup(conn, "nlp.lemme", colname="graphie")
    lookup_pos = TryDatabaseLookup(conn, "nlp.nature")
    lookup_dep = TryDatabaseLookup(conn, "nlp.fonction")
    lookup_morph = TryDatabaseLookup(conn, "nlp.morph", colname="feats")
    lookup_lex = MultiColumnLookup(
        conn=conn,
        table="nlp.lexeme",
        colid="id",
        columns=["lemme", "norme", "nature", "morph"],
    )

    # créer une table temporaire à partir de laquelle exécuter les 'copy', et dans laquelle vont aller les mots, tokens, ..., avec les IDs pour remplacer les textes (des POS, DEP, MORPH, etc.).
    conn.execute("create temp table _temp_doc (id int, j jsonb);")

    # deux curseurs: un pour envoyer les données, l'autre pour recevoir: je fais ça en même temps (avec des Generator).
    cur_get = conn.cursor()
    cur_send = conn.cursor()

    def numerize_lex(lex):
        """Numerise les lexèmes.

        Args:
            lex (dict):  le dict décrivant le lexème.

        Returns (int):  l'id du lexème.

        Durant le processus, les POS (nature), DEP (fonction) et LEMMA (lemme) sont aussi analysés. ils sont ajoutés dans leurs tables lookups respectives, à partir desquelles ils seront ajoutés dans la base de données.
        """

        for (
            tag,
            lookup,
        ) in (
            ("nature", lookup_pos),
            ("lemme", lookup_lemma),
            ("morph", lookup_morph),
        ):
            val = lex[tag]
            lex[tag] = lookup[val]
        key = lookup_lex.key_from_dict(lex)
        _id = lookup_lex[key]
        return _id

    def numerize_mot(word):
        """Numérise un mot."""

        dep = lookup_dep[word["fonction"]]
        lex = numerize_lex(word["lexeme"])
        head = word["noyau"]
        word.update(
            {
                "lexeme": lex,
                "fonction": dep,
                "noyau": head,
            }
        )
        return word

    def numerize_doc():
        """Numerize les composants des docs."""

        docs = cur_get.execute(
            "select id, j from import._document limit 1000;"
        )
        with cur_send.copy("copy _temp_doc (id, j) from stdin") as copy:
            for i in docs:
                _id = i[0]
                j = i[1]
                words = j["mots"]
                for word in words:
                    _ = numerize_mot(word)
                copy.write_row(
                    (
                        _id,
                        json.dumps(j),
                    )
                )

    # numériser les docs.
    numerize_doc()

    # ajouter les morphologie, nature, fonctions, lemmes, dans les tables respectives.
    lookup_morph.copy_to()
    lookup_pos.copy_to()
    lookup_dep.copy_to()
    lookup_lemma.copy_to()

    # l'ordre est important: la table 'lexeme' dépend de 'morph', 'pos', 'lemma'. et la table 'mot' dépend de 'dep'.
    lookup_lex.copy_to()

    # copier les mots, tokens, phrases dans les tables respectives. (avec ajout des propriétés user-defined.)
    for obj, attrs in [
        (TOKEN, []),
        (MOT, add_word_attrs),
        (PHRASE, add_span_attrs),
        (SPAN, add_span_attrs),
    ]:
        obj["columns"].extend(attrs)
        _copy_from_temp(conn, **obj)

    # commit et clore la connection: fin de la fonction.
    conn.commit()
    conn.close()


def add_user_defined_columns(conn, table, userattrs):
    """Ajoute les colonnes et tables nécessaires aux attributs user-defined.

    Args:
        conn (Connection)
        table (str, Identifier)
        userattrs (list[dict])

    Format de 'userattrs':
        [
            {"name": "my_pos", "is_literal": True, "datatype": "text"},
            {"name": "my_morph", "is_literal": False, "value_column": "feats", "datatype": "text"},
        ]
        - 'is_literal' définit si la valeur d'une colonne est une valeur littérale, ou une référence (fk) vers une autre table.
        - 'value_column' n'est utile que si 'is_literal' est False: c'est le nom de la colonne contenant, dans la table de référence, la valeur littérale (la colonne référencée est toujours "id").
        - 'name' contient le nom de l'attribut: c'est le nom de la colonne dans la table, et aussi le nom de la table de référence si 'is_literal' est False.
        - 'datatype' contient le datatype (text, jsonb, integer, etc).
    """

    if isinstance(table, str):
        table = Identifier(table)

    for i in userattrs:
        name = Identifier(i["name"])
        datatype = SQL(i["datatype"])

        if i["is_literal"] is True:
            # s'il s'agit d'une colonne littérale, il suffit d'ajouter la colonne.

            s = SQL("alter table {} add column if not exists {} {}")
            s = s.format(table, name, datatype)
            conn.execute(s)

        else:
            # s'il s'agit d'une valeur référencée dans une autre table:
            # 1. création de la table avec deux colonnes, 'id' et une colonne contenant la valeur (value_column).
            # 2. ajout de la colonne référençant cette nouvelle table.

            value_column = Identifier(i["value_column"])

            s = SQL(
                "create table if not exists {table} (id integer primary key generated by default as identity, {col} {datatype})"
            )
            s = s.format(
                table=name, col=value_column, datatype=datatype
            )
            conn.execute(s)

            s = SQL(
                "alter table {} add column if not exists {} integer references {} (id)"
            )
            s = s.format(table, name, name)
            conn.execute(s)


def _insert_lexemes(conn, lex_user_attrs=None, **kwargs):
    """Ajoute les nouveaux lexèmes.

    Args:
        conn (Connection)

    Optionnel:
        lex_user_attrs (list[dict])

    Les dicts qui se trouvent dans lex_user_attrs doivent avoir le format suivant:
        {"name": "alt_pos", "value_column": "tag", "is_literal": False, "datatype": "text"}
        {"name": "alt_pos", "is_literal": True; "datatype": "text"}
    """

    # la table temporaire pour store les informations des lexèmes.
    lexeme_text = Identifier(LEXEME_TEXT_TABLE)

    # les attributs (et colonnes) de base des lexèmes.
    lex_attrs = [i for i in LEXEME_ATTRS]

    # ajouter à ces lexèmes les lexèmes définis par l'utilisateurice
    if lex_user_attrs:
        userattrs = lex_user_attrs
        lex_attrs.extend(userattrs)

    # ajoute les colonnes et tables supplémentaires.
    add_user_defined_columns(conn, "lexeme", userattrs)

    # une vue pour les lexemes-text (avec les valeurs, et pas les fk).
    s = SQL("""drop view if exists {}; create view {} as """)
    s = s.format(lexeme_text, lexeme_text)
    s += select_values_fk("lexeme", lex_attrs)
    conn.execute(s)

    # table temporaire avec uniquement les nouveaux lexèmes.
    sql_reverse = SQL("""create temp table _nouveau_lexeme as
    select lexeme from _mot
    except
    select to_jsonb(x) - 'id' from {lextext} x
    """).format(lextext=lexeme_text)

    conn.execute(sql_reverse)

    # construire la description des fields à récupérer dans le JSONB
    # (nom et datatype)
    fields = [(i["name"], i["datatype"]) for i in lex_attrs]
    fields = [(Identifier(i[0]), SQL(i[1])) for i in fields]
    fields = [SQL(" ").join(i) for i in fields]
    fields = SQL(",\n").join(fields)

    # déplier les JSONB: récupérer les lexèmes dans les Docs.
    sql_add_lexeme = SQL("""create temp table _lex as
    select 
        x.* 
    from _nouveau_lexeme lx, 
        jsonb_to_record(lx.lexeme) as x(
            {fields}
        )
    """)
    sql_add_lexeme = sql_add_lexeme.format(fields=fields)
    conn.execute(sql_add_lexeme)

    # ajoute les propriétés des lexèmes qui sont dans des tables séparées: lemme, nature, morph. (les autres, norme et 'j' ne sont pas des foreign keys mais des valeurs littérales.)
    sql_add_lex_attr = SQL("""
    insert into {tablename} ({col})
    select distinct lexeme ->> %s from _nouveau_lexeme
    except select {col} from {tablename}
    """)

    # ajouter les valeurs dans les tables FK.
    for i in lex_attrs:
        if i["is_literal"] is False:
            tablename = i["name"]
            column_value = i["value_column"]
            stmt = sql_add_lex_attr.format(
                tablename=Identifier(tablename),
                col=Identifier(column_value),
            )
            conn.execute(stmt, (tablename,))

    # construit le statement qui ajoute les nouveaux lexèmes, avec les jointures sur les tables foreign keys (lemme, nature, morph, et aussi les user-defined).
    insert_columns = [i["name"] for i in lex_attrs if i["name"] != "id"]
    insert_columns = map(Identifier, insert_columns)
    insert_columns = SQL(", ").join(insert_columns)

    stmt = SQL("insert into lexeme ({columns})").format(
        columns=insert_columns
    )
    attrs = [i for i in lex_attrs if i["name"] != "id"]
    stmt += select_values_fk("_lex", attrs, rev=True)
    conn.execute(stmt)


def _insert_mots(conn, **kwargs):
    """Ajoute les mots et objets dérivés (pos, lexèmes, ...).

    Args:
        conn (Connection)
    """

    # ajouter les tags de fonction manquants
    sql_add_dep_tag = SQL("""with _mot as (
        select 
        x.fonction
        from import._document d,
        jsonb_to_recordset(d.j -> 'mots') as x(fonction text)
    ) 
    insert into fonction (nom)
    select distinct * from _mot
    except select nom from fonction""")
    conn.execute(sql_add_dep_tag)

    # crée une table temporaire pour les mots
    sql_temp_mot = SQL("""create temp table _mot as
    select 
        d.id as texte,
        f.id as fonction,
        x.debut,
        x.fin,
        x.num,
        x.lexeme,
        x.noyau
    from import._document d,
    jsonb_to_recordset(d.j -> 'mots') as x (
        fonction text,
        debut int, 
        fin int, 
        num int, 
        lexeme jsonb, 
        noyau int
    ) join fonction f on x.fonction = f.nom""")
    conn.execute(sql_temp_mot)

    _insert_lexemes(conn, **kwargs)

    # crée une table lookup avec deux colonnes: les IDs des lexèmes et leur représentations (textuelle) en JSONB (similaire à celle dans les mots).
    sql_lex_id_jsonb = SQL("""
    create temp table id_jsonb_lex as
    select x.id, to_jsonb(x) - 'id' as j from _lexeme_text x;""")
    conn.execute(sql_lex_id_jsonb)

    # ajoute les mots
    sql_add_mot = SQL("""
    insert into mot (texte, debut, fin, num, noyau, fonction, lexeme)
    select
        m.texte,
        m.debut,
        m.fin,
        m.num,
        m.noyau,
        m.fonction,
        x.id
    from _mot m
    join id_jsonb_lex x on x.j = m.lexeme;""")
    conn.execute(sql_add_mot)


def _insert_phrases(conn, **kwargs):
    """Ajoute les phrases depuis les annotations.

    Args:
        conn (Connection)
    """

    sql_add_phrase = SQL("""
        insert into phrase
        select
            d.id as texte,
            x.debut,
            x.fin
        from import._document d,
        jsonb_to_recordset(d.j -> 'phrases') as x(
            debut integer, fin integer
        );""")
    conn.execute(sql_add_phrase)


def _insert_tokens(conn, **kwargs):
    """Ajoute les tokens depuis les annotations.

    Args:
        conn (Connection)
    """

    sql_add_token = SQL("""
        insert into token
        select
            d.id as texte,
            x.debut,
            x.fin,
            x.num
        from import._document d,
        jsonb_to_recordset(d.j -> 'nonmots') as x(
            debut integer, fin integer, num integer
        );""")
    conn.execute(sql_add_token)


def _insert_spans(conn, **kwargs):
    """Ajoute les spans depuis les annotations.

    Args:
        conn (Connection)
    """

    sql_add_span = SQL("""
        insert into span
        select
            d.id as texte,
            x.debut,
            x.fin,
            x.attrs
        from import._document d,
        jsonb_to_recordset(d.j -> 'spans') as x(
            debut integer, fin integer, attrs jsonb
        );""")
    conn.execute(sql_add_span)


def inserer(conn, **kwargs):
    """Ajoute les annotations dans les tables.

    Args:
        conn (Connection)
    """

    _insert_mots(conn, **kwargs)
    _insert_tokens(conn, **kwargs)
    _insert_spans(conn, **kwargs)
    _insert_phrases(conn, **kwargs)

    conn.commit()
    conn.close()
