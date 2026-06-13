# The Frontier Assembly

**Multi-model brainstorming debates with zero idle compute, on Nebius Serverless.**

Submit a raw idea → a thin Serverless **Endpoint** spins up a Serverless **Job** → three
AI agents (**Architect → Critic → Synthesizer**) debate it across rounds → a
decision-grade product brief lands in **Object Storage** → the Job terminates. You pay
for heavy multi-model reasoning *only while a debate is actually running*.

> A reusable template for **agentic workloads that need deep reasoning but not a 24/7 server.**

---

## Why this wins on Nebius

Most multi-agent demos run inside an always-on notebook, VM, or web server — burning
compute even when idle. Frontier Assembly demonstrates the better pattern:

```
Endpoint  =  always-available, tiny trigger        (cheap)
Job       =  heavy multi-model reasoning, on demand (bills only while running)
Storage   =  durable state + artifact after the Job disappears
```

| Setup | Idle cost / month | Billing |
| --- | --- | --- |
| 24/7 VM cluster (2 vCPU) | always-on | pay around the clock |
| **Nebius Serverless Job** | **$0** | per-second, only while a debate runs |

```bash
python -m scripts.estimate_cost --jobs-per-month 300 --seconds-per-job 90
# Effective utilization ~2.8%  ->  idle compute avoided ~97%
```

---

## Architecture

```
            POST /debate
 user ─────────────────────►  FastAPI Serverless Endpoint
                                   │  writes request.json to Object Storage
                                   │  launches Job (JOB_ID + INPUT_KEY)
                                   ▼
                         Nebius Serverless Job
                         ┌──────────────────────────────┐
                         │  Architect → Critic → Synth   │  × MAX_ROUNDS
                         │  checkpoint state every turn  │
                         └──────────────────────────────┘
                                   │  renders final brief
                                   ▼
                         Nebius Object Storage
                         jobs/<id>/request.json
                         jobs/<id>/state.json      (durable, restartable)
                         jobs/<id>/final_brief.md  (the deliverable)
```

State lives entirely in Object Storage and is checkpointed after **every** turn, so the
ephemeral Job survives cold starts, retries, and partial failures.

---

## The lineup (and the narrative)

| Role | Default (all-Nebius) | Cross-frontier mode |
| --- | --- | --- |
| 🏛 Architect | Llama-3.3-70B (Nebius) | Claude (Anthropic) |
| 🔬 Critic | Gemma-3-27B (Nebius) | GPT-4o (OpenAI) |
| 🧩 **Synthesizer** | **Llama-3.3-70B (Nebius)** | **Nebius-native model** |

The **Nebius-native model is always the Synthesizer** — it gets the final word and writes
the deliverable. Routing is a one-line change in [`shared/config.py`](shared/config.py)
(`MODEL_MAP`): swap any role's model without touching another line of code. Cross-vendor
mode adds Claude / GPT / Grok / Gemini / Meta — **Western providers + native Nebius only**
(sanctions-clean by design).

---

## Quickstart — reproduce a full debate in one command

The default lineup runs entirely on Nebius, so you need **only a Nebius key** and **no
bucket** (artifacts go to `./artifacts/`):

```bash
pip install -r job/requirements.txt
export NEBIUS_API_KEY=...                       # from studio / token factory
python -m scripts.run_local "An AI tool that drafts grant applications"
# -> artifacts/jobs/<job_id>/final_brief.md
```

### Deploy to Nebius Serverless

```bash
# build & push the two images
docker build -f endpoint/Dockerfile.endpoint -t cr.nebius.cloud/frontier-assembly/endpoint .
docker build -f job/Dockerfile.job          -t cr.nebius.cloud/frontier-assembly/job .

# create the endpoint (it launches the Job per request)
nebius serverless endpoint create -f infra/nebius-manifest.yaml

# fire a debate
curl -X POST "$ENDPOINT_URL/debate" -H 'Content-Type: application/json' \
  -d '{"concept":"A serverless RAG pipeline for legal teams","max_rounds":2}'
# -> { "job_id": "...", "brief_key": "jobs/<id>/final_brief.md" }
```

---

## Repository layout

```
nebius-frontier-assembly/
├── endpoint/        # thin FastAPI trigger (Serverless Endpoint)
├── job/             # the debate engine (Serverless Job)
│   ├── run.py            # job entry point (reads JOB_ID + INPUT_KEY)
│   ├── orchestrator.py   # architect→critic→synth loop, checkpoints
│   ├── agents/base.py    # one role bound to one model
│   ├── models/router.py  # provider routing (OpenAI-compat + Anthropic SDK)
│   ├── render.py         # final synthesis → brief.md
│   ├── resilience.py     # retry + graceful degrade
│   └── prompts/          # architect / critic / synthesizer
├── shared/          # schemas.py + config.py (MODEL_MAP, the single swap point)
├── infra/           # nebius-manifest.yaml, nebius-job.yaml
├── scripts/         # run_local.py, estimate_cost.py
├── templates/       # brief.md reference shape
├── .env.example
└── LICENSE          # MIT
```

---

## Reliability features

- Per-turn **immutable checkpoints** to Object Storage (restartable across cold starts)
- **Retry with backoff** on every model call; a failed agent **degrades** instead of
  crashing the debate
- **One-key reproducibility** — default lineup needs only `NEBIUS_API_KEY`
- **Storage-agnostic** orchestrator (S3 in prod, filesystem locally) — same code path
- **Token + degraded-turn metrics** captured per run

---

## Built by Aurum Nebula LLC — with the Frontier Assembly Swarm 🛰️

This project was **itself** designed agentically: a collaborative circle of frontier
models each took a role and contributed to the architecture — the same Architect /
Critic / Synthesizer pattern the tool runs at runtime.

| Model | Contribution |
| --- | --- |
| Gemini | Rules alignment, concept, the three-persona pattern, cost narrative |
| GPT | Production state model, resilience, containers, cost math |
| Grok | Repo architecture, provider routing, brief template |
| Claude (Sonnet) | `MODEL_MAP` one-line routing + Nebius-as-Synthesizer narrative |
| Claude (Opus) | Consolidation, multi-provider router, end-to-end build |

**Primary developer: Bryan S. Long** · Aurum Nebula LLC · `bryanslong@aurumnebula.com`

Licensed **MIT** — copy it, adapt it, deploy it.
