create or replace procedure import.importer()
language plpgsql
as $$
    declare

    begin

        -- crée une table temporaire pour préparer l'insertion des entités, de leurs propriétés et de leurs relations. cette première table sépare les champs "id", "classe", "relations" et "proprietes", qui requierent tous des traitements différents.
        create temp table _ent as 
        select 
            nextval('entite_id_seq') as id,
            j ->> 'id' as import_id,
            j ->> 'classe' as classe_nom,
            j -> 'relations' as relations,
            j - 'id' - 'classe' - 'relations' as proprietes
        from import._entite;

        -- ajoute les classes manquantes.
        insert into classe (nom)
        select distinct classe_nom from _ent
        except select nom from classe;

        -- ajoute les entités dans la lookup table.
        insert into import._lookup_ent
        (id, import_id)
        select id, import_id from _ent;

        -- ajoute les entités
        insert into entite (id, classe)
        select
            e.id as id,
            c.id as classe
        from _ent e
        join classe c
        on c.nom = e.classe_nom;

        -- déplie les relations
        create temp table _relation_text as
        select
            -- import_id as sujet,
            id as sujet,
            r.*
        from _ent e,
        jsonb_to_recordset(e.relations) as r(type text, objet text);

        -- ajoute les types de relations
        insert into type_relation (nom)
        select distinct type from _relation_text
        except
        select nom from type_relation;

        -- ajoute les relations
        insert into relation (sujet, type, objet)
        select
            -- l1.id as sujet,
            r.sujet,
            y.id as type,
            l2.id as objet
        from _relation_text r
        -- join import._lookup_ent l1 on l1.import_id = r.sujet
        join import._lookup_ent l2 on l2.import_id = r.objet
        join type_relation y on y.nom = r.type;

        -- déplie les propriétés dans un format key/value (deux colonnes), ajoute le 'datatype' jsonb (string, array, object, number), duquel va dépendre la sous-tablede propriété dans laquelle chaque propriété va aller.
        create temp table _propriete as
        select
            e.id as entite,
            key as type_nom,
            jsonb_build_array(value) as val,
            jsonb_typeof(value) as datatype
        from _ent e,
        jsonb_each(e.proprietes);

        -- ajoute les types de propriétés
        insert into type_propriete (nom)
        select distinct type_nom from _propriete
        except
        select nom from type_propriete;

        -- ajoute les textes (les propriétés de datatype string).
        insert into texte (entite, type, val)
        select
            p.entite,
            y.id as type,
            p.val ->> 0 as val
        from _propriete p
        join type_propriete y on y.nom = p.type_nom
        where p.datatype = 'string';

        -- ajoute les propriétés à valeur jsonb (array/object).
        insert into prop_jsonb (entite, type, val)
        select
            p.entite,
            y.id as type,
            p.val -> 0 as val
        from _propriete p
        join type_propriete y on y.nom = p.type_nom
        where p.datatype in ('array', 'object');

        -- ajoute les propriétés numériques entières.
        insert into prop_int (entite, type, val)
        select
            p.entite,
            y.id as type,
            (p.val -> 0)::integer as val
        from _propriete p
        join type_propriete y on y.nom = p.type_nom
        where p.datatype = 'number' and not regexp_like(p.val ->> 0, '\.');

        -- ajoute les propriétés numériques décimales.
        insert into prop_float (entite, type, val)
        select
            p.entite,
            y.id as type,
            (p.val -> 0)::float as val
        from _propriete p
        join type_propriete y on y.nom = p.type_nom
        where p.datatype = 'number' and regexp_like(p.val ->> 0, '\.');

        -- ajoute les propriétés numériques décimales.
        insert into propriete (entite, type)
        select
            p.entite,
            y.id as type
        from _propriete p
        join type_propriete y on y.nom = p.type_nom
        where p.datatype = 'null' ;

        -- drop les tables temporaires, 
        drop table _propriete;
        drop table _relation_text;
        drop table _ent;

        -- vider la table d'importation.
        truncate import._entite;

    end;
$$;
