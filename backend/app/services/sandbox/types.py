from dataclasses import dataclass
from typing import Any, Callable, Coroutine


@dataclass
class CommandResult:
    stdout: str
    stderr: str
    exit_code: int


@dataclass
class FileMetadata:
    path: str
    type: str
    size: int
    modified: float
    is_binary: bool = False


@dataclass
class FileContent:
    path: str
    content: str
    type: str
    is_binary: bool


@dataclass
class PtySession:
    id: str
    pid: int | None
    rows: int
    cols: int


@dataclass
class PtySize:
    rows: int
    cols: int


@dataclass
class CheckpointInfo:
    message_id: str
    created_at: str


@dataclass
class PreviewLink:
    preview_url: str
    port: int


@dataclass
class SecretEntry:
    key: str
    value: str


@dataclass
class DockerConfig:
    image: str = "ghcr.io/mng-dev-ai/claudex-sandbox:latest"
    network: str = "claudex-sandbox-net"
    host: str | None = None
    preview_base_url: str = "http://localhost"
    user_home: str = "/home/user"
    openvscode_port: int = 8765
    sandbox_domain: str = ""
    traefik_network: str = ""


PtyDataCallbackType = Callable[[bytes], Coroutine[Any, Any, None]]
