"""ATS score and skill-match heuristics for resume YAML."""

from __future__ import annotations

import re
from typing import Any

import yaml

from ppd.schema import Resume

SENIOR_KEYWORDS = {
    "lead", "leadership", "mentor", "architect", "strategy", "stakeholder",
    "cross-functional", "scale", "roadmap", "team", "senior", "principal",
}
METRIC_PATTERN = re.compile(r"\d+\s*%|\d+\+\s*years|\$\d|#\d|\d+\s*(users|customers|projects)", re.I)
COMMON_SKILLS = {
    "python", "javascript", "typescript", "java", "sql", "react", "node",
    "aws", "azure", "docker", "kubernetes", "git", "agile", "scrum",
    "leadership", "communication", "excel", "project management",
}


def parse_resume_yaml(text: str) -> Resume | None:
    try:
        raw = yaml.safe_load(text)
        if not isinstance(raw, dict):
            return None
        if "resume" in raw:
            from ppd.resume_v2 import ResumeDocument, structured_to_legacy

            structured = ResumeDocument.model_validate(raw).resume
            return structured_to_legacy(structured)
        if "basics" not in raw:
            return None
        return Resume.model_validate(raw)
    except Exception:
        return None


def _all_text(resume: Resume) -> str:
    parts = [resume.basics.name or "", resume.basics.title or "", resume.summary or ""]
    for job in resume.experience:
        parts.extend([job.role, job.company, *job.bullets])
    for edu in resume.education:
        parts.extend([edu.degree, edu.institution, *edu.details])
    for group in resume.skills:
        parts.extend(group.items)
    return " ".join(parts).lower()


def _collect_skills(resume: Resume) -> set[str]:
    skills: set[str] = set()
    for group in resume.skills:
        for item in group.items:
            skills.add(item.lower().strip())
    return skills


def compute_ats_score(text: str) -> dict[str, Any]:
    """Return ATS score 0-100 and breakdown."""
    resume = parse_resume_yaml(text)
    if not resume:
        return {"score": 0, "label": "Invalid YAML", "checks": []}

    checks: list[dict[str, Any]] = []
    score = 0

    if resume.basics.name and resume.basics.email:
        checks.append({"name": "Contact info", "ok": True, "pts": 15})
        score += 15
    else:
        checks.append({"name": "Contact info", "ok": False, "pts": 0})

    if resume.summary and len(resume.summary) > 40:
        checks.append({"name": "Professional summary", "ok": True, "pts": 15})
        score += 15
    else:
        checks.append({"name": "Professional summary", "ok": False, "pts": 0})

    if resume.experience:
        checks.append({"name": "Work experience", "ok": True, "pts": 20})
        score += 20
        bullets = [b for j in resume.experience for b in j.bullets]
        metric_bullets = sum(1 for b in bullets if METRIC_PATTERN.search(b))
        if metric_bullets >= 2:
            checks.append({"name": "Quantified achievements", "ok": True, "pts": 15})
            score += 15
        elif metric_bullets >= 1:
            checks.append({"name": "Quantified achievements", "ok": True, "pts": 8})
            score += 8
        else:
            checks.append({"name": "Quantified achievements", "ok": False, "pts": 0})
    else:
        checks.append({"name": "Work experience", "ok": False, "pts": 0})

    if resume.skills and sum(len(g.items) for g in resume.skills) >= 5:
        checks.append({"name": "Skills section", "ok": True, "pts": 15})
        score += 15
    else:
        checks.append({"name": "Skills section", "ok": False, "pts": 0})

    if resume.education:
        checks.append({"name": "Education", "ok": True, "pts": 10})
        score += 10
    else:
        checks.append({"name": "Education", "ok": False, "pts": 0})

    body = _all_text(resume)
    action_verbs = sum(1 for v in ("led", "built", "developed", "managed", "created", "improved") if v in body)
    if action_verbs >= 3:
        checks.append({"name": "Action verbs", "ok": True, "pts": 10})
        score += 10
    elif action_verbs >= 1:
        checks.append({"name": "Action verbs", "ok": True, "pts": 5})
        score += 5
    else:
        checks.append({"name": "Action verbs", "ok": False, "pts": 0})

    score = min(100, score)
    if score >= 80:
        label = "High Match"
    elif score >= 60:
        label = "Good Match"
    elif score >= 40:
        label = "Needs Work"
    else:
        label = "Low Match"

    return {"score": score, "label": label, "checks": checks}


def compute_skill_match(text: str, target_role: str = "senior") -> dict[str, Any]:
    resume = parse_resume_yaml(text)
    if not resume:
        return {"percent": 0, "matched": [], "missing": list(COMMON_SKILLS)[:8]}

    have = _collect_skills(resume)
    body = _all_text(resume)
    matched = [s for s in COMMON_SKILLS if s in have or s in body]
    missing = [s for s in COMMON_SKILLS if s not in matched][:8]
    percent = min(100, int(len(matched) / max(len(COMMON_SKILLS), 1) * 100) + 20)
    percent = min(100, percent)

    if target_role == "senior":
        senior_hits = sum(1 for k in SENIOR_KEYWORDS if k in body)
        if senior_hits >= 2:
            percent = min(100, percent + 10)

    return {"percent": percent, "matched": matched[:12], "missing": missing}


def skill_gap_analysis(text: str) -> dict[str, Any]:
    match = compute_skill_match(text)
    return {
        "missing_skills": match["missing"],
        "matched_skills": match["matched"],
        "recommendation": (
            f"Add these keywords to your skills or experience: {', '.join(match['missing'][:5])}"
            if match["missing"]
            else "Your skill coverage looks strong for ATS scanning."
        ),
    }
