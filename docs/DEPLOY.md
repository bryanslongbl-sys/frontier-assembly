# Deploying Frontier Assembly on Nebius Serverless

The CI workflow (`.github/workflows/deploy.yml`) builds both container images in the
cloud and pushes them to the **Nebius Container Registry** (`cr.ai.nebius.cloud`) on
every push to `main` — no local Docker required.

## 1. One-time Nebius setup
In your Nebius project:
1. **Container Registry** — create a registry. Note its ID/path:
   `cr.ai.nebius.cloud/<registry-id>`.
2. **Object Storage** — create an S3-compatible bucket named `frontier-assembly`
   and an access-key pair (access key id + secret).
3. **Service account** for CI push — give it `container-registry` push permission and
   create credentials for it (this is what CI uses to `docker login`).

## 2. GitHub repo secrets (Settings → Secrets and variables → Actions)
| Secret | Value |
|---|---|
| `NEBIUS_REGISTRY` | `cr.ai.nebius.cloud/<registry-id>` (the image path prefix) |
| `NEBIUS_REGISTRY_USERNAME` | Nebius Container Registry username (service-account based) |
| `NEBIUS_REGISTRY_PASSWORD` | the matching registry token / key |

> ⚠️ **These are NOT your Token Factory inference key.** `NEBIUS_API_KEY` is for
> model inference only; the registry needs **Nebius IAM / service-account** credentials
> with container-registry push access. Mixing them up is the #1 deploy gotcha.

Once these are set, the next push to `main` builds **and pushes** both images. Until
then the workflow still runs green (build-only, push skipped).

## 3. Create the serverless Endpoint + Job
After the images are in the registry, create the serverless resources (CLI or console),
pointing them at the pushed images. Reference `infra/nebius-manifest.yaml` for the shape:

```bash
# the endpoint launches the job per request (JOB_ID + INPUT_KEY injected)
nebius serverless endpoint create -f infra/nebius-manifest.yaml
```

Runtime secrets the Job/Endpoint need (set as Nebius secrets, never committed):
`NEBIUS_API_KEY`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `S3_BUCKET=frontier-assembly`.

> Verify the exact `nebius` CLI subcommands against the current Nebius docs
> (https://docs.nebius.com/serverless) — the platform's CLI surface evolves.

## 4. Fire a debate
```bash
curl -X POST "$ENDPOINT_URL/debate" -H 'Content-Type: application/json' \
  -d '{"concept":"A serverless RAG pipeline for legal teams","max_rounds":2}'
# -> { "job_id": "...", "brief_key": "jobs/<id>/final_brief.md" }
```
The brief lands in Object Storage at `jobs/<id>/final_brief.md` and the Job terminates.
