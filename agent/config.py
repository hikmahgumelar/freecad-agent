import os
from dataclasses import dataclass
from urllib.parse import urlparse

from dotenv import load_dotenv


load_dotenv()


@dataclass
class Config:
    github_token: str
    github_repo: str
    poll_interval: int
    freecad_host: str
    freecad_port: int


def normalize_github_repo(value: str) -> str:
    value = value.strip().rstrip("/")

    if value.startswith("https://") or value.startswith("http://"):
        parsed = urlparse(value)

        path = parsed.path.strip("/")

        if path.endswith(".git"):
            path = path[:-4]

        parts = path.split("/")

        if len(parts) != 2:
            raise ValueError(
                f"Invalid GitHub repository URL: {value}"
            )

        return "/".join(parts)

    if value.endswith(".git"):
        value = value[:-4]

    parts = value.split("/")

    if len(parts) != 2:
        raise ValueError(
            f"Invalid GitHub repository: {value}"
        )

    return value


def load_config() -> Config:
    token = os.getenv("GITHUB_TOKEN")
    repo = os.getenv("GITHUB_REPO")

    if not token:
        raise RuntimeError(
            "GITHUB_TOKEN is not configured"
        )

    if not repo:
        raise RuntimeError(
            "GITHUB_REPO is not configured"
        )

    return Config(
        github_token=token,
        github_repo=normalize_github_repo(repo),
        poll_interval=int(
            os.getenv("POLL_INTERVAL", "5")
        ),
        freecad_host=os.getenv(
            "FREECAD_AGENT_HOST",
            "127.0.0.1",
        ),
        freecad_port=int(
            os.getenv(
                "FREECAD_AGENT_PORT",
                "8765",
            )
        ),
    )
