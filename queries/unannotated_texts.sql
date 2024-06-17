-- SELECT les textes pas encore annotés.
with unannotated as (
    select t.id from texte t
    except
    select distinct s.texte from segment s
) select t.id, t.val from texte t
join unannotated u on u.id = t.id;
