"""Тесты для transaction() метода ProgressTracker."""

from __future__ import annotations

import pytest

from task_sequencer.adapters import MemoryProgressTracker
from task_sequencer.progress import TaskProgress, TaskStatus


class TestTransaction:
    """Тесты для transaction() метода."""

    def test_memory_tracker_transaction(self) -> None:
        """Тест transaction() для MemoryProgressTracker."""
        tracker = MemoryProgressTracker()

        progress = TaskProgress(
            task_name="test_task",
            status=TaskStatus.IN_PROGRESS,
            total_items=10,
            processed_items=5,
        )

        with tracker.transaction():
            tracker.save_progress("test_task", progress)

        saved = tracker.get_progress("test_task")
        assert saved is not None
        assert saved.task_name == "test_task"
        assert saved.status == TaskStatus.IN_PROGRESS
        assert saved.processed_items == 5

    def test_memory_tracker_transaction_multiple_operations(self) -> None:
        """Тест transaction() с несколькими операциями."""
        tracker = MemoryProgressTracker()

        with tracker.transaction():
            progress1 = TaskProgress(
                task_name="task1", status=TaskStatus.IN_PROGRESS, processed_items=1
            )
            tracker.save_progress("task1", progress1)

            progress2 = TaskProgress(
                task_name="task2", status=TaskStatus.IN_PROGRESS, processed_items=2
            )
            tracker.save_progress("task2", progress2)

            tracker.mark_completed("task1")

        assert tracker.get_progress("task1") is not None
        assert tracker.get_progress("task1").status == TaskStatus.COMPLETED
        assert tracker.get_progress("task2") is not None
        assert tracker.get_progress("task2").status == TaskStatus.IN_PROGRESS

    def test_memory_tracker_transaction_nested(self) -> None:
        """Тест вложенных транзакций для MemoryProgressTracker."""
        tracker = MemoryProgressTracker()

        with tracker.transaction():
            progress1 = TaskProgress(
                task_name="task1", status=TaskStatus.IN_PROGRESS
            )
            tracker.save_progress("task1", progress1)

            with tracker.transaction():
                progress2 = TaskProgress(
                    task_name="task2", status=TaskStatus.IN_PROGRESS
                )
                tracker.save_progress("task2", progress2)

        assert tracker.get_progress("task1") is not None
        assert tracker.get_progress("task2") is not None



