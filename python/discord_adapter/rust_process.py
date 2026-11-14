"""
Async process supervisor for the Rust engine.

V1 serializes requests to keep response correlation safe.
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys

from pathlib import Path
from typing import Any

from .protocol import (
    EngineResponse,
    decode_response,
    encode_request,
)


_LOG = logging.getLogger("mhn.v4.rust")


class RustProcessError(RuntimeError):
    """Rust process or protocol failure."""


class RustProcess:

    def __init__(
        self,
        command: list[str] | None = None,
        request_timeout: float = 5.0,
    ) -> None:

        self._command = (
            command or self._default_command()
        )

        self._request_timeout = request_timeout

        self._process: (
            asyncio.subprocess.Process | None
        ) = None

        self._request_lock = asyncio.Lock()

        self._stderr_task: (
            asyncio.Task[None] | None
        ) = None

    @staticmethod
    def _default_command() -> list[str]:

        configured = os.getenv("MHN_RUST_BIN")

        if configured:
            return [configured]

        root = Path(__file__).resolve().parents[2]

        binary = (
            root
            / "rust"
            / "target"
            / "release"
            / "mhn-service"
        )

        if sys.platform == "win32":
            binary = binary.with_suffix(".exe")

        return [str(binary)]

    async def start(self) -> None:

        if (
            self._process is not None
            and self._process.returncode is None
        ):
            return

        try:
            self._process = (
                await asyncio.create_subprocess_exec(
                    *self._command,
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
            )

        except (FileNotFoundError, PermissionError, OSError) as error:

            raise RustProcessError(
                f"Could not start Rust service: {error}"
            ) from error

        self._stderr_task = asyncio.create_task(
            self._drain_stderr()
        )

    async def _drain_stderr(self) -> None:

        process = self._process

        if process is None or process.stderr is None:
            return

        while True:

            line = await process.stderr.readline()

            if not line:
                return

            _LOG.info(
                "rust: %s",
                line.decode(
                    "utf-8",
                    errors="replace",
                ).rstrip(),
            )

    async def request(
        self,
        request_id: str,
        operation: str,
        payload: dict[str, Any] | None = None,
    ) -> EngineResponse:

        async with self._request_lock:

            await self.start()

            process = self._process

            if (
                process is None
                or process.stdin is None
                or process.stdout is None
            ):
                raise RustProcessError(
                    "Rust process pipes unavailable"
                )

            encoded = encode_request(
                request_id,
                operation,
                payload,
            )

            process.stdin.write(
                (encoded + "\n").encode("utf-8")
            )

            try:

                await process.stdin.drain()

                raw_line = await asyncio.wait_for(
                    process.stdout.readline(),
                    timeout=self._request_timeout,
                )

                if not raw_line:
                    raise RustProcessError(
                        "Rust service closed stdout"
                    )

                response = decode_response(
                    raw_line.decode(
                        "utf-8"
                    ).rstrip("\r\n")
                )

                if response.request_id != request_id:
                    raise RustProcessError(
                        "Response request_id mismatch"
                    )

                return response

            except (
                asyncio.TimeoutError,
                ValueError,
                OSError,
            ) as error:

                await self.close()

                raise RustProcessError(
                    f"Rust request failed: {error}"
                ) from error

    async def close(self) -> None:

        process = self._process

        self._process = None

        if (
            process is not None
            and process.returncode is None
        ):

            if process.stdin is not None:
                process.stdin.close()

            try:

                await asyncio.wait_for(
                    process.wait(),
                    timeout=2.0,
                )

            except asyncio.TimeoutError:

                process.kill()
                await process.wait()

        task = self._stderr_task

        self._stderr_task = None

        if task is not None:

            task.cancel()

            try:
                await task

            except asyncio.CancelledError:
                pass
