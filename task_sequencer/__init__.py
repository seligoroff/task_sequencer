"""
Task Sequencer - Sequential task orchestrator with dependency management and progress tracking.

A universal Python component for managing sequential task execution with dependencies,
progress tracking, and resume capability.

Основные компоненты:
    - TaskOrchestrator: Основной класс для управления выполнением задач
    - Task, IterableTask: Абстрактные классы для определения задач
    - ProgressTracker: Абстрактный класс для отслеживания прогресса
    - TaskRegistry: Реестр задач
    - DependencyValidator: Валидатор зависимостей
    - ResumeIterator, LimitingIterator: Итераторы для управления потоком элементов

Пример использования:
    >>> from task_sequencer import TaskOrchestrator, TaskRegistry, Task
    >>> from task_sequencer.adapters import MemoryProgressTracker
    >>> from task_sequencer.validators import DependencyValidator
    >>>
    >>> class MyTask(Task):
    ...     @property
    ...     def name(self) -> str:
    ...         return "my_task"
    ...     @property
    ...     def depends_on(self) -> list[str]:
    ...         return []
    ...     def execute(self, context) -> TaskResult:
    ...         return TaskResult.success_result()
    >>>
    >>> registry = TaskRegistry([MyTask()])
    >>> tracker = MemoryProgressTracker()
    >>> validator = DependencyValidator()
    >>> orchestrator = TaskOrchestrator(registry, tracker, validator)
    >>> result = orchestrator.execute(["my_task"])
"""

__version__ = "0.2.0"
from task_sequencer.core import ExecutionResult, TaskOrchestrator, TaskRegistry
from task_sequencer.exceptions import (
    DependencyError,
    ProgressError,
    TaskExecutionError,
)
from task_sequencer.interfaces import (
    ExecutionContext,
    IterableTask,
    ParameterizedIterableTask,
    ProgressTracker,
    Task,
    TaskMode,
    TaskResult,
)
from task_sequencer.iterators import LimitingIterator, ResumeIterator
from task_sequencer.logging import get_logger, setup_logging
from task_sequencer.progress import TaskProgress, TaskStatus
from task_sequencer.validators import DependencyValidator

__all__ = [
    "TaskOrchestrator",
    "TaskRegistry",
    "ExecutionResult",
    "DependencyValidator",
    "ResumeIterator",
    "LimitingIterator",
    "Task",
    "IterableTask",
    "ParameterizedIterableTask",
    "ProgressTracker",
    "TaskResult",
    "TaskMode",
    "ExecutionContext",
    "TaskProgress",
    "TaskStatus",
    "DependencyError",
    "TaskExecutionError",
    "ProgressError",
    "get_logger",
    "setup_logging",
]

# Адаптеры импортируются напрямую из task_sequencer.adapters
# Например: from task_sequencer.adapters import MemoryProgressTracker

