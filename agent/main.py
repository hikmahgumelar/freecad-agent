import signal
import time
from datetime import datetime, timezone

from .config import load_config
from .freecad_executor import FreeCADExecutor
from .github import GitHubClient, GitHubRateLimitError
from .jobs import Job, JobQueue


STATUS_LOG_PATH = "status.log"
DEFAULT_RATE_LIMIT_SLEEP = 300


class Watchdog:
    def __init__(self):
        self.running = True
        self.rate_limit_reset_at = None

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

    def _rate_limit_cooldown(self, exc: GitHubRateLimitError):
        now = int(time.time())
        reset_at = exc.reset_at

        if reset_at is not None and reset_at > now:
            sleep_seconds = reset_at - now + 2
            reset_text = datetime.fromtimestamp(
                reset_at,
                tz=timezone.utc,
            ).isoformat()
        else:
            sleep_seconds = DEFAULT_RATE_LIMIT_SLEEP
            reset_text = "unknown"

        self.rate_limit_reset_at = reset_at

        print(
            "[GITHUB] API rate limit reached; "
            f"cooling down for {sleep_seconds}s "
            f"(reset={reset_text})"
        )

        deadline = time.monotonic() + sleep_seconds

        while self.running and time.monotonic() < deadline:
            remaining = max(
                0,
                int(deadline - time.monotonic()),
            )
            print(
                f"[GITHUB] rate-limit cooldown: "
                f"{remaining}s remaining",
                end="\r",
                flush=True,
            )
            time.sleep(min(5, max(0.1, remaining)))

        if self.running:
            print("[GITHUB] rate-limit cooldown finished")

    def execute_job(self, job: Job):
        print(
            f"[JOB] {job.job_id} "
            f"action={job.action}"
        )

        if not job.action:
            raise ValueError(
                "Job is missing 'action'"
            )

        # Health-check the FreeCAD listener before executing a real CAD job.
        self.freecad.execute({"action": "ping"})
        print("[FREECAD] listener healthy")

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
        except GitHubRateLimitError as exc:
            print(
                f"[GITHUB] Could not write {STATUS_LOG_PATH}: "
                "rate limit reached"
            )
            self._rate_limit_cooldown(exc)
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
            started_at = datetime.now(
                timezone.utc
            ).isoformat()

            job = self.queue.update(
                job,
                "running",
                started_at=started_at,
                completed_at=None,
                error=None,
            )

            result = self.execute_job(job)

            completed_at = datetime.now(
                timezone.utc
            ).isoformat()

            self.queue.update(
                job,
                "completed",
                result=result,
                completed_at=completed_at,
                error=None,
            )

            print(
                f"[JOB] {job.job_id} "
                f"status=completed"
            )

            self._write_status_log(
                job,
                "completed",
            )

        except GitHubRateLimitError as exc:
            print(
                f"[GITHUB] Rate limit interrupted "
                f"job {job.job_id}"
            )
            self._rate_limit_cooldown(exc)

        except Exception as exc:
            print(
                f"[JOB] {job.job_id} "
                f"status=failed "
                f"error={exc}"
            )

            try:
                failed_at = datetime.now(
                    timezone.utc
                ).isoformat()

                self.queue.update(
                    job,
                    "failed",
                    error=str(exc),
                    completed_at=failed_at,
                )
            except GitHubRateLimitError as rate_exc:
                print(
                    f"[GITHUB] Could not report failure for "
                    f"{job.job_id}: rate limit reached"
                )
                self._rate_limit_cooldown(rate_exc)
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
        print(" freecad-agent-watchdog v0.4")
        print("================================")
        print(
            f"Polling interval: "
            f"{self.poll_interval}s"
        )
        print(
            "FreeCAD endpoint: "
            f"{self.freecad.host}:{self.freecad.port}"
        )
        print("Health check: enabled")
        print("GitHub rate-limit handling: enabled")
        print("GitHub SHA-conflict recovery: enabled")
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

            except GitHubRateLimitError as exc:
                self._rate_limit_cooldown(exc)

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
