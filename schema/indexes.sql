create index if not exists classe_nom_idx on classe(nom);
create index if not exists nature_nom_idx on nature(nom);
create index if not exists fonction_nom_idx on fonction(nom);
create index if not exists type_propriete_nom_idx on type_propriete(nom);
create index if not exists type_relation_nom_idx on type_relation(nom);

create index if not exists entite_classe_idx on entite(classe);

create index if not exists texte_entite_idx on texte(entite);
create index if not exists texte_type_idx on texte(type);

create index if not exists segment_texte_idx on segment(texte);

create index if not exists phrase_texte_idx on phrase(texte);

create index if not exists token_texte_idx on token(texte);

create index if not exists mot_fonction_idx on mot(fonction);
create index if not exists mot_lexeme_idx on mot(lexeme);
create index if not exists mot_texte_idx on mot(texte);

create index if not exists lexeme_lemme_idx on lexeme(lemme);
create index if not exists lexeme_nature_idx on lexeme(nature);
create index if not exists lexeme_morph_idx on lexeme(morph);
create index if not exists lexeme_vv_pos_idx on lexeme(vv_pos);
create index if not exists lexeme_vv_morph_idx on lexeme(vv_morph);

create index if not exists propriete_entite_idx on propriete(entite);
create index if not exists propriete_type_idx on propriete(type);

create index if not exists prop_int_entite_idx on prop_int(entite);
create index if not exists prop_int_type_idx on prop_int(type);

create index if not exists prop_float_entite_idx on prop_float(entite);
create index if not exists prop_float_type_idx on prop_float(type);

create index if not exists prop_jsonb_entite_idx on prop_jsonb(entite);
create index if not exists prop_jsonb_type_idx on prop_jsonb(type);

create index if not exists relation_objet_idx on relation(objet);
create index if not exists relation_sujet_idx on relation(sujet);
create index if not exists relation_type_idx on relation(type);
