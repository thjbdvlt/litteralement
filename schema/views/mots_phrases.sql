-- une vue pour les mots dans des phrases
--
create view mot_phrase as
select
    p.debut as phrase_debut,
    m.*
from mot m
join phrase p on p.texte = m.texte 
and p.debut <= m.debut
and p.fin >= m.fin;
