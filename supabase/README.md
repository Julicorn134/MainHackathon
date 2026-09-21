# BloodSight cloud data

Project: **Bloodsight**, `xbabvlorkjilnnxrifmy` (EU West). Migration `20260921142836_bloodsight_data.sql` is applied to this project.

Migration `20260921152121_bloodsight_sms.sql` is also applied. It adds private SMS
contacts and delivery attempts, plus server-only RPCs. See [SMS setup](../docs/SMS_SETUP.md).

The Streamlit server imports validated records through the Supabase Data API. The browser never receives the server key. Forecasts and AI evidence read from the selected backend on each request; cloud failures do not switch to local fixtures.

## Tables

| Table | Main columns and purpose |
| --- | --- |
| `bloodsight_facilities` | `id`, `kind`, `created_at`: centre/lab owning each deposit |
| `bloodsight_imports` | `id`, `kind`, `owner`, `filename`, `digest`, `row_count`, `created_by`, `created_at`: import audit trail |
| `bloodsight_history` | `place_id`, `date`, `blood_type`, `donations`, `demand`, `inventory`, `holiday`, `import_id`, `updated_at`: daily units; unique facility/date/type |
| `bloodsight_reports` | `id`, `org`, `lab_code`, `date`, `blood_type`, `lab`, `urgent`, `status`, `phoned_by`, `published_at`, `import_id`: draft/publication workflow; unique code/date |
| `bloodsight_report_values` | `report_id`, `key`, `name`, `unit`, `value`, `low`, `high`, `flag`, `line`: measured values with a database-derived range flag |
| `bloodsight_sms_contacts` | `username`, `phone`, `consent`, `consent_at`, `updated_at`: own test-phone settings |
| `bloodsight_sms_attempts` | `id`, `username`, `phone`, `body`, `mode`, `status`, `provider_sid`, `error_code`, timestamps: deduplicated send attempts |

Foreign keys connect facilities, imports, reports and values. Constraints reject negative daily units, unknown blood groups, invalid ranges and duplicate report keys. Transactional RPCs save whole batches, serialize concurrent imports for a facility and make unchanged repeat uploads idempotent. Reapplying an earlier history file after a correction restores that file's values and adds an audit record.

## Configure the app

In `bloodsight/.streamlit/secrets.toml` (ignored by Git), or the hosting service's server secrets:

```toml
BLOODSIGHT_DATA_BACKEND = "supabase"
SUPABASE_URL = "https://xbabvlorkjilnnxrifmy.supabase.co"
SUPABASE_SECRET_KEY = "your-server-secret-key"
```

Get a secret key from **Supabase → Settings → API Keys**. A legacy `SUPABASE_SERVICE_ROLE_KEY` is accepted too. A publishable/anonymous key is deliberately insufficient. Environment variables override file settings. Set `BLOODSIGHT_DATA_BACKEND = "sqlite"` explicitly for offline tests; existing SQLite rows are not automatically copied into Supabase. Export them from the Data page and reimport after changing backends.

Run the app, select **Blood centre → Data → Check database connection**. Upload a history CSV, review its preview and choose **Save history**. **Outlook → Uploaded data** immediately uses saved records. The **Lab → Data** screen accepts JSON reports and publishes reviewed drafts. Templates and manual-entry forms are included in both screens.

The initial verification loaded the bundled **1,440 synthetic history rows** (180 days × eight groups) and **one synthetic draft report**. The draft stays hidden from the patient until explicitly published. These are test records, not observations from a hospital.

## Access model

All five tables have RLS enabled. `anon` and `authenticated` have no table or RPC privileges. RPCs use `SECURITY INVOKER` and an empty search path. Only the server's `service_role`/secret key can access this data. The app checks the saved demo account's role and organisation before issuing each scoped request.

The current app still uses local demo identities and booking/request state; **this is not Supabase Auth or production patient authorization**. A server key bypasses RLS, so app scoping remains essential. Use synthetic records only. Production identities, tenancy and organisation onboarding need a separate implementation.

The Supabase Security Advisor reports informational [RLS enabled without policies](https://supabase.com/docs/guides/database/database-linter?lint=0008_rls_enabled_no_policy) findings for these seven intentionally server-only tables. Browser grants are revoked; do not add permissive public policies to silence them. No security warnings or errors were returned at verification.

## Reproduce verification

- Run `python -m pytest tests -q` from `bloodsight/` for isolated storage, HTTP-adapter and Streamlit tests. These never use real keys.
- Run `tests/storage.sql` in this directory through Supabase's SQL editor to check real transactions, corrections, duplicate imports, report publication guards and grants. It uses random test identities and rolls every fixture back.
- The live app API was checked with the configured secret: import and reread 1,440 rows (including pagination), repeat-file deduplication, report draft import and patient invisibility. Centre Data/Outlook, Lab Data and Patient Results passed Streamlit checks against the live database.

For a new project, apply the migration once before starting the app. Keep new changes in migrations; do not rerun this initial migration over existing tables. Official references: [API keys](https://supabase.com/docs/guides/getting-started/api-keys), [database functions](https://supabase.com/docs/guides/database/functions), [Data API access](https://supabase.com/docs/guides/api/securing-your-api).
