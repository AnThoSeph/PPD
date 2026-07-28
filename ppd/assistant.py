"""Local resume assistant — rule-based suggestions + LLM section management."""

from __future__ import annotations

import json
import os
import re
import urllib.request
from typing import Any

import yaml

from ppd.ats import compute_ats_score, compute_skill_match, parse_resume_yaml
from ppd.resume_v2 import (
    CustomSection,
    EducationEntry,
    ProjectEntry,
    ResumeDocument,
    StructuredResume,
    structured_from_dict,
    structured_to_dict,
)

PAST_TENSE_MARKERS = re.compile(r"\b(managed|led|developed|built|created|designed|implemented)\b", re.I)
PRESENT_TENSE_MARKERS = re.compile(r"\b(manage|lead|develop|build|create|design|implement)\b", re.I)


def get_greeting_and_insights(yaml_text: str) -> dict[str, Any]:
    resume = parse_resume_yaml(yaml_text)
    ats = compute_ats_score(yaml_text)
    skills = compute_skill_match(yaml_text)

    name = resume.basics.name if resume else "there"
    message = (
        f"Hi {name.split()[0] if name else 'there'}! I've scanned your resume. "
        f"Your ATS Score is {ats['score']}% ({ats['label']}). "
        f"Skill match is {skills['percent']}%. "
    )
    if ats["score"] < 70:
        message += "Would you like help improving weak sections?"
    else:
        message += "Looking good — want to optimize for senior roles?"

    suggestions = _build_suggestions(yaml_text, ats, skills)
    return {"message": message, "suggestions": suggestions}


def _build_suggestions(yaml_text: str, ats: dict, skills: dict) -> list[dict[str, str]]:
    suggestions: list[dict[str, str]] = []
    resume = parse_resume_yaml(yaml_text)

    if ats["score"] < 85:
        suggestions.append({
            "id": "optimize_senior",
            "label": "Optimize for Senior Roles",
            "icon": "trending_up",
        })

    if resume and _has_tense_issues(yaml_text):
        suggestions.append({
            "id": "fix_tense",
            "label": "Fix Tense Consistency",
            "icon": "spellcheck",
        })

    if skills.get("missing"):
        suggestions.append({
            "id": "add_keywords",
            "label": "Add Missing Keywords",
            "icon": "key",
        })

    if not resume or not resume.summary:
        suggestions.append({
            "id": "add_summary",
            "label": "Add Professional Summary",
            "icon": "notes",
        })

    return suggestions[:4]


def _has_tense_issues(text: str) -> bool:
    past_jobs = False
    present_jobs = False
    raw = yaml.safe_load(text)
    if not isinstance(raw, dict):
        return False
    for job in raw.get("experience", []) or []:
        end = str(job.get("end", "")).lower()
        bullets = " ".join(job.get("bullets", []) or [])
        if end in ("present", "current", "now"):
            if PAST_TENSE_MARKERS.search(bullets):
                present_jobs = True
        else:
            if PRESENT_TENSE_MARKERS.search(bullets):
                past_jobs = True
    return past_jobs or present_jobs


def apply_action(yaml_text: str, action_id: str) -> dict[str, Any]:
    """Apply a suggested improvement and return updated YAML + explanation."""
    resume = parse_resume_yaml(yaml_text)
    if not resume:
        return {"yaml": yaml_text, "message": "Fix YAML errors before applying suggestions."}

    raw = yaml.safe_load(yaml_text)
    if not isinstance(raw, dict):
        return {"yaml": yaml_text, "message": "Invalid YAML structure."}

    if action_id == "add_summary":
        if not raw.get("summary"):
            raw["summary"] = (
                f"{resume.basics.title or 'Professional'} with proven experience delivering "
                "measurable results. Seeking new challenges to apply expertise and drive impact."
            )
        return {
            "yaml": yaml.dump(raw, sort_keys=False, allow_unicode=True, default_flow_style=False),
            "message": "Added a starter professional summary — customize it for your target role.",
        }

    if action_id == "add_keywords":
        skills = compute_skill_match(yaml_text)
        missing = skills.get("missing", [])[:5]
        groups = raw.setdefault("skills", [])
        if groups and isinstance(groups[0], dict):
            items = groups[0].setdefault("items", [])
            for kw in missing:
                title = kw.title() if kw.islower() else kw
                if title not in items:
                    items.append(title)
        else:
            raw["skills"] = [{"category": "Technical", "items": [m.title() for m in missing]}]
        return {
            "yaml": yaml.dump(raw, sort_keys=False, allow_unicode=True, default_flow_style=False),
            "message": f"Added keywords: {', '.join(missing)}. Review placement in skills section.",
        }

    if action_id == "fix_tense":
        exp = raw.get("experience", []) or []
        for job in exp:
            end = str(job.get("end", "")).lower()
            bullets = job.get("bullets", []) or []
            fixed = []
            for b in bullets:
                if end in ("present", "current", "now"):
                    b = re.sub(r"\bManaged\b", "Manage", b)
                    b = re.sub(r"\bLed\b", "Lead", b)
                    b = re.sub(r"\bDeveloped\b", "Develop", b)
                else:
                    b = re.sub(r"\bManage\b", "Managed", b)
                    b = re.sub(r"\bLead\b", "Led", b)
                    b = re.sub(r"\bDevelop\b", "Developed", b)
                fixed.append(b)
            job["bullets"] = fixed
        return {
            "yaml": yaml.dump(raw, sort_keys=False, allow_unicode=True, default_flow_style=False),
            "message": "Adjusted verb tenses — past roles use past tense, current role uses present.",
        }

    if action_id == "optimize_senior":
        exp = raw.get("experience", []) or []
        if exp and exp[0].get("bullets"):
            bullets = exp[0].setdefault("bullets", [])
            line = "Led cross-functional initiatives delivering measurable business impact."
            if line not in bullets:
                bullets.insert(0, line)
        summary = raw.get("summary") or ""
        if "leadership" not in summary.lower():
            raw["summary"] = (summary + " Strong leadership and stakeholder management skills.").strip()
        return {
            "yaml": yaml.dump(raw, sort_keys=False, allow_unicode=True, default_flow_style=False),
            "message": "Added senior-level language to summary and top experience entry.",
        }

    return {"yaml": yaml_text, "message": "Unknown action."}


def chat_response(yaml_text: str, user_message: str) -> str:
    """Simple keyword-based chat replies."""
    msg = user_message.lower()
    ats = compute_ats_score(yaml_text)
    gap = compute_skill_match(yaml_text)

    if "ats" in msg or "score" in msg:
        return f"Your ATS score is {ats['score']}% ({ats['label']}). Focus on quantified bullets and a complete skills section."
    if "skill" in msg or "keyword" in msg:
        missing = gap.get("missing", [])[:5]
        return f"Skill match: {gap['percent']}%. Consider adding: {', '.join(missing) if missing else 'none — looks good'}."
    if "summary" in msg:
        return "A strong summary is 2-3 lines highlighting years of experience, domain expertise, and target role."
    if "help" in msg or "polish" in msg:
        return "Try the suggested action buttons, or ask about ATS score, skills, or summary tips."
    return "I can help with ATS score, keywords, tense fixes, and senior-role optimization. Try a suggested action or ask a specific question."


# ---------------------------------------------------------------------------
# LLM-based section management
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """You are a resume section management assistant. Modify the resume JSON based on the user's natural language request.

The resume follows this JSON schema wrapped in {"resume": { ... }}:

{
  "personal": { "name": "...", "title": "...", "email": "...", "phone": "...", "location": "...", "github": "...", "linkedin": "...", "portfolio": "..." },
  "summary": { "text": "..." },
  "experience": [{ "title": "...", "company": "...", "location": "...", "employment_type": "...", "start_date": "...", "end_date": "...", "bullets": ["..."] }],
  "projects": [{ "name": "...", "technologies": ["..."], "description": "...", "bullets": ["..."] }],
  "skills": { "frontend": ["..."], "backend": ["..."], "database": ["..."], "cloud_tools": ["..."], "other": ["..."] },
  "education": [{ "degree": "...", "field": "...", "institution": "...", "location": "...", "graduation": "...", "gpa": "..." }],
  "certifications": ["..."],
  "custom_sections": [{ "title": "...", "items": ["..."] }],
  "visible_sections": ["personal", "summary", "experience", "projects", "skills", "education", "certifications", "custom_sections"],
  "visible_skill_categories": ["frontend", "backend", "database", "cloud_tools", "other"]
}

RULES:
1. Preserve ALL existing data. Only add, remove, or reorder sections and entries.
2. The visible_sections array controls section DISPLAY ORDER. When adding a section, insert it at the correct position.
3. When creating entries (project entries, experience entries, etc.), generate realistic placeholder content relevant to the person's field/title.
4. For custom sections use: {"title": "...", "items": ["..."]}.
5. Return the COMPLETE updated resume JSON wrapped in {"resume": {...}}.
6. Generate 1-3 follow-up suggestions after the change (e.g. "Add bullet points to Projects").
7. If the request cannot be understood or applied, set modified to false.

Return ONLY valid JSON in this exact format:
{"modified": true/false, "structured": {"resume": {...}}, "reply": "human-readable chat response", "assistant_message": "short technical summary", "suggestions": [{"id": "snake-case-id", "label": "Display text"}]}"""


def _call_openai(system: str, user: str, api_key: str, model: str) -> str | None:
    data = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0.1,
        "response_format": {"type": "json_object"},
    }).encode()
    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            body = json.loads(resp.read())
        return body["choices"][0]["message"]["content"]
    except Exception:
        return None


def _call_anthropic(system: str, user: str, api_key: str, model: str) -> str | None:
    data = json.dumps({
        "model": model,
        "max_tokens": 8192,
        "system": system,
        "messages": [{"role": "user", "content": user}],
    }).encode()
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=data,
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            body = json.loads(resp.read())
        return body["content"][0]["text"]
    except Exception:
        return None


def _call_llm(system: str, user: str) -> str | None:
    openai_key = os.environ.get("OPENAI_API_KEY", "").strip()
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    openai_model = os.environ.get("OPENAI_MODEL", "gpt-4o").strip()
    anthropic_model = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-20250514").strip()

    if openai_key:
        return _call_openai(system, user, openai_key, openai_model)
    if anthropic_key:
        return _call_anthropic(system, user, anthropic_key, anthropic_model)
    return None


def _parse_resume(yaml_text: str) -> StructuredResume:
    try:
        raw = yaml.safe_load(yaml_text) if yaml_text.strip() else {}
        if not isinstance(raw, dict):
            raw = {}
    except Exception:
        raw = {}
    try:
        structured = structured_from_dict(raw)
    except Exception:
        structured = StructuredResume()
    return structured


def _rule_based_structured_chat(
    structured: StructuredResume,
    yaml_text: str,
    user_message: str,
) -> dict[str, Any] | None:
    """Handle common section management requests without an LLM.

    Returns None if the request doesn't match a known pattern.
    """
    msg = user_message.lower().strip()

    # --- Detect section names in the message ---
    section_names = {
        "summary": "summary",
        "experience": "experience",
        "projects": "projects",
        "project": "projects",
        "skills": "skills",
        "skill": "skills",
        "education": "education",
        "certifications": "certifications",
        "certification": "certifications",
        "custom": "custom_sections",
        "languages": "custom_sections",
        "publications": "custom_sections",
        "awards": "custom_sections",
        "certificates": "certifications",
    }

    # --- Determine intent ---
    has_add = any(w in msg for w in ("add ", "create ", "insert "))
    has_remove = any(w in msg for w in ("remove ", "delete ", "remove the "))
    has_move = any(w in msg for w in ("move ", "reorder ", "re-order "))
    has_before = "before" in msg
    has_after = "after" in msg

    if has_add:
        target, ref_sec = _detect_add_section_and_reference(msg, section_names)
        if target:
            position = _detect_position_from_ref(msg, ref_sec or "summary")
            count = _detect_count(msg)
            return _apply_add_section(structured, yaml_text, target, position, count, user_message)

    if has_move and (has_before or has_after):
        found = []
        for kw, sec in section_names.items():
            idx = msg.find(kw)
            if idx != -1:
                found.append((idx, sec))
        found.sort()
        unique = []
        seen = set()
        for _, sec in found:
            if sec not in seen:
                unique.append(sec)
                seen.add(sec)
        if len(unique) >= 2:
            subject, ref = unique[0], unique[1]
        elif len(unique) == 1:
            subject = unique[0]
            ref = _detect_reference_section(msg, section_names, exclude=subject)
        else:
            subject, ref = None, None
        if subject and ref and subject != ref:
            return _apply_reorder(structured, yaml_text, subject, ref, has_before, user_message)

    return None


def _detect_add_section_and_reference(
    msg: str, section_names: dict[str, str]
) -> tuple[str | None, str | None]:
    """Detect which section to add and which reference section is mentioned.

    Returns (target_section, reference_section).
    Uses word position in the message to distinguish target from reference.
    """
    custom_indicators = ["languages", "publications", "awards", "interests", "volunteer"]
    found = []
    for kw, sec in section_names.items():
        idx = msg.find(kw)
        if idx != -1:
            found.append((idx, kw, sec))
    found.sort()

    target = None
    ref = None

    for idx, kw, sec in found:
        if target is None:
            target = sec
        elif sec != target:
            ref = sec
            break

    # Detect custom sections via title-specific keywords
    for indicator in custom_indicators:
        if indicator in msg:
            target = "custom_sections"
            break

    return target, ref


def _detect_reference_section(msg: str, section_names: dict[str, str], exclude: str | None = None) -> str | None:
    """Detect a reference section (after X, before Y), optionally excluding one."""
    for keyword, section in section_names.items():
        if keyword in msg and section != exclude:
            return section
    return None


def _detect_position_from_ref(msg: str, ref_sec: str | None) -> str | None:
    if ref_sec and "after" in msg:
        return f"after_{ref_sec}"
    if ref_sec and "before" in msg:
        return f"before_{ref_sec}"
    if "after" in msg:
        return "after_summary"
    if "before" in msg:
        return "before_personal"
    return "end"


def _detect_count(msg: str) -> int:
    m = re.search(r"(\d+)\s+entries|\b(\d+)\s+items|\b(\d+)\s+bullets?|\bwith\s+(\d+)", msg)
    if m:
        for g in m.groups():
            if g is not None:
                return int(g)
    return 1


def _apply_add_section(
    structured: StructuredResume,
    yaml_text: str,
    section_type: str,
    position: str | None,
    count: int,
    user_message: str,
) -> dict[str, Any]:
    """Add a section to the resume."""
    modified = False
    reply_parts = []
    suggestions = []

    if section_type == "projects":
        if not structured.projects or len(structured.projects) < count:
            existing_count = len(structured.projects)
            need = max(0, count - existing_count)
            for i in range(need):
                structured.projects.append(ProjectEntry(
                    name=f"Project {existing_count + i + 1}",
                    technologies=["Technology"],
                    description="Project description",
                    bullets=["Key achievement or responsibility"],
                ))
            if need > 0:
                reply_parts.append(f"Added {need} project entries")
                modified = True
        if "projects" not in structured.visible_sections:
            structured.visible_sections.append("projects")
            reply_parts.append("made Projects section visible")

    elif section_type == "custom_sections":
        title = _extract_custom_title(user_message)
        if not any(cs.title.lower() == title.lower() for cs in structured.custom_sections):
            structured.custom_sections.append(CustomSection(
                title=title,
                items=[f"{title} entry"] * count,
            ))
            reply_parts.append(f"Added {title} section with {count} entries")
            modified = True
        if "custom_sections" not in structured.visible_sections:
            structured.visible_sections.append("custom_sections")
            modified = True

    elif section_type == "skills":
        if not any(getattr(structured.skills, cat) for cat in ("frontend", "backend", "database", "cloud_tools", "other")):
            structured.skills.frontend = ["JavaScript", "TypeScript", "React"]
            reply_parts.append("Added starter skills")
            modified = True
        if "skills" not in structured.visible_sections:
            structured.visible_sections.append("skills")
            modified = True

    elif section_type == "education":
        if not structured.education:
            structured.education.append(EducationEntry(
                degree="Bachelor's",
                field="Field of Study",
                institution="University Name",
                location="City, State",
                graduation="YYYY",
            ))
            reply_parts.append("Added education entry")
            modified = True
        if "education" not in structured.visible_sections:
            structured.visible_sections.append("education")
            modified = True

    elif section_type == "certifications":
        if not structured.certifications:
            structured.certifications = ["Certification Name"]
            reply_parts.append("Added certification entry")
            modified = True
        if "certifications" not in structured.visible_sections:
            structured.visible_sections.append("certifications")
            modified = True

    elif section_type == "summary":
        if not structured.summary.text:
            structured.summary.text = (
                f"{structured.personal.name or 'Professional'} with experience delivering results. "
                "Seeking new challenges to apply expertise."
            )
            reply_parts.append("Added professional summary")
            modified = True
        if "summary" not in structured.visible_sections:
            structured.visible_sections.append("summary")
            modified = True

    if not modified:
        return None

    # Ensure visible_sections follows default ordering
    default_order = [
        "personal", "summary", "experience", "projects",
        "skills", "education", "certifications", "custom_sections",
    ]
    structured.visible_sections = [s for s in default_order if s in structured.visible_sections]

    updated_yaml = yaml.dump(
        ResumeDocument(resume=structured).model_dump(mode="json", exclude_none=True),
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
    )
    if modified and not suggestions:
        if structured.projects:
            suggestions.append({"id": "add-projects-bullets", "label": "Add bullet points to Projects"})
        if len(structured.visible_sections) > 1:
            suggestions.append({"id": "reorder-sections", "label": "Reorder sections"})

    report = ". ".join(reply_parts) + "."
    return {
        "reply": report,
        "structured": structured_to_dict(structured),
        "yaml": updated_yaml,
        "suggestions": suggestions,
        "assistant_message": reply_parts[0] if reply_parts else "Applied section changes",
    }


def _extract_custom_title(user_message: str) -> str:
    """Extract a custom section title from user message (e.g. 'Languages', 'Publications')."""
    for word in ("languages", "publications", "awards", "interests", "volunteer"):
        if word in user_message.lower():
            return word.title()
    return "Custom"


def _apply_reorder(
    structured: StructuredResume,
    yaml_text: str,
    subject: str,
    reference: str,
    is_before: bool,
    user_message: str,
) -> dict[str, Any] | None:
    """Reorder visible_sections."""
    current = list(structured.visible_sections)
    if subject not in current or reference not in current:
        return None
    current.remove(subject)
    if is_before:
        idx = current.index(reference)
    else:
        idx = current.index(reference) + 1
    current.insert(idx, subject)
    structured.visible_sections = current
    reply = f"Moved {subject.title()} {'before' if is_before else 'after'} {reference.title()}"
    updated_yaml = yaml.dump(
        ResumeDocument(resume=structured).model_dump(mode="json", exclude_none=True),
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
    )
    suggestions = [
        {"id": "reorder-sections", "label": "Reorder sections further"},
    ]
    return {
        "reply": reply + ".",
        "structured": structured_to_dict(structured),
        "yaml": updated_yaml,
        "suggestions": suggestions,
        "assistant_message": reply,
    }


def chat_response_structured(yaml_text: str, user_message: str) -> dict[str, Any]:
    """Parse YAML → LLM section management → return structured response.

    Returns a dict with keys: reply, structured, yaml, suggestions, assistant_message.
    Falls back to rule-based patterns when no LLM is available.
    Falls back to keyword-based chat when no section intent is detected.
    """
    structured = _parse_resume(yaml_text)

    # --- Try LLM first ---
    structured_json = json.dumps(structured_to_dict(structured), indent=2)
    user_prompt = f"Current resume:\n{structured_json}\n\nUser request:\n{user_message}"
    llm_raw = _call_llm(_SYSTEM_PROMPT, user_prompt)

    if llm_raw:
        try:
            parsed = json.loads(llm_raw)
            if parsed.get("modified") and "structured" in parsed:
                llm_structured = parsed["structured"]
                validated = structured_from_dict(llm_structured)
                updated_yaml = yaml.dump(
                    ResumeDocument(resume=validated).model_dump(mode="json", exclude_none=True),
                    sort_keys=False,
                    allow_unicode=True,
                    default_flow_style=False,
                )
                return {
                    "reply": parsed.get("reply", "Done."),
                    "structured": structured_to_dict(validated),
                    "yaml": updated_yaml,
                    "suggestions": parsed.get("suggestions", []),
                    "assistant_message": parsed.get("assistant_message", ""),
                }
        except (json.JSONDecodeError, Exception):
            pass

    # --- Fallback: rule-based section management ---
    rule_result = _rule_based_structured_chat(structured, yaml_text, user_message)
    if rule_result:
        return rule_result

    # --- Fallback: keyword-based chat reply ---
    reply = chat_response(yaml_text, user_message)
    return {
        "reply": reply,
        "structured": structured_to_dict(structured),
        "yaml": yaml_text,
        "suggestions": [],
        "assistant_message": "",
    }
