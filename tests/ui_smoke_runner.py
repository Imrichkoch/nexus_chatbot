from __future__ import annotations

import socket
import time
from threading import Thread

import uvicorn

from local_ui_server import build_app
from ui_smoke import run


def wait_for_port(port: int, timeout_seconds: float = 15) -> None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                return
        except OSError:
            time.sleep(0.1)
    raise RuntimeError(f"UI test server did not start on port {port}.")


def main() -> None:
    config = uvicorn.Config(
        build_app(),
        host="127.0.0.1",
        port=8765,
        log_level="warning",
    )
    server = uvicorn.Server(config)
    thread = Thread(target=server.run, name="nexus-ui-smoke-server", daemon=True)
    thread.start()
    wait_for_port(8765)
    try:
        run()
    finally:
        server.should_exit = True
        thread.join(timeout=10)
        if thread.is_alive():
            raise RuntimeError("UI test server did not stop cleanly.")


if __name__ == "__main__":
    main()
