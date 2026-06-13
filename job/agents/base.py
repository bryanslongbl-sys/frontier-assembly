"""Agent: one debate role bound to one {provider, model} via MODEL_MAP.

Each agent builds its context (concept + constraints + the recent transcript),
calls its model through the router (with retry), and returns an AgentTurn. If the
model call fails after retries, the agent returns a DEGRADED turn so the debate
keeps moving instead of crashing the whole job.
"""
from __future__ import annotations

from pathlib import Path

from shared.config import MAX_TOKENS, MODEL_MAP, TEMPERATURE
from shared.schemas import AgentTurn, DebateState, Role
from job.models.router import ModelRouter
from job.resilience import call_with_retry

_PROMPTS = Path(__file__).resolve().parent.parent / "prompts"


class Agent:
    def __init__(self, role: Role, router: ModelRouter) -> None:
        self.role = role
        self.cfg = MODEL_MAP[role]
        self.router = router
        self.system_prompt = (_PROMPTS / f"{role}.md").read_text(encoding="utf-8")

    def run(self, state: DebateState, round_no: int) -> AgentTurn:
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": self._context(state)},
        ]

        def _call():
            return self.router.chat(
                self.cfg["provider"],
                self.cfg["model"],
                messages,
                max_tokens=MAX_TOKENS,
                temperature=TEMPERATURE,
            )

        try:
            text, tin, tout = call_with_retry(_call)
            return AgentTurn(
                agent=self.role,
                provider=self.cfg["provider"],
                model=self.cfg["model"],
                round=round_no,
                content=text.strip(),
                tokens_in=tin,
                tokens_out=tout,
            )
        except Exception as exc:  # noqa: BLE001 - degrade, don't crash the debate
            return AgentTurn(
                agent=self.role,
                provider=self.cfg["provider"],
                model=self.cfg["model"],
                round=round_no,
                degraded=True,
                content=(
                    f"[DEGRADED] {self.role} via {self.cfg['provider']} "
                    f"({type(exc).__name__}) failed after retries. "
                    "The debate continues from prior context."
                ),
            )

    def _context(self, state: DebateState) -> str:
        req = state.request
        recent = state.turns[-6:]
        transcript = "\n\n".join(
            f"[{t.agent.upper()} · round {t.round} · {t.model}]\n{t.content}" for t in recent
        )
        constraints = "\n".join(f"- {c}" for c in req.constraints) or "- (none specified)"
        return (
            f"CONCEPT:\n{req.concept}\n\n"
            f"TARGET AUDIENCE:\n{req.target_audience or '(not specified)'}\n\n"
            f"CONSTRAINTS:\n{constraints}\n\n"
            f"DEBATE SO FAR:\n{transcript or '(you are opening the debate)'}\n\n"
            f"Respond now in your role as the {self.role}."
        )
