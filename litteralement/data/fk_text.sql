-- foreign key nlp tables -> texte.

alter table mot add constraint mot_texte_fk
foreign key (texte) references text(id);

alter table token add constraint token_texte_fk
foreign key (texte) references text(id);

alter table segment add constraint segment_texte_fk
foreign key (texte) references text(id);

alter table span add constraint span_texte_fk
foreign key (texte) references text(id);
