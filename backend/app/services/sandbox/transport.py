import asyncio
import json
import logging
import re
import select
import shlex
import socket
from abc import ABC, abstractmethod
from collections.abc import AsyncIterable, AsyncIterator
from concurrent.futures import ThreadPoolExecutor
from contextlib import suppress
from dataclasses import asdict
from types import TracebackType
from typing import Any, Self

from claude_agent_sdk._errors import (
    CLIConnectionError,
    CLIJSONDecodeError,
    ProcessError,
)
from claude_agent_sdk._internal.transport import Transport
from claude_agent_sdk._version import __version__ as sdk_version
from claude_agent_sdk.types import ClaudeAgentOptions

from app.services.sandbox.types import DockerConfig

logger = logging.getLogger(__name__)

DEFAULT_MAX_BUFFER_SIZE = 1024 * 1024 * 10  # 10MB
STDOUT_QUEUE_MAXSIZE = 32
ANSI_ESCAPE_RE = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")


class BaseSandboxTransport(Transport, ABC):
    _SENTINEL = object()

    def __init__(
        self,
        *,
        sandbox_id: str,
        prompt: str | AsyncIterable[dict[str, Any]],
        options: ClaudeAgentOptions,
    ) -> None:
        self._sandbox_id = sandbox_id
        self._prompt = prompt
        self._options = options
        self._max_buffer_size = (
            options.max_buffer_size
            if options.max_buffer_size is not None
            else DEFAULT_MAX_BUFFER_SIZE
        )
        self._json_decoder = json.JSONDecoder()
        self._monitor_task: asyncio.Task[None] | None = None
        self._stdout_queue: asyncio.Queue[str | object] = asyncio.Queue(
            maxsize=STDOUT_QUEUE_MAXSIZE
        )
        self._ready = False
        self._exit_error: Exception | None = None
        self._stdin_closed = False

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> bool:
        try:
            await self.close()
        except Exception as cleanup_error:
            self._get_logger().error(
                f"Error during {self.__class__.__name__} cleanup: {cleanup_error}",
                exc_info=True,
            )
            if exc_type is None:
                raise
        return False

    @abstractmethod
    def _get_logger(self) -> Any:
        pass

    def _prepare_environment(self) -> tuple[dict[str, str], str, str]:
        envs = {
            "CLAUDE_CODE_ENTRYPOINT": "sdk-py",
            "CLAUDE_AGENT_SDK_VERSION": sdk_version,
            "CLAUDE_CODE_SANDBOX": "1",
            "PYTHONUNBUFFERED": "1",
        }
        envs.update(self._options.env or {})
        cwd = str(self._options.cwd) if self._options.cwd else "/home/user"
        user = self._options.user or "user"
        return envs, cwd, user

    async def _cancel_task(self, task: asyncio.Task[Any] | None) -> None:
        if task:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task

    def _ensure_input_open(self) -> None:
        if self._stdin_closed:
            raise CLIConnectionError("Cannot write after input has been closed")

    async def _put_sentinel(self) -> None:
        try:
            self._stdout_queue.put_nowait(self._SENTINEL)
        except asyncio.QueueFull:
            pass

    @abstractmethod
    async def connect(self) -> None:
        pass

    @abstractmethod
    async def _cleanup_resources(self) -> None:
        pass

    @abstractmethod
    def _is_connection_ready(self) -> bool:
        pass

    @abstractmethod
    async def _send_data(self, data: str) -> None:
        pass

    @abstractmethod
    async def _send_eof(self) -> None:
        pass

    async def close(self) -> None:
        if self._ready:
            await self.end_input()
        self._ready = False
        await self._cancel_task(self._monitor_task)
        self._monitor_task = None
        await self._cleanup_resources()
        self._stdin_closed = False
        await self._put_sentinel()

    async def write(self, data: str) -> None:
        if not self._ready or not self._is_connection_ready():
            raise CLIConnectionError("Transport is not ready for writing")
        self._ensure_input_open()
        try:
            await self._send_data(data)
        except CLIConnectionError:
            raise
        except Exception as exc:
            self._exit_error = CLIConnectionError(
                f"Failed to send data to Claude CLI: {exc}"
            )
            raise self._exit_error

    async def end_input(self) -> None:
        if not self._ready or not self._is_connection_ready():
            return
        if self._stdin_closed:
            return
        try:
            await self._send_eof()
            self._stdin_closed = True
        except Exception:
            pass

    def read_messages(self) -> AsyncIterator[dict[str, Any]]:
        return self._parse_cli_output()

    def is_ready(self) -> bool:
        return self._ready

    def _build_command(self) -> str:
        cli_binary = str(self._options.cli_path) if self._options.cli_path else "claude"
        cmd = [cli_binary, "--output-format", "stream-json", "--verbose"]

        if self._options.system_prompt is None:
            pass
        elif isinstance(self._options.system_prompt, str):
            cmd.extend(["--system-prompt", self._options.system_prompt])
        else:
            if (
                self._options.system_prompt.get("type") == "preset"
                and "append" in self._options.system_prompt
            ):
                cmd.extend(
                    ["--append-system-prompt", self._options.system_prompt["append"]]
                )

        if self._options.allowed_tools:
            cmd.extend(["--allowedTools", ",".join(self._options.allowed_tools)])

        if self._options.max_turns:
            cmd.extend(["--max-turns", str(self._options.max_turns)])

        if self._options.disallowed_tools:
            cmd.extend(["--disallowedTools", ",".join(self._options.disallowed_tools)])

        if self._options.model:
            cmd.extend(["--model", self._options.model])

        if self._options.permission_prompt_tool_name:
            cmd.extend(
                ["--permission-prompt-tool", self._options.permission_prompt_tool_name]
            )

        if self._options.permission_mode:
            cmd.extend(["--permission-mode", self._options.permission_mode])

        if self._options.continue_conversation:
            cmd.append("--continue")

        if self._options.resume:
            cmd.extend(["--resume", self._options.resume])

        if self._options.settings:
            cmd.extend(["--settings", self._options.settings])

        for directory in self._options.add_dirs:
            cmd.extend(["--add-dir", str(directory)])

        if self._options.mcp_servers:
            if isinstance(self._options.mcp_servers, dict):
                servers_for_cli: dict[str, Any] = {}
                for name, config in self._options.mcp_servers.items():
                    if isinstance(config, dict) and config.get("type") == "sdk":
                        servers_for_cli[name] = {
                            key: value
                            for key, value in config.items()
                            if key != "instance"
                        }
                    else:
                        servers_for_cli[name] = config
                if servers_for_cli:
                    cmd.extend(
                        ["--mcp-config", json.dumps({"mcpServers": servers_for_cli})]
                    )
            else:
                cmd.extend(["--mcp-config", str(self._options.mcp_servers)])

        if self._options.include_partial_messages:
            cmd.append("--include-partial-messages")

        if self._options.fork_session:
            cmd.append("--fork-session")

        if self._options.max_thinking_tokens:
            cmd.extend(
                ["--max-thinking-tokens", str(self._options.max_thinking_tokens)]
            )

        if self._options.agents:
            agents_dict = {
                name: {k: v for k, v in asdict(agent_def).items() if v is not None}
                for name, agent_def in self._options.agents.items()
            }
            cmd.extend(["--agents", json.dumps(agents_dict)])

        sources_value = (
            ",".join(self._options.setting_sources)
            if self._options.setting_sources is not None
            else ""
        )
        cmd.extend(["--setting-sources", sources_value])

        for flag, value in self._options.extra_args.items():
            if value is None:
                cmd.append(f"--{flag}")
            else:
                cmd.extend([f"--{flag}", str(value)])

        cmd.extend(["--input-format", "stream-json"])
        return shlex.join(cmd)

    def _parse_json_buffer(self, buffer: str) -> tuple[str, list[Any]]:
        messages: list[Any] = []
        working = buffer

        while working:
            stripped = working.lstrip()
            leading = len(working) - len(stripped)
            if leading:
                working = stripped
            try:
                data, offset = self._json_decoder.raw_decode(working)
            except json.JSONDecodeError:
                break
            messages.append(data)
            working = working[offset:]

        return working, messages

    async def _parse_cli_output(self) -> AsyncIterator[dict[str, Any]]:
        if not self._ready and not self._monitor_task:
            raise CLIConnectionError("Transport is not connected")

        json_buffer = ""
        json_started = False
        should_stop = False

        while True:
            chunk = await self._stdout_queue.get()

            if chunk is self._SENTINEL:
                break
            if not isinstance(chunk, str):
                continue

            clean_chunk = ANSI_ESCAPE_RE.sub("", chunk)
            clean_chunk = clean_chunk.replace("\r", "")

            json_lines = clean_chunk.split("\n")
            for json_line in json_lines:
                json_line = json_line.strip()
                if not json_line:
                    continue

                if not json_started:
                    first_brace_positions = [
                        pos
                        for pos in (json_line.find("{"), json_line.find("["))
                        if pos != -1
                    ]
                    if not first_brace_positions:
                        continue
                    json_line = json_line[min(first_brace_positions) :]
                    json_started = True

                json_buffer += json_line
                if len(json_buffer) > self._max_buffer_size:
                    json_buffer = ""
                    raise CLIJSONDecodeError(
                        json_line,
                        ValueError(
                            f"CLI output exceeded max buffer size of {self._max_buffer_size}"
                        ),
                    )

                json_buffer, parsed_messages = self._parse_json_buffer(json_buffer)
                if parsed_messages:
                    for data in parsed_messages:
                        yield data
                        if isinstance(data, dict) and data.get("type") == "result":
                            json_buffer = ""
                            should_stop = True
                            break
                    if not json_buffer:
                        json_started = False
                if should_stop:
                    break
            if should_stop:
                break

        if json_buffer:
            leftover, parsed_messages = self._parse_json_buffer(json_buffer)
            for data in parsed_messages:
                yield data
            if leftover.strip():
                try:
                    json.loads(leftover)
                except json.JSONDecodeError as exc:
                    raise CLIJSONDecodeError(leftover, exc) from exc

        if self._exit_error:
            raise self._exit_error


class DockerSandboxTransport(BaseSandboxTransport):
    def __init__(
        self,
        *,
        sandbox_id: str,
        docker_config: DockerConfig,
        prompt: str | AsyncIterable[dict[str, Any]],
        options: ClaudeAgentOptions,
    ) -> None:
        super().__init__(sandbox_id=sandbox_id, prompt=prompt, options=options)
        self._docker_config = docker_config
        self._executor = ThreadPoolExecutor(max_workers=4)
        self._docker_client: Any = None
        self._container: Any = None
        self._exec_id: str | None = None
        self._socket: Any = None
        self._reader_task: asyncio.Task[None] | None = None

    def _get_logger(self) -> Any:
        return logger

    def _get_docker_client(self) -> Any:
        if self._docker_client is None:
            try:
                import docker

                if self._docker_config.host:
                    self._docker_client = docker.DockerClient(
                        base_url=self._docker_config.host
                    )
                else:
                    self._docker_client = docker.from_env()
            except ImportError:
                raise CLIConnectionError(
                    "Docker SDK not installed. Run: pip install docker"
                )
            except Exception as e:
                raise CLIConnectionError(f"Failed to connect to Docker: {e}")
        return self._docker_client

    def _get_container(self) -> Any:
        client = self._get_docker_client()
        try:
            container = client.containers.get(f"claudex-sandbox-{self._sandbox_id}")
            container.reload()
            if container.status != "running":
                container.start()
            return container
        except Exception as e:
            raise CLIConnectionError(
                f"Failed to connect to sandbox {self._sandbox_id}: {e}"
            )

    def _create_exec(
        self,
        command_line: str,
        envs: dict[str, str],
        cwd: str,
        user: str,
    ) -> tuple[str, Any]:
        exec_result = self._container.client.api.exec_create(
            self._container.id,
            cmd=["bash", "-c", f"exec {command_line}"],
            stdin=True,
            tty=False,
            environment=envs,
            workdir=cwd,
            user=user,
        )
        exec_id = exec_result["Id"]
        socket = self._container.client.api.exec_start(
            exec_id,
            socket=True,
            tty=False,
        )
        return exec_id, socket

    async def connect(self) -> None:
        if self._ready:
            return
        self._stdin_closed = False

        loop = asyncio.get_running_loop()

        try:
            self._container = await loop.run_in_executor(
                self._executor, self._get_container
            )
        except Exception as exc:
            raise CLIConnectionError(
                f"Failed to connect to sandbox {self._sandbox_id}: {exc}"
            ) from exc

        command_line = self._build_command()
        envs, cwd, user = self._prepare_environment()
        envs["TERM"] = "xterm-256color"

        try:
            self._exec_id, self._socket = await loop.run_in_executor(
                self._executor,
                lambda: self._create_exec(command_line, envs, cwd, user),
            )
        except Exception as exc:
            raise CLIConnectionError(f"Failed to start Claude CLI: {exc}") from exc

        self._reader_task = loop.create_task(self._read_socket_data())
        self._monitor_task = loop.create_task(self._monitor_process())
        self._ready = True

    def _is_connection_ready(self) -> bool:
        return self._socket is not None

    def _send_signal_to_pid(self, pid: int, signal: str) -> None:
        try:
            self._container.exec_run(
                ["/bin/kill", f"-{signal}", f"-{pid}"], user="root"
            )
            self._container.exec_run(["/bin/kill", f"-{signal}", str(pid)], user="root")
        except Exception:
            pass

    async def _kill_exec_process(self) -> None:
        exec_id = self._exec_id
        container = self._container
        if not exec_id or not container:
            return
        loop = asyncio.get_running_loop()
        try:
            info = await loop.run_in_executor(self._executor, self._get_exec_info)
            if not info or not info.get("Running", False):
                return
            pid = info.get("Pid")
            if not pid:
                return
            await loop.run_in_executor(
                self._executor, self._send_signal_to_pid, pid, "TERM"
            )
            await asyncio.sleep(0.5)
            info = await loop.run_in_executor(self._executor, self._get_exec_info)
            if info and info.get("Running", False):
                await loop.run_in_executor(
                    self._executor, self._send_signal_to_pid, pid, "KILL"
                )
        except Exception as e:
            logger.debug("Failed to kill exec process: %s", e)

    async def _cleanup_resources(self) -> None:
        await self._cancel_task(self._reader_task)
        self._reader_task = None

        await self._kill_exec_process()

        if self._socket:
            with suppress(Exception):
                self._socket.close()
            self._socket = None

        self._exec_id = None

        if self._docker_client:
            with suppress(Exception):
                self._docker_client.close()
            self._docker_client = None

        await asyncio.to_thread(self._executor.shutdown, wait=True)

    async def _send_data(self, data: str) -> None:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            self._executor, lambda: self._socket_send(data.encode("utf-8"))
        )

    async def _send_eof(self) -> None:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(self._executor, self._shutdown_socket_write)

    def _shutdown_socket_write(self) -> None:
        if not self._socket:
            return
        if hasattr(self._socket, "shutdown"):
            try:
                self._socket.shutdown(socket.SHUT_WR)
                return
            except Exception:
                pass
        if hasattr(self._socket, "_sock"):
            try:
                self._socket._sock.shutdown(socket.SHUT_WR)
                return
            except Exception:
                pass
        self._socket_send(b"\x04")

    def _get_socket_fd(self) -> int | None:
        if not self._socket:
            return None
        if hasattr(self._socket, "fileno"):
            try:
                return int(self._socket.fileno())
            except Exception:
                pass
        if hasattr(self._socket, "_sock"):
            try:
                return int(self._socket._sock.fileno())
            except Exception:
                pass
        return None

    def _recv_with_select(self, timeout: float) -> bytes | None:
        fd = self._get_socket_fd()
        if fd is None:
            return None
        try:
            readable, _, _ = select.select([fd], [], [], timeout)
            if not readable:
                return b""
            return self._socket_recv(4096)
        except Exception:
            return None

    async def _read_socket_data(self) -> None:
        loop = asyncio.get_running_loop()
        buffer = b""
        drain_empty_count = 0

        try:
            while True:
                timeout = 5.0 if self._ready else 0.2
                data = await loop.run_in_executor(
                    self._executor, self._recv_with_select, timeout
                )
                if data is None:
                    break
                if len(data) == 0:
                    if not self._ready:
                        drain_empty_count += 1
                        if drain_empty_count >= 5:
                            break
                    continue
                drain_empty_count = 0

                buffer += data

                while len(buffer) >= 8:
                    stream_type = buffer[0]
                    frame_size = int.from_bytes(buffer[4:8], byteorder="big")

                    if frame_size > self._max_buffer_size:
                        buffer = b""
                        break

                    if len(buffer) < 8 + frame_size:
                        break

                    payload = buffer[8 : 8 + frame_size]
                    buffer = buffer[8 + frame_size :]

                    if stream_type == 1:
                        decoded = payload.decode("utf-8", errors="replace")
                        await self._stdout_queue.put(decoded)
                    elif stream_type == 2 and self._options.stderr:
                        try:
                            self._options.stderr(
                                payload.decode("utf-8", errors="replace")
                            )
                        except Exception:
                            pass
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error("Socket reader error: %s", e)
        finally:
            await self._put_sentinel()

    def _socket_recv(self, size: int) -> bytes:
        if not self._socket:
            return b""
        if hasattr(self._socket, "recv"):
            return bytes(self._socket.recv(size))
        if hasattr(self._socket, "read"):
            return bytes(self._socket.read(size))
        if hasattr(self._socket, "_sock"):
            return bytes(self._socket._sock.recv(size))
        raise CLIConnectionError("Socket does not support recv/read")

    def _socket_send(self, payload: bytes) -> None:
        if not self._socket:
            return
        if hasattr(self._socket, "sendall"):
            self._socket.sendall(payload)
            return
        if hasattr(self._socket, "send"):
            self._socket.send(payload)
            return
        if hasattr(self._socket, "_sock"):
            self._socket._sock.sendall(payload)
            return
        raise CLIConnectionError("Socket does not support send")

    def _get_exec_info(self) -> dict[str, Any] | None:
        try:
            result: dict[str, Any] = self._container.client.api.exec_inspect(
                self._exec_id
            )
            return result
        except Exception as e:
            logger.warning("exec_inspect failed for exec_id %s: %s", self._exec_id, e)
            return None

    async def _monitor_process(self) -> None:
        if not self._exec_id or not self._container:
            return

        loop = asyncio.get_running_loop()

        try:
            while self._ready:
                await asyncio.sleep(0.5)

                info = await loop.run_in_executor(self._executor, self._get_exec_info)
                if info is None:
                    self._exit_error = CLIConnectionError(
                        "Claude CLI process disappeared"
                    )
                    break

                if not info.get("Running", True):
                    exit_code = info.get("ExitCode", -1)
                    if exit_code != 0:
                        self._exit_error = ProcessError(
                            "Claude CLI exited with an error",
                            exit_code=exit_code,
                            stderr="",
                        )
                    break
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            self._exit_error = CLIConnectionError(
                f"Claude CLI stopped unexpectedly: {exc}"
            )
        finally:
            self._ready = False
