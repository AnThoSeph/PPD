"""Semantic PDF → StructuredResume parser."""

from __future__ import annotations

import re
from pathlib import Path

from ppd.import_pdf import extract_text_lines, lines_to_resume, _parse_date_range, _is_bullet, _clean_bullet
from ppd.resume_v2 import (
    CustomSection,
    EducationEntry,
    ExperienceEntry,
    PersonalInfo,
    ProjectEntry,
    SkillsBlock,
    StructuredResume,
    SummaryBlock,
    compute_visible_sections,
    legacy_to_structured,
)

SECTION_MAP = {
    "summary": (
        "summary", "profile", "about me", "about", "objective", "professional summary",
        "career summary", "personal statement",
    ),
    "experience": (
        "experience", "work experience", "employment", "work history", "professional experience",
        "career history", "employment history",
    ),
    "projects": ("projects", "personal projects", "key projects", "selected projects", "academic projects"),
    "skills": ("skills", "technical skills", "core skills", "technologies", "expertise", "competencies"),
    "education": ("education", "academic background", "qualifications", "academic"),
    "certifications": ("certifications", "certificates", "licenses", "licences", "credentials", "courses"),
}

CUSTOM_HEADINGS = (
    "awards", "achievements", "honors", "honours", "volunteer", "languages", "organizations",
    "interests", "publications", "references", "patents", "leadership", "hobbies", "research",
)

SKILL_BUCKETS = {
    "frontend": {"react", "vue", "angular", "html", "css", "javascript", "typescript", "next.js", "responsive"},
    "backend": {"node", "node.js", "express", "python", "django", "flask", "java", "spring", "rest", "api", "rasa"},
    "database": {"sql", "mongodb", "postgres", "mysql", "redis", "database"},
    "cloud_tools": {"aws", "azure", "gcp", "firebase", "docker", "kubernetes", "git", "github", "postman", "ci/cd"},
}


def _normalize_heading(line: str) -> str:
    return re.sub(r"[^a-z ]", "", line.lower()).strip()


def _map_section(line: str) -> tuple[str, str | None]:
    norm = _normalize_heading(line)
    if not norm or len(norm) > 50:
        return "body", None
    for key, keywords in SECTION_MAP.items():
        if any(norm == kw or norm.startswith(kw) or kw in norm for kw in keywords):
            return key, None
    for custom in CUSTOM_HEADINGS:
        if custom in norm:
            return "custom", line.strip()
    if norm.isupper() and len(norm.split()) <= 4:
        return "custom", line.strip()
    return "body", None


def _parse_sections(lines: list[str]) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {"header": []}
    custom: dict[str, list[str]] = {}
    current = "header"
    custom_title: str | None = None

    for line in lines:
        key, custom_name = _map_section(line)
        if key == "custom" and custom_name:
            current = "custom"
            custom_title = custom_name
            custom.setdefault(custom_title, [])
            continue
        if key != "body":
            current = key
            custom_title = None
            sections.setdefault(current, [])
            continue
        if current == "custom" and custom_title:
            custom.setdefault(custom_title, []).append(line)
        else:
            sections.setdefault(current, []).append(line)

    if custom:
        sections["_custom"] = []
        for title, items in custom.items():
            sections["_custom"].append(f"__TITLE__:{title}")
            sections["_custom"].extend(items)
    return sections


def _parse_contact(lines: list[str]) -> PersonalInfo:
    personal = PersonalInfo()
    if not lines:
        return personal
    personal.name = lines[0]
    for line in lines[1:8]:
        lower = line.lower()
        if "|" in line:
            for part in line.split("|"):
                p = part.strip()
                pl = p.lower()
                if "@" in p and not personal.email:
                    personal.email = p
                elif re.search(r"\+?\d[\d\s().-]{7,}", p) and not personal.phone:
                    personal.phone = p
                elif "github" in pl and not personal.github:
                    personal.github = p.split(":")[-1].strip()
                elif "linkedin" in pl and not personal.linkedin:
                    personal.linkedin = p.split(":")[-1].strip()
                elif "," in p and not personal.location:
                    personal.location = p
        elif "@" in line:
            personal.email = line.strip()
        elif re.search(r"\+?\d[\d\s().-]{7,}", line):
            personal.phone = line.strip()
        elif "github" in lower:
            personal.github = line.split(":")[-1].strip()
        elif "linkedin" in lower:
            personal.linkedin = line.split(":")[-1].strip()
        elif not personal.title and len(line) < 80:
            personal.title = line
    return personal


def _parse_experience(lines: list[str]) -> list[ExperienceEntry]:
    entries: list[ExperienceEntry] = []
    title = company = None
    start = end = None
    bullets: list[str] = []

    def flush() -> None:
        nonlocal title, company, start, end, bullets
        if title or company or bullets:
            entries.append(
                ExperienceEntry(
                    title=title or "Role",
                    company=company or "Company",
                    start_date=start or "YYYY",
                    end_date=end or "present",
                    bullets=bullets[:],
                )
            )
        title = company = start = end = None
        bullets = []

    for line in lines:
        s = line.strip()
        if not s:
            continue
        if _is_bullet(s):
            bullets.append(_clean_bullet(s))
            continue
        dr = _parse_date_range(s)
        if dr:
            start, end = dr
            continue
        if title and not company:
            company = s
            continue
        if not title:
            title = s
            continue
        if bullets:
            bullets[-1] = f"{bullets[-1]} {s}".strip()
        else:
            bullets.append(s)
    flush()
    return entries


def _parse_projects(lines: list[str]) -> list[ProjectEntry]:
    projects: list[ProjectEntry] = []
    name = tech_line = None
    bullets: list[str] = []

    def flush() -> None:
        nonlocal name, tech_line, bullets
        if name:
            techs = [t.strip() for t in re.split(r",|/|·", tech_line or "") if t.strip()]
            projects.append(ProjectEntry(name=name, technologies=techs, bullets=bullets[:]))
        name = tech_line = None
        bullets = []

    for line in lines:
        s = line.strip()
        if not s:
            continue
        if _is_bullet(s):
            bullets.append(_clean_bullet(s))
            continue
        if not name:
            name = s
        elif not tech_line and ("," in s or len(s) < 60):
            tech_line = s
        elif name and not bullets:
            tech_line = s
        else:
            bullets.append(s)
    flush()
    return projects


def _categorize_skill(item: str) -> str:
    lower = item.lower()
    for bucket, keywords in SKILL_BUCKETS.items():
        if any(k in lower for k in keywords):
            return bucket
    return "other"


def _parse_skills(lines: list[str]) -> SkillsBlock:
    block = SkillsBlock()
    current: str | None = None

    def add(item: str) -> None:
        item = item.strip()
        if not item:
            return
        bucket = current or _categorize_skill(item)
        if bucket == "frontend":
            block.frontend.append(item)
        elif bucket == "backend":
            block.backend.append(item)
        elif bucket == "database":
            block.database.append(item)
        elif bucket == "cloud_tools":
            block.cloud_tools.append(item)
        else:
            block.other.append(item)

    for line in lines:
        s = line.strip()
        if not s:
            continue
        if s.endswith(":"):
            label = s[:-1].lower()
            if "front" in label:
                current = "frontend"
            elif "back" in label:
                current = "backend"
            elif "data" in label:
                current = "database"
            elif "cloud" in label or "tool" in label:
                current = "cloud_tools"
            else:
                current = "other"
            continue
        if ":" in s and len(s.split(":")[0]) < 25:
            label, rest = s.split(":", 1)
            label_l = label.lower()
            if "front" in label_l:
                current = "frontend"
            elif "back" in label_l:
                current = "backend"
            elif "data" in label_l:
                current = "database"
            elif "cloud" in label_l or "tool" in label_l:
                current = "cloud_tools"
            else:
                current = "other"
            for part in re.split(r",|/|·", rest):
                add(part)
            continue
        for part in re.split(r",|/|·", s):
            add(part)
    return block


def _parse_education(lines: list[str]) -> list[EducationEntry]:
    entries: list[EducationEntry] = []
    degree = institution = grad = gpa = None

    def flush() -> None:
        nonlocal degree, institution, grad, gpa
        if degree or institution:
            entries.append(
                EducationEntry(
                    degree=degree or "Degree",
                    institution=institution or "Institution",
                    graduation=grad,
                    gpa=gpa,
                )
            )
        degree = institution = grad = gpa = None

    for line in lines:
        s = line.strip()
        if not s:
            continue
        if s.lower().startswith("gpa"):
            gpa = s
            continue
        if re.fullmatch(r"\d{1,2}/\d{4}|\d{4}", s):
            grad = re.search(r"\d{4}", s).group(0)
            if degree and institution:
                flush()
            continue
        if not degree or "bachelor" in s.lower() or "engineering" in s.lower() or "board" in s.lower():
            if degree and institution:
                flush()
            degree = s
        elif not institution:
            institution = s
    flush()
    return entries


def _parse_custom(lines: list[str]) -> list[CustomSection]:
    sections: list[CustomSection] = []
    title: str | None = None
    items: list[str] = []

    def flush() -> None:
        nonlocal title, items
        if title:
            sections.append(CustomSection(title=title, items=items[:]))
        title = None
        items = []

    for line in lines:
        if line.startswith("__TITLE__:"):
            flush()
            title = line.split(":", 1)[1]
            continue
        s = _clean_bullet(line) if _is_bullet(line) else line.strip()
        if s:
            items.append(s)
    flush()
    return sections


def lines_to_structured(lines: list[str]) -> StructuredResume:
    sections = _parse_sections(lines)
    found_headings = {k for k in sections if k not in ("header", "_custom")}

    legacy = lines_to_resume(lines)
    structured = legacy_to_structured(legacy)
    custom = _parse_custom(sections.pop("_custom", []))
    if custom:
        structured.custom_sections = custom
        found_headings.add("_custom")

    contact = _parse_contact(sections.get("header", lines[:6]))
    if contact.name and contact.name != "Your Name":
        structured.personal = contact

    visible, skill_cats = compute_visible_sections(structured, found_headings)
    structured.visible_sections = visible
    structured.visible_skill_categories = skill_cats
    return structured


def import_pdf_structured(pdf_path: Path, output_yaml: Path, raw_txt: Path) -> StructuredResume:
    lines = extract_text_lines(pdf_path)
    raw_txt.parent.mkdir(parents=True, exist_ok=True)
    raw_txt.write_text("\n".join(lines), encoding="utf-8")
    if not lines:
        raise ValueError("PDF contains no readable text.")
    structured = lines_to_structured(lines)
    from ppd.resume_v2 import dump_structured

    dump_structured(structured, output_yaml)
    return structured
