import psycopg
import json
from psycopg.sql import SQL, Identifier
from litteralement.lookups.database import TryDatabaseLookup
from litteralement.lookups.database import MultiColumnLookup
from litteralement.statements import qualify
from litteralement.statements import make_copy_stmt
from litteralement.importer.importdata import numerise
from litteralement.importer.importdata import create_data_temp_table
from litteralement.importer.importdata import DATA_TEMP_TABLE
from litteralement.importer.importdata import DATA_TABLE
from litteralement.importer.importdata import DATA_TEMP_COLUMNS


dbname = "litteralement"
conn = psycopg.connect(dbname=dbname)

create_data_temp_table(conn)

curval = conn.execute("select nextval('entite_id_seq')").fetchone()[0]
lookup_entite = MultiColumnLookup(
    conn=conn,
    colid="id_entite",
    columns=["dataset", "id_dataset"],
    table="import._lookup_entite",
    start_id=curval,
)
lookup_classe = TryDatabaseLookup(conn, "onto.classe")
lookup_type_relation = TryDatabaseLookup(conn, "onto.type_relation")
lookup_type_propriete = TryDatabaseLookup(conn, "onto.type_propriete")


cur_get = conn.cursor()
cur_send = conn.cursor()

sql_get = SQL("select * from {}").format(qualify(DATA_TABLE))
data = (i[0] for i in cur_get.execute(sql_get))

sql_copy = make_copy_stmt(DATA_TEMP_TABLE, DATA_TEMP_COLUMNS)

with cur_send.copy(sql_copy) as copy:
    for d in data:
        num = numerise(d, lookup_entite=lookup_entite)
        row = [num[i] for i in DATA_TEMP_COLUMNS]
        copy.write_row([json.dumps(i) for i in row])

lookup_classe.copy_to()
lookup_type_relation.copy_to()
lookup_type_propriete.copy_to()


# def copy_entite(conn):

cur_send = conn.cursor()
cur_get = conn.cursor()
columns = ["id", "classe"]
copy_sql = make_copy_stmt("entite", columns)
sql_get = SQL("select {} from {}").format(
    Identifier("entites"), Identifier(DATA_TEMP_TABLE)
)
data = cur_get.execute(sql_get)
with cur_send.copy(copy_sql) as copy:
    for row in data:
        for e in row:
            print(e)

            copy.write_row([e[i] for i in columns])


# def copy_entite(conn):
#     table = "public.entite"
#     columns = ("id", "classe")
#     copy(conn, table, columns)


def copy_entite(conn):
    cur_send = conn.cursor()
    cur_get = conn.cursor()
    numdata = (i[0] for i in cur_get.execute("select entites from {}"))
    with cur_send.copy("copy entite (id, classe) from stdin") as copy:
        for entites in num:
            for e in entites:
                copy.write_row(e["id"], e["classe"])


list(lookup_classe.as_tuples())

lookup_classe.copy_to()


# cur_send.executemany(
#     "insert into entite (id, classe) select %s, %s",
#     [(i["id"], i["classe"]) for i in entites],
# )


list(cur_send.execute("select * from entite"))

list(cur_get.execute("select * from classe"))

lookup_classe.copy_to()

lookup_type_propriete.copy_to()
lookup_type_relation.copy_to()

list(lookup_classe.conn.execute("select * from onto.classe"))

list(
    lookup_type_relation.conn.execute(
        "select * from onto.type_relation"
    )
)

# mhhhh ya KED

list(lookup_classe.conn.execute("select * from onto.type_propriete"))


list(conn.execute("select * from " + DATA_TEMP_TABLE))

lookup_entite.copy_to()  # pas public.entite, mais import._lookup_entite!!!

lookup_classe.copy_to()
conn.commit()

lookup_type_relation.copy_to()
lookup_type_propriete.copy_to()

sql_copy = SQL("select {} from {}").format()
# with cur_get.copy()

# for column,

conn.execute("select id, classe from entite")

list(conn.execute("select * from import._lookup_entite"))

conn.close()
