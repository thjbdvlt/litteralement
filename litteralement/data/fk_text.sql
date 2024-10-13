-- foreign key nlp tables -> texte.

alter table phrase add constraint phrase_texte_fk
foreign key (texte) references texte(id);
