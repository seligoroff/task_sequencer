"""Ядро task_sequencer: TaskRegistry и TaskOrchestrator."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any

from task_sequencer.exceptions import DependencyError, TaskExecutionError
from task_sequencer.interfaces import (
    ExecutionContext,
    IterableTask,
    ProgressTracker,
    Task,
    TaskMode,
    TaskResult,
)
from task_sequencer.logging import get_logger
from task_sequencer.progress import TaskProgress, TaskStatus

if TYPE_CHECKING:
    from task_sequencer.validators import DependencyValidator


class TaskRegistry:
    """Реестр задач для управления и доступа к задачам.

    Реестр хранит задачи и обеспечивает их регистрацию с проверкой
    уникальности имен. Предоставляет методы для получения задач
    по имени и получения всех зарегистрированных задач.

    Пример использования:
        >>> from task_sequencer import TaskRegistry, Task
        >>> from task_sequencer.interfaces import TaskResult, ExecutionContext
        >>>
        >>> class Task1(Task):
        ...     @property
        ...     def name(self) -> str:
        ...         return "task1"
        ...     @property
        ...     def depends_on(self) -> list[str]:
        ...         return []
        ...     def execute(self, context: ExecutionContext) -> TaskResult:
        ...         return TaskResult.success_result()
        >>>
        >>> registry = TaskRegistry([Task1()])
        >>> # Проверка наличия задачи
        >>> "task1" in registry
        True
        >>> # Доступ через оператор []
        >>> task = registry["task1"]
        >>> # Получение словаря всех задач
        >>> all_tasks = registry.tasks  # dict[str, Task]
        >>> # Старые методы продолжают работать
        >>> task = registry.get("task1")
        >>> all_tasks_list = registry.get_all()  # list[Task]

    Attributes:
        _tasks: Словарь задач (имя задачи -> Task)
    """

    def __init__(self, tasks: list[Task] | None = None) -> None:
        """Инициализирует реестр задач.

        Args:
            tasks: Список задач для начальной регистрации

        Raises:
            ValueError: Если в списке tasks есть задачи с дублирующимися именами
        """
        self._tasks: dict[str, Task] = {}
        if tasks:
            for task in tasks:
                self.register(task)

    def register(self, task: Task) -> None:
        """Регистрирует задачу в реестре.

        Args:
            task: Задача для регистрации

        Raises:
            ValueError: Если задача с таким именем уже зарегистрирована
        """
        task_name = task.name
        self._check_unique_name(task_name)
        self._tasks[task_name] = task

    def get(self, task_name: str) -> Task:
        """Получает задачу по имени.

        Args:
            task_name: Имя задачи

        Returns:
            Задача с указанным именем

        Raises:
            KeyError: Если задача с указанным именем не найдена

        Пример:
            >>> registry = TaskRegistry([Task1(), Task2()])
            >>> task = registry.get("task1")
            >>> # Проверка наличия задачи
            >>> try:
            ...     task = registry.get("task3")
            ... except KeyError:
            ...     print("Task not found")
        """
        if task_name not in self._tasks:
            raise KeyError(f"Task '{task_name}' not found in registry")
        return self._tasks[task_name]

    def get_all(self) -> list[Task]:
        """Получает все зарегистрированные задачи.

        Returns:
            Список всех задач в реестре
        """
        return list(self._tasks.values())

    def __contains__(self, task_name: str) -> bool:
        """Проверяет наличие задачи в реестре.

        Поддерживает оператор `in` для проверки наличия задачи.

        Args:
            task_name: Имя задачи

        Returns:
            True, если задача зарегистрирована, иначе False

        Пример:
            >>> registry = TaskRegistry([Task1()])
            >>> "task1" in registry
            True
            >>> "task2" in registry
            False
        """
        return task_name in self._tasks

    def __getitem__(self, task_name: str) -> Task:
        """Получает задачу по имени через оператор [].

        Поддерживает доступ к задачам через оператор `[]`.

        Args:
            task_name: Имя задачи

        Returns:
            Задача с указанным именем

        Raises:
            KeyError: Если задача с указанным именем не найдена

        Пример:
            >>> registry = TaskRegistry([Task1()])
            >>> task = registry["task1"]
        """
        return self._tasks[task_name]

    @property
    def tasks(self) -> dict[str, Task]:
        """Возвращает словарь всех зарегистрированных задач.

        Возвращает копию словаря для безопасности (read-only доступ).

        Returns:
            Словарь задач (имя задачи -> Task)

        Пример:
            >>> registry = TaskRegistry([Task1(), Task2()])
            >>> all_tasks = registry.tasks
            >>> len(all_tasks)
            2
            >>> "task1" in all_tasks
            True
            >>> for name, task in all_tasks.items():
            ...     print(f"{name}: {task}")
        """
        return self._tasks.copy()

    def _check_unique_name(self, task_name: str) -> None:
        """Проверяет уникальность имени задачи.

        Args:
            task_name: Имя задачи для проверки

        Raises:
            ValueError: Если задача с таким именем уже зарегистрирована
        """
        if task_name in self._tasks:
            raise ValueError(
                f"Task with name '{task_name}' is already registered"
            )


@dataclass
class ExecutionResult:
    """Результат выполнения последовательности задач.

    Attributes:
        status: Общий статус выполнения
        results: Результаты выполнения каждой задачи (имя задачи -> TaskResult)
        completed_tasks: Список имен успешно выполненных задач
        failed_tasks: Список имен задач, выполнение которых завершилось с ошибкой
        metadata: Дополнительные метаданные о выполнении
    """

    status: TaskStatus
    results: dict[str, TaskResult]
    completed_tasks: list[str]
    failed_tasks: list[str]
    metadata: dict[str, Any] = field(default_factory=dict)


class TaskOrchestrator:
    """Оркестратор для управления последовательным выполнением задач.

    Управляет выполнением задач с зависимостями, отслеживает прогресс
    и обеспечивает возможность восстановления с места остановки.

    Пример использования:
        >>> from task_sequencer import TaskOrchestrator, TaskRegistry, Task
        >>> from task_sequencer.adapters import MemoryProgressTracker
        >>> from task_sequencer.validators import DependencyValidator
        >>> from task_sequencer.interfaces import TaskResult, ExecutionContext
        >>>
        >>> class MyTask(Task):
        ...     @property
        ...     def name(self) -> str:
        ...         return "my_task"
        ...     @property
        ...     def depends_on(self) -> list[str]:
        ...         return []
        ...     def execute(self, context: ExecutionContext) -> TaskResult:
        ...         return TaskResult.success_result()
        >>>
        >>> registry = TaskRegistry([MyTask()])
        >>> tracker = MemoryProgressTracker()
        >>> validator = DependencyValidator()
        >>> orchestrator = TaskOrchestrator(registry, tracker, validator)
        >>> result = orchestrator.execute(["my_task"])
        >>> print(f"Completed: {result.completed_tasks}")

    Attributes:
        task_registry: Реестр задач
        progress_tracker: Трекер прогресса
        dependency_validator: Валидатор зависимостей
    """

    def __init__(
        self,
        task_registry: TaskRegistry,
        progress_tracker: ProgressTracker,
        dependency_validator: DependencyValidator,
    ) -> None:
        """Инициализирует оркестратор задач.

        Args:
            task_registry: Реестр задач
            progress_tracker: Трекер прогресса
            dependency_validator: Валидатор зависимостей
        """
        self.task_registry = task_registry
        self.progress_tracker = progress_tracker
        self.dependency_validator = dependency_validator

    def execute(
        self,
        task_order: list[str],
        mode: TaskMode = "run",
        resume: bool = False,
    ) -> ExecutionResult:
        """Выполняет задачи в указанном порядке.

        Args:
            task_order: Явный список задач в порядке выполнения
            mode: Режим выполнения ('run', 'dry-run', 'resume')
            resume: Флаг восстановления с места остановки

        Returns:
            ExecutionResult с результатами выполнения задач

        Raises:
            DependencyError: Если нарушены зависимости задач
            TaskExecutionError: Если произошла ошибка при выполнении задачи
        """
        # Валидация зависимостей
        self._validate_dependencies(task_order)

        # Инициализация контекста выполнения
        context = ExecutionContext(
            task_order=task_order,
            results={},
            metadata={},
            progress_tracker=self.progress_tracker,
            mode=mode,
        )

        logger = get_logger()
        logger.info(
            f"Starting execution of {len(task_order)} tasks",
            extra={"mode": mode, "resume": resume, "task_order": task_order},
        )

        completed_tasks: list[str] = []
        completed_set: set[str] = set()
        results: dict[str, TaskResult] = {}

        # Выполнение задач в указанном порядке
        for task_name in task_order:
            # Проверка удовлетворенности зависимостей
            task = self.task_registry.get(task_name)
            if not self._check_dependencies_satisfied(task, completed_set):
                raise DependencyError(
                    f"Task '{task_name}' dependencies not satisfied"
                )

            # Выполнение задачи
            try:
                # Сохранение прогресса: начало выполнения (только если задача еще не начата)
                existing_progress = self.progress_tracker.get_progress(task_name)
                if existing_progress is None or existing_progress.status != TaskStatus.IN_PROGRESS:
                    self._mark_task_started(task_name)

                # Для IterableTask с resume нужно установить id_extractor в metadata
                if isinstance(task, IterableTask) and resume:
                    # Пытаемся использовать id_extractor из metadata, если есть
                    if "id_extractor" not in context.metadata:
                        # Используем функцию по умолчанию, которая работает с dict
                        def default_id_extractor(item: Any) -> str:
                            if isinstance(item, dict) and "id" in item:
                                return str(item["id"])
                            return str(item)

                        context.metadata["id_extractor"] = default_id_extractor
                    # Устанавливаем флаг resume в metadata для IterableTask
                    context.metadata["resume"] = True

                # Выполнение задачи
                if isinstance(task, IterableTask):
                    result = self._execute_iterable_task(task, context)
                else:
                    result = self._execute_task(task, context)

                results[task_name] = result
                context.results[task_name] = result

                if result.success:
                    completed_tasks.append(task_name)
                    completed_set.add(task_name)
                    with self.progress_tracker.transaction():
                        self.progress_tracker.mark_completed(task_name)
                else:
                    # Задача провалилась - прерываем выполнение
                    self._mark_task_failed(task_name, result.error or "Unknown error")
                    break

            except TaskExecutionError as e:
                # Ошибка выполнения задачи
                error_result = TaskResult.failure_result(
                    error=str(e), metadata={"task_name": task_name}
                )
                results[task_name] = error_result
                context.results[task_name] = error_result
                self._mark_task_failed(task_name, str(e))
                break

        # Формирование результата
        failed_tasks = [
            name for name, result in results.items() if not result.success
        ]
        final_status = (
            TaskStatus.COMPLETED
            if len(completed_tasks) == len(task_order)
            else TaskStatus.FAILED
        )

        return ExecutionResult(
            status=final_status,
            results=results,
            completed_tasks=completed_tasks,
            failed_tasks=failed_tasks,
            metadata={"mode": mode, "resume": resume},
        )

    def _validate_dependencies(self, task_order: list[str]) -> None:
        """Валидирует зависимости между задачами.

        Args:
            task_order: Список задач в порядке выполнения

        Raises:
            DependencyError: Если нарушены зависимости
        """
        self.dependency_validator.validate(task_order, self.task_registry)

    def _check_dependencies_satisfied(
        self, task: Task, completed: set[str]
    ) -> bool:
        """Проверяет, что все зависимости задачи выполнены.

        Args:
            task: Задача для проверки
            completed: Множество имен выполненных задач

        Returns:
            True если все зависимости выполнены, False иначе
        """
        return all(dep in completed for dep in task.depends_on)

    def _execute_task(
        self, task: Task, context: ExecutionContext
    ) -> TaskResult:
        """Выполняет обычную задачу.

        Args:
            task: Задача для выполнения
            context: Контекст выполнения

        Returns:
            TaskResult с результатом выполнения

        Raises:
            TaskExecutionError: Если произошла ошибка при выполнении
        """
        logger = get_logger(task.name)
        logger.debug("Executing task")

        try:
            result = task.execute(context)
            logger.info(
                "Task completed successfully",
                extra={
                    "success": result.success,
                    "status": result.status.value,
                },
            )
            return result
        except Exception as e:
            logger.error(f"Task execution failed: {e}", exc_info=True)
            raise TaskExecutionError(
                f"Error executing task '{task.name}': {e}",
                task_name=task.name,
            ) from e

    def _execute_iterable_task(
        self, task: IterableTask, context: ExecutionContext
    ) -> TaskResult:
        """Выполняет итеративную задачу с логированием прогресса.

        Args:
            task: Итеративная задача для выполнения
            context: Контекст выполнения

        Returns:
            TaskResult с результатом выполнения

        Raises:
            TaskExecutionError: Если произошла ошибка при выполнении
        """
        logger = get_logger(task.name)
        logger.debug("Executing iterable task")

        try:
            # Получаем элементы для обработки
            items = list(task.get_items(context))
            total = len(items)

            if total == 0:
                logger.info("No items to process")
                return TaskResult.success_result()

            logger.info(
                f"Processing {total} items",
                extra={"total_items": total},
            )

            # Выполняем задачу (она сама обрабатывает элементы)
            result = task.execute(context)

            # Логируем прогресс из сохраненного прогресса, если доступен
            progress = self.progress_tracker.get_progress(task.name)
            if progress:
                processed = progress.processed_items or 0
                logger.info(
                    f"Task completed: {processed}/{total} items processed",
                    extra={
                        "processed_items": processed,
                        "total_items": total,
                        "success": result.success,
                        "status": result.status.value,
                    },
                )
            else:
                logger.info(
                    "Task completed",
                    extra={
                        "success": result.success,
                        "status": result.status.value,
                    },
                )

            return result
        except Exception as e:
            logger.error(f"Iterable task execution failed: {e}", exc_info=True)
            raise TaskExecutionError(
                f"Error executing iterable task '{task.name}': {e}",
                task_name=task.name,
            ) from e


    def _mark_task_started(self, task_name: str) -> None:
        """Отмечает задачу как начатую.

        Args:
            task_name: Имя задачи
        """
        with self.progress_tracker.transaction():
            progress = TaskProgress(
                task_name=task_name,
                status=TaskStatus.IN_PROGRESS,
                started_at=datetime.now(),
            )
            self.progress_tracker.save_progress(task_name, progress)

    def _mark_task_failed(self, task_name: str, error_message: str) -> None:
        """Отмечает задачу как провалившуюся.

        Args:
            task_name: Имя задачи
            error_message: Сообщение об ошибке
        """
        with self.progress_tracker.transaction():
            progress = TaskProgress(
                task_name=task_name,
                status=TaskStatus.FAILED,
                error_message=error_message,
                completed_at=datetime.now(),
            )
            self.progress_tracker.save_progress(task_name, progress)

