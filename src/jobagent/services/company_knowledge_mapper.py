import re
import unicodedata

from jobagent.models.company_enums import (
    BusinessDomain,
    WorkModel,
)


WORK_MODEL_ALIASES = {
    "remote": WorkModel.REMOTE.value,
    "home office": WorkModel.REMOTE.value,
    "homeoffice": WorkModel.REMOTE.value,
    "fully remote": WorkModel.REMOTE.value,
    "hybrid": WorkModel.HYBRID.value,
    "hybride": WorkModel.HYBRID.value,
    "onsite": WorkModel.ONSITE.value,
    "on site": WorkModel.ONSITE.value,
    "vor ort": WorkModel.ONSITE.value,
    "praesenz": WorkModel.ONSITE.value,
    "präsenz": WorkModel.ONSITE.value,
}

BUSINESS_DOMAIN_ALIASES = {
    "energy": BusinessDomain.ENERGY.value,
    "energie": BusinessDomain.ENERGY.value,
    "rail": BusinessDomain.RAIL.value,
    "bahn": BusinessDomain.RAIL.value,
    "telecommunication": BusinessDomain.TELECOMMUNICATION.value,
    "telecommunications": BusinessDomain.TELECOMMUNICATION.value,
    "telekommunikation": BusinessDomain.TELECOMMUNICATION.value,
    "healthcare": BusinessDomain.HEALTHCARE.value,
    "gesundheit": BusinessDomain.HEALTHCARE.value,
    "industry": BusinessDomain.INDUSTRY.value,
    "industrie": BusinessDomain.INDUSTRY.value,
    "public sector": BusinessDomain.PUBLIC_SECTOR.value,
    "public_sector": BusinessDomain.PUBLIC_SECTOR.value,
    "öffentlicher dienst": BusinessDomain.PUBLIC_SECTOR.value,
    "oeffentlicher dienst": BusinessDomain.PUBLIC_SECTOR.value,
    "offentlicher dienst": BusinessDomain.PUBLIC_SECTOR.value,
    "verwaltung": BusinessDomain.PUBLIC_SECTOR.value,
    "finance": BusinessDomain.FINANCE.value,
    "banking": BusinessDomain.FINANCE.value,
    "education": BusinessDomain.EDUCATION.value,
    "bildung": BusinessDomain.EDUCATION.value,
    "research": BusinessDomain.RESEARCH.value,
    "forschung": BusinessDomain.RESEARCH.value,
    "manufacturing": BusinessDomain.MANUFACTURING.value,
    "produktion": BusinessDomain.MANUFACTURING.value,
    "fertigung": BusinessDomain.MANUFACTURING.value,
    "agriculture": "agriculture",
    "landwirtschaft": "agriculture",
}


def _ascii_fold(value: str) -> str:
    value = unicodedata.normalize(
        "NFKD",
        str(value or ""),
    )

    return "".join(
        char
        for char in value
        if not unicodedata.combining(char)
    )


def _normalize_key(value: str) -> str:
    value = _ascii_fold(
        value
    ).lower()
    value = re.sub(
        r"[^a-z0-9+#.]+",
        " ",
        value,
    )

    return re.sub(
        r"\s+",
        " ",
        value,
    ).strip()


def normalize_work_model(value: str | WorkModel | None) -> str:
    if isinstance(value, WorkModel):
        return value.value

    key = _normalize_key(
        str(value or "")
    )

    return WORK_MODEL_ALIASES.get(
        key,
        key,
    )


def normalize_business_domain(value: str | BusinessDomain | None) -> str:
    if isinstance(value, BusinessDomain):
        return value.value

    key = _normalize_key(
        str(value or "")
    ).replace(
        " ",
        "_",
    )
    alias_key = key.replace(
        "_",
        " ",
    )

    return BUSINESS_DOMAIN_ALIASES.get(
        key,
        BUSINESS_DOMAIN_ALIASES.get(
            alias_key,
            key,
        ),
    )


def normalize_technology(value: str | None) -> str:
    key = _normalize_key(
        str(value or "")
    )

    technology_aliases = {
        "ms azure": "Azure",
        "microsoft azure": "Azure",
        "azure": "Azure",
        "sap": "SAP",
        "data analytics": "Data Analytics",
        "data analysis": "Data Analytics",
        "ki": "AI",
        "ai": "AI",
    }

    return technology_aliases.get(
        key,
        str(value or "").strip(),
    )


def normalize_location(value: str | None) -> str:
    value = re.sub(
        r"\s+",
        " ",
        str(value or ""),
    ).strip()

    if not value:
        return ""

    return value
