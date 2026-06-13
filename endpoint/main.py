"""Thin Serverless Endpoint.

It does the minimum and returns immediately (never runs the debate itself):
  1. validate the request
  2. write the request payload to Object Storage
  3. launch a Nebius Serverless Job (passing JOB_ID + INPUT_KEY)
  4. return the job id + where the brief will land

Keeping the endpoint thin is what makes the whole thing cheap: the always-on
surface is tiny, and the heavy multi-model reasoning only bills while a Job runs.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import uuid

from fastapi import FastAPI, HTTPException

from shared.config import S3_BUCKET
from shared.schemas import DebateState, UserRequest
from job.storage import ObjectStore

app = FastAPI(title="Frontier Assembly Endpoint")


def _store() -> ObjectStore:
    return ObjectStore()


def _launch_job(job_id: str, input_key: str) -> str:
    """Launch the Serverless Job via the Nebius CLI if present.

    Returns a status string. We never block on the job; if the CLI is unavailable
    (e.g. local dev) the request payload is still persisted and the status says so.
    """
    manifest = os.getenv("NEBIUS_JOB_MANIFEST", "infra/nebius-job.yaml")
    if not shutil.which("nebius"):
        return "persisted (nebius CLI not found — run the Job manually with this INPUT_KEY)"
    try:
        subprocess.Popen(  # fire-and-forget; the Job is async by design
            [
                "nebius", "serverless", "job", "run",
                "-f", manifest,
                "--env", f"JOB_ID={job_id}",
                "--env", f"INPUT_KEY={input_key}",
            ]
        )
        return "launched"
    except Exception as exc:  # noqa: BLE001
        return f"persisted (launch error: {type(exc).__name__})"


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok"}


@app.post("/debate")
def start_debate(request: UserRequest) -> dict:
    try:
        job_id = uuid.uuid4().hex
        input_key = f"jobs/{job_id}/request.json"
        _store().put_json(input_key, request)
        status = _launch_job(job_id, input_key)
        return {
            "job_id": job_id,
            "status": status,
            "input_key": input_key,
            "brief_key": f"jobs/{job_id}/final_brief.md",
            "bucket": S3_BUCKET,
        }
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc
