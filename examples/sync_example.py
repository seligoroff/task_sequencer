"""
Пример синхронизации данных с использованием task-sequencer.

Демонстрирует:
- Использование режима resume для восстановления с места остановки
- Работу с прогрессом выполнения
- Обработку больших объемов данных с возможностью прерывания и продолжения
"""

from __future__ import annotations

from task_orchestrator import (
    DependencyValidator,
    ExecutionContext,
    IterableTask,
    TaskOrchestrator,
    TaskRegistry,
    TaskResult,
)
from task_orchestrator.adapters.memory import MemoryProgressTracker
from task_orchestrator.progress import TaskProgress, TaskStatus


class SyncDataTask(IterableTask):
    """Задача синхронизации данных между системами."""

    def __init__(self) -> None:
        self._synced_items: list[dict[str, str]] = []

    @property
    def name(self) -> str:
        return "sync_data"

    @property
    def depends_on(self) -> list[str]:
        return []

    def execute(self, context: ExecutionContext) -> TaskResult:
        """Синхронизирует данные с поддержкой resume."""
        from task_orchestrator.iterators import ResumeIterator

        items = list(self.get_items(context))

        # Используем ResumeIterator если resume=True
        if context.metadata.get("resume", False):
            id_extractor = context.metadata.get("id_extractor")
            if id_extractor is None:
                def default_id_extractor(item: dict[str, str]) -> str:
                    return item["id"]
                id_extractor = default_id_extractor

            if context.progress_tracker:
                items_iterator = ResumeIterator(
                    items=items,
                    progress_tracker=context.progress_tracker,
                    task_name=self._name,
                    id_extractor=id_extractor,
                    save_interval=5,  # Сохраняем прогресс каждые 5 элементов
                )
            else:
                items_iterator = iter(items)
        else:
            items_iterator = iter(items)

        for item in items_iterator:
            self.execute_for_item(item, context)

        return TaskResult.success_result(
            data={"synced_count": len(self._synced_items)}
        )

    def get_items(self, context: ExecutionContext) -> list[dict[str, str]]:
        """Возвращает список элементов для синхронизации."""
        # Симулируем большой список данных для синхронизации
        return [
            {"id": str(i), "name": f"Record {i}", "status": "pending"}
            for i in range(1, 21)  # 20 элементов
        ]

    def execute_for_item(self, item: dict[str, str], context: ExecutionContext) -> None:
        """Синхронизирует один элемент."""
        # Симулируем синхронизацию
        print(f"  Синхронизация: {item['name']} (ID: {item['id']})")
        item["status"] = "synced"
        self._synced_items.append(item)


def main() -> None:
    """Основная функция для запуска примера."""
    print("=== Пример синхронизации данных ===\n")

    # Создаем задачу
    sync_task = SyncDataTask()

    # Создаем трекер прогресса
    tracker = MemoryProgressTracker()

    # Создаем валидатор зависимостей
    validator = DependencyValidator()

    # Первый запуск - обрабатываем часть данных
    print("Первый запуск: синхронизация первых 10 элементов...")
    print("(В реальном сценарии это может быть прервано внешним фактором)\n")

    # Симулируем ситуацию: обработали 10 элементов, затем прервали
    # Выполняем синхронизацию первых 10 элементов
    context = ExecutionContext(
        task_order=["sync_data"],
        results={},
        metadata={},
        progress_tracker=tracker,
    )
    items = sync_task.get_items(context)
    for i, item in enumerate(items):
        if i >= 10:
            # Сохраняем прогресс перед прерыванием
            last_id = (
                sync_task._synced_items[-1]["id"] if sync_task._synced_items else None
            )
            progress = TaskProgress(
                task_name="sync_data",
                status=TaskStatus.IN_PROGRESS,
                last_processed_id=last_id,
                processed_items=len(sync_task._synced_items),
                total_items=20,
            )
            tracker.save_progress("sync_data", progress)
            break
        sync_task.execute_for_item(item, context)

    print(f"\nОбработано элементов: {len(sync_task._synced_items)}")
    print("Прогресс сохранен.\n")

    # Второй запуск - продолжаем с места остановки
    print("Второй запуск: продолжение синхронизации с места остановки...\n")

    # Создаем новую задачу для второго запуска
    sync_task2 = SyncDataTask()
    registry2 = TaskRegistry([sync_task2])
    orchestrator2 = TaskOrchestrator(registry2, tracker, validator)

    result = orchestrator2.execute(["sync_data"], resume=True)

    # Выводим результаты
    print("\n=== Результаты выполнения ===")
    print(f"Статус: {result.status.value}")
    print(f"Выполнено задач: {len(result.completed_tasks)}")

    if result.completed_tasks:
        task_result = result.results[result.completed_tasks[0]]
        print(f"\nЗадача '{result.completed_tasks[0]}':")
        print(f"  Успешно: {task_result.success}")
        if task_result.data:
            print(f"  Синхронизировано элементов: {task_result.data.get('synced_count', 0)}")

    # Проверяем прогресс
    progress = tracker.get_progress("sync_data")
    if progress:
        print("\nФинальный прогресс:")
        print(f"  Статус: {progress.status.value}")
        print(f"  Обработано: {progress.processed_items}/{progress.total_items}")
        print(f"  Последний ID: {progress.last_processed_id}")
        print(f"  Начато: {progress.started_at}")
        print(f"  Завершено: {progress.completed_at}")


if __name__ == "__main__":
    main()

