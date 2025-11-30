"""
Пример создания кастомного ProgressTracker.

Демонстрирует реализацию собственного трекера прогресса,
хранящего данные в файле JSON.
"""

from __future__ import annotations

import json
from contextlib import contextmanager
from pathlib import Path
from typing import ContextManager

from task_sequencer import (
    DependencyValidator,
    ExecutionContext,
    Task,
    TaskOrchestrator,
    TaskRegistry,
    TaskResult,
)
from task_sequencer.interfaces import ProgressTracker
from task_sequencer.progress import TaskProgress, TaskStatus


class JsonFileProgressTracker(ProgressTracker):
    """Кастомный трекер прогресса, хранящий данные в JSON файле.

    Все трекеры должны реализовать следующие методы:
    - save_progress(task_name: str, progress: TaskProgress) -> None
    - get_progress(task_name: str) -> TaskProgress | None
    - mark_completed(task_name: str) -> None
    - clear_progress(task_name: str) -> None
    - transaction() -> ContextManager[None]
    """

    def __init__(self, file_path: str = "task_progress.json") -> None:
        """Инициализирует трекер прогресса.

        Args:
            file_path: Путь к JSON файлу для хранения прогресса
        """
        self.file_path = Path(file_path)
        self._storage: dict[str, dict] = {}
        self._load()

    def _load(self) -> None:
        """Загружает прогресс из файла."""
        if self.file_path.exists():
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    self._storage = json.load(f)
            except (json.JSONDecodeError, IOError):
                self._storage = {}

    def _save(self) -> None:
        """Сохраняет прогресс в файл."""
        try:
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(self._storage, f, indent=2, default=str)
        except IOError as e:
            raise RuntimeError(f"Failed to save progress: {e}") from e

    def save_progress(self, task_name: str, progress: TaskProgress) -> None:
        """Сохраняет прогресс выполнения задачи.

        Args:
            task_name: Имя задачи
            progress: Информация о прогрессе

        Raises:
            RuntimeError: Если не удалось сохранить прогресс
        """
        self._storage[task_name] = {
            "task_name": progress.task_name,
            "status": progress.status.value,
            "total_items": progress.total_items,
            "processed_items": progress.processed_items,
            "last_processed_id": progress.last_processed_id,
            "started_at": progress.started_at.isoformat() if progress.started_at else None,
            "completed_at": progress.completed_at.isoformat() if progress.completed_at else None,
            "error_message": progress.error_message,
            "metadata": progress.metadata,
        }
        self._save()

    def get_progress(self, task_name: str) -> TaskProgress | None:
        """Получает сохраненный прогресс выполнения задачи.

        Args:
            task_name: Имя задачи

        Returns:
            TaskProgress или None, если прогресс не найден
        """
        if task_name not in self._storage:
            return None

        data = self._storage[task_name]
        from datetime import datetime

        return TaskProgress(
            task_name=data["task_name"],
            status=TaskStatus(data["status"]),
            total_items=data.get("total_items"),
            processed_items=data.get("processed_items", 0),
            last_processed_id=data.get("last_processed_id"),
            started_at=datetime.fromisoformat(data["started_at"]) if data.get("started_at") else None,
            completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None,
            error_message=data.get("error_message"),
            metadata=data.get("metadata", {}),
        )

    def mark_completed(self, task_name: str) -> None:
        """Отмечает задачу как завершенную.

        Args:
            task_name: Имя задачи
        """
        if task_name in self._storage:
            self._storage[task_name]["status"] = TaskStatus.COMPLETED.value
            from datetime import datetime

            self._storage[task_name]["completed_at"] = datetime.now().isoformat()
            self._save()

    def clear_progress(self, task_name: str) -> None:
        """Очищает сохраненный прогресс задачи.

        Args:
            task_name: Имя задачи
        """
        if task_name in self._storage:
            del self._storage[task_name]
            self._save()

    @contextmanager
    def transaction(self) -> ContextManager[None]:
        """Возвращает контекстный менеджер для транзакции.

        Для файлового трекера транзакция просто гарантирует,
        что изменения сохраняются атомарно.

        Yields:
            None
        """
        # Для файлового трекера транзакция - это просто сохранение
        # В реальной реализации можно использовать временный файл
        try:
            yield
        finally:
            self._save()


class ExampleTask(Task):
    """Пример задачи для демонстрации."""

    @property
    def name(self) -> str:
        return "example_task"

    @property
    def depends_on(self) -> list[str]:
        return []

    def execute(self, context: ExecutionContext) -> TaskResult:
        print("Executing example task...")
        return TaskResult.success_result(data={"message": "Task completed"})


def main() -> None:
    """Основная функция для запуска примера."""
    print("=== Пример кастомного ProgressTracker ===\n")

    # Создаем кастомный трекер
    tracker = JsonFileProgressTracker("example_progress.json")

    # Создаем компоненты
    registry = TaskRegistry([ExampleTask()])
    validator = DependencyValidator()
    orchestrator = TaskOrchestrator(registry, tracker, validator)

    # Выполняем задачу
    print("Выполнение задачи...")
    result = orchestrator.execute(["example_task"])

    print(f"\nСтатус: {result.status.value}")
    print(f"Выполнено задач: {len(result.completed_tasks)}")

    # Проверяем сохраненный прогресс
    progress = tracker.get_progress("example_task")
    if progress:
        print(f"\nСохраненный прогресс:")
        print(f"  Статус: {progress.status.value}")
        print(f"  Начато: {progress.started_at}")
        print(f"  Завершено: {progress.completed_at}")

    # Очищаем прогресс
    tracker.clear_progress("example_task")
    print("\nПрогресс очищен")

    # Проверяем, что файл создан
    if Path("example_progress.json").exists():
        print("Файл прогресса создан: example_progress.json")


if __name__ == "__main__":
    main()

