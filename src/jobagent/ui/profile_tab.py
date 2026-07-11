import hashlib
import json

import streamlit as st

from jobagent.models.tag_labels import label_tag
from jobagent.models.skill_candidate import SkillCandidate
from jobagent.services.document_parser import extract_text_from_pdf
from jobagent.services.keyword_detector import detect_keyword_matches
from jobagent.services.ollama_provider import OllamaProvider
from jobagent.services.review_queue_service import (
    add_review_candidates,
    load_review_queue,
    review_item_key,
    update_review_status,
)
from jobagent.services.skill_registry_service import (
    list_skills,
)
from jobagent.services.skill_candidate_evaluator import (
    evaluate_unknown_skill_candidates,
    last_skill_evaluator_debug,
)
from jobagent.services.skill_candidate_builder import build_skill_candidates
from jobagent.services.skill_fusion import merge_skill_candidates
from jobagent.services.skill_profile_io import (
    profile_preferences_from_csv,
    skill_candidates_from_csv,
    skill_candidates_to_csv,
)
from jobagent.services.unknown_skill_service import (
    detect_unknown_skill_candidates,
)
from jobagent.services.job_service import (
    build_runtime_profile,
)
from jobagent.services.profile_mission_service import (
    build_profile_mission,
)


PREFERENCE_LABELS = {
    "banking": "Banking / Finanzbranche",
    "military": "Militär / Verteidigung",
    "defense": "Verteidigungsindustrie",
    "temporary_work": "Zeitarbeit",
    "labour_leasing": "Arbeitnehmerüberlassung",
    "labor_leasing": "Arbeitnehmerüberlassung",
    "security_clearance": "Sicherheitsüberprüfung",
}

PREFERENCE_LABEL_TO_KEY = {
    label.lower(): key
    for key, label in PREFERENCE_LABELS.items()
}
PREFERENCE_LABEL_TO_KEY.update(
    {
        "banking": "banking",
        "finanzbranche": "banking",
        "militaer": "military",
        "militaer / verteidigung": "military",
        "militär": "military",
        "militär / verteidigung": "military",
        "verteidigung": "defense",
        "verteidigungsindustrie": "defense",
        "zeitarbeit": "temporary_work",
        "temporary work": "temporary_work",
        "arbeitnehmerueberlassung": "labour_leasing",
        "arbeitnehmerüberlassung": "labour_leasing",
        "arbeitnehmerüberlassung": "labour_leasing",
        "labor leasing": "labour_leasing",
        "labour leasing": "labour_leasing",
        "sicherheitsueberpruefung": "security_clearance",
        "sicherheitsüberprüfung": "security_clearance",
        "security clearance": "security_clearance",
    }
)

INDUSTRY_EXCLUSION_OPTIONS = [
    "banking",
    "military",
    "defense",
    "gambling",
    "tobacco",
    "temporary_work",
]
EMPLOYMENT_EXCLUSION_OPTIONS = [
    "temporary_work",
    "labour_leasing",
    "freelance",
    "fixed_term",
    "shift_work",
]
REQUIREMENT_EXCLUSION_OPTIONS = [
    "security_clearance",
    "travel_required",
    "drivers_license_required",
    "onsite_only",
]
WORK_MODEL_LABELS = {
    "remote": "Remote",
    "hybrid": "Hybrid",
    "onsite": "Vor Ort",
}

PREFERENCE_LABELS.update(
    {
        "gambling": "Glücksspiel",
        "tobacco": "Tabak",
        "freelance": "Freelance",
        "fixed_term": "Befristet",
        "shift_work": "Schichtarbeit",
        "travel_required": "Reisetaetigkeit",
        "drivers_license_required": "Fuehrerschein erforderlich",
        "onsite_only": "Vor-Ort-only",
    }
)
PREFERENCE_LABEL_TO_KEY.update(
    {
        label.lower(): key
        for key, label in PREFERENCE_LABELS.items()
    }
)
PREFERENCE_LABEL_TO_KEY.update(
    {
        "gluecksspiel": "gambling",
        "glücksspiel": "gambling",
        "tabak": "tobacco",
        "freelance": "freelance",
        "befristet": "fixed_term",
        "schichtarbeit": "shift_work",
        "reisetaetigkeit": "travel_required",
        "reisetätigkeit": "travel_required",
        "fuehrerschein erforderlich": "drivers_license_required",
        "führerschein erforderlich": "drivers_license_required",
        "vor ort only": "onsite_only",
        "vor-ort-only": "onsite_only",
    }
)

PROFILE_DEPENDENT_SESSION_KEYS = (
    "job_results_cache",
    "jobs",
    "ranked_jobs",
    "job_results",
    "loaded_jobs",
    "job_matches",
    "profile_search_queries",
    "query_sources",
    "selected_job",
    "selected_application_job",
    "selected_application_result",
    "selected_application_job_key",
    "generated_cover_letter",
    "generated_cover_letter_job_key",
    "generated_context_resume",
    "generated_context_resume_job_key",
    "application_job_skill_analysis",
    "application_profile_summary",
    "application_profile_summary_tags",
    "application_context_cache",
    "application_attachment_cache",
    "job_unknown_skill_result",
)

ACTIVE_PROFILE_SESSION_KEYS = (
    "active_profile_fingerprint",
    "skill_candidates",
    "edited_skills",
    "profile_tags",
    "imported_profile_skills",
    "profile_csv_signature",
    "uploaded_pdf_signature",
    "llm_skill_candidates",
    "unknown_skill_candidates",
    "unknown_skill_evaluations",
    "unknown_skill_evaluation_signature",
    "evaluated_unknown_skill_candidates",
)

SKILL_REVIEW_WIDGET_PREFIXES = (
    "skill_enabled_",
    "skill_weight_",
)


def _clear_skill_review_widget_state() -> None:
    for key in list(st.session_state.keys()):
        if any(
            key.startswith(prefix)
            for prefix in SKILL_REVIEW_WIDGET_PREFIXES
        ):
            st.session_state.pop(key, None)


def _clear_profile_dependent_state() -> None:
    for key in PROFILE_DEPENDENT_SESSION_KEYS:
        st.session_state.pop(key, None)


def _clear_active_profile_state() -> bool:
    had_active_profile = any(
        key in st.session_state
        for key in ACTIVE_PROFILE_SESSION_KEYS
    )

    for key in ACTIVE_PROFILE_SESSION_KEYS:
        st.session_state.pop(key, None)

    _clear_skill_review_widget_state()
    _clear_profile_dependent_state()

    if had_active_profile:
        st.session_state["skill_review_id"] = (
            st.session_state.get("skill_review_id", 0) + 1
        )

    return had_active_profile


def _reset_current_profile_build_state() -> None:
    for key in (
        "skill_candidates",
        "edited_skills",
        "profile_tags",
        "llm_skill_candidates",
        "unknown_skill_candidates",
        "unknown_skill_evaluations",
        "unknown_skill_evaluation_signature",
        "evaluated_unknown_skill_candidates",
    ):
        st.session_state.pop(key, None)

    _clear_skill_review_widget_state()


def _split_preference_lines(value: str) -> list[str]:
    normalized = value.replace(
        ",",
        "\n",
    )

    values = []

    for item in normalized.splitlines():
        item = item.strip()

        if not item:
            continue

        normalized_item = item.lower()
        key = PREFERENCE_LABEL_TO_KEY.get(
            normalized_item,
            item,
        )

        if key not in values:
            values.append(key)

    return values


def _join_preference_lines(values) -> str:
    return "\n".join(
        PREFERENCE_LABELS.get(str(value), str(value))
        for value in values or []
        if str(value).strip()
    )


def _default_profile_preferences() -> dict:
    return {
        "salary_minimum": 0,
        "salary_target": 0,
        "salary_dream": 0,
        "hard_exclusion_industries": [],
        "hard_exclusion_employment_models": [],
        "hard_exclusion_requirements": [],
        "work_model_preferred": [],
        "work_model_acceptable": [],
    }


def _set_profile_preferences(preferences: dict) -> None:
    merged_preferences = _default_profile_preferences()
    merged_preferences.update(
        preferences or {}
    )

    st.session_state["profile_preferences"] = merged_preferences
    st.session_state["profile_pref_salary_minimum"] = int(
        merged_preferences.get("salary_minimum", 0) or 0
    )
    st.session_state["profile_pref_salary_target"] = int(
        merged_preferences.get("salary_target", 0) or 0
    )
    st.session_state["profile_pref_salary_dream"] = int(
        merged_preferences.get("salary_dream", 0) or 0
    )
    st.session_state["profile_pref_exclusion_industries"] = list(
        merged_preferences.get("hard_exclusion_industries", [])
        or []
    )
    st.session_state["profile_pref_exclusion_employment_models"] = list(
        merged_preferences.get("hard_exclusion_employment_models", [])
        or []
    )
    st.session_state["profile_pref_exclusion_requirements"] = list(
        merged_preferences.get("hard_exclusion_requirements", [])
        or []
    )
    st.session_state["profile_pref_work_model_preferred"] = list(
        merged_preferences.get("work_model_preferred", [])
        or []
    )
    st.session_state["profile_pref_work_model_acceptable"] = list(
        merged_preferences.get("work_model_acceptable", [])
        or []
    )


def _queue_profile_preferences_update(preferences: dict) -> None:
    merged_preferences = _default_profile_preferences()
    merged_preferences.update(
        preferences or {}
    )
    st.session_state["profile_preferences"] = merged_preferences
    st.session_state["pending_profile_preferences_from_csv"] = (
        merged_preferences
    )


def _apply_pending_profile_preferences_before_widgets() -> None:
    pending_preferences = st.session_state.pop(
        "pending_profile_preferences_from_csv",
        None,
    )

    if pending_preferences:
        _set_profile_preferences(
            pending_preferences
        )


def _looks_like_legacy_personal_defaults(preferences: dict) -> bool:
    return (
        int(preferences.get("salary_minimum", 0) or 0) == 60000
        and int(preferences.get("salary_target", 0) or 0) == 80000
        and int(preferences.get("salary_dream", 0) or 0) == 100000
        and {
            "banking",
            "military",
            "defense",
        }.issubset(
            set(
                preferences.get("hard_exclusion_industries", [])
                or []
            )
        )
    )


def _valid_options(values, options) -> list[str]:
    option_set = set(options)

    return [
        value
        for value in values or []
        if value in option_set
    ]


def _label_for_preference(value: str) -> str:
    return PREFERENCE_LABELS.get(
        value,
        value,
    )


def _normalize_legacy_multiselect_state() -> None:
    for key in [
        "profile_pref_exclusion_industries",
        "profile_pref_exclusion_employment_models",
        "profile_pref_exclusion_requirements",
    ]:
        value = st.session_state.get(key)

        if isinstance(value, str):
            st.session_state[key] = _split_preference_lines(
                value
            )


def _render_profile_preferences() -> None:
    preferences = st.session_state.get(
        "profile_preferences"
    )
    has_active_profile = bool(
        st.session_state.get("active_profile_fingerprint")
        or st.session_state.get("profile_tags")
    )

    if preferences is None or (
        not has_active_profile
        and _looks_like_legacy_personal_defaults(preferences)
    ):
        preferences = _default_profile_preferences()
        st.session_state["profile_preferences"] = preferences

    _normalize_legacy_multiselect_state()

    st.markdown("### Praeferenzen & Ausschluesse")

    salary_col1, salary_col2, salary_col3 = st.columns(3)

    salary_minimum = salary_col1.number_input(
        "Mindestgehalt",
        min_value=0,
        max_value=150000,
        step=5000,
        value=int(preferences.get("salary_minimum", 0) or 0),
        key="profile_pref_salary_minimum",
    )
    target_value = max(
        int(preferences.get("salary_target", 0) or 0),
        salary_minimum,
    )
    salary_target = salary_col2.number_input(
        "Zielgehalt",
        min_value=salary_minimum,
        max_value=150000,
        step=5000,
        value=target_value,
        key="profile_pref_salary_target",
    )
    dream_value = max(
        int(preferences.get("salary_dream", 0) or 0),
        salary_target,
    )
    salary_dream = salary_col3.number_input(
        "Wunschgehalt",
        min_value=salary_target,
        max_value=150000,
        step=5000,
        value=dream_value,
        key="profile_pref_salary_dream",
    )

    exclusion_col1, exclusion_col2, exclusion_col3 = st.columns(3)

    industries = exclusion_col1.multiselect(
        "Ausgeschlossene Branchen",
        options=INDUSTRY_EXCLUSION_OPTIONS,
        default=_valid_options(
            preferences.get("hard_exclusion_industries", []),
            INDUSTRY_EXCLUSION_OPTIONS,
        ),
        format_func=_label_for_preference,
        key="profile_pref_exclusion_industries",
    )
    employment_models = exclusion_col2.multiselect(
        "Ausgeschlossene Beschaeftigungsmodelle",
        options=EMPLOYMENT_EXCLUSION_OPTIONS,
        default=_valid_options(
            preferences.get("hard_exclusion_employment_models", []),
            EMPLOYMENT_EXCLUSION_OPTIONS,
        ),
        format_func=_label_for_preference,
        key="profile_pref_exclusion_employment_models",
    )
    requirements = exclusion_col3.multiselect(
        "Ausgeschlossene Anforderungen",
        options=REQUIREMENT_EXCLUSION_OPTIONS,
        default=_valid_options(
            preferences.get("hard_exclusion_requirements", []),
            REQUIREMENT_EXCLUSION_OPTIONS,
        ),
        format_func=_label_for_preference,
        key="profile_pref_exclusion_requirements",
    )

    work_model_col1, work_model_col2 = st.columns(2)
    preferred_work_models = work_model_col1.multiselect(
        "Bevorzugtes Arbeitsmodell",
        options=list(WORK_MODEL_LABELS),
        default=_valid_options(
            preferences.get("work_model_preferred", []),
            list(WORK_MODEL_LABELS),
        ),
        format_func=lambda value: WORK_MODEL_LABELS.get(value, value),
        key="profile_pref_work_model_preferred",
    )
    acceptable_work_models = work_model_col2.multiselect(
        "Akzeptable Arbeitsmodelle",
        options=list(WORK_MODEL_LABELS),
        default=_valid_options(
            preferences.get("work_model_acceptable", []),
            list(WORK_MODEL_LABELS),
        ),
        format_func=lambda value: WORK_MODEL_LABELS.get(value, value),
        key="profile_pref_work_model_acceptable",
    )

    updated_preferences = {
        "salary_minimum": salary_minimum,
        "salary_target": salary_target,
        "salary_dream": salary_dream,
        "hard_exclusion_industries": industries,
        "hard_exclusion_employment_models": employment_models,
        "hard_exclusion_requirements": requirements,
        "work_model_preferred": preferred_work_models,
        "work_model_acceptable": acceptable_work_models,
    }

    if updated_preferences != preferences:
        st.session_state["profile_preferences"] = updated_preferences

        if st.session_state.get("active_profile_fingerprint"):
            _clear_profile_dependent_state()


def _profile_skill_fingerprint(skills) -> str:
    payload = []

    for skill in skills or []:
        payload.append(
            {
                "name": str(getattr(skill, "name", "")).strip(),
                "category": str(getattr(skill, "category", "")).strip(),
                "weight": int(getattr(skill, "weight", 0) or 0),
                "enabled": bool(getattr(skill, "enabled", False)),
                "provider": str(getattr(skill, "provider", "")).strip(),
                "source": str(getattr(skill, "source", "")).strip(),
                "confidence": float(
                    getattr(skill, "confidence", 0) or 0
                ),
            }
        )

    payload = sorted(
        payload,
        key=lambda item: (
            item["name"].lower(),
            item["provider"].lower(),
            item["source"].lower(),
        ),
    )

    source_marker = {
        "profile_csv_signature": st.session_state.get(
            "profile_csv_signature"
        ),
        "uploaded_pdf_signature": st.session_state.get(
            "uploaded_pdf_signature"
        ),
    }

    data = {
        "skills": payload,
        "source": source_marker,
        "preferences": st.session_state.get(
            "profile_preferences",
            {},
        ),
    }

    return hashlib.sha256(
        json.dumps(
            data,
            ensure_ascii=False,
            sort_keys=True,
            default=str,
        ).encode("utf-8")
    ).hexdigest()


def _invalidate_profile_dependent_state(skills) -> bool:
    fingerprint = _profile_skill_fingerprint(skills)
    previous_fingerprint = st.session_state.get(
        "active_profile_fingerprint"
    )

    st.session_state["active_profile_fingerprint"] = fingerprint

    if previous_fingerprint is None:
        return False

    if previous_fingerprint == fingerprint:
        return False

    _clear_profile_dependent_state()

    return True


def _is_llm_suggestion(skill) -> bool:
    return getattr(skill, "provider", "") in {
        "llm",
        "unknown_llm",
    }


def render_skill_review(skill_candidates):
    st.markdown("**Skill Review:**")

    edited_skills = []
    review_id = st.session_state.get(
        "skill_review_id",
        0,
    )

    for skill in skill_candidates:
        with st.container():
            col_active, col_skill, col_weight = st.columns([1, 4, 3])

            with col_active:
                enabled = st.checkbox(
                    "Aktiv",
                    value=skill.enabled,
                    key=(
                        f"skill_enabled_{review_id}_"
                        f"{skill.provider}_{skill.name}"
                    ),
                )

            with col_skill:
                st.write(label_tag(skill.name))
                st.caption(
                    f"Quelle: {skill.provider} · {skill.source}"
                )

            with col_weight:
                if _is_llm_suggestion(skill) and not enabled:
                    weight = 5
                    st.caption(
                        "Profilgewichtung erst nach Aktivierung."
                    )
                else:
                    weight = st.slider(
                        "Gewichtung",
                        min_value=0,
                        max_value=10,
                        value=skill.weight,
                        key=(
                            f"skill_weight_{review_id}_"
                            f"{skill.provider}_{skill.name}"
                        ),
                    )

            skill.enabled = enabled
            skill.weight = weight
            edited_skills.append(skill)

    st.session_state["edited_skills"] = edited_skills

    active_profile_tags = {
        skill.name
        for skill in edited_skills
        if skill.enabled and skill.weight > 0
    }

    st.session_state["profile_tags"] = active_profile_tags

    if active_profile_tags:
        st.success(
            f"{len(active_profile_tags)} aktive Kompetenzen im Profil."
        )
    else:
        st.warning("Keine aktiven Kompetenzen im Profil.")


def _render_profile_mission() -> None:
    profile_tags = st.session_state.get(
        "profile_tags",
        set(),
    )
    profile_preferences = st.session_state.get(
        "profile_preferences",
        _default_profile_preferences(),
    )

    with st.expander(
        "Mission Profil",
        expanded=False,
    ):
        if not profile_tags:
            st.caption(
                "Noch keine aktiven Kompetenzen für ein Mission Profil vorhanden."
            )
            return

        runtime_profile = build_runtime_profile(
            profile_skills=profile_tags,
            profile_preferences=profile_preferences,
        )
        mission = build_profile_mission(
            runtime_profile
        )

        st.write(
            f"**Mission Summary:** {mission.summary}"
        )
        st.write(
            "**Mission Keywords:** "
            + (", ".join(mission.mission_keywords) or "-")
        )
        st.write(
            "**Domänen:** "
            + (", ".join(mission.interest_domains) or "-")
        )
        st.write(
            "**Problemfelder:** "
            + (", ".join(mission.preferred_problem_domains) or "-")
        )
        st.write(
            "**Technologien:** "
            + (", ".join(mission.preferred_technologies) or "-")
        )
        st.write(
            "**Arbeitsmodelle:** "
            + (", ".join(mission.preferred_work_models) or "-")
        )
        st.write(
            "**Unternehmenstypen:** "
            + (", ".join(mission.preferred_company_types) or "-")
        )
        st.write(
            f"**KRITIS Affinity:** {mission.kritis_affinity:.2f}"
        )
        st.write(
            f"**Innovation Affinity:** {mission.innovation_affinity:.2f}"
        )
        st.write(
            f"**Public Sector Affinity:** {mission.public_sector_affinity:.2f}"
        )
        st.write(
            f"**Research Affinity:** {mission.research_affinity:.2f}"
        )
        st.write(
            f"**Confidence:** {mission.confidence:.2f}"
        )


def _load_profile_csv(profile_csv) -> bool:
    if not profile_csv:
        return False

    csv_signature = (
        profile_csv.name,
        profile_csv.size,
    )

    if (
        st.session_state.get("profile_csv_signature")
        != csv_signature
    ):
        _reset_current_profile_build_state()
        csv_text = profile_csv.getvalue().decode("utf-8-sig")
        imported_skills = skill_candidates_from_csv(csv_text)
        imported_preferences = profile_preferences_from_csv(csv_text)

        if imported_preferences:
            _queue_profile_preferences_update(
                imported_preferences
            )

        st.session_state["profile_csv_signature"] = csv_signature
        st.session_state["imported_profile_skills"] = imported_skills
        st.session_state["skill_review_id"] = (
            st.session_state.get("skill_review_id", 0) + 1
        )

        if imported_preferences:
            st.rerun()
    else:
        imported_skills = st.session_state.get(
            "imported_profile_skills",
            [],
        )

    st.session_state["skill_candidates"] = imported_skills

    profile_tags = {
        skill.name
        for skill in imported_skills
        if skill.enabled and skill.weight > 0
    }

    st.session_state["profile_tags"] = profile_tags

    st.success(
        f"Profil mit {len(imported_skills)} Skills geladen."
    )

    render_skill_review(imported_skills)

    if _invalidate_profile_dependent_state(
        st.session_state.get("edited_skills", imported_skills)
    ):
        st.info(
            "Profil geaendert: Job-Ergebnisse und Bewerbungsmappe-Auswahl "
            "wurden zurueckgesetzt."
        )

    return True


def _run_llm_analysis(text: str):
    progress = st.progress(0)
    status = st.empty()

    status.write("LLM-Analyse vorbereitet...")
    progress.progress(10)

    status.write("Dokumenttext wird übergeben...")
    progress.progress(25)

    status.write("Qwen analysiert Skills...")
    progress.progress(60)

    provider = OllamaProvider()
    llm_skills = provider.extract_skills(text)

    status.write("LLM-Analyse abgeschlossen.")
    progress.progress(100)

    if llm_skills:
        st.success(
            f"LLM hat {len(llm_skills)} Skill(s) erkannt."
        )

        existing_candidates = st.session_state.get(
            "llm_skill_candidates",
            [],
        )

        existing_candidates.extend(llm_skills)

        st.session_state[
            "llm_skill_candidates"
        ] = existing_candidates
    else:
        st.info(
            "LLM hat keine zusätzlichen Skills erkannt."
        )


def _evaluation_signature(candidates: list[str]) -> tuple[str, ...]:
    return tuple(
        sorted(
            candidate.strip().lower()
            for candidate in candidates
            if candidate and candidate.strip()
        )
    )


def _run_unknown_skill_evaluation(
    candidates: list[str],
    context_text: str,
    document_sources: dict[str, list[str]],
) -> None:
    with st.spinner(
        "Qwen bewertet unbekannte Skill-Kandidaten..."
    ):
        evaluations = evaluate_unknown_skill_candidates(
            candidates,
            context_text,
            document_sources=document_sources,
        )

    st.session_state[
        "unknown_skill_evaluations"
    ] = evaluations
    st.session_state[
        "review_queue"
    ] = add_review_candidates(
        evaluations
    )
    st.session_state[
        "unknown_skill_evaluation_signature"
    ] = _evaluation_signature(
        candidates
    )

    evaluated_candidates = [
        SkillCandidate(
            name=evaluation.suggested_tag,
            category=evaluation.category,
            confidence=evaluation.confidence,
            weight=5,
            enabled=False,
            source=(
                f"{evaluation.canonical_name}: "
                f"{evaluation.reason} | "
                f"LLM-Gewichtungsvorschlag: {evaluation.weight}/10"
            ),
            provider="unknown_llm",
            candidate_domain=evaluation.candidate_domain,
        )
        for evaluation in evaluations
        if evaluation.is_skill
        and evaluation.accepted
        and evaluation.confidence >= 0.5
    ]

    st.session_state[
        "evaluated_unknown_skill_candidates"
    ] = evaluated_candidates
    st.session_state["skill_review_id"] = (
        st.session_state.get("skill_review_id", 0) + 1
    )

    if evaluations:
        st.success(
            f"Qwen hat {len(evaluations)} Skill-Vorschlag/Vorschlaege bewertet."
        )
    else:
        st.info(
            "Qwen hat keine belastbaren neuen Skills vorgeschlagen."
        )
        debug = last_skill_evaluator_debug()

        if debug:
            with st.expander(
                "Evaluator-Debug anzeigen",
                expanded=False,
            ):
                st.code(
                    debug,
                    language="text",
                )


def _render_unknown_skill_evaluations():
    evaluations = st.session_state.get(
        "unknown_skill_evaluations",
        [],
    )

    if not evaluations:
        return

    st.markdown("### Bewertete Skill-Vorschlaege")

    for evaluation in evaluations:
        with st.container():
            st.write(
                f"**{evaluation.name}** -> "
                f"`{evaluation.suggested_tag}`"
            )
            st.caption(
                f"Typ: {evaluation.candidate_type} | "
                f"Canonical: {evaluation.canonical_name} | "
                f"Kategorie: {evaluation.category} | "
                f"Gewichtung: {evaluation.weight}/10 | "
                f"Confidence: {evaluation.confidence:.2f}"
            )
            st.caption(
                f"Quelle: {evaluation.source_type} | "
                f"{evaluation.document_source or 'unbekannt'} | "
                f"is_skill={evaluation.is_skill}"
            )

            if evaluation.reason:
                st.write(evaluation.reason)


def _source_origin_label(item: dict) -> str:
    sources = item.get("sources")

    if not isinstance(sources, list) or not sources:
        source_type = item.get("source_type") or "profile_document"

        if source_type == "job_posting":
            return "Jobanzeige"

        if source_type == "mixed":
            return "Profil + Jobanzeige"

        return "Profil"

    profile_count = sum(
        1
        for source in sources
        if source.get("source_type") == "profile_document"
    )
    job_count = sum(
        1
        for source in sources
        if source.get("source_type") == "job_posting"
    )

    if profile_count and job_count:
        return f"Profil + {job_count} Jobanzeige(n)"

    if job_count:
        return f"{job_count} Jobanzeige(n)"

    return "Profil"


def _source_kind(item: dict) -> str:
    sources = item.get("sources")

    if not isinstance(sources, list) or not sources:
        source_type = item.get("source_type") or "profile_document"

        if source_type == "mixed":
            return "mixed"

        if source_type == "job_posting":
            return "job_posting"

        return "profile_document"

    source_types = {
        source.get("source_type")
        for source in sources
        if source.get("source_type")
    }

    if "profile_document" in source_types and "job_posting" in source_types:
        return "mixed"

    if "job_posting" in source_types:
        return "job_posting"

    return "profile_document"


def _queue_sort_key(item: dict):
    return 0 if item.get("status") == "pending" else 1


def _source_lines(item: dict) -> list[str]:
    sources = item.get("sources")

    if not isinstance(sources, list) or not sources:
        return [
            item.get("document_source") or "unbekannt"
        ]

    lines = []

    for source in sources:
        if source.get("source_type") == "job_posting":
            parts = [
                source.get("job_title") or source.get("document_source"),
                source.get("company"),
                source.get("job_source"),
            ]
            line = " | ".join(
                part
                for part in parts
                if part
            )
        else:
            line = source.get("document_source") or "Profil"

        if line and line not in lines:
            lines.append(line)

    return lines


def _render_review_queue_status():
    queue = st.session_state.get(
        "review_queue",
    )

    if queue is None:
        queue = load_review_queue()
        st.session_state["review_queue"] = queue

    if not queue:
        return

    pending_count = len(
        [
            item
            for item in queue
            if item.get("status") == "pending"
        ]
    )

    st.caption(
        f"Persistente Review Queue: {pending_count} pending, "
        f"{len(queue)} gesamt."
    )

    with st.expander(
        "Review Queue anzeigen",
        expanded=False,
    ):
        filter_col1, filter_col2, filter_col3 = st.columns(3)
        status_filter = filter_col1.selectbox(
            "Status anzeigen",
            [
                "pending",
                "approved",
                "rejected",
                "alle",
            ],
            key="review_queue_status_filter",
        )
        source_filter = filter_col2.selectbox(
            "Quelle anzeigen",
            [
                "alle",
                "Profil",
                "Jobanzeige",
                "gemischt",
            ],
            key="review_queue_source_filter",
        )
        max_items = filter_col3.selectbox(
            "Eintraege",
            [
                20,
                50,
                100,
                200,
            ],
            index=1,
            key="review_queue_max_items",
        )
        source_filter_map = {
            "Profil": "profile_document",
            "Jobanzeige": "job_posting",
            "gemischt": "mixed",
        }
        filtered_queue = []

        for item in queue:
            if (
                status_filter != "alle"
                and item.get("status", "pending") != status_filter
            ):
                continue

            if (
                source_filter != "alle"
                and _source_kind(item) != source_filter_map[source_filter]
            ):
                continue

            filtered_queue.append(item)

        filtered_queue = sorted(
            filtered_queue,
            key=lambda item: str(
                item.get("updated_at") or item.get("created_at") or ""
            ),
            reverse=True,
        )
        filtered_queue = sorted(
            filtered_queue,
            key=_queue_sort_key,
        )

        st.caption(
            f"{len(filtered_queue)} Eintrag/Eintraege im aktuellen Filter."
        )

        if not filtered_queue:
            st.info(
                "Keine Review-Einträge für diesen Filter."
            )
            return

        for index, item in enumerate(filtered_queue[:max_items]):
            suggested_tag = item.get(
                "suggested_tag",
                "",
            )
            current_status = item.get(
                "status",
                "pending",
            )
            options = [
                "pending",
                "approved",
                "rejected",
            ]

            if current_status not in options:
                current_status = "pending"

            item_key = review_item_key(item)

            st.write(
                f"**{item.get('name', suggested_tag)}** -> "
                f"`{suggested_tag}`"
            )
            try:
                confidence = float(
                    item.get("confidence", 0)
                )
            except (TypeError, ValueError):
                confidence = 0.0

            st.caption(
                f"Typ: {item.get('candidate_type', 'unknown')} | "
                f"Domain: {item.get('candidate_domain', 'unknown')} | "
                f"Canonical: {item.get('canonical_name', '')} | "
                f"{item.get('category', 'unknown')} | "
                f"Quelle: {_source_origin_label(item)} | "
                f"Confidence: {confidence:.2f}"
            )

            for source_line in _source_lines(item)[:5]:
                st.caption(
                    f"- {source_line}"
                )

            selected_status = st.selectbox(
                "Status",
                options,
                index=options.index(current_status),
                key=f"review_status_{index}_{item_key}",
            )

            canonical_override = st.text_input(
                "Canonical Name",
                value=str(
                    item.get("canonical_name")
                    or item.get("name")
                    or suggested_tag
                    or ""
                ),
                key=f"review_canonical_{index}_{item_key}",
            )
            type_options = [
                "skill",
                "certification",
                "role",
                "context",
                "other",
            ]
            current_type = str(
                item.get("candidate_type") or "skill"
            ).lower()
            if current_type not in type_options:
                current_type = "skill"
            selected_type = st.selectbox(
                "Typ",
                type_options,
                index=type_options.index(current_type),
                key=f"review_type_{index}_{item_key}",
            )
            existing_skills = list_skills()
            existing_options = [
                "Neuen Skill anlegen"
            ] + [
                f"{skill.id}: {skill.display_name} ({skill.type})"
                for skill in existing_skills
                if skill.id is not None
            ]
            selected_existing = st.selectbox(
                "Registry-Ziel",
                existing_options,
                key=f"review_existing_{index}_{item_key}",
            )
            alias_text = st.text_input(
                "Weitere Aliases (Semikolon-getrennt)",
                value="",
                key=f"review_aliases_{index}_{item_key}",
            )
            conflict = item.get("registry_conflict")
            if conflict:
                st.warning(
                    "Registry-Konflikt: gleicher Name/Alias existiert "
                    f"bereits als Typ `{conflict.get('existing_type')}`."
                )

            if selected_status != item.get("status"):
                existing_skill_id = None
                if selected_existing != "Neuen Skill anlegen":
                    try:
                        existing_skill_id = int(
                            selected_existing.split(
                                ":",
                                1,
                            )[0]
                        )
                    except (TypeError, ValueError):
                        existing_skill_id = None

                st.session_state["review_queue"] = update_review_status(
                    item_key,
                    selected_status,
                    canonical_name=canonical_override,
                    candidate_type=selected_type,
                    aliases=[
                        alias.strip()
                        for alias in alias_text.split(";")
                        if alias.strip()
                    ],
                    existing_skill_id=existing_skill_id,
                )


def _uploaded_file_signature(uploaded_file) -> tuple[str, int]:
    return (
        uploaded_file.name,
        uploaded_file.size,
    )


def _analyze_uploaded_file(uploaded_file):
    cache = st.session_state.setdefault(
        "uploaded_pdf_analysis_cache",
        {},
    )
    signature = _uploaded_file_signature(
        uploaded_file
    )

    if signature in cache:
        return cache[signature]

    text = extract_text_from_pdf(uploaded_file)
    matches = detect_keyword_matches(text)

    cache[signature] = {
        "text": text,
        "matches": matches,
    }

    return cache[signature]


def render_profile_tab():
    st.subheader("Bewerbungsunterlagen")

    _apply_pending_profile_preferences_before_widgets()

    _render_profile_preferences()

    profile_csv = st.file_uploader(
        "Bestehendes Profil laden",
        type=["csv"],
        accept_multiple_files=False,
    )

    if _load_profile_csv(profile_csv):
        return

    uploaded_files = st.file_uploader(
        "Lebenslauf, Zeugnisse oder Zertifikate hochladen",
        type=["pdf"],
        accept_multiple_files=True,
    )

    run_llm = st.button(
        "LLM-Analyse starten",
        disabled=not uploaded_files,
    )

    if not uploaded_files:
        if _clear_active_profile_state():
            st.info(
                "Profil entfernt: Skill Review, Job-Ergebnisse und "
                "Bewerbungsmappe-Auswahl wurden zurueckgesetzt."
            )

        st.info(
            "Bitte zuerst ein Profil hochladen oder laden."
        )
        return

    st.success(f"{len(uploaded_files)} Datei(en) ausgewählt")

    pdf_signature = tuple(
        _uploaded_file_signature(uploaded_file)
        for uploaded_file in uploaded_files
    )

    if (
        st.session_state.get("uploaded_pdf_signature")
        != pdf_signature
    ):
        _reset_current_profile_build_state()
        st.session_state["uploaded_pdf_signature"] = pdf_signature
        st.session_state["skill_review_id"] = (
            st.session_state.get("skill_review_id", 0) + 1
        )

    all_matches = {}
    all_unknown_candidates = set()
    all_unknown_sources = {}
    all_text_parts = []

    if run_llm:
        st.session_state["llm_skill_candidates"] = []

    for uploaded_file in uploaded_files:
        st.write(
            f"Dokument: {uploaded_file.name} "
            f"({uploaded_file.size / 1024:.1f} KB)"
        )

        try:
            analysis = _analyze_uploaded_file(
                uploaded_file
            )
            text = analysis["text"]
            matches = analysis["matches"]
            all_text_parts.append(text)

            unknown_candidates = detect_unknown_skill_candidates(
                text
            )

            all_unknown_candidates.update(
                unknown_candidates
            )

            for candidate in unknown_candidates:
                all_unknown_sources.setdefault(
                    candidate,
                    set(),
                ).add(uploaded_file.name)

            st.write(f"Extrahierte Zeichen: {len(text)}")

            with st.expander(
                f"PDF-Textvorschau: {uploaded_file.name}",
                expanded=False,
            ):
                st.text_area(
                    "Extrahierter Rohtext",
                    text[:3000],
                    height=300,
                )

            for tag, keywords in matches.items():
                if tag not in all_matches:
                    all_matches[tag] = set()

                all_matches[tag].update(keywords)

            if run_llm:
                _run_llm_analysis(text)

        except Exception as error:
            st.error(
                f"Fehler beim Lesen von {uploaded_file.name}: {error}"
            )

    st.session_state[
        "unknown_skill_candidates"
    ] = sorted(
        all_unknown_candidates
    )

    if not all_matches and not st.session_state.get(
        "llm_skill_candidates",
        [],
    ):
        st.info(
            "Keine bekannten Kompetenzen in den hochgeladenen PDFs erkannt."
        )

    if all_matches:
        st.markdown("**Erkannte Kompetenzen:**")

        for tag, keywords in sorted(all_matches.items()):
            st.write(
                f"✓ **{label_tag(tag)}** "
                f"({', '.join(sorted(keywords))})"
            )

    if all_unknown_candidates:
        st.markdown("### Neue Skill-Kandidaten")

        st.info(
            f"{len(all_unknown_candidates)} unbekannte Begriffe erkannt."
        )

        with st.expander(
            "Unbekannte Begriffe anzeigen",
            expanded=False,
        ):
            for candidate in sorted(
                all_unknown_candidates,
                key=str.lower,
            )[:100]:
                st.write(
                    f"• {candidate}"
                )
        sorted_unknown_candidates = sorted(
            all_unknown_candidates,
            key=str.lower,
        )
        document_sources = {
            candidate: sorted(sources)
            for candidate, sources in all_unknown_sources.items()
        }

        with st.expander(
            "Rohkandidaten für Qwen anzeigen",
            expanded=False,
        ):
            st.code(
                "\n".join(sorted_unknown_candidates),
                language="text",
            )

        if st.button(
            "Unbekannte Skills mit Qwen bewerten",
            disabled=not sorted_unknown_candidates,
        ):
            _run_unknown_skill_evaluation(
                sorted_unknown_candidates,
                "\n\n".join(all_text_parts),
                document_sources,
            )
    else:
        st.info(
            "Keine unbekannten Skill-Kandidaten erkannt."
        )

    _render_unknown_skill_evaluations()
    _render_review_queue_status()

    evaluated_unknown_skills = st.session_state.get(
        "evaluated_unknown_skill_candidates",
        [],
    )

    if (
        not all_matches
        and not st.session_state.get("llm_skill_candidates", [])
        and not evaluated_unknown_skills
    ):
        return

    skill_candidates = build_skill_candidates(all_matches)

    llm_skill_candidates = st.session_state.get(
        "llm_skill_candidates",
        [],
    )

    skill_candidates.extend(llm_skill_candidates)
    skill_candidates.extend(evaluated_unknown_skills)
    skill_candidates = merge_skill_candidates(
        skill_candidates
    )

    st.session_state["skill_candidates"] = skill_candidates
    st.session_state.setdefault(
        "skill_review_id",
        0,
    )

    render_skill_review(skill_candidates)

    edited_skills = st.session_state.get(
        "edited_skills",
        [],
    )

    if _invalidate_profile_dependent_state(
        edited_skills or skill_candidates
    ):
        st.info(
            "Profil geaendert: Job-Ergebnisse und Bewerbungsmappe-Auswahl "
            "wurden zurueckgesetzt."
        )

    _render_profile_mission()

    if edited_skills:
        csv_content = skill_candidates_to_csv(
            edited_skills,
            preferences=st.session_state.get(
                "profile_preferences",
                _default_profile_preferences(),
            ),
        )

        st.download_button(
            label="Profil als CSV herunterladen",
            data=csv_content,
            file_name="careerhub_profile.csv",
            mime="text/csv",
        )
