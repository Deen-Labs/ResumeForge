"""
ATS Resume Builder — Streamlit + Google Gemini + LaTeX PDF
==========================================================
"""

import json
import os
import re
import subprocess
import tempfile
import textwrap
from datetime import datetime
from pathlib import Path

from google import genai
from google.genai import types
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components

# ──────────────────────────────────────────────────────────────────────────────
# Page config
# ──────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="ResumeLabs — ATS Resume Builder",
    page_icon="",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ──────────────────────────────────────────────────────────────────────────────
# Styles
# ──────────────────────────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    /* ═══════════════════════════════════════════════════════
       PAGE SHELL
       Deep navy canvas. Both panel cards float on top.
       block-container gives 2rem breathing room on all
       sides so nothing ever touches the browser edge.
    ═══════════════════════════════════════════════════════ */
    .stApp,
    [data-testid="stAppViewContainer"],
    [data-testid="stMain"] {
        background: #0b1520 !important;
    }
    header[data-testid="stHeader"] {
        background: #0b1520 !important;
        border-bottom: 1px solid #0f2030 !important;
    }
    .block-container {
        padding: 2rem 2rem 3rem !important;
        max-width: 100% !important;
    }

    /* ═══════════════════════════════════════════════════════
       COLUMN LAYOUT
       1.5rem gutter between the two cards.
       flex-start alignment so the shorter card doesn't
       awkwardly stretch to fill the taller one's height.
    ═══════════════════════════════════════════════════════ */
    [data-testid="stHorizontalBlock"] {
        gap: 1.5rem !important;
        align-items: flex-start !important;
    }

    /* ── LEFT CARD — History panel ──────────────────────────
       Dark frosted-glass surface, fully bordered, rounded.
       max-height + overflow-y: auto keeps it compact and
       scrollable no matter how many entries accumulate.
       The thin 4px scrollbar matches the dark palette.
    ────────────────────────────────────────────────────── */
    [data-testid="stHorizontalBlock"] > [data-testid="column"]:first-child {
        background: #0d1e2c;
        border: 1px solid #1a3040;
        border-radius: 14px;
        max-height: 80vh;
        overflow-y: auto;
        overflow-x: hidden;
        flex-shrink: 0;
    }
    [data-testid="stHorizontalBlock"] > [data-testid="column"]:first-child::-webkit-scrollbar {
        width: 4px;
    }
    [data-testid="stHorizontalBlock"] > [data-testid="column"]:first-child::-webkit-scrollbar-track {
        background: transparent;
    }
    [data-testid="stHorizontalBlock"] > [data-testid="column"]:first-child::-webkit-scrollbar-thumb {
        background: #1e3040;
        border-radius: 4px;
    }
    [data-testid="stHorizontalBlock"] > [data-testid="column"]:first-child > div {
        padding: 1.4rem 1.1rem 1.6rem 1.3rem !important;
    }

    /* ── RIGHT CARD — Builder panel ─────────────────────────
       White elevated surface, light border, generous padding.
       Box-shadow gives subtle depth against the dark canvas.
    ────────────────────────────────────────────────────── */
    [data-testid="stHorizontalBlock"] > [data-testid="column"]:last-child {
        background: #ffffff;
        border: 1px solid #dde5ef;
        border-radius: 14px;
        box-shadow: 0 2px 20px rgba(0, 0, 0, 0.18);
    }
    [data-testid="stHorizontalBlock"] > [data-testid="column"]:last-child > div {
        padding: 2rem 2.4rem 2.5rem !important;
    }

    /* Reset styles for nested columns so they don't inherit history panel or builder card styles */
    [data-testid="column"] [data-testid="column"] {
        background: transparent !important;
        border: none !important;
        max-height: none !important;
        overflow: visible !important;
        box-shadow: none !important;
        padding: 0 !important;
    }

    /* ═══════════════════════════════════════════════════════
       HISTORY PANEL ELEMENTS
    ═══════════════════════════════════════════════════════ */
    .hist-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 1rem;
        padding-bottom: 0.75rem;
        border-bottom: 1px solid #162433;
    }
    .hist-title {
        font-size: 0.64rem;
        font-weight: 700;
        color: #ffffff;
        text-transform: uppercase;
        letter-spacing: 1.8px;
    }
    .hist-count {
        background: #122030;
        color: #4a7a8e;
        font-size: 0.6rem;
        font-weight: 700;
        padding: 2px 7px;
        border-radius: 999px;
    }
    .hist-empty {
        color: #ffffff;
        font-size: 0.75rem;
        line-height: 1.7;
        text-align: center;
        padding: 2rem 0.5rem;
        border: 1px dashed #172535;
        border-radius: 8px;
        margin-top: 0.4rem;
    }
    .hist-card {
        background: #0e2030;
        border: 1px solid #1a3040;
        border-radius: 8px;
        padding: 0.8rem 0.85rem 0.7rem;
        margin-bottom: 0.5rem;
        transition: border-color 0.15s, background 0.15s;
    }
    .hist-card:hover {
        border-color: #2c5364;
        background: #102333;
    }
    .hist-name {
        font-size: 0.8rem;
        font-weight: 600;
        color: #ffffff;
        margin-bottom: 1px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    .hist-date {
        font-size: 0.62rem;
        color: #94a3b8;
        margin-bottom: 6px;
    }
    .hist-scores {
        display: flex;
        align-items: center;
        gap: 5px;
        margin-bottom: 6px;
    }
    .score-before {
        background: #2a1510; color: #b85a40;
        font-size: 0.63rem; font-weight: 700;
        padding: 2px 6px; border-radius: 4px;
    }
    .score-arrow { color: #1e3240; font-size: 0.65rem; }
    .score-after {
        background: #0a2218; color: #30a888;
        font-size: 0.63rem; font-weight: 700;
        padding: 2px 6px; border-radius: 4px;
    }
    .score-label { color: #254050; font-size: 0.6rem; margin-left: 2px; }
    .hist-snippet {
        font-size: 0.67rem;
        color: #e2e8f0;
        line-height: 1.45;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
    }
    .hist-session-note {
        font-size: 0.59rem;
        color: #ffffff;
        text-align: center;
        margin-top: 1rem;
        line-height: 1.6;
        padding-top: 0.6rem;
        border-top: 1px solid #112030;
    }

    /* ═══════════════════════════════════════════════════════
       HERO BANNER (inside right card)
    ═══════════════════════════════════════════════════════ */
    .hero {
        background: linear-gradient(135deg, #0f2027 0%, #1a3545 55%, #2c5364 100%);
        border-radius: 10px;
        padding: 1.8rem 2rem 1.5rem;
        margin-bottom: 1.5rem;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.12);
    }
    .hero-badge {
        display: inline-block;
        background: rgba(255, 255, 255, 0.07);
        color: #7fb8cc;
        font-size: 0.6rem;
        font-weight: 600;
        letter-spacing: 2px;
        text-transform: uppercase;
        padding: 3px 12px;
        border-radius: 999px;
        margin-bottom: 0.75rem;
        border: 1px solid rgba(127, 184, 204, 0.18);
    }
    .hero h1 {
        font-size: 1.6rem;
        font-weight: 700;
        color: #ffffff;
        margin: 0 0 0.45rem;
        letter-spacing: -0.3px;
        line-height: 1.2;
    }
    .hero p {
        color: #90b8c5;
        font-size: 0.84rem;
        margin: 0;
        line-height: 1.7;
        max-width: 520px;
    }
    .hero-steps {
        display: flex;
        gap: 6px;
        flex-wrap: wrap;
        margin-top: 1rem;
    }
    .hero-step {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.08);
        color: #a8ccd8;
        border-radius: 5px;
        padding: 3px 10px;
        font-size: 0.66rem;
        font-weight: 500;
    }

    /* ═══════════════════════════════════════════════════════
       INPUT GUIDANCE BOX
    ═══════════════════════════════════════════════════════ */
    .input-guidance {
        background: #f8fafc;
        border: 1px solid #dde8f0;
        border-left: 3px solid #2c5364;
        border-radius: 6px;
        padding: 0.7rem 1rem 0.65rem;
        margin-top: 0.55rem;
    }
    .input-guidance .title {
        font-size: 0.65rem;
        font-weight: 700;
        color: #334155;
        text-transform: uppercase;
        letter-spacing: 0.9px;
        margin-bottom: 0.25rem;
    }
    .input-guidance .subtitle {
        font-size: 0.75rem;
        color: #64748b;
        margin-bottom: 0.4rem;
        line-height: 1.5;
    }
    .format-tags { display: flex; flex-wrap: wrap; gap: 4px; }
    .format-tag {
        background: #edf3f8;
        color: #2c5364;
        font-size: 0.64rem;
        font-weight: 600;
        padding: 2px 8px;
        border-radius: 4px;
        border: 1px solid #c4d8e4;
    }

    /* ═══════════════════════════════════════════════════════
       BUTTONS
    ═══════════════════════════════════════════════════════ */
    /* Base button transition rules */
    div.stButton > button {
        width: 100%;
        border-radius: 8px;
        transition: all 0.17s ease;
    }

    /* Primary buttons */
    div.stButton > button[data-testid="baseButton-primary"] {
        background: linear-gradient(135deg, #2c5364, #1a3a47);
        color: white;
        border: none;
        padding: 0.62rem 1.5rem;
        font-size: 0.87rem;
        font-weight: 600;
        letter-spacing: 0.1px;
        box-shadow: 0 2px 8px rgba(44, 83, 100, 0.26);
    }
    div.stButton > button[data-testid="baseButton-primary"]:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 14px rgba(44, 83, 100, 0.38);
        background: linear-gradient(135deg, #24465a, #142f3c);
    }
    div.stButton > button[data-testid="baseButton-primary"]:active {
        transform: translateY(0);
    }

    /* Secondary buttons (default) */
    div.stButton > button[data-testid="baseButton-secondary"] {
        background: transparent;
        color: #2c5364;
        border: 1px solid #c4d8e4;
        padding: 0.5rem 1.2rem;
        font-size: 0.82rem;
        font-weight: 500;
        box-shadow: none;
    }
    div.stButton > button[data-testid="baseButton-secondary"]:hover {
        background: #f1f5f9;
        border-color: #2c5364;
        color: #1a3a47;
    }
    div.stButton > button[data-testid="baseButton-secondary"]:active {
        background: #e2e8f0;
    }

    /* Secondary buttons on dark first column (History card) */
    [data-testid="column"]:first-child div.stButton > button[data-testid="baseButton-secondary"] {
        color: #bcd8e8;
        border-color: #254050;
        background: #0e2030;
    }
    [data-testid="column"]:first-child div.stButton > button[data-testid="baseButton-secondary"]:hover {
        background: #152c3e;
        border-color: #3a5a6e;
        color: #ffffff;
    }

    div.stDownloadButton > button {
        width: 100%;
        background: linear-gradient(135deg, #0f7b6c, #12a08e);
        color: #fff;
        border: none;
        border-radius: 8px;
        padding: 0.62rem 1.5rem;
        font-size: 0.87rem;
        font-weight: 700;
        transition: all 0.17s ease;
        box-shadow: 0 2px 8px rgba(15, 123, 108, 0.26);
    }
    div.stDownloadButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 14px rgba(15, 123, 108, 0.38);
    }

    /* ═══════════════════════════════════════════════════════
       TEXTAREA
    ═══════════════════════════════════════════════════════ */
    textarea {
        border-radius: 7px !important;
        border-color: #dde8f0 !important;
        font-family: 'Inter', sans-serif !important;
        font-size: 0.84rem !important;
        line-height: 1.65 !important;
        background: #fafcff !important;
        color: #1e293b !important;
    }
    textarea:focus {
        border-color: #2c5364 !important;
        box-shadow: 0 0 0 3px rgba(44, 83, 100, 0.08) !important;
    }
    .stTextInput input {
        background: #fafcff !important;
        color: #1e293b !important;
        border: 1px solid #dde8f0 !important;
        border-radius: 7px !important;
    }
    .stTextInput input:focus {
        border-color: #2c5364 !important;
        box-shadow: 0 0 0 3px rgba(44, 83, 100, 0.08) !important;
    }

    /* ═══════════════════════════════════════════════════════
       ANALYTICS DASHBOARD
    ═══════════════════════════════════════════════════════ */
    .analytics-header {
        font-size: 0.64rem;
        font-weight: 700;
        color: #ffffff;
        text-transform: uppercase;
        letter-spacing: 1.2px;
        margin-bottom: 0.8rem;
        padding-bottom: 0.4rem;
        border-bottom: 1px solid #1e3040;
    }
    .improvement-item {
        display: flex;
        align-items: flex-start;
        gap: 8px;
        padding: 5px 0;
        border-bottom: 1px solid #162433;
        font-size: 0.78rem;
        color: #ffffff;
        line-height: 1.5;
    }
    .improvement-item:last-child { border-bottom: none; }
    .improvement-dot {
        width: 5px; height: 5px;
        border-radius: 50%;
        background: #0f7b6c;
        margin-top: 7px; flex-shrink: 0;
    }
    .missing-item {
        display: flex;
        align-items: flex-start;
        gap: 8px;
        padding: 4px 0;
        font-size: 0.75rem;
        color: #e2e8f0;
        line-height: 1.5;
    }
    .missing-dot {
        width: 5px; height: 5px;
        border-radius: 50%;
        background: #cbd5e1;
        margin-top: 7px; flex-shrink: 0;
    }

    /* ═══════════════════════════════════════════════════════
       FOOTER & UTILITY LABELS
    ═══════════════════════════════════════════════════════ */
    .footer {
        font-size: 0.69rem;
        color: #94a3b8;
        margin-top: 2rem;
        padding-top: 0.9rem;
        border-top: 1px solid #e8eef5;
        line-height: 1.8;
    }
    .section-label {
        font-size: 0.63rem;
        font-weight: 700;
        color: #ffffff;
        text-transform: uppercase;
        letter-spacing: 1.3px;
        margin: 1.3rem 0 0.65rem;
    }

    /* ═══════════════════════════════════════════════════════
       NAVBAR (Title bar)
    ═══════════════════════════════════════════════════════ */
    .navbar {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0.9rem 1.6rem;
        background: #0d1e2c;
        border: 1px solid #1a3040;
        border-radius: 12px;
        margin-bottom: 1.5rem;
    }
    .nav-brand {
        display: flex;
        align-items: baseline;
        gap: 10px;
    }
    .brand-title {
        font-family: 'Inter', sans-serif;
        font-size: 1.25rem;
        font-weight: 700;
        color: #ffffff;
        letter-spacing: -0.4px;
    }
    .brand-tagline {
        font-size: 0.75rem;
        color: #4a7a8e;
        font-weight: 500;
    }
    .nav-attribution {
        font-size: 0.78rem;
        color: #90b8c5;
        font-weight: 400;
    }
    .nav-attribution a {
        color: #bcd8e8;
        text-decoration: none;
        font-weight: 600;
        transition: color 0.15s ease;
    }
    .nav-attribution a:hover {
        color: #ffffff;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ──────────────────────────────────────────────────────────────────────────────
# API key
# ──────────────────────────────────────────────────────────────────────────────
def _get_api_key() -> str:
    try:
        return st.secrets["GEMINI_API_KEY"]
    except (KeyError, FileNotFoundError):
        key = os.environ.get("GEMINI_API_KEY", "")
        if not key:
            st.error(
                "API key not found. Add `GEMINI_API_KEY` to `.streamlit/secrets.toml` "
                "or set it as an environment variable before running the app."
            )
            st.stop()
        return key


# ──────────────────────────────────────────────────────────────────────────────
# Pydantic Schemas for Structured JSON Output
# ──────────────────────────────────────────────────────────────────────────────
from pydantic import BaseModel, Field
from typing import List, Optional

class SkillCategory(BaseModel):
    category: str = Field(description="Category of skills, e.g., 'Languages', 'Frameworks'.")
    items: List[str] = Field(description="List of skills within this category.")

class ExperienceItem(BaseModel):
    title: str = Field(description="Job title.")
    company: str = Field(description="Company or organization name.")
    location: str = Field(description="City and country/state.")
    start_date: str = Field(description="Start date, format: Mon YYYY.")
    end_date: str = Field(description="End date, format: Mon YYYY or 'Present'.")
    bullets: List[str] = Field(description="List of strong, quantified achievement bullet points starting with an action verb.")

class EducationItem(BaseModel):
    degree: str = Field(description="Name of the degree, e.g., 'B.Sc. Computer Science'.")
    institution: str = Field(description="University or school name.")
    location: str = Field(description="City and country/state.")
    graduation: str = Field(description="Graduation year.")
    notes: Optional[str] = Field(default="", description="GPA, honors, or key achievements.")

class CertificationItem(BaseModel):
    name: str = Field(description="Name of the certification.")
    issuer: str = Field(description="Issuing organization.")
    year: str = Field(description="Year of completion.")

class ProjectItem(BaseModel):
    name: str = Field(description="Project name.")
    description: str = Field(description="One-line description of the project.")
    tech: List[str] = Field(description="Key technologies used.")
    url: Optional[str] = Field(default="", description="Repository or project URL.")

class AnalysisDetails(BaseModel):
    ats_score_before: int = Field(description="ATS score of raw input, from 0 to 100.")
    ats_score_after: int = Field(description="ATS score of revised resume, from 0 to 100.")
    weak_phrases_upgraded: int = Field(description="Count of weak phrases/verbs upgraded.")
    achievements_quantified: int = Field(description="Count of bullet points quantified with metrics.")
    action_verbs_count: int = Field(description="Count of strong action verbs introduced.")
    key_improvements: List[str] = Field(description="List of key improvements made by the AI (max 5 items).")
    missing_info: List[str] = Field(description="Details that were missing from input which would improve ATS score.")

class ResumeSchema(BaseModel):
    name: str = Field(description="Candidate's full name.")
    email: str = Field(description="Professional email address.")
    phone: str = Field(description="Phone number.")
    linkedin: str = Field(description="LinkedIn profile link or username.")
    github: str = Field(description="GitHub profile link or username.")
    location: str = Field(description="Current city and country/state.")
    summary: str = Field(description="2-3 sentence professional summary summarizing experience and key value.")
    skills: List[SkillCategory] = Field(description="Grouped list of technical/professional skills.")
    experience: List[ExperienceItem] = Field(description="List of work experience history.")
    education: List[EducationItem] = Field(description="List of academic history.")
    certifications: List[CertificationItem] = Field(description="List of relevant professional certifications.")
    projects: List[ProjectItem] = Field(description="List of representative engineering or personal projects.")
    analysis: AnalysisDetails = Field(description="ATS score comparison, verb statistics, and textual improvement logs.")


# ──────────────────────────────────────────────────────────────────────────────
# System prompt
# ──────────────────────────────────────────────────────────────────────────────
_SYSTEM_PROMPT = textwrap.dedent("""
    You are a senior technical recruiter and professional resume strategist with 15+ years of
    experience placing engineers, designers, and analysts at Fortune 500 companies and elite startups.

    Your task is to convert ANY form of raw input into a polished, ATS-optimised resume.

    INPUT FORMATS YOU MUST HANDLE:
    - Conversational text: "I've been working at Google for 3 years on the ads backend..."
    - Stream-of-consciousness: "did python stuff, led a team, got a CS degree in 2019"
    - Rough bullet lists: "- React developer  - Built dashboard  - 2 years exp"
    - Old resume copy-paste: messy formatting, inconsistent tense, weak verbs
    - LinkedIn About + Experience sections
    - Mixed formats combining any of the above
    Never refuse to process any of the above. Always extract the most relevant information.

    REWRITING RULES:
    - Replace ALL weak verbs (did, worked on, helped, was responsible for, made, built)
      with powerful action verbs: Architected, Spearheaded, Optimised, Delivered, Scaled,
      Reduced, Increased, Collaborated, Mentored, Automated, Deployed, Designed.
    - Quantify every achievement where the raw text gives any indication of scale or impact.
      Use reasonable professional estimates if exact numbers are implied but not stated.
      Mark estimated figures with "~" so the candidate can confirm them.
    - Use past tense for historical roles, present tense for current role.
    - Each bullet: <= 2 lines, starts with an action verb, no filler phrases.
    - Do NOT invent company names, schools, or certifications.
    - Fix all spelling and grammar errors silently.
    - Group skills by category (Languages, Frameworks, Tools, Cloud, etc.).
    - If a section has no data, use [] for arrays or "" for strings.
""")


def call_gemini(raw_text: str) -> dict:
    models = ["gemini-3.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]
    api_key = _get_api_key()
    
    last_error = None
    for model_name in models:
        try:
            # Set a 60-second (60,000 ms) timeout policy for client requests
            client = genai.Client(
                api_key=api_key,
                http_options=types.HttpOptions(timeout=60000)
            )
            response = client.models.generate_content(
                model=model_name,
                contents=raw_text,
                config=types.GenerateContentConfig(
                    system_instruction=_SYSTEM_PROMPT,
                    temperature=0.3,
                    response_mime_type="application/json",
                    response_schema=ResumeSchema,
                ),
            )
            text = response.text.strip()
            return json.loads(text)
        except Exception as e:
            last_error = e
            st.warning(f"{model_name} failed or timed out: {e}. Trying next available model...")
            
    # If all models in the list fail, report the error and raise the last exception
    st.error("All available Gemini models failed or timed out.")
    raise last_error


# ──────────────────────────────────────────────────────────────────────────────
# LaTeX builder
# ──────────────────────────────────────────────────────────────────────────────
def _escape_latex(s: str) -> str:
    if not s:
        return ""
    latex_escapes = {
        '\\': r'\textbackslash{}',
        '&': r'\&',
        '%': r'\%',
        '$': r'\$',
        '#': r'\#',
        '_': r'\_',
        '{': r'\{',
        '}': r'\}',
        '~': r'\textasciitilde{}',
        '^': r'\textasciicircum{}',
    }
    regex = re.compile('|'.join(re.escape(key) for key in latex_escapes.keys()))
    return regex.sub(lambda match: latex_escapes[match.group(0)], s)


def build_latex(data: dict) -> str:
    def esc(v):
        return _escape_latex(str(v)) if v else ""

    contact_parts = []
    if data.get("email"):
        contact_parts.append(r"\href{mailto:" + esc(data["email"]) + r"}{" + esc(data["email"]) + "}")
    if data.get("phone"):
        contact_parts.append(esc(data["phone"]))
    if data.get("location"):
        contact_parts.append(esc(data["location"]))
    if data.get("linkedin"):
        url = data["linkedin"]
        if not url.startswith("http"): url = "https://" + url
        contact_parts.append(r"\href{" + url + r"}{\faLinkedin\ LinkedIn}")
    if data.get("github"):
        url = data["github"]
        if not url.startswith("http"): url = "https://" + url
        contact_parts.append(r"\href{" + url + r"}{\faGithub\ GitHub}")
    contact_line = r" $\vert$ ".join(contact_parts)

    summary_block = ""
    if data.get("summary"):
        summary_block = r"\section{Professional Summary}" + "\n" + esc(data["summary"]) + "\n"

    skills_rows = ""
    for cat in data.get("skills", []):
        items = ", ".join(esc(i) for i in cat.get("items", []))
        if items:
            skills_rows += f"  \\textbf{{{esc(cat.get('category',''))}:}} & {items} \\\\\n"
    skills_block = ""
    if skills_rows:
        skills_block = (r"\section{Skills}" + "\n"
                        + r"\begin{tabular}{@{}p{1.6in}p{4.5in}@{}}" + "\n"
                        + skills_rows + r"\end{tabular}" + "\n")

    exp_entries = ""
    for job in data.get("experience", []):
        title = esc(job.get("title", ""))
        company = esc(job.get("company", ""))
        loc = esc(job.get("location", ""))
        start = esc(job.get("start_date", ""))
        end = esc(job.get("end_date", ""))
        dates = f"{start} -- {end}" if start else end
        bullets = "\n".join(r"    \item " + esc(b) for b in job.get("bullets", []))
        exp_entries += rf"""
  \resumeSubheading
    {{{title}}}{{{dates}}}
    {{{company}}}{{{loc}}}
  \resumeItemListStart
{bullets}
  \resumeItemListEnd
"""
    exp_block = ""
    if exp_entries:
        exp_block = (r"\section{Experience}" + "\n"
                     + r"\resumeSubHeadingListStart" + "\n"
                     + exp_entries + r"\resumeSubHeadingListEnd" + "\n")

    edu_entries = ""
    for edu in data.get("education", []):
        notes_line = f"    \\item {esc(edu.get('notes',''))}" if edu.get("notes") else ""
        edu_entries += rf"""
  \resumeSubheading
    {{{esc(edu.get('degree',''))}}}{{Graduated: {esc(edu.get('graduation',''))}}}
    {{{esc(edu.get('institution',''))}}}{{{esc(edu.get('location',''))}}}
  \resumeItemListStart
{notes_line}
  \resumeItemListEnd
"""
    edu_block = ""
    if edu_entries:
        edu_block = (r"\section{Education}" + "\n"
                     + r"\resumeSubHeadingListStart" + "\n"
                     + edu_entries + r"\resumeSubHeadingListEnd" + "\n")

    cert_block = ""
    if data.get("certifications"):
        cert_items = "\n".join(
            r"  \item \textbf{" + esc(c.get("name", "")) + r"} --- "
            + esc(c.get("issuer", "")) + r" (" + esc(c.get("year", "")) + ")"
            for c in data["certifications"]
        )
        cert_block = (r"\section{Certifications}" + "\n"
                      + r"\begin{itemize}[leftmargin=0.15in, label={}]" + "\n"
                      + r"  \small" + "\n"
                      + cert_items + "\n" + r"\end{itemize}" + "\n")

    proj_block = ""
    if data.get("projects"):
        proj_entries = ""
        for p in data["projects"]:
            url = p.get("url", "")
            link = ""
            if url:
                if not url.startswith("http"): url = "https://" + url
                link = rf" \href{{{url}}}{{[link]}}"
            tech = ", ".join(esc(t) for t in p.get("tech", []))
            proj_entries += rf"""
  \item
    \textbf{{{esc(p.get('name',''))}}}{link} \\
    {esc(p.get('description',''))} \\
    \textit{{Tech:}} {tech}
  \vspace{{2pt}}
"""
        proj_block = (r"\section{Projects}" + "\n"
                      + r"\begin{itemize}[leftmargin=0.15in, label={}]" + "\n"
                      + r"  \small" + "\n"
                      + proj_entries + "\n" + r"\end{itemize}" + "\n")

    return rf"""
%!TEX program = pdflatex
\documentclass[letterpaper,10pt]{{article}}

\usepackage[empty]{{fullpage}}
\usepackage{{titlesec}}
\usepackage{{marvosym}}
\usepackage[usenames,dvipsnames]{{color}}
\usepackage{{verbatim}}
\usepackage{{enumitem}}
\usepackage[hidelinks]{{hyperref}}
\usepackage{{fancyhdr}}
\usepackage[english]{{babel}}
\usepackage{{tabularx}}
\usepackage{{fontawesome5}}
\usepackage{{multicol}}
\setlength{{\multicolsep}}{{-3.0pt}}
\setlength{{\columnsep}}{{-1pt}}
\input{{glyphtounicode}}

\pagestyle{{fancy}}
\fancyhf{{}}
\fancyfoot{{}}
\renewcommand{{\headrulewidth}}{{0pt}}
\renewcommand{{\footrulewidth}}{{0pt}}
\addtolength{{\oddsidemargin}}{{-0.6in}}
\addtolength{{\evensidemargin}}{{-0.5in}}
\addtolength{{\textwidth}}{{1.19in}}
\addtolength{{\topmargin}}{{-.7in}}
\addtolength{{\textheight}}{{1.4in}}
\urlstyle{{same}}
\raggedbottom
\raggedright
\setlength{{\tabcolsep}}{{0in}}
\pdfgentounicode=1

\titleformat{{\section}}{{\vspace{{-4pt}}\scshape\raggedright\large\bfseries}}{{}}{{0em}}{{}}[\color{{black}}\titlerule\vspace{{-5pt}}]

\newcommand{{\resumeSubheading}}[4]{{
  \vspace{{-2pt}}\item
    \begin{{tabular*}}{{1.0\textwidth}}[t]{{l@{{\extracolsep{{\fill}}}}r}}
      \textbf{{#1}} & \textbf{{\small #2}} \\
      \textit{{\small#3}} & \textit{{\small #4}} \\
    \end{{tabular*}}\vspace{{-7pt}}
}}
\newcommand{{\resumeItemListStart}}{{\begin{{itemize}}}}
\newcommand{{\resumeItemListEnd}}{{\end{{itemize}}\vspace{{-5pt}}}}
\newcommand{{\resumeSubHeadingListStart}}{{\begin{{itemize}}[leftmargin=0.0in, label={{}}]}}
\newcommand{{\resumeSubHeadingListEnd}}{{\end{{itemize}}}}

\begin{{document}}

\begin{{center}}
  {{\Huge \scshape \textbf{{{esc(data.get("name", "Your Name"))}}}}} \\[4pt]
  \small
  {contact_line}
\end{{center}}

{summary_block}
{skills_block}
{exp_block}
{edu_block}
{cert_block}
{proj_block}

\end{{document}}
"""


# ──────────────────────────────────────────────────────────────────────────────
# PDF compilation
# ──────────────────────────────────────────────────────────────────────────────
def compile_latex_to_pdf(latex_str: str) -> bytes:
    with tempfile.TemporaryDirectory() as tmpdir:
        tex_path = Path(tmpdir) / "resume.tex"
        pdf_path = Path(tmpdir) / "resume.pdf"
        tex_path.write_text(latex_str, encoding="utf-8")
        cmd = ["pdflatex", "-interaction=nonstopmode", "-output-directory", tmpdir, str(tex_path)]
        for pass_num in range(2):
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=tmpdir)
            if result.returncode != 0 and pass_num == 1:
                log = result.stdout + "\n" + result.stderr
                st.error("PDF compilation failed. Review the pdflatex log below.")
                with st.expander("pdflatex log"):
                    st.code(log, language="text")
                st.stop()
        return pdf_path.read_bytes()


# ──────────────────────────────────────────────────────────────────────────────
# Analytics charts
# ──────────────────────────────────────────────────────────────────────────────
def render_analytics(data: dict, raw_text: str):
    analysis     = data.get("analysis", {})
    score_before = analysis.get("ats_score_before", 0)
    score_after  = analysis.get("ats_score_after",  0)

    st.markdown('<div class="analytics-header">Resume Analysis Report</div>', unsafe_allow_html=True)

    col_a, col_b = st.columns(2)

    def _gauge(title, value, color):
        fig = go.Figure(go.Indicator(
            mode="gauge+number", value=value,
            title={"text": title, "font": {"size": 12, "family": "Inter", "color": "#ffffff"}},
            number={"suffix": "/100", "font": {"size": 20, "family": "Inter", "color": "#ffffff"}},
            gauge={
                "axis": {"range": [0, 100], "tickfont": {"size": 9, "color": "#ffffff"}, "tickcolor": "#ffffff"},
                "bar": {"color": color, "thickness": 0.25},
                "bgcolor": "#0d1e2c", "bordercolor": "#1e3040",
                "steps": [
                    {"range": [0,  40], "color": "#2a1510"},
                    {"range": [40, 70], "color": "#282510"},
                    {"range": [70, 100], "color": "#0a2218"},
                ],
                "threshold": {"line": {"color": color, "width": 2}, "thickness": 0.7, "value": value},
            },
        ))
        fig.update_layout(
            height=190, margin=dict(t=36, b=8, l=18, r=18),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font={"family": "Inter"},
        )
        return fig

    with col_a:
        st.plotly_chart(_gauge("ATS Score — Before", score_before, "#c0614a"),
                        use_container_width=True, config={"displayModeBar": False})
    with col_b:
        st.plotly_chart(_gauge("ATS Score — After", score_after, "#0f7b6c"),
                        use_container_width=True, config={"displayModeBar": False})

    raw_words    = len(raw_text.split())
    final_words  = sum(
        len(b.split()) for job in data.get("experience", []) for b in job.get("bullets", [])
    ) + len(data.get("summary", "").split())
    total_skills = sum(len(s.get("items", [])) for s in data.get("skills", []))

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("ATS Score Gain", f"+{score_after - score_before}", f"{score_before} → {score_after}")
    with c2:
        st.metric("Phrases Upgraded", analysis.get("weak_phrases_upgraded", 0), "weak verbs replaced")
    with c3:
        st.metric("Achievements Quantified", analysis.get("achievements_quantified", 0), "metrics added")
    with c4:
        st.metric("Skills Identified", total_skills, f"across {len(data.get('skills', []))} categories")

    st.markdown("<br>", unsafe_allow_html=True)

    col_chart, col_list = st.columns([1, 1], gap="large")

    with col_chart:
        sections, counts = [], []
        exp_bullets = sum(len(j.get("bullets", [])) for j in data.get("experience", []))
        if exp_bullets: sections.append("Experience bullets"); counts.append(exp_bullets)
        if total_skills: sections.append("Skills"); counts.append(total_skills)
        if data.get("education"):    sections.append("Education");     counts.append(len(data["education"]))
        if data.get("certifications"): sections.append("Certifications"); counts.append(len(data["certifications"]))
        if data.get("projects"):     sections.append("Projects");      counts.append(len(data["projects"]))
        if data.get("summary"):      sections.append("Summary");       counts.append(1)

        if sections:
            palette = ["#2c5364", "#0f7b6c", "#3b82f6", "#8b5cf6", "#f59e0b", "#64748b"]
            fig_pie = go.Figure(go.Pie(
                labels=sections, values=counts, hole=0.52,
                marker=dict(colors=palette[:len(sections)], line=dict(color="#fff", width=2)),
                textfont=dict(size=10, family="Inter"),
                hovertemplate="%{label}: %{value}<extra></extra>",
            ))
            fig_pie.update_layout(
                title=dict(text="Resume Composition", font=dict(size=11, family="Inter", color="#ffffff"), x=0.5),
                height=260, margin=dict(t=36, b=8, l=8, r=8),
                paper_bgcolor="rgba(0,0,0,0)", showlegend=True,
                legend=dict(font=dict(size=9, family="Inter", color="#ffffff"), orientation="v"),
            )
            st.plotly_chart(fig_pie, use_container_width=True, config={"displayModeBar": False})

    with col_list:
        improvements = analysis.get("key_improvements", [])
        missing      = analysis.get("missing_info", [])
        if improvements:
            st.markdown("**Key improvements made**")
            for item in improvements:
                st.markdown(
                    f'<div class="improvement-item"><div class="improvement-dot"></div>{item}</div>',
                    unsafe_allow_html=True,
                )
        if missing:
            st.markdown("<br>**Information that could not be filled**", unsafe_allow_html=True)
            for item in missing:
                st.markdown(
                    f'<div class="missing-item"><div class="missing-dot"></div>{item}</div>',
                    unsafe_allow_html=True,
                )

    fig_bar = go.Figure()
    fig_bar.add_trace(go.Bar(name="Original input", x=["Word Count"], y=[raw_words],
                             marker_color="#c0614a", width=0.3,
                             hovertemplate="Original: %{y} words<extra></extra>"))
    fig_bar.add_trace(go.Bar(name="Optimised resume", x=["Word Count"], y=[final_words],
                             marker_color="#0f7b6c", width=0.3,
                             hovertemplate="Optimised: %{y} words<extra></extra>"))
    fig_bar.update_layout(
        title=dict(text="Input Length vs. Resume Content",
                   font=dict(size=11, family="Inter", color="#ffffff"), x=0),
        barmode="group", height=190, margin=dict(t=36, b=28, l=38, r=16),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(font=dict(size=9, family="Inter", color="#ffffff"), orientation="h",
                    yanchor="bottom", y=1.02, xanchor="right", x=1),
        yaxis=dict(gridcolor="#1e3040", title="Words", title_font=dict(size=9, color="#ffffff"), tickfont=dict(color="#ffffff")),
        xaxis=dict(showticklabels=False, tickfont=dict(color="#ffffff")),
        font=dict(family="Inter", color="#ffffff"),
    )
    st.plotly_chart(fig_bar, use_container_width=True, config={"displayModeBar": False})


# ──────────────────────────────────────────────────────────────────────────────
# Session state
# ──────────────────────────────────────────────────────────────────────────────
for key, default in [
    ("resume_data", None),
    ("pdf_bytes",   None),
    ("raw_input",   ""),
    ("history",     []),
    ("load_idx",    None),
]:
    if key not in st.session_state:
        st.session_state[key] = default


# ──────────────────────────────────────────────────────────────────────────────
# Title bar / Navbar
# ──────────────────────────────────────────────────────────────────────────────
st.markdown(
    """
    <div class="navbar">
      <div class="nav-brand">
        <span class="brand-title">ResumeLabs</span>
        <span class="brand-tagline">ATS Resume Builder</span>
      </div>
      <div class="nav-attribution">
        by <a href="https://deenlabs.tech" target="_blank">deenlabs.tech</a>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ──────────────────────────────────────────────────────────────────────────────
# Two-column layout
# ──────────────────────────────────────────────────────────────────────────────
left_col, right_col = st.columns([1, 3], gap="small")


# ══════════════════════════════════════════════════════════════════════════════
# LEFT COLUMN — History panel
# ══════════════════════════════════════════════════════════════════════════════
with left_col:
    history = st.session_state.history
    n = len(history)

    st.markdown(
        f'<div class="hist-header">'
        f'<span class="hist-title">Session History</span>'
        f'<span class="hist-count">{n}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    if n == 0:
        st.markdown(
            '<div class="hist-empty">'
            'Generated resumes will appear here.<br><br>'
            'History lives in this browser tab only'
            '</div>',
            unsafe_allow_html=True,
        )
    else:
        for i, entry in enumerate(reversed(history)):
            real_idx = n - 1 - i
            snippet = entry.get("snippet", "")[:90]
            st.markdown(
                f'<div class="hist-card">'
                f'  <div class="hist-name">{entry["name"]}</div>'
                f'  <div class="hist-date">{entry["timestamp"]}</div>'
                f'  <div class="hist-scores">'
                f'    <span class="score-before">{entry["ats_before"]}</span>'
                f'    <span class="score-arrow">&#8594;</span>'
                f'    <span class="score-after">{entry["ats_after"]}</span>'
                f'    <span class="score-label">ATS</span>'
                f'  </div>'
                f'  <div class="hist-snippet">{snippet}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
            if st.button("Load this entry", key=f"load_{real_idx}_{entry['timestamp']}"):
                st.session_state.raw_input = entry["raw_input"]
                st.session_state.resume_data = entry.get("resume_data")
                st.session_state.pdf_bytes = entry.get("pdf_bytes")
                st.rerun()

        if st.button("Clear history", key="clear_history"):
            st.session_state.history = []
            st.rerun()

    st.markdown(
        '<div class="hist-session-note">'
        'History lives in this browser tab only.<br>'
        'Zero data stored on any server.'
        '</div>',
        unsafe_allow_html=True,
    )


# ══════════════════════════════════════════════════════════════════════════════
# RIGHT COLUMN — Builder
# ══════════════════════════════════════════════════════════════════════════════
with right_col:

    # ── Hero ──────────────────────────────────────────────────────────────────
    st.markdown(
        """
        <div class="hero">
          <div class="hero-badge">ATS-Optimised &nbsp;&middot;&nbsp; Powered by Gemini &nbsp;&middot;&nbsp; Free</div>
          <h1>ResumeLabs</h1>
          <p>Describe your background in any format — rough notes, a conversational summary,
          or an old resume draft. Gemini restructures and optimises it into a clean,
          recruiter-ready PDF.</p>
          <div class="hero-steps">
            <span class="hero-step">1. Describe your experience</span>
            <span class="hero-step">2. Gemini rewrites &amp; scores</span>
            <span class="hero-step">3. PDF compiles via LaTeX</span>
            <span class="hero-step">4. Download instantly</span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Fading placeholder animation ──────────────────────────────────────
    # Runs in a 1px iframe (height=0 is suppressed by browsers).
    # The script injects a positioned overlay div onto the parent page's
    # textarea, then fades it between two phrases using CSS transitions.
    # Idempotent: repeated Streamlit reruns won't stack multiple overlays.
    components.html(
        """
        <style> body { margin:0; overflow:hidden; } </style>
        <script>
        (function () {
            var PHRASES = [
                "Paste your resume, describe your background, or write however feels natural \u2014 we\u2019ll handle the rest.",
                "Switching careers? Tell us where you\u2019ve been and where you want to go. We\u2019ll build the bridge."
            ];
            var FADE_MS  = 600;   /* fade-out + fade-in duration each */
            var HOLD_MS  = 3400;  /* time each phrase stays visible */
            var pIdx     = 0;
            var ta       = null;
            var overlay  = null;
            var doc      = null;
            var running  = false;

            function findTA() {
                try {
                    doc = window.parent.document;
                    var all = doc.querySelectorAll('textarea');
                    for (var i = 0; i < all.length; i++) {
                        if (all[i].getAttribute('aria-label') === 'resume_input') return all[i];
                    }
                    return all[0] || null;
                } catch(e) { return null; }
            }

            function buildOverlay() {
                /* Idempotent — only inject once per page load */
                if (doc.getElementById('ats-ph-overlay')) {
                    overlay = doc.getElementById('ats-ph-overlay');
                    return;
                }

                overlay = doc.createElement('div');
                overlay.id = 'ats-ph-overlay';

                /* Match Streamlit textarea inner padding exactly */
                overlay.style.cssText = [
                    'position:absolute',
                    'top:10px',
                    'left:14px',
                    'right:14px',
                    'pointer-events:none',
                    'font-family:Inter,ui-sans-serif,sans-serif',
                    'font-size:0.84rem',
                    'color:#94a3b8',
                    'line-height:1.65',
                    'opacity:1',
                    'transition:opacity ' + FADE_MS + 'ms ease',
                    'z-index:9',
                    'user-select:none',
                    '-webkit-user-select:none'
                ].join(';');

                overlay.textContent = PHRASES[0];

                /* The textarea is inside several wrapper divs; we need a
                   relatively-positioned ancestor to anchor our overlay */
                var wrapper = ta.closest('.stTextArea') || ta.parentElement;
                while (wrapper && getComputedStyle(wrapper).position === 'static') {
                    wrapper = wrapper.parentElement;
                    if (!wrapper || wrapper === doc.body) break;
                }
                /* If nothing is positioned, make the direct parent relative */
                if (!wrapper || wrapper === doc.body) {
                    wrapper = ta.parentElement;
                    wrapper.style.position = 'relative';
                }
                wrapper.appendChild(overlay);
            }

            function isActive() {
                return doc && ta && doc.activeElement === ta;
            }

            function showOverlay() {
                if (!overlay) return;
                overlay.style.opacity = (ta.value || isActive()) ? '0' : '1';
            }

            function fadeToNext() {
                if (!overlay || !ta) return;

                /* Fade out */
                overlay.style.opacity = '0';

                setTimeout(function() {
                    pIdx = (pIdx + 1) % PHRASES.length;
                    overlay.textContent = PHRASES[pIdx];

                    /* Fade in only when the field is empty and unfocused */
                    if (!ta.value && !isActive()) {
                        overlay.style.opacity = '1';
                    }

                    setTimeout(fadeToNext, HOLD_MS);
                }, FADE_MS);
            }

            function init() {
                ta = findTA();
                if (!ta) { setTimeout(init, 100); return; }

                /* Clear the native placeholder so it doesn't show through */
                ta.setAttribute('placeholder', '');

                buildOverlay();
                showOverlay();

                /* React to user interaction */
                ta.addEventListener('focus', showOverlay);
                ta.addEventListener('blur',  showOverlay);
                ta.addEventListener('input', showOverlay);

                if (!running) {
                    running = true;
                    setTimeout(fadeToNext, HOLD_MS);
                }
            }

            setTimeout(init, 50);
        })();
        </script>
        """,
        height=1,
    )


    # ── Textarea and Sample Loader ──────────────────────────────────────────
    col_lbl, col_smp = st.columns([2, 1])
    with col_lbl:
        st.markdown('<div style="font-size:0.85rem; font-weight:600; color:#334155; margin-top: 6px;">Describe your background</div>', unsafe_allow_html=True)
    with col_smp:
        if st.button("Load sample draft", key="try_sample_btn"):
            st.session_state.raw_input = (
                "Hi, I'm Alex. I've been working as a junior python dev at Acme Corp since Jan 2024. "
                "Mainly I did bug fixing on their core product. I also helped rewrite our legacy codebase, "
                "which was responsible for slow response times. It went down from 5 seconds to like 0.8 seconds. "
                "Also I led a couple of sprints when our senior PM was away. I know Python, JS, React, Django, SQL. "
                "Before that I was a freelancer and built some websites for local shops using React. "
                "I graduated from state university in 2023 with a GPA of 3.4."
            )
            st.rerun()

    raw_text = st.text_area(
        label="resume_input",
        label_visibility="collapsed",
        key="raw_input",
        placeholder="",
        height=140,
    )

    # ── Guidance box ───────────────────────────────────────────────────────
    st.markdown(
        """
        <div class="input-guidance">
          <div class="title">Accepted formats</div>
          <div class="subtitle">
            You do not need a polished resume. Write in any style and the AI will
            extract, rewrite, and structure everything into a clean PDF.
          </div>
          <div class="format-tags">
            <span class="format-tag">Old resume text</span>
            <span class="format-tag">LinkedIn About section</span>
            <span class="format-tag">Rough bullet points</span>
            <span class="format-tag">Conversational description</span>
            <span class="format-tag">Career transition notes</span>
            <span class="format-tag">Mixed formats</span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("<br>", unsafe_allow_html=True)
    generate_btn = st.button("Generate ATS Resume", type="primary", use_container_width=True)

    # ── Pipeline ───────────────────────────────────────────────────────────
    if generate_btn:
        if not raw_text.strip():
            st.warning("The input field is empty. Please describe your experience before generating.")
        else:
            with st.status("Processing your resume...", expanded=True) as status:
                st.write("Sending content to Gemini for analysis and rewriting...")
                try:
                    resume_data = call_gemini(raw_text)
                    st.session_state.resume_data = resume_data
                    st.write("Structured data received. Building LaTeX template...")
                except json.JSONDecodeError as e:
                    st.error(f"Could not parse the AI response as structured data: {e}")
                    st.stop()
                except Exception as e:
                    st.error(f"Gemini API error: {e}")
                    st.stop()

                try:
                    latex_str = build_latex(resume_data)
                    st.write("Compiling PDF...")
                    pdf_bytes = compile_latex_to_pdf(latex_str)
                    st.session_state.pdf_bytes = pdf_bytes
                    st.write("PDF compiled successfully.")
                except FileNotFoundError:
                    st.error(
                        "pdflatex was not found. On Streamlit Cloud, ensure packages.txt includes "
                        "the TeX Live packages. Locally, install TeX Live and add pdflatex to PATH."
                    )
                    st.stop()
                except Exception as e:
                    st.error(f"PDF compilation error: {e}")
                    st.stop()

                # Append to session history
                analysis = resume_data.get("analysis", {})
                st.session_state.history.append({
                    "timestamp":    datetime.now().strftime("%d %b %Y, %H:%M"),
                    "name":         resume_data.get("name", "Unknown"),
                    "ats_before":   analysis.get("ats_score_before", 0),
                    "ats_after":    analysis.get("ats_score_after",  0),
                    "raw_input":    raw_text,
                    "snippet":      raw_text[:120].replace("\n", " "),
                    "resume_data":  resume_data,
                    "pdf_bytes":    pdf_bytes,
                })

                status.update(label="Resume generated.", state="complete", expanded=False)

    # ── Results ────────────────────────────────────────────────────────────
    if st.session_state.resume_data and st.session_state.pdf_bytes:
        data      = st.session_state.resume_data
        pdf_bytes = st.session_state.pdf_bytes
        raw_input = st.session_state.raw_input

        name = data.get("name", "your resume")
        st.success(f"Your resume for **{name}** is ready. Review, edit, and download it below.")

        # Split into side-by-side columns: Editor on the left, PDF Preview on the right
        col_editor, col_preview = st.columns([1, 1], gap="medium")

        with col_preview:
            st.markdown('<div style="font-size:0.9rem; font-weight:700; color:#334155; margin-bottom:12px;">Live PDF Preview</div>', unsafe_allow_html=True)
            import base64
            try:
                b64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
                
                pdf_viewer_html = f"""
                <style>
                    html, body {{
                        margin: 0;
                        padding: 0;
                        height: 100%;
                        background: #f1f5f9;
                        overflow: hidden;
                    }}
                    #pdf-container {{
                        background: #f1f5f9;
                        padding: 16px;
                        display: flex;
                        flex-direction: column;
                        gap: 16px;
                        align-items: center;
                        overflow-y: auto;
                        height: 100%;
                        box-sizing: border-box;
                    }}
                    #loading {{
                        color: #64748b;
                        font-family: 'Inter', sans-serif;
                        font-size: 14px;
                        margin-top: 50px;
                        text-align: center;
                    }}
                    canvas {{
                        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                        border-radius: 4px;
                        max-width: 100%;
                        height: auto;
                        background: #ffffff;
                        display: block;
                    }}
                </style>
                <div id="pdf-container">
                    <div id="loading">Loading resume preview...</div>
                </div>
                <script type="module">
                    import * as pdfjsLib from 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/4.0.379/pdf.min.mjs';
                    pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/4.0.379/pdf.worker.min.mjs';

                    function base64ToUint8Array(base64) {{
                        const raw = atob(base64);
                        const uint8Array = new Uint8Array(raw.length);
                        for (let i = 0; i < raw.length; i++) {{
                            uint8Array[i] = raw.charCodeAt(i);
                        }}
                        return uint8Array;
                    }}

                    const base64Data = "{b64_pdf}";
                    const pdfData = base64ToUint8Array(base64Data);

                    pdfjsLib.getDocument({{ data: pdfData }}).promise.then(async (pdf) => {{
                        const container = document.getElementById('pdf-container');
                        const loading = document.getElementById('loading');
                        if (loading) loading.remove();

                        for (let pageNum = 1; pageNum <= pdf.numPages; pageNum++) {{
                            const page = await pdf.getPage(pageNum);
                            const scale = 1.35;
                            const viewport = page.getViewport({{ scale }});
                            
                            const canvas = document.createElement('canvas');
                            const context = canvas.getContext('2d');
                            canvas.height = viewport.height;
                            canvas.width = viewport.width;
                            
                            container.appendChild(canvas);

                            await page.render({{
                                canvasContext: context,
                                viewport: viewport
                            }}).promise;
                        }}
                    }}).catch(err => {{
                        const loading = document.getElementById('loading');
                        if (loading) {{
                            loading.textContent = 'Error loading preview: ' + err.message;
                            loading.style.color = '#ef4444';
                        }}
                    }});
                </script>
                """
                components.html(pdf_viewer_html, height=700)
            except Exception as e:
                st.error(f"Could not render PDF preview: {e}")

            st.markdown("<br>", unsafe_allow_html=True)
            candidate_name = name.replace(" ", "_")
            st.download_button(
                label="Download Resume (PDF)",
                data=pdf_bytes,
                file_name=f"{candidate_name}_ATS_Resume.pdf",
                mime="application/pdf",
                use_container_width=True,
            )

        with col_editor:
            st.markdown('<div style="font-size:0.9rem; font-weight:700; color:#334155; margin-bottom:12px;">Interactive Editor</div>', unsafe_allow_html=True)
            
            with st.form("resume_editor_form"):
                tab_contact, tab_exp, tab_skills, tab_edu_proj = st.tabs([
                    "Contact & Info", "Experience", "Skills & Certs", "Projects & Education"
                ])
                
                with tab_contact:
                    edit_name = st.text_input("Full Name", value=data.get("name", ""))
                    edit_email = st.text_input("Email", value=data.get("email", ""))
                    edit_phone = st.text_input("Phone", value=data.get("phone", ""))
                    edit_loc = st.text_input("Location", value=data.get("location", ""))
                    edit_link = st.text_input("LinkedIn", value=data.get("linkedin", ""))
                    edit_git = st.text_input("GitHub", value=data.get("github", ""))
                    edit_sum = st.text_area("Summary", value=data.get("summary", ""), height=120)

                with tab_exp:
                    updated_exp = []
                    for i, job in enumerate(data.get("experience", [])):
                        st.markdown(f"**Role {i+1}**")
                        j_title = st.text_input(f"Job Title #{i+1}", value=job.get("title", ""), key=f"job_title_{i}")
                        j_comp = st.text_input(f"Company #{i+1}", value=job.get("company", ""), key=f"job_company_{i}")
                        j_loc = st.text_input(f"Location #{i+1}", value=job.get("location", ""), key=f"job_location_{i}")
                        col_d1, col_d2 = st.columns(2)
                        with col_d1:
                            j_start = st.text_input(f"Start Date #{i+1}", value=job.get("start_date", ""), key=f"job_start_{i}")
                        with col_d2:
                            j_end = st.text_input(f"End Date #{i+1}", value=job.get("end_date", ""), key=f"job_end_{i}")
                        
                        j_bullets = st.text_area(
                            f"Bullets (one per line) #{i+1}",
                            value="\n".join(job.get("bullets", [])),
                            height=140,
                            key=f"job_bullets_{i}",
                            help="Each line will compile to a LaTeX list item bullet."
                        )
                        
                        bullets_list = [b.strip() for b in j_bullets.split("\n") if b.strip()]
                        updated_exp.append({
                            "title": j_title,
                            "company": j_comp,
                            "location": j_loc,
                            "start_date": j_start,
                            "end_date": j_end,
                            "bullets": bullets_list
                        })

                with tab_skills:
                    updated_skills = []
                    for i, cat in enumerate(data.get("skills", [])):
                        st.markdown(f"**Skill Category {i+1}**")
                        c_name = st.text_input(f"Category Name #{i+1}", value=cat.get("category", ""), key=f"cat_name_{i}")
                        c_items = st.text_input(
                            f"Items (comma-separated) #{i+1}",
                            value=", ".join(cat.get("items", [])),
                            key=f"cat_items_{i}"
                        )
                        items_list = [item.strip() for item in c_items.split(",") if item.strip()]
                        updated_skills.append({
                            "category": c_name,
                            "items": items_list
                        })
                    
                    st.markdown("---")
                    updated_certs = []
                    for i, cert in enumerate(data.get("certifications", [])):
                        st.markdown(f"**Certification {i+1}**")
                        c_title = st.text_input(f"Name #{i+1}", value=cert.get("name", ""), key=f"cert_name_{i}")
                        c_issuer = st.text_input(f"Issuer #{i+1}", value=cert.get("issuer", ""), key=f"cert_issuer_{i}")
                        c_year = st.text_input(f"Year #{i+1}", value=cert.get("year", ""), key=f"cert_year_{i}")
                        updated_certs.append({
                            "name": c_title,
                            "issuer": c_issuer,
                            "year": c_year
                        })

                with tab_edu_proj:
                    updated_edu = []
                    for i, edu in enumerate(data.get("education", [])):
                        st.markdown(f"**Degree {i+1}**")
                        e_deg = st.text_input(f"Degree #{i+1}", value=edu.get("degree", ""), key=f"edu_degree_{i}")
                        e_inst = st.text_input(f"Institution #{i+1}", value=edu.get("institution", ""), key=f"edu_inst_{i}")
                        e_loc = st.text_input(f"Location #{i+1}", value=edu.get("location", ""), key=f"edu_location_{i}")
                        e_grad = st.text_input(f"Graduation Year #{i+1}", value=edu.get("graduation", ""), key=f"edu_grad_{i}")
                        e_notes = st.text_input(f"Notes/GPA #{i+1}", value=edu.get("notes", ""), key=f"edu_notes_{i}")
                        updated_edu.append({
                            "degree": e_deg,
                            "institution": e_inst,
                            "location": e_loc,
                            "graduation": e_grad,
                            "notes": e_notes
                        })
                    
                    st.markdown("---")
                    updated_proj = []
                    for i, proj in enumerate(data.get("projects", [])):
                        st.markdown(f"**Project {i+1}**")
                        p_name = st.text_input(f"Project Name #{i+1}", value=proj.get("name", ""), key=f"proj_name_{i}")
                        p_desc = st.text_input(f"Description #{i+1}", value=proj.get("description", ""), key=f"proj_desc_{i}")
                        p_tech = st.text_input(
                            f"Tech (comma-separated) #{i+1}",
                            value=", ".join(proj.get("tech", [])),
                            key=f"proj_tech_{i}"
                        )
                        p_url = st.text_input(f"URL #{i+1}", value=proj.get("url", ""), key=f"proj_url_{i}")
                        tech_list = [t.strip() for t in p_tech.split(",") if t.strip()]
                        updated_proj.append({
                            "name": p_name,
                            "description": p_desc,
                            "tech": tech_list,
                            "url": p_url
                        })

                submit_edit = st.form_submit_button("Apply Changes & Recompile PDF", type="primary", use_container_width=True)
                
                if submit_edit:
                    updated_data = {
                        "name": edit_name,
                        "email": edit_email,
                        "phone": edit_phone,
                        "location": edit_loc,
                        "linkedin": edit_link,
                        "github": edit_git,
                        "summary": edit_sum,
                        "skills": updated_skills,
                        "experience": updated_exp,
                        "education": updated_edu,
                        "certifications": updated_certs,
                        "projects": updated_proj,
                        "analysis": data.get("analysis", {
                            "ats_score_before": 0, "ats_score_after": 0,
                            "weak_phrases_upgraded": 0, "achievements_quantified": 0,
                            "action_verbs_count": 0, "key_improvements": [], "missing_info": []
                        })
                    }
                    
                    try:
                        latex_str = build_latex(updated_data)
                        new_pdf_bytes = compile_latex_to_pdf(latex_str)
                        
                        st.session_state.resume_data = updated_data
                        st.session_state.pdf_bytes = new_pdf_bytes
                        
                        if st.session_state.history:
                            st.session_state.history[-1]["name"] = edit_name
                            st.session_state.history[-1]["resume_data"] = updated_data
                            st.session_state.history[-1]["pdf_bytes"] = new_pdf_bytes
                        
                        st.rerun()
                    except Exception as ex:
                        st.error(f"Recompilation error: {ex}")

        st.markdown("<br>", unsafe_allow_html=True)
        st.divider()
        st.markdown('<div class="section-label">Analysis</div>', unsafe_allow_html=True)
        render_analytics(data, raw_input)

        st.divider()
        with st.expander("View extracted resume data (JSON)", expanded=False):
            st.json(data)

    # ── Footer ─────────────────────────────────────────────────────────────
    st.markdown(
        """
        <div class="footer">
            ResumeLabs by <a href="https://deenlabs.tech" target="_blank" style="color: #2c5364; font-weight: 600; text-decoration: none;">deenlabs.tech</a> &nbsp;&middot;&nbsp; Powered by Google Gemini &amp; LaTeX<br>
            No resume data is stored or logged &nbsp;&middot;&nbsp;
            History is browser-session only &nbsp;&middot;&nbsp; Free to use
        </div>
        """,
        unsafe_allow_html=True,
    )
