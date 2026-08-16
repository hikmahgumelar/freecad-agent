import signal
import time
from datetime import datetime, timezone

from .config import load_config
from .freecad_executor import FreeCADExecutor
from .github import GitHubClient
from .jobs import Job, JobQueue


STATUS_LOG_PATH = "status.log"


class Watchdog:
    def __init__(self):
        self.running = True

        config = load_config()

        self.poll_interval = config.poll_interval

        self.github = GitHubClient(
            token=config.github_token,
            repository=config.github_repo,
        )

        self.queue = JobQueue(self.github)

        self.freecad = FreeCADExecutor(
            host=config.freecad_host,
            port=config.freecad_port,
        )

    def stop(self, *_):
        print("\nStopping watchdog...")
        self.running = False

    def execute_job(self, job: Job):
        print(
            f"[JOB] {job.job_id} "
            f"action={job.action}"
        )

        if not job.action:
            raise ValueError(
                "Job is missing 'action'"
            )

        result = self.freecad.execute(job.data)

        return result

    def _write_status_log(
        self,
        job: Job,
        status: str,
        error: str | None = None,
    ):
        timestamp = datetime.now(
            timezone.utc
        ).isoformat()

        parts = [
            timestamp,
            f"job={job.job_id}",
            f"action={job.action}",
            f"status={status}",
        ]

        if error:
            safe_error = " ".join(
                str(error).splitlines()
            )
            parts.append(f"error={safe_error}")

        line = " | ".join(parts)

        try:
            self.github.append_status_log(line)
            print(
                f"[STATUS] {job.job_id} "
                f"status={status} logged"
            )
        except Exception as exc:
            print(
                f"[ERROR] Could not write "
                f"{STATUS_LOG_PATH}: {exc}"
            )

    def process_job(self, job: Job):
        print(
            f"[JOB] {job.job_id} "
            f"status=pending"
        )

        try:
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

            self._write_status_log(
                job,
                "completed",
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

            self._write_status_log(
                job,
                "failed",
                error=str(exc),
            )

    def run(self):
        print("================================")
        print(" freecad-agent-watchdog v0.2")
        print("================================")
        print(
            f"Polling interval: "
            f"{self.poll_interval}s"
        )
        print(
            "FreeCAD endpoint: "
            f"{self.freecad.host}:{self.freecad.port}"
        )
        print()

        while self.running:
            try:
                jobs = self.queue.list_pending_jobs()

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
                print(f"[ERROR] {exc}")

            for _ in range(self.poll_interval * 10):
                if not self.running:
                    break

                time.sleep(0.1)

        print("Watchdog stopped.")


def main():
    watchdog = Watchdog()

    signal.signal(signal.SIGINT, watchdog.stop)
    signal.signal(signal.SIGTERM, watchdog.stop)

    watchdog.run()


if __name__ == "__main__":
    main()
