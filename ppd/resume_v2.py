"""Structured resume schema (v2) with migration to/from legacy Resume."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

import yaml
from pydantic import BaseModel, Field, field_validator

from ppd.schema import (
    Basics,
    CertificationItem,
    EducationItem,
    ExperienceItem,
    Link,
    ProjectItem,
    Resume,
    SkillGroup,
    dump_resume,
    load_resume,
)


class PersonalInfo(BaseModel):
    name: str = "Your Name"
    title: Optional[str] = None
    location: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    github: Optional[str] = None
    linkedin: Optional[str] = None
    portfolio: Optional[str] = None


class SummaryBlock(BaseModel):
    text: Optional[str] = None


class ExperienceEntry(BaseModel):
    title: str
    company: str
    location: Optional[str] = None
    employment_type: Optional[str] = None
    start_date: str = "YYYY"
    end_date: str = "present"
    bullets: list[str] = Field(default_factory=list)


class ProjectEntry(BaseModel):
    name: str
    technologies: list[str] = Field(default_factory=list)
    description: Optional[str] = None
    bullets: list[str] = Field(default_factory=list)


class SkillsBlock(BaseModel):
    frontend: list[str] = Field(default_factory=list)
    backend: list[str] = Field(default_factory=list)
    database: list[str] = Field(default_factory=list)
    cloud_tools: list[str] = Field(default_factory=list)
    other: list[str] = Field(default_factory=list)


class EducationEntry(BaseModel):
    degree: str
    field: Optional[str] = None
    institution: str
    location: Optional[str] = None
    graduation: Optional[str] = None
    gpa: Optional[str] = None


class CustomSection(BaseModel):
    title: str
    items: list[str] = Field(default_factory=list)


class StructuredResume(BaseModel):
    personal: PersonalInfo = Field(default_factory=PersonalInfo)
    summary: SummaryBlock = Field(default_factory=SummaryBlock)
    experience: list[ExperienceEntry] = Field(default_factory=list)
    projects: list[ProjectEntry] = Field(default_factory=list)
    skills: SkillsBlock = Field(default_factory=SkillsBlock)
    education: list[EducationEntry] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    custom_sections: list[CustomSection] = Field(default_factory=list)
    visible_sections: list[str] = Field(default_factory=list)
    visible_skill_categories: list[str] = Field(default_factory=list)

    @field_validator(
        "experience", "projects", "education", "certifications", "custom_sections", mode="before"
    )
    @classmethod
    def none_to_list(cls, value: object) -> object:
        return value if value is not None else []


class ResumeDocument(BaseModel):
    resume: StructuredResume


def _link_value(links: list[Link], *labels: str) -> Optional[str]:
    for link in links:
        if any(label.lower() in link.label.lower() for label in labels):
            return link.url
    return None


def legacy_to_structured(legacy: Resume) -> StructuredResume:
    personal = PersonalInfo(
        name=legacy.basics.name,
        title=legacy.basics.title,
        location=legacy.basics.location,
        phone=legacy.basics.phone,
        email=legacy.basics.email,
        github=_link_value(legacy.basics.links, "github"),
        linkedin=_link_value(legacy.basics.links, "linkedin"),
        portfolio=_link_value(legacy.basics.links, "portfolio", "link"),
    )
    skills = SkillsBlock()
    for group in legacy.skills:
        cat = group.category.lower()
        if "front" in cat:
            skills.frontend.extend(group.items)
        elif "back" in cat:
            skills.backend.extend(group.items)
        elif "data" in cat or "db" in cat:
            skills.database.extend(group.items)
        elif "cloud" in cat or "tool" in cat:
            skills.cloud_tools.extend(group.items)
        else:
            skills.other.extend(group.items)

    return StructuredResume(
        personal=personal,
        summary=SummaryBlock(text=legacy.summary),
        experience=[
            ExperienceEntry(
                title=e.role,
                company=e.company,
                location=e.location,
                start_date=e.start,
                end_date=e.end,
                bullets=e.bullets[:],
            )
            for e in legacy.experience
        ],
        projects=[
            ProjectEntry(
                name=p.name,
                technologies=[t.strip() for t in (p.description or "").split(",") if t.strip()],
                description=None,
                bullets=p.bullets[:],
            )
            for p in legacy.projects
        ],
        skills=skills,
        education=[
            EducationEntry(
                degree=e.degree,
                institution=e.institution,
                location=e.location,
                graduation=e.end,
                gpa=next((d for d in e.details if "gpa" in d.lower()), None),
            )
            for e in legacy.education
        ],
        certifications=[c.name for c in legacy.certifications],
    )


def structured_to_legacy(structured: StructuredResume) -> Resume:
    links: list[Link] = []
    if structured.personal.github:
        links.append(Link(label="GitHub", url=structured.personal.github))
    if structured.personal.linkedin:
        links.append(Link(label="LinkedIn", url=structured.personal.linkedin))
    if structured.personal.portfolio:
        links.append(Link(label="Portfolio", url=structured.personal.portfolio))

    skill_groups: list[SkillGroup] = []
    mapping = [
        ("Frontend", structured.skills.frontend),
        ("Backend", structured.skills.backend),
        ("Database", structured.skills.database),
        ("Cloud & Tools", structured.skills.cloud_tools),
        ("Other", structured.skills.other),
    ]
    for cat, items in mapping:
        if items:
            skill_groups.append(SkillGroup(category=cat, items=items))

    certifications = [CertificationItem(name=c) for c in structured.certifications]

    return Resume(
        basics=Basics(
            name=structured.personal.name,
            title=structured.personal.title,
            email=structured.personal.email,
            phone=structured.personal.phone,
            location=structured.personal.location,
            links=links,
        ),
        summary=structured.summary.text,
        experience=[
            ExperienceItem(
                role=e.title,
                company=e.company,
                location=e.location,
                start=e.start_date,
                end=e.end_date,
                bullets=e.bullets[:],
            )
            for e in structured.experience
        ],
        projects=[
            ProjectItem(
                name=p.name,
                description=", ".join(p.technologies) if p.technologies else p.description,
                bullets=p.bullets[:],
            )
            for p in structured.projects
        ],
        skills=skill_groups,
        education=[
            EducationItem(
                institution=e.institution,
                degree=e.degree,
                location=e.location,
                end=e.graduation,
                details=[e.gpa] if e.gpa else [],
            )
            for e in structured.education
        ],
        certifications=certifications,
    )


def load_structured(path: Path) -> StructuredResume:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"{path} must contain a YAML mapping.")
    if "resume" in raw:
        structured = ResumeDocument.model_validate(raw).resume
    elif "basics" in raw:
        structured = legacy_to_structured(Resume.model_validate(raw))
    else:
        raise ValueError("Unrecognized resume YAML format.")
    if not structured.visible_sections:
        structured.visible_sections, structured.visible_skill_categories = compute_visible_sections(structured)
    return structured


def dump_structured(structured: StructuredResume, path: Path) -> None:
    doc = ResumeDocument(resume=structured)
    data = doc.model_dump(mode="json", exclude_none=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.dump(data, sort_keys=False, allow_unicode=True, default_flow_style=False),
        encoding="utf-8",
    )


def structured_to_dict(structured: StructuredResume) -> dict[str, Any]:
    return ResumeDocument(resume=structured).model_dump(mode="json", exclude_none=True)


def structured_from_dict(data: dict[str, Any]) -> StructuredResume:
    if "resume" in data:
        structured = ResumeDocument.model_validate(data).resume
    else:
        structured = StructuredResume.model_validate(data)
    if not structured.visible_sections:
        structured.visible_sections, structured.visible_skill_categories = compute_visible_sections(structured)
    return structured


def compute_visible_sections(
    structured: StructuredResume,
    found_headings: set[str] | None = None,
) -> tuple[list[str], list[str]]:
    """Return (visible_sections, visible_skill_categories) from parsed content."""
    found = found_headings or set()
    visible: list[str] = ["personal"]

    if structured.summary.text or "summary" in found:
        visible.append("summary")
    if structured.experience or "experience" in found:
        visible.append("experience")
    if structured.projects or "projects" in found:
        visible.append("projects")
    if "skills" in found or any(
        getattr(structured.skills, cat)
        for cat in ("frontend", "backend", "database", "cloud_tools", "other")
    ):
        visible.append("skills")
    if structured.education or "education" in found:
        visible.append("education")
    if structured.certifications or "certifications" in found:
        visible.append("certifications")
    if structured.custom_sections or "_custom" in found:
        visible.append("custom_sections")

    skill_cats: list[str] = []
    for key in ("frontend", "backend", "database", "cloud_tools", "other"):
        if getattr(structured.skills, key):
            skill_cats.append(key)

    return visible, skill_cats
