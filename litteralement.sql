--
-- PostgreSQL database dump
--

-- Dumped from database version 16.4 (Debian 16.4-1.pgdg110+1)
-- Dumped by pg_dump version 16.4 (Debian 16.4-1.pgdg110+1)

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
-- Name: nlp; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA nlp;


--
-- Name: onto; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA onto;


--
-- Name: vector; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public;


--
-- Name: EXTENSION vector; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION vector IS 'vector data type and ivfflat and hnsw access methods';


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
            nextval('entite_id_seq') as id,
            j ->> 'id' as import_id,
            j ->> 'classe' as classe_nom,
            j -> 'relations' as relations,
            j - 'id' - 'classe' - 'relations' as proprietes
        from import._entite;

        -- ajoute les classes manquantes.
        insert into onto.classe (nom)
        select distinct classe_nom from _ent
        except select nom from onto.classe;

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
        join onto.classe c
        on c.nom = e.classe_nom;

        -- déplie les relations
        create temp table _relation_text as
        select
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
            r.sujet,
            y.id as type,
            l2.id as objet
        from _relation_text r
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


--
-- Name: feats_to_json(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.feats_to_json() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
begin
    update morph
    set j = case
        when feats != ''
            then jsonb_object(regexp_split_to_array(feats, '\||='))
        else
            '{}'::jsonb
        end
    where id = new.id;
return new;
end;
$$;


SET default_tablespace = '';

SET default_table_access_method = heap;

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
-- Name: fonction; Type: TABLE; Schema: nlp; Owner: -
--

CREATE TABLE nlp.fonction (
    id smallint NOT NULL,
    nom text NOT NULL,
    definition text
);


--
-- Name: fonction_id_seq; Type: SEQUENCE; Schema: nlp; Owner: -
--

ALTER TABLE nlp.fonction ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME nlp.fonction_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    MAXVALUE 32767
    CACHE 1
);


--
-- Name: lemme; Type: TABLE; Schema: nlp; Owner: -
--

CREATE TABLE nlp.lemme (
    id integer NOT NULL,
    graphie text NOT NULL
);


--
-- Name: lemme_id_seq; Type: SEQUENCE; Schema: nlp; Owner: -
--

ALTER TABLE nlp.lemme ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME nlp.lemme_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: lexeme; Type: TABLE; Schema: nlp; Owner: -
--

CREATE TABLE nlp.lexeme (
    id integer NOT NULL,
    lemme integer NOT NULL,
    nature smallint NOT NULL,
    morph smallint NOT NULL,
    norme text NOT NULL
);


--
-- Name: lexeme_id_seq; Type: SEQUENCE; Schema: nlp; Owner: -
--

ALTER TABLE nlp.lexeme ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME nlp.lexeme_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: morph; Type: TABLE; Schema: nlp; Owner: -
--

CREATE TABLE nlp.morph (
    id smallint NOT NULL,
    feats text,
    j jsonb
);


--
-- Name: morph_id_seq; Type: SEQUENCE; Schema: nlp; Owner: -
--

ALTER TABLE nlp.morph ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME nlp.morph_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: segment; Type: TABLE; Schema: nlp; Owner: -
--

CREATE TABLE nlp.segment (
    texte integer NOT NULL,
    debut integer NOT NULL,
    fin integer NOT NULL
);


--
-- Name: token; Type: TABLE; Schema: nlp; Owner: -
--

CREATE TABLE nlp.token (
    num integer NOT NULL,
    phrase integer
)
INHERITS (nlp.segment);


--
-- Name: mot; Type: TABLE; Schema: nlp; Owner: -
--

CREATE TABLE nlp.mot (
    fonction smallint NOT NULL,
    lexeme integer NOT NULL,
    noyau integer NOT NULL
)
INHERITS (nlp.token);


--
-- Name: nature; Type: TABLE; Schema: nlp; Owner: -
--

CREATE TABLE nlp.nature (
    id smallint NOT NULL,
    nom text NOT NULL,
    definition text
);


--
-- Name: nature_id_seq; Type: SEQUENCE; Schema: nlp; Owner: -
--

ALTER TABLE nlp.nature ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME nlp.nature_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    MAXVALUE 32767
    CACHE 1
);


--
-- Name: phrase; Type: TABLE; Schema: nlp; Owner: -
--

CREATE TABLE nlp.phrase (
)
INHERITS (nlp.segment);


--
-- Name: span; Type: TABLE; Schema: nlp; Owner: -
--

CREATE TABLE nlp.span (
    attrs jsonb
)
INHERITS (nlp.segment);


--
-- Name: stopword; Type: TABLE; Schema: nlp; Owner: -
--

CREATE TABLE nlp.stopword (
    norme text,
    lemme text
);


--
-- Name: classe; Type: TABLE; Schema: onto; Owner: -
--

CREATE TABLE onto.classe (
    id smallint NOT NULL,
    nom text NOT NULL,
    definition text
);


--
-- Name: classe_id_seq; Type: SEQUENCE; Schema: onto; Owner: -
--

ALTER TABLE onto.classe ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME onto.classe_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: type_propriete; Type: TABLE; Schema: onto; Owner: -
--

CREATE TABLE onto.type_propriete (
    id smallint NOT NULL,
    nom text NOT NULL,
    definition text
);


--
-- Name: type_propriete_id_seq; Type: SEQUENCE; Schema: onto; Owner: -
--

ALTER TABLE onto.type_propriete ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME onto.type_propriete_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    MAXVALUE 32767
    CACHE 1
);


--
-- Name: type_relation; Type: TABLE; Schema: onto; Owner: -
--

CREATE TABLE onto.type_relation (
    id smallint NOT NULL,
    nom text NOT NULL,
    definition text
);


--
-- Name: type_relation_id_seq; Type: SEQUENCE; Schema: onto; Owner: -
--

ALTER TABLE onto.type_relation ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME onto.type_relation_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    MAXVALUE 32767
    CACHE 1
);


--
-- Name: nonstop_lemme; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW public.nonstop_lemme AS
 WITH nonstop AS (
         SELECT l_1.id
           FROM nlp.lemme l_1
        EXCEPT
         SELECT l_1.id
           FROM (nlp.lemme l_1
             JOIN nlp.stopword s ON ((s.lemme = l_1.graphie)))
        )
 SELECT l.id,
    l.graphie
   FROM (nonstop n
     JOIN nlp.lemme l ON ((l.id = n.id)));


--
-- Name: nonstop_lexeme; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW public.nonstop_lexeme AS
 WITH nonstop AS (
         SELECT l_1.id
           FROM nlp.lexeme l_1
        EXCEPT
         SELECT l_1.id
           FROM (nlp.lexeme l_1
             JOIN nlp.stopword s ON ((s.norme = l_1.norme)))
        )
 SELECT l.id,
    l.lemme,
    l.nature,
    l.morph,
    l.norme
   FROM (nonstop n
     JOIN nlp.lexeme l ON ((l.id = n.id)));


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
-- Name: fonction fonction_nom_key; Type: CONSTRAINT; Schema: nlp; Owner: -
--

ALTER TABLE ONLY nlp.fonction
    ADD CONSTRAINT fonction_nom_key UNIQUE (nom);


--
-- Name: fonction fonction_pkey; Type: CONSTRAINT; Schema: nlp; Owner: -
--

ALTER TABLE ONLY nlp.fonction
    ADD CONSTRAINT fonction_pkey PRIMARY KEY (id);


--
-- Name: lemme lemme_graphie_key; Type: CONSTRAINT; Schema: nlp; Owner: -
--

ALTER TABLE ONLY nlp.lemme
    ADD CONSTRAINT lemme_graphie_key UNIQUE (graphie);


--
-- Name: lemme lemme_pkey; Type: CONSTRAINT; Schema: nlp; Owner: -
--

ALTER TABLE ONLY nlp.lemme
    ADD CONSTRAINT lemme_pkey PRIMARY KEY (id);


--
-- Name: lexeme lexeme_pkey; Type: CONSTRAINT; Schema: nlp; Owner: -
--

ALTER TABLE ONLY nlp.lexeme
    ADD CONSTRAINT lexeme_pkey PRIMARY KEY (id);


--
-- Name: morph morph_feats_key; Type: CONSTRAINT; Schema: nlp; Owner: -
--

ALTER TABLE ONLY nlp.morph
    ADD CONSTRAINT morph_feats_key UNIQUE (feats);


--
-- Name: morph morph_pkey; Type: CONSTRAINT; Schema: nlp; Owner: -
--

ALTER TABLE ONLY nlp.morph
    ADD CONSTRAINT morph_pkey PRIMARY KEY (id);


--
-- Name: nature nature_nom_key; Type: CONSTRAINT; Schema: nlp; Owner: -
--

ALTER TABLE ONLY nlp.nature
    ADD CONSTRAINT nature_nom_key UNIQUE (nom);


--
-- Name: nature nature_pkey; Type: CONSTRAINT; Schema: nlp; Owner: -
--

ALTER TABLE ONLY nlp.nature
    ADD CONSTRAINT nature_pkey PRIMARY KEY (id);


--
-- Name: token token_texte_num_key; Type: CONSTRAINT; Schema: nlp; Owner: -
--

ALTER TABLE ONLY nlp.token
    ADD CONSTRAINT token_texte_num_key UNIQUE (texte, num);


--
-- Name: classe classe_nom_key; Type: CONSTRAINT; Schema: onto; Owner: -
--

ALTER TABLE ONLY onto.classe
    ADD CONSTRAINT classe_nom_key UNIQUE (nom);


--
-- Name: classe classe_pkey; Type: CONSTRAINT; Schema: onto; Owner: -
--

ALTER TABLE ONLY onto.classe
    ADD CONSTRAINT classe_pkey PRIMARY KEY (id);


--
-- Name: type_propriete type_propriete_nom_key; Type: CONSTRAINT; Schema: onto; Owner: -
--

ALTER TABLE ONLY onto.type_propriete
    ADD CONSTRAINT type_propriete_nom_key UNIQUE (nom);


--
-- Name: type_propriete type_propriete_pkey; Type: CONSTRAINT; Schema: onto; Owner: -
--

ALTER TABLE ONLY onto.type_propriete
    ADD CONSTRAINT type_propriete_pkey PRIMARY KEY (id);


--
-- Name: type_relation type_relation_nom_key; Type: CONSTRAINT; Schema: onto; Owner: -
--

ALTER TABLE ONLY onto.type_relation
    ADD CONSTRAINT type_relation_nom_key UNIQUE (nom);


--
-- Name: type_relation type_relation_pkey; Type: CONSTRAINT; Schema: onto; Owner: -
--

ALTER TABLE ONLY onto.type_relation
    ADD CONSTRAINT type_relation_pkey PRIMARY KEY (id);


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
-- Name: fonction_nom_idx; Type: INDEX; Schema: nlp; Owner: -
--

CREATE INDEX fonction_nom_idx ON nlp.fonction USING btree (nom);


--
-- Name: lexeme_lemme_idx; Type: INDEX; Schema: nlp; Owner: -
--

CREATE INDEX lexeme_lemme_idx ON nlp.lexeme USING btree (lemme);


--
-- Name: lexeme_morph_idx; Type: INDEX; Schema: nlp; Owner: -
--

CREATE INDEX lexeme_morph_idx ON nlp.lexeme USING btree (morph);


--
-- Name: lexeme_nature_idx; Type: INDEX; Schema: nlp; Owner: -
--

CREATE INDEX lexeme_nature_idx ON nlp.lexeme USING btree (nature);


--
-- Name: morph_feats_idx; Type: INDEX; Schema: nlp; Owner: -
--

CREATE INDEX morph_feats_idx ON nlp.morph USING btree (feats);


--
-- Name: morph_j_idx; Type: INDEX; Schema: nlp; Owner: -
--

CREATE INDEX morph_j_idx ON nlp.morph USING btree (j);


--
-- Name: mot_fonction_idx; Type: INDEX; Schema: nlp; Owner: -
--

CREATE INDEX mot_fonction_idx ON nlp.mot USING btree (fonction);


--
-- Name: mot_lexeme_idx; Type: INDEX; Schema: nlp; Owner: -
--

CREATE INDEX mot_lexeme_idx ON nlp.mot USING btree (lexeme);


--
-- Name: mot_texte_idx; Type: INDEX; Schema: nlp; Owner: -
--

CREATE INDEX mot_texte_idx ON nlp.mot USING btree (texte);


--
-- Name: nature_nom_idx; Type: INDEX; Schema: nlp; Owner: -
--

CREATE INDEX nature_nom_idx ON nlp.nature USING btree (nom);


--
-- Name: phrase_texte_idx; Type: INDEX; Schema: nlp; Owner: -
--

CREATE INDEX phrase_texte_idx ON nlp.phrase USING btree (texte);


--
-- Name: segment_texte_idx; Type: INDEX; Schema: nlp; Owner: -
--

CREATE INDEX segment_texte_idx ON nlp.segment USING btree (texte);


--
-- Name: token_texte_idx; Type: INDEX; Schema: nlp; Owner: -
--

CREATE INDEX token_texte_idx ON nlp.token USING btree (texte);


--
-- Name: classe_nom_idx; Type: INDEX; Schema: onto; Owner: -
--

CREATE INDEX classe_nom_idx ON onto.classe USING btree (nom);


--
-- Name: type_propriete_nom_idx; Type: INDEX; Schema: onto; Owner: -
--

CREATE INDEX type_propriete_nom_idx ON onto.type_propriete USING btree (nom);


--
-- Name: type_relation_nom_idx; Type: INDEX; Schema: onto; Owner: -
--

CREATE INDEX type_relation_nom_idx ON onto.type_relation USING btree (nom);


--
-- Name: morph jsonize_feats; Type: TRIGGER; Schema: nlp; Owner: -
--

CREATE TRIGGER jsonize_feats AFTER INSERT OR UPDATE OF feats ON nlp.morph FOR EACH ROW EXECUTE FUNCTION public.feats_to_json();


--
-- Name: entite entite_classe_fkey; Type: FK CONSTRAINT; Schema: eav; Owner: -
--

ALTER TABLE ONLY eav.entite
    ADD CONSTRAINT entite_classe_fkey FOREIGN KEY (classe) REFERENCES onto.classe(id);


--
-- Name: prop_date prop_date_entite_fk; Type: FK CONSTRAINT; Schema: eav; Owner: -
--

ALTER TABLE ONLY eav.prop_date
    ADD CONSTRAINT prop_date_entite_fk FOREIGN KEY (entite) REFERENCES eav.entite(id);


--
-- Name: prop_date prop_date_type_fk; Type: FK CONSTRAINT; Schema: eav; Owner: -
--

ALTER TABLE ONLY eav.prop_date
    ADD CONSTRAINT prop_date_type_fk FOREIGN KEY (type) REFERENCES onto.type_propriete(id);


--
-- Name: prop_float prop_float_entite_fk; Type: FK CONSTRAINT; Schema: eav; Owner: -
--

ALTER TABLE ONLY eav.prop_float
    ADD CONSTRAINT prop_float_entite_fk FOREIGN KEY (entite) REFERENCES eav.entite(id);


--
-- Name: prop_float prop_float_type_fk; Type: FK CONSTRAINT; Schema: eav; Owner: -
--

ALTER TABLE ONLY eav.prop_float
    ADD CONSTRAINT prop_float_type_fk FOREIGN KEY (type) REFERENCES onto.type_propriete(id);


--
-- Name: prop_int prop_int_entite_fk; Type: FK CONSTRAINT; Schema: eav; Owner: -
--

ALTER TABLE ONLY eav.prop_int
    ADD CONSTRAINT prop_int_entite_fk FOREIGN KEY (entite) REFERENCES eav.entite(id);


--
-- Name: prop_int prop_int_type_fk; Type: FK CONSTRAINT; Schema: eav; Owner: -
--

ALTER TABLE ONLY eav.prop_int
    ADD CONSTRAINT prop_int_type_fk FOREIGN KEY (type) REFERENCES onto.type_propriete(id);


--
-- Name: prop_jsonb prop_jsonb_entite_fk; Type: FK CONSTRAINT; Schema: eav; Owner: -
--

ALTER TABLE ONLY eav.prop_jsonb
    ADD CONSTRAINT prop_jsonb_entite_fk FOREIGN KEY (entite) REFERENCES eav.entite(id);


--
-- Name: prop_jsonb prop_jsonb_type_fk; Type: FK CONSTRAINT; Schema: eav; Owner: -
--

ALTER TABLE ONLY eav.prop_jsonb
    ADD CONSTRAINT prop_jsonb_type_fk FOREIGN KEY (type) REFERENCES onto.type_propriete(id);


--
-- Name: propriete propriete_entite_fkey; Type: FK CONSTRAINT; Schema: eav; Owner: -
--

ALTER TABLE ONLY eav.propriete
    ADD CONSTRAINT propriete_entite_fkey FOREIGN KEY (entite) REFERENCES eav.entite(id);


--
-- Name: propriete propriete_type_fkey; Type: FK CONSTRAINT; Schema: eav; Owner: -
--

ALTER TABLE ONLY eav.propriete
    ADD CONSTRAINT propriete_type_fkey FOREIGN KEY (type) REFERENCES onto.type_propriete(id);


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
    ADD CONSTRAINT relation_type_fkey FOREIGN KEY (type) REFERENCES onto.type_relation(id);


--
-- Name: texte texte_entite_fk; Type: FK CONSTRAINT; Schema: eav; Owner: -
--

ALTER TABLE ONLY eav.texte
    ADD CONSTRAINT texte_entite_fk FOREIGN KEY (entite) REFERENCES eav.entite(id);


--
-- Name: texte texte_type_fk; Type: FK CONSTRAINT; Schema: eav; Owner: -
--

ALTER TABLE ONLY eav.texte
    ADD CONSTRAINT texte_type_fk FOREIGN KEY (type) REFERENCES onto.type_propriete(id);


--
-- Name: lexeme lexeme_lemme_fkey; Type: FK CONSTRAINT; Schema: nlp; Owner: -
--

ALTER TABLE ONLY nlp.lexeme
    ADD CONSTRAINT lexeme_lemme_fkey FOREIGN KEY (lemme) REFERENCES nlp.lemme(id);


--
-- Name: lexeme lexeme_morph_fkey; Type: FK CONSTRAINT; Schema: nlp; Owner: -
--

ALTER TABLE ONLY nlp.lexeme
    ADD CONSTRAINT lexeme_morph_fkey FOREIGN KEY (morph) REFERENCES nlp.morph(id);


--
-- Name: lexeme lexeme_nature_fkey; Type: FK CONSTRAINT; Schema: nlp; Owner: -
--

ALTER TABLE ONLY nlp.lexeme
    ADD CONSTRAINT lexeme_nature_fkey FOREIGN KEY (nature) REFERENCES nlp.nature(id);


--
-- Name: mot mot_fonction_fkey; Type: FK CONSTRAINT; Schema: nlp; Owner: -
--

ALTER TABLE ONLY nlp.mot
    ADD CONSTRAINT mot_fonction_fkey FOREIGN KEY (fonction) REFERENCES nlp.fonction(id);


--
-- Name: mot mot_lexeme_fkey; Type: FK CONSTRAINT; Schema: nlp; Owner: -
--

ALTER TABLE ONLY nlp.mot
    ADD CONSTRAINT mot_lexeme_fkey FOREIGN KEY (lexeme) REFERENCES nlp.lexeme(id);


--
-- Name: mot mot_texte_fk; Type: FK CONSTRAINT; Schema: nlp; Owner: -
--

ALTER TABLE ONLY nlp.mot
    ADD CONSTRAINT mot_texte_fk FOREIGN KEY (texte) REFERENCES eav.texte(id);


--
-- Name: phrase phrase_texte_fk; Type: FK CONSTRAINT; Schema: nlp; Owner: -
--

ALTER TABLE ONLY nlp.phrase
    ADD CONSTRAINT phrase_texte_fk FOREIGN KEY (texte) REFERENCES eav.texte(id);


--
-- Name: span phrase_texte_fk; Type: FK CONSTRAINT; Schema: nlp; Owner: -
--

ALTER TABLE ONLY nlp.span
    ADD CONSTRAINT phrase_texte_fk FOREIGN KEY (texte) REFERENCES eav.texte(id);


--
-- Name: segment segment_texte_fkey; Type: FK CONSTRAINT; Schema: nlp; Owner: -
--

ALTER TABLE ONLY nlp.segment
    ADD CONSTRAINT segment_texte_fkey FOREIGN KEY (texte) REFERENCES eav.texte(id);


--
-- Name: token token_texte_fk; Type: FK CONSTRAINT; Schema: nlp; Owner: -
--

ALTER TABLE ONLY nlp.token
    ADD CONSTRAINT token_texte_fk FOREIGN KEY (texte) REFERENCES eav.texte(id);


--
-- PostgreSQL database dump complete
--

