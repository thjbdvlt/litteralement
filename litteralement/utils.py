from psycopg import sql


def get_labels_updated(conn, tablename, labels, colname="nom"):
    """Ajoute des labels et récupère une lookup table avec les éléments d'une table données.

    Args:
        cursor:  le curseur psycopg.
        tablename:  le nom de la table.
        labels (list[str]):  les labels.
        colname:  alternative à la colonne "nom".

    La table doit avoir les colonnes "nom" et "id" (avec des contraintes UNIQUE). (la colonne "nom" peut être remplacée par une autre colonne dans le paramètre "col_nom" mais elle doit tout de même être unique).

    Returns (dict):  la lookup table {nom: id}.
    """

    cur = conn.cursor()

    # premier statement: récupérer les labels déjà présents.
    stmt_select = sql.SQL("select {} from {}").format(
        sql.Identifier(colname),
        sql.Identifier(tablename),
    )

    # second statement: insérer les labels (absents).
    stmt_insert = sql.SQL("insert into {} ({}) select (%s)").format(
        sql.Identifier(tablename), sql.Identifier(colname)
    )

    # troisième statement: récupérer le lookup {nom: id}.
    stmt_select_lookup = sql.SQL("select {}, id from {}").format(
        sql.Identifier(colname), sql.Identifier(tablename)
    )

    # identifier les labels manquants.
    registered = set(cur.execute(stmt_select))
    registered = [i[0] for i in registered]
    unregistered = [i for i in set(labels) if i not in registered]

    # ajouter les labels manquants.
    cur.executemany(stmt_insert, [(i,) for i in unregistered])
    conn.commit()

    # récupérer le lookup.
    lookup = dict(conn.execute(stmt_select_lookup).fetchall())
    return lookup


def get_feats(nlp):
    """Enlever les tag 'POS=...' des FEATS.

    Args:
        labels (list[str]):  la liste de labels.

    Returns (list[str]):  la liste de labels, sans 'POS='.

    Note:
        Les POS=NOUN, etc., sont enlevés lors de l'analyse avec spacy, c'est pourquoi il faut les enlever aussi ici.
    """

    feats = []
    for feature in nlp.get_pipe("morphologizer").labels:
        x = []
        splitted = feature.split("|")
        for i in splitted:
            if not i.lower().startswith("POS="):
                x.append(i)
        feats.append("|".join(x))
    return feats
