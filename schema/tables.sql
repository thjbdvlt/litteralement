-- 0. Note sur le modèle EAV hybride:
-- implémentation d'un modèle EAV hybride pour l'analyse de texte, avec une séparation stricte entre la partie EAV (entité, propriété, valeurs, relations, classe) et la partie relationnelle standard consacrée à l'analyse de textes (mots, segments, pos-tags, morphologies, etc.)
-- (un modèle EAV complet est souvent peu recommandé par la communauté des développeur·euses pour des raisons de performances, mais aussi de lisibilité des requêtes -- et dans le cas d'un travail académique, c'est peut-être cette seconde raison qui doit le plus décourager ce choix.)

create schema if not exists nlp;
create schema if not exists onto;
alter database litteralement set search_path to public, onto, nlp;

-- 1. EAV
-- les classes qui construisent l'ontologie de la partie EAV de la base de données. toutes ces classes ont la même structure, et c'est pourquoi elles sont toutes définies sur la base de la table 'classe'. quoi qu'elles soient toutes structurellement identiques, elles ont des positions différentes dans la base de données et accueillent des objets qui, eux aussi, ont des natures différentes, c'est pourquoi il ne me semble ni judicieux ni utile d'en faire une seule table (qui rendrait, en plus, les requêtes plus compliquées et nécessiterait l'utilisation d'index pour éviter des baisses de performances, quoique légères).

-- 1.1. les tables qui constituent l'ontologie: classes, types de propriétés et types de relation.
create table onto.classe (
    id smallint primary key 
        generated by default as identity not null, 
    nom text not null,
    definition text,
    unique (nom)
);
create table onto.type_relation (like onto.classe including all);
create table onto.type_propriete (like onto.classe including all);

-- 1.2. les tables qui contiennent les instances (entités, propriétés, relations, instance_a_tag, propriete_value) de la partie public.

create table public.entite (
    id int primary key 
        generated by default as identity not null, 
    classe smallint references onto.classe(id) not null
);

create table public.relation (
    id int primary key 
        generated by default as identity not null,
    type smallint references onto.type_relation(id) not null,
    sujet int references public.entite(id) not null,
    objet int references public.entite(id) not null
);

create table public.propriete (
    -- pour les propriétés qui ne nécessite aucune valeur, par exemple 'is_fictional'.
    type smallint references onto.type_propriete(id) not null,
    entite int references public.entite(id) not null
);
-- 1.2.1. les propriétés qui nécessitent des valeurs ont, pour chaque datatype, une table correspondante, qui hérite de la table propriété.
create table public.prop_text (val text) inherits (public.propriete);
create table public.prop_int (val int) inherits (public.propriete);
create table public.prop_float (val float) inherits (public.propriete);
create table public.prop_date (val timestamp) inherits (public.propriete);
create table public.prop_jsonb (val jsonb) inherits (public.propriete);

-- 1.3. la table qui fait la liaison entre les deux parties de la base de données (EAV et relationnel standard) est la table texte.

create table nlp.texte(
    -- la table 'texte' est différente de la table 'prop_text' car elle contient des objets avec un identifiant, auquel peut faire référence les tables du schéma 'nlp'. (dans les faits, on va probablement tout mettre dans texte par simplicité.)
    id int primary key 
        generated by default as identity not null,
    val text
) inherits(propriete);

-- 2. la partie relationnelle standard de la base de données, pour l'analyse linguistique qui se fait à l'aide de catégories, d'outils conceptuels indépendant des objets matériels et sociaux qui contiennent les textes.

-- 2.1. première partie décrit les mots possibles et les types de segment, elle est en quelque sorte idéale et abstraite.

create table nlp.nature (like onto.type_propriete including all);
create table nlp.fonction (like onto.type_propriete including all);

create table nlp.morph (
    id smallint primary key
        generated by default as identity not null,
    feats text,
    j jsonb
);

create table nlp.lemme (
    id int primary key
        generated by default as identity not null,
    graphie text,
    stopword boolean default false
);

create table nlp.lexeme (
    id int primary key
        generated by default as identity not null,
    lemme smallint references nlp.lemme (id) not null,
    nature smallint references nlp.nature(id) not null,
    morph smallint references nlp.morph(id) not null,
    norme text not null
);

-- 2.2. seconde partie décrit les mots et segments réels, utilisés dans des contextes (des textes).

create table nlp.segment (
    texte int references nlp.texte(id) not null,
    debut int not null,
    fin int not null
);

create table nlp.phrase () inherits (nlp.segment);

create table nlp.span (attrs jsonb) inherits (nlp.segment);

create table nlp.token (num int not null) inherits (nlp.segment);

create table nlp.mot(
    fonction smallint references nlp.fonction(id) not null,
    lexeme int references nlp.lexeme(id),
    noyau int
) inherits (nlp.token);


-- 3. le schéma import sert à ajouter les données.

create schema if not exists import;

create table import._data(
    j jsonb
);

create table import._document(
    id int,
    j jsonb
);

create table import._lookup_entite(
    dataset smallint,
    id_dataset int,
    id_entite int
);
