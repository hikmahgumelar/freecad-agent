import base64
from typing import Any

import requests


class GitHubClient:
    def __init__(self, token: str, repository: str):
        self.repository = repository

        self.base_url = (
            f"https://api.github.com/repos/{repository}"
        )

        self.session = requests.Session()

        self.session.headers.update({
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        })

    def _request(
        self,
        method: str,
        path: str,
        **kwargs: Any,
    ):
        url = f"{self.base_url}/{path.lstrip('/')}"

        response = self.session.request(
            method,
            url,
            timeout=30,
            **kwargs,
        )

        if not response.ok:
            raise RuntimeError(
                f"GitHub API error "
                f"{response.status_code}: "
                f"{response.text}"
            )

        if not response.text:
            return None

        return response.json()

    def list_directory(self, path: str):
        return self._request(
            "GET",
            f"/contents/{path.lstrip('/')}",
        )

    def read_file(self, path: str):
        data = self._request(
            "GET",
            f"/contents/{path.lstrip('/')}",
        )

        if data["type"] != "file":
            raise RuntimeError(
                f"{path} is not a file"
            )

        content = base64.b64decode(
            data["content"]
        ).decode("utf-8")

        return content, data["sha"]

    def write_file(
        self,
        path: str,
        content: str,
        message: str,
        sha: str | None = None,
    ):
        encoded = base64.b64encode(
            content.encode("utf-8")
        ).decode("ascii")

        payload = {
            "message": message,
            "content": encoded,
        }

        if sha:
            payload["sha"] = sha

        return self._request(
            "PUT",
            f"/contents/{path.lstrip('/')}",
            json=payload,
        )

    def update_file(
        self,
        path: str,
        content: str,
        sha: str,
        message: str,
    ):
        return self.write_file(
            path=path,
            content=content,
            message=message,
            sha=sha,
        )

    def append_status_log(self, line: str):
        """Append one execution result to status.log.

        The status log is intentionally best-effort. A failure to write the
        log must never prevent the watchdog from reporting the actual job
        result through cad/jobs/*.json.
        """
        path = "status.log"

        try:
            content, sha = self.read_file(path)
        except RuntimeError as exc:
            if "404" not in str(exc):
                raise
            content = ""
            sha = None

        if content and not content.endswith("\n"):
            content += "\n"

        content += line.rstrip("\n") + "\n"

        self.write_file(
            path=path,
            content=content,
            sha=sha,
            message="chore: update CAD execution status log",
        )
