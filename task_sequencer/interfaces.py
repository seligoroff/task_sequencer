"""Интерфейсы для задач и трекеров прогресса."""

from __future__ import annotations

from abc import ABC, abstractmethod
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, ContextManager, Generic, Iterator, Literal, TypeVar

from task_sequencer.progress import TaskProgress, TaskStatus
from task_sequencer.types import ProgressTrackerProtocol

# Тип для режима выполнения задач
TaskMode = Literal["run", "dry-run", "resume"]


@dataclass
class TaskResult:
    """Результат выполнения задачи.

    Attributes:
        status: Статус выполнения задачи
        data: Данные, возвращаемые задачей
        error: Сообщение об ошибке (если есть)
        metadata: Дополнительные метаданные о результате
    """

    status: TaskStatus
    data: Any | None = None
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def success(self) -> bool:
        """Флаг успешного выполнения (вычисляется из status).

        Returns:
            True, если статус COMPLETED, иначе False
        """
        return self.status == TaskStatus.COMPLETED

    @classmethod
    def success_result(
        cls, data: Any | None = None, metadata: dict[str, Any] | None = None
    ) -> TaskResult:
        """Создает успешный результат выполнения задачи.

        Args:
            data: Данные, возвращаемые задачей
            metadata: Дополнительные метаданные

        Returns:
            TaskResult со статусом COMPLETED
        """
        return cls(
            status=TaskStatus.COMPLETED,
            data=data,
            metadata=metadata or {},
        )

    @classmethod
    def failure_result(
        cls, error: str, metadata: dict[str, Any] | None = None
    ) -> TaskResult:
        """Создает результат с ошибкой выполнения задачи.

        Args:
            error: Сообщение об ошибке
            metadata: Дополнительные метаданные

        Returns:
            TaskResult со статусом FAILED
        """
        return cls(
            status=TaskStatus.FAILED,
            error=error,
            metadata=metadata or {},
        )


@dataclass
class ExecutionContext:
    """Контекст выполнения задачи.

    Предоставляет доступ к информации о текущем выполнении,
    трекеру прогресса и результатам других задач.

    Attributes:
        task_order: Список задач в порядке выполнения
        results: Результаты выполнения задач (имя задачи -> TaskResult)
        metadata: Дополнительные метаданные контекста
        progress_tracker: Трекер прогресса для сохранения состояния
        mode: Режим выполнения ('run', 'dry-run', 'resume')
    """

    task_order: list[str]
    results: dict[str, TaskResult]
    metadata: dict[str, Any]
    progress_tracker: ProgressTrackerProtocol | None = None
    mode: TaskMode = "run"


class Task(ABC):
    """Абстрактный базовый класс для задач.

    Все задачи должны наследоваться от этого класса и реализовывать
    обязательные методы.

    Пример использования:
        >>> from task_sequencer.interfaces import Task, TaskResult, ExecutionContext
        >>>
        >>> class MyTask(Task):
        ...     @property
        ...     def name(self) -> str:
        ...         return "my_task"
        ...     @property
        ...     def depends_on(self) -> list[str]:
        ...         return ["other_task"]
        ...     def execute(self, context: ExecutionContext) -> TaskResult:
        ...         # Получаем результат предыдущей задачи
        ...         other_result = context.results.get("other_task")
        ...         # Выполняем логику задачи
        ...         return TaskResult.success_result(data={"result": "done"})
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Уникальное имя задачи.

        Returns:
            Имя задачи
        """
        ...

    @property
    @abstractmethod
    def depends_on(self) -> list[str]:
        """Список имен задач, от которых зависит данная задача.

        Returns:
            Список имен задач-зависимостей
        """
        ...

    @abstractmethod
    def execute(self, context: ExecutionContext) -> TaskResult:
        """Выполняет задачу.

        Args:
            context: Контекст выполнения задачи

        Returns:
            TaskResult с результатом выполнения

        Raises:
            TaskExecutionError: Если произошла ошибка при выполнении
        """
        ...


class IterableTask(Task):
    """Абстрактный класс для итеративных задач.

    Итеративные задачи обрабатывают коллекции элементов.
    Наследуется от Task и добавляет методы для работы с элементами.

    Пример использования:
        >>> from task_sequencer.interfaces import IterableTask, TaskResult, ExecutionContext
        >>> from typing import Iterator
        >>>
        >>> class ProcessItemsTask(IterableTask):
        ...     @property
        ...     def name(self) -> str:
        ...         return "process_items"
        ...     @property
        ...     def depends_on(self) -> list[str]:
        ...         return []
        ...     def get_items(self, context: ExecutionContext) -> Iterator[str]:
        ...         return iter(["item1", "item2", "item3"])
        ...     def execute_for_item(self, item: str, context: ExecutionContext) -> None:
        ...         # Обработка одного элемента
        ...         print(f"Processing {item}")
        ...     def execute(self, context: ExecutionContext) -> TaskResult:
        ...         # Базовая реализация обрабатывает все элементы
        ...         for item in self.get_items(context):
        ...             self.execute_for_item(item, context)
        ...         return TaskResult.success_result()
    """

    @abstractmethod
    def get_items(self, context: ExecutionContext) -> Iterator[Any]:
        """Получает итератор элементов для обработки.

        Args:
            context: Контекст выполнения задачи

        Returns:
            Итератор элементов для обработки
        """
        ...

    @abstractmethod
    def execute_for_item(
        self, item: Any, context: ExecutionContext
    ) -> None:
        """Выполняет обработку одного элемента.

        Args:
            item: Элемент для обработки
            context: Контекст выполнения задачи

        Raises:
            TaskExecutionError: Если произошла ошибка при обработке элемента
        """
        ...


TParam = TypeVar("TParam")
"""Type variable для параметров ParameterizedIterableTask."""


class ParameterizedIterableTask(IterableTask, Generic[TParam]):
    """Задача, обрабатывающая элементы с внешними параметрами.

    Используется для случаев, когда элементы для обработки
    зависят от результатов других задач (например, *ForMatch методы).

    Поддерживает различные стратегии обработки ошибок:
    - "stop": Остановить выполнение при первой ошибке (по умолчанию)
    - "continue": Продолжить выполнение для остальных элементов
    - "retry": Повторить попытку (требует max_retries > 0)

    Пример использования:
        >>> from task_sequencer.interfaces import (
        ...     ParameterizedIterableTask, TaskResult, ExecutionContext
        ... )
        >>>
        >>> class StatsForMatchTask(ParameterizedIterableTask[str]):
        ...     @property
        ...     def name(self) -> str:
        ...         return "stats_for_match"
        ...     @property
        ...     def depends_on(self) -> list[str]:
        ...         return ["matches"]
        ...     def get_parameters(self, context: ExecutionContext) -> list[str]:
        ...         # Получаем match_ids из предыдущей задачи
        ...         matches_result = context.results.get("matches")
        ...         if matches_result and matches_result.data:
        ...             return matches_result.data.get("match_ids", [])
        ...         return []
        ...     def execute_for_parameter(self, match_id: str, context: ExecutionContext) -> None:
        ...         # Обрабатываем один match_id
        ...         print(f"Processing match {match_id}")
        ...     # execute наследуется с обработкой ошибок
    """

    def __init__(
        self, error_strategy: Literal["stop", "continue", "retry"] = "stop", max_retries: int = 0
    ) -> None:
        """Инициализирует параметризованную итеративную задачу.

        Args:
            error_strategy: Стратегия обработки ошибок:
                - "stop": Остановить выполнение при первой ошибке (по умолчанию)
                - "continue": Продолжить выполнение для остальных элементов
                - "retry": Повторить попытку (требует max_retries > 0)
            max_retries: Максимальное количество повторов при error_strategy="retry".
                По умолчанию: 0 (повторы отключены)

        Raises:
            ValueError: Если error_strategy="retry" и max_retries <= 0
        """
        if error_strategy == "retry" and max_retries <= 0:
            raise ValueError(
                "max_retries must be > 0 when error_strategy='retry'"
            )
        self.error_strategy = error_strategy
        self.max_retries = max_retries

    @abstractmethod
    def get_parameters(self, context: ExecutionContext) -> list[TParam]:
        """Получает параметры из контекста или предыдущих задач.

        Args:
            context: Контекст выполнения с результатами предыдущих задач

        Returns:
            Список параметров для обработки
        """
        ...

    def get_items(self, context: ExecutionContext) -> Iterator[Any]:
        """Реализация get_items через get_parameters.

        Args:
            context: Контекст выполнения задачи

        Returns:
            Итератор параметров для обработки
        """
        return iter(self.get_parameters(context))

    @abstractmethod
    def execute_for_parameter(
        self, param: TParam, context: ExecutionContext
    ) -> None:
        """Выполняет обработку для конкретного параметра.

        Args:
            param: Параметр для обработки
            context: Контекст выполнения

        Raises:
            TaskExecutionError: Если произошла ошибка при обработке параметра
        """
        ...

    def execute_for_item(self, item: Any, context: ExecutionContext) -> None:
        """Адаптер для execute_for_parameter.

        Args:
            item: Элемент для обработки (параметр)
            context: Контекст выполнения задачи

        Raises:
            TaskExecutionError: Если произошла ошибка при обработке элемента
        """
        self.execute_for_parameter(item, context)

    def on_error(
        self, param: TParam, error: Exception, context: ExecutionContext
    ) -> bool | None:
        """Обрабатывает ошибку при выполнении для параметра.

        Может быть переопределен для кастомной обработки ошибок.
        Если возвращает None, используется error_strategy.

        Args:
            param: Параметр, для которого произошла ошибка
            error: Исключение
            context: Контекст выполнения

        Returns:
            True - продолжить выполнение, False - остановить,
            None - использовать error_strategy по умолчанию

        Пример:
            >>> class MyTask(ParameterizedIterableTask[str]):
            ...     def on_error(self, param: str, error: Exception, context: ExecutionContext) -> bool:
            ...         # Логируем ошибку
            ...         logger.error(f"Error processing {param}: {error}")
            ...         # Продолжаем для остальных
            ...         return True
        """
        return None  # Использовать error_strategy по умолчанию

    def execute(self, context: ExecutionContext) -> TaskResult:
        """Выполняет задачу с обработкой ошибок.

        Обрабатывает все параметры согласно error_strategy и on_error callback.

        Args:
            context: Контекст выполнения задачи

        Returns:
            TaskResult с результатом выполнения. Если были ошибки, содержит
            информацию об ошибках в data["errors"] и количестве обработанных
            элементов в data["processed"].
        """
        parameters = self.get_parameters(context)
        errors: list[tuple[TParam, str]] = []
        processed = 0

        for param in parameters:
            retries = 0
            success = False
            param_error: tuple[TParam, str] | None = None

            while retries <= self.max_retries and not success:
                try:
                    self.execute_for_parameter(param, context)
                    success = True
                    processed += 1
                    # Если успешно после повтора, не добавляем ошибку
                    if param_error:
                        errors.remove(param_error)
                        param_error = None
                except Exception as e:
                    error_msg = str(e)
                    param_error = (param, error_msg)
                    # Добавляем ошибку только при первой попытке
                    if retries == 0:
                        errors.append(param_error)

                    # Вызываем on_error callback
                    should_continue = self.on_error(param, e, context)

                    # Если callback вернул явное значение, используем его
                    if should_continue is not None:
                        if not should_continue:
                            # Остановить выполнение для всех параметров
                            return self._create_result(errors, processed, len(parameters))
                        # Продолжить выполнение
                        if self.error_strategy == "retry" and retries < self.max_retries:
                            retries += 1
                            continue
                        # Продолжить для следующего параметра
                        break

                    # Используем error_strategy
                    if self.error_strategy == "stop":
                        # Остановить выполнение для всех параметров
                        return self._create_result(errors, processed, len(parameters))
                    elif self.error_strategy == "continue":
                        # Продолжить для следующего параметра
                        break
                    elif self.error_strategy == "retry":
                        if retries < self.max_retries:
                            retries += 1
                            continue
                        # Исчерпаны попытки, продолжаем для следующего параметра
                        break

        return self._create_result(errors, processed, len(parameters))

    def _create_result(
        self, errors: list[tuple[TParam, str]], processed: int, total: int
    ) -> TaskResult:
        """Создает результат выполнения задачи.

        Args:
            errors: Список ошибок (параметр, сообщение)
            processed: Количество успешно обработанных параметров
            total: Общее количество параметров

        Returns:
            TaskResult с результатом выполнения
        """
        if errors:
            result = TaskResult.failure_result(
                error=f"Failed to process {len(errors)} parameter(s)"
            )
            result.data = {
                "errors": errors,
                "processed": processed,
                "total": total,
            }
            return result

        result = TaskResult.success_result()
        result.data = {"processed": processed, "total": total}
        return result


class ProgressTracker(ABC):
    """Абстрактный класс для трекеров прогресса.

    Трекеры прогресса отвечают за сохранение и загрузку
    информации о прогрессе выполнения задач.

    Пример использования:
        >>> from task_sequencer.interfaces import ProgressTracker
        >>> from task_sequencer.progress import TaskProgress, TaskStatus
        >>>
        >>> class MyProgressTracker(ProgressTracker):
        ...     def __init__(self):
        ...         self._storage = {}
        ...     def save_progress(self, task_name: str, progress: TaskProgress) -> None:
        ...         self._storage[task_name] = progress
        ...     def get_progress(self, task_name: str) -> TaskProgress | None:
        ...         return self._storage.get(task_name)
        ...     def mark_completed(self, task_name: str) -> None:
        ...         if task_name in self._storage:
        ...             self._storage[task_name].status = TaskStatus.COMPLETED
        ...     def clear_progress(self, task_name: str) -> None:
        ...         self._storage.pop(task_name, None)
        >>>
        >>> tracker = MyProgressTracker()
        >>> progress = TaskProgress("task1", TaskStatus.IN_PROGRESS, total_items=10, processed_items=5)
        >>> tracker.save_progress("task1", progress)
        >>> saved = tracker.get_progress("task1")
    """

    @abstractmethod
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
        ...

    @abstractmethod
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

    @abstractmethod
    def mark_completed(self, task_name: str) -> None:
        """Отмечает задачу как завершенную.

        Args:
            task_name: Имя задачи

        Raises:
            ProgressError: Если не удалось обновить статус
        """
        ...

    @abstractmethod
    def clear_progress(self, task_name: str) -> None:
        """Очищает сохраненный прогресс задачи.

        Args:
            task_name: Имя задачи

        Raises:
            ProgressError: Если не удалось очистить прогресс
        """
        ...

    @abstractmethod
    def transaction(self) -> ContextManager[None]:
        """Возвращает контекстный менеджер для изолированной транзакции прогресса.

        Используется для гарантии сохранения прогресса независимо от
        основной транзакции БД. Для MemoryProgressTracker это заглушка.

        Пример использования:
            >>> with progress_tracker.transaction():
            ...     progress_tracker.save_progress("task1", progress)
            ...     # Прогресс сохранится даже если основная транзакция откатится

        Returns:
            Контекстный менеджер для транзакции
        """
        ...

