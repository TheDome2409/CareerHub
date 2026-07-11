TAG_LABELS = {
    "artificial_intelligence": "KI / AI",
    "ai": "🤖 KI / AI",
    "leadership": "👥 Leadership",
    "project_responsibility": "📋 Projektverantwortung",
    "budget_responsibility": "💰 Budgetverantwortung",
    "stakeholder_management": "🤝 Stakeholder Management",
    "change_management": "🔄 Change Management",
    "digitalization": "💡 Digitalisierung",
    "strategic_role": "🧭 Strategie",
    "innovation": "🧪 Innovation",
    "automation": "⚙️ Automatisierung",
    "cloud": "☁️ Cloud",
    "security": "🔒 Security",
    "consulting": "🧑‍💼 Consulting",
    "data": "📊 Data / EDI",
    "architecture": "🏗 Infrastruktur / Architektur",
    "governance": "📐 Governance",
    "platform": "🧱 Plattform",
    "product": "📦 Product",
    "social_engagement": "🤝 Soziales Engagement",
    "vendor_management": "🏢 Dienstleistersteuerung",
}


def label_tag(tag: str) -> str:
    return TAG_LABELS.get(tag, tag)
