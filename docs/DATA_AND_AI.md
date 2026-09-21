# Data deposits and real AI

This change continues the Streamlit application. It adds data persistence and replaces template-based answers; it does not connect every hospital system or complete every requirement in the source PDF.

## What is implemented

- **Centre Data page:** UTF-8 CSV preview/import, manual daily figures, a sample download, saved-history export, quality report and import provenance. The expected columns are `date,blood_type,donations,demand,inventory,holiday`; optional `place_id` must match the staff organisation. Quantities are nonnegative whole units. Dates are ISO. Files are limited to 5 MB and 20,000 rows.
- **Persistent storage:** Supabase/Postgres cloud tables with transactional imports, or explicitly selected SQLite for offline tests. Import corrections update date/type keys; unchanged imports are idempotent. A fresh application process reads the same records. Database files, WAL files and secrets are ignored by Git. See [the applied schema and cloud setup](../supabase/README.md).
- **Uploaded-data forecasting:** reads the current centre's history, requires 42 consecutive days per type and never silently fills missing days or substitutes demo data. Training uses imported holiday flags. Unsupported types/series are excluded with a reason. The source's closing-stock date is shown.
- **Lab Data page:** JSON reports or a single-value manual entry become stored drafts. Validate values and supplied reference ranges, derive their flags, review and explicitly publish. An urgent report requires the phone-call confirmation. New imported lab codes can be used by the existing demo registration flow. Published measurements cannot be silently overwritten by another import.
- **Patient records:** published deposited reports replace the same patient's bundled history. Drafts stay hidden. Results preference and account lab-code scoping are respected.
- **AI:** staff ask about computed forecasts; patients ask about their own records or request an explanation of a measured value. OpenRouter Chat Completions or the direct OpenAI Responses API returns a structured answer and evidence IDs. Unknown source IDs, missing configuration, refusals/incomplete answers and provider failures do not produce a canned substitute. Provider keys are kept separate and requests use the selected provider's fixed endpoint.

The current configuration uses [OpenRouter structured outputs](https://openrouter.ai/docs/guides/features/structured-outputs) with `openai/gpt-4.1-mini`. Requests require a provider that supports the supplied parameters, disallow data-collection providers and disable automatic provider fallback. Direct OpenAI remains optional; its [Structured Outputs guide](https://developers.openai.com/api/docs/guides/structured-outputs) describes that API path. Another compatible model can be selected in server configuration.

## Local setup

Use Python 3.11+ and the run commands in [the app README](../bloodsight/README.md). From `bloodsight/`, copy `.streamlit/secrets.example.toml` to `.streamlit/secrets.toml`, then put your key in the local copy:

```toml
AI_PROVIDER = "openrouter"
OPENROUTER_API_KEY = "your-local-key"
OPENROUTER_MODEL = "openai/gpt-4.1-mini"
BLOODSIGHT_DATA_BACKEND = "supabase"
SUPABASE_URL = "https://xbabvlorkjilnnxrifmy.supabase.co"
SUPABASE_SECRET_KEY = "your-server-secret-key"
```

For direct OpenAI instead, set `AI_PROVIDER = "openai"`, `OPENAI_API_KEY` and optionally `OPENAI_MODEL = "gpt-4.1-mini"`. An OpenRouter key must not be placed in `OPENAI_API_KEY`.

Environment variables with the same names take precedence. Keep the real key out of Git, chat, screenshots and client-side code. A key is required only for LLM calls: importing data and calculating forecasts work without it. The prototype calls the configured AI service only when the user submits a question or asks for a value explanation. It has a timeout, bounded input/output and no automatic retry. OpenRouter credit errors are displayed without exposing response bodies.

Each AI request shows a notice naming the destination: OpenRouter and its selected model provider, or direct OpenAI. The application omits account names, passwords, lab codes and postcodes from its constructed evidence packet; a user can still type identifying details into their question, so use synthetic data. Requests use `store=False`; this is not a claim of zero provider retention. The model receives no execution, database-write or messaging tools. Returned source IDs are checked, but that alone does not prove every generated statement is correct.

## Demonstrate that answers use deposited data

1. As `centre`, download and import the history sample from Data. Open Outlook with Saved records selected.
2. Enter a different closing inventory for the final date/type. Return to Outlook: stock and forecast change without editing a Python file or restarting.
3. As `lab`, download the report JSON template, change the measured value and import it. Publish the selected draft. Use synthetic lab code `BL-4790` for the existing `patient` account.
4. As `patient`, open Results: the published imported measurement appears with its uploaded source label. Ask for a summary. Inspect the evidence shown under the generated answer.
5. Change to `patient2`: the imported report for `BL-4790` is not available. Removing the API key produces the connection message instead of an invented answer.

## Checks performed

`python -m pytest -q`: **114 passed** on the implementation environment. Coverage includes persisted imports, duplicate/replayed corrections, whole-batch rejection/rollback, cross-role/facility reads, quality checks, zero-demand calculations, publication/urgent-report guards, patient record scoping and registration from a deposited code. It also checks the actual OpenAI SDK request/response format against a mock HTTP transport, error-body suppression, source-ID rejection, and Streamlit AppTest rendering for the new pages. An AppTest verifies that a saved stock correction changes the displayed outlook. The redesigned staff/hospital/lab screens and sign-up-then-link flow are checked too. Supabase-specific checks cover HTTP pagination, trusted organisation filters, manual form submission, missing keys, connection failures, error redaction and no silent SQLite fallback.

**Live Supabase verification passed:** the applied migration, transaction/permission assertions in `supabase/tests/storage.sql`, importing and rereading 1,440 synthetic records through the app's Data API adapter, duplicate detection, a synthetic lab draft hidden from patients, and four Streamlit screens against the live project. One draft report remains available for review; it has not been published.

`python -m pip check`: no broken requirements. The installed NumPy/pandas combination emits a timedelta deprecation warning in the existing date-range path; tests pass. These are automated backend and headless UI checks, not a clinical evaluation or a full human browser acceptance report.

**Live OpenRouter verification passed:** a request using the synthetic history saved in Supabase returned the correct total of **2,856 units**, its record date and valid evidence IDs via `openai/gpt-4.1-mini`. This proves the configured connection and one grounded answer, not general medical correctness. Mock transport checks also cover OpenRouter's endpoint, structured schema, refusal/truncation handling, credit failures, key separation and one-request-per-submit UI behavior.

## Remaining boundaries

- Current imports use defined CSV/JSON schemas. Excel, arbitrary column mapping, scanned PDFs, Sheets, ODK, FHIR/HL7 and DHIS2 require connectors. See [the integration roadmap](BLOODSIGHT_INTEGRATIONS.md).
- Uploaded history, report values and import provenance are shared in Supabase when configured. Demo users and existing request/booking state remain in the original local JSON store. Production authentication, real organisation onboarding and hosting the app are separate work.
- Uploaded forecasts do not overlay the old synthetic campaign-response counts. Lot expiry, product-specific stock, transfers, dated appointment yield and clinical eligibility policies remain unimplemented in that baseline.
- External SMS is limited to an explicit test button and consenting team recipients; forecasts and requests do not trigger SMS automatically. See [SMS setup](SMS_SETUP.md). No new automated diagnosis, medical eligibility decision, or background AI campaign execution is provided.
- The original manual acceptance checklist and four-person prompts describe broader work. This change does not mark those requirements complete.

**SMS verification:** 22 automated messaging checks and the live rollback-only `supabase/tests/sms.sql` assertions pass. The Twilio credentials authenticate successfully. A single real test submission was rejected with provider code 572003 and no message SID; delivery has not been verified. The account setup/recipient verification remains to be completed in Twilio. The new SMS screen was inspected in the browser against the live Supabase records.
