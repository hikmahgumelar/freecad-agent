import os
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class Config:
    github_token: str
    github_repo: str
    poll_interval: int


def load_config() -> Config:
    token = os.getenv("GITHUB_TOKEN")
    repo = os.getenv("GITHUB_REPO")
    poll_interval = int(os.getenv("POLL_INTERVAL", "5"))

    if not token:
        raise RuntimeError("GITHUB_TOKEN is not set")

    if not repo:
        raise RuntimeError("GITHUB_REPO is not set")

    if "/" not in repo:
        raise RuntimeError(
            "GITHUB_REPO must be in owner/repository format"
        )

    return Config(
        github_token=token,
        github_repo=repo,
        poll_interval=poll_interval,
    )
