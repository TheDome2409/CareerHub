import html
import re


KEYWORDS = {
    "ai": [
        "ai",
        "artificial intelligence",
        "machine learning",
        "llm",
        "genai",
        "ki",
        "künstliche intelligenz",
    ],
    "leadership": [
        "lead",
        "leader",
        "leadership",
        "team lead",
        "head of",
        "manager",
        "department lead",
        "leiter",
        "leiterin",
        "teamleiter",
        "teamleiterin",
        "führung",
        "führungsverantwortung",
        "teamkoordination",
        "koordination",
        "geschäftsführung",
    ],
    "project_responsibility": [
        "project management",
        "project manager",
        "projektleitung",
        "projektmanager",
        "projektmanagerin",
        "projektkoordinator",
        "projektkoordinatorin",
        "projektleiter",
        "projektleiterin",
        "program manager",
        "programme manager",
        "planung",
        "umsetzung",
        "projekte",
        "projekt",
    ],
    "budget_responsibility": [
        "budget",
        "cost responsibility",
        "budget responsibility",
        "budgetverantwortung",
        "kostenverantwortung",
        "p&l",
        "profit and loss",
    ],
    "stakeholder_management": [
        "stakeholder",
        "stakeholder management",
        "stakeholder-management",
        "executive communication",
        "board",
        "management reporting",
        "geschäftsführung",
        "vorstand",
    ],
    "change_management": [
        "change management",
        "change",
        "transformation",
        "organizational change",
        "business transformation",
        "veränderungsmanagement",
        "prozessoptimierung",
        "weiterentwicklung",
        "einführung",
        "fehleranalyse",
        "dokumentation",
    ],
    "digitalization": [
        "digitalization",
        "digitalisation",
        "digital transformation",
        "digitization",
        "digitalisierung",
        "digitalisierungsprojekt",
        "digitalisierungsprojekte",
        "einführung",
        "it-systeme",
        "systeme",
        "prozessoptimierung",
    ],
    "strategic_role": [
        "strategy",
        "strategic",
        "roadmap",
        "vision",
        "governance",
        "strategie",
        "strategisch",
        "zielbild",
    ],
    "innovation": [
        "innovation",
        "innovative",
        "research",
        "r&d",
        "forschung",
        "entwicklung",
    ],
    "automation": [
        "automation",
        "process automation",
        "workflow automation",
        "orchestration",
        "automatisierung",
        "prozessautomatisierung",
        "prozessoptimierung",
        "optimierung",
        "optimierung",
        "weiterentwicklung",
    ],
    "cloud": [
        "aws",
        "azure",
        "gcp",
        "cloud",
        "cloud native",
        "exchange online",
    ],
    "security": [
        "security",
        "cyber security",
        "cybersecurity",
        "information security",
        "iso 27001",
        "isms",
        "informationssicherheit",
        "it-sicherheit",
        "datensicherheit",
        "firewall",
        "firewalls",
        "vpn",
    ],
    "consulting": [
        "consultant",
        "consulting",
        "customer advisory",
        "solution consulting",
        "beratung",
        "berater",
        "beraterin",
        "unterstützung",
        "entscheidungsprozesse",
        "technische entscheidungsprozesse",
    ],
    "data": [
        "data",
        "analytics",
        "business intelligence",
        "bi",
        "data platform",
        "datenanalyse",
        "datenplattform",
        "edi",
        "electronic data interchange",
        "schnittstellen",
    ],
    "architecture": [
        "enterprise architecture",
        "solution architecture",
        "architect",
        "target architecture",
        "architektur",
        "lösungsarchitektur",
        "infrastruktur",
        "systemintegration",
        "virtualisierung",
        "server",
        "netzwerk",
    ],
    "governance": [
        "governance",
        "compliance",
        "policy",
        "richtlinie",
        "regelwerk",
    ],
    "platform": [
        "platform",
        "platform engineering",
        "shared services",
        "plattform",
    ],
    "product": [
        "product owner",
        "product management",
        "product strategy",
        "produktmanagement",
        "produkteigner",
    ],
    "social_engagement": [
    "rettungshelfer",
    "oberfeuerwehrmann",
    "feuerwehr",
    "freiwillige feuerwehr",
    "ehrenamt",
    "ehrenamtlich",
    "ausbilder",
    "breitenausbilder",
    "erste hilfe",
    ]
}


def normalize_text(text: str) -> str:
    text = html.unescape(text)
    text = text.lower()
    text = text.replace("&", " und ")
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"[/|_]+", " ", text)
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def _contains_keyword(text: str, keyword: str) -> bool:
    keyword = normalize_text(keyword)
    pattern = rf"(?<!\w){re.escape(keyword)}(?!\w)"

    return re.search(pattern, text) is not None


def detect_keyword_matches(text: str) -> dict[str, list[str]]:
    normalized_text = normalize_text(text)
    matches = {}

    for tag, keywords in KEYWORDS.items():
        found_keywords = []

        for keyword in keywords:
            if _contains_keyword(normalized_text, keyword):
                found_keywords.append(keyword)

        if found_keywords:
            matches[tag] = found_keywords

    return matches


def detect_tags(text: str) -> list[str]:
    return list(
        detect_keyword_matches(text).keys()
    )