from jobagent.models.company_enums import SourceType
from jobagent.models.recommended_company import RecommendedCompany
from jobagent.repositories.company_repository import CompanyRepository
from jobagent.services.company_source_service import ensure_company_sources


def _repository(repository: CompanyRepository | None = None) -> CompanyRepository:
    return repository or CompanyRepository()


def _load_seed_companies() -> list[RecommendedCompany]:
    return [
        RecommendedCompany(
            name="Dataport",
            website_url="https://www.dataport.de",
            career_url="https://www.dataport.de/karriere",
            industry="public_sector",
            region="Germany",
            priority=1,
            reason="Öffentliche Digitalisierung und kritische Infrastruktur.",
            tags=[
                "public_sector",
                "digitalization",
                "kritis",
            ],
        ),
        RecommendedCompany(
            name="DB InfraGO",
            website_url="https://www.dbinfrago.com",
            career_url="https://db.jobs",
            industry="rail",
            region="Germany",
            priority=2,
            reason="Digitale Infrastruktur und Bahnsysteme.",
            tags=[
                "rail",
                "infrastructure",
                "digitalization",
            ],
        ),
        RecommendedCompany(
            name="Amprion",
            website_url="https://www.amprion.net",
            career_url="https://www.amprion.net/Karriere/",
            industry="energy",
            region="Germany",
            priority=3,
            reason="Energiewende und Stromnetz.",
            tags=[
                "energy",
                "grid",
                "kritis",
            ],
        ),
        RecommendedCompany(
            name="KWS",
            website_url="https://www.kws.com",
            career_url="https://jobs.kws.com",
            industry="agriculture",
            region="Germany",
            priority=4,
            reason="Agrartechnologie, Forschung und digitale Landwirtschaft.",
            tags=[
                "agriculture",
                "research",
                "digitalization",
            ],
        ),
        RecommendedCompany(
            name="Deutsche Telekom",
            website_url="https://www.telekom.com",
            career_url="https://www.telekom.com/de/karriere",
            industry="telecommunication",
            region="Germany",
            priority=5,
            reason="Telekommunikation, Cloud und digitale Infrastruktur.",
            tags=[
                "telecommunication",
                "cloud",
                "infrastructure",
            ],
        ),
        RecommendedCompany(
            name="Avacon",
            website_url="https://www.avacon.de",
            career_url="https://www.avacon.de/de/karriere.html",
            industry="energy",
            region="Germany",
            priority=6,
            reason="Regionale Energieinfrastruktur und Netzbetrieb.",
            tags=[
                "energy",
                "grid",
                "regional",
            ],
        ),
        RecommendedCompany(
            name="Westfalen Weser",
            website_url="https://www.westfalenweser.com",
            career_url="https://www.westfalenweser.com/karriere",
            industry="energy",
            region="Germany",
            priority=7,
            reason="Kommunale Energieversorgung und regionale Infrastruktur.",
            tags=[
                "energy",
                "municipal",
                "infrastructure",
            ],
        ),
        RecommendedCompany(
            name="50Hertz",
            website_url="https://www.50hertz.com",
            career_url="https://www.50hertz.com/de/Karriere",
            industry="energy",
            region="Germany",
            priority=8,
            reason="Übertragungsnetz, Energiewende und kritische Infrastruktur.",
            tags=[
                "energy",
                "grid",
                "kritis",
            ],
        ),
        RecommendedCompany(
            name="TenneT",
            website_url="https://www.tennet.eu",
            career_url="https://www.tennet.eu/de/karriere",
            industry="energy",
            region="Germany",
            priority=9,
            reason="Stromübertragung, Offshore-Netze und Energiewende.",
            tags=[
                "energy",
                "grid",
                "offshore",
            ],
        ),
        RecommendedCompany(
            name="E.ON",
            website_url="https://www.eon.com",
            career_url="https://www.eon.com/de/karriere.html",
            industry="energy",
            region="Europe",
            priority=10,
            reason="Energielösungen, Netze und digitale Transformation.",
            tags=[
                "energy",
                "digitalization",
                "transformation",
            ],
        ),
    ]


def _seed_source_definitions(
    recommended_company: RecommendedCompany,
) -> list[dict]:
    sources = []

    if recommended_company.website_url:
        sources.append(
            {
                "source_type": SourceType.COMPANY_WEBSITE,
                "url": recommended_company.website_url,
                "title": f"{recommended_company.name} Website",
                "priority": 1,
                "notes": "Seed-Quelle aus CompanyHub-Empfehlung.",
            }
        )

    if recommended_company.career_url:
        sources.append(
            {
                "source_type": SourceType.CAREER_PAGE,
                "url": recommended_company.career_url,
                "title": f"{recommended_company.name} Karriere",
                "priority": 2,
                "notes": "Seed-Quelle aus CompanyHub-Empfehlung.",
            }
        )

    return sources


def get_recommended_companies(profile=None) -> list[RecommendedCompany]:
    del profile

    return sorted(
        _load_seed_companies(),
        key=lambda company: (
            company.priority,
            company.name.lower(),
        ),
    )


def track_recommended_company(
    recommended_company: RecommendedCompany,
    profile_fingerprint: str,
    repository: CompanyRepository | None = None,
) -> dict:
    repo = _repository(
        repository
    )
    company = repo.upsert_company(
        name=recommended_company.name,
        website_url=recommended_company.website_url,
        career_url=recommended_company.career_url,
        industry=recommended_company.industry,
    )
    ensure_company_sources(
        company_id=company.id,
        source_definitions=_seed_source_definitions(
            recommended_company
        ),
        repository=repo,
    )

    return repo.track_company(
        company_id=company.id,
        profile_fingerprint=profile_fingerprint,
        priority=recommended_company.priority,
        notes=recommended_company.reason,
    )


def get_tracked_companies(
    profile_fingerprint: str,
    repository: CompanyRepository | None = None,
) -> list[dict]:
    return _repository(
        repository
    ).list_tracked_companies(
        profile_fingerprint
    )


def deactivate_tracked_company(
    company_id: int,
    profile_fingerprint: str,
    repository: CompanyRepository | None = None,
) -> dict:
    return _repository(
        repository
    ).deactivate_tracked_company(
        company_id=company_id,
        profile_fingerprint=profile_fingerprint,
    )
