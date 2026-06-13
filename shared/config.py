"""Single source of truth for model routing and runtime settings.

The MODEL_MAP design (per the Frontier Assembly swarm): each debate role maps to
exactly one {provider, model}. Swap a model in ONE line — no other code changes.

Default lineup runs ENTIRELY on Nebius-hosted open models, so a judge needs only a
single NEBIUS_API_KEY to reproduce a full debate. Set USE_CROSS_VENDOR=1 (and the
matching keys) to run a true cross-frontier debate across Claude / GPT / Grok / Gemini
with the Nebius-native model always taking the final Synthesizer word.
"""
from __future__ import annotations

import os

# --- Nebius Token Factory (OpenAI-compatible inference) ---------------------
# Verified 2026-06-13 against docs.tokenfactory.nebius.com
NEBIUS_BASE_URL = os.getenv("NEBIUS_BASE_URL", "https://api.tokenfactory.nebius.com/v1/")

USE_CROSS_VENDOR = os.getenv("USE_CROSS_VENDOR", "0") == "1"

# All-Nebius default: one key, fully reproducible, showcases Nebius models end-to-end.
# Verified available on Token Factory 2026-06-13 (3 distinct vendors: Meta + Google).
NEBIUS_ONLY_MAP = {
    "architect":   {"provider": "nebius", "model": os.getenv("ARCHITECT_MODEL", "meta-llama/Llama-3.3-70B-Instruct")},
    "critic":      {"provider": "nebius", "model": os.getenv("CRITIC_MODEL", "google/gemma-3-27b-it")},
    "synthesizer": {"provider": "nebius", "model": os.getenv("SYNTH_MODEL", "meta-llama/Llama-3.3-70B-Instruct")},
}

# Cross-frontier debate. Sanctions-clean: Western providers + native Nebius only.
# The Nebius-native model is always the Synthesizer — it gets the final word and
# writes the deliverable (the hackathon narrative the judges will notice).
CROSS_VENDOR_MAP = {
    "architect":   {"provider": "anthropic", "model": os.getenv("ARCHITECT_MODEL", "claude-3-5-sonnet-20241022")},
    "critic":      {"provider": "openai",    "model": os.getenv("CRITIC_MODEL", "gpt-4o")},
    "synthesizer": {"provider": "nebius",    "model": os.getenv("SYNTH_MODEL", "meta-llama/Llama-3.3-70B-Instruct")},
}

MODEL_MAP = CROSS_VENDOR_MAP if USE_CROSS_VENDOR else NEBIUS_ONLY_MAP

# Debate runs architect -> critic -> synthesizer, repeated MAX_ROUNDS times.
ROLE_ORDER = ["architect", "critic", "synthesizer"]
MAX_ROUNDS = int(os.getenv("MAX_ROUNDS", "2"))

# Per-call model limits.
MODEL_TIMEOUT = float(os.getenv("MODEL_TIMEOUT", "180"))
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "1500"))
TEMPERATURE = float(os.getenv("TEMPERATURE", "0.5"))

# --- Nebius Object Storage (S3-compatible) ----------------------------------
S3_ENDPOINT = os.getenv("NEBIUS_S3_ENDPOINT", "https://storage.eu-north1.nebius.cloud:443")
S3_BUCKET = os.getenv("S3_BUCKET", "frontier-assembly")
S3_REGION = os.getenv("AWS_REGION", "eu-north1")
