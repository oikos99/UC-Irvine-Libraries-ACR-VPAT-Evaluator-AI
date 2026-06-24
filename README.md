# UC Irvine Libraries AI-Assisted ACR/VPAT Reviewer

A Streamlit prototype for reviewing uploaded ACR/VPAT PDFs as accessibility documentation evidence.

## What this app does

- Lets library staff upload an ACR/VPAT PDF.
- Shows a large UC Irvine Libraries logo next to the app title, using assets stored in the `assets/` folder.
- Uses the uploaded PDF file name as the review ID.
- Provides a left Streamlit settings panel with an OpenAI API key field and model setting.
- Locks Product tier to Tier 3 and defaults Usage level to Medium Usage.
- Places Upload ACR/VPAT PDF across the page, with ID, Product tier, and Usage level aligned below it.
- Shows preset evaluation criteria in one criteria table, with a blank bottom row for adding custom criteria.
- Preset criteria rows are visually locked in the criteria grid; only the custom bottom row and added custom rows are editable.
- Lets staff save the current evaluation criteria table as a JSON profile.
- Lets staff load the preset profile or upload a saved evaluation profile from JSON.
- Includes an advanced UC Irvine risk-level criteria section that explains the Gate logic and allows WCAG version/level and critical WCAG criteria settings to be adjusted. WCAG 2.1 Level AA is selected by default, and the backend treats WCAG levels as cumulative.
- Uses AI to extract evidence, summarize findings, explain rationale, and suggest vendor follow-up questions.
- Uses rule-based logic to assign a recommended High / Medium / Low risk level based on UC Irvine Libraries risk-level criteria.
- Exports evaluation results CSV, inventory-ready CSV, and vendor follow-up TXT.

## Important boundary

This app is an AI-assisted ACR/VPAT documentation reviewer. It does **not** prove whether the vendor product itself is accessible. It reviews whether the vendor documentation is complete, current, specific, and risky enough to require follow-up.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

Then open the local Streamlit URL shown in the terminal.

## Files

- `app.py` — Streamlit app
- `default_criteria.json` — preset evaluation profile
- `assets/uci_libraries_favicon.png` — page icon
- `assets/uci_libraries_logo.jpg` — large title logo
- `requirements.txt` — Python dependencies

## Notes

- The prototype extracts embedded PDF text with PyMuPDF. Scanned/image-only PDFs may need OCR in a later version.
- The OpenAI model is configurable in the sidebar. Use a model available to your API account. The app sends the full extracted PDF text to AI for completeness.
- Keep vendor privacy, procurement sensitivity, and campus AI guidance in mind before testing real vendor documents.
