from psycopg.sql import SQL, Identifier
from litteralement.util.statements import select_values_fk
from litteralement.util.statements import qualify
from litteralement.util.tables import DOC_TABLE
from litteralement.util.tables import LEXEME_ATTRS
from litteralement.util.tables import LEXEME_TEXT_TABLE
from litteralement.util.tables import SCHEMA


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
        # table = Identifier(table)
        table = qualify(table)

    for i in userattrs:
        # name = Identifier(i["name"])
        name = qualify(i["name"])
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

            s = SQL("""create table if not exists {table} 
            (id integer primary key generated by default as identity,
            {col} {datatype}
            )""")
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

    # les attributs (et colonnes) de base des lexèmes. (copie)
    lex_attrs = [{k: v for k, v in i.items()} for i in LEXEME_ATTRS]

    # ajouter à ces lexèmes les lexèmes définis par l'utilisateurice. créer aussi les colonnes et tables correspondantes.
    if lex_user_attrs:
        lex_attrs.extend(lex_user_attrs)
        add_user_defined_columns(
            conn, f"{SCHEMA}.lexeme", lex_user_attrs
        )

    # une vue pour les lexemes-text (avec les valeurs, et pas les fk).
    s = SQL("""drop view if exists {}; create view {} as """)
    s = s.format(lexeme_text, lexeme_text)
    s += select_values_fk(f"{SCHEMA}.lexeme", lex_attrs)
    conn.execute(s)

    # table temporaire avec uniquement les nouveaux lexèmes.
    s_rev = SQL("""create temp table _nouveau_lexeme as
    select lexeme from _mot
    except
    select to_jsonb(x) - 'id' from {lextext} x
    """)
    s_rev = s_rev.format(lextext=lexeme_text)
    conn.execute(s_rev)

    # construire la description des fields à récupérer dans le JSONB
    # (nom et datatype)
    fields = [(i["name"], i["datatype"]) for i in lex_attrs]
    fields = [(Identifier(i[0]), SQL(i[1])) for i in fields]
    fields = [SQL(" ").join(i) for i in fields]
    fields = SQL(",\n").join(fields)

    # déplier les JSONB: récupérer les lexèmes dans les Docs.
    s_add = SQL("""create temp table _lex as
    select 
        x.* 
    from _nouveau_lexeme lx, 
    jsonb_to_record(lx.lexeme) as x(
        {fields}
    )
    """)
    s_add = s_add.format(fields=fields)
    conn.execute(s_add)

    # ajoute les propriétés des lexèmes qui sont dans des tables séparées: lemme, nature, morph. (les autres, norme et 'j' ne sont pas des foreign keys mais des valeurs littérales.)
    sql_add_lex_attr = SQL("""
    insert into {tablename} ({col})
    select distinct lexeme {getter} %s from _nouveau_lexeme
    except select {col} from {tablename}
    """)

    # ajouter les valeurs dans les tables FK.
    for i in lex_attrs:
        if i["is_literal"] is False:
            tablename = i["name"]
            column_value = i["value_column"]
            if i["datatype"] == "text":
                getter = SQL("->>")
            else:
                getter = SQL("->")
            stmt = sql_add_lex_attr.format(
                tablename=Identifier(tablename),
                getter=getter,
                col=Identifier(column_value),
            )
            conn.execute(stmt, (tablename,))

    # construit le statement qui ajoute les nouveaux lexèmes, avec les jointures sur les tables foreign keys (lemme, nature, morph, et aussi les user-defined).
    insert_columns = [i["name"] for i in lex_attrs if i["name"] != "id"]
    insert_columns = map(Identifier, insert_columns)
    insert_columns = SQL(", ").join(insert_columns)

    stmt = SQL("insert into {schema}.lexeme ({columns})").format(
        columns=insert_columns, schema=Identifier(SCHEMA)
    )
    attrs = [i for i in lex_attrs if i["name"] != "id"]
    stmt += select_values_fk("_lex", attrs, rev=True)
    conn.execute(stmt)


def _add_missing_deps(conn):
    """Ajoute les tags de fonction (dep) manquants.

    Args:
        conn (Connection)
    """

    s = SQL("""with _mot as (
        select 
            x.fonction
        from {doc} d,
        jsonb_to_recordset(d.j -> 'mots') as x(fonction text)
    ) 
    insert into {schema}.fonction (nom)
    select distinct fonction from _mot
    except select nom from {schema}.fonction
    """)

    s = s.format(doc=qualify(DOC_TABLE), schema=Identifier(SCHEMA))

    conn.execute(s)


def _insert_mots(conn, **kwargs):
    """Ajoute les mots et objets dérivés (pos, lexèmes, ...).

    Args:
        conn (Connection)
    """

    print(1.1, 'ajout des fonctions syntaxiques manquantes...')
    _add_missing_deps(conn)

    print(1.2, "récupération des mots...")
    # crée une table temporaire pour les mots
    s_temp = SQL("""create temp table _mot as
    select 
        d.id as texte,
        f.id as fonction,
        x.debut,
        x.fin,
        x.num,
        x.phrase,
        x.lexeme,
        x.noyau
    from {doc} d,
    jsonb_to_recordset(d.j -> 'mots') as x (
        fonction text,
        debut int, 
        fin int, 
        num int, 
        phrase int,
        lexeme jsonb, 
        noyau int
    ) join {schema}.fonction f on x.fonction = f.nom""")
    s_temp = s_temp.format(
        doc=qualify(DOC_TABLE), schema=Identifier(SCHEMA)
    )
    conn.execute(s_temp)

    print(1.3, "insertion des lexèmes...")
    _insert_lexemes(conn, **kwargs)

    # crée une table lookup avec deux colonnes: les IDs des lexèmes et leur représentations (textuelle) en JSONB (similaire à celle dans les mots).
    s = SQL("""create temp table id_jsonb_lex as
    select 
        x.id, to_jsonb(x) - 'id' as j 
    from {lextext} x;
    """)

    s = s.format(lextext=Identifier(LEXEME_TEXT_TABLE))

    conn.execute(s)

    print(1.5, "insertion des mots...")
    # ajoute les mots
    sql_add_mot = SQL("""
    insert into {schema}.mot (texte, debut, fin, num, phrase, noyau, fonction, lexeme)
    select
        m.texte,
        m.debut,
        m.fin,
        m.num,
        m.phrase,
        m.noyau,
        m.fonction,
        x.id
    from _mot m
    join id_jsonb_lex x on x.j = m.lexeme;""").format(
        schema=Identifier(SCHEMA)
    )
    conn.execute(sql_add_mot)
    print("mots OK!")


def _insert_phrases(conn, **kwargs):
    """Ajoute les phrases depuis les annotations.

    Args:
        conn (Connection)
    """

    s = SQL("""
        insert into {schema}.phrase
        select
            d.id as texte,
            x.debut,
            x.fin
        from {doc} d,
        jsonb_to_recordset(d.j -> 'phrases') as x(
            debut integer,
            fin integer
        );
    """)

    s = s.format(doc=qualify(DOC_TABLE), schema=Identifier(SCHEMA))

    conn.execute(s)


def _insert_tokens(conn, **kwargs):
    """Ajoute les tokens depuis les annotations.

    Args:
        conn (Connection)
    """

    s = SQL("""
        insert into {schema}.token 
            (texte, debut, fin, num, phrase)
        select
            d.id as texte,
            x.debut,
            x.fin,
            x.num,
            x.phrase
        from {doc} d,
        jsonb_to_recordset(d.j -> 'nonmots') as x(
            debut integer,
            fin integer,
            num integer,
            phrase integer
        );
    """)

    s = s.format(doc=qualify(DOC_TABLE), schema=Identifier(SCHEMA))

    conn.execute(s)


def _insert_spans(conn, **kwargs):
    """Ajoute les spans depuis les annotations.

    Args:
        conn (Connection)
    """

    s = SQL("""insert into {schema}.span
        select
            d.id as texte,
            x.debut,
            x.fin,
            x.attrs
        from {doc} d,
        jsonb_to_recordset(d.j -> 'spans') as x(
            debut integer,
            fin integer,
            attrs jsonb
        );
    """)

    s = s.format(doc=qualify(DOC_TABLE), schema=Identifier(SCHEMA))

    conn.execute(s)


def inserer(conn, keep_data=False, **kwargs):
    """Ajoute les annotations dans les tables.

    Args:
        conn (Connection)
        keep_data (bool)
        **kwargs
    """

    conn.execute("set search_path to litteralement, eav, public")

    print(1)
    _insert_mots(conn, **kwargs)
    print(2, 'insertions des tokens (non-mots)...')
    _insert_tokens(conn, **kwargs)
    print('tokens OK.')
    print(3, 'insertions des spans...')
    _insert_spans(conn, **kwargs)
    print('spans OK.')
    print(4, 'insertion des phrases...')
    _insert_phrases(conn, **kwargs)
    print("phrases OK.")

    if keep_data is False:
        doctable = qualify(DOC_TABLE)
        conn.execute(SQL("truncate {}").format(doctable))

    conn.commit()
    print("terminé.")
