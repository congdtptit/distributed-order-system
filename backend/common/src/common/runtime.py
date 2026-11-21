"""Background workers inside a service process: the consumer loop and the outbox relay run in
threads next to the HTTP API, started and stopped with the app."""

import logging
import os
import socket
import threading
from collections.abc import Callable

log = logging.getLogger(__name__)


def configure_logging() -> None:
    """One format for every service. Called by each app at start; with reload, uvicorn runs the
    app in a child process, so this cannot happen in common.service.main."""
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def instance_name() -> str:
    return socket.gethostname()


class Workers:
    def __init__(self) -> None:
        self._stop = threading.Event()
        self._threads: dict[str, threading.Thread] = {}

    def start(self, name: str, target: Callable[[threading.Event], None]) -> None:
        def run() -> None:
            try:
                target(self._stop)
            except Exception:
                log.exception("worker %s stopped on an error", name)
                raise

        thread = threading.Thread(target=run, name=name, daemon=True)
        self._threads[name] = thread
        thread.start()

    def alive(self) -> dict[str, bool]:
        return {name: t.is_alive() for name, t in self._threads.items()}

    def stop(self, timeout_s: float = 15) -> None:
        self._stop.set()
        for thread in self._threads.values():
            thread.join(timeout_s)
