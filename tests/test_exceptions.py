"""Тесты для исключений task-orchestrator."""

from __future__ import annotations

import pytest

from task_sequencer.exceptions import (
    DependencyError,
    ProgressError,
    TaskExecutionError,
    TaskOrchestratorError,
)


class TestTaskOrchestratorError:
    """Тесты для базового исключения TaskOrchestratorError."""

    def test_base_exception_creation(self) -> None:
        """Тест создания базового исключения."""
        error = TaskOrchestratorError("Test error message")
        assert str(error) == "Test error message"
        assert error.message == "Test error message"

    def test_base_exception_is_exception(self) -> None:
        """Тест проверяет, что TaskOrchestratorError наследуется от Exception."""
        error = TaskOrchestratorError("Test")
        assert isinstance(error, Exception)


class TestDependencyError:
    """Тесты для DependencyError."""

    def test_dependency_error_creation(self) -> None:
        """Тест создания DependencyError."""
        error = DependencyError("Dependency validation failed")
        assert str(error) == "Dependency validation failed"
        assert error.message == "Dependency validation failed"

    def test_dependency_error_inheritance(self) -> None:
        """Тест проверяет наследование DependencyError от TaskOrchestratorError."""
        error = DependencyError("Test")
        assert isinstance(error, TaskOrchestratorError)
        assert isinstance(error, Exception)

    def test_dependency_error_raises(self) -> None:
        """Тест проверяет, что DependencyError может быть выброшено."""
        with pytest.raises(DependencyError, match="Dependency error"):
            raise DependencyError("Dependency error")


class TestTaskExecutionError:
    """Тесты для TaskExecutionError."""

    def test_task_execution_error_creation(self) -> None:
        """Тест создания TaskExecutionError без task_name."""
        error = TaskExecutionError("Execution failed")
        assert str(error) == "Execution failed"
        assert error.message == "Execution failed"
        assert error.task_name is None

    def test_task_execution_error_with_task_name(self) -> None:
        """Тест создания TaskExecutionError с task_name."""
        error = TaskExecutionError("Execution failed", task_name="test_task")
        assert str(error) == "Execution failed"
        assert error.message == "Execution failed"
        assert error.task_name == "test_task"

    def test_task_execution_error_inheritance(self) -> None:
        """Тест проверяет наследование TaskExecutionError от TaskOrchestratorError."""
        error = TaskExecutionError("Test")
        assert isinstance(error, TaskOrchestratorError)
        assert isinstance(error, Exception)

    def test_task_execution_error_raises(self) -> None:
        """Тест проверяет, что TaskExecutionError может быть выброшено."""
        with pytest.raises(TaskExecutionError, match="Execution error"):
            raise TaskExecutionError("Execution error", task_name="test_task")


class TestProgressError:
    """Тесты для ProgressError."""

    def test_progress_error_creation(self) -> None:
        """Тест создания ProgressError."""
        error = ProgressError("Progress save failed")
        assert str(error) == "Progress save failed"
        assert error.message == "Progress save failed"

    def test_progress_error_inheritance(self) -> None:
        """Тест проверяет наследование ProgressError от TaskOrchestratorError."""
        error = ProgressError("Test")
        assert isinstance(error, TaskOrchestratorError)
        assert isinstance(error, Exception)

    def test_progress_error_raises(self) -> None:
        """Тест проверяет, что ProgressError может быть выброшено."""
        with pytest.raises(ProgressError, match="Progress error"):
            raise ProgressError("Progress error")


class TestExceptionHierarchy:
    """Тесты для проверки иерархии исключений."""

    def test_all_exceptions_inherit_from_base(self) -> None:
        """Тест проверяет, что все исключения наследуются от TaskOrchestratorError."""
        assert issubclass(DependencyError, TaskOrchestratorError)
        assert issubclass(TaskExecutionError, TaskOrchestratorError)
        assert issubclass(ProgressError, TaskOrchestratorError)

    def test_all_exceptions_inherit_from_exception(self) -> None:
        """Тест проверяет, что все исключения наследуются от Exception."""
        assert issubclass(TaskOrchestratorError, Exception)
        assert issubclass(DependencyError, Exception)
        assert issubclass(TaskExecutionError, Exception)
        assert issubclass(ProgressError, Exception)



