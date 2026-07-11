import os

import pandas as pd
import streamlit as st

from jobagent.services.company_aggregation_service import (
    UNKNOWN_COMPANY,
    aggregate_companies,
)
from jobagent.services.company_analysis_pipeline import (
    analyze_company,
)
from jobagent.services.company_concept_normalizer import (
    canonicalize_company_concepts,
    extract_company_concepts,
)
from jobagent.services.company_match_service import (
    match_companies,
    prioritize_known_companies,
)
from jobagent.services.company_profile_match_service import (
    match_company_to_profile,
)
from jobagent.services.company_pipeline_inspector import (
    inspect_company,
)
from jobagent.services.company_profile_loader import (
    load_company_profiles,
)
from jobagent.services.company_fetch_service import (
    fetch_company_with_summary,
)
from jobagent.services.company_evidence_service import (
    list_company_evidence,
)
from jobagent.services.company_knowledge_builder import (
    build_company_knowledge,
    load_latest_company_knowledge_draft,
)
from jobagent.services.company_knowledge_review_service import (
    review_company_knowledge_draft,
)
from jobagent.services.ollama_client import (
    OllamaClient,
)
from jobagent.services.company_recommendation_service import (
    deactivate_tracked_company,
    get_recommended_companies,
    get_tracked_companies,
    track_recommended_company,
)
from jobagent.services.company_relationship_service import (
    list_company_relationships,
)
from jobagent.services.company_source_service import (
    list_documents,
    list_company_sources,
    load_latest_document,
)
from jobagent.services.company_match_report_service import (
    company_match_report_key,
    generate_company_match_report,
)
from jobagent.services.company_ground_truth_service import (
    GROUND_TRUTH_TOPICS,
    USER_ASSESSMENTS,
    add_ground_truth_review,
    calculate_ground_truth_accuracy,
    ensure_xox_ground_truth_company,
    list_ground_truth_reviews,
    mark_company_as_ground_truth,
)
from jobagent.services.job_service import (
    build_runtime_profile,
    build_runtime_search_queries,
    load_and_rank_jobs,
)
from jobagent.services.label_service import (
    get_label,
)
from jobagent.services.skill_candidate_domain_service import (
    normalize_domain_text,
)
from jobagent.repositories.company_repository import (
    CompanyRepository,
)


def _available_ollama_models(client: OllamaClient | None = None) -> list[str]:
    try:
        return (client or OllamaClient()).list_models()
    except Exception:
        return []


def _selected_ollama_model() -> str | None:
    selected = st.session_state.get(
        "companyhub_ollama_model"
    )

    if selected:
        return str(
            selected
        )

    return None


def _render_ollama_model_selection() -> str | None:
    models = _available_ollama_models()

    if not models:
        st.info(
            "Ollama ist nicht erreichbar oder es sind keine Modelle verfügbar. "
            "Knowledge Reviews fallen auf Rule Based zurück."
        )
        st.session_state.pop(
            "companyhub_ollama_model",
            None,
        )
        return None

    preferred = (
        st.session_state.get("companyhub_ollama_model")
        or os.getenv("OLLAMA_MODEL")
        or os.getenv("COMPANYHUB_OLLAMA_MODEL")
    )
    default_index = (
        models.index(preferred)
        if preferred in models
        else 0
    )

    selected = st.selectbox(
        "Ollama Modell",
        options=models,
        index=default_index,
        key="companyhub_ollama_model",
    )

    return str(selected) if selected else None


def _cached_job_results():
    cached = st.session_state.get(
        "job_results_cache"
    )

    if isinstance(cached, dict):
        return cached.get(
            "results"
        )

    return None


def _load_company_job_results(
    min_score: int,
    profile_tags,
    profile_preferences,
):
    search_queries = build_runtime_search_queries(
        profile_skills=profile_tags,
        profile_preferences=profile_preferences,
    )
    results = load_and_rank_jobs(
        min_score=min_score,
        profile_skills=profile_tags,
        search_queries=search_queries,
        profile_preferences=profile_preferences,
    )

    st.session_state["profile_search_queries"] = search_queries
    st.session_state["query_sources"] = search_queries
    st.session_state["job_results_cache"] = {
        "min_score": min_score,
        "profile_fingerprint": st.session_state.get(
            "active_profile_fingerprint"
        ),
        "query_fingerprint": None,
        "preferences_fingerprint": None,
        "queries": search_queries,
        "results": results,
    }

    return results


def _label_values(values, limit: int = 12) -> str:
    labels = [
        get_label(value)
        for value in values or []
        if str(value).strip()
    ][:limit]

    return ", ".join(labels) if labels else "-"


def _claim_options_from_company(company) -> list[str]:
    options = []

    for label, values in (
        ("Schwerpunkt", getattr(company, "focus_areas", [])),
        ("Einsatzfeld", getattr(company, "possible_use_cases", [])),
        ("Skill", getattr(company, "detected_skills", [])),
        ("Kompetenz", getattr(company, "detected_competencies", [])),
        (
            "Qualifikationsanforderung",
            getattr(company, "qualification_requirements", []),
        ),
    ):
        options.extend(
            f"{label}: {value}"
            for value in values or []
            if str(value).strip()
        )

    if getattr(company, "description", ""):
        options.append(
            f"Beschreibung: {company.description[:160]}"
        )

    return options or [
        "Manuelle Aussage"
    ]


def _render_ground_truth_review(
    company_id,
    company_name: str,
    claims: list[str],
    key_prefix: str,
    ground_truth_available: bool = False,
    relationship_status: str | None = None,
) -> None:
    with st.expander(
        "Ground Truth Review",
        expanded=ground_truth_available,
    ):
        if ground_truth_available:
            st.caption(
                f"{company_name}: {relationship_status or 'Ground Truth verfuegbar'}"
            )
        else:
            st.caption(
                "Unternehmen fuer manuell pruefbare Aussagen markieren."
            )

        if isinstance(company_id, int) and st.button(
            "Als Ground Truth markieren",
            key=f"{key_prefix}_mark_ground_truth",
            disabled=ground_truth_available,
        ):
            mark_company_as_ground_truth(
                company_id=company_id,
            )
            st.success(
                "Ground Truth fuer dieses Unternehmen aktiviert."
            )
            st.rerun()

        selected_claim = st.selectbox(
            "Aussage",
            claims,
            key=f"{key_prefix}_claim",
        )
        custom_claim = st.text_area(
            "Aussage konkretisieren",
            key=f"{key_prefix}_custom_claim",
        )
        topic = st.selectbox(
            "Thema",
            GROUND_TRUTH_TOPICS,
            key=f"{key_prefix}_topic",
        )
        system_assessment = st.text_area(
            "Systemeinschaetzung",
            value=selected_claim,
            key=f"{key_prefix}_system_assessment",
        )
        user_assessment = st.radio(
            "Bewertung",
            USER_ASSESSMENTS,
            horizontal=True,
            key=f"{key_prefix}_user_assessment",
        )
        user_comment = st.text_area(
            "Kommentar",
            key=f"{key_prefix}_user_comment",
        )
        confidence = st.slider(
            "Sicherheit",
            0.0,
            1.0,
            0.5,
            0.05,
            key=f"{key_prefix}_confidence",
        )

        if st.button(
            "Review speichern",
            key=f"{key_prefix}_save_review",
        ):
            add_ground_truth_review(
                company_id=company_id,
                topic=topic,
                claim=custom_claim.strip() or selected_claim,
                system_assessment=system_assessment,
                user_assessment=user_assessment,
                user_comment=user_comment,
                confidence=confidence,
            )
            st.success(
                "Ground Truth Review gespeichert."
            )
            st.rerun()

        summary = calculate_ground_truth_accuracy(
            company_id
        )
        st.caption(
            "Reviews: "
            f"{summary['total_reviews']} | bewertet: "
            f"{summary['rated_reviews']} | unbekannt: "
            f"{summary['unknown_count']}"
        )
        if summary["accuracy"] is not None:
            st.caption(
                f"Ground-Truth-Accuracy: {summary['accuracy']:.0%}"
            )

        reviews = list_ground_truth_reviews(
            company_id
        )
        for review in reviews[:5]:
            st.write(
                f"- {review.topic}: {review.user_assessment} - {review.claim}"
            )


def _active_profile_fingerprint() -> str:
    return str(
        st.session_state.get(
            "active_profile_fingerprint"
        )
        or "default"
    )


def _render_companyhub_dashboard(profile) -> None:
    profile_fingerprint = _active_profile_fingerprint()
    profile_tags = st.session_state.get(
        "profile_tags",
        set(),
    )
    profile_preferences = st.session_state.get(
        "profile_preferences",
        {},
    )

    if profile is None and profile_tags:
        profile = build_runtime_profile(
            profile_skills=profile_tags,
            profile_preferences=profile_preferences,
        )

    recommendations = get_recommended_companies(
        profile
    )

    st.subheader("CompanyHub")
    st.caption(
        "Empfohlene Unternehmen können dauerhaft beobachtet werden. "
        "Crawler, News und LLM-Analyse kommen später."
    )

    fetch_summary = st.session_state.pop(
        "companyhub_fetch_summary",
        None,
    )
    if fetch_summary:
        st.success(
            fetch_summary
        )
    analysis_summary = st.session_state.pop(
        "companyhub_analysis_summary",
        None,
    )
    if analysis_summary:
        st.success(
            analysis_summary
        )
    analysis_warning = st.session_state.pop(
        "companyhub_analysis_warning",
        None,
    )
    if analysis_warning:
        st.warning(
            analysis_warning
        )
    knowledge_summary = st.session_state.pop(
        "companyhub_knowledge_summary",
        None,
    )
    if knowledge_summary:
        st.success(
            knowledge_summary
        )
    profile_match_summary = st.session_state.pop(
        "companyhub_profile_match_summary",
        None,
    )
    if profile_match_summary:
        st.success(
            profile_match_summary
        )

    selected_ollama_model = _render_ollama_model_selection()

    st.markdown("**Empfohlene Unternehmen**")

    header = st.columns(
        [0.8, 2.0, 1.4, 3.0, 2.0, 1.2]
    )
    header[0].caption("Priorität")
    header[1].caption("Unternehmen")
    header[2].caption("Branche")
    header[3].caption("Grund")
    header[4].caption("Tags")
    header[5].caption("Aktion")

    for recommendation in recommendations:
        columns = st.columns(
            [0.8, 2.0, 1.4, 3.0, 2.0, 1.2]
        )
        columns[0].write(
            recommendation.priority
        )
        columns[1].write(
            recommendation.name
        )
        columns[2].write(
            recommendation.industry or "-"
        )
        columns[3].write(
            recommendation.reason
        )
        columns[4].write(
            ", ".join(recommendation.tags) or "-"
        )

        if columns[5].button(
            "Beobachten",
            key=(
                "companyhub_track_"
                + normalize_domain_text(recommendation.name).replace(" ", "_")
            ),
            disabled=not recommendation.tracking_enabled,
        ):
            track_recommended_company(
                recommended_company=recommendation,
                profile_fingerprint=profile_fingerprint,
            )
            st.rerun()

    st.markdown("**Meine Unternehmen**")

    if st.button(
        "Example Foods Ground Truth anlegen",
        key="companyhub_seed_xox_ground_truth",
    ):
        xox = ensure_xox_ground_truth_company()
        CompanyRepository().track_company(
            company_id=xox.id,
            profile_fingerprint=profile_fingerprint,
            priority=1,
            notes="Ehemaliger Arbeitgeber / Ground Truth verfuegbar.",
        )
        st.success(
            "Example Foods wurde als Ground-Truth-Unternehmen angelegt."
        )
        st.rerun()

    tracked_companies = get_tracked_companies(
        profile_fingerprint
    )

    if not tracked_companies:
        st.info(
            "Noch keine Unternehmen beobachtet."
        )
        return

    tracked_header = st.columns(
        [2.2, 1.0, 3.0, 0.9, 1.4]
    )
    tracked_header[0].caption("Unternehmen")
    tracked_header[1].caption("Priorität")
    tracked_header[2].caption("Notiz")
    tracked_header[3].caption("Aktiv")
    tracked_header[4].caption("Aktion")

    for tracked in tracked_companies:
        columns = st.columns(
            [2.2, 1.0, 3.0, 0.9, 1.4]
        )
        columns[0].write(
            tracked.get("name") or "-"
        )
        columns[1].write(
            tracked.get("priority") or "-"
        )
        columns[2].write(
            tracked.get("notes") or "-"
        )
        columns[3].write(
            "Ja" if tracked.get("active") else "Nein"
        )

        if columns[4].button(
            "Nicht mehr beobachten",
            key=f"companyhub_deactivate_{tracked.get('company_id')}",
        ):
            deactivate_tracked_company(
                company_id=tracked["company_id"],
                profile_fingerprint=profile_fingerprint,
            )
            st.rerun()

        action_columns = st.columns(
            [1.3, 1.4, 4.0]
        )
        if action_columns[0].button(
            "Quellen abrufen",
            key=f"companyhub_fetch_sources_{tracked.get('company_id')}",
        ):
            with st.spinner(
                "Quellen werden abgerufen..."
            ):
                summary = fetch_company_with_summary(
                    tracked["company_id"]
                )
            st.session_state["companyhub_fetch_summary"] = summary.message()
            st.rerun()

        tracked_claims = [
            claim
            for claim in (
                f"Branche: {tracked.get('industry')}"
                if tracked.get("industry")
                else "",
                f"Notiz: {tracked.get('notes')}"
                if tracked.get("notes")
                else "",
                f"Status: {tracked.get('status')}"
                if tracked.get("status")
                else "",
            )
            if claim
        ]
        try:
            evidence_items = list_company_evidence(
                company_id=tracked["company_id"]
            )
        except Exception:
            evidence_items = []
        tracked_claims.extend(
            f"Evidence: {item.title or item.text[:120]}"
            for item in evidence_items[:8]
            if (item.title or item.text)
        )
        _render_ground_truth_review(
            company_id=tracked["company_id"],
            company_name=tracked.get("name") or "Unternehmen",
            claims=tracked_claims or ["Manuelle Aussage"],
            key_prefix=f"companyhub_gt_{tracked.get('company_id')}",
            ground_truth_available=bool(
                tracked.get("ground_truth_available")
            ),
            relationship_status=tracked.get("relationship_status"),
        )

        if action_columns[1].button(
            "Alle Dokumente anzeigen",
            key=f"companyhub_show_documents_{tracked.get('company_id')}",
        ):
            st.session_state[
                f"companyhub_documents_visible_{tracked.get('company_id')}"
            ] = True

        if action_columns[2].button(
            "Evidenz erzeugen",
            key=f"companyhub_analyze_documents_{tracked.get('company_id')}",
        ):
            with st.spinner(
                "Dokumente werden analysiert..."
            ):
                summary = analyze_company(
                    tracked["company_id"]
                )
            evidence_total = (
                summary.evidence_created
                + summary.evidence_updated
                + summary.evidence_unchanged
            )
            st.session_state["companyhub_analysis_summary"] = summary.message()
            if summary.documents_processed and evidence_total == 0:
                st.session_state["companyhub_analysis_warning"] = (
                    "Dokumente vorhanden, aber kein verwertbarer Text erkannt "
                    "oder keine Evidence erzeugt."
                )
            st.rerun()

        if st.button(
            "Profil-Match berechnen",
            key=f"companyhub_profile_match_{tracked.get('company_id')}",
        ):
            match = match_company_to_profile(
                tracked["company_id"],
                profile=profile,
                profile_fingerprint=profile_fingerprint,
            )
            st.session_state["companyhub_profile_match_summary"] = (
                f"Profil-Match berechnet: {match.total_score}/100, "
                f"Confidence {match.confidence:.2f}."
            )
            st.rerun()

        with st.expander(
            f"Company Match: {tracked.get('name') or 'Unternehmen'}",
            expanded=False,
        ):
            latest_match = CompanyRepository().load_latest_company_profile_match(
                tracked["company_id"],
                profile_fingerprint,
            )

            if latest_match is None:
                st.caption(
                    "Noch kein Profil-Match berechnet."
                )
            else:
                st.write(
                    f"**Gesamt Score:** {latest_match.total_score}/100"
                )
                st.write(
                    f"**Mission:** {latest_match.mission_score}"
                )
                st.write(
                    f"**Domänen:** {latest_match.domain_score}"
                )
                st.write(
                    f"**Technologie:** {latest_match.technology_score}"
                )
                st.write(
                    f"**Arbeitsmodell:** {latest_match.work_model_score}"
                )
                st.write(
                    f"**KRITIS:** {latest_match.kritis_score}"
                )
                st.write(
                    f"**Exclusions:** {latest_match.exclusion_score}"
                )
                st.write(
                    f"**Confidence:** {latest_match.confidence:.2f}"
                )
                st.write(
                    "**Matched Concepts:** "
                    + (", ".join(latest_match.matched_concepts) or "-")
                )
                if latest_match.risk_flags:
                    st.warning(
                        "Risiken: " + "; ".join(latest_match.risk_flags)
                    )
                if latest_match.missing_profile_preferences:
                    st.caption(
                        "Fehlende Präferenzen: "
                        + ", ".join(latest_match.missing_profile_preferences)
                    )
                if latest_match.reasons:
                    st.write("**Gründe:**")
                    for reason in latest_match.reasons:
                        st.write(
                            f"- {reason}"
                        )

        if st.button(
            "Knowledge Draft erzeugen",
            key=f"companyhub_build_knowledge_{tracked.get('company_id')}",
        ):
            draft = build_company_knowledge(
                tracked["company_id"]
            )
            st.session_state["companyhub_knowledge_summary"] = (
                f"Knowledge Draft erzeugt: {draft.evidence_count} Evidence, "
                f"Confidence {draft.confidence:.2f}."
            )
            st.rerun()

        if st.button(
            "Knowledge Draft prüfen / verbessern",
            key=f"companyhub_review_knowledge_{tracked.get('company_id')}",
        ):
            llm_client = (
                OllamaClient(
                    default_model=selected_ollama_model,
                )
                if selected_ollama_model
                else None
            )
            draft = review_company_knowledge_draft(
                tracked["company_id"],
                llm_client=llm_client,
            )
            st.session_state["companyhub_knowledge_summary"] = (
                f"Knowledge Draft geprüft: {draft.evidence_count} Evidence, "
                f"Confidence {draft.confidence:.2f}, {draft.review_method}."
            )
            st.rerun()

        with st.expander(
            f"Quellen: {tracked.get('name') or 'Unternehmen'}",
            expanded=False,
        ):
            sources = list_company_sources(
                company_id=tracked["company_id"]
            )

            if not sources:
                st.caption(
                    "Noch keine Quellen hinterlegt."
                )
            else:
                rows = []

                for source in sources:
                    latest_document = load_latest_document(
                        source.id
                    )
                    rows.append(
                        {
                            "Quelle": source.title,
                            "Typ": str(
                                source.source_type.value
                                if hasattr(source.source_type, "value")
                                else source.source_type
                            ),
                            "Aktiv": "Ja" if source.enabled else "Nein",
                            "Priorität": source.priority,
                            "Letzter Abruf": (
                                latest_document.fetched_at
                                if latest_document
                                else source.last_checked or "-"
                            ),
                            "Status": (
                                latest_document.status_code
                                if latest_document
                                else "-"
                            ),
                            "Hash": (
                                "Ja"
                                if latest_document
                                and latest_document.content_hash
                                else "Nein"
                            ),
                            "Content Size": (
                                latest_document.content_size
                                if latest_document
                                else "-"
                            ),
                            "URL": source.url,
                        }
                    )

                st.dataframe(
                    pd.DataFrame(
                        rows
                    ),
                    width="stretch",
                    hide_index=True,
                )

        if st.session_state.get(
            f"companyhub_documents_visible_{tracked.get('company_id')}"
        ):
            with st.expander(
                f"Dokumente: {tracked.get('name') or 'Unternehmen'}",
                expanded=True,
            ):
                documents = list_documents(
                    company_id=tracked["company_id"]
                )

                if not documents:
                    st.caption(
                        "Noch keine Dokumente abgerufen."
                    )
                else:
                    previous_hash_by_source = {}
                    change_labels_by_document = {}

                    for document in reversed(
                        documents
                    ):
                        previous_hash = previous_hash_by_source.get(
                            document.source_id
                        )

                        if not document.content_hash:
                            label = "-"
                        elif previous_hash is None:
                            label = "NEW"
                        elif previous_hash == document.content_hash:
                            label = "Unverändert"
                        else:
                            label = "Aktualisiert"

                        change_labels_by_document[document.id] = label
                        previous_hash_by_source[
                            document.source_id
                        ] = document.content_hash

                    st.dataframe(
                        pd.DataFrame(
                            [
                                {
                                    "Quelle": document.title or document.url,
                                    "Zeitpunkt": document.fetched_at,
                                    "Status": document.status_code,
                                    "Änderung": change_labels_by_document.get(
                                        document.id,
                                        "-",
                                    ),
                                    "Content Size": document.content_size,
                                    "Hash": document.content_hash or "-",
                                    "Content Type": (
                                        document.content_type or "-"
                                    ),
                                    "MIME Type": document.mime_type or "-",
                                }
                                for document in documents
                            ]
                        ),
                        width="stretch",
                        hide_index=True,
                    )

                    for document in documents:
                        if st.button(
                            f"Vorschau: {document.title or document.url}",
                            key=f"companyhub_preview_document_{document.id}",
                        ):
                            st.text_area(
                                "Vorschau",
                                (document.content_text or "")[:1000]
                                or "Kein Textinhalt gespeichert.",
                                height=240,
                                key=(
                                    "companyhub_preview_text_"
                                    f"{document.id}"
                                ),
                            )

            with st.expander(
                f"Evidence: {tracked.get('name') or 'Unternehmen'}",
                expanded=False,
            ):
                evidence_items = list_company_evidence(
                    company_id=tracked["company_id"]
                )

                if not evidence_items:
                    st.caption(
                        "Keine Evidence hinterlegt."
                    )
                else:
                    grouped_counts = {}

                    for evidence in evidence_items:
                        grouped_counts[evidence.evidence_type] = (
                            grouped_counts.get(
                                evidence.evidence_type,
                                0,
                            )
                            + 1
                        )

                    st.dataframe(
                        pd.DataFrame(
                            [
                                {
                                    "Typ": evidence_type,
                                    "Anzahl": count,
                                }
                                for evidence_type, count in sorted(
                                    grouped_counts.items()
                                )
                            ]
                        ),
                        width="stretch",
                        hide_index=True,
                    )
                    st.dataframe(
                        pd.DataFrame(
                            [
                                {
                                    "Typ": evidence.evidence_type,
                                    "Titel": evidence.title or "-",
                                    "Text": evidence.text[:200],
                                    "Quelle": evidence.source_name or "-",
                                    "Confidence": evidence.confidence,
                                }
                                for evidence in evidence_items
                            ]
                        ),
                        width="stretch",
                        hide_index=True,
                    )

            with st.expander(
                f"Canonical Concepts: {tracked.get('name') or 'Unternehmen'}",
                expanded=False,
            ):
                evidence_items = list_company_evidence(
                    company_id=tracked["company_id"]
                )
                concepts = canonicalize_company_concepts(
                    [
                        concept
                        for evidence in evidence_items
                        for concept in extract_company_concepts(
                            evidence
                        )
                    ]
                )

                if not concepts:
                    st.caption(
                        "Keine canonical concepts erkannt."
                    )
                else:
                    st.dataframe(
                        pd.DataFrame(
                            [
                                {
                                    "Concept Type": concept.concept_type,
                                    "Raw Value": concept.raw_value,
                                    "Canonical Value": concept.canonical_value,
                                    "Confidence": concept.confidence,
                                    "Quelle": concept.source_type or "-",
                                }
                                for concept in concepts
                            ]
                        ),
                        width="stretch",
                        hide_index=True,
                    )

            with st.expander(
                f"Knowledge Draft: {tracked.get('name') or 'Unternehmen'}",
                expanded=False,
            ):
                draft = load_latest_company_knowledge_draft(
                    tracked["company_id"]
                )

                if draft is None:
                    st.caption(
                        "Kein Knowledge Draft vorhanden."
                    )
                else:
                    st.write(
                        f"**Mission:** {draft.mission or '-'}"
                    )
                    st.write(
                        f"**Vision:** {draft.vision or '-'}"
                    )
                    st.write(
                        "**Mission Keywords:** "
                        + (", ".join(draft.mission_keywords) or "-")
                    )
                    st.write(
                        "**Business Domains:** "
                        + (", ".join(draft.business_domains) or "-")
                    )
                    st.write(
                        "**Technologien:** "
                        + (", ".join(draft.technologies) or "-")
                    )
                    st.write(
                        "**Benefits:** "
                        + (", ".join(draft.benefits) or "-")
                    )
                    st.write(
                        "**Work Models:** "
                        + (", ".join(draft.work_models) or "-")
                    )
                    st.write(
                        f"**Evidence Count:** {draft.evidence_count}"
                    )
                    if draft.canonical_concepts:
                        st.write(
                            "**Canonical Concepts:** "
                            + ", ".join(draft.canonical_concepts)
                        )
                    if draft.concept_statistics:
                        st.write(
                            f"**Concept Statistics:** {draft.concept_statistics}"
                        )
                    st.write(
                        f"**Confidence:** {draft.confidence:.2f}"
                    )
                    st.write(
                        f"**Review:** {draft.review_method}"
                    )
                    if getattr(draft, "review_model", None):
                        st.write(
                            f"**Modell:** {draft.review_model}"
                        )

            with st.expander(
                f"Pipeline Inspector: {tracked.get('name') or 'Unternehmen'}",
                expanded=False,
            ):
                report = inspect_company(
                    tracked["company_id"]
                )

                if report.warnings:
                    for warning in report.warnings:
                        st.warning(
                            warning
                        )

                if report.errors:
                    for error in report.errors:
                        st.error(
                            error
                        )

                st.write(
                    f"**Sources:** {len(report.sources)}"
                )
                st.write(
                    f"**Dokumente:** {len(report.documents)}"
                )
                st.write(
                    f"**Evidence Count:** {report.evidence_count}"
                )
                st.write(
                    "**Knowledge Draft:** "
                    + ("vorhanden" if report.knowledge_draft_exists else "fehlt")
                )
                st.write(
                    f"**Review:** {report.review_method or '-'}"
                    + (
                        f" ({report.review_model})"
                        if report.review_model
                        else ""
                    )
                )

                if report.sources:
                    st.dataframe(
                        pd.DataFrame(report.sources),
                        width="stretch",
                        hide_index=True,
                    )

                if report.documents:
                    document_rows = []

                    for document in report.documents:
                        document_id = document.get("id")
                        document_rows.append(
                            {
                                "Dokument": document_id,
                                "Quelle": document.get("title") or document.get("url"),
                                "Status": document.get("status_code"),
                                "Content Size": document.get("content_size"),
                                "Clean Text Länge": report.clean_text_lengths.get(
                                    document_id,
                                    0,
                                ),
                                "MIME Type": document.get("mime_type") or "-",
                            }
                        )

                    st.dataframe(
                        pd.DataFrame(document_rows),
                        width="stretch",
                        hide_index=True,
                    )

                    for document in report.documents:
                        document_id = document.get("id")
                        processing_result = report.processing_results.get(
                            document_id
                        )

                        if not processing_result:
                            continue

                        if st.button(
                            f"Clean Text anzeigen: {document.get('title') or document.get('url')}",
                            key=f"companyhub_pipeline_clean_text_{document_id}",
                        ):
                            st.text_area(
                                "Clean Text",
                                (processing_result.clean_text or "")[:2000]
                                or "Kein Clean Text verfügbar.",
                                height=280,
                                key=f"companyhub_pipeline_clean_text_area_{document_id}",
                            )

                if report.evidence_by_type:
                    st.dataframe(
                        pd.DataFrame(
                            [
                                {
                                    "Typ": evidence_type,
                                    "Anzahl": count,
                                }
                                for evidence_type, count in sorted(
                                    report.evidence_by_type.items()
                                )
                            ]
                        ),
                        width="stretch",
                        hide_index=True,
                    )

                if report.concept_types:
                    st.dataframe(
                        pd.DataFrame(
                            [
                                {
                                    "Concept Type": concept_type,
                                    "Anzahl": count,
                                }
                                for concept_type, count in sorted(
                                    report.concept_types.items()
                                )
                            ]
                        ),
                        width="stretch",
                        hide_index=True,
                    )

                if report.canonical_concepts:
                    st.dataframe(
                        pd.DataFrame(
                            [
                                {
                                    "Canonical Concept": concept,
                                }
                                for concept in report.canonical_concepts
                            ]
                        ),
                        width="stretch",
                        hide_index=True,
                    )

                if report.unknown_concepts:
                    st.write(
                        "**Unknown Concepts:** "
                        + ", ".join(report.unknown_concepts)
                    )

                inspector_evidence_items = list_company_evidence(
                    company_id=tracked["company_id"]
                )

                if inspector_evidence_items:
                    st.dataframe(
                        pd.DataFrame(
                            [
                                {
                                    "Typ": evidence.evidence_type,
                                    "Confidence": evidence.confidence,
                                    "Text": evidence.text[:300],
                                    "Quelle": evidence.source_name or evidence.source_url or "-",
                                }
                                for evidence in inspector_evidence_items
                            ]
                        ),
                        width="stretch",
                        hide_index=True,
                    )

                if draft is not None:
                    st.write(
                        f"**Mission:** {draft.mission or '-'}"
                    )
                    st.write(
                        f"**Vision:** {draft.vision or '-'}"
                    )
                    st.write(
                        "**Benefits:** "
                        + (", ".join(draft.benefits) or "-")
                    )
                    st.write(
                        "**Technologien:** "
                        + (", ".join(draft.technologies) or "-")
                    )

        with st.expander(
            f"Unternehmensverflechtungen: {tracked.get('name') or 'Unternehmen'}",
            expanded=False,
        ):
            relationships = list_company_relationships(
                company_id=tracked["company_id"]
            )

            if not relationships:
                st.caption(
                    "Keine Unternehmensverflechtungen hinterlegt."
                )
            else:
                st.dataframe(
                    pd.DataFrame(
                        [
                            {
                                "Beziehung": relationship.relationship_type,
                                "Verbundenes Unternehmen": (
                                    relationship.related_company_name
                                ),
                                "Richtung": relationship.direction,
                                "Quelle": relationship.source or "-",
                                "Confidence": relationship.confidence,
                                "Evidenz": relationship.evidence_text or "-",
                            }
                            for relationship in relationships
                        ]
                    ),
                    width="stretch",
                    hide_index=True,
                )


def _company_rows(results):
    rows = []

    for result in results:
        company = result.company
        rows.append(
            {
                "Score": result.total_score,
                "Firma": company.name,
                "Jobs": len(company.jobs),
                "Rollen": result.role_opportunity_score,
                "Skills": result.skill_coverage_score,
                "Kompetenzen": result.competency_coverage_score,
                "Strategie": result.strategic_fit_score,
                "Praeferenzen": result.preference_score,
                "Risiken": len(result.risk_flags),
                "Empfehlung": result.application_recommendation,
                "Quelle": company.source_name or "Jobpool",
                "Arbeitsmodelle": ", ".join(company.work_models) or "-",
                "Standorte": ", ".join(company.locations[:3]) or "-",
            }
        )

    return rows


def _render_company_result(result, profile) -> None:
    company = result.company
    report_key = company_match_report_key(
        result
    )

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric(
        "Gesamt-Score",
        result.total_score,
    )
    col2.metric(
        "Rollen",
        result.role_opportunity_score,
    )
    col3.metric(
        "Skills",
        result.skill_coverage_score,
    )
    col4.metric(
        "Kompetenzen",
        result.competency_coverage_score,
    )
    col5.metric(
        "Strategie",
        result.strategic_fit_score,
    )

    st.write(
        f"**Praeferenz-Score:** {result.preference_score}"
    )
    st.write(
        f"**Empfehlung:** {result.application_recommendation}"
    )

    if company.source_type:
        st.caption(
            f"Quelle: {company.source_name or company.source_type}"
        )

    if st.button(
        "Als Initiativziel vormerken",
        key=(
            "select_company_match_"
            + normalize_domain_text(company.name).replace(" ", "_")
        ),
    ):
        st.session_state["selected_company_match"] = result
        st.success(
            f"{company.name} wurde als Company Match vorgemerkt."
        )

    if st.button(
        "Company Match Report erzeugen",
        key=(
            "company_match_report_"
            + normalize_domain_text(company.name).replace(" ", "_")
        ),
    ):
        report = generate_company_match_report(
            result,
            profile,
        )
        reports = st.session_state.setdefault(
            "company_match_reports",
            {},
        )
        reports[report_key] = report
        st.session_state["selected_company_match_report"] = report
        st.session_state["selected_company_match_report_key"] = report_key
        st.success(
            "Company Match Report erzeugt."
        )

    report = st.session_state.get(
        "company_match_reports",
        {},
    ).get(report_key)

    if report:
        with st.expander(
            "Company Match Report anzeigen",
            expanded=True,
        ):
            st.markdown(
                report
            )

    if result.reasons:
        st.write("**Gruende:**")

        for reason in result.reasons:
            st.write(
                f"- {reason}"
            )

    if result.risk_flags:
        st.warning(
            "Risiken oder moegliche Ausschluesse erkannt."
        )

        for flag in result.risk_flags:
            st.write(
                f"- {flag}"
            )

    st.write(
        f"**Erkannte Skills:** {_label_values(company.detected_skills)}"
    )
    st.write(
        "**Erkannte Kompetenzen:** "
        + _label_values(company.detected_competencies)
    )

    if company.focus_areas:
        st.write(
            "**Schwerpunkte:** " + _label_values(company.focus_areas)
        )

    if company.possible_use_cases:
        st.write(
            "**Moegliche Einsatzfelder:** "
            + _label_values(company.possible_use_cases)
        )

    st.write(
        "**Qualifikationsanforderungen:** "
        + _label_values(company.qualification_requirements)
    )

    if company.company_intel.kununu_rating is not None:
        st.caption(
            f"Kununu: {company.company_intel.kununu_rating}"
        )

    _render_ground_truth_review(
        company_id=normalize_domain_text(company.name).replace(" ", "_"),
        company_name=company.name,
        claims=_claim_options_from_company(company),
        key_prefix=(
            "company_match_gt_"
            + normalize_domain_text(company.name).replace(" ", "_")
        ),
        ground_truth_available=bool(
            getattr(company, "ground_truth_available", False)
        ),
        relationship_status=getattr(
            company,
            "relationship_status",
            None,
        ),
    )

    with st.expander(
        "Passende Jobs als Einstiegspunkte anzeigen",
        expanded=True,
    ):
        for job in result.matching_jobs:
            st.write(
                f"**{job.title}**"
            )
            details = [
                job.location,
                job.work_model,
                job.query_source,
            ]
            st.caption(
                " | ".join(
                    str(detail)
                    for detail in details
                    if detail
                )
                or "Keine weiteren Details"
            )

            if job.url:
                st.link_button(
                    "Stellenanzeige oeffnen",
                    job.url,
            )


def render_company_tab(
    min_score: int,
    max_results: int,
):
    profile_tags = st.session_state.get(
        "profile_tags",
        set(),
    )
    profile_preferences = st.session_state.get(
        "profile_preferences",
        {},
    )

    _render_companyhub_dashboard(
        profile=None
    )
    st.divider()
    st.subheader("Company Match")

    if not profile_tags:
        st.warning(
            "Noch kein Profil erstellt. Bitte zuerst im Profil-Tab "
            "Kompetenzen laden oder aktivieren."
        )
        return

    unknown_company_mode = st.radio(
        "Firmen ohne Arbeitgebername",
        [
            "Ans Ende sortieren",
            "Ausblenden",
        ],
        horizontal=True,
        key="company_match_unknown_company_mode",
    )
    include_manual_profiles = st.checkbox(
        "Manuelle CompanyProfiles laden",
        value=False,
        key="company_match_include_manual_profiles",
    )
    manual_profiles = (
        load_company_profiles()
        if include_manual_profiles
        else []
    )

    if include_manual_profiles:
        st.caption(
            f"{len(manual_profiles)} manuelle CompanyProfile(s) geladen."
        )

    job_results = _cached_job_results()

    if not job_results and not manual_profiles:
        st.info(
            "Es sind noch keine Job-Ergebnisse geladen. "
            "Company Match nutzt denselben Jobpool wie das Job Matching."
        )

        if not st.button(
            "Jobpool laden und Firmen matchen",
            key="company_match_load_jobs",
        ):
            return

        with st.spinner(
            "Lade Jobpool und aggregiere Firmen..."
        ):
            job_results = _load_company_job_results(
                min_score,
                profile_tags,
                profile_preferences,
            )

    if job_results is None:
        job_results = []

    if st.button(
        "Company Match aktualisieren",
        key="company_match_refresh",
    ):
        with st.spinner(
            "Aktualisiere Company Match..."
        ):
            job_results = _load_company_job_results(
                min_score,
                profile_tags,
                profile_preferences,
            )

    profile = build_runtime_profile(
        profile_skills=profile_tags,
        profile_preferences=profile_preferences,
    )
    companies = aggregate_companies(
        job_results
    )
    companies.extend(
        manual_profiles
    )
    results = match_companies(
        companies,
        profile,
    )

    if unknown_company_mode == "Ausblenden":
        results = [
            result
            for result in results
            if result.company.name != UNKNOWN_COMPANY
        ]
    else:
        results = prioritize_known_companies(
            results
        )

    results = results[:max_results]

    if not results:
        st.warning(
            "Keine Firmen aus dem aktuellen Jobpool aggregiert."
        )
        return

    st.caption(
        f"{len(companies)} Firma/Firmen aus {len(job_results)} "
        "Job-Ergebnissen aggregiert."
    )

    st.dataframe(
        pd.DataFrame(
            _company_rows(results)
        ),
        width="stretch",
        hide_index=True,
    )

    st.divider()

    for result in results:
        with st.expander(
            f"{result.total_score} Punkte - {result.company.name}"
        ):
            _render_company_result(
                result,
                profile,
            )
