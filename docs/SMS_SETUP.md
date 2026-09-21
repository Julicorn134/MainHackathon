# SMS test setup

BloodSight now saves a phone number and explicit test-message consent, sends one real
SMS on a button click, and records the provider's delivery state. Every role has an
**SMS test** page. Forecasts, requests and lab notifications still use their existing
in-app workflow; they do not automatically send SMS.

## Private configuration

Copy the Twilio entries from `bloodsight/.streamlit/secrets.example.toml` into the
ignored `secrets.toml` file or deployment secret store. Never commit credentials.
Use `TWILIO_ACCOUNT_SID` and `TWILIO_AUTH_TOKEN` from the account that owns the sender.

- `TWILIO_MESSAGE_MODE = "trial_template"` (default): sends the predefined
  `sms_account_alerts` template. The current trial API assigns the sender, so the
  request includes only `To` and `Body`. Finish **Messaging > Try out SMS** in the
  Twilio console and verify the receiving number. Trial restrictions and console
  versions differ; follow the API example shown for your actual account. The trial
  test does not contain the custom BloodSight donation wording.
- `TWILIO_MESSAGE_MODE = "custom"`: sends the BloodSight test donation message
  shown on the page. Set an SMS-capable `TWILIO_FROM_NUMBER` or a
  `TWILIO_MESSAGING_SERVICE_SID` with a configured sender pool. Enable the recipient's
  country in Twilio's geographic permissions. New trial accounts restrict custom
  content; enable it with Twilio before selecting this mode.

The sender number and receiving number are separate. Enter the receiving mobile
number, including its country code, on **SMS test**; save it with consent and press
**Send test SMS**. Press **Check delivery** to fetch the status without sending again.
Outbound SMS works from the local app; a public URL is only needed for mobile booking
links or future inbound/delivery webhooks.

## Storage and sending

Apply the `bloodsight_sms` migration after the main storage migration. It adds:

- `bloodsight_sms_contacts`: account, phone, consent and consent timestamp.
- `bloodsight_sms_attempts`: destination snapshot, template/text, attempt UUID,
  provider message SID, status, safe numeric error code and timestamps.

Tables have RLS enabled and no public-client grants. Server-only invoker RPCs save
contacts, reserve a send and record its outcome. The existing Streamlit account
session scopes all reads and writes. SQLite remains an explicit offline/test option;
a failed cloud operation never falls back to local storage.

A reservation is committed before calling Twilio. Reusing the same attempt UUID
never sends again. Database locks enforce a 60-second cooldown, five attempts per
rolling 24 hours per account or phone, and 50 total attempts per rolling 24 hours.
Rejected/uncertain attempts count toward the limits. Phone settings are checked
again at reservation time. These limits are for the team demo, not donor campaigns.

No transport retry is automatic. Timeouts or malformed success responses are marked
`unknown`; a crash or database failure after submission may leave `submitting`.
Check Twilio's message log before preparing another test in either case. `queued`,
`accepted` and `sent` are not displayed as confirmed delivery. Only `delivered`
means Twilio received a delivery receipt.

## Current boundary

This remains a demo with local account identities. Use only consenting team test
numbers. Public donor onboarding needs production authentication and phone ownership
verification; campaign sending also needs channel-specific consent, opt-out/reply
webhooks, staff recipient review, and deployment with an appropriate sender. The
existing in-app donation switches do not grant SMS consent. No phone is included in
the AI evidence packet.

The implementation is covered by `bloodsight/tests/test_sms.py`; tests mock Twilio
and cannot send live SMS. `supabase/tests/sms.sql` checks real database permissions,
consent, attempt deduplication, recipient limits and ownership, and rolls back all
fixtures.

Supabase's security advisor reports informational
[RLS enabled without policies](https://supabase.com/docs/guides/database/database-linter?lint=0008_rls_enabled_no_policy)
notices for these server-only tables. Public roles have no grants; no public policies
are intended. Database tests verify both restrictions.

References checked September 2026:

- [Twilio SMS trial API](https://www.twilio.com/docs/usage/trials/try-out-sms)
- [Trial restrictions and country support](https://www.twilio.com/docs/usage/trials)
- [Messages API and delivery states](https://www.twilio.com/docs/messaging/api/message-resource)
- [Netherlands SMS support](https://www.twilio.com/en-us/guidelines/nl/sms)
