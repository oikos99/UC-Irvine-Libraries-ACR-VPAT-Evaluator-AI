import base64
import hashlib
import html
import json
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import fitz  # PyMuPDF
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from dateutil import parser as date_parser
from openai import OpenAI

APP_TITLE = "UC Irvine Libraries AI-Assisted ACR/VPAT Reviewer"
CRITERIA_PATH = Path(__file__).with_name("default_criteria.json")
ASSETS_DIR = Path(__file__).with_name("assets")
FAVICON_PATH = ASSETS_DIR / "uci_libraries_favicon.png"
LOGO_PATH = ASSETS_DIR / "uci_libraries_logo.jpg"

DISPLAY_CRITERIA_COLUMNS = [
    "category",
    "review_question",
    "why_this_matters",
    "what_to_look_for",
]

CRITERIA_COLUMNS = [
    "id",
    "locked",
    "category",
    "review_question",
    "why_this_matters",
    "what_to_look_for",
    "inventory_field",
]

RESULT_COLUMNS = [
    "review_area",
    "review_item",
    "result",
    "what_ai_found",
    "evidence_location",
    "evidence_text",
    "rationale",
    "recommended_action",
    "inventory_field",
]

CRITICAL_SC_OPTIONS = [
    "2.1.1 Keyboard",
    "2.4.7 Focus Visible",
    "1.3.1 Info and Relationships",
    "4.1.2 Name, Role, Value",
    "3.3.1 Error Identification",
    "3.3.3 Error Suggestion",
]

DEFAULT_CRITICAL_SC = CRITICAL_SC_OPTIONS.copy()

PLACEHOLDER_VALUES = {
    "category": "Enter review area",
    "review_question": "Enter evaluation question",
    "why_this_matters": "Enter why this matters",
    "what_to_look_for": "Enter evidence to look for",
}

st.set_page_config(page_title=APP_TITLE, page_icon=str(FAVICON_PATH), layout="wide")

st.markdown(
    """
    <style>
    .block-container {padding-top: 1.5rem;}
    .app-header {
        display: flex;
        align-items: center;
        gap: 1.5rem;
        margin-bottom: 1.4rem;
    }
    .app-header img {
        width: 112px;
        height: 112px;
        object-fit: contain;
        object-position: center center;
        border-radius: 0.35rem;
        flex: 0 0 112px;
        display: block;
        margin-top: 1.25rem;
    }
    .app-header h1 {
        color: rgb(0, 80, 143);
        font-size: clamp(1.65rem, 1.9vw, 2.35rem);
        line-height: 1.14;
        margin: 0 !important;
        font-weight: 800;
        max-width: 100%;
        overflow-wrap: anywhere;
    }

    h1#uc-irvine-libraries-ai-assisted-acr-vpat-reviewer {
        margin-bottom: 0 !important;
    }
    .app-header p {
        font-size: 1.15rem;
        line-height: 1.55;
        margin: 0;
        color: #303241;
    }

    /* Left settings panel: UC Irvine Libraries light-blue theme, matching the PDF-to-HTML review app */
    [data-testid="stSidebar"] {
        background: #eaf4fb !important;
        border-right: 1px solid #d7e3ec !important;
    }
    [data-testid="stSidebar"] [data-testid="stSidebarContent"] {
        background: transparent !important;
    }
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] h4,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] span,
    [data-testid="stSidebar"] div[data-testid="stMarkdownContainer"] {
        color: #303241 !important;
    }
    [data-testid="stSidebar"] small,
    [data-testid="stSidebar"] .stCaptionContainer,
    [data-testid="stSidebar"] [data-testid="stCaptionContainer"] {
        color: #6b7280 !important;
    }
    [data-testid="stSidebar"] a {
        color: rgb(0, 80, 143) !important;
    }
    [data-testid="stSidebar"] input,
    [data-testid="stSidebar"] textarea,
    [data-testid="stSidebar"] div[data-baseweb="select"] *,
    [data-testid="stSidebar"] div[data-baseweb="input"] *,
    [data-testid="stSidebar"] div[data-baseweb="textarea"] * {
        color: #1f2937 !important;
    }
    [data-testid="stSidebar"] div[data-baseweb="select"] > div,
    [data-testid="stSidebar"] div[data-baseweb="input"] > div,
    [data-testid="stSidebar"] div[data-baseweb="textarea"] > div,
    [data-testid="stSidebar"] input,
    [data-testid="stSidebar"] textarea {
        background-color: #ffffff !important;
        border-color: #d7e3ec !important;
        border-radius: 0.5rem !important;
    }
    [data-testid="stSidebar"] input:focus,
    [data-testid="stSidebar"] textarea:focus,
    [data-testid="stSidebar"] div[data-baseweb="select"]:focus-within > div,
    [data-testid="stSidebar"] div[data-baseweb="input"]:focus-within > div,
    [data-testid="stSidebar"] div[data-baseweb="textarea"]:focus-within > div {
        border-color: rgb(0, 80, 143) !important;
        box-shadow: 0 0 0 1px rgb(0, 80, 143) !important;
    }
    [data-testid="stSidebar"] [data-testid="stBaseButton-primary"] {
        background-color: rgb(0, 80, 143) !important;
        border-color: rgb(0, 80, 143) !important;
        color: #ffffff !important;
    }
    [data-testid="stSidebar"] [data-testid="stBaseButton-primary"] * {
        color: #ffffff !important;
    }
    [data-testid="stSidebar"] hr {
        border-color: #d7e3ec !important;
    }
    @media (max-width: 900px) {
        .app-header {align-items: flex-start;}
        .app-header img {width: 112px; height: 112px;}
        .app-header h1 {font-size: 1.9rem;}
        .app-header p {font-size: 1.05rem;}
    }
    div[data-testid="stMetric"] {
        background: #f8fafc;
        border: 1px solid #d7e3ec;
        padding: 0.75rem;
        border-radius: 0.75rem;
    }
    :root {
        --primary-color: rgb(0, 80, 143) !important;
    }
    [data-testid="stBaseButton-primary"] {
        background-color: rgb(0, 80, 143) !important;
        border-color: rgb(0, 80, 143) !important;
        color: white !important;
    }
    [data-testid="stBaseButton-primary"]:hover {
        background-color: rgb(0, 66, 118) !important;
        border-color: rgb(0, 66, 118) !important;
        color: white !important;
    }
    div.stButton > button:first-child,
    div.stDownloadButton > button:first-child {
        border-radius: 0.5rem;
        font-weight: 600;
    }
    div[data-testid="stDataFrame"], div[data-testid="stDataEditor"] {
        max-width: 100%;
        overflow-x: hidden !important;
    }
    div[data-testid="stDataFrame"] *,
    div[data-testid="stDataEditor"] * {
        max-width: 100%;
    }
    div[data-testid="stDataEditor"] [role="row"]:last-child [role="gridcell"],
    div[data-testid="stDataEditor"] [role="row"]:last-child [role="columnheader"] {
        background-color: #eef2f7 !important;
        font-weight: 700 !important;
    }
    div[data-testid="stDataEditor"] [role="row"]:last-child [role="gridcell"] * {
        font-weight: 700 !important;
    }
    input[type="checkbox"] {
        accent-color: rgb(0, 80, 143) !important;
    }
    /* Do not override Streamlit's generated .st-* classes.
       Those names are unstable and can land on the wrong elements.
       Use stable widget attributes instead. */

    /* BaseWeb/Streamlit checkbox: the visible square is the first span inside the label.
       Streamlit's generated red classes often land here, so target the stable BaseWeb structure. */
    label[data-baseweb="checkbox"] > span:first-child {
        border-color: rgb(0, 80, 143) !important;
    }
    label[data-baseweb="checkbox"]:has(input:checked) > span:first-child {
        background-color: rgb(0, 80, 143) !important;
        border-color: rgb(0, 80, 143) !important;
    }
    label[data-baseweb="checkbox"]:focus-within > span:first-child {
        border-color: rgb(0, 80, 143) !important;
        box-shadow: 0 0 0 2px rgba(0, 80, 143, 0.18) !important;
    }
    label[data-baseweb="checkbox"] svg {
        color: white !important;
        fill: white !important;
        stroke: white !important;
    }

    div[data-baseweb="select"] div[role="button"],
    div[data-baseweb="select"] div[role="combobox"] {
        border-color: transparent !important;
    }
    div[data-baseweb="select"]:focus-within div[role="button"],
    div[data-baseweb="select"]:focus-within div[role="combobox"] {
        border-color: rgb(0, 80, 143) !important;
        box-shadow: 0 0 0 1px rgb(0, 80, 143) !important;
    }
    span[data-baseweb="tag"] *,
    div[data-baseweb="tag"] * {
        background-color: transparent !important;
        color: rgb(0, 80, 143) !important;
    }
    button[aria-label="Remove"],
    button[title="Remove"] {
        color: rgb(0, 80, 143) !important;
    }
    div[data-testid="stCheckbox"] input[type="checkbox"] {
        accent-color: rgb(0, 80, 143) !important;
    }
    div[data-baseweb="input"] input:focus,
    div[data-baseweb="textarea"] textarea:focus,
    textarea:focus,
    input:focus {
        border-color: rgb(0, 80, 143) !important;
        outline-color: rgb(0, 80, 143) !important;
        box-shadow: 0 0 0 1px rgb(0, 80, 143) !important;
    }
    div[data-testid="stCheckbox"] label p {
        background-color: transparent !important;
        color: #303241 !important;
    }
    div[data-testid="stCheckbox"] label p::selection {
        background: rgba(0, 80, 143, 0.18) !important;
        color: inherit !important;
    }
    span[data-baseweb="tag"], div[data-baseweb="tag"] {
        background-color: rgba(0, 80, 143, 0.12) !important;
        color: rgb(0, 80, 143) !important;
        border-color: rgba(0, 80, 143, 0.35) !important;
    }
    .criteria-placeholder-note {
        background: #eef2f7;
        border: 1px solid #cbd5e1;
        border-radius: 0.5rem;
        padding: 0.65rem 0.85rem;
        color: #334155;
        font-weight: 700;
        margin-top: -0.35rem;
        margin-bottom: 0.75rem;
    }
    .fixed-table-wrap {
        width: 100%;
        overflow-x: hidden;
    }
    table.fixed-table {
        table-layout: fixed;
        width: 100%;
        border-collapse: collapse;
        font-size: 0.9rem;
    }
    table.fixed-table th {
        background: #f8fafc;
        border: 1px solid #d7e3ec;
        padding: 0.5rem;
        text-align: left;
        vertical-align: top;
        overflow-wrap: anywhere;
        word-break: break-word;
    }
    table.fixed-table td {
        border: 1px solid #d7e3ec;
        padding: 0.5rem;
        vertical-align: top;
        white-space: normal;
        overflow-wrap: anywhere;
        word-break: break-word;
    }
    table.fixed-table details.cell-details {
        cursor: pointer;
    }
    table.fixed-table details.cell-details summary {
        list-style: none;
        color: #303241;
        font-weight: 400;
        line-height: 1.35;
    }
    table.fixed-table details.cell-details summary::-webkit-details-marker {
        display: none;
    }
    table.fixed-table details.cell-details summary::marker {
        content: "";
    }
    table.fixed-table details.cell-details .cell-preview {
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
        white-space: normal;
    }
    table.fixed-table details.cell-details .cell-full-summary {
        display: none;
        white-space: pre-wrap;
        color: #303241;
        font-weight: 400;
    }
    table.fixed-table tr:has(details.cell-details[open]) details.cell-details .cell-preview {
        display: none;
    }
    table.fixed-table tr:has(details.cell-details[open]) details.cell-details .cell-full-summary {
        display: inline;
    }
    table.fixed-table tr:nth-child(even) td {
        background: #fbfdff;
    }
    .locked-criteria-hint {
        color: #52677a;
        font-size: 0.9rem;
    }

    .criteria-grid {
        width: 100%;
        border: 1px solid #d7e3ec;
        border-bottom: 0;
        margin-top: 0.35rem;
    }
    .criteria-grid-row {
        display: grid;
        grid-template-columns: 16% 28% 28% 28%;
        border-bottom: 1px solid #d7e3ec;
    }
    .criteria-grid-cell {
        padding: 0.55rem 0.65rem;
        border-right: 1px solid #d7e3ec;
        min-width: 0;
        overflow-wrap: anywhere;
        word-break: break-word;
        line-height: 1.35;
    }
    .criteria-grid-cell:last-child {border-right: 0;}
    .criteria-grid-header .criteria-grid-cell {
        background: #f8fafc;
        font-weight: 800;
        color: #1f2937;
    }
    .criteria-grid-locked:nth-child(odd) .criteria-grid-cell {background: #ffffff;}
    .criteria-grid-locked:nth-child(even) .criteria-grid-cell {background: #fbfdff;}
    .criteria-grid-locked .criteria-grid-cell {
        color: #303241;
    }
    div[class*="st-key-criteria_custom_row"] {
        border-left: 1px solid #d7e3ec;
        border-right: 1px solid #d7e3ec;
        border-bottom: 1px solid #d7e3ec;
        padding: 0.35rem 0.5rem 0.15rem 0.5rem;
    }
    div[class*="st-key-criteria_add_row"] {
        background: #eef2f7 !important;
        border: 2px solid #cbd5e1 !important;
        padding: 0.45rem 0.55rem 0.2rem 0.55rem !important;
        margin-top: 0 !important;
        border-radius: 0 0 0.35rem 0.35rem;
    }
    div[class*="st-key-criteria_add_row"] input,
    div[class*="st-key-criteria_add_row"] textarea {
        background-color: #f1f5f9 !important;
        font-weight: 800 !important;
        color: #1f2937 !important;
    }
    div[class*="st-key-criteria_add_row"] input::placeholder,
    div[class*="st-key-criteria_add_row"] textarea::placeholder {
        color: #334155 !important;
        opacity: 1 !important;
        font-style: italic !important;
        font-weight: 800 !important;
    }
    div[class*="st-key-criteria_add_row"] [data-testid="stTextArea"] label,
    div[class*="st-key-criteria_add_row"] [data-testid="stTextInput"] label {
        font-weight: 800 !important;
    }
    /* Keep Streamlit checkbox labels from inheriting a filled background.
       The checkbox color itself is controlled by the Streamlit theme primaryColor. */
    div[data-testid="stCheckbox"] label p {
        background: transparent !important;
    }
    /* Evaluation profile action row: make all controls visually identical. */
    div[class*="st-key-load_preset_profile_btn"] button,
    div[class*="st-key-save_evaluation_profile_btn"] button,
    div[class*="st-key-process_ai_review_btn"] button,
    .profile-upload-faux-button {
        width: 100% !important;
        height: 2.9rem !important;
        min-height: 2.9rem !important;
        border-radius: 0.5rem !important;
        border: 1px solid #d1d5db !important;
        background: #ffffff !important;
        color: #303241 !important;
        font-size: 1rem !important;
        font-weight: 400 !important;
        line-height: 1.4 !important;
        padding: 0.25rem 0.75rem !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        box-sizing: border-box !important;
        white-space: nowrap !important;
        overflow: hidden !important;
        text-align: center !important;
        margin: 0 !important;
    }
    div[class*="st-key-load_preset_profile_btn"] button:hover,
    div[class*="st-key-save_evaluation_profile_btn"] button:hover,
    .profile-upload-faux-button:hover {
        border-color: rgb(0, 80, 143) !important;
        color: #303241 !important;
        background: #ffffff !important;
    }
    div[class*="st-key-process_ai_review_btn"] button {
        background-color: rgb(0, 80, 143) !important;
        border-color: rgb(0, 80, 143) !important;
        color: #ffffff !important;
    }
    div[class*="st-key-process_ai_review_btn"] button:hover:not(:disabled) {
        background-color: rgb(0, 66, 118) !important;
        border-color: rgb(0, 66, 118) !important;
        color: #ffffff !important;
    }
    div[class*="st-key-process_ai_review_btn"] button:disabled {
        opacity: 0.65 !important;
    }
    div[class*="st-key-process_ai_review_btn"] button * {
        color: inherit !important;
    }

    /* Functional upload button overlay.
       The visible part is a normal button-looking div. The real Streamlit uploader
       is transparent and sits on top so selecting a JSON file triggers immediately. */
    div[class*="st-key-profile_upload_button"] {
        position: relative !important;
        height: 2.9rem !important;
        min-height: 2.9rem !important;
        margin: 0 !important;
    }
    div[class*="st-key-profile_upload_button"] .profile-upload-faux-button {
        position: absolute !important;
        inset: 0 !important;
        z-index: 1 !important;
        pointer-events: none !important;
    }
    div[class*="st-key-profile_upload_button"] [data-testid="stFileUploader"] {
        position: absolute !important;
        inset: 0 !important;
        z-index: 2 !important;
        opacity: 0 !important;
        height: 2.9rem !important;
        min-height: 2.9rem !important;
        cursor: pointer !important;
        margin: 0 !important;
        padding: 0 !important;
    }
    div[class*="st-key-profile_upload_button"] [data-testid="stFileUploaderDropzone"] {
        height: 2.9rem !important;
        min-height: 2.9rem !important;
        padding: 0 !important;
        margin: 0 !important;
        border: 0 !important;
        background: transparent !important;
        cursor: pointer !important;
    }
    div[class*="st-key-profile_upload_button"] [data-testid="stFileUploaderDropzone"] button {
        width: 100% !important;
        height: 2.9rem !important;
        min-height: 2.9rem !important;
        cursor: pointer !important;
    }
    div[class*="st-key-profile_upload_button"] [data-testid="stFileUploaderFile"],
    div[class*="st-key-profile_upload_button"] [data-testid="stFileUploaderDeleteBtn"],
    div[class*="st-key-profile_upload_button"] [data-testid="InputInstructions"] {
        display: none !important;
    }




    </style>

    """,
    unsafe_allow_html=True,
)


def table_height(row_count: int, extra_rows: int = 1) -> int:
    """Return enough height to avoid Streamlit's internal vertical scrolling."""
    return max(130, (row_count + extra_rows) * 38 + 20)


def load_default_criteria() -> pd.DataFrame:
    with open(CRITERIA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return normalize_criteria_df(pd.DataFrame(data))


def normalize_criteria_df(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # Compatibility with the first prototype profile shape.
    if "enabled" in df.columns:
        df = df[df["enabled"] != False].copy()  # noqa: E712
    if "required" in df.columns and "locked" not in df.columns:
        df["locked"] = df["required"].fillna(False).astype(bool)

    for col in CRITERIA_COLUMNS:
        if col not in df.columns:
            if col == "locked":
                df[col] = False
            elif col == "id":
                df[col] = ""
            elif col == "inventory_field":
                df[col] = "Notes / Follow-up"
            else:
                df[col] = ""

    for idx in df.index:
        if not str(df.at[idx, "id"]).strip():
            seed = "|".join(
                str(df.at[idx, c])
                for c in ["category", "review_question", "why_this_matters"]
                if c in df.columns
            )
            df.at[idx, "id"] = "custom_" + hashlib.sha1(seed.encode("utf-8")).hexdigest()[:10]

    df["locked"] = df["locked"].fillna(False).astype(bool)
    for col in CRITERIA_COLUMNS:
        if col != "locked":
            df[col] = df[col].fillna("").astype(str)
    return df[CRITERIA_COLUMNS].reset_index(drop=True)


def criteria_signature(df: pd.DataFrame) -> str:
    normalized = normalize_criteria_df(df)
    records = normalized[CRITERIA_COLUMNS].fillna("").to_dict(orient="records")
    blob = json.dumps(records, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def current_profile_modified() -> bool:
    return criteria_signature(st.session_state.criteria_df) != criteria_signature(load_default_criteria())


def criteria_profile_bytes(df: pd.DataFrame) -> bytes:
    normalized = normalize_criteria_df(df)
    payload = {
        "profile_name": "Evaluation criteria profile",
        "app": APP_TITLE,
        "saved_at": datetime.now().isoformat(timespec="seconds"),
        "criteria": normalized.to_dict(orient="records"),
    }
    return json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8")


def load_profile_from_json(uploaded_file) -> pd.DataFrame:
    if isinstance(uploaded_file, (bytes, bytearray)):
        raw = bytes(uploaded_file)
    else:
        raw = uploaded_file.getvalue()
    data = json.loads(raw.decode("utf-8"))
    if isinstance(data, dict) and "criteria" in data:
        data = data["criteria"]
    if not isinstance(data, list):
        raise ValueError("Evaluation profile JSON must contain a list of criteria or a 'criteria' array.")
    return normalize_criteria_df(pd.DataFrame(data))


def initialize_state() -> None:
    if "criteria_df" not in st.session_state:
        st.session_state.criteria_df = load_default_criteria()
    if "review_payload" not in st.session_state:
        st.session_state.review_payload = None
    if "review_rows" not in st.session_state:
        st.session_state.review_rows = None
    if "rule_summary" not in st.session_state:
        st.session_state.rule_summary = None
    if "extracted_text" not in st.session_state:
        st.session_state.extracted_text = ""
    if "show_preset_confirm" not in st.session_state:
        st.session_state.show_preset_confirm = False
    if "loaded_profile_hash" not in st.session_state:
        st.session_state.loaded_profile_hash = ""
    if "criteria_editor_version" not in st.session_state:
        st.session_state.criteria_editor_version = 0
    if "profile_upload_version" not in st.session_state:
        st.session_state.profile_upload_version = 0


def extract_pdf_text(uploaded_file) -> Tuple[str, List[Dict[str, Any]]]:
    pdf_bytes = uploaded_file.getvalue()
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    pages = []
    full_text_parts = []
    for i, page in enumerate(doc, start=1):
        text = page.get_text("text") or ""
        cleaned = re.sub(r"\n{3,}", "\n\n", text).strip()
        pages.append({"page": i, "char_count": len(cleaned), "text": cleaned})
        full_text_parts.append(f"\n\n--- PDF PAGE {i} ---\n{cleaned}")
    return "".join(full_text_parts).strip(), pages


def truncate_text(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    head = int(max_chars * 0.65)
    tail = max_chars - head
    return (
        text[:head]
        + "\n\n[...PDF text truncated for token control...]\n\n"
        + text[-tail:]
    )


def compact_criteria(criteria_df: pd.DataFrame) -> List[Dict[str, Any]]:
    fields = [
        "category",
        "review_question",
        "why_this_matters",
        "what_to_look_for",
        "inventory_field",
    ]
    normalized = normalize_criteria_df(criteria_df)
    return normalized[fields].fillna("").to_dict(orient="records")


def sc_id(label: str) -> str:
    return label.split(" ", 1)[0].strip()


def build_prompt(
    pdf_text: str,
    criteria: List[Dict[str, Any]],
    context: Dict[str, Any],
    risk_settings: Dict[str, Any],
) -> str:
    return f"""
You are assisting UC Irvine Libraries staff with an AI-assisted review of a vendor Accessibility Conformance Report (ACR), also called a completed VPAT.

Important boundaries:
- Do NOT claim that the product itself is accessible or inaccessible.
- Review the uploaded PDF as documentation evidence only.
- Use plain English for staff with little to no accessibility background.
- Prefer "risk", "evidence", "documentation quality", and "needs follow-up" over legal conclusions.
- If evidence is missing or ambiguous, say "Not Found" or "Needs Human Review".
- Keep evidence excerpts short.
- Do not create a product-match question based on the document ID. The document ID is only the uploaded PDF file name.

Library-provided review context:
{json.dumps(context, indent=2)}

UC Irvine defined risk-level criteria settings:
{json.dumps(risk_settings, indent=2)}

Evaluation criteria:
{json.dumps(criteria, indent=2)}

Extracted PDF text:
{pdf_text}

Return ONLY valid JSON using this exact shape:
{{
  "document_summary": {{
    "company_name": "string or Not Found",
    "product_name": "string or Not Found",
    "product_version_or_build": "string or Not Found",
    "report_date": "string or Not Found",
    "vpat_version_or_edition": "string or Not Found",
    "wcag_level": "string or Not Found",
    "evaluation_methods": "short string or Not Found",
    "accessibility_statement": "string or Not Found"
  }},
  "critical_scan": [
    {{
      "sc": "2.1.1",
      "name": "Keyboard",
      "conformance_term": "Supports / Partially Supports / Does Not Support / Not Applicable / Not Evaluated / Not Found",
      "remarks": "short excerpt or summary",
      "page_or_section": "page/section if known",
      "dated_plan_found": "Yes / No / Partial / Unknown",
      "common_library_workflow_impact": "Yes / No / Unclear",
      "confidence": "High / Medium / Low"
    }}
  ],
  "criteria_results": [
    {{
      "review_area": "category",
      "review_item": "criterion question",
      "result": "Pass / Concern / Fail / Not Found / Needs Human Review",
      "what_ai_found": "short plain-English finding",
      "evidence_location": "page/section/table if known",
      "evidence_text": "short excerpt; do not quote long passages",
      "rationale": "why this result was chosen",
      "recommended_action": "what staff should do next",
      "inventory_field": "matching inventory/spreadsheet field from the criterion"
    }}
  ],
  "vendor_follow_up_questions": ["short question 1", "short question 2"],
  "known_issues_bullets": ["short bullet 1", "short bullet 2"],
  "notes": "short plain-English notes"
}}
""".strip()


def strip_json_fence(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()


def parse_json_response(text: str) -> Dict[str, Any]:
    cleaned = strip_json_fence(text)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise


def call_openai_review(
    api_key: str,
    model: str,
    prompt: str,
) -> Dict[str, Any]:
    client = OpenAI(api_key=api_key)
    response = client.responses.create(
        model=model,
        input=[
            {
                "role": "system",
                "content": "You are a careful accessibility documentation reviewer. Return only valid JSON.",
            },
            {"role": "user", "content": prompt},
        ],
    )
    text = getattr(response, "output_text", None)
    if not text:
        text = str(response)
    return parse_json_response(text)


def normalize_rows(payload: Dict[str, Any]) -> pd.DataFrame:
    rows = payload.get("criteria_results", []) or []
    normalized = []
    for row in rows:
        item = {col: row.get(col, "") for col in RESULT_COLUMNS}
        normalized.append(item)
    df = pd.DataFrame(normalized)
    for col in RESULT_COLUMNS:
        if col not in df.columns:
            df[col] = ""
    return df[RESULT_COLUMNS]


def find_value(summary: Dict[str, Any], key: str) -> str:
    value = str(summary.get(key, "") or "").strip()
    if not value or value.lower() in {"not found", "none", "n/a", "unknown"}:
        return ""
    return value


def try_parse_date(value: str) -> Optional[date]:
    if not value:
        return None
    try:
        return date_parser.parse(value, fuzzy=True, default=datetime(1900, 1, 1)).date()
    except Exception:
        return None


def is_stale(
    report_date: Optional[date],
    product_version: str,
    tier: str,
    risk_settings: Dict[str, Any],
) -> Tuple[bool, str]:
    missing_version_is_stale = bool(risk_settings.get("missing_version_or_date_is_stale", True))
    if not product_version and missing_version_is_stale:
        return True, "Missing product version/build; treated as stale under the selected UC Irvine criteria."
    if report_date is None and missing_version_is_stale:
        return True, "Missing or unreadable report date; treated as stale under the selected UC Irvine criteria."
    if report_date is None:
        return False, "Report date not found, but the stale check was relaxed in the advanced settings."

    age_days = (date.today() - report_date).days
    tier_lower = tier.lower()
    if "tier 1" in tier_lower:
        months = int(risk_settings.get("tier_1_stale_months", 12))
    elif "tier 2" in tier_lower:
        months = int(risk_settings.get("tier_2_stale_months", 18))
    else:
        months = int(risk_settings.get("tier_3_stale_months", 24))

    threshold_days = int(months * 30.4375)
    if age_days > threshold_days:
        return True, f"Report appears older than the selected {months}-month threshold."
    return False, f"Report appears within the selected {months}-month threshold."


def normalize_term(term: str) -> str:
    term = (term or "").lower().strip()
    term = term.replace("_", " ").replace("-", " ")
    return re.sub(r"\s+", " ", term)


def gate_value(value: str) -> str:
    value = (value or "").strip()
    if not value:
        return "Unknown"
    lower = value.lower()
    if lower.startswith("yes"):
        return "Yes"
    if lower.startswith("no"):
        return "No"
    if "skip" in lower or "not needed" in lower:
        return "Skip"
    if "unclear" in lower or "unknown" in lower:
        return "Unclear"
    return value.split()[0]


def wcag_coverage_present(wcag_level: str, risk_settings: Dict[str, Any]) -> bool:
    """Check whether the ACR text appears to cover the selected WCAG version/level.

    WCAG conformance levels are cumulative: Level AA includes Level A success
    criteria, and Level AAA includes Level A and Level AA success criteria. This
    function therefore evaluates the highest selected level needed and accepts a
    document that clearly reports that level or a higher level.
    """
    wcag_lower = (wcag_level or "").lower()
    selected_versions = [str(v).lower() for v in risk_settings.get("wcag_versions", ["WCAG 2.1"])]
    raw_levels = risk_settings.get("wcag_levels", ["Level AA"])
    if isinstance(raw_levels, str):
        raw_levels = [raw_levels]
    selected_levels = [str(v).lower().replace("level", "").strip() for v in raw_levels]

    version_present = any(version in wcag_lower for version in selected_versions)
    if not version_present:
        return False

    def level_rank(level: str) -> int:
        level = level.strip().lower()
        if level == "aaa":
            return 3
        if level == "aa":
            return 2
        if level == "a":
            return 1
        return 0

    required_rank = max([level_rank(level) for level in selected_levels] or [2])

    # Identify the highest level explicitly reported in the ACR summary text.
    # Check AAA before AA before A so the shorter tokens do not steal matches.
    if re.search(r"\blevel\s+aaa\b|\baaa\b", wcag_lower):
        found_rank = 3
    elif re.search(r"\blevel\s+aa\b|\baa\b|\ba/aa\b|\ba\s+and\s+aa\b", wcag_lower):
        found_rank = 2
    elif re.search(r"\blevel\s+a\b|\ba\b", wcag_lower):
        found_rank = 1
    else:
        found_rank = 0

    return found_rank >= required_rank


def compute_rule_summary(
    payload: Dict[str, Any],
    context: Dict[str, Any],
    risk_settings: Dict[str, Any],
) -> Dict[str, Any]:
    summary = payload.get("document_summary", {}) or {}
    company = find_value(summary, "company_name")
    product = find_value(summary, "product_name")
    version = find_value(summary, "product_version_or_build")
    report_date_raw = find_value(summary, "report_date")
    wcag_level = find_value(summary, "wcag_level")
    vpat_version = find_value(summary, "vpat_version_or_edition")
    eval_methods = find_value(summary, "evaluation_methods")

    report_date = try_parse_date(report_date_raw)
    acr_usable = all([company, product, version, report_date_raw])
    wcag_present = wcag_coverage_present(wcag_level, risk_settings)

    selected_sc = [sc_id(x) for x in risk_settings.get("critical_criteria", DEFAULT_CRITICAL_SC)]
    critical_scan = payload.get("critical_scan", []) or []
    core_issue_items = []
    all_core_dated = True
    has_dated_info = False
    for item in critical_scan:
        sc = str(item.get("sc", ""))
        term = normalize_term(str(item.get("conformance_term", "")))
        if any(sc.startswith(x) for x in selected_sc):
            if term in {"partially supports", "does not support"}:
                core_issue_items.append(item)
                dated = normalize_term(str(item.get("dated_plan_found", "")))
                if dated == "yes":
                    has_dated_info = True
                else:
                    all_core_dated = False
    core_issue = len(core_issue_items) > 0
    dated_plan = core_issue and all_core_dated and has_dated_info

    stale, stale_reason = is_stale(report_date, version, context.get("product_tier", ""), risk_settings)

    usage = context.get("usage_level", "").lower()
    if not acr_usable:
        risk = "High"
        risk_reason = "Required ACR identity information is missing: company name, product name, product version/build, or report date."
    elif not wcag_present:
        risk = "High"
        risk_reason = "WCAG Level A/AA coverage was not clearly found under the selected UC Irvine criteria."
    elif not core_issue:
        if stale:
            risk = "Medium"
            risk_reason = "No core issue was identified in the critical scan, but the ACR appears stale."
        else:
            risk = "Low"
            risk_reason = "ACR identity information is present, WCAG A/AA coverage is present, no core issue was identified, and the ACR does not appear stale."
    else:
        if dated_plan:
            risk = "Medium"
            risk_reason = "Core issue found, but a dated plan appears available for all core issues."
        else:
            if "low" in usage:
                risk = str(risk_settings.get("low_usage_core_issue_no_plan_risk", "Medium"))
                risk_reason = f"Core issue found without a dated remediation plan. Usage is marked Low, so the selected UC Irvine criteria assign {risk} risk."
            else:
                risk = str(risk_settings.get("medium_high_usage_core_issue_no_plan_risk", "High"))
                risk_reason = f"Core issue found without a dated remediation plan. Usage is marked High/Medium, so the selected UC Irvine criteria assign {risk} risk."

    dated_label = "Yes" if dated_plan else ("No" if core_issue else "Skip")

    return {
        "recommended_risk": risk,
        "risk_reason": risk_reason,
        "acr_usable": "Yes" if acr_usable else "No",
        "wcag_a_aa_present": "Yes" if wcag_present else "No",
        "core_issue_found": "Yes" if core_issue else "No",
        "dated_plan_found": dated_label,
        "acr_stale": "Yes" if stale else "No",
        "stale_reason": stale_reason,
        "company_name": company or "Not Found",
        "product_name": product or "Not Found",
        "product_version_or_build": version or "Not Found",
        "report_date": report_date_raw or "Not Found",
        "vpat_version_or_edition": vpat_version or "Not Found",
        "wcag_level": wcag_level or "Not Found",
        "evaluation_methods": eval_methods or "Not Found",
        "known_issues_bullets": payload.get("known_issues_bullets", []) or [],
        "vendor_follow_up_questions": payload.get("vendor_follow_up_questions", []) or [],
        "risk_settings": risk_settings,
    }


def dataframe_to_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")


def questions_to_text(questions: List[str]) -> str:
    if not questions:
        return "No specific vendor follow-up questions generated."
    return "\n".join(f"- {q}" for q in questions)


def useful_result_rows(rows_df: pd.DataFrame, field: str) -> pd.DataFrame:
    if rows_df is None or rows_df.empty or "inventory_field" not in rows_df.columns:
        return pd.DataFrame()
    matches = rows_df[rows_df["inventory_field"].fillna("").str.lower() == field.lower()].copy()
    if matches.empty:
        return matches
    concern_terms = {"concern", "fail", "not found", "needs human review"}
    result_mask = matches["result"].fillna("").str.lower().isin(concern_terms)
    filtered = matches[result_mask]
    return filtered if not filtered.empty else matches


def summarize_rows_for_field(rows_df: pd.DataFrame, field: str, fallback: str = "") -> str:
    matches = useful_result_rows(rows_df, field)
    if matches.empty:
        return fallback
    bullets = []
    for _, row in matches.iterrows():
        item = str(row.get("review_item", "")).strip()
        finding = str(row.get("what_ai_found", "")).strip()
        result = str(row.get("result", "")).strip()
        if finding:
            bullets.append(f"- {item}: {result}. {finding}")
        else:
            bullets.append(f"- {item}: {result}.")
    return "\n".join(bullets)


def inventory_summary(rule_summary: Dict[str, Any], context: Dict[str, Any], rows_df: pd.DataFrame) -> pd.DataFrame:
    known_issues_from_rows = summarize_rows_for_field(rows_df, "Known Issues")
    known_issues_from_payload = rule_summary.get("known_issues_bullets", [])
    if known_issues_from_rows:
        known_issues = known_issues_from_rows
    elif known_issues_from_payload:
        known_issues = "\n".join(f"- {x}" for x in known_issues_from_payload)
    else:
        known_issues = "None identified in AI-assisted critical scan."

    notes_from_rows = summarize_rows_for_field(rows_df, "Notes / Follow-up")
    notes = [
        f"Document ID: {context.get('document_id', 'Not Found')}",
        f"Product identified in ACR: {rule_summary.get('product_name', 'Not Found')}",
        f"Version/build: {rule_summary.get('product_version_or_build', 'Not Found')}",
        f"Report date: {rule_summary.get('report_date', 'Not Found')}",
        f"Staleness: {rule_summary.get('acr_stale')} — {rule_summary.get('stale_reason')}",
        f"Risk rationale: {rule_summary.get('risk_reason')}",
    ]
    if notes_from_rows:
        notes.append("Evaluation Results tied to Notes / Follow-up:")
        notes.append(notes_from_rows)

    data = {
        "ID": context.get("document_id", "Not Found"),
        "VPAT Provided": context.get("acr_source", "Uploaded PDF"),
        "WCAG Level": rule_summary.get("wcag_level", "Not Found"),
        "VPAT Version": rule_summary.get("vpat_version_or_edition", "Not Found"),
        "Known Issues": known_issues,
        "Vendor Roadmap Provided": rule_summary.get("dated_plan_found", "Unknown"),
        "Risk Level": rule_summary.get("recommended_risk", "Needs Human Review"),
        "Note": "\n".join(notes),
        "Last Updated": date.today().isoformat(),
    }
    return pd.DataFrame([data])


def render_table_cell(value: str, collapse_threshold: int = 90) -> str:
    """Render compact cells that expand in place without link styling or nested text boxes."""
    value = value or ""
    escaped = html.escape(value)
    is_long = len(value) > collapse_threshold or "\n" in value
    if not is_long:
        return f"<span>{escaped}</span>"

    single_line = " ".join(value.split())
    preview = single_line[:160] + ("…" if len(single_line) > 160 else "")
    return (
        '<details class="cell-details" title="Click to expand or collapse this cell">'
        '<summary>'
        f'<span class="cell-preview">{html.escape(preview)}</span>'
        f'<span class="cell-full-summary">{escaped}</span>'
        '</summary>'
        '</details>'
    )


def render_fixed_table(df: pd.DataFrame, column_labels: Optional[Dict[str, str]] = None) -> None:
    """Render a fixed-width HTML table with compact expandable cells."""
    if df is None or df.empty:
        st.info("No rows available.")
        return
    column_labels = column_labels or {}
    cols = list(df.columns)
    header = "".join(f"<th>{html.escape(column_labels.get(c, c))}</th>" for c in cols)
    body_rows = []
    for _, row in df.iterrows():
        cells = []
        for c in cols:
            value = "" if pd.isna(row.get(c, "")) else str(row.get(c, ""))
            cells.append(f"<td>{render_table_cell(value)}</td>")
        body_rows.append("<tr>" + "".join(cells) + "</tr>")
    table_html = (
        '<div class="fixed-table-wrap"><table class="fixed-table">'
        f"<thead><tr>{header}</tr></thead>"
        f"<tbody>{''.join(body_rows)}</tbody>"
        "</table></div>"
    )
    st.markdown(table_html, unsafe_allow_html=True)


def sanitize_filename(name: str, default: str = "acr_review") -> str:
    stem = Path(name or default).stem
    stem = re.sub(r"[^A-Za-z0-9._-]+", "_", stem).strip("._-")
    return stem or default


initialize_state()


@st.dialog("Replace current evaluation profile?")
def confirm_preset_dialog() -> None:
    st.write(
        "Loading the preset evaluation profile will overwrite the current evaluation criteria table, including added rows."
    )
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Replace with preset", type="primary"):
            st.session_state.criteria_df = load_default_criteria()
            st.session_state.criteria_editor_version += 1
            st.session_state.show_preset_confirm = False
            st.rerun()
    with c2:
        if st.button("Cancel"):
            st.session_state.show_preset_confirm = False
            st.rerun()


with st.sidebar:
    st.header("Settings")
    openai_api_key = st.text_input("OpenAI API key", type="password", help="Used only for this AI-assisted review session.")
    model = st.selectbox(
        "OpenAI model",
        ["gpt-4.1-mini"],
        index=0,
        help="Use the model available to your OpenAI API account.",
    )
    st.caption("For completeness, the app sends all extracted PDF text to AI. For scanned PDFs, this prototype may need OCR later because it currently extracts embedded PDF text.")


logo_b64 = base64.b64encode(LOGO_PATH.read_bytes()).decode("ascii")
st.markdown(
    f'''<div class="app-header">
        <img src="data:image/jpeg;base64,{logo_b64}" alt="UC Irvine Libraries logo">
        <div>
            <h1>{APP_TITLE}</h1>
            <p>Upload an ACR/VPAT PDF, confirm the basic review context, adjust the evaluation criteria if needed, then process an AI-assisted documentation review.</p>
        </div>
    </div>''',
    unsafe_allow_html=True,
)

uploaded_pdf = st.file_uploader("Upload ACR/VPAT PDF", type=["pdf"])
document_id = uploaded_pdf.name if uploaded_pdf else "The uploaded PDF file name will be used as the ID."
id_col, tier_col, usage_col = st.columns(3)
with id_col:
    st.text_input("ID", value=document_id, disabled=True, help="This is automatically based on the uploaded PDF file name.")
with tier_col:
    product_tier = st.text_input("Product tier", value="Tier 3", disabled=True, help="Locked for this prototype.")
with usage_col:
    usage_level = st.selectbox("Usage level", ["High Usage", "Medium Usage", "Low Usage", "Unknown"], index=1)

# Optional documentation context fields were removed from the staff-facing UI.
# Keep neutral defaults in the internal context so exported inventory rows and prompts stay stable.
acr_source = "Uploaded PDF"
accessibility_statement_url = ""
roadmap_notes = ""
additional_context = ""

with st.expander("UC Irvine defined risk-level criteria (advanced)", expanded=False):
    st.markdown(
        """
        These settings control the overall High / Medium / Low risk recommendation after the AI extracts evidence. In this app, the overall recommendation is based on **Gates**: each Gate checks one documentation or risk condition before the final risk level is assigned.

        UC Irvine Libraries currently follows **WCAG 2.1 Level AA** for this review workflow. WCAG conformance levels are cumulative: Level AA includes Level A requirements, and Level AAA includes Level A and Level AA requirements.

        - **Gate: ACR usable** — Missing company name, product name, product version/build, or report date means the ACR documentation is not usable for this protocol and the overall risk is High.
        - **Gate: WCAG coverage** — The selected WCAG version and level must be clearly present. If not, the overall risk is High.
        - **Gate: Core issue** — A core issue is triggered when a selected critical WCAG criterion is marked Partially Supports or Does Not Support.
        - **Gate: Staleness** — If no core issue is found, a current ACR can be Low risk; a stale ACR becomes Medium risk.
        - **Gate: Dated plan** — If a core issue is found, a dated remediation plan keeps the overall risk at Medium. Without a dated plan, High/Medium usage becomes High risk and Low usage becomes Medium risk by default.
        """
    )
    st.markdown("**WCAG coverage used for the WCAG coverage Gate**")
    w1, w2 = st.columns(2)
    with w1:
        wcag_versions = st.multiselect(
            "Accepted WCAG versions",
            ["WCAG 2.1", "WCAG 2.2"],
            default=["WCAG 2.1"],
        )
    with w2:
        wcag_level_requirement = st.selectbox(
            "Required WCAG conformance level",
            ["Level A", "Level AA", "Level AAA"],
            index=1,
            help="WCAG conformance levels are cumulative: Level AA includes Level A success criteria, and Level AAA includes Level A and Level AA success criteria.",
        )
        wcag_levels = [wcag_level_requirement]

    a1, a2, a3 = st.columns(3)
    with a1:
        missing_version_or_date_is_stale = st.checkbox("Missing version/date counts as stale", value=True)
    with a2:
        tier_3_stale_months = st.number_input("Tier 3 stale threshold in months", min_value=6, max_value=60, value=24, step=1)
    with a3:
        medium_high_usage_core_issue_no_plan_risk = st.selectbox(
            "Risk when High/Medium usage has core issue and no dated plan",
            ["High", "Medium"],
            index=0,
        )
        low_usage_core_issue_no_plan_risk = st.selectbox(
            "Risk when Low usage has core issue and no dated plan",
            ["Medium", "High", "Low"],
            index=0,
        )
    critical_criteria = st.multiselect(
        "Critical criteria used for core issue detection",
        CRITICAL_SC_OPTIONS,
        default=DEFAULT_CRITICAL_SC,
    )

risk_settings = {
    "wcag_versions": wcag_versions,
    "wcag_levels": wcag_levels,
    "missing_version_or_date_is_stale": missing_version_or_date_is_stale,
    "tier_1_stale_months": 12,
    "tier_2_stale_months": 18,
    "tier_3_stale_months": int(tier_3_stale_months),
    "medium_high_usage_core_issue_no_plan_risk": medium_high_usage_core_issue_no_plan_risk,
    "low_usage_core_issue_no_plan_risk": low_usage_core_issue_no_plan_risk,
    "critical_criteria": critical_criteria,
}

st.subheader("Evaluation Criteria")
st.caption("Preset rows are locked. Add new criteria by editing the blank bottom row.")
st.markdown('<div class="criteria-placeholder-note">The shaded bottom row is for a new custom criterion. Complete all four cells to add the row; another blank row will appear automatically.</div>', unsafe_allow_html=True)


def render_locked_criteria_table(locked_df: pd.DataFrame) -> None:
    """Render preset criteria as a locked, wrapping table."""
    headers = [
        ("Review area", "category"),
        ("Review question", "review_question"),
        ("Why this matters", "why_this_matters"),
        ("What to look for", "what_to_look_for"),
    ]
    parts = ['<div class="criteria-grid">']
    parts.append(
        '<div class="criteria-grid-row criteria-grid-header">'
        + ''.join(f'<div class="criteria-grid-cell">{html.escape(label)}</div>' for label, _ in headers)
        + '</div>'
    )
    for _, row in locked_df.iterrows():
        cells = []
        for _, col in headers:
            value = str(row.get(col, "") or "")
            cells.append(f'<div class="criteria-grid-cell">{html.escape(value)}</div>')
        parts.append('<div class="criteria-grid-row criteria-grid-locked">' + ''.join(cells) + '</div>')
    parts.append('</div>')
    st.markdown(''.join(parts), unsafe_allow_html=True)


def new_custom_record(values: Dict[str, str]) -> Dict[str, Any]:
    cleaned = {col: str(values.get(col, "") or "").strip() for col in DISPLAY_CRITERIA_COLUMNS}
    seed = "|".join(cleaned[col] for col in DISPLAY_CRITERIA_COLUMNS) + datetime.now().isoformat(timespec="microseconds")
    return {
        "id": "custom_" + hashlib.sha1(seed.encode("utf-8")).hexdigest()[:10],
        "locked": False,
        "category": cleaned["category"],
        "review_question": cleaned["review_question"],
        "why_this_matters": cleaned["why_this_matters"],
        "what_to_look_for": cleaned["what_to_look_for"],
        "inventory_field": "Notes / Follow-up",
    }


def render_criteria_editor() -> None:
    """Render a dependency-free criteria editor with locked preset rows and one gray add row."""
    criteria_df = normalize_criteria_df(st.session_state.criteria_df)
    locked_df = criteria_df[criteria_df["locked"]].copy().reset_index(drop=True)
    custom_df = criteria_df[~criteria_df["locked"]].copy().reset_index(drop=True)

    render_locked_criteria_table(locked_df)

    edited_custom_records = []
    for idx, row in custom_df.iterrows():
        row_id = str(row.get("id", f"custom_{idx}"))
        with st.container(key=f"criteria_custom_row_{row_id}"):
            c1, c2, c3, c4 = st.columns([16, 28, 28, 28])
            values = {}
            with c1:
                values["category"] = st.text_area(
                    "Review area",
                    value=str(row.get("category", "")),
                    key=f"criteria_custom_{row_id}_category",
                    label_visibility="collapsed",
                    height=72,
                )
            with c2:
                values["review_question"] = st.text_area(
                    "Review question",
                    value=str(row.get("review_question", "")),
                    key=f"criteria_custom_{row_id}_review_question",
                    label_visibility="collapsed",
                    height=72,
                )
            with c3:
                values["why_this_matters"] = st.text_area(
                    "Why this matters",
                    value=str(row.get("why_this_matters", "")),
                    key=f"criteria_custom_{row_id}_why_this_matters",
                    label_visibility="collapsed",
                    height=72,
                )
            with c4:
                values["what_to_look_for"] = st.text_area(
                    "What to look for",
                    value=str(row.get("what_to_look_for", "")),
                    key=f"criteria_custom_{row_id}_what_to_look_for",
                    label_visibility="collapsed",
                    height=72,
                )
        cleaned = {col: str(values.get(col, "") or "").strip() for col in DISPLAY_CRITERIA_COLUMNS}
        if any(cleaned.values()):
            edited_custom_records.append(
                {
                    "id": row_id,
                    "locked": False,
                    "category": cleaned["category"],
                    "review_question": cleaned["review_question"],
                    "why_this_matters": cleaned["why_this_matters"],
                    "what_to_look_for": cleaned["what_to_look_for"],
                    "inventory_field": str(row.get("inventory_field", "Notes / Follow-up") or "Notes / Follow-up"),
                }
            )

    placeholder_key_suffix = st.session_state.criteria_editor_version
    with st.container(key=f"criteria_add_row_{placeholder_key_suffix}"):
        p1, p2, p3, p4 = st.columns([16, 28, 28, 28])
        new_values = {}
        with p1:
            new_values["category"] = st.text_input(
                "New review area",
                value="",
                placeholder=PLACEHOLDER_VALUES["category"],
                key=f"criteria_new_{placeholder_key_suffix}_category",
                label_visibility="collapsed",
            )
        with p2:
            new_values["review_question"] = st.text_input(
                "New evaluation question",
                value="",
                placeholder=PLACEHOLDER_VALUES["review_question"],
                key=f"criteria_new_{placeholder_key_suffix}_review_question",
                label_visibility="collapsed",
            )
        with p3:
            new_values["why_this_matters"] = st.text_input(
                "New why this matters",
                value="",
                placeholder=PLACEHOLDER_VALUES["why_this_matters"],
                key=f"criteria_new_{placeholder_key_suffix}_why_this_matters",
                label_visibility="collapsed",
            )
        with p4:
            new_values["what_to_look_for"] = st.text_input(
                "New evidence to look for",
                value="",
                placeholder=PLACEHOLDER_VALUES["what_to_look_for"],
                key=f"criteria_new_{placeholder_key_suffix}_what_to_look_for",
                label_visibility="collapsed",
            )

    locked_records = locked_df[CRITERIA_COLUMNS].to_dict(orient="records")
    rebuilt_records = locked_records + edited_custom_records
    rebuilt_df = normalize_criteria_df(pd.DataFrame(rebuilt_records))

    if criteria_signature(rebuilt_df) != criteria_signature(st.session_state.criteria_df):
        st.session_state.criteria_df = rebuilt_df

    cleaned_new = {col: str(new_values.get(col, "") or "").strip() for col in DISPLAY_CRITERIA_COLUMNS}
    if all(cleaned_new.values()):
        next_records = normalize_criteria_df(st.session_state.criteria_df).to_dict(orient="records")
        next_records.append(new_custom_record(cleaned_new))
        st.session_state.criteria_df = normalize_criteria_df(pd.DataFrame(next_records))
        st.session_state.criteria_editor_version += 1
        st.rerun()


st.markdown("**Preset evaluation criteria**")
render_criteria_editor()

context = {
    "document_id": uploaded_pdf.name if uploaded_pdf else "Not available",
    "product_tier": product_tier,
    "usage_level": usage_level,
    "acr_source": acr_source or "Uploaded PDF",
    "accessibility_statement_url": accessibility_statement_url,
    "roadmap_notes": roadmap_notes,
    "additional_context": additional_context,
    "review_date": date.today().isoformat(),
}

st.divider()
profile_col1, profile_col2, profile_col3, process_col = st.columns(4)
with profile_col1:
    if st.button("Load preset evaluation profile", use_container_width=True, key="load_preset_profile_btn"):
        if current_profile_modified():
            st.session_state.show_preset_confirm = True
        else:
            st.session_state.criteria_df = load_default_criteria()
            st.session_state.criteria_editor_version += 1
            st.rerun()
with profile_col2:
    with st.container(key="profile_upload_button"):
        st.markdown('<div class="profile-upload-faux-button">Upload evaluation profile from file</div>', unsafe_allow_html=True)
        profile_file = st.file_uploader(
            "Upload evaluation profile from file",
            type=["json"],
            accept_multiple_files=False,
            key=f"profile_upload_file_{st.session_state.profile_upload_version}",
            label_visibility="collapsed",
            help="Upload a saved evaluation criteria profile JSON file.",
        )
    if profile_file is not None:
        profile_bytes = profile_file.getvalue()
        profile_hash = hashlib.sha256(profile_bytes).hexdigest()
        try:
            st.session_state.criteria_df = load_profile_from_json(profile_bytes)
            st.session_state.criteria_editor_version += 1
            st.session_state.loaded_profile_hash = profile_hash
            # Reset the uploader widget after a successful load so selecting a profile
            # triggers immediately every time, including if the same file is selected again later.
            st.session_state.profile_upload_version += 1
            st.toast("Evaluation profile loaded.")
            st.rerun()
        except Exception as e:
            st.error(f"Could not load evaluation profile: {e}")
with profile_col3:
    st.download_button(
        "Save evaluation profile JSON",
        criteria_profile_bytes(st.session_state.criteria_df),
        file_name="evaluation_criteria_profile.json",
        mime="application/json",
        use_container_width=True,
        key="save_evaluation_profile_btn",
    )
with process_col:
    run_disabled = not uploaded_pdf or not openai_api_key
    run_help = "Upload a PDF and enter an OpenAI API key before running."
    run_review = st.button(
        "Process AI-assisted review",
        type="primary",
        disabled=run_disabled,
        help=run_help if run_disabled else None,
        use_container_width=True,
        key="process_ai_review_btn",
    )

if st.session_state.show_preset_confirm:
    confirm_preset_dialog()

st.caption("The overall risk recommendation is calculated with rule-based logic after AI extracts evidence from the ACR text.")

if run_review:
    st.markdown('<div id="processing-status-panel"></div>', unsafe_allow_html=True)
    components.html(
        """
        <script>
        const target = window.parent.document.getElementById("processing-status-panel");
        if (target) {
            setTimeout(() => target.scrollIntoView({behavior: "smooth", block: "start"}), 80);
        }
        </script>
        """,
        height=0,
    )
    try:
        with st.status("Reviewing ACR/VPAT PDF...", expanded=True) as status:
            st.write("Extracting text from PDF...")
            pdf_text, page_stats = extract_pdf_text(uploaded_pdf)
            st.session_state.extracted_text = pdf_text
            if not pdf_text.strip():
                st.warning("No embedded PDF text was extracted. This may be a scanned PDF and may need OCR support in the next version.")
            else:
                st.write(f"Extracted {len(pdf_text):,} characters from {len(page_stats)} pages.")

            st.write("Preparing evaluation criteria...")
            criteria = compact_criteria(st.session_state.criteria_df)
            prompt = build_prompt(pdf_text, criteria, context, risk_settings)

            st.write("Calling OpenAI for evidence extraction and rationale...")
            payload = call_openai_review(openai_api_key, model, prompt)
            rows_df = normalize_rows(payload)
            rule_summary = compute_rule_summary(payload, context, risk_settings)

            st.session_state.review_payload = payload
            st.session_state.review_rows = rows_df
            st.session_state.rule_summary = rule_summary
            status.update(label="Review complete", state="complete")
    except Exception as e:
        st.error(f"Review failed: {e}")

if st.session_state.rule_summary is not None:
    rule_summary = st.session_state.rule_summary
    rows_df = st.session_state.review_rows

    st.subheader("Review summary")
    m1, m2, m3, m4, m5, m6 = st.columns(6)
    m1.metric("Recommended risk", rule_summary.get("recommended_risk", "Needs Review"))
    m2.metric("Gate: ACR usable", gate_value(rule_summary.get("acr_usable", "Unknown")))
    m3.metric("Gate: WCAG coverage", gate_value(rule_summary.get("wcag_a_aa_present", "Unknown")))
    m4.metric("Gate: Core issue", gate_value(rule_summary.get("core_issue_found", "Unknown")))
    m5.metric("Gate: Dated plan", gate_value(rule_summary.get("dated_plan_found", "Unknown")))
    m6.metric("Gate: ACR stale", gate_value(rule_summary.get("acr_stale", "Unknown")))

    st.info(rule_summary.get("risk_reason", "No rationale available."))

    with st.expander("Extracted document summary", expanded=True):
        summary_df = pd.DataFrame(
            [
                {"Field": "ID", "Value": context.get("document_id")},
                {"Field": "Company/vendor", "Value": rule_summary.get("company_name")},
                {"Field": "Product identified in ACR", "Value": rule_summary.get("product_name")},
                {"Field": "Version/build", "Value": rule_summary.get("product_version_or_build")},
                {"Field": "Report date", "Value": rule_summary.get("report_date")},
                {"Field": "VPAT version/edition", "Value": rule_summary.get("vpat_version_or_edition")},
                {"Field": "WCAG level", "Value": rule_summary.get("wcag_level")},
                {"Field": "Evaluation methods", "Value": rule_summary.get("evaluation_methods")},
                {"Field": "Staleness rationale", "Value": rule_summary.get("stale_reason")},
            ]
        )
        render_fixed_table(summary_df, {"Field": "Field", "Value": "Value"})

    st.subheader("Evaluation Results")
    st.caption("The Inventory Field column connects each result back to the Inventory-ready summary below.")
    render_fixed_table(
        rows_df,
        {
            "review_area": "Review Area",
            "review_item": "Review Item",
            "result": "Result",
            "what_ai_found": "What AI Found",
            "evidence_location": "Evidence Location",
            "evidence_text": "Evidence Text",
            "rationale": "Rationale",
            "recommended_action": "Recommended Action",
            "inventory_field": "Inventory Field",
        },
    )

    st.subheader("Inventory-ready summary")
    inv_df = inventory_summary(rule_summary, context, rows_df)
    render_fixed_table(inv_df)

    st.subheader("Vendor follow-up questions")
    follow_up_text = questions_to_text(rule_summary.get("vendor_follow_up_questions", []))
    estimated_follow_up_lines = sum(max(1, (len(line) // 140) + 1) for line in follow_up_text.splitlines()) or 1
    follow_up_height = max(140, estimated_follow_up_lines * 28 + 55)
    st.text_area("Copy/paste into vendor email", follow_up_text, height=follow_up_height)

    safe_id = sanitize_filename(context.get("document_id", "acr_review"))
    st.subheader("Downloads")
    d1, d2, d3 = st.columns(3)
    with d1:
        st.download_button(
            "Download full review CSV",
            dataframe_to_csv_bytes(rows_df),
            file_name=f"{safe_id}_evaluation_results.csv",
            mime="text/csv",
        )
    with d2:
        st.download_button(
            "Download inventory CSV",
            dataframe_to_csv_bytes(inv_df),
            file_name=f"{safe_id}_inventory_row.csv",
            mime="text/csv",
        )
    with d3:
        st.download_button(
            "Download follow-up TXT",
            follow_up_text.encode("utf-8"),
            file_name=f"{safe_id}_vendor_follow_up_questions.txt",
            mime="text/plain",
        )

with st.expander("Prototype notes", expanded=False):
    st.markdown(
        """
        - This app reviews the ACR/VPAT document as evidence. It does not prove whether the vendor product itself is accessible.
        - This prototype extracts embedded PDF text with PyMuPDF. OCR for scanned PDFs can be added later.
        - The AI extracts evidence and writes rationale. The High/Medium/Low risk recommendation is calculated with a rule-based protocol.
        - Keep vendor PDFs and API usage policies in mind before using this with sensitive procurement documents.
        """
    )
