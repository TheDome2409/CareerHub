from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(
        0,
        str(SRC),
    )

import streamlit as st

from jobagent.ui.application_tab import render_application_tab
from jobagent.ui.branding import APP_NAME, logo_data_uri
from jobagent.ui.company_tab import render_company_tab
from jobagent.ui.jobs_tab import render_jobs_tab
from jobagent.ui.profile_tab import render_profile_tab


st.set_page_config(
    page_title=APP_NAME,
    page_icon=logo_data_uri(),
    layout="wide",
)

st.markdown(
    f"""
    <div style="display:flex;align-items:center;gap:0.75rem;margin-bottom:1rem;">
        <img src="{logo_data_uri()}" alt="{APP_NAME} Logo" width="48" height="48">
        <h1 style="margin:0;font-size:2.4rem;line-height:1;">{APP_NAME}</h1>
    </div>
    """,
    unsafe_allow_html=True,
)

mode = st.sidebar.radio(
    "Ausgabemodus",
    ["Mensch", "Asgard"],
)

st.sidebar.header("Filter")

min_score = st.sidebar.slider(
    "Mindestscore",
    min_value=0,
    max_value=100,
    value=20,
)

max_results = st.sidebar.slider(
    "Maximale Treffer",
    min_value=5,
    max_value=100,
    value=25,
)

available_tags = [
    "digitalization",
    "leadership",
    "project_responsibility",
    "change_management",
    "automation",
    "cloud",
    "security",
    "consulting",
    "architecture",
    "platform",
    "data",
    "social_engagement",
]

selected_tags = st.sidebar.multiselect(
    "Tags",
    available_tags,
)

tab_profile, tab_jobs, tab_companies, tab_application, tab_mail = st.tabs(
    [
        "Profil erstellen",
        "Jobs matchen",
        "🏢 CompanyHub",
        "Bewerbungsmappe",
        "Versand",
    ]
)

with tab_profile:
    render_profile_tab()

with tab_jobs:
    render_jobs_tab(
        mode=mode,
        min_score=min_score,
        max_results=max_results,
        selected_tags=selected_tags,
    )

with tab_companies:
    render_company_tab(
        min_score=min_score,
        max_results=max_results,
    )

with tab_application:
    render_application_tab()

with tab_mail:
    st.subheader("Versand")

    st.info(
        "Hier wird später der Versand vorbereitet. "
        "Für die lokale Version bleibt zunächst der PDF-Download im Fokus."
    )

    st.button(
        "Bewerbung versenden",
        disabled=True,
    )
