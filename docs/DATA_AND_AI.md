# Data deposits and real AI

This change continues the Streamlit application. It adds data persistence and replaces template-based answers; it does not connect every hospital system or complete every requirement in the source PDF.

## What is implemented

- **Centre Data page:** UTF-8 CSV preview/import, manual daily figures, a sample download, saved-history export, quality report and import provenance. The expected columns are `date,blood_type,donations,demand,inventory,holiday`; optional `place_id` must match the staff organisation. Quantities are nonnegative whole units. Dates are ISO. Files are limited to 5 MB and 20,000 rows.
- **Persistent storage:** SQLite transactions, parameterised SQL, write serialisation and disk-backed records. Import corrections update date/type keys; unchanged imports are idempotent. A fresh application process reads the same records. Database files, WAL files and secrets are ignored by Git.
- **Uploaded-data forecasting:** reads the current centre's history, requires 42 consecutive days per type and never silently fills missing days or substitutes demo data. Training uses imported holiday flags. Unsupported types/series are excluded with a reason. The source's closing-stock date is shown.
- **Lab Data page:** JSON reports or a single-value manual entry become stored drafts. Validate values and supplied reference ranges, derive their flags, review and explicitly publish. An urgent report requires the phone-call confirmation. New imported lab codes can be used by the existing demo registration flow. Published measurements cannot be silently overwritten by another import.
- **Patient records:** published deposited reports replace the same patient's bundled history. Drafts stay hidden. Results preference and account lab-code scoping are respected.
- **AI:** staff ask about computed forecasts; patients ask about their own records or request an explanation of a measured value. The OpenAI Responses API returns a structured answer and evidence IDs. Unknown source IDs, missing configuration, refusals/incomplete answers and provider failures do not produce a canned substitute.

The [official Structured Outputs guide](https://developers.openai.com/api/docs/guides/structured-outputs) defines the API approach. The default [GPT-4.1 mini model](https://developers.openai.com/api/docs/models/gpt-4.1-mini) supports structured outputs; another supported model can be selected in configuration.

## Local setup

Use Python 3.11+ and the run commands in [the app README](../bloodsight/README.md). From `bloodsight/`, copy `.streamlit/secrets.example.toml` to `.streamlit/secrets.toml`, then put your key in the local copy:

```toml
OPENAI_API_KEY = "your-local-key"
OPENAI_MODEL = "gpt-4.1-mini"
```

Environment variables with the same names take precedence. Keep the real key out of Git, chat, screenshots and client-side code. A key is required only for LLM calls: importing data and calculating forecasts work without it. The prototype calls the OpenAI API only when the user submits a question or asks for a value explanation. It has a timeout, bounded input/output and no automatic retry.

Each AI request shows a notice about sending selected test records to OpenAI. The application omits account names, passwords, lab codes and postcodes from its constructed evidence packet; a user can still type identifying details into their question, so use synthetic data. Requests use `store=False`; this is not a claim of zero provider retention. The model receives no execution, database-write or messaging tools. Returned source IDs are checked, but that alone does not prove every generated statement is correct.

## Demonstrate that answers use deposited data

1. As `centre`, download and import the history sample from Data. Open Outlook with Uploaded data selected.
2. Enter a different closing inventory for the final date/type. Return to Outlook: stock and forecast change without editing a Python file or restarting.
3. As `lab`, download the report JSON template, change the measured value and import it. Publish the selected draft. Use synthetic lab code `BL-4790` for the existing `patient` account.
4. As `patient`, open Results: the published imported measurement appears with its uploaded source label. Ask for a summary. Inspect the evidence shown under the generated answer.
5. Change to `patient2`: the imported report for `BL-4790` is not available. Removing the API key produces the connection message instead of an invented answer.

## Checks performed

`python -m pytest -q`: **36 passed** on the implementation environment. Coverage includes persisted imports, duplicate/replayed corrections, whole-batch rejection/rollback, cross-role/facility reads, quality checks, zero-demand calculations, publication/urgent-report guards, patient record scoping and registration from a deposited code. It also checks the actual OpenAI SDK request/response format against a mock HTTP transport, error-body suppression, source-ID rejection, and Streamlit AppTest rendering for the new pages. An AppTest verifies that a saved stock correction changes the displayed outlook.

`python -m pip check`: no broken requirements. The installed NumPy/pandas combination emits a timedelta deprecation warning in the existing date-range path; tests pass. These are automated backend and headless UI checks, not a clinical evaluation or a full human browser acceptance report.

**A live provider response is not verified until a working key is configured.** Mock transport tests verify integration mechanics, not output quality, account quota or live model access.

## Remaining boundaries

- Current imports use defined CSV/JSON schemas. Excel, arbitrary column mapping, scanned PDFs, Sheets, ODK, FHIR/HL7 and DHIS2 require connectors. See [the integration roadmap](BLOODSIGHT_INTEGRATIONS.md).
- This is local persistent storage, not shared cloud hosting. Demo users and existing request/booking state remain in the original JSON store. Production authentication, real organisation onboarding and deployment are separate work.
- Uploaded forecasts do not overlay the old synthetic campaign-response counts. Lot expiry, product-specific stock, transfers, dated appointment yield and clinical eligibility policies remain unimplemented in that baseline.
- No donor messages are sent externally. No new automated diagnosis, medical eligibility decision, or background AI campaign execution is provided.
- The original manual acceptance checklist and four-person prompts describe broader work. This change does not mark those requirements complete.
