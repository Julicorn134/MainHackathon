-- Real Postgres verification; fixtures and changes are rolled back. Never contacts Twilio.
begin;
do $$
declare
  actor text := 'sms-test-' || gen_random_uuid()::text;
  other_actor text := 'sms-test-' || gen_random_uuid()::text;
  attempt uuid := gen_random_uuid();
  result jsonb;
begin
  assert (select relrowsecurity from pg_class where oid='public.bloodsight_sms_contacts'::regclass);
  assert (select relrowsecurity from pg_class where oid='public.bloodsight_sms_attempts'::regclass);
  assert not has_table_privilege('anon','public.bloodsight_sms_contacts','SELECT');
  assert not has_table_privilege('authenticated','public.bloodsight_sms_attempts','SELECT');
  assert not has_function_privilege('anon','public.bloodsight_sms_reserve(text,uuid,text,text,text)','EXECUTE');
  assert not has_function_privilege('authenticated','public.bloodsight_sms_contact(text,text,boolean)','EXECUTE');
  assert has_function_privilege('service_role','public.bloodsight_sms_reserve(text,uuid,text,text,text)','EXECUTE');
  perform public.bloodsight_sms_contact(actor,'+31600000000',false);
  begin
    perform public.bloodsight_sms_reserve(actor,attempt,'+31600000000','sms_account_alerts','trial_template');
    raise exception 'Consent must be required';
  exception when sqlstate 'SM001' then null;
  end;
  perform public.bloodsight_sms_contact(actor,'+31600000000',true);
  result := public.bloodsight_sms_reserve(actor,attempt,'+31600000000','sms_account_alerts','trial_template');
  assert (result->>'send')::boolean;
  result := public.bloodsight_sms_reserve(actor,attempt,'+31600000000','sms_account_alerts','trial_template');
  assert not (result->>'send')::boolean;
  begin
    perform public.bloodsight_sms_reserve(other_actor,attempt,'+31600000000','sms_account_alerts','trial_template');
    raise exception 'Other account must not read the attempt';
  exception when sqlstate 'SM003' then null;
  end;
  begin
    perform public.bloodsight_sms_reserve(actor,gen_random_uuid(),'+31600000000','sms_account_alerts','trial_template');
    raise exception 'Cooldown must be enforced';
  exception when sqlstate 'SM002' then null;
  end;
  perform public.bloodsight_sms_contact(other_actor,'+31600000000',true);
  begin
    perform public.bloodsight_sms_reserve(other_actor,gen_random_uuid(),'+31600000000','sms_account_alerts','trial_template');
    raise exception 'Shared phone must share the cooldown';
  exception when sqlstate 'SM002' then null;
  end;
  result := public.bloodsight_sms_record(actor,attempt,'delivered','SM'||repeat('a',32),null);
  assert result->>'status' = 'delivered';
  result := public.bloodsight_sms_record(actor,attempt,'queued','SM'||repeat('a',32),null);
  assert result->>'status' = 'delivered';
  begin
    perform public.bloodsight_sms_record(other_actor,attempt,'failed',null,null);
    raise exception 'Other account must not update the attempt';
  exception when sqlstate 'SM003' then null;
  end;
  perform public.bloodsight_sms_contact(actor,'+31600000000',false);
  begin
    perform public.bloodsight_sms_reserve(actor,gen_random_uuid(),'+31600000000','sms_account_alerts','trial_template');
    raise exception 'Revoked consent must be enforced';
  exception when sqlstate 'SM001' then null;
  end;
end;
$$;
rollback;
