"""Фикстуры pytest для тестирования task-orchestrator."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, Mock

import pytest

# Импорты будут добавляться по мере реализации модулей
from task_sequencer.progress import TaskProgress, TaskStatus


@pytest.fixture
def task_progress() -> TaskProgress:
    """Создает объект TaskProgress для тестирования."""
    return TaskProgress(
        task_name="test_task",
        status=TaskStatus.PENDING,
        metadata={},
    )


@pytest.fixture
def completed_task_progress() -> TaskProgress:
    """Создает объект TaskProgress со статусом COMPLETED."""
    return TaskProgress(
        task_name="test_task",
        status=TaskStatus.COMPLETED,
        metadata={},
    )


@pytest.fixture
def failed_task_progress() -> TaskProgress:
    """Создает объект TaskProgress со статусом FAILED."""
    return TaskProgress(
        task_name="test_task",
        status=TaskStatus.FAILED,
        error_message="Test error",
        metadata={"error": "Test error"},
    )


# Фикстуры для других компонентов будут добавляться по мере их реализации

