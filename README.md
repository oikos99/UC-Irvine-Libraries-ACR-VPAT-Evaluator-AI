# UC Irvine Libraries AI-Assisted ACR/VPAT Reviewer

A Streamlit prototype for reviewing uploaded ACR/VPAT PDFs as accessibility documentation evidence.

## Important boundary

This app is an AI-assisted ACR/VPAT documentation reviewer. It does **not** prove whether the vendor product itself is accessible. It reviews whether the vendor documentation is complete, current, specific, and risky enough to require follow-up.

## Requirements

- Python 3.10 or newer
- An OpenAI API key
- A text-based ACR/VPAT PDF

Scanned/image-only PDFs may not extract useful text yet because this prototype does not currently include OCR.

## Quick start

Run these commands from the folder that contains `app.py`, `requirements.txt`, and this `README.md`.

```bash
python -m venv .venv
source .venv/bin/activate  # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

Then open the local Streamlit URL shown in the terminal.

## How to use

1. Start the app with `streamlit run app.py`.
2. Enter your OpenAI API key in the left Settings panel.
3. Upload an ACR/VPAT PDF.
4. Confirm the review ID, product tier, and usage level.
5. Adjust the Evaluation Criteria table if needed.
6. Use the advanced **UC Irvine defined risk-level criteria** section only if you need to change the Gate logic.
7. Select **Process AI-assisted review**.
8. Review the Evaluation Results, Inventory-ready summary, and Vendor follow-up questions.
9. Export CSV/TXT files as needed.

## What this app does

- Lets library staff upload an ACR/VPAT PDF.
- Uses the uploaded PDF file name as the review ID.
- Provides a left Streamlit settings panel with an OpenAI API key field and model dropdown.
- Locks Product tier to Tier 3 and defaults Usage level to Medium Usage.
- Places Upload ACR/VPAT PDF across the page, with ID, Product tier, and Usage level aligned below it.
- Shows preset evaluation criteria in one criteria table, with a blank bottom row for adding custom criteria.
- Keeps preset criteria rows visually locked; only custom rows are editable.
- Lets staff save and reload evaluation profiles as JSON files.
- Includes an advanced UC Irvine risk-level criteria section that explains the Gate logic and allows WCAG version/level and critical WCAG criteria settings to be adjusted.
- Defaults to WCAG 2.1 Level AA, with backend logic treating WCAG levels as cumulative: Level AA includes A, and Level AAA includes A and AA.
- Dynamically syncs advanced Gate settings with the criteria table. Changing selected critical WCAG success criteria updates the table, and loading a saved profile updates the advanced settings.
- Uses AI to extract evidence, summarize findings, explain rationale, and suggest vendor follow-up questions. The AI prompt is built from the current Evaluation Criteria table, including custom rows.
- Uses rule-based logic to assign a recommended High / Medium / Low risk level based on UC Irvine Libraries risk-level criteria.
- Exports evaluation results CSV, inventory-ready CSV, and vendor follow-up TXT.

## Evaluation profiles

The app can save and reload evaluation profiles as JSON files. A profile includes:

- the current Evaluation Criteria table
- custom rows added by staff
- advanced Gate settings, including accepted WCAG version, required conformance level, stale threshold, and selected critical WCAG success criteria

Older criteria-only JSON profiles should still load. When a profile does not include saved Gate settings, the app tries to infer them from the criteria rows where possible.

## Data note

The app sends the full extracted PDF text and evaluation criteria to the selected OpenAI model. Do not upload confidential vendor documents unless that use is approved under local campus, library, procurement, and AI guidance.

## Files

- `app.py` — Streamlit app
- `default_criteria.json` — preset evaluation profile
- `assets/uci_libraries_favicon.png` — page icon
- `assets/uci_libraries_logo.jpg` — large title logo
- `requirements.txt` — Python dependencies

## Notes and limitations

- The prototype extracts embedded PDF text with PyMuPDF.
- Scanned/image-only PDFs may need OCR in a later version.
- The app sends the full extracted PDF text to AI for completeness.
- The OpenAI model dropdown currently includes one default option: `gpt-4.1-mini`.
- Keep vendor privacy, procurement sensitivity, and campus AI guidance in mind before testing real vendor documents.

## Do not commit generated files

Do not include local environment or generated Python files in the repo:

```text
.venv/
__pycache__/
*.pyc
```
