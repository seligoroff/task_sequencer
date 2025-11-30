"""Тесты для TaskOrchestrator."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import Mock

import pytest

from task_sequencer.adapters.memory import MemoryProgressTracker
from task_sequencer.core import ExecutionResult, TaskOrchestrator, TaskRegistry
from task_sequencer.exceptions import DependencyError, TaskExecutionError
from task_sequencer.interfaces import (
    ExecutionContext,
    IterableTask,
    Task,
    TaskResult,
)
from task_sequencer.progress import TaskProgress, TaskStatus
from task_sequencer.validators import DependencyValidator


class SimpleTask(Task):
    """Простая задача для тестирования."""

    def __init__(self, name: str, depends_on: list[str] | None = None) -> None:
        self._name = name
        self._depends_on = depends_on or []

    @property
    def name(self) -> str:
        return self._name

    @property
    def depends_on(self) -> list[str]:
        return self._depends_on

    def execute(self, context: ExecutionContext) -> TaskResult:
        return TaskResult.success_result(data=f"Task {self._name} completed")


class FailingTask(Task):
    """Задача, которая всегда проваливается."""

    def __init__(self, name: str, error_message: str = "Task failed") -> None:
        self._name = name
        self._error_message = error_message

    @property
    def name(self) -> str:
        return self._name

    @property
    def depends_on(self) -> list[str]:
        return []

    def execute(self, context: ExecutionContext) -> TaskResult:
        return TaskResult.failure_result(error=self._error_message)


class ExceptionTask(Task):
    """Задача, которая выбрасывает исключение."""

    def __init__(self, name: str, exception_message: str = "Exception occurred") -> None:
        self._name = name
        self._exception_message = exception_message

    @property
    def name(self) -> str:
        return self._name

    @property
    def depends_on(self) -> list[str]:
        return []

    def execute(self, context: ExecutionContext) -> TaskResult:
        raise ValueError(self._exception_message)


class SimpleIterableTask(IterableTask):
    """Простая итеративная задача для тестирования."""

    def __init__(
        self,
        name: str,
        items: list[dict[str, str]],
        depends_on: list[str] | None = None,
    ) -> None:
        self._name = name
        self._items = items
        self._depends_on = depends_on or []
        self._processed_items: list[dict[str, str]] = []

    @property
    def name(self) -> str:
        return self._name

    @property
    def depends_on(self) -> list[str]:
        return self._depends_on

    def execute(self, context: ExecutionContext) -> TaskResult:
        # Для IterableTask execute должен обрабатывать элементы
        from task_sequencer.iterators import ResumeIterator

        items = list(self.get_items(context))
        
        # Используем ResumeIterator если resume=True
        if context.metadata.get("resume", False):
            id_extractor = context.metadata.get("id_extractor")
            if id_extractor is None:
                # Используем функцию по умолчанию
                def default_id_extractor(item: dict[str, str]) -> str:
                    return item["id"]
                id_extractor = default_id_extractor
            
            if context.progress_tracker:
                items_iterator = ResumeIterator(
                    items=items,
                    progress_tracker=context.progress_tracker,
                    task_name=self._name,
                    id_extractor=id_extractor,
                )
            else:
                items_iterator = iter(items)
        else:
            items_iterator = iter(items)
        
        for item in items_iterator:
            self.execute_for_item(item, context)
        
        return TaskResult.success_result(
            data={"processed_items": len(self._processed_items)}
        )

    def get_items(self, context: ExecutionContext) -> list[dict[str, str]]:
        return self._items

    def execute_for_item(self, item: dict[str, str], context: ExecutionContext) -> None:
        self._processed_items.append(item)


class TestTaskOrchestrator:
    """Тесты для TaskOrchestrator."""

    def test_execute_simple_task(self) -> None:
        """Тест выполнения простой задачи."""
        task = SimpleTask("task1")
        registry = TaskRegistry([task])
        tracker = MemoryProgressTracker()
        validator = DependencyValidator()
        orchestrator = TaskOrchestrator(registry, tracker, validator)

        result = orchestrator.execute(["task1"])

        assert result.status == TaskStatus.COMPLETED
        assert len(result.completed_tasks) == 1
        assert "task1" in result.completed_tasks
        assert len(result.failed_tasks) == 0
        assert "task1" in result.results
        assert result.results["task1"].success is True

    def test_execute_multiple_tasks_in_order(self) -> None:
        """Тест выполнения нескольких задач в указанном порядке."""
        task1 = SimpleTask("task1")
        task2 = SimpleTask("task2")
        task3 = SimpleTask("task3")
        registry = TaskRegistry([task1, task2, task3])
        tracker = MemoryProgressTracker()
        validator = DependencyValidator()
        orchestrator = TaskOrchestrator(registry, tracker, validator)

        result = orchestrator.execute(["task1", "task2", "task3"])

        assert result.status == TaskStatus.COMPLETED
        assert len(result.completed_tasks) == 3
        assert result.completed_tasks == ["task1", "task2", "task3"]
        assert len(result.failed_tasks) == 0

    def test_execute_tasks_with_dependencies(self) -> None:
        """Тест выполнения задач с зависимостями."""
        task1 = SimpleTask("task1")
        task2 = SimpleTask("task2", depends_on=["task1"])
        task3 = SimpleTask("task3", depends_on=["task2"])
        registry = TaskRegistry([task1, task2, task3])
        tracker = MemoryProgressTracker()
        validator = DependencyValidator()
        orchestrator = TaskOrchestrator(registry, tracker, validator)

        result = orchestrator.execute(["task1", "task2", "task3"])

        assert result.status == TaskStatus.COMPLETED
        assert len(result.completed_tasks) == 3
        assert result.completed_tasks == ["task1", "task2", "task3"]

    def test_execute_stops_on_failure(self) -> None:
        """Тест прерывания выполнения при ошибке."""
        task1 = SimpleTask("task1")
        task2 = FailingTask("task2")
        task3 = SimpleTask("task3")
        registry = TaskRegistry([task1, task2, task3])
        tracker = MemoryProgressTracker()
        validator = DependencyValidator()
        orchestrator = TaskOrchestrator(registry, tracker, validator)

        result = orchestrator.execute(["task1", "task2", "task3"])

        assert result.status == TaskStatus.FAILED
        assert len(result.completed_tasks) == 1
        assert "task1" in result.completed_tasks
        assert len(result.failed_tasks) == 1
        assert "task2" in result.failed_tasks
        assert "task3" not in result.completed_tasks
        assert "task3" not in result.results

    def test_execute_handles_exception(self) -> None:
        """Тест обработки исключения при выполнении задачи."""
        task1 = SimpleTask("task1")
        task2 = ExceptionTask("task2", "Test exception")
        registry = TaskRegistry([task1, task2])
        tracker = MemoryProgressTracker()
        validator = DependencyValidator()
        orchestrator = TaskOrchestrator(registry, tracker, validator)

        result = orchestrator.execute(["task1", "task2"])

        assert result.status == TaskStatus.FAILED
        assert len(result.completed_tasks) == 1
        assert "task1" in result.completed_tasks
        assert len(result.failed_tasks) == 1
        assert "task2" in result.failed_tasks
        assert "task2" in result.results
        assert result.results["task2"].success is False
        assert "Test exception" in (result.results["task2"].error or "")

    def test_execute_validates_dependencies(self) -> None:
        """Тест валидации зависимостей перед выполнением."""
        task1 = SimpleTask("task1")
        task2 = SimpleTask("task2", depends_on=["task1"])
        # task2 зависит от task1, но task1 не в task_order
        registry = TaskRegistry([task1, task2])
        tracker = MemoryProgressTracker()
        validator = DependencyValidator()
        orchestrator = TaskOrchestrator(registry, tracker, validator)

        with pytest.raises(DependencyError, match="depends on tasks not in task_order"):
            orchestrator.execute(["task2"])

    def test_execute_validates_dependency_order(self) -> None:
        """Тест валидации порядка зависимостей."""
        task1 = SimpleTask("task1", depends_on=["task2"])
        task2 = SimpleTask("task2")
        # task1 зависит от task2, но task2 идет после task1 в task_order
        registry = TaskRegistry([task1, task2])
        tracker = MemoryProgressTracker()
        validator = DependencyValidator()
        orchestrator = TaskOrchestrator(registry, tracker, validator)

        with pytest.raises(DependencyError, match="depends on tasks that come after"):
            orchestrator.execute(["task1", "task2"])

    def test_execute_checks_dependencies_before_each_task(self) -> None:
        """Тест проверки зависимостей перед каждой задачей."""
        task1 = SimpleTask("task1")
        task2 = SimpleTask("task2", depends_on=["task1"])
        task3 = SimpleTask("task3", depends_on=["task2"])
        registry = TaskRegistry([task1, task2, task3])
        tracker = MemoryProgressTracker()
        validator = DependencyValidator()
        orchestrator = TaskOrchestrator(registry, tracker, validator)

        # Если task1 не выполнится, task2 не должна запуститься
        # Но это проверяется валидатором перед выполнением
        result = orchestrator.execute(["task1", "task2", "task3"])

        assert result.status == TaskStatus.COMPLETED
        assert len(result.completed_tasks) == 3

    def test_execute_saves_progress(self) -> None:
        """Тест сохранения прогресса при выполнении."""
        task = SimpleTask("task1")
        registry = TaskRegistry([task])
        tracker = MemoryProgressTracker()
        validator = DependencyValidator()
        orchestrator = TaskOrchestrator(registry, tracker, validator)

        orchestrator.execute(["task1"])

        # Проверяем, что прогресс был сохранен
        progress = tracker.get_progress("task1")
        assert progress is not None
        assert progress.status == TaskStatus.COMPLETED
        assert progress.started_at is not None
        assert progress.completed_at is not None

    def test_execute_iterable_task(self) -> None:
        """Тест выполнения итеративной задачи."""
        items = [{"id": "1"}, {"id": "2"}, {"id": "3"}]
        task = SimpleIterableTask("iterable_task", items)
        registry = TaskRegistry([task])
        tracker = MemoryProgressTracker()
        validator = DependencyValidator()
        orchestrator = TaskOrchestrator(registry, tracker, validator)

        result = orchestrator.execute(["iterable_task"])

        assert result.status == TaskStatus.COMPLETED
        assert "iterable_task" in result.completed_tasks
        assert result.results["iterable_task"].success is True
        assert len(task._processed_items) == 3

    def test_execute_iterable_task_with_resume(self) -> None:
        """Тест выполнения итеративной задачи с восстановлением."""
        items = [{"id": "1"}, {"id": "2"}, {"id": "3"}]
        
        # Сохраняем прогресс: обработали элемент "1"
        tracker = MemoryProgressTracker()
        progress = TaskProgress(
            task_name="iterable_task",
            status=TaskStatus.IN_PROGRESS,
            last_processed_id="1",
            processed_items=1,
        )
        tracker.save_progress("iterable_task", progress)

        # Создаем новый экземпляр задачи для второго запуска
        task2 = SimpleIterableTask("iterable_task", items)
        registry2 = TaskRegistry([task2])
        validator = DependencyValidator()
        orchestrator2 = TaskOrchestrator(registry2, tracker, validator)

        result = orchestrator2.execute(["iterable_task"], resume=True)

        assert result.status == TaskStatus.COMPLETED
        # Должны обработать только элементы "2" и "3"
        assert len(task2._processed_items) == 2
        assert task2._processed_items == [{"id": "2"}, {"id": "3"}]

    def test_execute_result_contains_metadata(self) -> None:
        """Тест, что ExecutionResult содержит метаданные."""
        task = SimpleTask("task1")
        registry = TaskRegistry([task])
        tracker = MemoryProgressTracker()
        validator = DependencyValidator()
        orchestrator = TaskOrchestrator(registry, tracker, validator)

        result = orchestrator.execute(["task1"], mode="dry-run", resume=True)

        assert result.metadata["mode"] == "dry-run"
        assert result.metadata["resume"] is True

    def test_execute_empty_task_order(self) -> None:
        """Тест выполнения с пустым списком задач."""
        registry = TaskRegistry()
        tracker = MemoryProgressTracker()
        validator = DependencyValidator()
        orchestrator = TaskOrchestrator(registry, tracker, validator)

        result = orchestrator.execute([])

        assert result.status == TaskStatus.COMPLETED
        assert len(result.completed_tasks) == 0
        assert len(result.failed_tasks) == 0

    def test_execute_mark_task_started(self) -> None:
        """Тест отметки задачи как начатой."""
        task = SimpleTask("task1")
        registry = TaskRegistry([task])
        tracker = MemoryProgressTracker()
        validator = DependencyValidator()
        orchestrator = TaskOrchestrator(registry, tracker, validator)

        orchestrator.execute(["task1"])

        # Проверяем, что задача была отмечена как начатая
        progress = tracker.get_progress("task1")
        assert progress is not None
        assert progress.started_at is not None

    def test_execute_mark_task_failed(self) -> None:
        """Тест отметки задачи как провалившейся."""
        task = FailingTask("task1", "Test error")
        registry = TaskRegistry([task])
        tracker = MemoryProgressTracker()
        validator = DependencyValidator()
        orchestrator = TaskOrchestrator(registry, tracker, validator)

        orchestrator.execute(["task1"])

        # Проверяем, что задача была отмечена как провалившаяся
        progress = tracker.get_progress("task1")
        assert progress is not None
        assert progress.status == TaskStatus.FAILED
        assert progress.error_message == "Test error"
        assert progress.completed_at is not None

    def test_execute_context_contains_results(self) -> None:
        """Тест, что ExecutionContext содержит результаты выполненных задач."""
        task1 = SimpleTask("task1")
        task2 = SimpleTask("task2")
        registry = TaskRegistry([task1, task2])
        tracker = MemoryProgressTracker()
        validator = DependencyValidator()
        orchestrator = TaskOrchestrator(registry, tracker, validator)

        # Мокаем задачу, чтобы проверить context
        executed_tasks: list[str] = []
        context_results: dict[str, TaskResult] = {}

        class ContextAwareTask(Task):
            @property
            def name(self) -> str:
                return "context_task"

            @property
            def depends_on(self) -> list[str]:
                return []

            def execute(self, context: ExecutionContext) -> TaskResult:
                executed_tasks.append(self.name)
                context_results.update(context.results)
                return TaskResult.success_result()

        context_task = ContextAwareTask()
        registry.register(context_task)
        orchestrator.execute(["task1", "task2", "context_task"])

        assert "task1" in context_results
        assert "task2" in context_results
        assert context_results["task1"].success is True
        assert context_results["task2"].success is True

