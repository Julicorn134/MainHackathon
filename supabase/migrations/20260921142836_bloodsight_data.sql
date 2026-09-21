-- BloodSight's synthetic-data prototype. Only the trusted Streamlit server may
-- access these tables. Demo identity/booking state remains local in store.py.
create table public.bloodsight_facilities (
    id text primary key check (length(id) between 1 and 100),
    kind text not null check (kind in ('centre', 'lab')),
    created_at timestamptz not null default now()
);

create table public.bloodsight_imports (
    id uuid primary key default gen_random_uuid(),
    kind text not null check (kind in ('history', 'reports')),
    owner text not null references public.bloodsight_facilities(id),
    filename text not null check (length(filename) between 1 and 160),
    digest text not null check (digest ~ '^[a-f0-9]{64}$'),
    row_count integer not null check (row_count between 1 and 20000),
    created_by text not null check (length(created_by) between 1 and 100),
    created_at timestamptz not null default now()
);
-- Deliberately not unique: replaying a file after a correction is a new import.
create index bloodsight_imports_lookup on public.bloodsight_imports(owner, kind, digest, created_at desc);

create table public.bloodsight_history (
    place_id text not null references public.bloodsight_facilities(id),
    date date not null,
    blood_type text not null check (blood_type in ('O-','O+','A-','A+','B-','B+','AB-','AB+')),
    donations integer not null check (donations between 0 and 10000000),
    demand integer not null check (demand between 0 and 10000000),
    inventory integer not null check (inventory between 0 and 10000000),
    holiday boolean not null,
    import_id uuid not null references public.bloodsight_imports(id),
    updated_at timestamptz not null default now(),
    primary key (place_id, date, blood_type)
);
create index bloodsight_history_import on public.bloodsight_history(import_id);

create table public.bloodsight_reports (
    id text primary key default ('IMP-' || gen_random_uuid()::text),
    org text not null references public.bloodsight_facilities(id),
    lab_code text not null check (lab_code ~ '^BL-[A-Z0-9-]{2,28}$'),
    date date not null,
    blood_type text not null check (blood_type in ('O-','O+','A-','A+','B-','B+','AB-','AB+')),
    lab text not null check (length(lab) between 1 and 100 and lab !~ '[<>]'),
    urgent boolean not null,
    status text not null default 'draft' check (status in ('draft','published')),
    phoned_by text,
    published_at timestamptz,
    import_id uuid not null references public.bloodsight_imports(id),
    unique (lab_code, date),
    check ((status = 'draft' and published_at is null) or (status = 'published' and published_at is not null)),
    check (status <> 'published' or not urgent or phoned_by is not null)
);
create index bloodsight_reports_org on public.bloodsight_reports(org, date desc);
create index bloodsight_reports_import on public.bloodsight_reports(import_id);

create table public.bloodsight_report_values (
    report_id text not null references public.bloodsight_reports(id),
    key text not null check (key ~ '^[a-z][a-z0-9_]{0,39}$'),
    name text not null check (length(name) between 1 and 100 and name !~ '[<>]'),
    unit text not null check (length(unit) between 1 and 40 and unit !~ '[<>]'),
    value numeric not null check (value between -10000000 and 10000000),
    low numeric not null check (low between -10000000 and 10000000),
    high numeric not null check (high between -10000000 and 10000000),
    flag text generated always as (case when value < low then 'Low' when value > high then 'High' else 'In range' end) stored,
    line integer not null check (line between 1 and 100),
    primary key (report_id, key),
    unique (report_id, line),
    check (low <= high)
);

alter table public.bloodsight_facilities enable row level security;
alter table public.bloodsight_imports enable row level security;
alter table public.bloodsight_history enable row level security;
alter table public.bloodsight_reports enable row level security;
alter table public.bloodsight_report_values enable row level security;
-- No browser/anonymous policies: all access is through the trusted server.
revoke all on table public.bloodsight_facilities, public.bloodsight_imports,
    public.bloodsight_history, public.bloodsight_reports, public.bloodsight_report_values from public, anon, authenticated;
grant select, insert, update on table public.bloodsight_facilities, public.bloodsight_imports,
    public.bloodsight_history, public.bloodsight_reports, public.bloodsight_report_values to service_role;

create function public.bloodsight_storage_status() returns jsonb
language sql stable security invoker set search_path = '' as $$
    select jsonb_build_object('schema_version', 1);
$$;

create function public.bloodsight_import_history(
    p_owner text, p_actor text, p_rows jsonb, p_filename text, p_digest text
) returns jsonb language plpgsql security invoker set search_path = '' as $$
declare
    batch public.bloodsight_imports;
    unchanged boolean;
begin
    if p_rows is null or jsonb_typeof(p_rows) <> 'array' then
        raise exception using errcode = 'BS003', message = 'Expected an array';
    end if;
    if jsonb_array_length(p_rows) not between 1 and 20000 then
        raise exception using errcode = 'BS003', message = 'Invalid batch size';
    end if;
    -- Serialize imports for one facility, including duplicate/correction decisions.
    perform pg_advisory_xact_lock(hashtextextended('bloodsight:history:' || p_owner, 0));
    insert into public.bloodsight_facilities(id, kind) values (p_owner, 'centre') on conflict do nothing;
    if not exists (select 1 from public.bloodsight_facilities where id = p_owner and kind = 'centre') then
        raise exception using errcode = 'BS003', message = 'Wrong facility kind';
    end if;

    select not exists (
        select 1 from jsonb_to_recordset(p_rows) as r(date date, blood_type text, donations integer, demand integer, inventory integer, holiday boolean)
        left join public.bloodsight_history h on h.place_id = p_owner and h.date = r.date and h.blood_type = r.blood_type
        where h.place_id is null or (h.donations,h.demand,h.inventory,h.holiday) is distinct from (r.donations,r.demand,r.inventory,r.holiday)
    ) into unchanged;
    if unchanged then
        select * into batch from public.bloodsight_imports where owner = p_owner and kind = 'history' and digest = p_digest
            order by created_at desc limit 1;
        if found then return to_jsonb(batch) || jsonb_build_object('duplicate', true); end if;
    end if;

    insert into public.bloodsight_imports(kind, owner, filename, digest, row_count, created_by)
        values ('history', p_owner, p_filename, p_digest, jsonb_array_length(p_rows), p_actor) returning * into batch;
    insert into public.bloodsight_history(place_id,date,blood_type,donations,demand,inventory,holiday,import_id)
        select p_owner, r.date,r.blood_type,r.donations,r.demand,r.inventory,r.holiday,batch.id
        from jsonb_to_recordset(p_rows) as r(date date, blood_type text, donations integer, demand integer, inventory integer, holiday boolean)
        on conflict (place_id,date,blood_type) do update set
            donations=excluded.donations, demand=excluded.demand, inventory=excluded.inventory,
            holiday=excluded.holiday, import_id=excluded.import_id, updated_at=now();
    return to_jsonb(batch) || jsonb_build_object('duplicate', false);
end;
$$;

create function public.bloodsight_import_reports(
    p_owner text, p_actor text, p_rows jsonb, p_filename text, p_digest text
) returns jsonb language plpgsql security invoker set search_path = '' as $$
declare
    batch public.bloodsight_imports;
    report jsonb;
    report_id text;
begin
    if p_rows is null or jsonb_typeof(p_rows) <> 'array' then
        raise exception using errcode = 'BS003', message = 'Expected an array';
    end if;
    if jsonb_array_length(p_rows) not between 1 and 200 then
        raise exception using errcode = 'BS003', message = 'Invalid batch size';
    end if;
    perform pg_advisory_xact_lock(hashtextextended('bloodsight:reports:' || p_owner, 0));
    insert into public.bloodsight_facilities(id, kind) values (p_owner, 'lab') on conflict do nothing;
    if not exists (select 1 from public.bloodsight_facilities where id = p_owner and kind = 'lab') then
        raise exception using errcode = 'BS003', message = 'Wrong facility kind';
    end if;
    select * into batch from public.bloodsight_imports where owner = p_owner and kind = 'reports' and digest = p_digest
        order by created_at desc limit 1;
    if found then return to_jsonb(batch) || jsonb_build_object('duplicate', true); end if;

    insert into public.bloodsight_imports(kind,owner,filename,digest,row_count,created_by)
        values ('reports',p_owner,p_filename,p_digest,jsonb_array_length(p_rows),p_actor) returning * into batch;
    for report in select value from jsonb_array_elements(p_rows) loop
        if report->'values' is null or jsonb_typeof(report->'values') <> 'array' then
            raise exception using errcode = 'BS003', message = 'Expected measured values';
        end if;
        if jsonb_array_length(report->'values') not between 1 and 100 then
            raise exception using errcode = 'BS003', message = 'Invalid value count';
        end if;
        insert into public.bloodsight_reports(org,lab_code,date,blood_type,lab,urgent,import_id)
            values (p_owner,report->>'lab_code',(report->>'date')::date,report->>'blood_type',
                    report->>'lab',(report->>'urgent')::boolean,batch.id) returning id into report_id;
        insert into public.bloodsight_report_values(report_id,key,name,unit,value,low,high,line)
            select report_id,r.key,r.name,r.unit,r.value,r.low,r.high,r.line
            from jsonb_to_recordset(report->'values') as r(key text,name text,unit text,value numeric,low numeric,high numeric,line integer);
    end loop;
    return to_jsonb(batch) || jsonb_build_object('duplicate', false);
end;
$$;

create function public.bloodsight_publish_report(p_owner text,p_actor text,p_report_id text,p_phoned boolean)
returns boolean language plpgsql security invoker set search_path = '' as $$
declare report public.bloodsight_reports;
begin
    select * into report from public.bloodsight_reports where id=p_report_id and org=p_owner for update;
    if not found then raise exception using errcode = 'BS002', message = 'Report not found'; end if;
    if report.status = 'published' then return false; end if;
    if report.urgent and not coalesce(p_phoned, false) and report.phoned_by is null then
        raise exception using errcode = 'BS001', message = 'Phone call required';
    end if;
    update public.bloodsight_reports set status='published', published_at=now(),
        phoned_by=case when p_phoned then p_actor else phoned_by end where id=p_report_id;
    return true;
end;
$$;

revoke all on function public.bloodsight_storage_status(),
    public.bloodsight_import_history(text,text,jsonb,text,text),
    public.bloodsight_import_reports(text,text,jsonb,text,text),
    public.bloodsight_publish_report(text,text,text,boolean) from public, anon, authenticated;
grant execute on function public.bloodsight_storage_status(),
    public.bloodsight_import_history(text,text,jsonb,text,text),
    public.bloodsight_import_reports(text,text,jsonb,text,text),
    public.bloodsight_publish_report(text,text,text,boolean) to service_role;

comment on table public.bloodsight_history is 'Daily units used by uploaded-data forecasts; synthetic prototype records only.';
comment on table public.bloodsight_report_values is 'Lab-supplied measurements and reference bounds; no inferred diagnosis.';
notify pgrst, 'reload schema';
