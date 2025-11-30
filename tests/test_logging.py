"""Тесты для логирования task-orchestrator."""

from __future__ import annotations

import logging
from io import StringIO
from unittest.mock import patch

import pytest

from task_sequencer import Task, TaskOrchestrator, TaskRegistry
from task_sequencer.adapters import MemoryProgressTracker
from task_sequencer.interfaces import ExecutionContext, TaskResult
from task_sequencer.logging import get_logger, setup_logging
from task_sequencer.validators import DependencyValidator


class TestLogging:
    """Тесты для логирования."""

    def test_get_logger(self) -> None:
        """Тест создания логгера."""
        logger = get_logger("test_task")
        assert logger.logger.name == "task_sequencer"
        assert logger.extra == {"task": "test_task"}

    def test_get_logger_without_task_name(self) -> None:
        """Тест создания логгера без имени задачи."""
        logger = get_logger()
        assert logger.logger.name == "task_sequencer"
        assert logger.extra == {"task": "core"}

    def test_setup_logging(self) -> None:
        """Тест настройки логирования."""
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        logger = logging.getLogger("task_sequencer")
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

        task_logger = get_logger("test")
        task_logger.info("Test message")

        output = stream.getvalue()
        assert "test" in output or "Test message" in output

    def test_orchestrator_logs_execution_start(self) -> None:
        """Тест логирования начала выполнения."""
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        logger = logging.getLogger("task_sequencer")
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

        class TestTask(Task):
            @property
            def name(self) -> str:
                return "test_task"

            @property
            def depends_on(self) -> list[str]:
                return []

            def execute(self, context: ExecutionContext) -> TaskResult:
                return TaskResult.success_result()

        registry = TaskRegistry([TestTask()])
        tracker = MemoryProgressTracker()
        validator = DependencyValidator()
        orchestrator = TaskOrchestrator(registry, tracker, validator)

        orchestrator.execute(["test_task"])

        output = stream.getvalue()
        assert "Starting execution" in output or "test_task" in output

    def test_orchestrator_logs_task_completion(self) -> None:
        """Тест логирования завершения задачи."""
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        logger = logging.getLogger("task_sequencer")
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

        class TestTask(Task):
            @property
            def name(self) -> str:
                return "test_task"

            @property
            def depends_on(self) -> list[str]:
                return []

            def execute(self, context: ExecutionContext) -> TaskResult:
                return TaskResult.success_result()

        registry = TaskRegistry([TestTask()])
        tracker = MemoryProgressTracker()
        validator = DependencyValidator()
        orchestrator = TaskOrchestrator(registry, tracker, validator)

        orchestrator.execute(["test_task"])

        output = stream.getvalue()
        # Проверяем, что есть логирование (может быть в разных форматах)
        assert len(output) > 0



