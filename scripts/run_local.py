"""Run a full debate locally — no bucket, no endpoint, just a NEBIUS_API_KEY.

    pip install -r job/requirements.txt
    export NEBIUS_API_KEY=...            # only key needed for the default lineup
    python -m scripts.run_local "An AI tool that drafts grant applications"

Artifacts (state.json + final_brief.md) land under ./artifacts/jobs/<job_id>/.
This is the path a hackathon judge takes to reproduce the project in one command.
"""
from __future__ import annotations

import sys

from shared.schemas import DebateState, UserRequest
from job.orchestrator import run_debate
from job.storage import LocalStore

DEFAULT_CONCEPT = (
    "An AI tool that turns messy startup ideas into implementation-ready product briefs."
)


def main() -> None:
    concept = " ".join(sys.argv[1:]).strip() or DEFAULT_CONCEPT
    state = DebateState(request=UserRequest(concept=concept))
    store = LocalStore("artifacts")

    print(f"▶ debating: {concept}")
    run_debate(state, store)

    print(f"✅ job {state.job_id}")
    print(f"   brief:   artifacts/{state.s3_brief_key}")
    print(f"   metrics: {state.metrics}")


if __name__ == "__main__":
    main()
