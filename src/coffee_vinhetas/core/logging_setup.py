"""Configuração centralizada de logs rotativos locais."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path

from .constants import APP_ORG


def get_app_data_dir() -> Path:
    base = Path(os.environ.get("LOCALAPPDATA") or Path.home()) / APP_ORG / "CoffeeVinhetasExpress"
    base.mkdir(parents=True, exist_ok=True)
    return base


def setup_logging() -> tuple[logging.Logger, Path]:
    log_dir = get_app_data_dir() / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "coffee_vinhetas.log"

    logger = logging.getLogger("coffee_vinhetas")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(threadName)s: %(message)s")
        file_handler = RotatingFileHandler(log_file, maxBytes=2_000_000, backupCount=3, encoding="utf-8")
        file_handler.setFormatter(fmt)
        logger.addHandler(file_handler)

        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(fmt)
        logger.addHandler(stream_handler)
    return logger, log_file


LOGGER, LOG_FILE_PATH = setup_logging()
