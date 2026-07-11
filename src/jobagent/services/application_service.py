from datetime import datetime
from pathlib import Path

try:
    from ollama import chat
except ModuleNotFoundError:
    chat = None

from jobagent.models.tag_labels import label_tag


MODEL = "qwen3:30b"
MAX_DESCRIPTION_CHARS = 2600
MAX_PROFILE_CONTEXT_CHARS = 4500
MAX_OUTPUT_TOKENS = 1100
MAX_RESUME_OUTPUT_TOKENS = 650
LETTER_PREFIX = "Mit grossem Interesse"
RESUME_PREFIX = "Berufliches Profil"
INITIATIVE_PREFIX = "Mit grossem Interesse"
DEBUG = True
PROJECT_ROOT = Path(__file__).resolve().parents[3]
LOG_FILE = PROJECT_ROOT / "logs" / "careerhub_application.log"
LAST_DEBUG = ""


def _company_prompt_value(company: str | None) -> str:
    if company:
        return company

    return "Arbeitgeber in der Stellenanzeige nicht eindeutig genannt"


def _response_content(response) -> str:
    message = getattr(response, "message", None)

    if message is not None:
        content = getattr(message, "content", None)

        if content:
            return content

        if isinstance(message, dict):
            content = message.get("content")

            if content:
                return content

    if isinstance(response, dict):
        message = response.get("message")

        if isinstance(message, dict):
            content = message.get("content")

            if content:
                return content

        content = response.get("response")

        if content:
            return content

    return ""


def _clean_cover_letter(content: str) -> str:
    think_end = "</think>"

    if think_end in content:
        content = content.split(
            think_end,
            1,
        )[1]

    marker = LETTER_PREFIX
    marker_alt = "Mit großem Interesse"

    for candidate in [marker, marker_alt]:
        index = content.find(candidate)

        if index > 0:
            return content[index:].strip()

    return content.strip()


def _sanitize_cover_letter(content: str) -> str:
    replacements = {
        "[Firma]": "Ihrem Unternehmen",
        "[Unternehmen]": "Ihrem Unternehmen",
        "[Name]": "",
        "bei [Firma]": "",
        "bei [Unternehmen]": "",
        "Meine Erfahrung in": "Meine Schwerpunkte in",
        "Durch meine Arbeit als Projektleiter habe ich gelernt,": (
            "In der Rolle als IT-Projektleiter ist es zentral,"
        ),
        "Durch meine Arbeit als Projektleiter": (
            "In der Rolle als IT-Projektleiter"
        ),
    }

    for old, new in replacements.items():
        content = content.replace(old, new)

    return content.strip()


def _skill_labels(profile_tags: list[str]) -> str:
    labels = []

    for tag in profile_tags[:12]:
        label = label_tag(tag)
        labels.append(label)

    return ", ".join(labels)


def _thinking_length(response) -> int | None:
    message = getattr(response, "message", None)

    if message is not None:
        thinking = getattr(message, "thinking", None)

        if thinking:
            return len(thinking)

        if isinstance(message, dict):
            thinking = message.get("thinking")

            if thinking:
                return len(thinking)

    if isinstance(response, dict):
        message = response.get("message")

        if isinstance(message, dict):
            thinking = message.get("thinking")

            if thinking:
                return len(thinking)

    return None


def _write_debug(message: str) -> None:
    if not DEBUG:
        return

    global LAST_DEBUG

    timestamp = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )
    line = f"[{timestamp}] {message}"
    LAST_DEBUG = line

    LOG_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with open(
        LOG_FILE,
        "a",
        encoding="utf-8",
    ) as file:
        file.write(line + "\n")

    print(line)


def last_cover_letter_debug() -> str:
    return LAST_DEBUG


def _debug_response(response, content: str) -> None:
    if not DEBUG:
        return

    done_reason = getattr(response, "done_reason", None)
    total_duration = getattr(response, "total_duration", None)
    eval_count = getattr(response, "eval_count", None)
    thinking_length = _thinking_length(response)

    if isinstance(response, dict):
        done_reason = done_reason or response.get("done_reason")
        total_duration = total_duration or response.get("total_duration")
        eval_count = eval_count or response.get("eval_count")

    _write_debug(
        "[CareerHub] cover letter response: "
        f"content_length={len(content)}, "
        f"thinking_length={thinking_length}, "
        f"done_reason={done_reason}, "
        f"eval_count={eval_count}, "
        f"total_duration={total_duration}"
    )


def _chat(
    **kwargs,
):
    if chat is None:
        raise RuntimeError(
            "Ollama Python-Paket ist nicht verfuegbar."
        )

    return chat(
        **kwargs
    )


def generate_cover_letter(
    job_title: str,
    company: str | None,
    profile_tags: list[str],
    job_description: str,
    profile_context: str = "",
) -> str:
    skills = _skill_labels(profile_tags)
    description = (job_description or "")[:MAX_DESCRIPTION_CHARS]
    profile_context = (
        profile_context or ""
    )[:MAX_PROFILE_CONTEXT_CHARS]

    if DEBUG:
        _write_debug(
            "[CareerHub] cover letter request: "
            f"model={MODEL}, "
            f"title_length={len(job_title or '')}, "
            f"skills_count={len(profile_tags)}, "
            f"description_length={len(description)}, "
            f"profile_context_length={len(profile_context)}, "
            f"num_predict={MAX_RESUME_OUTPUT_TOKENS}"
        )

    response = _chat(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "Antworte ausschliesslich mit dem fertigen "
                    "deutschen Anschreiben. Keine Analyse, keine "
                    "Meta-Kommentare, keine Listen, kein JSON. "
                    "Schreibe professionell, konkret und souveraen "
                    "fuer eine IT-Fach- oder Fuehrungsrolle. "
                    "Nutze Profilkontext als primaere Quelle fuer "
                    "Aussagen ueber die Person. "
                    "Nutze eine klare Dramaturgie: Motivation zur "
                    "Rolle, passender Kompetenzbezug, konkreter "
                    "Mehrwert fuer die Aufgaben, kurzer Abschluss. "
                    "Erfinde keine Arbeitgeber, Kundennamen, Zahlen, "
                    "Projektergebnisse, Zertifikate oder bisherigen "
                    "Stationen. Behaupte keine bereits erzielten "
                    "Effizienzsteigerungen, abgeschlossenen Projekte "
                    "oder Methoden, die nicht im Input stehen. "
                    "Beschreibe Kompetenzen und Arbeitsweise, keine "
                    "unbelegten Erfolgsgeschichten. Verwende keine Platzhalter wie "
                    "[Firma]. Wenn Details fehlen, formuliere neutral. "
                    "Keine Grussformel und kein Adressblock."
                ),
            },
            {
                "role": "user",
                "content": f"""
Position:
{job_title}

Unternehmen:
{_company_prompt_value(company)}

Skills:
{skills}

Profilkontext:
{profile_context or "Kein zusaetzlicher Profilkontext hochgeladen."}

Stellenbeschreibung:
{description}

Aufgabe:
Fuehre den begonnenen Satz als hochwertiges Anschreiben fort.
Schreibe 3 bis 4 kurze Absaetze mit insgesamt etwa 180 bis 260 Woertern.
Verbinde die Skills sichtbar mit den Anforderungen der Stelle.
Nutze konkrete Informationen aus dem Profilkontext, wenn sie dort stehen.
Klinge selbstbewusst, aber nicht uebertrieben.
Nutze keine erfundenen Stationen, Zahlen, Projekte oder Firmennamen.
Schreibe nicht "bereits mehrfach", "erfolgreich abgeschlossen",
"signifikante Effizienzsteigerungen" oder aehnliche unbelegte Erfolge.
Formuliere stattdessen: "Meine Schwerpunkte liegen in ..." oder
"Ich kann dazu beitragen, ...".
Wenn der Arbeitgeber unbekannt ist, schreibe neutral mit "Ihr Unternehmen"
oder "Ihre Organisation".
""",
            },
            {
                "role": "assistant",
                "content": LETTER_PREFIX,
            },
        ],
        options={
            "num_predict": MAX_OUTPUT_TOKENS,
            "temperature": 0.2,
        },
        think=False,
        keep_alive="30m",
    )

    raw_content = LETTER_PREFIX + _response_content(response)
    content = _sanitize_cover_letter(
        _clean_cover_letter(raw_content)
    )

    _debug_response(
        response,
        raw_content,
    )

    if DEBUG:
        _write_debug(
            "[CareerHub] cover letter cleaned: "
            f"content_length={len(content)}"
        )

    return content


def generate_context_resume(
    job_title: str,
    company: str | None,
    profile_tags: list[str],
    job_description: str,
    profile_context: str = "",
) -> str:
    skills = _skill_labels(profile_tags)
    description = (job_description or "")[:MAX_DESCRIPTION_CHARS]
    profile_context = (
        profile_context or ""
    )[:MAX_PROFILE_CONTEXT_CHARS]

    if DEBUG:
        _write_debug(
            "[CareerHub] resume request: "
            f"model={MODEL}, "
            f"title_length={len(job_title or '')}, "
            f"skills_count={len(profile_tags)}, "
            f"description_length={len(description)}, "
            f"profile_context_length={len(profile_context)}, "
            f"num_predict={MAX_OUTPUT_TOKENS}"
        )

    response = _chat(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "Antworte ausschliesslich mit einem "
                    "kontextbezogenen deutschen Kurzlebenslauf "
                    "als moderne, kompakte CV-Seite. "
                    "Keine Analyse, kein JSON, keine Meta-Kommentare. "
                    "Der Text muss auf genau eine DIN-A4-Seite passen. "
                    "Schreibe natuerlich und hochwertig, nicht wie "
                    "eine reine Tabelle. "
                    "Nutze nur Informationen, die im Profilkontext, "
                    "in den Skills oder in der Stellenbeschreibung "
                    "stehen. Erfinde keine Arbeitgeber, Zeitraeume, "
                    "Abschluesse, Zertifikate oder Projekte. "
                    "Wenn Details fehlen, formuliere allgemein und "
                    "kompetenzorientiert. Keine Kontaktinformationen."
                ),
            },
            {
                "role": "user",
                "content": f"""
Zielposition:
{job_title}

Unternehmen:
{_company_prompt_value(company)}

Skills:
{skills}

Profilkontext:
{profile_context or "Kein zusaetzlicher Profilkontext hochgeladen."}

Stellenbeschreibung:
{description}

Aufgabe:
Erstelle einen kompakten, zur Stelle passenden Lebenslauf im DIN-Stil.
Maximal 190 Woerter insgesamt.
Struktur:
Kurzprofil
2 bis 3 kurze Saetze als zusammenhaengender Profilblock.

Relevanz fuer die Position
3 kurze Bulletpoints, die Anforderungen der Stelle mit belegbaren
Erfahrungen aus dem Profilkontext verbinden.

Kompetenzschwerpunkte
5 kurze, gruppierte Kompetenzen als Bulletpoints.

Nachweise
Maximal 3 kurze Bulletpoints, nur wenn Zertifikate oder Nachweise
im Profilkontext vorhanden sind.

Keine Tabellen, keine erfundenen Zeitraeume, keine Wiederholungen,
kein Anschreibenston. Schreibe sachlich, konkret und drucktauglich.
""",
            },
            {
                "role": "assistant",
                "content": RESUME_PREFIX,
            },
        ],
        options={
            "num_predict": MAX_RESUME_OUTPUT_TOKENS,
            "temperature": 0.2,
        },
        think=False,
        keep_alive="30m",
    )

    raw_content = RESUME_PREFIX + _response_content(response)
    content = _clean_cover_letter(raw_content)

    _debug_response(
        response,
        raw_content,
    )

    if DEBUG:
        _write_debug(
            "[CareerHub] resume cleaned: "
            f"content_length={len(content)}"
        )

    return content


def generate_company_initiative_letter(
    company_name: str,
    profile_tags: list[str],
    company_context: str,
    profile_context: str = "",
) -> str:
    skills = _skill_labels(profile_tags)
    company_context = (
        company_context or ""
    )[:MAX_DESCRIPTION_CHARS]
    profile_context = (
        profile_context or ""
    )[:MAX_PROFILE_CONTEXT_CHARS]

    if DEBUG:
        _write_debug(
            "[CareerHub] company initiative request: "
            f"model={MODEL}, "
            f"company_length={len(company_name or '')}, "
            f"skills_count={len(profile_tags)}, "
            f"company_context_length={len(company_context)}, "
            f"profile_context_length={len(profile_context)}, "
            f"num_predict={MAX_OUTPUT_TOKENS}"
        )

    response = _chat(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "Antworte ausschliesslich mit einem fertigen "
                    "deutschen Motivationsschreiben fuer eine "
                    "Initiativbewerbung. Keine Analyse, keine Listen, "
                    "kein JSON, keine Meta-Kommentare. "
                    "Es gibt keine konkrete Stellenanzeige. "
                    "FAKTENTREUE: Verwende ausschliesslich "
                    "Informationen, die im Kandidatenprofil, in den "
                    "Profilskills, im Profilkontext, im CompanyProfile "
                    "oder im CompanyMatchResult stehen. "
                    "Erfinde keine Faehigkeiten. "
                    "Erfinde keine Zertifikate. "
                    "Erfinde keine Abschluesse. "
                    "Erfinde keine Projekte. "
                    "Erfinde keine Rollen. "
                    "Erfinde keine Verantwortlichkeiten. "
                    "Erfinde keine Zahlen. "
                    "Erfinde keine Mitarbeiterverantwortung. "
                    "Erfinde keine Umsatz- oder Budgetverantwortung. "
                    "Erfinde keine Erfolge. "
                    "UNSICHERHEIT: Wenn eine Information nicht eindeutig "
                    "vorhanden ist, erwaehne sie nicht. Keine "
                    "Spekulationen ueber Kenntnisse oder Erfahrungen. "
                    "Verwende keine Woerter wie vermutlich, "
                    "wahrscheinlich, duerfte oder sicherlich. Lieber "
                    "weniger schreiben als halluzinieren. "
                    "UNTERNEHMEN: Erfinde keine Behauptungen ueber das "
                    "Unternehmen. Nutze nur Informationen aus dem "
                    "CompanyProfile und CompanyMatchResult. Erfinde "
                    "keine offenen Stellen und keine Rollen. "
                    "INITIATIVBEWERBUNG: Beschreibe moegliche "
                    "Einsatzfelder, keine konkrete Stelle. Erwuenschte "
                    "Formulierungen sind: Ich sehe moegliche "
                    "Einsatzfelder in... oder Aus meiner bisherigen "
                    "Erfahrung koennte ich insbesondere in folgenden "
                    "Bereichen Mehrwert stiften... "
                    "CAREERHUB: Erwaehne CareerHub nur, wenn es im "
                    "Profilkontext vorkommt. Dann nur als Projekt "
                    "darstellen, niemals als Unternehmen, Produktfirma "
                    "oder Marktfuehrer. Erfinde keine Kunden, Umsaetze "
                    "oder Produktivnutzung. "
                    "TONALITAET: professionell, selbstbewusst, neugierig, "
                    "loesungsorientiert, ohne Uebertreibungen und ohne "
                    "Buzzword-Bingo. "
                    "QUALITAETSKONTROLLE vor der Ausgabe: Pruefe intern, "
                    "ob jede Behauptung durch Eingabedaten belegt ist; "
                    "ob eine Zahl, Rolle, Qualifikation oder "
                    "Unternehmensinformation erfunden wurde. Falls ja, "
                    "entferne die Behauptung. Keine Grussformel und "
                    "kein Adressblock."
                ),
            },
            {
                "role": "user",
                "content": f"""
Unternehmen:
{company_name or "Zielunternehmen nicht eindeutig genannt"}

Profilskills:
{skills}

Company-Match-Kontext:
{company_context or "Keine zusaetzlichen Company-Match-Signale vorhanden."}

Profilkontext:
{profile_context or "Kein zusaetzlicher Profilkontext hochgeladen."}

Aufgabe:
Erstelle ein kurzes, glaubwuerdiges Motivationsschreiben fuer eine
Initiativbewerbung. Schreibe 3 kurze Absaetze mit insgesamt etwa
150 bis 220 Woertern.

Nutze bevorzugt die hoechst priorisierten Candidate Insights als
konkrete Beispiele. Wenn "Top Candidate Insights" vorhanden sind,
verwende diese vor den allgemeinen Candidate Insights und vor dem
Rohtext. Nutze den Rohtext nur ergaenzend, wenn die Information dort
eindeutig vorkommt.

Absatz 1:
Interesse am Unternehmen nur aus vorhandenen CompanyProfile- oder
CompanyMatchResult-Signalen ableiten.

Absatz 2:
Moegliche Einsatzfelder beschreiben. Nutze gern Formulierungen wie
"Ich sehe moegliche Einsatzfelder in..." oder
"Aus meiner bisherigen Erfahrung koennte ich insbesondere in folgenden
Bereichen Mehrwert stiften...".

Absatz 3:
Interesse an einem Austausch ueber passende Einsatzfelder formulieren.

Wiederhole keine Listen aus dem Input. Erfinde keine konkrete Stelle,
keine Rolle, keine Qualifikation, keine Zahl und keinen Erfolg.
Wenn Belege fehlen, lasse die Aussage weg.
""",
            },
            {
                "role": "assistant",
                "content": INITIATIVE_PREFIX,
            },
        ],
        options={
            "num_predict": MAX_OUTPUT_TOKENS,
            "temperature": 0.2,
        },
        think=False,
        keep_alive="30m",
    )

    raw_content = INITIATIVE_PREFIX + _response_content(response)
    content = _sanitize_cover_letter(
        _clean_cover_letter(raw_content)
    )

    _debug_response(
        response,
        raw_content,
    )

    if DEBUG:
        _write_debug(
            "[CareerHub] company initiative cleaned: "
            f"content_length={len(content)}"
        )

    return content
