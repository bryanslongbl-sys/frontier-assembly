"""Final synthesis + brief rendering.

The Synthesizer model (Nebius-native by design — it gets the final word) reads the
full debate and writes the decision-grade brief body. We then wrap that body with a
deterministic metadata header and a collapsible transcript appendix, so the artifact
is both human-useful and fully auditable.
"""
from __future__ import annotations

from shared.config import MAX_TOKENS, MODEL_MAP
from shared.schemas import DebateState
from job.models.router import ModelRouter
from job.resilience import call_with_retry

_SYNTH_INSTRUCTION = """You are the Product Synthesizer. Read the full multi-model debate \
below and write the FINAL product brief. This is a decision artifact, not a transcript.

Use exactly these markdown sections:

## 1. Executive Summary
## 2. Problem & Who It's For
## 3. Recommended Solution
## 4. Architecture (Nebius-native: Serverless Endpoints + Jobs + Object Storage)
## 5. Key Risks (from the Critic) & Mitigations
## 6. Implementation Checklist
## 7. What NOT to build (non-goals)

Be concrete and implementation-ready. Resolve disagreements between the Architect and \
Critic explicitly. Do not invent facts beyond the debate.

Section 4 MUST be Nebius-native: name Serverless Endpoints, Serverless Jobs, Object \
Storage (S3-compatible), and Nebius AI Studio / Token Factory inference. Do NOT \
reference AWS/GCP/Azure services (no Lambda, AWS S3, API Gateway, DynamoDB, SQS)."""


def _transcript(state: DebateState) -> str:
    return "\n\n".join(
        f"[{t.agent.upper()} · round {t.round} · {t.model}]\n{t.content}" for t in state.turns
    )


def synthesize_brief_body(state: DebateState, router: ModelRouter) -> str:
    cfg = MODEL_MAP["synthesizer"]
    messages = [
        {"role": "system", "content": _SYNTH_INSTRUCTION},
        {
            "role": "user",
            "content": (
                f"ORIGINAL CONCEPT:\n{state.request.concept}\n\n"
                f"FULL DEBATE:\n{_transcript(state)}\n\n"
                "Now write the final brief."
            ),
        },
    ]
    try:
        text, _, _ = call_with_retry(
            lambda: router.chat(cfg["provider"], cfg["model"], messages, max_tokens=MAX_TOKENS * 2)
        )
        if text.strip():
            return text.strip()
    except Exception:  # noqa: BLE001 - degrade to a deterministic brief, never crash the run
        pass
    return _fallback_body(state)


def _fallback_body(state: DebateState) -> str:
    """Deterministic brief assembled from the last synthesizer turns when the live
    synthesis call is unavailable — so a run ALWAYS yields a usable artifact."""
    synth = [t.content for t in state.turns if t.agent == "synthesizer" and not t.degraded]
    architect = [t.content for t in state.turns if t.agent == "architect" and not t.degraded]
    critic = [t.content for t in state.turns if t.agent == "critic" and not t.degraded]
    section = lambda items: "\n\n".join(items) if items else "_(no successful turns)_"
    return (
        "> _Final synthesis model was unavailable; this brief is assembled "
        "deterministically from the debate._\n\n"
        "## 1. Executive Summary\n\n" + section(synth[-1:]) + "\n\n"
        "## 2. Architect's Direction\n\n" + section(architect[-1:]) + "\n\n"
        "## 3. Critic's Risks\n\n" + section(critic[-1:])
    )


def render_brief(state: DebateState, router: ModelRouter) -> str:
    body = synthesize_brief_body(state, router)
    models_used = sorted({f"{t.provider}:{t.model}" for t in state.turns})
    header = (
        f"# Product Brief — Frontier Assembly\n\n"
        f"> **Concept:** {state.request.concept}\n>\n"
        f"> **Job ID:** `{state.job_id}` · **Generated:** {state.updated_at.isoformat()}\n>\n"
        f"> **Debate models:** {', '.join(models_used)}\n>\n"
        f"> **Synthesizer (final word):** "
        f"`{MODEL_MAP['synthesizer']['provider']}:{MODEL_MAP['synthesizer']['model']}`\n\n"
        f"---\n\n"
    )
    appendix = (
        "\n\n---\n\n<details>\n<summary>Full debate transcript "
        f"({len(state.turns)} turns)</summary>\n\n{_transcript(state)}\n\n</details>\n"
    )
    return header + body + appendix
