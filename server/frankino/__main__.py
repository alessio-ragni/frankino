"""`python -m frankino`: accende il server."""

from __future__ import annotations

import logging
import re

import uvicorn

from frankino.app import create_app
from frankino.config import Settings


class HideToken(logging.Filter):
    """Il gettone viaggia nell'indirizzo del websocket: nei registri non deve comparire."""

    PATTERN = re.compile(r"token=[^&\s\"']+")

    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        if "token=" in message:
            record.msg = self.PATTERN.sub("token=***", message)
            record.args = None
        return True


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    for handler in logging.getLogger().handlers:
        handler.addFilter(HideToken())
    s = Settings.from_env()
    # log_config=None: i registri di uvicorn passano dai nostri, filtro compreso.
    uvicorn.run(create_app(s), host=s.host, port=s.port, ws_max_size=16 * 1024 * 1024, log_config=None)


if __name__ == "__main__":
    main()
