"""Idle-cost comparison: always-on VM vs. Nebius Serverless Job.

    python -m scripts.estimate_cost --jobs-per-month 300 --seconds-per-job 90

The whole pitch in one number: you pay for heavy multi-model reasoning only while a
Job is actually running.
"""
from __future__ import annotations

import argparse

SECONDS_PER_MONTH = 30 * 24 * 3600


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs-per-month", type=int, required=True)
    ap.add_argument("--seconds-per-job", type=float, required=True)
    ap.add_argument("--job-rate-per-hour", type=float, default=0.09,
                    help="$/hr while a Job runs (2 vCPU est.)")
    ap.add_argument("--vm-rate-per-hour", type=float, default=0.06,
                    help="$/hr for an always-on VM of the same size")
    args = ap.parse_args()

    active_seconds = args.jobs_per_month * args.seconds_per_job
    utilization = active_seconds / SECONDS_PER_MONTH

    job_cost = (active_seconds / 3600) * args.job_rate_per_hour
    vm_cost = (SECONDS_PER_MONTH / 3600) * args.vm_rate_per_hour

    print(f"Active job seconds/month : {active_seconds:,.0f}")
    print(f"Effective utilization    : {utilization:.2%}")
    print(f"Idle compute avoided     : {1 - utilization:.2%}")
    print(f"Serverless Job cost/month: ${job_cost:,.2f}")
    print(f"Always-on VM cost/month  : ${vm_cost:,.2f}")
    if job_cost > 0:
        print(f"Cost ratio (VM / Job)    : {vm_cost / job_cost:,.0f}x")


if __name__ == "__main__":
    main()
