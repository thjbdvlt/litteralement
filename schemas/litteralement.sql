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
-- Name: litteralement; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA litteralement;


--
-- Name: feats_to_json(); Type: FUNCTION; Schema: litteralement; Owner: -
--

CREATE FUNCTION litteralement.feats_to_json() RETURNS trigger
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
-- Name: segment; Type: TABLE; Schema: litteralement; Owner: -
--

CREATE TABLE litteralement.segment (
    texte integer NOT NULL,
    debut integer NOT NULL,
    fin integer NOT NULL
);


--
-- Name: token; Type: TABLE; Schema: litteralement; Owner: -
--

CREATE TABLE litteralement.token (
    num integer NOT NULL,
    phrase integer
)
INHERITS (litteralement.segment);


--
-- Name: mot; Type: TABLE; Schema: litteralement; Owner: -
--

CREATE TABLE litteralement.mot (
    fonction smallint NOT NULL,
    lexeme integer NOT NULL,
    noyau integer NOT NULL
)
INHERITS (litteralement.token);
ALTER TABLE ONLY litteralement.mot ALTER COLUMN phrase SET NOT NULL;


--
-- Name: has_aux(litteralement.mot, integer); Type: FUNCTION; Schema: litteralement; Owner: -
--

CREATE FUNCTION litteralement.has_aux(litteralement.mot, n integer) RETURNS litteralement.mot
    LANGUAGE sql
    AS $_$
select
    m2
from mot m2
join lexeme x2 on m2.lexeme = x2.id
join nature n on n.id = x2.nature
join fonction f on f.id = m2.fonction
where $1.texte = m2.texte and $1.num = m2.noyau
and (n.nom in ('aux', 'verb') or f.nom like 'aux:%')
limit $2
$_$;


--
-- Name: has_head(litteralement.mot); Type: FUNCTION; Schema: litteralement; Owner: -
--

CREATE FUNCTION litteralement.has_head(litteralement.mot) RETURNS litteralement.mot
    LANGUAGE sql
    AS $_$
select
    m2
from mot m2
join lexeme x2 on m2.lexeme = x2.id
join lexeme x1 on $1.lexeme = x1.id
where $1.texte = m2.texte and $1.noyau = m2.num
$_$;


--
-- Name: is_head_of(litteralement.mot); Type: FUNCTION; Schema: litteralement; Owner: -
--

CREATE FUNCTION litteralement.is_head_of(litteralement.mot) RETURNS litteralement.mot
    LANGUAGE sql
    AS $_$
select
    m2
from mot m2
join lexeme x2 on m2.lexeme = x2.id
join lexeme x1 on $1.lexeme = x1.id
where $1.texte = m2.texte and $1.num = m2.noyau
$_$;


--
-- Name: fonction; Type: TABLE; Schema: litteralement; Owner: -
--

CREATE TABLE litteralement.fonction (
    id smallint NOT NULL,
    nom text NOT NULL,
    definition text
);


--
-- Name: fonction_id_seq; Type: SEQUENCE; Schema: litteralement; Owner: -
--

ALTER TABLE litteralement.fonction ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME litteralement.fonction_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: lemme; Type: TABLE; Schema: litteralement; Owner: -
--

CREATE TABLE litteralement.lemme (
    id integer NOT NULL,
    graphie text NOT NULL
);


--
-- Name: lemme_id_seq; Type: SEQUENCE; Schema: litteralement; Owner: -
--

ALTER TABLE litteralement.lemme ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME litteralement.lemme_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: lexeme; Type: TABLE; Schema: litteralement; Owner: -
--

CREATE TABLE litteralement.lexeme (
    id integer NOT NULL,
    lemme integer NOT NULL,
    nature smallint NOT NULL,
    morph smallint NOT NULL,
    norme text NOT NULL
);


--
-- Name: lexeme_id_seq; Type: SEQUENCE; Schema: litteralement; Owner: -
--

ALTER TABLE litteralement.lexeme ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME litteralement.lexeme_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: morph; Type: TABLE; Schema: litteralement; Owner: -
--

CREATE TABLE litteralement.morph (
    id smallint NOT NULL,
    feats text,
    j jsonb
);


--
-- Name: morph_id_seq; Type: SEQUENCE; Schema: litteralement; Owner: -
--

ALTER TABLE litteralement.morph ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME litteralement.morph_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: nature; Type: TABLE; Schema: litteralement; Owner: -
--

CREATE TABLE litteralement.nature (
    id smallint NOT NULL,
    nom text NOT NULL,
    definition text
);


--
-- Name: nature_id_seq; Type: SEQUENCE; Schema: litteralement; Owner: -
--

ALTER TABLE litteralement.nature ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME litteralement.nature_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: stopword; Type: TABLE; Schema: litteralement; Owner: -
--

CREATE TABLE litteralement.stopword (
    norme text,
    lemme text
);


--
-- Name: nonstop_lemme; Type: VIEW; Schema: litteralement; Owner: -
--

CREATE VIEW litteralement.nonstop_lemme AS
 WITH nonstop AS (
         SELECT l_1.id
           FROM litteralement.lemme l_1
        EXCEPT
         SELECT l_1.id
           FROM (litteralement.lemme l_1
             JOIN litteralement.stopword s ON ((s.lemme = l_1.graphie)))
        )
 SELECT l.id,
    l.graphie
   FROM (nonstop n
     JOIN litteralement.lemme l ON ((l.id = n.id)));


--
-- Name: nonstop_lexeme; Type: VIEW; Schema: litteralement; Owner: -
--

CREATE VIEW litteralement.nonstop_lexeme AS
 WITH nonstop AS (
         SELECT l_1.id
           FROM litteralement.lexeme l_1
        EXCEPT
         SELECT l_1.id
           FROM (litteralement.lexeme l_1
             JOIN litteralement.stopword s ON ((s.norme = l_1.norme)))
        )
 SELECT l.id,
    l.lemme,
    l.nature,
    l.morph,
    l.norme
   FROM (nonstop n
     JOIN litteralement.lexeme l ON ((l.id = n.id)));


--
-- Name: phrase; Type: TABLE; Schema: litteralement; Owner: -
--

CREATE TABLE litteralement.phrase (
)
INHERITS (litteralement.segment);


--
-- Name: span; Type: TABLE; Schema: litteralement; Owner: -
--

CREATE TABLE litteralement.span (
    attrs jsonb
)
INHERITS (litteralement.segment);

--
-- Name: _entite; Type: TABLE; Schema: import; Owner: -
--

CREATE TABLE litteralement._document (
    id integer,
    j jsonb
);

--
-- Name: fonction fonction_nom_key; Type: CONSTRAINT; Schema: litteralement; Owner: -
--

ALTER TABLE ONLY litteralement.fonction
    ADD CONSTRAINT fonction_nom_key UNIQUE (nom);


--
-- Name: fonction fonction_pkey; Type: CONSTRAINT; Schema: litteralement; Owner: -
--

ALTER TABLE ONLY litteralement.fonction
    ADD CONSTRAINT fonction_pkey PRIMARY KEY (id);


--
-- Name: lemme lemme_graphie_key; Type: CONSTRAINT; Schema: litteralement; Owner: -
--

ALTER TABLE ONLY litteralement.lemme
    ADD CONSTRAINT lemme_graphie_key UNIQUE (graphie);


--
-- Name: lemme lemme_pkey; Type: CONSTRAINT; Schema: litteralement; Owner: -
--

ALTER TABLE ONLY litteralement.lemme
    ADD CONSTRAINT lemme_pkey PRIMARY KEY (id);


--
-- Name: lexeme lexeme_pkey; Type: CONSTRAINT; Schema: litteralement; Owner: -
--

ALTER TABLE ONLY litteralement.lexeme
    ADD CONSTRAINT lexeme_pkey PRIMARY KEY (id);


--
-- Name: morph morph_feats_key; Type: CONSTRAINT; Schema: litteralement; Owner: -
--

ALTER TABLE ONLY litteralement.morph
    ADD CONSTRAINT morph_feats_key UNIQUE (feats);


--
-- Name: morph morph_pkey; Type: CONSTRAINT; Schema: litteralement; Owner: -
--

ALTER TABLE ONLY litteralement.morph
    ADD CONSTRAINT morph_pkey PRIMARY KEY (id);


--
-- Name: nature nature_nom_key; Type: CONSTRAINT; Schema: litteralement; Owner: -
--

ALTER TABLE ONLY litteralement.nature
    ADD CONSTRAINT nature_nom_key UNIQUE (nom);


--
-- Name: nature nature_pkey; Type: CONSTRAINT; Schema: litteralement; Owner: -
--

ALTER TABLE ONLY litteralement.nature
    ADD CONSTRAINT nature_pkey PRIMARY KEY (id);


--
-- Name: token token_texte_num_key; Type: CONSTRAINT; Schema: litteralement; Owner: -
--

ALTER TABLE ONLY litteralement.token
    ADD CONSTRAINT token_texte_num_key UNIQUE (texte, num);


--
-- Name: fonction_nom_idx; Type: INDEX; Schema: litteralement; Owner: -
--

CREATE INDEX fonction_nom_idx ON litteralement.fonction USING btree (nom);


--
-- Name: lexeme_lemme_idx; Type: INDEX; Schema: litteralement; Owner: -
--

CREATE INDEX lexeme_lemme_idx ON litteralement.lexeme USING btree (lemme);


--
-- Name: lexeme_morph_idx; Type: INDEX; Schema: litteralement; Owner: -
--

CREATE INDEX lexeme_morph_idx ON litteralement.lexeme USING btree (morph);


--
-- Name: lexeme_nature_idx; Type: INDEX; Schema: litteralement; Owner: -
--

CREATE INDEX lexeme_nature_idx ON litteralement.lexeme USING btree (nature);


--
-- Name: morph_feats_idx; Type: INDEX; Schema: litteralement; Owner: -
--

CREATE INDEX morph_feats_idx ON litteralement.morph USING btree (feats);


--
-- Name: morph_j_idx; Type: INDEX; Schema: litteralement; Owner: -
--

CREATE INDEX morph_j_idx ON litteralement.morph USING btree (j);


--
-- Name: mot_fonction_idx; Type: INDEX; Schema: litteralement; Owner: -
--

CREATE INDEX mot_fonction_idx ON litteralement.mot USING btree (fonction);


--
-- Name: mot_lexeme_idx; Type: INDEX; Schema: litteralement; Owner: -
--

CREATE INDEX mot_lexeme_idx ON litteralement.mot USING btree (lexeme);


--
-- Name: mot_noyau_idx; Type: INDEX; Schema: litteralement; Owner: -
--

CREATE INDEX mot_noyau_idx ON litteralement.mot USING btree (noyau);


--
-- Name: mot_num_idx; Type: INDEX; Schema: litteralement; Owner: -
--

CREATE INDEX mot_num_idx ON litteralement.mot USING btree (num);


--
-- Name: mot_phrase_idx; Type: INDEX; Schema: litteralement; Owner: -
--

CREATE INDEX mot_phrase_idx ON litteralement.mot USING btree (phrase);


--
-- Name: mot_texte_idx; Type: INDEX; Schema: litteralement; Owner: -
--

CREATE INDEX mot_texte_idx ON litteralement.mot USING btree (texte);


--
-- Name: nature_nom_idx; Type: INDEX; Schema: litteralement; Owner: -
--

CREATE INDEX nature_nom_idx ON litteralement.nature USING btree (nom);


--
-- Name: phrase_texte_idx; Type: INDEX; Schema: litteralement; Owner: -
--

CREATE INDEX phrase_texte_idx ON litteralement.phrase USING btree (texte);


--
-- Name: segment_texte_idx; Type: INDEX; Schema: litteralement; Owner: -
--

CREATE INDEX segment_texte_idx ON litteralement.segment USING btree (texte);


--
-- Name: token_texte_idx; Type: INDEX; Schema: litteralement; Owner: -
--

CREATE INDEX token_texte_idx ON litteralement.token USING btree (texte);


--
-- Name: morph jsonize_feats; Type: TRIGGER; Schema: litteralement; Owner: -
--

CREATE TRIGGER jsonize_feats AFTER INSERT OR UPDATE OF feats ON litteralement.morph FOR EACH ROW EXECUTE FUNCTION litteralement.feats_to_json();


--
-- Name: lexeme lexeme_lemme_fkey; Type: FK CONSTRAINT; Schema: litteralement; Owner: -
--

ALTER TABLE ONLY litteralement.lexeme
    ADD CONSTRAINT lexeme_lemme_fkey FOREIGN KEY (lemme) REFERENCES litteralement.lemme(id);


--
-- Name: lexeme lexeme_morph_fkey; Type: FK CONSTRAINT; Schema: litteralement; Owner: -
--

ALTER TABLE ONLY litteralement.lexeme
    ADD CONSTRAINT lexeme_morph_fkey FOREIGN KEY (morph) REFERENCES litteralement.morph(id);


--
-- Name: lexeme lexeme_nature_fkey; Type: FK CONSTRAINT; Schema: litteralement; Owner: -
--

ALTER TABLE ONLY litteralement.lexeme
    ADD CONSTRAINT lexeme_nature_fkey FOREIGN KEY (nature) REFERENCES litteralement.nature(id);


--
-- Name: mot mot_fonction_fkey; Type: FK CONSTRAINT; Schema: litteralement; Owner: -
--

ALTER TABLE ONLY litteralement.mot
    ADD CONSTRAINT mot_fonction_fkey FOREIGN KEY (fonction) REFERENCES litteralement.fonction(id);


--
-- Name: mot mot_lexeme_fkey; Type: FK CONSTRAINT; Schema: litteralement; Owner: -
--

ALTER TABLE ONLY litteralement.mot
    ADD CONSTRAINT mot_lexeme_fkey FOREIGN KEY (lexeme) REFERENCES litteralement.lexeme(id);


--
-- PostgreSQL database dump complete
--

