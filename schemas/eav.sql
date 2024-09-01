--
-- PostgreSQL database dump
--

-- Dumped from database version 16.4 (Debian 16.4-1.pgdg120+1)
-- Dumped by pg_dump version 16.4 (Debian 16.4-1.pgdg120+1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: eav; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA eav;


--
-- Name: import; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA import;


--
-- Name: importer(); Type: PROCEDURE; Schema: import; Owner: -
--

CREATE PROCEDURE import.importer()
    LANGUAGE plpgsql
    AS $$
    declare

    begin

        -- crée une table temporaire pour préparer l'insertion des entités, de leurs propriétés et de leurs relations. cette première table sépare les champs "id", "classe", "relations" et "proprietes", qui requierent tous des traitements différents.
        create temp table _ent as 
        select 
            nextval('eav.entite_id_seq') as id,
            j ->> 'id' as import_id,
            j ->> 'classe' as classe_nom,
            j -> 'relations' as relations,
            j - 'id' - 'classe' - 'relations' as proprietes
        from import._entite;

        -- ajoute les classes manquantes.
        insert into eav.classe (nom)
        select distinct classe_nom from _ent
        except select nom from eav.classe;

        -- ajoute les entités dans la lookup table.
        insert into import._lookup_ent
        (id, import_id)
        select id, import_id from _ent;

        -- ajoute les entités
        insert into eav.entite (id, classe)
        select
            e.id as id,
            c.id as classe
        from _ent e
        join eav.classe c
        on c.nom = e.classe_nom;

        -- déplie les relations
        create temp table _relation_text as
        select
            id as sujet,
            r.*
        from _ent e,
        jsonb_to_recordset(e.relations) as r(type text, objet text);

        -- ajoute les types de relations
        insert into eav.type_relation (nom)
        select distinct type from _relation_text
        except
        select nom from eav.type_relation;

        -- ajoute les relations
        insert into eav.relation (sujet, type, objet)
        select
            r.sujet,
            y.id as type,
            l2.id as objet
        from _relation_text r
        join import._lookup_ent l2 on l2.import_id = r.objet
        join eav.type_relation y on y.nom = r.type;

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
        insert into eav.type_propriete (nom)
        select distinct type_nom from _propriete
        except
        select nom from eav.type_propriete;

        -- ajoute les textes (les propriétés de datatype string).
        insert into eav.texte (entite, type, val)
        select
            p.entite,
            y.id as type,
            p.val ->> 0 as val
        from _propriete p
        join eav.type_propriete y on y.nom = p.type_nom
        where p.datatype = 'string';

        -- ajoute les propriétés à valeur jsonb (array/object).
        insert into eav.prop_jsonb (entite, type, val)
        select
            p.entite,
            y.id as type,
            p.val -> 0 as val
        from _propriete p
        join eav.type_propriete y on y.nom = p.type_nom
        where p.datatype in ('array', 'object');

        -- ajoute les propriétés numériques entières.
        insert into eav.prop_int (entite, type, val)
        select
            p.entite,
            y.id as type,
            (p.val -> 0)::integer as val
        from _propriete p
        join eav.type_propriete y on y.nom = p.type_nom
        where p.datatype = 'number' and not regexp_like(p.val ->> 0, '\.');

        -- ajoute les propriétés numériques décimales.
        insert into eav.prop_float (entite, type, val)
        select
            p.entite,
            y.id as type,
            (p.val -> 0)::float as val
        from _propriete p
        join eav.type_propriete y on y.nom = p.type_nom
        where p.datatype = 'number' and regexp_like(p.val ->> 0, '\.');

        -- ajoute les propriétés numériques décimales.
        insert into eav.propriete (entite, type)
        select
            p.entite,
            y.id as type
        from _propriete p
        join eav.type_propriete y on y.nom = p.type_nom
        where p.datatype = 'null' ;

        -- drop les tables temporaires, 
        drop table _propriete;
        drop table _relation_text;
        drop table _ent;

        -- vider la table d'importation.
        truncate import._entite;

    end;
$$;


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: classe; Type: TABLE; Schema: eav; Owner: -
--

CREATE TABLE eav.classe (
    id smallint NOT NULL,
    nom text NOT NULL,
    definition text
);


--
-- Name: classe_id_seq; Type: SEQUENCE; Schema: eav; Owner: -
--

ALTER TABLE eav.classe ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME eav.classe_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: entite; Type: TABLE; Schema: eav; Owner: -
--

CREATE TABLE eav.entite (
    id integer NOT NULL,
    classe smallint NOT NULL
);


--
-- Name: entite_id_seq; Type: SEQUENCE; Schema: eav; Owner: -
--

ALTER TABLE eav.entite ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME eav.entite_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: propriete; Type: TABLE; Schema: eav; Owner: -
--

CREATE TABLE eav.propriete (
    type smallint NOT NULL,
    entite integer NOT NULL
);


--
-- Name: prop_date; Type: TABLE; Schema: eav; Owner: -
--

CREATE TABLE eav.prop_date (
    val timestamp without time zone
)
INHERITS (eav.propriete);


--
-- Name: prop_float; Type: TABLE; Schema: eav; Owner: -
--

CREATE TABLE eav.prop_float (
    val double precision
)
INHERITS (eav.propriete);


--
-- Name: prop_int; Type: TABLE; Schema: eav; Owner: -
--

CREATE TABLE eav.prop_int (
    val integer
)
INHERITS (eav.propriete);


--
-- Name: prop_jsonb; Type: TABLE; Schema: eav; Owner: -
--

CREATE TABLE eav.prop_jsonb (
    val jsonb
)
INHERITS (eav.propriete);


--
-- Name: relation; Type: TABLE; Schema: eav; Owner: -
--

CREATE TABLE eav.relation (
    type smallint NOT NULL,
    sujet integer NOT NULL,
    objet integer NOT NULL
);


--
-- Name: texte; Type: TABLE; Schema: eav; Owner: -
--

CREATE TABLE eav.texte (
    id integer NOT NULL,
    val text
)
INHERITS (eav.propriete);


--
-- Name: texte_id_seq; Type: SEQUENCE; Schema: eav; Owner: -
--

ALTER TABLE eav.texte ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME eav.texte_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: type_propriete; Type: TABLE; Schema: eav; Owner: -
--

CREATE TABLE eav.type_propriete (
    id smallint NOT NULL,
    nom text NOT NULL,
    definition text
);


--
-- Name: type_propriete_id_seq; Type: SEQUENCE; Schema: eav; Owner: -
--

ALTER TABLE eav.type_propriete ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME eav.type_propriete_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: type_relation; Type: TABLE; Schema: eav; Owner: -
--

CREATE TABLE eav.type_relation (
    id smallint NOT NULL,
    nom text NOT NULL,
    definition text
);


--
-- Name: type_relation_id_seq; Type: SEQUENCE; Schema: eav; Owner: -
--

ALTER TABLE eav.type_relation ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME eav.type_relation_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: _document; Type: TABLE; Schema: import; Owner: -
--

CREATE TABLE import._document (
    id integer,
    j jsonb
);


--
-- Name: _entite; Type: TABLE; Schema: import; Owner: -
--

CREATE TABLE import._entite (
    j jsonb
);


--
-- Name: _lookup_ent; Type: TABLE; Schema: import; Owner: -
--

CREATE TABLE import._lookup_ent (
    import_id text,
    id integer
);


--
-- Name: classe classe_nom_key; Type: CONSTRAINT; Schema: eav; Owner: -
--

ALTER TABLE ONLY eav.classe
    ADD CONSTRAINT classe_nom_key UNIQUE (nom);


--
-- Name: classe classe_pkey; Type: CONSTRAINT; Schema: eav; Owner: -
--

ALTER TABLE ONLY eav.classe
    ADD CONSTRAINT classe_pkey PRIMARY KEY (id);


--
-- Name: entite entite_pkey; Type: CONSTRAINT; Schema: eav; Owner: -
--

ALTER TABLE ONLY eav.entite
    ADD CONSTRAINT entite_pkey PRIMARY KEY (id);


--
-- Name: texte texte_pkey; Type: CONSTRAINT; Schema: eav; Owner: -
--

ALTER TABLE ONLY eav.texte
    ADD CONSTRAINT texte_pkey PRIMARY KEY (id);


--
-- Name: type_propriete type_propriete_nom_key; Type: CONSTRAINT; Schema: eav; Owner: -
--

ALTER TABLE ONLY eav.type_propriete
    ADD CONSTRAINT type_propriete_nom_key UNIQUE (nom);


--
-- Name: type_propriete type_propriete_pkey; Type: CONSTRAINT; Schema: eav; Owner: -
--

ALTER TABLE ONLY eav.type_propriete
    ADD CONSTRAINT type_propriete_pkey PRIMARY KEY (id);


--
-- Name: type_relation type_relation_nom_key; Type: CONSTRAINT; Schema: eav; Owner: -
--

ALTER TABLE ONLY eav.type_relation
    ADD CONSTRAINT type_relation_nom_key UNIQUE (nom);


--
-- Name: type_relation type_relation_pkey; Type: CONSTRAINT; Schema: eav; Owner: -
--

ALTER TABLE ONLY eav.type_relation
    ADD CONSTRAINT type_relation_pkey PRIMARY KEY (id);


--
-- Name: classe_nom_idx; Type: INDEX; Schema: eav; Owner: -
--

CREATE INDEX classe_nom_idx ON eav.classe USING btree (nom);


--
-- Name: entite_classe_idx; Type: INDEX; Schema: eav; Owner: -
--

CREATE INDEX entite_classe_idx ON eav.entite USING btree (classe);


--
-- Name: prop_float_entite_idx; Type: INDEX; Schema: eav; Owner: -
--

CREATE INDEX prop_float_entite_idx ON eav.prop_float USING btree (entite);


--
-- Name: prop_float_type_idx; Type: INDEX; Schema: eav; Owner: -
--

CREATE INDEX prop_float_type_idx ON eav.prop_float USING btree (type);


--
-- Name: prop_int_entite_idx; Type: INDEX; Schema: eav; Owner: -
--

CREATE INDEX prop_int_entite_idx ON eav.prop_int USING btree (entite);


--
-- Name: prop_int_type_idx; Type: INDEX; Schema: eav; Owner: -
--

CREATE INDEX prop_int_type_idx ON eav.prop_int USING btree (type);


--
-- Name: prop_jsonb_entite_idx; Type: INDEX; Schema: eav; Owner: -
--

CREATE INDEX prop_jsonb_entite_idx ON eav.prop_jsonb USING btree (entite);


--
-- Name: prop_jsonb_type_idx; Type: INDEX; Schema: eav; Owner: -
--

CREATE INDEX prop_jsonb_type_idx ON eav.prop_jsonb USING btree (type);


--
-- Name: propriete_entite_idx; Type: INDEX; Schema: eav; Owner: -
--

CREATE INDEX propriete_entite_idx ON eav.propriete USING btree (entite);


--
-- Name: propriete_type_idx; Type: INDEX; Schema: eav; Owner: -
--

CREATE INDEX propriete_type_idx ON eav.propriete USING btree (type);


--
-- Name: relation_objet_idx; Type: INDEX; Schema: eav; Owner: -
--

CREATE INDEX relation_objet_idx ON eav.relation USING btree (objet);


--
-- Name: relation_sujet_idx; Type: INDEX; Schema: eav; Owner: -
--

CREATE INDEX relation_sujet_idx ON eav.relation USING btree (sujet);


--
-- Name: relation_type_idx; Type: INDEX; Schema: eav; Owner: -
--

CREATE INDEX relation_type_idx ON eav.relation USING btree (type);


--
-- Name: texte_entite_idx; Type: INDEX; Schema: eav; Owner: -
--

CREATE INDEX texte_entite_idx ON eav.texte USING btree (entite);


--
-- Name: texte_type_idx; Type: INDEX; Schema: eav; Owner: -
--

CREATE INDEX texte_type_idx ON eav.texte USING btree (type);


--
-- Name: type_propriete_nom_idx; Type: INDEX; Schema: eav; Owner: -
--

CREATE INDEX type_propriete_nom_idx ON eav.type_propriete USING btree (nom);


--
-- Name: type_relation_nom_idx; Type: INDEX; Schema: eav; Owner: -
--

CREATE INDEX type_relation_nom_idx ON eav.type_relation USING btree (nom);


--
-- Name: entite entite_classe_fkey; Type: FK CONSTRAINT; Schema: eav; Owner: -
--

ALTER TABLE ONLY eav.entite
    ADD CONSTRAINT entite_classe_fkey FOREIGN KEY (classe) REFERENCES eav.classe(id);


--
-- Name: prop_date prop_date_entite_fk; Type: FK CONSTRAINT; Schema: eav; Owner: -
--

ALTER TABLE ONLY eav.prop_date
    ADD CONSTRAINT prop_date_entite_fk FOREIGN KEY (entite) REFERENCES eav.entite(id);


--
-- Name: prop_date prop_date_type_fk; Type: FK CONSTRAINT; Schema: eav; Owner: -
--

ALTER TABLE ONLY eav.prop_date
    ADD CONSTRAINT prop_date_type_fk FOREIGN KEY (type) REFERENCES eav.type_propriete(id);


--
-- Name: prop_float prop_float_entite_fk; Type: FK CONSTRAINT; Schema: eav; Owner: -
--

ALTER TABLE ONLY eav.prop_float
    ADD CONSTRAINT prop_float_entite_fk FOREIGN KEY (entite) REFERENCES eav.entite(id);


--
-- Name: prop_float prop_float_type_fk; Type: FK CONSTRAINT; Schema: eav; Owner: -
--

ALTER TABLE ONLY eav.prop_float
    ADD CONSTRAINT prop_float_type_fk FOREIGN KEY (type) REFERENCES eav.type_propriete(id);


--
-- Name: prop_int prop_int_entite_fk; Type: FK CONSTRAINT; Schema: eav; Owner: -
--

ALTER TABLE ONLY eav.prop_int
    ADD CONSTRAINT prop_int_entite_fk FOREIGN KEY (entite) REFERENCES eav.entite(id);


--
-- Name: prop_int prop_int_type_fk; Type: FK CONSTRAINT; Schema: eav; Owner: -
--

ALTER TABLE ONLY eav.prop_int
    ADD CONSTRAINT prop_int_type_fk FOREIGN KEY (type) REFERENCES eav.type_propriete(id);


--
-- Name: prop_jsonb prop_jsonb_entite_fk; Type: FK CONSTRAINT; Schema: eav; Owner: -
--

ALTER TABLE ONLY eav.prop_jsonb
    ADD CONSTRAINT prop_jsonb_entite_fk FOREIGN KEY (entite) REFERENCES eav.entite(id);


--
-- Name: prop_jsonb prop_jsonb_type_fk; Type: FK CONSTRAINT; Schema: eav; Owner: -
--

ALTER TABLE ONLY eav.prop_jsonb
    ADD CONSTRAINT prop_jsonb_type_fk FOREIGN KEY (type) REFERENCES eav.type_propriete(id);


--
-- Name: propriete propriete_entite_fkey; Type: FK CONSTRAINT; Schema: eav; Owner: -
--

ALTER TABLE ONLY eav.propriete
    ADD CONSTRAINT propriete_entite_fkey FOREIGN KEY (entite) REFERENCES eav.entite(id);


--
-- Name: propriete propriete_type_fkey; Type: FK CONSTRAINT; Schema: eav; Owner: -
--

ALTER TABLE ONLY eav.propriete
    ADD CONSTRAINT propriete_type_fkey FOREIGN KEY (type) REFERENCES eav.type_propriete(id);


--
-- Name: relation relation_objet_fkey; Type: FK CONSTRAINT; Schema: eav; Owner: -
--

ALTER TABLE ONLY eav.relation
    ADD CONSTRAINT relation_objet_fkey FOREIGN KEY (objet) REFERENCES eav.entite(id);


--
-- Name: relation relation_sujet_fkey; Type: FK CONSTRAINT; Schema: eav; Owner: -
--

ALTER TABLE ONLY eav.relation
    ADD CONSTRAINT relation_sujet_fkey FOREIGN KEY (sujet) REFERENCES eav.entite(id);


--
-- Name: relation relation_type_fkey; Type: FK CONSTRAINT; Schema: eav; Owner: -
--

ALTER TABLE ONLY eav.relation
    ADD CONSTRAINT relation_type_fkey FOREIGN KEY (type) REFERENCES eav.type_relation(id);


--
-- Name: texte texte_entite_fk; Type: FK CONSTRAINT; Schema: eav; Owner: -
--

ALTER TABLE ONLY eav.texte
    ADD CONSTRAINT texte_entite_fk FOREIGN KEY (entite) REFERENCES eav.entite(id);


--
-- Name: texte texte_type_fk; Type: FK CONSTRAINT; Schema: eav; Owner: -
--

ALTER TABLE ONLY eav.texte
    ADD CONSTRAINT texte_type_fk FOREIGN KEY (type) REFERENCES eav.type_propriete(id);


--
-- PostgreSQL database dump complete
--

