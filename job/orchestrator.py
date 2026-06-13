"""The debate engine.

Runs architect -> critic -> synthesizer for MAX_ROUNDS rounds, checkpointing the
full DebateState to storage after every turn (durable across cold starts / restarts),
then renders the final brief and writes it as a markdown artifact.
"""
from __future__ import annotations

from shared.config import ROLE_ORDER
from shared.schemas import DebateState
from job.agents.base import Agent
from job.models.router import ModelRouter
from job.render import render_brief
from job.storage import LocalStore, ObjectStore

Store = ObjectStore | LocalStore


def _state_key(state: DebateState) -> str:
    return f"jobs/{state.job_id}/state.json"


def _checkpoint(state: DebateState, store: Store) -> None:
    store.put_json(_state_key(state), state)


def _metrics(state: DebateState) -> dict:
    return {
        "turns": len(state.turns),
        "rounds": state.request.max_rounds,
        "tokens_in": sum(t.tokens_in for t in state.turns),
        "tokens_out": sum(t.tokens_out for t in state.turns),
        "degraded_turns": sum(1 for t in state.turns if t.degraded),
    }


def run_debate(state: DebateState, store: Store) -> DebateState:
    router = ModelRouter()
    agents = {role: Agent(role, router) for role in ROLE_ORDER}

    state.status = "debating"
    _checkpoint(state, store)

    for rnd in range(1, state.request.max_rounds + 1):
        for role in ROLE_ORDER:
            turn = agents[role].run(state, rnd)
            state.turns.append(turn)
            state.updated_at = turn.timestamp
            _checkpoint(state, store)  # immutable progress; restartable

    state.status = "synthesized"
    brief_md = render_brief(state, router)
    brief_key = f"jobs/{state.job_id}/final_brief.md"
    store.put_text(brief_key, brief_md, "text/markdown")
    state.s3_brief_key = brief_key

    state.metrics = _metrics(state)
    state.status = "completed"
    _checkpoint(state, store)
    return state
