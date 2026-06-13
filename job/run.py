"""Serverless Job entry point.

The Job is launched with two env vars set by the endpoint:
    JOB_ID     - the run id
    INPUT_KEY  - Object Storage key of the request payload (UserRequest JSON)

It loads the request from storage, runs the debate, and writes the brief back to
storage. On any fatal error it marks the state failed and re-raises (non-zero exit).
"""
from __future__ import annotations

import os
import sys

from shared.schemas import DebateState, UserRequest
from job.orchestrator import run_debate
from job.storage import ObjectStore


def main() -> int:
    store = ObjectStore()
    input_key = os.getenv("INPUT_KEY")

    if input_key:
        request = UserRequest.model_validate(store.get_json(input_key))
    else:
        # Local container smoke test: pass the concept as args.
        concept = " ".join(sys.argv[1:]) or os.getenv("CONCEPT", "")
        if not concept:
            raise SystemExit("No INPUT_KEY env and no concept argv provided.")
        request = UserRequest(concept=concept)

    state = DebateState(request=request)
    if os.getenv("JOB_ID"):
        state.job_id = os.environ["JOB_ID"]

    try:
        run_debate(state, store)
    except Exception:
        state.status = "failed"
        store.put_json(f"jobs/{state.job_id}/state.json", state)
        raise

    print(f"completed job {state.job_id} -> {state.s3_brief_key}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
