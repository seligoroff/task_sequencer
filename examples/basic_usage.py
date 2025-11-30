"""
Базовый пример использования task-sequencer.

Демонстрирует простейший сценарий: выполнение одной задачи без зависимостей.
"""

from __future__ import annotations

from task_sequencer import (
    DependencyValidator,
    ExecutionContext,
    Task,
    TaskOrchestrator,
    TaskRegistry,
    TaskResult,
)
from task_sequencer.adapters.memory import MemoryProgressTracker


class HelloWorldTask(Task):
    """Простая задача, которая выводит приветствие."""

    @property
    def name(self) -> str:
        return "hello_world"

    @property
    def depends_on(self) -> list[str]:
        return []

    def execute(self, context: ExecutionContext) -> TaskResult:
        """Выполняет задачу - выводит приветствие."""
        message = "Hello, World! Task executed successfully."
        print(message)
        return TaskResult.success_result(data={"message": message})


def main() -> None:
    """Основная функция для запуска примера."""
    print("=== Базовый пример использования task-sequencer ===\n")

    # Создаем задачу
    task = HelloWorldTask()

    # Создаем реестр задач
    registry = TaskRegistry([task])

    # Создаем трекер прогресса (в памяти)
    tracker = MemoryProgressTracker()

    # Создаем валидатор зависимостей
    validator = DependencyValidator()

    # Создаем оркестратор
    orchestrator = TaskOrchestrator(
        task_registry=registry,
        progress_tracker=tracker,
        dependency_validator=validator,
    )

    # Выполняем задачу
    print("Выполнение задачи 'hello_world'...")
    result = orchestrator.execute(["hello_world"])

    # Выводим результаты
    print(f"\nСтатус выполнения: {result.status.value}")
    print(f"Выполнено задач: {len(result.completed_tasks)}")
    print(f"Провалено задач: {len(result.failed_tasks)}")

    if result.completed_tasks:
        print(f"\nРезультат задачи '{result.completed_tasks[0]}':")
        task_result = result.results[result.completed_tasks[0]]
        print(f"  Успешно: {task_result.success}")
        print(f"  Данные: {task_result.data}")

    # Проверяем прогресс
    progress = tracker.get_progress("hello_world")
    if progress:
        print("\nПрогресс задачи:")
        print(f"  Статус: {progress.status.value}")
        print(f"  Начато: {progress.started_at}")
        print(f"  Завершено: {progress.completed_at}")


if __name__ == "__main__":
    main()

