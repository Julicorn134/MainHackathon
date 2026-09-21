# BloodSight AI: interface spec (clinical operations software, not a demo page)

The owner's complaint: the interface reads as AI-generated. Remove the tells. The reference he likes is a dense
hospital operations dashboard: compact, quiet, data first, red used sparingly as the brand accent.

## The tells to remove
- Default-looking or oversized buttons; full-width buttons outside forms; blue primary buttons.
- Pastel pill chips on everything; rounded cards nested inside rounded cards; soft shadows on content cards.
- Left accent bars on cards; uppercase letter-spaced labels on content blocks (allowed only for the sidebar group label and table headers).
- Huge metric numerals (2.5rem+) with a sentence under each.
- Copy that explains the design to the reader ("This page shows...", "The model recommends. A staff member presses send."), captions under every control, sentences where a label would do, anything that says prototype, demo, simulated, synthetic inside the working screens.
- Emoji anywhere. Long dash characters anywhere. Exclamation marks. "AI" attached to ordinary headings.
- Everything the same visual weight: a page needs one clear primary block and quieter secondary blocks.
- Centered text blocks in working screens; excessive bold inside sentences.

## Tokens
- Font: Inter (already loaded). Base 14px. Page title 20px/600. Section heading 15px/600. Body 14px/400. Secondary text 12.5px #5f5d58.
- Colors: ink #111827, secondary ink #4b5563, muted #6b7280, border #e5e4df, page #f7f7f5, surface #ffffff, brand red #c8102e (hover #a50d26), red tint #fdecef. Status: critical #c8102e, warning #b45309, ok #15803d, info #1d4ed8, each on a very light tint.
- Buttons: height 36px, radius 6px, 13.5px/500, padding 0 14px, width fits the label. Primary: solid #c8102e, white text, no shadow. Secondary: white, 1px #d4d3cd border, ink text, hover border #9ca3af. Quiet: no border, muted text, underline on hover. Only a form's submit may span its form. One primary button per block at most.
- Status marks (HARD RULE from the owner: no pills): never a rounded tinted pill or badge. A status is a 6px round dot in the status colour followed by plain text, 12.5px/600, in a darker shade of the same colour, no background, no border, no padding box. The same goes for tags such as "You gave here", "Draft", "Sent", "Closed", "app account": plain small text, optionally preceded by a dot, separated from neighbours by a middle dot. Remove every `border-radius: 999px` and every `.bs-chip` style pill.
- Cards: white, 1px #e5e4df border, radius 10px, padding 16px 18px, no shadow, never nested.
- Metrics: label 12px muted above, value 24px/600 ink, optional 12px note under. In one bordered strip divided by 1px rules, not four floating numbers.
- Tables: 13px, header 11.5px/600 muted (uppercase allowed), cell padding 8px 12px, 1px row rules, numbers right-aligned, no zebra, no outer heavy border.
- Spacing: 8px grid. Section gap 24px. Do not leave large empty areas.

## Streamlit rules
- A `<style>` block passed to st.markdown must contain no blank lines and no `/* comments */` (markdown breaks it and the CSS leaks as text).
- Streamlit 1.64 markup: buttons are `[data-testid="stBaseButton-primary"]`, `[data-testid="stBaseButton-secondary"]`, form submit `[data-testid="stBaseButton-primaryFormSubmit"]` / `-secondaryFormSubmit`; text inputs `[data-testid="stTextInputRootElement"]`; tabs `[data-testid="stTab"]`; radio option `label[data-testid="stRadioOption"]` with `data-selected="true"` when active; metric `[data-testid="stMetric"]`. A widget with `key="x"` gets the class `.st-key-x`.
- Edited modules are not hot-reloaded: restart your test server to see a change.
