"""Resume YAML schema and validation."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, Field, field_validator


class Link(BaseModel):
    label: str
    url: str


class Basics(BaseModel):
    name: str
    title: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    links: list[Link] = Field(default_factory=list)


class ExperienceItem(BaseModel):
    company: str
    role: str
    location: Optional[str] = None
    start: str
    end: str = "present"
    bullets: list[str] = Field(default_factory=list)


class EducationItem(BaseModel):
    institution: str
    degree: str
    location: Optional[str] = None
    start: Optional[str] = None
    end: Optional[str] = None
    details: list[str] = Field(default_factory=list)


class SkillGroup(BaseModel):
    category: str
    items: list[str]


class ProjectItem(BaseModel):
    name: str
    url: Optional[str] = None
    description: Optional[str] = None
    bullets: list[str] = Field(default_factory=list)


class CertificationItem(BaseModel):
    name: str
    issuer: Optional[str] = None
    date: Optional[str] = None


class Resume(BaseModel):
    basics: Basics
    summary: Optional[str] = None
    experience: list[ExperienceItem] = Field(default_factory=list)
    education: list[EducationItem] = Field(default_factory=list)
    skills: list[SkillGroup] = Field(default_factory=list)
    projects: list[ProjectItem] = Field(default_factory=list)
    certifications: list[CertificationItem] = Field(default_factory=list)

    @field_validator("experience", "education", "skills", mode="before")
    @classmethod
    def none_to_list(cls, value: object) -> object:
        return value if value is not None else []


def load_resume(path: Path) -> Resume:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"{path} must contain a YAML mapping at the top level.")
    return Resume.model_validate(raw)


def dump_resume(resume: Resume, path: Path) -> None:
    data = resume.model_dump(mode="json", exclude_none=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.dump(data, sort_keys=False, allow_unicode=True, default_flow_style=False),
        encoding="utf-8",
    )