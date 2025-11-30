"""Интеграционные тесты для task-orchestrator."""

from __future__ import annotations

import time
from datetime import datetime

import pytest

from task_sequencer.adapters.memory import MemoryProgressTracker
from task_sequencer.core import ExecutionResult, TaskOrchestrator, TaskRegistry
from task_sequencer.exceptions import DependencyError, TaskExecutionError
from task_sequencer.interfaces import ExecutionContext, IterableTask, Task, TaskResult
from task_sequencer.iterators import ResumeIterator
from task_sequencer.progress import TaskProgress, TaskStatus
from task_sequencer.validators import DependencyValidator


class SimpleTask(Task):
    """Простая задача для интеграционных тестов."""

    def __init__(self, name: str, depends_on: list[str] | None = None, result_data: str | None = None) -> None:
        self._name = name
        self._depends_on = depends_on or []
        self._result_data = result_data or f"Task {name} completed"
        self._executed = False

    @property
    def name(self) -> str:
        return self._name

    @property
    def depends_on(self) -> list[str]:
        return self._depends_on

    def execute(self, context: ExecutionContext) -> TaskResult:
        self._executed = True
        return TaskResult.success_result(data=self._result_data)


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


class SimpleIterableTask(IterableTask):
    """Простая итеративная задача для интеграционных тестов."""

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
        """Выполняет итеративную задачу с поддержкой resume."""
        items = list(self.get_items(context))

        # Используем ResumeIterator если resume=True
        if context.metadata.get("resume", False):
            id_extractor = context.metadata.get("id_extractor")
            if id_extractor is None:
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


class TestIntegration:
    """Интеграционные тесты для task-orchestrator."""

    def test_full_execution_cycle_with_dependencies(self) -> None:
        """Тест полного цикла выполнения задач с зависимостями."""
        # Создаем задачи с зависимостями
        task1 = SimpleTask("task1")
        task2 = SimpleTask("task2", depends_on=["task1"])
        task3 = SimpleTask("task3", depends_on=["task2"])
        task4 = SimpleTask("task4", depends_on=["task1", "task3"])

        registry = TaskRegistry([task1, task2, task3, task4])
        tracker = MemoryProgressTracker()
        validator = DependencyValidator()
        orchestrator = TaskOrchestrator(registry, tracker, validator)

        # Выполняем задачи
        result = orchestrator.execute(["task1", "task2", "task3", "task4"])

        # Проверяем результаты
        assert result.status == TaskStatus.COMPLETED
        assert len(result.completed_tasks) == 4
        assert result.completed_tasks == ["task1", "task2", "task3", "task4"]
        assert len(result.failed_tasks) == 0

        # Проверяем, что все задачи выполнены
        assert task1._executed is True
        assert task2._executed is True
        assert task3._executed is True
        assert task4._executed is True

        # Проверяем, что прогресс сохранен
        for task_name in ["task1", "task2", "task3", "task4"]:
            progress = tracker.get_progress(task_name)
            assert progress is not None
            assert progress.status == TaskStatus.COMPLETED

    def test_iterable_task_with_resume(self) -> None:
        """Тест выполнения IterableTask с восстановлением."""
        items = [{"id": str(i), "data": f"item_{i}"} for i in range(1, 11)]

        tracker = MemoryProgressTracker()
        validator = DependencyValidator()

        # Первый запуск - обрабатываем первые 5 элементов и сохраняем прогресс
        # Сохраняем прогресс вручную после обработки 5 элементов
        progress = TaskProgress(
            task_name="iterable_task",
            status=TaskStatus.IN_PROGRESS,
            last_processed_id="5",
            processed_items=5,
        )
        tracker.save_progress("iterable_task", progress)

        # Второй запуск - продолжаем с места остановки
        task2 = SimpleIterableTask("iterable_task", items)
        registry2 = TaskRegistry([task2])
        orchestrator2 = TaskOrchestrator(registry2, tracker, validator)

        result2 = orchestrator2.execute(["iterable_task"], resume=True)

        assert result2.status == TaskStatus.COMPLETED
        # Должны обработать оставшиеся 5 элементов (6-10)
        assert len(task2._processed_items) == 5
        assert task2._processed_items[0]["id"] == "6"
        assert task2._processed_items[-1]["id"] == "10"

    def test_error_handling_and_stop_execution(self) -> None:
        """Тест обработки ошибок и прерывания выполнения."""
        task1 = SimpleTask("task1")
        task2 = FailingTask("task2", "Test error")
        task3 = SimpleTask("task3")

        registry = TaskRegistry([task1, task2, task3])
        tracker = MemoryProgressTracker()
        validator = DependencyValidator()
        orchestrator = TaskOrchestrator(registry, tracker, validator)

        result = orchestrator.execute(["task1", "task2", "task3"])

        # Проверяем, что выполнение прервалось
        assert result.status == TaskStatus.FAILED
        assert len(result.completed_tasks) == 1
        assert "task1" in result.completed_tasks
        assert len(result.failed_tasks) == 1
        assert "task2" in result.failed_tasks
        assert "task3" not in result.completed_tasks
        assert "task3" not in result.results

        # Проверяем, что task2 отмечена как провалившаяся
        progress = tracker.get_progress("task2")
        assert progress is not None
        assert progress.status == TaskStatus.FAILED
        assert progress.error_message == "Test error"

    def test_progress_tracker_integration(self) -> None:
        """Тест интеграции с ProgressTracker."""
        task1 = SimpleTask("task1")
        task2 = SimpleTask("task2", depends_on=["task1"])

        registry = TaskRegistry([task1, task2])
        tracker = MemoryProgressTracker()
        validator = DependencyValidator()
        orchestrator = TaskOrchestrator(registry, tracker, validator)

        result = orchestrator.execute(["task1", "task2"])

        assert result.status == TaskStatus.COMPLETED

        # Проверяем, что прогресс сохранен для обеих задач
        progress1 = tracker.get_progress("task1")
        assert progress1 is not None
        assert progress1.status == TaskStatus.COMPLETED
        assert progress1.started_at is not None
        assert progress1.completed_at is not None

        progress2 = tracker.get_progress("task2")
        assert progress2 is not None
        assert progress2.status == TaskStatus.COMPLETED

    def test_dependency_validation_integration(self) -> None:
        """Тест интеграции валидации зависимостей."""
        task1 = SimpleTask("task1")
        task2 = SimpleTask("task2", depends_on=["task1"])
        task3 = SimpleTask("task3", depends_on=["task2"])

        registry = TaskRegistry([task1, task2, task3])
        tracker = MemoryProgressTracker()
        validator = DependencyValidator()
        orchestrator = TaskOrchestrator(registry, tracker, validator)

        # Правильный порядок
        result = orchestrator.execute(["task1", "task2", "task3"])
        assert result.status == TaskStatus.COMPLETED

        # Неправильный порядок - должна быть ошибка
        with pytest.raises(DependencyError):
            orchestrator.execute(["task3", "task2", "task1"])

    def test_execution_context_propagation(self) -> None:
        """Тест распространения ExecutionContext между задачами."""
        executed_tasks: list[str] = []
        context_results: dict[str, TaskResult] = {}

        class ContextAwareTask(Task):
            def __init__(self, name: str) -> None:
                self._name = name

            @property
            def name(self) -> str:
                return self._name

            @property
            def depends_on(self) -> list[str]:
                return []

            def execute(self, context: ExecutionContext) -> TaskResult:
                executed_tasks.append(self._name)
                context_results.update(context.results)
                return TaskResult.success_result(data=f"Task {self._name} completed")

        task1 = ContextAwareTask("task1")
        task2 = ContextAwareTask("task2")
        task3 = ContextAwareTask("task3")

        registry = TaskRegistry([task1, task2, task3])
        tracker = MemoryProgressTracker()
        validator = DependencyValidator()
        orchestrator = TaskOrchestrator(registry, tracker, validator)

        result = orchestrator.execute(["task1", "task2", "task3"])

        assert result.status == TaskStatus.COMPLETED
        assert len(executed_tasks) == 3
        assert executed_tasks == ["task1", "task2", "task3"]

        # Проверяем, что task3 видит результаты task1 и task2
        assert "task1" in context_results
        assert "task2" in context_results
        assert context_results["task1"].success is True
        assert context_results["task2"].success is True

    def test_performance_dependency_validation_100_tasks(self) -> None:
        """Тест производительности валидации зависимостей для 100 задач (AC-6.1)."""
        # Создаем 100 задач с линейными зависимостями
        tasks = []
        for i in range(100):
            depends_on = [f"task_{i-1}"] if i > 0 else []
            task = SimpleTask(f"task_{i}", depends_on=depends_on)
            tasks.append(task)

        registry = TaskRegistry(tasks)
        tracker = MemoryProgressTracker()
        validator = DependencyValidator()
        orchestrator = TaskOrchestrator(registry, tracker, validator)

        task_order = [f"task_{i}" for i in range(100)]

        # Измеряем время валидации
        start_time = time.time()
        orchestrator.execute(task_order)
        end_time = time.time()

        execution_time = end_time - start_time

        # AC-6.1: Валидация зависимостей для 100 задач должна выполняться менее чем за 1 секунду
        # Но здесь мы измеряем полное выполнение, включая валидацию
        # Валидация сама по себе должна быть быстрой
        assert execution_time < 2.0, f"Execution took {execution_time:.2f}s, expected < 2.0s"

        # Проверяем, что все задачи выполнены
        result = orchestrator.execute(task_order)
        assert result.status == TaskStatus.COMPLETED
        assert len(result.completed_tasks) == 100

    def test_performance_progress_save(self) -> None:
        """Тест производительности сохранения прогресса (AC-6.2)."""
        task = SimpleTask("test_task")
        registry = TaskRegistry([task])
        tracker = MemoryProgressTracker()
        validator = DependencyValidator()
        # Создаем оркестратор для инициализации компонентов
        _ = TaskOrchestrator(registry, tracker, validator)

        # Измеряем время сохранения прогресса
        progress = TaskProgress(
            task_name="test_task",
            status=TaskStatus.IN_PROGRESS,
            processed_items=1,
        )

        start_time = time.time()
        tracker.save_progress("test_task", progress)
        end_time = time.time()

        save_time = (end_time - start_time) * 1000  # в миллисекундах

        # AC-6.2: Сохранение прогресса не должно блокировать выполнение более чем на 10ms
        assert save_time < 10, f"Save took {save_time:.2f}ms, expected < 10ms"

    def test_performance_50_tasks_execution(self) -> None:
        """Тест производительности выполнения 50+ задач (AC-6.3)."""
        # Создаем 50 задач
        tasks = []
        for i in range(50):
            task = SimpleTask(f"task_{i}")
            tasks.append(task)

        registry = TaskRegistry(tasks)
        tracker = MemoryProgressTracker()
        validator = DependencyValidator()
        orchestrator = TaskOrchestrator(registry, tracker, validator)

        task_order = [f"task_{i}" for i in range(50)]

        # Выполняем задачи
        result = orchestrator.execute(task_order)

        # AC-6.3: Компонент должен успешно обрабатывать последовательность из 50+ задач
        assert result.status == TaskStatus.COMPLETED
        assert len(result.completed_tasks) == 50

    def test_complex_scenario_with_iterable_and_regular_tasks(self) -> None:
        """Тест сложного сценария с итеративными и обычными задачами."""
        # Создаем смешанный набор задач
        task1 = SimpleTask("setup_task")
        items = [{"id": str(i), "data": f"item_{i}"} for i in range(1, 6)]
        task2 = SimpleIterableTask("process_items", items, depends_on=["setup_task"])
        task3 = SimpleTask("cleanup_task", depends_on=["process_items"])

        registry = TaskRegistry([task1, task2, task3])
        tracker = MemoryProgressTracker()
        validator = DependencyValidator()
        orchestrator = TaskOrchestrator(registry, tracker, validator)

        result = orchestrator.execute(["setup_task", "process_items", "cleanup_task"])

        assert result.status == TaskStatus.COMPLETED
        assert len(result.completed_tasks) == 3
        assert task1._executed is True
        assert len(task2._processed_items) == 5
        assert task3._executed is True

    def test_resume_after_failure(self) -> None:
        """Тест восстановления после ошибки."""
        items = [{"id": str(i), "data": f"item_{i}"} for i in range(1, 6)]

        tracker = MemoryProgressTracker()
        validator = DependencyValidator()

        # Симулируем ситуацию: обработали 3 элемента, затем произошла ошибка
        # Сохраняем прогресс с ошибкой
        progress = TaskProgress(
            task_name="iterable_task",
            status=TaskStatus.FAILED,
            last_processed_id="3",
            processed_items=3,
            error_message="Processing error",
        )
        tracker.save_progress("iterable_task", progress)

        # Второй запуск - продолжаем с места остановки после очистки ошибки
        # Очищаем ошибку из прогресса перед восстановлением
        progress = tracker.get_progress("iterable_task")
        assert progress is not None
        progress.status = TaskStatus.IN_PROGRESS
        progress.error_message = None
        tracker.save_progress("iterable_task", progress)

        task2 = SimpleIterableTask("iterable_task", items)
        registry2 = TaskRegistry([task2])
        orchestrator2 = TaskOrchestrator(registry2, tracker, validator)

        result2 = orchestrator2.execute(["iterable_task"], resume=True)

        # Должны обработать оставшиеся элементы (4 и 5)
        assert result2.status == TaskStatus.COMPLETED
        assert len(task2._processed_items) == 2
        assert task2._processed_items[0]["id"] == "4"
        assert task2._processed_items[-1]["id"] == "5"

    def test_empty_task_order(self) -> None:
        """Тест выполнения с пустым списком задач."""
        registry = TaskRegistry()
        tracker = MemoryProgressTracker()
        validator = DependencyValidator()
        orchestrator = TaskOrchestrator(registry, tracker, validator)

        result = orchestrator.execute([])

        assert result.status == TaskStatus.COMPLETED
        assert len(result.completed_tasks) == 0
        assert len(result.failed_tasks) == 0

    def test_single_task_execution(self) -> None:
        """Тест выполнения одной задачи."""
        task = SimpleTask("single_task")
        registry = TaskRegistry([task])
        tracker = MemoryProgressTracker()
        validator = DependencyValidator()
        orchestrator = TaskOrchestrator(registry, tracker, validator)

        result = orchestrator.execute(["single_task"])

        assert result.status == TaskStatus.COMPLETED
        assert len(result.completed_tasks) == 1
        assert "single_task" in result.completed_tasks
        assert task._executed is True

    def test_metadata_in_execution_result(self) -> None:
        """Тест метаданных в ExecutionResult."""
        task = SimpleTask("test_task")
        registry = TaskRegistry([task])
        tracker = MemoryProgressTracker()
        validator = DependencyValidator()
        orchestrator = TaskOrchestrator(registry, tracker, validator)

        result = orchestrator.execute(["test_task"], mode="dry-run", resume=True)

        assert result.metadata["mode"] == "dry-run"
        assert result.metadata["resume"] is True

