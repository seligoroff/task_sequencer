"""Логирование для task-sequencer."""

from __future__ import annotations

import logging
from logging import LoggerAdapter

# Логгер для task-sequencer
_logger = logging.getLogger("task_sequencer")


def get_logger(task_name: str | None = None) -> LoggerAdapter:
    """Создает логгер с префиксом для task-sequencer.

    Args:
        task_name: Имя задачи (опционально)

    Returns:
        LoggerAdapter с префиксом [task-sequencer] и именем задачи

    Пример использования:
        >>> logger = get_logger("my_task")
        >>> logger.info("Task started")
        # Выведет: [task-sequencer] my_task: Task started
    """
    return logging.LoggerAdapter(_logger, {"task": task_name or "core"})


def setup_logging(level: int = logging.INFO) -> None:
    """Настраивает логирование для task-sequencer.

    Args:
        level: Уровень логирования (по умолчанию INFO)

    Пример использования:
        >>> from task_sequencer.logging import setup_logging
        >>> import logging
        >>> setup_logging(logging.DEBUG)
    """
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "[task-sequencer] %(task)s: %(message)s", style="%"
    )
    handler.setFormatter(formatter)
    _logger.addHandler(handler)
    _logger.setLevel(level)
    _logger.propagate = False


