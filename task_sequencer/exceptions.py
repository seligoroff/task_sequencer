"""Исключения для task-sequencer."""

from __future__ import annotations


class TaskOrchestratorError(Exception):
    """Базовое исключение для всех ошибок task-sequencer.

    Все исключения компонента наследуются от этого класса.
    """

    def __init__(self, message: str) -> None:
        """Инициализирует исключение.

        Args:
            message: Сообщение об ошибке
        """
        super().__init__(message)
        self.message = message


class DependencyError(TaskOrchestratorError):
    """Исключение, возникающее при нарушении зависимостей между задачами.

    Выбрасывается когда:
    - Задача не найдена в реестре
    - Зависимость задачи отсутствует в task_order
    - Обнаружены циклические зависимости
    - Порядок задач не соответствует зависимостям
    """

    def __init__(self, message: str) -> None:
        """Инициализирует исключение.

        Args:
            message: Описание проблемы с зависимостями
        """
        super().__init__(message)


class TaskExecutionError(TaskOrchestratorError):
    """Исключение, возникающее при ошибке выполнения задачи.

    Выбрасывается когда задача не может быть выполнена из-за ошибки
    в логике выполнения или внешних факторов.
    """

    def __init__(self, message: str, task_name: str | None = None) -> None:
        """Инициализирует исключение.

        Args:
            message: Описание ошибки выполнения
            task_name: Имя задачи, при выполнении которой произошла ошибка
        """
        super().__init__(message)
        self.task_name = task_name


class ProgressError(TaskOrchestratorError):
    """Исключение, возникающее при ошибке работы с прогрессом.

    Выбрасывается когда:
    - Не удалось сохранить прогресс
    - Не удалось загрузить прогресс
    - Ошибка при работе с хранилищем прогресса
    """

    def __init__(self, message: str) -> None:
        """Инициализирует исключение.

        Args:
            message: Описание проблемы с прогрессом
        """
        super().__init__(message)


