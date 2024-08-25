create or replace function feats_to_json()
returns trigger
language plpgsql
as $function$
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
$function$;


create or replace trigger jsonize_feats
after insert or update of feats on morph
for each row
execute function feats_to_json();
