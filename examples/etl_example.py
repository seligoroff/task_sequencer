"""
Пример ETL процесса с использованием task-sequencer.

Демонстрирует:
- Задачи с зависимостями
- Использование IterableTask для обработки данных
- Последовательное выполнение Extract -> Transform -> Load
"""

from __future__ import annotations

from task_orchestrator import (
    DependencyValidator,
    ExecutionContext,
    IterableTask,
    Task,
    TaskOrchestrator,
    TaskRegistry,
    TaskResult,
)
from task_orchestrator.adapters.memory import MemoryProgressTracker


class ExtractTask(IterableTask):
    """Задача извлечения данных из источника."""

    def __init__(self) -> None:
        self._extracted_data: list[dict[str, str]] = []

    @property
    def name(self) -> str:
        return "extract"

    @property
    def depends_on(self) -> list[str]:
        return []

    def execute(self, context: ExecutionContext) -> TaskResult:
        """Извлекает данные из источника."""
        items = list(self.get_items(context))
        for item in items:
            self.execute_for_item(item, context)

        return TaskResult.success_result(
            data={"extracted_count": len(self._extracted_data)}
        )

    def get_items(self, context: ExecutionContext) -> list[dict[str, str]]:
        """Возвращает список элементов для извлечения."""
        # Симулируем извлечение данных из источника
        return [
            {"id": "1", "name": "Item 1", "value": "100"},
            {"id": "2", "name": "Item 2", "value": "200"},
            {"id": "3", "name": "Item 3", "value": "300"},
        ]

    def execute_for_item(self, item: dict[str, str], context: ExecutionContext) -> None:
        """Обрабатывает один элемент при извлечении."""
        print(f"  Извлечение: {item['name']} (ID: {item['id']})")
        self._extracted_data.append(item)


class TransformTask(Task):
    """Задача трансформации данных."""

    @property
    def name(self) -> str:
        return "transform"

    @property
    def depends_on(self) -> list[str]:
        return ["extract"]  # Зависит от задачи extract

    def execute(self, context: ExecutionContext) -> TaskResult:
        """Трансформирует извлеченные данные."""
        # Получаем результаты задачи extract
        extract_result = context.results.get("extract")
        if extract_result and extract_result.data:
            extracted_count = extract_result.data.get("extracted_count", 0)
            print(f"  Трансформация {extracted_count} элементов...")
            print("  Применение бизнес-правил...")
            print("  Валидация данных...")
            return TaskResult.success_result(
                data={"transformed_count": extracted_count}
            )
        return TaskResult.failure_result(error="No data to transform")


class LoadTask(IterableTask):
    """Задача загрузки данных в целевое хранилище."""

    def __init__(self) -> None:
        self._loaded_data: list[dict[str, str]] = []

    @property
    def name(self) -> str:
        return "load"

    @property
    def depends_on(self) -> list[str]:
        return ["transform"]  # Зависит от задачи transform

    def execute(self, context: ExecutionContext) -> TaskResult:
        """Загружает трансформированные данные."""
        items = list(self.get_items(context))
        for item in items:
            self.execute_for_item(item, context)

        return TaskResult.success_result(
            data={"loaded_count": len(self._loaded_data)}
        )

    def get_items(self, context: ExecutionContext) -> list[dict[str, str]]:
        """Возвращает список элементов для загрузки."""
        # В реальном сценарии данные берутся из результатов transform
        # Здесь симулируем получение трансформированных данных
        transform_result = context.results.get("transform")
        if transform_result and transform_result.data:
            count = transform_result.data.get("transformed_count", 0)
            return [{"id": str(i), "data": f"transformed_item_{i}"} for i in range(1, count + 1)]
        return []

    def execute_for_item(self, item: dict[str, str], context: ExecutionContext) -> None:
        """Загружает один элемент в целевое хранилище."""
        print(f"  Загрузка: {item['data']} (ID: {item['id']})")
        self._loaded_data.append(item)


def main() -> None:
    """Основная функция для запуска примера."""
    print("=== Пример ETL процесса ===\n")

    # Создаем задачи
    extract_task = ExtractTask()
    transform_task = TransformTask()
    load_task = LoadTask()

    # Создаем реестр задач
    registry = TaskRegistry([extract_task, transform_task, load_task])

    # Создаем трекер прогресса
    tracker = MemoryProgressTracker()

    # Создаем валидатор зависимостей
    validator = DependencyValidator()

    # Создаем оркестратор
    orchestrator = TaskOrchestrator(
        task_registry=registry,
        progress_tracker=tracker,
        dependency_validator=validator,
    )

    # Выполняем ETL процесс
    print("Запуск ETL процесса...")
    print("\n1. Extract (Извлечение):")
    print("2. Transform (Трансформация):")
    print("3. Load (Загрузка):\n")

    result = orchestrator.execute(["extract", "transform", "load"])

    # Выводим результаты
    print("\n=== Результаты выполнения ===")
    print(f"Статус: {result.status.value}")
    print(f"Выполнено задач: {len(result.completed_tasks)}")
    print(f"Провалено задач: {len(result.failed_tasks)}")

    for task_name in result.completed_tasks:
        task_result = result.results[task_name]
        print(f"\nЗадача '{task_name}':")
        print(f"  Успешно: {task_result.success}")
        if task_result.data:
            print(f"  Данные: {task_result.data}")


if __name__ == "__main__":
    main()

