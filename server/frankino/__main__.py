"""`python -m frankino`: accende il server."""

from __future__ import annotations

import logging

import uvicorn

from frankino.app import create_app
from frankino.config import Settings


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    s = Settings.from_env()
    uvicorn.run(create_app(s), host=s.host, port=s.port, ws_max_size=16 * 1024 * 1024)


if __name__ == "__main__":
    main()
