-- Run against a migrated project. All synthetic fixtures roll back, even on failure.
begin;
set local role service_role;
do $$
declare
    owner_id text := 'verify-' || gen_random_uuid()::text;
    lab_id text := 'verify-lab-' || gen_random_uuid()::text;
    code text := 'BL-' || upper(left(replace(gen_random_uuid()::text, '-', ''), 20));
    rows jsonb := '[{"date":"2026-01-01","blood_type":"O-","donations":10,"demand":12,"inventory":160,"holiday":false}]';
    changed jsonb;
    report jsonb;
    batch jsonb;
    first_id text;
    rid text;
    import_count integer;
begin
    assert public.bloodsight_storage_status()->>'schema_version' = '1';
    batch := public.bloodsight_import_history(owner_id,'verifier',rows,'synthetic.csv',repeat('a',64));
    first_id := batch->>'id';
    assert (batch->>'row_count')::int = 1 and not (batch->>'duplicate')::boolean;
    batch := public.bloodsight_import_history(owner_id,'verifier',rows,'synthetic.csv',repeat('a',64));
    assert (batch->>'duplicate')::boolean and batch->>'id' = first_id;

    changed := jsonb_set(rows,'{0,inventory}','500');
    perform public.bloodsight_import_history(owner_id,'verifier',changed,'correction.csv',repeat('b',64));
    assert (select inventory=500 from public.bloodsight_history where place_id=owner_id);
    batch := public.bloodsight_import_history(owner_id,'verifier',rows,'synthetic.csv',repeat('a',64));
    assert not (batch->>'duplicate')::boolean;
    assert (select inventory=160 from public.bloodsight_history where place_id=owner_id);

    select count(*) into import_count from public.bloodsight_imports where owner=owner_id;
    begin
        perform public.bloodsight_import_history(owner_id,'verifier',
            changed || '[{"date":"2026-01-02","blood_type":"O-","donations":-1,"demand":12,"inventory":1,"holiday":false}]',
            'invalid.csv',repeat('c',64));
        raise exception 'Invalid import unexpectedly succeeded';
    exception when check_violation then null;
    end;
    assert (select count(*)=import_count from public.bloodsight_imports where owner=owner_id);
    assert (select inventory=160 from public.bloodsight_history where place_id=owner_id);

    report := jsonb_build_array(jsonb_build_object('lab_code',code,'date','2026-09-21',
        'blood_type','O-','lab','Synthetic test lab','urgent',true,'values',
        '[{"key":"ferritin","name":"Ferritin","unit":"ng/mL","value":20,"low":30,"high":300,"line":1}]'::jsonb));
    batch := public.bloodsight_import_reports(lab_id,'verifier',report,'synthetic.json',repeat('d',64));
    assert (batch->>'row_count')::int=1 and not (batch->>'duplicate')::boolean;
    select id into rid from public.bloodsight_reports where lab_code=code;
    assert (select flag='Low' from public.bloodsight_report_values where report_id=rid);
    assert (select status='draft' from public.bloodsight_reports where id=rid);
    batch := public.bloodsight_import_reports(lab_id,'verifier',report,'synthetic.json',repeat('d',64));
    assert (batch->>'duplicate')::boolean;
    begin
        perform public.bloodsight_publish_report(lab_id,'verifier',rid,false);
        raise exception 'Urgent report published without phone confirmation';
    exception when sqlstate 'BS001' then null;
    end;
    begin
        perform public.bloodsight_publish_report(owner_id,'verifier',rid,true);
        raise exception 'Wrong organisation published a report';
    exception when sqlstate 'BS002' then null;
    end;
    assert public.bloodsight_publish_report(lab_id,'verifier',rid,true);
    assert not public.bloodsight_publish_report(lab_id,'verifier',rid,true);
    assert (select status='published' and phoned_by='verifier' from public.bloodsight_reports where id=rid);

    select count(*) into import_count from public.bloodsight_imports where owner=lab_id;
    begin
        perform public.bloodsight_import_reports(lab_id,'verifier',
            jsonb_set(report,'{0,date}','"2026-09-20"') || report, 'conflict.json',repeat('e',64));
        raise exception 'Duplicate patient/date import unexpectedly succeeded';
    exception when unique_violation then null;
    end;
    assert (select count(*)=import_count from public.bloodsight_imports where owner=lab_id);
    assert (select count(*)=1 from public.bloodsight_reports where org=lab_id);

    assert not exists (
        select 1 from pg_class c join pg_namespace n on n.oid=c.relnamespace
        where n.nspname='public' and c.relname like 'bloodsight_%' and c.relkind='r'
          and (not c.relrowsecurity or has_table_privilege('anon',c.oid,'select,insert,update,delete')
               or has_table_privilege('authenticated',c.oid,'select,insert,update,delete'))
    );
    assert not exists (
        select 1 from pg_proc p join pg_namespace n on n.oid=p.pronamespace
        where n.nspname='public' and p.proname like 'bloodsight_%'
          and (p.prosecdef or has_function_privilege('anon',p.oid,'execute')
               or has_function_privilege('authenticated',p.oid,'execute'))
    );
end;
$$;
select 'PASS: atomic imports, repeats, corrections, report values, publish guards, permissions' as result;
rollback;
