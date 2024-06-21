-- une vue pour les lemmes qui ne sont pas des stop words.
--
create view nonstop_lemme as
with nonstop as (
    select l.id
    from nlp.lemme l
    except
    select l.id
    from nlp.lemme l
    join stopword s on s.lemme = l.graphie
)
select
    l.*
from nonstop n
join nlp.lemme l on l.id = n.id;


-- une vue pour les lexèmes qui ne sont pas des stop words.
--
create view nonstop_lexeme as
with nonstop as (
    select l.id
    from nlp.lexeme l
    except
    select l.id
    from nlp.lexeme l
    join nlp.stopword s on s.norme = l.norme
)
select
    l.*
from nonstop n
join nlp.lexeme l on l.id = n.id;
