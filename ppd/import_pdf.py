"""Import resume content from a PDF into draft YAML."""

from __future__ import annotations

import re
from pathlib import Path

import fitz
import yaml

from ppd.schema import Basics, EducationItem, ExperienceItem, Link, ProjectItem, Resume, SkillGroup, dump_resume

SECTION_KEYWORDS = {
    "summary": (
        "summary", "profile", "about me", "about", "objective",
        "professional summary", "career summary", "personal statement",
    ),
    "experience": (
        "experience", "work experience", "employment", "work history",
        "professional experience", "career history", "employment history",
    ),
    "education": ("education", "academic", "qualifications", "academic background"),
    "skills": ("skills", "technical skills", "core competencies", "expertise", "competencies"),
    "projects": ("projects", "personal projects", "key projects", "selected projects"),
    "certifications": ("certifications", "certificates", "licenses", "licences", "credentials"),
}

MONTH = r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?"
DATE_TOKEN = rf"(?:\d{{1,2}}/\d{{4}}|{MONTH}\s+\d{{4}}|\d{{4}}|present|current|now)"
DATE_RANGE_RE = re.compile(rf"^\s*({DATE_TOKEN})\s+(?:to|[-–—])\s+({DATE_TOKEN})\s*$", re.I)
DATE_IN_LINE = re.compile(DATE_TOKEN, re.I)
BULLET_RE = re.compile(r"^[•●▪*·\-]\s*")
ROLE_HINT = re.compile(
    r"\b(engineer|developer|trainer|manager|analyst|intern|consultant|lead|architect|designer|specialist|associate|director|officer|coordinator)\b",
    re.I,
)
DEGREE_RE = re.compile(
    r"\b(bachelor|master|b\.?e|b\.?tech|m\.?e|bsc|msc|mba|ph\.?d|diploma|associate|engineering|degree|secondary|higher secondary|examination board|school)\b",
    re.I,
)


def _normalize_heading(line: str) -> str:
    return re.sub(r"[^a-z ]", "", line.lower()).strip()


def _match_section(line: str) -> str | None:
    norm = _normalize_heading(line)
    if not norm or len(norm) > 45:
        return None
    for section, keywords in SECTION_KEYWORDS.items():
        if any(norm == kw or norm.startswith(kw) or kw in norm for kw in keywords):
            return section
    return None


def _is_bullet_continuation(line: str) -> bool:
    s = line.strip()
    if not s:
        return False
    if s[0].islower():
        return True
    return len(s.split()) <= 5 and s.endswith(".")


def _is_bullet(line: str) -> bool:
    s = line.strip()
    return bool(BULLET_RE.match(s)) or s in {"•", "·", "-", "*", "●"}


def _clean_bullet(line: str) -> str:
    return BULLET_RE.sub("", line.strip()).strip()


def extract_text_lines(pdf_path: Path) -> list[str]:
    """Extract text in top-to-bottom reading order (all pages)."""
    doc = fitz.open(pdf_path)
    lines: list[str] = []

    for page in doc:
        spans: list[tuple[float, float, str]] = []
        for block in page.get_text("dict").get("blocks", []):
            if block.get("type") != 0:
                continue
            for line in block.get("lines", []):
                text = "".join(span.get("text", "") for span in line.get("spans", [])).strip()
                if text:
                    bbox = line.get("bbox", [0, 0, 0, 0])
                    spans.append((bbox[1], bbox[0], text))

        spans.sort(key=lambda s: (round(s[0], 0), s[1]))
        for _, _, text in spans:
            for part in text.splitlines():
                part = part.strip()
                if part and part != "•":
                    lines.append(part)

    doc.close()

    if not lines:
        doc = fitz.open(pdf_path)
        for page in doc:
            text = page.get_text("text")
            lines.extend(p.strip() for p in text.splitlines() if p.strip())
        doc.close()

    return lines


def _parse_sections(lines: list[str]) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {"header": []}
    current = "header"
    for i, line in enumerate(lines):
        section = _match_section(line)
        if section:
            current = section
            sections.setdefault(current, [])
            continue
        sections.setdefault(current, []).append(line)

    if not sections.get("header"):
        first_section_idx = len(lines)
        for i, line in enumerate(lines):
            if _match_section(line):
                first_section_idx = i
                break
        sections["header"] = lines[: min(first_section_idx, 6)]
    return sections


def _parse_contact_field(part: str) -> tuple[str, str]:
    part = part.strip()
    lower = part.lower()
    if "@" in part:
        return "email", part
    if re.search(r"\+?\d[\d\s().-]{7,}", part):
        return "phone", part
    if any(x in lower for x in ("linkedin", "github", "http", "www.")):
        label = "LinkedIn" if "linkedin" in lower else "GitHub" if "github" in lower else "Link"
        url = part if part.lower().startswith("http") else f"https://{part.lstrip('wWw.: ')}"
        url = url.replace("LinkedIn:", "").replace("linkedin:", "").strip()
        return "link", f"{label}|{url}"
    if "," in part and len(part) < 80 and "@" not in part:
        return "location", part
    return "other", part


def _guess_basics(header_lines: list[str]) -> Basics:
    name = "Your Name"
    title = email = phone = location = None
    links: list[Link] = []

    for i, line in enumerate(header_lines[:10]):
        stripped = line.strip()
        if not stripped:
            continue

        if "|" in stripped and i <= 2:
            for part in stripped.split("|"):
                kind, value = _parse_contact_field(part)
                if kind == "email" and not email:
                    email = value
                elif kind == "phone" and not phone:
                    phone = re.sub(r"\s+", " ", value).strip()
                elif kind == "location" and not location:
                    location = value
                elif kind == "link":
                    label, url = value.split("|", 1)
                    links.append(Link(label=label, url=url))
            continue

        kind, value = _parse_contact_field(stripped)
        if kind == "email" and not email:
            email = value
        elif kind == "phone" and not phone:
            phone = value
        elif kind == "location" and not location:
            location = value
        elif kind == "link":
            label, url = value.split("|", 1)
            links.append(Link(label=label, url=url))
        elif i == 0 and len(stripped) < 60 and "@" not in stripped:
            name = stripped
        elif not title and 3 < len(stripped) < 80 and kind == "other":
            title = stripped

    return Basics(name=name, title=title, email=email, phone=phone, location=location, links=links)


def _parse_date_range(line: str) -> tuple[str, str] | None:
    m = DATE_RANGE_RE.match(line.strip())
    if m:
        return m.group(1).strip(), m.group(2).strip()
    return None


def _is_date_line(line: str) -> bool:
    s = line.strip()
    if _parse_date_range(s):
        return True
    if len(s) > 50:
        return False
    tokens = DATE_IN_LINE.findall(s)
    return len(tokens) >= 1 and len(s) < 35 and ("to" in s.lower() or "/" in s)


def _looks_like_role(line: str) -> bool:
    s = line.strip()
    if not s or _is_bullet(s) or _match_section(s) or _is_date_line(s):
        return False
    if len(s) > 90 or s.lower().startswith("gpa"):
        return False
    if re.match(r"^\d{1,2}/\d{4}", s):
        return False
    if s[0].islower() or (s.endswith(".") and len(s.split()) <= 4 and not ROLE_HINT.search(s)):
        return False
    if not re.search(r"[A-Z]", s):
        return False
    return bool(ROLE_HINT.search(s) or (len(s.split()) >= 2 and s.istitle()))


def _looks_like_company(line: str) -> bool:
    s = line.strip()
    if not s or _is_bullet(s):
        return False
    markers = ("–", "—", "-", "remote", "inc", "ltd", "llc", "corp", "center", "centre", "university")
    lower = s.lower()
    return any(m in lower for m in markers) or (len(s) < 80 and s[0].isupper() and not _is_date_line(s))


def _parse_experience(lines: list[str]) -> list[ExperienceItem]:
    entries: list[ExperienceItem] = []
    role: str | None = None
    start = "YYYY"
    end = "present"
    company = ""
    bullets: list[str] = []
    pending_bullet = False
    collecting_bullets = False

    def flush() -> None:
        nonlocal role, start, end, company, bullets, pending_bullet, collecting_bullets
        if role or company or bullets:
            entries.append(
                ExperienceItem(
                    company=company or "Company",
                    role=role or "Role",
                    start=start,
                    end=end,
                    bullets=bullets[:],
                )
            )
        role = None
        start = "YYYY"
        end = "present"
        company = ""
        bullets = []
        pending_bullet = False
        collecting_bullets = False

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        if _is_bullet(stripped):
            text = _clean_bullet(stripped)
            collecting_bullets = True
            if text:
                bullets.append(text)
            else:
                pending_bullet = True
            continue

        if pending_bullet:
            bullets.append(stripped)
            pending_bullet = False
            collecting_bullets = True
            continue

        if _match_section(stripped):
            continue

        date_range = _parse_date_range(stripped)
        if date_range:
            if role is None and entries:
                flush()
            start, end = date_range
            continue

        if role and company:
            if _looks_like_role(stripped):
                flush()
                role = stripped
                continue
            if date_range := _parse_date_range(stripped):
                flush()
                role = None
                start, end = date_range
                continue
            if not bullets and _looks_like_company(stripped):
                company = stripped
                continue
            if bullets and _is_bullet_continuation(stripped):
                bullets[-1] = f"{bullets[-1]} {stripped}".strip()
                continue
            bullets.append(stripped)
            collecting_bullets = True
            continue

        if role and not company and _looks_like_company(stripped):
            company = stripped
            continue

        if _looks_like_role(stripped):
            if role or company or bullets:
                flush()
            role = stripped
            continue

        if role and not company and not collecting_bullets:
            company = stripped
            continue

        if role and collecting_bullets and bullets:
            bullets[-1] = f"{bullets[-1]} {stripped}".strip()

    flush()
    return entries


def _parse_education(lines: list[str]) -> list[EducationItem]:
    entries: list[EducationItem] = []
    degree = institution = None
    end = None
    details: list[str] = []
    pending_year: str | None = None

    def flush() -> None:
        nonlocal degree, institution, end, details, pending_year
        if degree or institution:
            entries.append(
                EducationItem(
                    institution=institution or "Institution",
                    degree=degree or "Degree",
                    end=end or pending_year,
                    details=details[:],
                )
            )
        degree = institution = end = None
        details = []
        pending_year = None

    for line in lines:
        stripped = line.strip()
        if not stripped or _match_section(stripped):
            continue

        if stripped.lower().startswith("gpa"):
            details.append(stripped)
            continue

        year_match = re.fullmatch(r"(\d{1,2}/)?(\d{4})", stripped) or re.fullmatch(r"(\d{4})", stripped)
        if year_match and len(stripped) <= 12:
            pending_year = re.search(r"(\d{4})", stripped).group(1)
            if degree and institution:
                end = pending_year
                flush()
            continue

        if DEGREE_RE.search(stripped) or (":" in stripped and DEGREE_RE.search(stripped.split(":")[0])):
            if degree or institution:
                flush()
            degree = stripped.rstrip(":")
            continue

        if degree and not institution:
            institution = stripped
            if pending_year:
                end = pending_year
                pending_year = None
            continue

        if degree:
            details.append(stripped)

    flush()
    return entries


def _parse_skills(lines: list[str]) -> list[SkillGroup]:
    groups: list[SkillGroup] = []
    category: str | None = None
    items: list[str] = []

    def flush() -> None:
        nonlocal category, items
        if category and items:
            groups.append(SkillGroup(category=category, items=items[:]))
        elif items and not category:
            groups.append(SkillGroup(category="Skills", items=items[:]))
        category = None
        items = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.endswith(":") and len(stripped.split(":")[0]) < 35:
            flush()
            category = stripped[:-1].strip()
            continue
        if ":" in stripped and len(stripped.split(":")[0]) < 30:
            flush()
            cat, rest = stripped.split(":", 1)
            category = cat.strip()
            chunk_items = [s.strip() for s in re.split(r",|;|/|·", rest) if s.strip()]
            items.extend(chunk_items)
            continue
        chunk_items = [s.strip() for s in re.split(r",|;|/|·", stripped) if s.strip() and len(s.strip()) < 50]
        items.extend(chunk_items)

    flush()
    return groups


ACTION_VERB = re.compile(
    r"^(Developed|Built|Created|Designed|Implemented|Structured|Guided|Integrated|"
    r"Managed|Led|Worked|Collaborated|Optimized|Deployed|Maintained|Trained|"
    r"Regularly|Created|Delivered|Automated|Configured|Established)\b",
    re.I,
)


def _looks_like_project_title(line: str) -> bool:
    if ACTION_VERB.match(line):
        return False
    if len(line) > 90 or (line.endswith(".") and len(line) > 45):
        return False
    if " – " in line or " - " in line:
        return True
    if re.match(r"^[A-Z][\w\s\-–—:()]+$", line) and 2 <= len(line.split()) <= 10:
        return True
    return False


def _is_wrapped_continuation(line: str) -> bool:
    if not line:
        return False
    if line[0].islower():
        return True
    if len(line.split()) <= 4 and not ACTION_VERB.match(line) and not _looks_like_project_title(line):
        return True
    return False


def _looks_like_tech_stack(line: str) -> bool:
    if "," in line and len(line) < 100 and not ACTION_VERB.match(line):
        return True
    lower = line.lower()
    tech_hints = ("react", "javascript", "python", "java", "node", "rasa", "native", "mongo", "sql", "aws")
    return any(h in lower for h in tech_hints) and len(line) < 80 and line.count(".") == 0


def _parse_projects(lines: list[str]) -> list[ProjectItem]:
    projects: list[ProjectItem] = []
    name: str | None = None
    description: str | None = None
    bullets: list[str] = []

    def flush() -> None:
        nonlocal name, description, bullets
        if name:
            projects.append(ProjectItem(name=name, description=description, bullets=bullets[:]))
        name = description = None
        bullets = []

    for line in lines:
        stripped = line.strip()
        if not stripped or _match_section(stripped):
            continue
        if _is_bullet(stripped):
            bullets.append(_clean_bullet(stripped))
            continue

        if not name:
            name = stripped
            continue

        if _looks_like_project_title(stripped) and (description or bullets):
            flush()
            name = stripped
            continue

        if not description and _looks_like_tech_stack(stripped):
            description = stripped
            continue

        if ACTION_VERB.match(stripped) or bullets or (description and len(stripped) > 25):
            if bullets and _is_wrapped_continuation(stripped):
                bullets[-1] = f"{bullets[-1]} {stripped}".strip()
            else:
                bullets.append(stripped)
            continue

        if _looks_like_project_title(stripped):
            flush()
            name = stripped
            continue

        if not description:
            description = stripped
        else:
            bullets.append(stripped)

    flush()
    return projects


def _parse_certifications(lines: list[str]) -> list[str]:
    certs: list[str] = []
    for line in lines:
        stripped = _clean_bullet(line.strip()) if _is_bullet(line) else line.strip()
        if stripped and not _match_section(stripped):
            certs.append(stripped)
    return certs


def _join_summary(lines: list[str]) -> str | None:
    parts = [ln.strip() for ln in lines if ln.strip() and not _match_section(ln)]
    if not parts:
        return None
    text = " ".join(parts)
    text = re.sub(r"\s+", " ", text).strip()
    return text if text else None


def lines_to_resume(lines: list[str]) -> Resume:
    if not lines:
        raise ValueError("No text could be extracted from the file.")

    sections = _parse_sections(lines)
    header = sections.get("header", lines[:6])
    summary = _join_summary(sections.get("summary", []))
    experience = _parse_experience(sections.get("experience", []))
    education = _parse_education(sections.get("education", []))
    skills = _parse_skills(sections.get("skills", []))
    projects = _parse_projects(sections.get("projects", []))
    cert_lines = _parse_certifications(sections.get("certifications", []))

    from ppd.schema import CertificationItem

    certifications = [CertificationItem(name=c) for c in cert_lines]

    if not experience:
        body = [l for l in lines if l not in header and not _match_section(l)]
        experience = _parse_experience(body[:40])

    return Resume(
        basics=_guess_basics(header),
        summary=summary,
        experience=experience,
        education=education,
        skills=skills,
        projects=projects,
        certifications=certifications,
    )


def import_pdf(pdf_path: Path, output_yaml: Path, raw_txt: Path) -> Resume:
    lines = extract_text_lines(pdf_path)
    raw_txt.parent.mkdir(parents=True, exist_ok=True)
    raw_txt.write_text("\n".join(lines), encoding="utf-8")
    if not lines:
        raise ValueError("PDF contains no readable text. If it is a scan, use an image file instead.")
    resume = lines_to_resume(lines)
    draft_path = output_yaml.with_suffix(".draft.yaml")
    dump_resume(resume, draft_path)
    note = {"note": "Review and rename to resume.yaml after cleanup.", "source_pdf": str(pdf_path)}
    draft_path.write_text(yaml.dump(note, sort_keys=False) + "\n" + draft_path.read_text(encoding="utf-8"), encoding="utf-8")
    return resume
