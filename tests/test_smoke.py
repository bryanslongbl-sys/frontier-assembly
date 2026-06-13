"""Offline end-to-end smoke test — no API keys, no network.

Stubs the model router with canned responses and runs the real orchestrator against
a LocalStore, then asserts the full artifact set was written and the brief is well
formed. Run: `python -m tests.test_smoke`
"""
from __future__ import annotations

import tempfile
from pathlib import Path

from shared.schemas import DebateState, UserRequest
from job.models.router import ModelRouter
from job.orchestrator import run_debate
from job.storage import LocalStore


def _fake_chat(self, provider, model, messages, *, max_tokens=1500, temperature=0.5):
    role = "synthesizer" if "FINAL" in messages[0]["content"].upper() or "final brief" in messages[-1]["content"].lower() else "agent"
    return (f"[{provider}:{model}] canned {role} response for testing.", 12, 34)


def main() -> None:
    ModelRouter.chat = _fake_chat  # type: ignore[method-assign]

    with tempfile.TemporaryDirectory() as tmp:
        store = LocalStore(tmp)
        state = DebateState(request=UserRequest(concept="A test concept for the smoke run", max_rounds=2))
        run_debate(state, store)

        root = Path(tmp)
        brief = root / "jobs" / state.job_id / "final_brief.md"
        stfile = root / "jobs" / state.job_id / "state.json"

        assert state.status == "completed", state.status
        assert stfile.exists(), "state.json missing"
        assert brief.exists(), "final_brief.md missing"
        # 2 rounds * 3 roles = 6 turns
        assert len(state.turns) == 6, len(state.turns)
        text = brief.read_text(encoding="utf-8")
        assert "# Product Brief" in text
        assert "Full debate transcript" in text
        assert state.metrics["tokens_out"] == 6 * 34, state.metrics

    print("PASS: end-to-end pipeline produced a brief")
    print(f"  turns={len(state.turns)} metrics={state.metrics}")


if __name__ == "__main__":
    main()
