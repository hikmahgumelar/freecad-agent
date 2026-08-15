import json
import signal
import sys
import time

from .config import load_config
from .github import GitHubClient
from .jobs import Job, JobQueue


class Watchdog:
    def __init__(self):
        self.running = True

        config = load_config()

        self.poll_interval = config.poll_interval

        self.github = GitHubClient(
            token=config.github_token,
            repository=config.github_repo,
        )

        self.queue = JobQueue(
            self.github
        )

    def stop(self, *_):
        print("\nStopping watchdog...")
        self.running = False

    def execute_job(self, job: Job):
        print(
            f"[JOB] {job.job_id} "
            f"action={job.action}"
        )

        # SAFETY BOUNDARY:
        #
        # V0.1 does not execute arbitrary
        # shell commands or FreeCAD operations.
        #
        # We only prove that the job reaches
        # the notebook and can be acknowledged.

        if not job.action:
            raise ValueError(
                "Job is missing 'action'"
            )

        result = {
            "executor": "freecad-agent-v0.1",
            "message": "Job received successfully",
            "action": job.action,
        }

        return result

    def process_job(self, job: Job):
        print(
            f"[JOB] {job.job_id} "
            f"status=pending"
        )

        try:
            # Claim the job.
            job = self.queue.update(
                job,
                "running",
                started_at=job.data.get(
                    "started_at"
                ) or None,
            )

            result = self.execute_job(job)

            self.queue.update(
                job,
                "completed",
                result=result,
                completed_at=None,
            )

            print(
                f"[JOB] {job.job_id} "
                f"status=completed"
            )

        except Exception as exc:
            print(
                f"[JOB] {job.job_id} "
                f"status=failed "
                f"error={exc}"
            )

            try:
                self.queue.update(
                    job,
                    "failed",
                    error=str(exc),
                )
            except Exception as report_error:
                print(
                    "[ERROR] Could not report "
                    f"job failure: {report_error}"
                )

    def run(self):
        print("================================")
        print(" freecad-agent-watchdog v0.1")
        print("================================")
        print(
            f"Polling interval: "
            f"{self.poll_interval}s"
        )
        print()

        while self.running:
            try:
                jobs = (
                    self.queue.list_pending_jobs()
                )

                if jobs:
                    print(
                        f"[QUEUE] "
                        f"{len(jobs)} pending job(s)"
                    )

                for job in jobs:
                    if not self.running:
                        break

                    self.process_job(job)

            except Exception as exc:
                print(
                    f"[ERROR] {exc}"
                )

            for _ in range(
                self.poll_interval * 10
            ):
                if not self.running:
                    break

                time.sleep(0.1)

        print("Watchdog stopped.")


def main():
    watchdog = Watchdog()

    signal.signal(
        signal.SIGINT,
        watchdog.stop,
    )

    signal.signal(
        signal.SIGTERM,
        watchdog.stop,
    )

    watchdog.run()


if __name__ == "__main__":
    main()
