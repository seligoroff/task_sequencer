"""Memory адаптер для трекера прогресса."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime
from typing import ContextManager

from task_sequencer.exceptions import ProgressError
from task_sequencer.interfaces import ProgressTracker
from task_sequencer.progress import TaskProgress, TaskStatus


class MemoryProgressTracker(ProgressTracker):
    """Трекер прогресса, хранящий данные в памяти.

    Используется для тестирования и простых сценариев,
    когда не требуется персистентность данных между запусками.

    Attributes:
        _storage: Словарь для хранения прогресса (имя задачи -> TaskProgress)
    """

    def __init__(self) -> None:
        """Инициализирует трекер прогресса."""
        self._storage: dict[str, TaskProgress] = {}

    def save_progress(
        self, task_name: str, progress: TaskProgress
    ) -> None:
        """Сохраняет прогресс выполнения задачи.

        Args:
            task_name: Имя задачи
            progress: Информация о прогрессе

        Raises:
            ProgressError: Если не удалось сохранить прогресс
        """
        if not task_name:
            raise ProgressError("Task name cannot be empty")

        if progress.task_name != task_name:
            raise ProgressError(
                f"Task name mismatch: expected '{task_name}', "
                f"got '{progress.task_name}'"
            )

        try:
            self._storage[task_name] = progress
        except Exception as e:
            raise ProgressError(f"Failed to save progress: {e}") from e

    def get_progress(self, task_name: str) -> TaskProgress | None:
        """Получает сохраненный прогресс выполнения задачи.

        Args:
            task_name: Имя задачи

        Returns:
            TaskProgress или None, если прогресс не найден

        Raises:
            ProgressError: Если произошла ошибка при загрузке прогресса
        """
        if not task_name:
            raise ProgressError("Task name cannot be empty")

        try:
            return self._storage.get(task_name)
        except Exception as e:
            raise ProgressError(f"Failed to get progress: {e}") from e

    def mark_completed(self, task_name: str) -> None:
        """Отмечает задачу как завершенную.

        Args:
            task_name: Имя задачи

        Raises:
            ProgressError: Если не удалось обновить статус
        """
        if not task_name:
            raise ProgressError("Task name cannot be empty")

        try:
            progress = self._storage.get(task_name)
            now = datetime.now()
            if progress is None:
                # Создаем новый прогресс, если его нет
                progress = TaskProgress(
                    task_name=task_name,
                    status=TaskStatus.COMPLETED,
                    started_at=now,
                    completed_at=now,
                )
                self._storage[task_name] = progress
            else:
                # Обновляем существующий прогресс
                progress.status = TaskStatus.COMPLETED
                progress.completed_at = now
                if progress.started_at is None:
                    progress.started_at = now

        except Exception as e:
            raise ProgressError(f"Failed to mark task as completed: {e}") from e

    def clear_progress(self, task_name: str) -> None:
        """Очищает сохраненный прогресс задачи.

        Args:
            task_name: Имя задачи

        Raises:
            ProgressError: Если не удалось очистить прогресс
        """
        if not task_name:
            raise ProgressError("Task name cannot be empty")

        try:
            if task_name in self._storage:
                del self._storage[task_name]
        except Exception as e:
            raise ProgressError(f"Failed to clear progress: {e}") from e

    @contextmanager
    def transaction(self) -> ContextManager[None]:
        """Заглушка для MemoryProgressTracker (не требует транзакций).

        Returns:
            Контекстный менеджер (заглушка)
        """
        yield

