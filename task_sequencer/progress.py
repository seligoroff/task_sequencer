"""Модели данных для отслеживания прогресса выполнения задач."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class TaskStatus(Enum):
    """Статус выполнения задачи.

    Attributes:
        PENDING: Задача ожидает выполнения
        IN_PROGRESS: Задача выполняется в данный момент
        COMPLETED: Задача завершена успешно
        FAILED: Задача завершена с ошибкой
        CANCELLED: Задача отменена
    """

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class TaskProgress:
    """Информация о прогрессе выполнения задачи.

    Attributes:
        task_name: Уникальное имя задачи
        status: Текущий статус выполнения задачи
        total_items: Общее количество элементов для обработки (для IterableTask)
        processed_items: Количество обработанных элементов
        last_processed_id: Идентификатор последнего обработанного элемента
        started_at: Время начала выполнения задачи
        completed_at: Время завершения выполнения задачи
        error_message: Сообщение об ошибке (если задача завершилась с ошибкой)
        metadata: Дополнительные метаданные о прогрессе
    """

    task_name: str
    status: TaskStatus = TaskStatus.PENDING
    total_items: int | None = None
    processed_items: int = 0
    last_processed_id: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_message: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Валидация данных после инициализации."""
        if self.processed_items < 0:
            raise ValueError("processed_items cannot be negative")
        if self.total_items is not None and self.total_items < 0:
            raise ValueError("total_items cannot be negative")
        if self.total_items is not None and self.processed_items > self.total_items:
            raise ValueError("processed_items cannot be greater than total_items")

