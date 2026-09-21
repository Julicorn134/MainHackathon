-- Server-only SMS tests. Demo identities are checked by Streamlit; no public client access.
create table public.bloodsight_sms_contacts (
  username text primary key check (length(username) between 1 and 100),
  phone text not null check (phone = '' or phone ~ '^\+[1-9][0-9]{7,14}$'),
  consent boolean not null default false,
  consent_at timestamptz,
  updated_at timestamptz not null default now(),
  check (not consent or (phone <> '' and consent_at is not null))
);
create table public.bloodsight_sms_attempts (
  id uuid primary key,
  username text not null check (length(username) between 1 and 100),
  phone text not null check (phone ~ '^\+[1-9][0-9]{7,14}$'),
  body text not null check (length(body) between 1 and 500),
  mode text not null check (mode in ('trial_template','custom')),
  status text not null check (status in ('submitting','unknown','accepted','queued','sending',
    'sent','delivered','undelivered','failed','canceled')),
  provider_sid text check (provider_sid ~ '^SM[0-9a-fA-F]{32}$'),
  error_code text check (error_code ~ '^[0-9]{3,6}$'),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index bloodsight_sms_phone_date on public.bloodsight_sms_attempts(phone,created_at);
create index bloodsight_sms_user_date on public.bloodsight_sms_attempts(username,created_at desc);
create index bloodsight_sms_date on public.bloodsight_sms_attempts(created_at);
alter table public.bloodsight_sms_contacts enable row level security;
alter table public.bloodsight_sms_attempts enable row level security;
revoke all on public.bloodsight_sms_contacts, public.bloodsight_sms_attempts from public, anon, authenticated;
grant select, insert, update, delete on public.bloodsight_sms_contacts, public.bloodsight_sms_attempts to service_role;

create function public.bloodsight_sms_contact(p_actor text, p_phone text, p_consent boolean)
returns boolean language plpgsql security invoker set search_path = '' as $$
begin
  insert into public.bloodsight_sms_contacts(username,phone,consent,consent_at)
  values(p_actor,p_phone,p_consent,case when p_consent then now() else null end)
  on conflict(username) do update set phone=excluded.phone,consent=excluded.consent,
    consent_at=excluded.consent_at,updated_at=now();
  return true;
end;
$$;

create function public.bloodsight_sms_reserve(p_actor text, p_id uuid, p_phone text, p_body text, p_mode text)
returns jsonb language plpgsql security invoker set search_path = '' as $$
declare
  attempt public.bloodsight_sms_attempts;
  contact public.bloodsight_sms_contacts;
begin
  perform pg_catalog.pg_advisory_xact_lock(621091516);
  select * into attempt from public.bloodsight_sms_attempts where id=p_id;
  if found then
    if attempt.username <> p_actor then
      raise exception using errcode='SM003',message='Unknown attempt';
    end if;
    return jsonb_build_object('send',false,'record',to_jsonb(attempt));
  end if;
  select * into contact from public.bloodsight_sms_contacts where username=p_actor for update;
  if not found or not contact.consent or contact.phone <> p_phone then
    raise exception using errcode='SM001',message='Contact consent required';
  end if;
  if exists(select 1 from public.bloodsight_sms_attempts
       where (username=p_actor or phone=p_phone) and created_at > now()-interval '60 seconds')
     or (select count(*) from public.bloodsight_sms_attempts
       where (username=p_actor or phone=p_phone) and created_at > now()-interval '24 hours') >= 5
     or (select count(*) from public.bloodsight_sms_attempts where created_at > now()-interval '24 hours') >= 50 then
    raise exception using errcode='SM002',message='SMS test limit';
  end if;
  insert into public.bloodsight_sms_attempts(id,username,phone,body,mode,status)
    values(p_id,p_actor,p_phone,p_body,p_mode,'submitting') returning * into attempt;
  return jsonb_build_object('send',true,'record',to_jsonb(attempt));
end;
$$;

create function public.bloodsight_sms_record(p_actor text, p_id uuid, p_status text, p_sid text, p_error text)
returns jsonb language plpgsql security invoker set search_path = '' as $$
declare attempt public.bloodsight_sms_attempts;
begin
  update public.bloodsight_sms_attempts set status=p_status,provider_sid=coalesce(p_sid,provider_sid),
    error_code=p_error,updated_at=now() where id=p_id and username=p_actor and status<>'delivered';
  select * into attempt from public.bloodsight_sms_attempts where id=p_id and username=p_actor;
  if not found then raise exception using errcode='SM003',message='Unknown attempt'; end if;
  return to_jsonb(attempt);
end;
$$;

revoke all on function public.bloodsight_sms_contact(text,text,boolean) from public,anon,authenticated;
revoke all on function public.bloodsight_sms_reserve(text,uuid,text,text,text) from public,anon,authenticated;
revoke all on function public.bloodsight_sms_record(text,uuid,text,text,text) from public,anon,authenticated;
grant execute on function public.bloodsight_sms_contact(text,text,boolean) to service_role;
grant execute on function public.bloodsight_sms_reserve(text,uuid,text,text,text) to service_role;
grant execute on function public.bloodsight_sms_record(text,uuid,text,text,text) to service_role;
