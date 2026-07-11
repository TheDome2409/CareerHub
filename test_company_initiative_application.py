import pytest

from jobagent.services import application_service


def test_company_initiative_letter_uses_company_context(monkeypatch):
    captured = {}

    def fake_chat(**kwargs):
        captured.update(kwargs)

        return {
            "message": {
                "content": (
                    " an Ihrem Unternehmen reizt mich die Verbindung "
                    "aus Digitalisierung und Projektverantwortung."
                )
            }
        }

    monkeypatch.setattr(
        application_service,
        "chat",
        fake_chat,
    )

    letter = application_service.generate_company_initiative_letter(
        company_name="CareerHub GmbH",
        profile_tags=[
            "project_management",
            "digitalization",
        ],
        company_context=(
            "Erkannte Skills: project_management, digitalization"
        ),
    )

    prompt_text = "\n".join(
        message["content"]
        for message in captured["messages"]
    )

    assert "CareerHub GmbH" in prompt_text
    assert "project_management" in prompt_text
    assert "konkrete Stellenanzeige" in prompt_text
    assert "Erfinde keine Faehigkeiten" in prompt_text
    assert "Erfinde keine Zertifikate" in prompt_text
    assert "Erfinde keine Abschluesse" in prompt_text
    assert "Erfinde keine Projekte" in prompt_text
    assert "Erfinde keine Rollen" in prompt_text
    assert "Erfinde keine Verantwortlichkeiten" in prompt_text
    assert "Erfinde keine offenen Stellen" in prompt_text
    assert "CareerHub nur, wenn es im Profilkontext vorkommt" in prompt_text
    assert "Ich sehe moegliche Einsatzfelder in" in prompt_text
    assert "QUALITAETSKONTROLLE" in prompt_text
    assert "Top Candidate Insights" in prompt_text
    assert "hoechst priorisierten Candidate Insights" in prompt_text
    assert letter.startswith("Mit grossem Interesse")


def test_company_initiative_letter_reports_missing_ollama(monkeypatch):
    monkeypatch.setattr(
        application_service,
        "chat",
        None,
    )

    with pytest.raises(RuntimeError):
        application_service.generate_company_initiative_letter(
            company_name="CareerHub GmbH",
            profile_tags=[
                "project_management",
            ],
            company_context="Company Match Score: 80",
        )
