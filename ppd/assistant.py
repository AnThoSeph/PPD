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
# LLM-based section management — YAML prompt for Gemini
# ---------------------------------------------------------------------------

_YAML_SYSTEM_PROMPT = """You are a resume YAML editor. Modify the resume YAML based on the user's request.

The resume uses this exact YAML structure:
resume:
  personal:
    name: string
    title: string or null
    email: string or null
    phone: string or null
    location: string or null
    github: string or null
    linkedin: string or null
    portfolio: string or null
  summary:
    text: string or null
  experience:
    - title: string
      company: string
      location: string or null
      employment_type: string or null
      start_date: string
      end_date: string
      bullets: [string]
  projects:
    - name: string
      technologies: [string]
      description: string or null
      bullets: [string]
  skills:
    frontend: [string]
    backend: [string]
    database: [string]
    cloud_tools: [string]
    other: [string]
  education:
    - degree: string
      field: string or null
      institution: string
      location: string or null
      graduation: string or null
      gpa: string or null
  certifications: [string]
  custom_sections:
    - title: string
      items: [string]
  visible_sections: [string]
  visible_skill_categories: [string]

RULES:
1. Preserve ALL existing data. Only modify what the user asks.
2. visible_sections controls the display order of sections. Add new sections at the requested position.
3. When adding entries (projects, experience, etc.), generate realistic placeholder content matching the person's title/field.
4. To rename a built-in section (e.g. "Projects" → "Side Projects"), move its entries into custom_sections with the new title, remove the original section key, and update visible_sections accordingly.
5. Return ONLY the complete updated YAML starting with 'resume:'. No explanations, no markdown."""


# ---------------------------------------------------------------------------
# LLM API callers
# ---------------------------------------------------------------------------

def _call_gemini(system: str, user: str, api_key: str, model: str) -> str | None:
    """Call Gemini with a combined system+user prompt, no JSON mode enforced."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    data = json.dumps({
        "contents": [
            {"role": "user", "parts": [{"text": f"{system}\n\n{user}"}]},
        ],
        "generationConfig": {
            "temperature": 0.1,
        },
    }).encode()
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            body = json.loads(resp.read())
        return body["candidates"][0]["content"]["parts"][0]["text"]
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Response building helpers
# ---------------------------------------------------------------------------

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


def _extract_yaml_from_llm_output(text: str) -> str | None:
    """Extract clean YAML from LLM output, stripping code fences and preamble."""
    m = re.search(r'```(?:yaml)?\s*\n(.*?)\n```', text, re.DOTALL)
    if m:
        return m.group(1).strip()
    m = re.search(r'^(resume:.*)$', text, re.DOTALL | re.MULTILINE)
    if m:
        return m.group(1).strip()
    if text.strip().startswith("resume:"):
        return text.strip()
    return None


def _generate_reply_and_suggestions(
    old: StructuredResume, new: StructuredResume, user_message: str
) -> tuple[str, str, list[dict[str, str]]]:
    """Diff old vs new to build a human reply, assistant_message, and suggestions."""
    parts = []
    suggestions: list[dict[str, str]] = []

    # Projects
    if new.projects and not old.projects:
        parts.append(f"Added Projects section with {len(new.projects)} entries")
        suggestions.append({"id": "add-project-bullets", "label": "Add bullet points to Projects"})
    elif len(new.projects) > len(old.projects):
        added = len(new.projects) - len(old.projects)
        parts.append(f"Added {added} project(s)")
        suggestions.append({"id": "add-project-bullets", "label": "Add bullet points to Projects"})

    # Custom sections
    old_titles = {cs.title.lower() for cs in old.custom_sections}
    for cs in new.custom_sections:
        if cs.title.lower() not in old_titles:
            parts.append(f"Added {cs.title} section")
            sid = cs.title.lower().replace(" ", "-")
            suggestions.append({"id": f"add-items-to-{sid}", "label": f"Add items to {cs.title}"})

    # Summary
    if new.summary.text and not old.summary.text:
        parts.append("Added professional summary")
        suggestions.append({"id": "refine-summary", "label": "Refine your professional summary"})

    # Education
    if new.education and not old.education:
        parts.append("Added education entry")
        suggestions.append({"id": "add-education-details", "label": "Add details to Education"})

    # Certifications
    if new.certifications and not old.certifications:
        parts.append("Added certifications")

    # Experience
    if new.experience and not old.experience:
        parts.append("Added experience entries")

    # Skills
    old_has_skills = any(getattr(old.skills, cat) for cat in ("frontend", "backend", "database", "cloud_tools", "other"))
    new_has_skills = any(getattr(new.skills, cat) for cat in ("frontend", "backend", "database", "cloud_tools", "other"))
    if new_has_skills and not old_has_skills:
        parts.append("Added skills section")
        suggestions.append({"id": "organize-skills", "label": "Organize skills by category"})

    # Reorder
    if new.visible_sections != old.visible_sections and not parts:
        parts.append("Reordered sections")
        suggestions.append({"id": "refine-content", "label": "Refine section content"})

    # Rename detection: old section missing, matching custom section present
    if not parts:
        old_secs = set(old.visible_sections)
        new_secs = set(new.visible_sections)
        removed = old_secs - new_secs
        added_custom = {cs.title.lower() for cs in new.custom_sections} - {cs.title.lower() for cs in old.custom_sections}
        if removed and added_custom:
            parts.append(f"Renamed {', '.join(sorted(removed))} section")
            suggestions.append({"id": "refine-content", "label": "Refine renamed section content"})

    if not parts:
        parts.append("Applied changes")
        suggestions = [
            {"id": "refine-content", "label": "Refine any section content"},
            {"id": "ats-optimize", "label": "Optimize for ATS scoring"},
        ]

    reply = ". ".join(parts) + "."
    assistant_message = parts[0]
    return reply, assistant_message, suggestions[:3]


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def chat_response_structured(yaml_text: str, user_message: str) -> dict[str, Any]:
    """Parse YAML → Gemini → return structured response.

    Priority:
    1. Gemini with YAML prompt
    2. Rule-based fallback for common patterns
    3. Keyword-based chat fallback
    """
    structured = _parse_resume(yaml_text)
    current_yaml = yaml.dump(
        ResumeDocument(resume=structured).model_dump(mode="json", exclude_none=True),
        sort_keys=False, allow_unicode=True, default_flow_style=False,
    )

    # --- 1. Gemini with YAML prompt ---
    gemini_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if gemini_key:
        gemini_model = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash").strip()
        user_prompt = (
            f"The user requested: \"{user_message}\"\n\n"
            f"Here is the current resume YAML:\n{current_yaml}\n\n"
            f"Modify the resume YAML to fulfill the request. "
            f"Return ONLY the complete updated YAML starting with 'resume:'."
        )
        llm_raw = _call_gemini(_YAML_SYSTEM_PROMPT, user_prompt, gemini_key, gemini_model)
        if llm_raw:
            yaml_str = _extract_yaml_from_llm_output(llm_raw)
            if yaml_str:
                try:
                    parsed = yaml.safe_load(yaml_str)
                    if isinstance(parsed, dict):
                        validated = structured_from_dict(parsed)
                        updated_yaml = yaml.dump(
                            ResumeDocument(resume=validated).model_dump(mode="json", exclude_none=True),
                            sort_keys=False, allow_unicode=True, default_flow_style=False,
                        )
                        reply, asst_msg, suggestions = _generate_reply_and_suggestions(
                            structured, validated, user_message
                        )
                        return {
                            "reply": reply,
                            "structured": structured_to_dict(validated),
                            "yaml": updated_yaml,
                            "suggestions": suggestions,
                            "assistant_message": asst_msg,
                        }
                except Exception:
                    pass

    # --- 2. Rule-based fallback ---
    rule_result = _rule_based_structured_chat(structured, yaml_text, user_message)
    if rule_result:
        return rule_result

    # --- 3. Keyword-based chat fallback ---
    reply = chat_response(yaml_text, user_message)
    return {
        "reply": reply,
        "structured": structured_to_dict(structured),
        "yaml": yaml_text,
        "suggestions": [],
        "assistant_message": "",
    }


# ---------------------------------------------------------------------------
# Rule-based fallback (used when no LLM is available)
# ---------------------------------------------------------------------------

def _rule_based_structured_chat(
    structured: StructuredResume,
    yaml_text: str,
    user_message: str,
) -> dict[str, Any] | None:
    """Handle common section management requests without an LLM.

    Returns None if the request doesn't match a known pattern.
    """
    msg = user_message.lower().strip()

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

    has_add = any(w in msg for w in ("add ", "create ", "insert "))
    has_remove = any(w in msg for w in ("remove ", "delete ", "remove the "))
    has_move = any(w in msg for w in ("move ", "reorder ", "re-order "))
    has_rename = "rename" in msg
    has_before = "before" in msg
    has_after = "after" in msg
    has_under = any(w in msg for w in (" under ", " below "))

    if has_add:
        target, ref_sec = _detect_add_section_and_reference(msg, section_names, user_message)
        if target:
            position = _detect_position_from_ref(msg, ref_sec or "summary")
            count = _detect_count(msg)
            return _apply_add_section(structured, yaml_text, target, position, count, user_message)

    if has_rename:
        result = _handle_rename(structured, yaml_text, msg, user_message)
        if result:
            return result

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


def _handle_rename(
    structured: StructuredResume,
    yaml_text: str,
    msg: str,
    user_message: str,
) -> dict[str, Any] | None:
    """Rename a section by moving its data into custom_sections."""
    words = msg.split()
    source_sec = None
    new_title = None

    # Find "rename <src> to <title>" pattern
    for i, w in enumerate(words):
        if w == "rename" and i + 3 < len(words):
            for kw, sec in (("summary", "summary"), ("experience", "experience"),
                            ("projects", "projects"), ("skills", "skills"),
                            ("education", "education"), ("certifications", "certifications")):
                if kw in words[i:i+3]:
                    source_sec = sec
                    break
            for j in range(i + 1, len(words)):
                if words[j] == "to" and j + 1 < len(words):
                    new_title = " ".join(words[j+1:]).strip(" ,.").title()
                    break
            break

    if not source_sec or not new_title:
        return None

    if any(cs.title.lower() == new_title.lower() for cs in structured.custom_sections):
        return {
            "reply": f"A section named '{new_title}' already exists.",
            "structured": structured_to_dict(structured),
            "yaml": yaml_text,
            "suggestions": [{"id": "choose-different-name", "label": "Choose a different name"}],
            "assistant_message": "Rename failed — duplicate name",
        }

    items = []
    if source_sec == "projects" and structured.projects:
        for p in structured.projects:
            items.append(f"{p.name}: {'; '.join(p.bullets) if p.bullets else p.description or ''}")
        structured.projects = []
    elif source_sec == "experience" and structured.experience:
        for e in structured.experience:
            items.append(f"{e.title} at {e.company}: {'; '.join(e.bullets)}")
        structured.experience = []
    elif source_sec == "education" and structured.education:
        for edu in structured.education:
            items.append(f"{edu.degree} in {edu.field or ''} at {edu.institution}")
        structured.education = []
    elif source_sec == "certifications" and structured.certifications:
        items = structured.certifications[:]
        structured.certifications = []
    elif source_sec == "summary" and structured.summary.text:
        items = [structured.summary.text]
        structured.summary.text = None
    elif source_sec == "skills":
        for cat in ("frontend", "backend", "database", "cloud_tools", "other"):
            items.extend(getattr(structured.skills, cat))
            setattr(structured.skills, cat, [])
    else:
        return None

    structured.custom_sections.append(CustomSection(title=new_title, items=items))
    if source_sec in structured.visible_sections:
        structured.visible_sections.remove(source_sec)
    if "custom_sections" not in structured.visible_sections:
        structured.visible_sections.append("custom_sections")

    updated_yaml = yaml.dump(
        ResumeDocument(resume=structured).model_dump(mode="json", exclude_none=True),
        sort_keys=False, allow_unicode=True, default_flow_style=False,
    )
    reply = f"Renamed {source_sec.title()} to {new_title}"
    return {
        "reply": reply + ".",
        "structured": structured_to_dict(structured),
        "yaml": updated_yaml,
        "suggestions": [{"id": "refine-content", "label": f"Refine {new_title} content"}],
        "assistant_message": reply,
    }


def _detect_add_section_and_reference(
    msg: str, section_names: dict[str, str], user_message: str = ""
) -> tuple[str | None, str | None]:
    words = msg.split()
    target = None
    ref = None

    add_keywords = {"add", "create", "insert"}
    stop_words = {"a", "an", "the", "new"}
    section_word = None
    add_idx = None
    for i, w in enumerate(words):
        raw = w.strip(" ,.:;!?,")
        if raw in add_keywords:
            add_idx = i
            for j in range(i + 1, min(i + 5, len(words))):
                raw_j = words[j].strip(" ,.:;!?,")
                if raw_j in ("section", "sections"):
                    if j > i + 1:
                        between = [words[k].strip(" ,.:;!?,") for k in range(i + 1, j)]
                        meaningful = [w for w in between if w.lower() not in stop_words]
                        candidate = (meaningful[0] if meaningful else between[0]).lower()
                        section_word = candidate
                    break

    if section_word:
        for kw, sec in section_names.items():
            if section_word in kw or kw.startswith(section_word) or section_word.startswith(kw):
                target = sec
                break
        known_custom = {"languages", "publications", "awards", "interests",
                        "volunteer", "hobbies", "references", "surname"}
        if target is None and section_word in known_custom:
            target = "custom_sections"
        if target is None and section_word not in stop_words:
            target = "custom_sections"
        if target is None and section_word in stop_words and add_idx is not None:
            for k in range(add_idx + 1, min(add_idx + 5, len(words))):
                if words[k].strip(" ,.:;!?,") not in stop_words:
                    candidate = words[k].strip(" ,.:;!?,").lower()
                    section_word = candidate
                    target = "custom_sections"
                    break

    # Fallback: if no "section" keyword but a known section name follows "add"
    if target is None and add_idx is not None:
        for k in range(add_idx + 1, min(add_idx + 4, len(words))):
            word = words[k].strip(" ,.:;!?,").lower()
            for kw, sec in section_names.items():
                if word == kw or word in kw or kw.startswith(word):
                    target = sec
                    break
            if target:
                break

    pos_keywords = {"after", "below", "under", "before"}
    for i, w in enumerate(words):
        raw_w = w.strip(" ,.:;!?,")
        if raw_w in pos_keywords and i + 1 < len(words):
            candidate = words[i + 1].strip(" ,.:;!?,").lower()
            for kw, sec in section_names.items():
                if candidate in kw or candidate.startswith(kw) or kw.startswith(candidate):
                    if sec != target:
                        ref = sec
                    break

    return target, ref


def _detect_reference_section(msg: str, section_names: dict[str, str], exclude: str | None = None) -> str | None:
    for keyword, section in section_names.items():
        if keyword in msg and section != exclude:
            return section
    return None


def _detect_position_from_ref(msg: str, ref_sec: str | None) -> str | None:
    has_after = "after" in msg or " below " in msg
    has_before = "before" in msg or " under " in msg
    if ref_sec and has_after:
        return f"after_{ref_sec}"
    if ref_sec and has_before:
        return f"before_{ref_sec}"
    if has_after:
        return "after_summary"
    if has_before:
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

    default_order = [
        "personal", "summary", "experience", "projects",
        "skills", "education", "certifications", "custom_sections",
    ]
    structured.visible_sections = [s for s in default_order if s in structured.visible_sections]

    updated_yaml = yaml.dump(
        ResumeDocument(resume=structured).model_dump(mode="json", exclude_none=True),
        sort_keys=False, allow_unicode=True, default_flow_style=False,
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


def _extract_custom_title(user_message: str, msg_lower: str | None = None) -> str:
    m = (msg_lower or user_message.lower())
    known_words = ("languages", "publications", "awards", "interests", "volunteer", "hobbies", "references", "surname")
    for word in known_words:
        if word in m:
            return word.title()

    words = m.split()
    for i, w in enumerate(words):
        w_clean = w.strip(" ,.:;!?")
        if w_clean in ("add", "create", "insert", "new"):
            for j in range(i + 1, min(i + 5, len(words))):
                wj_clean = words[j].strip(" ,.:;!?")
                if wj_clean in ("section", "sections"):
                    if j > i + 1:
                        between = [words[k].strip(" ,.:;!?") for k in range(i + 1, j)]
                        meaningful = [b for b in between if b not in ("a", "an", "the", "new")]
                        if meaningful:
                            return " ".join(meaningful).title()
                    for k in range(j + 1, min(j + 4, len(words))):
                        wk_clean = words[k].strip(" ,.:;!?")
                        if wk_clean and wk_clean not in (
                            "under", "below", "after", "before", "with", "and", "or", "the", "a", "an"
                        ):
                            return wk_clean.title()
                        if wk_clean in ("under", "below", "after", "before"):
                            break
                    break
    for i, w in enumerate(words):
        if w.strip(" ,.:;!?") == "section" and i + 1 < len(words):
            cand = words[i + 1].strip(" ,.:;!?")
            if cand and cand not in ("with", "called", "named", "below", "under", "after", "before", "and", "or", "the"):
                return cand.title()
    return "Custom"


def _apply_reorder(
    structured: StructuredResume,
    yaml_text: str,
    subject: str,
    reference: str,
    is_before: bool,
    user_message: str,
) -> dict[str, Any] | None:
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
        sort_keys=False, allow_unicode=True, default_flow_style=False,
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
