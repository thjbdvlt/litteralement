import json
from psycopg.sql import SQL, Identifier
import litteralement.util.statements
from litteralement.lookups.database import DatabaseLookup
from litteralement.lookups.database import TryDatabaseLookup
from litteralement.lookups.database import MultiColumnLookup


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


def _insert_lexemes(conn, **kwargs):
    """Ajoute les nouveaux lexèmes.

    Args:
        conn (Connection)

    Optionnel:
        lex_user_attrs (list[dict])

    Les dicts qui se trouvent dans lex_user_attrs doivent avoir le format suivant:
        {"name": "alt_pos", "value_column": "tag", "is_literal": False}
        {"name": "alt_pos", "is_literal": True}
    """

    # la table temporaire pour store les informations des lexèmes.
    temp_lex = Identifier("_lex")
    lexeme = Identifier("lexeme")

    # les attributs (et colonnes) de base des lexèmes.
    lex_attrs = [
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

    # ajouter à ces lexèmes les lexèmes définis par l'utilisateurice
    lex_user_attrs = kwargs.get("lex_user_attrs")
    if lex_user_attrs:
        lex_attrs.extend(lex_user_attrs)

    # # récupère les nouveaux lexèmes, à ajouter.
    # # TODO: récupérer tous les lex_user_attrs!!!
    # sql_nouveau_lexeme = SQL("""
    # create temp table _nouveau_lexeme as
    # with _lexeme_text as
    # (
    #     select
    #         n.nom as nature,
    #         l.graphie as lemme,
    #         m.feats as morph,
    #         x.norme as norme
    #     from lexeme x
    #     join nature n on n.id = x.nature
    #     join morph m on m.id = x.morph
    #     join lemme l on l.id = x.lemme
    # )
    # select lexeme from _mot
    # except
    # select to_jsonb(x) - 'id' from _lexeme_text x;""")
    # conn.execute(sql_nouveau_lexeme)

    # ajoute les lexèmes
    sql_add_lexeme = SQL("""
    create temp table _lex as
        select x.* from _nouveau_lexeme lx, jsonb_to_record(lx.lexeme) as x(
            norme text, 
            lemme text, 
            nature text, 
            morph text, 
            j jsonb
    )""")
    conn.execute(sql_add_lexeme)

    sql_join = SQL("join {table} on {table}.{col} = {table_lex}.{name}")
    sql_select = SQL("{table}.{col} as {name}")

    select_stmts = []
    joins_stmts = []
    columns = []

    reverse_select_stmts = []
    reverse_joins_stmts = []

    for i in lex_attrs:
        name = Identifier(i["name"])
        columns.append(name)
        is_literal = i["is_literal"]

        if is_literal is True:
            col_insert = Identifier(i["name"])
            table = temp_lex

        else:
            col = Identifier(i["value_column"])
            _id = Identifier("id")
            col_insert = _id
            table = name

            join = sql_join.format(
                table=name,
                name=name,
                col=col,
                table_lex=temp_lex,
            )
            joins_stmts.append(join)

            reverse_join = sql_join.format(
                table=name,
                name=name,
                table_lex=Identifier('lexeme'),
                col=_id,
            )
            reverse_joins_stmts.append(reverse_join)

        select = sql_select.format(
            table=table, col=col_insert, name=name
        )
        select_stmts.append(select)
        reverse_select = sql_select.format(
            table=table, col=col, name=name
        )

    # ajoute les propriétés des lexèmes qui sont dans des tables séparées: lemme, nature, morph. (les autres, norme et 'j' ne sont pas des foreign keys mais des valeurs littérales.)
    sql_add_lex_attr = SQL("""
    insert into {tablename} ({col})
    select distinct lexeme ->> %s from _nouveau_lexeme
    except select {col} from {tablename}""")
    for i in lex_attrs:
        if i["is_literal"] is False:
            tablename = i["name"]
            col = i["value_column"]
            stmt = sql_add_lex_attr.format(
                tablename=Identifier(tablename), col=Identifier(col)
            )
            conn.execute(stmt, (tablename,))

    # construit le statement qui ajoute les nouveaux lexèmes, avec les jointures sur les tables foreign keys (lemme, nature, morph, et aussi les user-defined).
    stmt = SQL("""insert into lexeme ({columns})
               select {values}
               from {temp_lex}
               {joins}
    """).format(
        columns=SQL(", ").join(columns),
        temp_lex=temp_lex,
        values=SQL(", ").join(select_stmts),
        joins=SQL("\n").join(joins_stmts),
    )
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
    with _lex as (
        select
            x.id,
            n.nom as nature,
            l.graphie as lemme,
            m.feats as morph,
            x.norme as norme
        from lexeme x
        join nature n on n.id = x.nature
        join morph m on m.id = x.morph
        join lemme l on l.id = x.lemme
    ) select x.id, to_jsonb(x) - 'id' as j from _lex x;""")
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
