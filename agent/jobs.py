import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from .github import GitHubClient, GitHubConflictError


JOB_DIRECTORY = "cad/jobs"


@dataclass
class Job:
    path: str
    sha: str
    data: dict[str, Any]

    @property
    def job_id(self) -> str:
        return str(self.data.get("id", ""))

    @property
    def status(self) -> str:
        return str(self.data.get("status", ""))

    @property
    def action(self) -> str:
        return str(self.data.get("action", ""))


def utc_now() -> str:
    return datetime.now(
        timezone.utc
    ).isoformat()


class JobQueue:
    def __init__(self, github: GitHubClient):
        self.github = github

    def list_pending_jobs(self) -> list[Job]:
        try:
            entries = self.github.list_directory(
                JOB_DIRECTORY
            )
        except RuntimeError as exc:
            if "404" in str(exc):
                return []

            raise

        jobs = []

        for entry in entries:
            if entry.get("type") != "file":
                continue

            name = entry.get("name", "")

            if not name.endswith(".json"):
                continue

            path = entry["path"]

            content, sha = self.github.read_file(path)

            data = json.loads(content)

            if data.get("status") != "pending":
                continue

            jobs.append(
                Job(
                    path=path,
                    sha=sha,
                    data=data,
                )
            )

        return jobs

    def update(
        self,
        job: Job,
        status: str,
        **extra,
    ) -> Job:
        data = dict(job.data)

        data["status"] = status
        data["updated_at"] = utc_now()

        data.update(extra)

        content = json.dumps(
            data,
            indent=2,
            sort_keys=True,
        ) + "\n"

        try:
            self.github.update_file(
                path=job.path,
                content=content,
                sha=job.sha,
                message=(
                    f"CAD job {job.job_id}: "
                    f"{status}"
                ),
            )
        except GitHubConflictError:
            # The job SHA may have changed while the watchdog was processing
            # the job. Refresh once and retry using the latest blob SHA.
            print(
                f"[GITHUB] SHA conflict for {job.job_id}; "
                "refreshing job before retry"
            )

            latest_content, latest_sha = (
                self.github.read_file(job.path)
            )
            latest_data = json.loads(latest_content)

            # Preserve the latest server-side job data, then apply only the
            # state transition requested by this watchdog instance.
            latest_data["status"] = status
            latest_data["updated_at"] = utc_now()
            latest_data.update(extra)

            latest_serialized = json.dumps(
                latest_data,
                indent=2,
                sort_keys=True,
            ) + "\n"

            self.github.update_file(
                path=job.path,
                content=latest_serialized,
                sha=latest_sha,
                message=(
                    f"CAD job {job.job_id}: "
                    f"{status} (refresh)"
                ),
            )

        # Re-read file to obtain the new SHA.
        new_content, new_sha = (
            self.github.read_file(job.path)
        )

        new_data = json.loads(new_content)

        return Job(
            path=job.path,
            sha=new_sha,
            data=new_data,
        )
