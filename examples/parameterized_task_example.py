"""Пример использования ParameterizedIterableTask.

Демонстрирует создание задачи, которая обрабатывает элементы,
зависящие от результатов предыдущих задач.
"""

from __future__ import annotations

from task_sequencer import (
    DependencyValidator,
    MemoryProgressTracker,
    ParameterizedIterableTask,
    Task,
    TaskOrchestrator,
    TaskRegistry,
)
from task_sequencer.interfaces import ExecutionContext, TaskResult
from task_sequencer.progress import TaskStatus


class ExtractMatchesTask(Task):
    """Задача извлечения списка матчей."""

    @property
    def name(self) -> str:
        return "extract_matches"

    @property
    def depends_on(self) -> list[str]:
        return []

    def execute(self, context: ExecutionContext) -> TaskResult:
        """Извлекает список ID матчей."""
        # Симуляция извлечения данных
        match_ids = ["match_1", "match_2", "match_3"]
        return TaskResult.success_result(data={"match_ids": match_ids})


class ProcessStatsForMatchTask(ParameterizedIterableTask[str]):
    """Задача обработки статистики для каждого матча.

    Использует ParameterizedIterableTask для обработки списка match_ids,
    полученных из предыдущей задачи.
    """

    @property
    def name(self) -> str:
        return "process_stats_for_match"

    @property
    def depends_on(self) -> list[str]:
        return ["extract_matches"]

    def get_parameters(self, context: ExecutionContext) -> list[str]:
        """Получает список match_ids из результата предыдущей задачи."""
        extract_result = context.results.get("extract_matches")
        if extract_result and extract_result.data:
            return extract_result.data.get("match_ids", [])
        return []

    def execute_for_parameter(
        self, match_id: str, context: ExecutionContext
    ) -> None:
        """Обрабатывает статистику для одного матча."""
        print(f"Processing stats for match: {match_id}")
        # Здесь была бы реальная логика обработки

    def execute(self, context: ExecutionContext) -> TaskResult:
        """Выполняет обработку всех матчей."""
        match_ids = self.get_parameters(context)
        print(f"Found {len(match_ids)} matches to process")

        for match_id in match_ids:
            self.execute_for_parameter(match_id, context)

        return TaskResult.success_result(
            data={"processed_matches": len(match_ids)}
        )


def main() -> None:
    """Основная функция для демонстрации."""
    # Создание реестра задач
    registry = TaskRegistry(
        [
            ExtractMatchesTask(),
            ProcessStatsForMatchTask(),
        ]
    )

    # Создание оркестратора
    tracker = MemoryProgressTracker()
    validator = DependencyValidator()
    orchestrator = TaskOrchestrator(registry, tracker, validator)

    # Выполнение задач
    print("Executing tasks...")
    result = orchestrator.execute(
        ["extract_matches", "process_stats_for_match"]
    )

    # Вывод результатов
    print(f"\nExecution status: {result.status}")
    print(f"Completed tasks: {result.completed_tasks}")
    print(f"Failed tasks: {result.failed_tasks}")

    if result.status == TaskStatus.COMPLETED:
        stats_result = result.results.get("process_stats_for_match")
        if stats_result and stats_result.data:
            print(
                f"Processed matches: {stats_result.data.get('processed_matches', 0)}"
            )


if __name__ == "__main__":
    main()



