from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path
from threading import Lock
from typing import Any

LOG_DIR = Path(os.getenv("MINESWEEPER_LOG_DIR", "logs"))
MAX_BYTES = int(os.getenv("MINESWEEPER_LOG_MAX_BYTES", str(2 * 1024 * 1024)))
BACKUP_COUNT = int(os.getenv("MINESWEEPER_LOG_BACKUP_COUNT", "5"))

_HANDLER_LOCK = Lock()
_CONFIGURED_LOGGERS: set[str] = set()

_RESERVED_RECORD_KEYS = {
    "name",
    "msg",
    "args",
    "levelname",
    "levelno",
    "pathname",
    "filename",
    "module",
    "exc_info",
    "exc_text",
    "stack_info",
    "lineno",
    "funcName",
    "created",
    "msecs",
    "relativeCreated",
    "thread",
    "threadName",
    "processName",
    "process",
    "message",
    "asctime",
}


def _safe_filename(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]", "_", value)
    return cleaned[:100] if cleaned else "unknown"


class JsonLineFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created, timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        for key, value in record.__dict__.items():
            if key in _RESERVED_RECORD_KEYS:
                continue
            if key.startswith("_"):
                continue
            payload[key] = value

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, ensure_ascii=False, default=str)


def _make_file_handler(path: Path) -> RotatingFileHandler:
    path.parent.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(
        path,
        maxBytes=MAX_BYTES,
        backupCount=BACKUP_COUNT,
        encoding="utf-8",
    )
    handler.setFormatter(JsonLineFormatter())
    return handler


def _make_console_handler() -> logging.StreamHandler:
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")
    )
    return handler


def _configure_logger(
    name: str, file_path: Path, *, console: bool = False
) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    if name in _CONFIGURED_LOGGERS:
        return logger

    logger.addHandler(_make_file_handler(file_path))

    if console:
        logger.addHandler(_make_console_handler())

    _CONFIGURED_LOGGERS.add(name)
    return logger


def get_system_logger() -> logging.Logger:
    return _configure_logger("system", LOG_DIR / "system.log", console=True)


def get_game_logger(game_code: str) -> logging.Logger:
    safe_code = _safe_filename(game_code.upper())
    return _configure_logger(
        f"game.{safe_code}",
        LOG_DIR / "games" / f"game_{safe_code}.log",
    )


def get_client_logger(player_id: str) -> logging.Logger:
    safe_player_id = _safe_filename(player_id)
    return _configure_logger(
        f"client.{safe_player_id}",
        LOG_DIR / "clients" / f"client_{safe_player_id}.log",
    )


def event(
    logger: logging.Logger,
    name: str,
    *,
    level: int = logging.INFO,
    **fields: Any,
) -> None:
    logger.log(level, name, extra={"event": name, **fields})


def event_names(events: list[dict]) -> list[str]:
    return [str(item.get("type", "unknown")) for item in events]
