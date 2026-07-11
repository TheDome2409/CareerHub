import hashlib
import json

import pandas as pd
import streamlit as st

from jobagent.models.tag_labels import label_tag
from jobagent.services.job_service import (
    build_runtime_search_queries,
    load_and_rank_jobs,
)
from jobagent.services.job_unknown_skill_service import (
    detect_job_unknown_skills,
)
from jobagent.services.label_service import (
    get_label,
)
from jobagent.services.profile_matcher import compare_tags
from jobagent.services.recommendation_snapshot_service import (
    build_recommendation_snapshot,
    save_snapshot_once,
    stable_recommendation_id,
)
from jobagent.services.recommendation_outcome_service import (
    append_outcome,
    create_outcome,
    get_outcomes_for_recommendation,
    load_outcomes,
)


OUTCOME_ACTIONS = (
    ("saved", "Gespeichert"),
    ("applied", "Beworben"),
    ("interview", "Interview"),
    ("offer", "Angebot"),
    ("accepted", "Angenommen"),
    ("rejected", "Abgelehnt"),
)


def score_icon(score: int) -> str:
    if score >= 50:
        return "🟢"

    if score >= 35:
        return "🟡"

    return "⚪"


def _source_name(job) -> str | None:
    return getattr(job, "source_name", None)


def _company_display(job) -> str:
    if job.company:
        return job.company

    return "Arbeitgeber unbekannt"


def _job_heading(job) -> str:
    company = _company_display(job)
    source_name = _source_name(job)

    if source_name and not job.company:
        return f"{job.title} · {company} · Quelle: {source_name}"

    return f"{job.title} · {company}"


def _job_key(job) -> str:
    return "|".join(
        [
            job.title or "",
            job.company or "",
            job.url or "",
            _source_name(job) or "",
        ]
    )


def _recommendation_id(
    result,
    profile_fingerprint: str,
) -> str:
    return stable_recommendation_id(
        profile_fingerprint,
        result["job"],
    )


def _result_score_snapshot(result) -> dict:
    return {
        "total_score": result.get("score", 0),
        "skill_score": result.get("skill_score", 0),
        "competency_score": result.get("competency_score", 0),
        "matched_skills": result.get("matched_skills", []),
        "missing_skills": result.get("missing_skills", []),
        "skill_match_ratio": result.get("skill_match_ratio", 0.0),
    }


def _qualification_status(result) -> str | None:
    qualification_result = result.get(
        "qualification_result"
    )

    if not qualification_result:
        return None

    return getattr(
        qualification_result,
        "qualification_status",
        None,
    )


def _persist_recommendation_snapshots(
    results,
    profile_fingerprint: str,
) -> None:
    for result in results:
        job = result["job"]
        recommendation_id = _recommendation_id(
            result,
            profile_fingerprint,
        )
        snapshot = build_recommendation_snapshot(
            profile_fingerprint=profile_fingerprint,
            job=job,
            score_result=_result_score_snapshot(result),
            query_source=job.query_source,
            recommendation_id=recommendation_id,
            qualification_status=_qualification_status(result),
        )
        save_snapshot_once(
            snapshot
        )


def _outcome_status(outcomes) -> str:
    if not outcomes:
        return "keine Markierung"

    labels = {
        event_type: label
        for event_type, label in OUTCOME_ACTIONS
    }

    return ", ".join(
        labels.get(
            outcome.event_type,
            outcome.event_type,
        )
        for outcome in outcomes
    )


def _render_outcome_controls(
    result,
    profile_fingerprint: str,
) -> None:
    recommendation_id = _recommendation_id(
        result,
        profile_fingerprint,
    )
    outcomes = get_outcomes_for_recommendation(
        recommendation_id,
        outcomes=load_outcomes(),
    )
    existing_events = {
        outcome.event_type
        for outcome in outcomes
    }

    st.write(
        f"**Outcome Status:** {_outcome_status(outcomes)}"
    )
    st.caption(
        f"Recommendation ID: {recommendation_id[:12]}"
    )

    columns = st.columns(
        len(OUTCOME_ACTIONS)
    )

    for column, (event_type, label) in zip(columns, OUTCOME_ACTIONS):
        disabled = event_type in existing_events

        if column.button(
            label,
            key=(
                f"outcome_{event_type}_{recommendation_id}"
            ),
            disabled=disabled,
        ):
            outcome = create_outcome(
                recommendation_id=recommendation_id,
                event_type=event_type,
            )
            append_outcome(
                outcome
            )
            st.success(
                f"Outcome gespeichert: {label}"
            )
            st.rerun()


def _qualification_state(result) -> str:
    qualification_result = result.get(
        "qualification_result"
    )

    if not qualification_result:
        return "not_checked"

    qualification_status = getattr(
        qualification_result,
        "qualification_status",
        None,
    )

    if qualification_status:
        return qualification_status

    if qualification_result.eligible and not qualification_result.warnings:
        return "ok"

    if qualification_result.eligible:
        return "needs_review"

    return "formal_review"


def _label_competency(name: str) -> str:
    return get_label(
        name
    )


def _render_competency_match(result) -> None:
    ratio = float(
        result.get("competency_match_ratio") or 0.0
    )
    percent = round(
        ratio * 100
    )
    matched = result.get(
        "matched_competencies",
        [],
    )
    missing = result.get(
        "missing_competencies",
        [],
    )
    skill_ratio = float(
        result.get("skill_match_ratio") or 0.0
    )

    st.write(
        f"**Kompetenz-Match:** {percent}%"
    )

    if ratio > skill_ratio:
        st.caption(
            "Der Kompetenz-Match ist hoeher als der direkte Skill-Match. "
            "CareerHub erkennt uebertragbare Kompetenzen aus Ihrem Profil."
        )

    if not matched and not missing:
        st.caption(
            "Keine Kompetenzanforderungen aus den Basisregeln erkannt."
        )
        return

    if matched:
        st.write(
            "Gematcht: "
            + ", ".join(
                _label_competency(competency)
                for competency in matched
            )
        )

    if missing:
        st.write(
            "Fehlend: "
            + ", ".join(
                _label_competency(competency)
                for competency in missing
            )
        )


def _render_limited_values(
    title: str,
    values,
    limit: int = 10,
) -> None:
    cleaned_values = [
        str(value)
        for value in values or []
        if str(value).strip()
    ]

    st.write(
        f"**{title}:**"
    )

    if not cleaned_values:
        st.caption(
            "Keine Werte erkannt."
        )
        return

    visible_values = cleaned_values[:limit]
    hidden_values = cleaned_values[limit:]

    for value in visible_values:
        st.write(
            f"- {get_label(value)}"
        )

    if hidden_values:
        with st.expander(
            f"Weitere {len(hidden_values)} anzeigen",
            expanded=False,
        ):
            for value in hidden_values:
                st.write(
                    f"- {get_label(value)}"
                )


def _render_job_intelligence(result) -> None:
    job_intelligence = result.get(
        "job_intelligence"
    )

    if not job_intelligence:
        return

    st.write(
        "**Job Intelligence**"
    )
    st.caption(
        "CareerHub hat diese Informationen aus Titel, Tags "
        "und Stellenbeschreibung abgeleitet."
    )
    st.write(
        f"Analyse Confidence: {round(job_intelligence.confidence * 100)}%"
    )

    _render_limited_values(
        "Erkannte Skills",
        job_intelligence.extracted_skills,
    )
    _render_limited_values(
        "Erkannte Kompetenzen",
        job_intelligence.extracted_competencies,
    )
    _render_limited_values(
        "Erkannte Qualifikationen",
        job_intelligence.qualification_requirements,
    )
    _render_limited_values(
        "Erkannte Evidence",
        job_intelligence.evidence_requirements,
    )


def _render_qualification_result(result) -> None:
    qualification_result = result.get(
        "qualification_result"
    )

    if not qualification_result:
        return

    state = _qualification_state(
        result
    )
    st.write(
        f"**Qualifikation:** {state} "
        f"({qualification_result.qualification_score}/100)"
    )

    if qualification_result.warnings:
        for warning in qualification_result.warnings:
            st.caption(
                f"Hinweis: {warning}"
            )
    else:
        st.caption(
            "Keine formalen Qualification Gaps aus den Basisregeln erkannt."
        )

    if qualification_result.missing_requirements:
        with st.expander(
            "Fehlende Qualifikationsanforderungen",
            expanded=False,
        ):
            for requirement in qualification_result.missing_requirements:
                st.write(
                    f"- {get_label(requirement.requirement_type)}: "
                    f"{requirement.description} "
                    f"({get_label(requirement.severity)})"
                )


def _profile_tags_fingerprint(profile_tags) -> str:
    tags = sorted(
        str(tag).strip()
        for tag in profile_tags or []
        if str(tag).strip()
    )

    return hashlib.sha256(
        json.dumps(
            tags,
            ensure_ascii=False,
        ).encode("utf-8")
    ).hexdigest()


def _query_fingerprint(queries: list[str]) -> str:
    normalized_queries = [
        str(query).strip()
        for query in queries
        if str(query).strip()
    ]

    return hashlib.sha256(
        json.dumps(
            normalized_queries,
            ensure_ascii=False,
        ).encode("utf-8")
    ).hexdigest()


def _preferences_fingerprint(preferences: dict) -> str:
    return hashlib.sha256(
        json.dumps(
            preferences or {},
            ensure_ascii=False,
            sort_keys=True,
            default=str,
        ).encode("utf-8")
    ).hexdigest()


def _render_job_unknown_skill_controls(results):
    st.divider()
    st.write("**Unbekannte Skills aus Stellenanzeigen**")

    limit = st.selectbox(
        "Anzahl Jobs analysieren",
        [5, 10, 25],
        index=1,
        key="job_unknown_skill_limit",
    )

    if st.button(
        "Unbekannte Skills aus geladenen Stellenanzeigen erkennen",
        key="detect_job_unknown_skills",
    ):
        jobs = [
            result["job"]
            for result in results
        ]

        with st.spinner(
            "Analysiere Stellenanzeigen und bewerte Kandidaten..."
        ):
            result = detect_job_unknown_skills(
                jobs,
                limit=limit,
            )

        st.session_state["job_unknown_skill_result"] = result

    result = st.session_state.get(
        "job_unknown_skill_result"
    )

    if not result:
        return

    col1, col2, col3 = st.columns(3)
    col1.metric(
        "Analysierte Jobs",
        result.analyzed_jobs,
    )
    col2.metric(
        "Kandidaten",
        len(result.candidates),
    )
    col3.metric(
        "Review Queue",
        result.queued_count,
    )

    if result.candidates:
        with st.expander(
            "Rohkandidaten aus Jobanzeigen anzeigen",
            expanded=False,
        ):
            for candidate in result.candidates:
                st.write(
                    f"- {candidate}"
                )

    if result.used_fallback:
        st.warning(
            "Qwen hat keine bewerteten Job-Skills geliefert. "
            "Die Rohkandidaten wurden deshalb als Review-Kandidaten "
            "mit niedrigerer Confidence uebernommen."
        )
        if result.evaluator_debug:
            st.caption(
                f"Evaluator Debug: {result.evaluator_debug}"
            )

    if result.evaluations:
        with st.expander(
            "Gefundene Job-Kandidaten anzeigen",
            expanded=False,
        ):
            for evaluation in result.evaluations:
                st.write(
                    f"**{evaluation.canonical_name or evaluation.name}**"
                )
                st.caption(
                    f"Typ: {evaluation.candidate_type} | "
                    f"Quelle: {evaluation.document_source or 'Jobanzeige'} | "
                    f"Confidence: {evaluation.confidence:.2f}"
                )
    elif result.candidates:
        st.info(
            "Kandidaten erkannt, aber Qwen hat keine Review-Eintraege "
            "zurueckgegeben."
        )
        if result.evaluator_debug:
            st.caption(
                f"Evaluator Debug: {result.evaluator_debug}"
            )
    else:
        st.info(
            "Keine unbekannten Skill-Kandidaten in den analysierten Jobs gefunden."
        )


def _render_active_search_queries() -> None:
    queries = st.session_state.get(
        "profile_search_queries",
        [],
    )

    if not queries:
        st.caption(
            "Aktuelle Suchbegriffe: keine profilbasierten Suchbegriffe."
        )
        return

    st.caption(
        "Aktuelle Suchbegriffe: "
        + ", ".join(
            str(query)
            for query in queries
        )
    )


def _load_cached_results(min_score: int, profile_tags, profile_preferences):
    cache_key = "job_results_cache"
    cached = st.session_state.get(cache_key)
    profile_fingerprint = st.session_state.get(
        "active_profile_fingerprint"
    ) or _profile_tags_fingerprint(profile_tags)
    search_queries = build_runtime_search_queries(
        profile_skills=profile_tags,
        profile_preferences=profile_preferences,
    )
    query_fingerprint = _query_fingerprint(
        search_queries
    )
    preferences_fingerprint = _preferences_fingerprint(
        profile_preferences
    )

    st.session_state["profile_search_queries"] = search_queries
    st.session_state["query_sources"] = search_queries

    if (
        cached
        and cached.get("min_score") == min_score
        and cached.get("profile_fingerprint") == profile_fingerprint
        and cached.get("query_fingerprint") == query_fingerprint
        and cached.get("preferences_fingerprint")
        == preferences_fingerprint
    ):
        return cached["results"]

    results = load_and_rank_jobs(
        min_score=min_score,
        profile_skills=profile_tags,
        search_queries=search_queries,
        profile_preferences=profile_preferences,
    )

    st.session_state[cache_key] = {
        "min_score": min_score,
        "profile_fingerprint": profile_fingerprint,
        "query_fingerprint": query_fingerprint,
        "preferences_fingerprint": preferences_fingerprint,
        "queries": search_queries,
        "results": results,
    }

    return results


def render_jobs_tab(
    mode: str,
    min_score: int,
    max_results: int,
    selected_tags: list[str],
):
    st.subheader("Jobs")

    profile_tags = st.session_state.get(
        "profile_tags",
        set(),
    )
    profile_preferences = st.session_state.get(
        "profile_preferences",
        {},
    )
    profile_fingerprint = st.session_state.get(
        "active_profile_fingerprint"
    ) or _profile_tags_fingerprint(profile_tags)

    if not profile_tags:
        st.warning(
            "Noch kein Profil erstellt. "
            "Bitte zuerst im Tab 'Profil erstellen' Dokumente hochladen."
        )
        return

    results = _load_cached_results(
        min_score=min_score,
        profile_tags=profile_tags,
        profile_preferences=profile_preferences,
    )

    if selected_tags:
        results = [
            result
            for result in results
            if any(
                tag in result["job"].career_tags
                for tag in selected_tags
            )
        ]

    results = results[:max_results]

    _render_active_search_queries()

    if results:
        _persist_recommendation_snapshots(
            results,
            profile_fingerprint,
        )

    if not results:
        if mode == "Asgard":
            st.warning("MALP meldet nur primitive Lebensformen.")
        else:
            st.warning("Keine passenden Jobs gefunden.")
        return

    scores = [result["score"] for result in results]

    top_score = max(scores)
    average_score = sum(scores) / len(scores)

    col1, col2, col3 = st.columns(3)

    if mode == "Asgard":
        col1.metric("Missionen", len(results))
        col2.metric("Top-Technologie-Level", top_score)
        col3.metric("Ø Technologie-Level", f"{average_score:.1f}")
    else:
        col1.metric("Treffer", len(results))
        col2.metric("Top Score", top_score)
        col3.metric("Ø Score", f"{average_score:.1f}")

    if mode == "Asgard":
        st.success("Asgard-Protokoll aktiviert.")
        st.subheader("Top Missionen")
    else:
        st.subheader("Top Jobs")

    if mode == "Asgard":
        if top_score >= 100:
            st.success("ASCENSION PROTOCOL AVAILABLE")
        elif top_score >= 95:
            st.error("⚠ ANCIENT TECHNOLOGY DETECTED")

    _render_job_unknown_skill_controls(
        results
    )

    rows = []

    for result in results:
        job = result["job"]

        rows.append(
            {
                "Score": f"{score_icon(result['score'])} {result['score']}",
                "Titel": job.title,
                "Firma": _company_display(job),
                "Quelle": _source_name(job) or "",
                "Suchbegriff": job.query_source or "",
                "Qualifikation": _qualification_state(result),
                "Kompetenz": (
                    f"{round(float(result.get('competency_match_ratio') or 0.0) * 100)}%"
                ),
                "Arbeitsmodell": job.work_model or "",
                "Tags": ", ".join(
                    label_tag(tag)
                    for tag in job.career_tags
                ),
                "Link": job.url or "",
            }
        )

    df = pd.DataFrame(rows)

    st.dataframe(
        df,
        width="stretch",
        hide_index=True,
    )

    st.divider()

    for result in results:
        job = result["job"]

        with st.expander(
            f"{score_icon(result['score'])} "
            f"{result['score']} Punkte · "
            f"{_job_heading(job)}"
        ):
            if job.url:
                st.link_button(
                    "Stellenanzeige öffnen",
                    job.url,
                )

            source_name = _source_name(job)

            if source_name:
                st.caption(
                    f"Quelle: {source_name}"
                )

            if job.query_source:
                st.caption(
                    f"Suchbegriff: {job.query_source}"
                )

            _render_outcome_controls(
                result,
                profile_fingerprint,
            )

            if job.career_tags:
                st.write(
                    "**Tags:** "
                    + ", ".join(
                        label_tag(tag)
                        for tag in job.career_tags
                    )
                )

            _render_qualification_result(
                result
            )

            _render_competency_match(
                result
            )

            _render_job_intelligence(
                result
            )

            if profile_tags:
                matches, missing = compare_tags(
                    profile_tags,
                    job.career_tags,
                )

                total_tags = len(matches) + len(missing)

                if total_tags > 0:
                    match_percentage = round(
                        (len(matches) / total_tags) * 100
                    )
                else:
                    match_percentage = 0

                st.write("**Profil-Match:**")

                st.progress(
                    match_percentage / 100
                )

                st.write(
                    f"Match: {match_percentage}%"
                )

                if matches:
                    st.write(
                        "✅ Passend: "
                        + ", ".join(
                            label_tag(tag)
                            for tag in matches
                        )
                    )

                if missing:
                    st.write(
                        "❌ Nicht erkannt: "
                        + ", ".join(
                            label_tag(tag)
                            for tag in missing
                        )
                    )

            st.write("**Begründung:**")

            for reason in result["reasons"]:
                if reason.startswith("  - "):
                    st.write(
                        "✓ "
                        + reason.replace("  - ", "")
                    )
                else:
                    st.write("• " + reason)

            st.divider()

            if st.button(
                "Bewerbungsmappe vorbereiten",
                key=f"application_{_job_key(job)}",
            ):
                previous_job_key = st.session_state.get(
                    "selected_application_job_key"
                )
                new_job_key = _job_key(job)

                st.session_state[
                    "selected_application_job"
                ] = job
                st.session_state[
                    "selected_application_result"
                ] = result
                st.session_state[
                    "selected_application_job_key"
                ] = new_job_key

                if previous_job_key != new_job_key:
                    st.session_state.pop(
                        "generated_cover_letter",
                        None,
                    )
                    st.session_state.pop(
                        "generated_cover_letter_job_key",
                        None,
                    )

                st.success(
                    "Job für Bewerbungsmappe übernommen."
                )
