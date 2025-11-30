"""Типы и протоколы для task-sequencer."""

from __future__ import annotations

from typing import Any, Protocol

from task_sequencer.progress import TaskProgress


class ProgressTrackerProtocol(Protocol):
    """Протокол для трекеров прогресса.

    Определяет интерфейс для всех реализаций ProgressTracker,
    позволяя использовать структурную типизацию без циклических зависимостей.
    """

    def save_progress(self, task_name: str, progress: TaskProgress) -> None:
        """Сохраняет прогресс выполнения задачи.

        Args:
            task_name: Имя задачи
            progress: Информация о прогрессе

        Raises:
            ProgressError: Если не удалось сохранить прогресс
        """
        ...

    def get_progress(self, task_name: str) -> TaskProgress | None:
        """Получает сохраненный прогресс выполнения задачи.

        Args:
            task_name: Имя задачи

        Returns:
            TaskProgress или None, если прогресс не найден

        Raises:
            ProgressError: Если произошла ошибка при загрузке прогресса
        """
        ...

    def mark_completed(self, task_name: str) -> None:
        """Отмечает задачу как завершенную.

        Args:
            task_name: Имя задачи

        Raises:
            ProgressError: Если не удалось обновить статус
        """
        ...

    def clear_progress(self, task_name: str) -> None:
        """Очищает сохраненный прогресс задачи.

        Args:
            task_name: Имя задачи

        Raises:
            ProgressError: Если не удалось очистить прогресс
        """
        ...


