"""
Пример использования различных адаптеров ProgressTracker.

Демонстрирует использование MemoryProgressTracker, MySQLProgressTracker,
MongoDBProgressTracker и PostgreSQLProgressTracker.
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
from task_sequencer.adapters import MemoryProgressTracker

# Для использования БД-адаптеров установите соответствующие зависимости:
# pip install task-sequencer[mysql]
# pip install task-sequencer[mongodb]
# pip install task-sequencer[postgresql]


class SimpleTask(Task):
    """Простая задача для демонстрации."""

    @property
    def name(self) -> str:
        return "simple_task"

    @property
    def depends_on(self) -> list[str]:
        return []

    def execute(self, context: ExecutionContext) -> TaskResult:
        print("Executing simple task...")
        return TaskResult.success_result(data={"message": "Task completed"})


def example_memory_tracker() -> None:
    """Пример использования MemoryProgressTracker."""
    print("=== MemoryProgressTracker ===")

    # MemoryProgressTracker не требует зависимостей
    tracker = MemoryProgressTracker()

    registry = TaskRegistry([SimpleTask()])
    validator = DependencyValidator()
    orchestrator = TaskOrchestrator(registry, tracker, validator)

    result = orchestrator.execute(["simple_task"])
    print(f"Status: {result.status.value}")
    print(f"Completed: {result.completed_tasks}")


def example_mysql_tracker() -> None:
    """Пример использования MySQLProgressTracker."""
    print("\n=== MySQLProgressTracker ===")
    print("Требует: pip install task-sequencer[mysql]")

    try:
        from task_sequencer.adapters import MySQLProgressTracker

        # Имя БД указывается в connection string
        tracker = MySQLProgressTracker(
            connection_string="mysql+pymysql://user:password@localhost:3306/task_sequencer",
            create_tables=True,  # Автоматически создает таблицу task_progress
        )

        registry = TaskRegistry([SimpleTask()])
        validator = DependencyValidator()
        orchestrator = TaskOrchestrator(registry, tracker, validator)

        result = orchestrator.execute(["simple_task"])
        print(f"Status: {result.status.value}")
    except ImportError:
        print("MySQLProgressTracker не доступен. Установите: pip install task-sequencer[mysql]")


def example_mongodb_tracker() -> None:
    """Пример использования MongoDBProgressTracker."""
    print("\n=== MongoDBProgressTracker ===")
    print("Требует: pip install task-sequencer[mongodb]")

    try:
        from task_sequencer.adapters import MongoDBProgressTracker

        # Без аутентификации
        tracker = MongoDBProgressTracker(
            connection_string="mongodb://localhost:27017/",
            database_name="task_sequencer",
            collection_name="task_progress",
        )

        # С аутентификацией (database в connection string для аутентификации)
        # tracker = MongoDBProgressTracker(
        #     connection_string="mongodb://user:pass@host:27017/task_sequencer",
        #     database_name="task_sequencer",  # Используется для выбора БД
        #     collection_name="task_progress",
        # )

        registry = TaskRegistry([SimpleTask()])
        validator = DependencyValidator()
        orchestrator = TaskOrchestrator(registry, tracker, validator)

        result = orchestrator.execute(["simple_task"])
        print(f"Status: {result.status.value}")
    except ImportError:
        print(
            "MongoDBProgressTracker не доступен. Установите: pip install task-sequencer[mongodb]"
        )


def example_postgresql_tracker() -> None:
    """Пример использования PostgreSQLProgressTracker."""
    print("\n=== PostgreSQLProgressTracker ===")
    print("Требует: pip install task-sequencer[postgresql]")

    try:
        from task_sequencer.adapters import PostgreSQLProgressTracker

        # Имя БД указывается в connection string
        tracker = PostgreSQLProgressTracker(
            connection_string="postgresql+psycopg2://user:password@localhost:5432/task_sequencer",
            create_tables=True,  # Автоматически создает таблицу task_progress
        )

        registry = TaskRegistry([SimpleTask()])
        validator = DependencyValidator()
        orchestrator = TaskOrchestrator(registry, tracker, validator)

        result = orchestrator.execute(["simple_task"])
        print(f"Status: {result.status.value}")
    except ImportError:
        print(
            "PostgreSQLProgressTracker не доступен. Установите: pip install task-sequencer[postgresql]"
        )


def main() -> None:
    """Основная функция для запуска примеров."""
    print("Примеры использования адаптеров ProgressTracker\n")

    # MemoryProgressTracker всегда доступен
    example_memory_tracker()

    # БД-адаптеры требуют установки зависимостей
    example_mysql_tracker()
    example_mongodb_tracker()
    example_postgresql_tracker()


if __name__ == "__main__":
    main()

