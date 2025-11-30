"""Тесты для интерфейсов task-orchestrator."""

from __future__ import annotations

from typing import Any
from unittest.mock import Mock

import pytest

from task_sequencer.interfaces import (
    ExecutionContext,
    IterableTask,
    ProgressTracker,
    Task,
    TaskResult,
)
from task_sequencer.progress import TaskStatus


class TestTaskResult:
    """Тесты для TaskResult dataclass."""

    def test_create_success_result(self) -> None:
        """Тест создания успешного результата через success_result."""
        result = TaskResult.success_result(data={"key": "value"})

        assert result.success is True
        assert result.status == TaskStatus.COMPLETED
        assert result.data == {"key": "value"}
        assert result.error is None
        assert result.metadata == {}

    def test_create_success_result_with_metadata(self) -> None:
        """Тест создания успешного результата с метаданными."""
        metadata = {"duration": 1.5, "items_processed": 100}
        result = TaskResult.success_result(data=None, metadata=metadata)

        assert result.success is True
        assert result.status == TaskStatus.COMPLETED
        assert result.metadata == metadata

    def test_create_failure_result(self) -> None:
        """Тест создания результата с ошибкой через failure_result."""
        result = TaskResult.failure_result("Test error message")

        assert result.success is False
        assert result.status == TaskStatus.FAILED
        assert result.error == "Test error message"
        assert result.data is None
        assert result.metadata == {}

    def test_create_failure_result_with_metadata(self) -> None:
        """Тест создания результата с ошибкой и метаданными."""
        metadata = {"error_code": 500, "retry_count": 3}
        result = TaskResult.failure_result("Error", metadata=metadata)

        assert result.success is False
        assert result.status == TaskStatus.FAILED
        assert result.error == "Error"
        assert result.metadata == metadata

    def test_create_task_result_directly(self) -> None:
        """Тест создания TaskResult напрямую."""
        result = TaskResult(
            status=TaskStatus.IN_PROGRESS,
            data="test_data",
            error=None,
            metadata={"key": "value"},
        )

        # IN_PROGRESS не является COMPLETED, поэтому success = False
        assert result.success is False
        assert result.status == TaskStatus.IN_PROGRESS
        assert result.data == "test_data"
        assert result.error is None
        assert result.metadata == {"key": "value"}

    def test_task_result_metadata_default_factory(self) -> None:
        """Тест проверяет, что metadata использует default_factory."""
        result1 = TaskResult.success_result()
        result2 = TaskResult.success_result()

        result1.metadata["key1"] = "value1"
        result2.metadata["key2"] = "value2"

        assert result1.metadata == {"key1": "value1"}
        assert result2.metadata == {"key2": "value2"}
        assert result1.metadata is not result2.metadata


class TestExecutionContext:
    """Тесты для ExecutionContext dataclass."""

    def test_create_execution_context(self) -> None:
        """Тест создания ExecutionContext."""
        mock_tracker = Mock(spec=ProgressTracker)
        context = ExecutionContext(
            task_order=["task1", "task2"],
            results={},
            metadata={},
            progress_tracker=mock_tracker,
            mode="run",
        )

        assert context.task_order == ["task1", "task2"]
        assert context.results == {}
        assert context.metadata == {}
        assert context.progress_tracker is mock_tracker
        assert context.mode == "run"

    def test_execution_context_default_mode(self) -> None:
        """Тест проверяет, что mode по умолчанию 'run'."""
        mock_tracker = Mock(spec=ProgressTracker)
        context = ExecutionContext(
            task_order=["task1"],
            results={},
            metadata={},
            progress_tracker=mock_tracker,
        )

        assert context.mode == "run"

    def test_execution_context_with_results(self) -> None:
        """Тест создания ExecutionContext с результатами."""
        mock_tracker = Mock(spec=ProgressTracker)
        result1 = TaskResult.success_result()
        result2 = TaskResult.failure_result("Error")

        context = ExecutionContext(
            task_order=["task1", "task2"],
            results={"task1": result1, "task2": result2},
            metadata={"key": "value"},
            progress_tracker=mock_tracker,
        )

        assert len(context.results) == 2
        assert context.results["task1"].success is True
        assert context.results["task2"].success is False


class TestTaskABC:
    """Тесты для абстрактного класса Task."""

    def test_cannot_instantiate_task_abc(self) -> None:
        """Тест проверяет, что нельзя создать экземпляр Task ABC."""
        with pytest.raises(TypeError):
            Task()  # type: ignore[abstract]

    def test_task_abc_requires_name_property(self) -> None:
        """Тест проверяет, что подкласс Task должен реализовать name."""
        # Создаем неполную реализацию без name
        class IncompleteTask(Task):
            @property
            def depends_on(self) -> list[str]:
                return []

            def execute(self, context: ExecutionContext) -> TaskResult:
                return TaskResult.success_result()

        with pytest.raises(TypeError):
            IncompleteTask()  # type: ignore[abstract]

    def test_task_abc_requires_depends_on_property(self) -> None:
        """Тест проверяет, что подкласс Task должен реализовать depends_on."""
        # Создаем неполную реализацию без depends_on
        class IncompleteTask(Task):
            @property
            def name(self) -> str:
                return "test_task"

            def execute(self, context: ExecutionContext) -> TaskResult:
                return TaskResult.success_result()

        with pytest.raises(TypeError):
            IncompleteTask()  # type: ignore[abstract]

    def test_task_abc_requires_execute_method(self) -> None:
        """Тест проверяет, что подкласс Task должен реализовать execute."""
        # Создаем неполную реализацию без execute
        class IncompleteTask(Task):
            @property
            def name(self) -> str:
                return "test_task"

            @property
            def depends_on(self) -> list[str]:
                return []

        with pytest.raises(TypeError):
            IncompleteTask()  # type: ignore[abstract]

    def test_complete_task_implementation(self) -> None:
        """Тест полной реализации Task."""
        mock_tracker = Mock(spec=ProgressTracker)
        context = ExecutionContext(
            task_order=["test_task"],
            results={},
            metadata={},
            progress_tracker=mock_tracker,
        )

        class CompleteTask(Task):
            @property
            def name(self) -> str:
                return "test_task"

            @property
            def depends_on(self) -> list[str]:
                return []

            def execute(self, context: ExecutionContext) -> TaskResult:
                return TaskResult.success_result(data="completed")

        task = CompleteTask()
        assert task.name == "test_task"
        assert task.depends_on == []
        result = task.execute(context)
        assert result.success is True
        assert result.data == "completed"


class TestIterableTaskABC:
    """Тесты для абстрактного класса IterableTask."""

    def test_cannot_instantiate_iterable_task_abc(self) -> None:
        """Тест проверяет, что нельзя создать экземпляр IterableTask ABC."""
        with pytest.raises(TypeError):
            IterableTask()  # type: ignore[abstract]

    def test_iterable_task_inherits_from_task(self) -> None:
        """Тест проверяет, что IterableTask наследуется от Task."""
        assert issubclass(IterableTask, Task)

    def test_iterable_task_requires_get_items(self) -> None:
        """Тест проверяет, что подкласс IterableTask должен реализовать get_items."""
        # Создаем неполную реализацию без get_items
        class IncompleteIterableTask(IterableTask):
            @property
            def name(self) -> str:
                return "test_task"

            @property
            def depends_on(self) -> list[str]:
                return []

            def execute(self, context: ExecutionContext) -> TaskResult:
                return TaskResult.success_result()

            def execute_for_item(
                self, item: Any, context: ExecutionContext
            ) -> None:
                pass

        with pytest.raises(TypeError):
            IncompleteIterableTask()  # type: ignore[abstract]

    def test_iterable_task_requires_execute_for_item(self) -> None:
        """Тест проверяет, что подкласс IterableTask должен реализовать execute_for_item."""
        # Создаем неполную реализацию без execute_for_item
        class IncompleteIterableTask(IterableTask):
            @property
            def name(self) -> str:
                return "test_task"

            @property
            def depends_on(self) -> list[str]:
                return []

            def execute(self, context: ExecutionContext) -> TaskResult:
                return TaskResult.success_result()

            def get_items(self, context: ExecutionContext) -> Any:
                return iter([])

        with pytest.raises(TypeError):
            IncompleteIterableTask()  # type: ignore[abstract]

    def test_complete_iterable_task_implementation(self) -> None:
        """Тест полной реализации IterableTask."""
        mock_tracker = Mock(spec=ProgressTracker)
        context = ExecutionContext(
            task_order=["test_task"],
            results={},
            metadata={},
            progress_tracker=mock_tracker,
        )

        class CompleteIterableTask(IterableTask):
            @property
            def name(self) -> str:
                return "iterable_task"

            @property
            def depends_on(self) -> list[str]:
                return []

            def execute(self, context: ExecutionContext) -> TaskResult:
                return TaskResult.success_result()

            def get_items(self, context: ExecutionContext) -> Any:
                return iter([1, 2, 3])

            def execute_for_item(
                self, item: Any, context: ExecutionContext
            ) -> None:
                pass

        task = CompleteIterableTask()
        assert task.name == "iterable_task"
        items = list(task.get_items(context))
        assert items == [1, 2, 3]


class TestProgressTrackerABC:
    """Тесты для абстрактного класса ProgressTracker."""

    def test_cannot_instantiate_progress_tracker_abc(self) -> None:
        """Тест проверяет, что нельзя создать экземпляр ProgressTracker ABC."""
        with pytest.raises(TypeError):
            ProgressTracker()  # type: ignore[abstract]

    def test_progress_tracker_requires_all_methods(self) -> None:
        """Тест проверяет, что подкласс ProgressTracker должен реализовать все методы."""
        # Создаем неполную реализацию
        class IncompleteProgressTracker(ProgressTracker):
            def save_progress(self, task_name: str, progress: Any) -> None:
                pass

            def get_progress(self, task_name: str) -> Any:
                return None

        with pytest.raises(TypeError):
            IncompleteProgressTracker()  # type: ignore[abstract]

