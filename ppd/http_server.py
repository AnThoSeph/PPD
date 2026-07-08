"""FastAPI REST layer for mobile Flutter clients."""

from __future__ import annotations

import base64
import os
from functools import lru_cache
from typing import Any

from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel

from ppd.api import PPDApi
from ppd.workspace import sanitize_workspace_id

API_KEY = os.environ.get("PPD_API_KEY", "").strip()
ALLOW_OPEN = os.environ.get("PPD_ALLOW_OPEN", "").lower() in {"1", "true", "yes"}


def _require_auth(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> None:
    if ALLOW_OPEN or not API_KEY:
        return
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


def _workspace_id(x_workspace_id: str | None = Header(default="default", alias="X-Workspace-Id")) -> str:
    return sanitize_workspace_id(x_workspace_id or "default")


@lru_cache(maxsize=64)
def _api_for_workspace(workspace_id: str) -> PPDApi:
    return PPDApi(workspace_id=workspace_id)


def get_api(workspace_id: str = Depends(_workspace_id)) -> PPDApi:
    return _api_for_workspace(workspace_id)


def _fail(result: dict[str, Any]) -> None:
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("message", "Request failed"))


class ResumeBody(BaseModel):
    resume: dict[str, Any] | None = None


class YamlBody(BaseModel):
    yaml: str = ""


class PreviewBody(BaseModel):
    resume: dict[str, Any] | None = None
    yaml: str | None = None


class ExportBody(BaseModel):
    yaml: str | None = None


class TemplateBody(BaseModel):
    template_id: str


class AssistantChatBody(BaseModel):
    yaml: str = ""
    message: str = ""


class SuggestionBody(BaseModel):
    yaml: str = ""
    action_id: str = ""


class SkillGapBody(BaseModel):
    yaml: str = ""


class JobPayload(BaseModel):
    id: str | None = None
    company: str = ""
    role: str = ""
    status: str | None = None
    date_applied: str | None = None
    location: str | None = None
    job_url: str | None = None
    salary_range: str | None = None
    source: str | None = None
    contact_name: str | None = None
    contact_email: str | None = None
    resume_template: str | None = None
    priority: str | None = None
    follow_up_date: str | None = None
    notes: str | None = None


app = FastAPI(title="PPD API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health(api: PPDApi = Depends(get_api), _: None = Depends(_require_auth)) -> dict[str, Any]:
    return api.ping()


@app.get("/state")
def initial_state(api: PPDApi = Depends(get_api), _: None = Depends(_require_auth)) -> dict[str, Any]:
    result = api.get_initial_state()
    _fail(result)
    return result


@app.post("/upload")
async def upload(
    file: UploadFile = File(...),
    extract: bool = True,
    api: PPDApi = Depends(get_api),
    _: None = Depends(_require_auth),
) -> dict[str, Any]:
    data = await file.read()
    filename = file.filename or "upload.pdf"
    result = api.upload_and_process_bytes(filename, data) if extract else api.upload_from_bytes(filename, data)
    _fail(result)
    return result


@app.post("/extract")
def extract(api: PPDApi = Depends(get_api), _: None = Depends(_require_auth)) -> dict[str, Any]:
    result = api.extract_content()
    _fail(result)
    return result


@app.get("/resume")
def get_resume(api: PPDApi = Depends(get_api), _: None = Depends(_require_auth)) -> dict[str, Any]:
    result = api.get_structured_resume()
    _fail(result)
    return result


@app.put("/resume")
def put_resume(body: ResumeBody, api: PPDApi = Depends(get_api), _: None = Depends(_require_auth)) -> dict[str, Any]:
    payload = {"resume": body.resume} if body.resume else {}
    result = api.save_structured_resume(payload)
    _fail(result)
    return result


@app.put("/resume/yaml")
def put_resume_yaml(body: YamlBody, api: PPDApi = Depends(get_api), _: None = Depends(_require_auth)) -> dict[str, Any]:
    result = api.save_yaml(body.yaml)
    _fail(result)
    return result


@app.post("/preview")
def preview(body: PreviewBody, api: PPDApi = Depends(get_api), _: None = Depends(_require_auth)) -> dict[str, Any]:
    if body.resume:
        result = api.save_and_preview({"resume": body.resume})
    elif body.yaml is not None:
        result = api.update_preview(body.yaml)
    else:
        structured = api.get_structured_resume()
        if structured.get("ok") and structured.get("structured"):
            result = api.save_and_preview({"resume": structured["structured"]})
        else:
            result = api.refresh_preview()
    _fail(result)
    return result


@app.post("/export")
def export_pdf(body: ExportBody | None = None, api: PPDApi = Depends(get_api), _: None = Depends(_require_auth)) -> dict[str, Any]:
    yaml_text = body.yaml if body else None
    result = api.export_pdf_bytes(yaml_text)
    _fail(result)
    return result


@app.get("/export/download")
def export_download(api: PPDApi = Depends(get_api), _: None = Depends(_require_auth)) -> Response:
    result = api.export_pdf_bytes()
    _fail(result)
    pdf = base64.b64decode(result["pdf_base64"])
    filename = result.get("filename", "resume.pdf")
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/templates")
def templates(api: PPDApi = Depends(get_api), _: None = Depends(_require_auth)) -> dict[str, Any]:
    return api.get_templates()


@app.put("/templates/{template_id}")
def set_template(template_id: str, api: PPDApi = Depends(get_api), _: None = Depends(_require_auth)) -> dict[str, Any]:
    result = api.set_preview_template(template_id)
    _fail(result)
    return result


@app.get("/skill-gap")
def skill_gap(yaml: str = "", api: PPDApi = Depends(get_api), _: None = Depends(_require_auth)) -> dict[str, Any]:
    if not yaml.strip():
        structured = api.get_structured_resume()
        yaml = structured.get("yaml", "") if structured.get("ok") else ""
    result = api.get_skill_gap(yaml)
    _fail(result)
    return result


@app.post("/skill-gap")
def skill_gap_post(body: SkillGapBody, api: PPDApi = Depends(get_api), _: None = Depends(_require_auth)) -> dict[str, Any]:
    result = api.get_skill_gap(body.yaml)
    _fail(result)
    return result


@app.post("/assistant/chat")
def assistant_chat(body: AssistantChatBody, api: PPDApi = Depends(get_api), _: None = Depends(_require_auth)) -> dict[str, Any]:
    result = api.send_chat(body.yaml, body.message)
    _fail(result)
    return result


@app.get("/assistant")
def assistant_state(yaml: str = "", api: PPDApi = Depends(get_api), _: None = Depends(_require_auth)) -> dict[str, Any]:
    if not yaml.strip():
        structured = api.get_structured_resume()
        yaml = structured.get("yaml", "") if structured.get("ok") else ""
    return api.get_assistant(yaml)


@app.post("/assistant/suggest")
def assistant_suggest(body: SuggestionBody, api: PPDApi = Depends(get_api), _: None = Depends(_require_auth)) -> dict[str, Any]:
    result = api.apply_suggestion(body.yaml, body.action_id)
    _fail(result)
    return result


@app.get("/jobs")
def list_jobs(api: PPDApi = Depends(get_api), _: None = Depends(_require_auth)) -> dict[str, Any]:
    return api.get_jobs()


@app.post("/jobs")
def create_job(body: JobPayload, api: PPDApi = Depends(get_api), _: None = Depends(_require_auth)) -> dict[str, Any]:
    result = api.add_job(body.model_dump(exclude_none=True))
    _fail(result)
    return result


@app.put("/jobs/{job_id}")
def update_job(job_id: str, body: JobPayload, api: PPDApi = Depends(get_api), _: None = Depends(_require_auth)) -> dict[str, Any]:
    payload = body.model_dump(exclude_none=True)
    payload.pop("id", None)
    result = api.update_job(job_id, payload)
    _fail(result)
    return result


@app.delete("/jobs/{job_id}")
def delete_job(job_id: str, api: PPDApi = Depends(get_api), _: None = Depends(_require_auth)) -> dict[str, Any]:
    result = api.delete_job(job_id)
    _fail(result)
    return result


@app.post("/design/analyze")
def analyze_design(api: PPDApi = Depends(get_api), _: None = Depends(_require_auth)) -> dict[str, Any]:
    result = api.analyze_design()
    _fail(result)
    return result
