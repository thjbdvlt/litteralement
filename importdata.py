import psycopg
import json
from psycopg.sql import SQL, Identifier
from litteralement.lookups.database import TryDatabaseLookup
from litteralement.lookups.database import MultiColumnLookup
from litteralement.statements import qualify
from litteralement.statements import make_copy_stmt
from litteralement.importer.importdata import numerise_row
from litteralement.importer.importdata import create_data_temp_table
from litteralement.importer.importdata import DATA_TEMP_TABLE
from litteralement.importer.importdata import DATA_TABLE
from litteralement.importer.importdata import DATA_TEMP_COLUMNS
from litteralement.importer.importdata import copy_entites
from litteralement.importer.importdata import copy_relations
# from litteralement.importer.importdata import copy_proprietes


dbname = "litteralement"
conn = psycopg.connect(dbname=dbname)

create_data_temp_table(conn)

curval = conn.execute("select nextval('entite_id_seq')").fetchone()[0]
lookup_entite = MultiColumnLookup(
    conn=conn,
    colid="id_entite",
    columns=("dataset", "id_dataset"),
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
        num = numerise_row(
            d,
            lookup_entite=lookup_entite,
            lookup_classe=lookup_classe,
            lookup_type_relation=lookup_type_relation,
            lookup_type_propriete=lookup_type_propriete,
        )
        row = [num[i] for i in DATA_TEMP_COLUMNS]
        copy.write_row([json.dumps(i) for i in row])

lookup_classe.copy_to()
lookup_type_relation.copy_to()
lookup_type_propriete.copy_to()

copy_entites(conn)
copy_relations(conn)

# copy_proprietes(conn)


# des tests
list(conn.execute("select * from entite"))
list(conn.execute("select * from relation"))
list(conn.execute("select * from type_relation"))


conn.close()
