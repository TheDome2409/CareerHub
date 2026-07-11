from jobagent.models.skill_candidate import SkillCandidate
from jobagent.services.skill_profile_io import (
    profile_preferences_from_csv,
    skill_candidates_from_csv,
    skill_candidates_to_csv,
)


def test_skill_profile_csv_exports_preferences_and_keeps_skill_rows():
    csv_content = skill_candidates_to_csv(
        [
            SkillCandidate(
                name="project_management",
                category="management",
                confidence=0.95,
                weight=8,
                enabled=True,
                source="profile",
                provider="manual",
            )
        ],
        preferences={
            "salary_minimum": 70000,
            "salary_target": 80000,
            "salary_dream": 100000,
            "work_model_preferred": [
                "remote",
                "hybrid",
            ],
            "work_model_acceptable": [
                "remote",
                "hybrid",
                "onsite",
            ],
            "hard_exclusion_industries": [
                "banking",
                "defense",
            ],
            "hard_exclusion_employment_models": [
                "temporary_work",
                "labour_leasing",
            ],
            "hard_exclusion_requirements": [
                "security_clearance",
            ],
        },
    )

    assert "skill,," in csv_content
    assert "project_management" in csv_content
    assert "preference,salary_minimum,70000" in csv_content
    assert "preference,salary_target,80000" in csv_content
    assert "preference,salary_dream,100000" in csv_content
    assert "preference,work_model_preferred,remote;hybrid" in csv_content
    assert (
        "preference,work_model_acceptable,remote;hybrid;onsite"
        in csv_content
    )
    assert "preference,exclusion_industries,banking;defense" in csv_content
    assert (
        "preference,exclusion_employment_models,"
        "temporary_work;labour_leasing"
    ) in csv_content
    assert (
        "preference,exclusion_requirements,security_clearance"
        in csv_content
    )


def test_skill_profile_csv_import_skips_preference_rows_for_skills():
    csv_content = (
        "type,key,value,Skill-Name,Kategorie,Confidence,Weight,Enabled,Source\n"
        "skill,,,project_management,management,0.95,8,True,profile\n"
        "preference,salary_minimum,70000,,,,,,\n"
        "preference,work_model_preferred,remote;hybrid,,,,,,\n"
    )

    skills = skill_candidates_from_csv(
        csv_content
    )

    assert len(skills) == 1
    assert skills[0].name == "project_management"
    assert skills[0].weight == 8


def test_skill_profile_csv_import_reads_preferences():
    csv_content = (
        "type,key,value,Skill-Name,Kategorie,Confidence,Weight,Enabled,Source\n"
        "skill,,,project_management,management,0.95,8,True,profile\n"
        "preference,salary_minimum,70000,,,,,,\n"
        "preference,salary_target,80000,,,,,,\n"
        "preference,salary_dream,100000,,,,,,\n"
        "preference,work_model_preferred,remote;hybrid,,,,,,\n"
        "preference,work_model_acceptable,remote;hybrid;onsite,,,,,,\n"
        "preference,exclusion_industries,banking;defense,,,,,,\n"
        "preference,exclusion_employment_models,temporary_work;labour_leasing,,,,,,\n"
        "preference,exclusion_requirements,security_clearance,,,,,,\n"
    )

    preferences = profile_preferences_from_csv(
        csv_content
    )

    assert preferences["salary_minimum"] == 70000
    assert preferences["salary_target"] == 80000
    assert preferences["salary_dream"] == 100000
    assert preferences["work_model_preferred"] == [
        "remote",
        "hybrid",
    ]
    assert preferences["work_model_acceptable"] == [
        "remote",
        "hybrid",
        "onsite",
    ]
    assert preferences["hard_exclusion_industries"] == [
        "banking",
        "defense",
    ]
    assert preferences["hard_exclusion_employment_models"] == [
        "temporary_work",
        "labour_leasing",
    ]
    assert preferences["hard_exclusion_requirements"] == [
        "security_clearance",
    ]
