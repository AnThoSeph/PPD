"""Local resume assistant — rule-based suggestions (no API key required)."""

from __future__ import annotations

import re
from typing import Any

import yaml

from ppd.ats import compute_ats_score, compute_skill_match, parse_resume_yaml

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
