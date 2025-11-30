"""Тесты для моделей данных прогресса."""

from __future__ import annotations

from datetime import datetime

import pytest

from task_sequencer.progress import TaskProgress, TaskStatus


class TestTaskStatus:
    """Тесты для TaskStatus enum."""

    def test_task_status_values(self) -> None:
        """Тест проверяет, что все значения TaskStatus определены."""
        assert TaskStatus.PENDING.value == "pending"
        assert TaskStatus.IN_PROGRESS.value == "in_progress"
        assert TaskStatus.COMPLETED.value == "completed"
        assert TaskStatus.FAILED.value == "failed"
        assert TaskStatus.CANCELLED.value == "cancelled"

    def test_task_status_count(self) -> None:
        """Тест проверяет, что определены все необходимые статусы."""
        expected_statuses = {
            "PENDING",
            "IN_PROGRESS",
            "COMPLETED",
            "FAILED",
            "CANCELLED",
        }
        actual_statuses = {status.name for status in TaskStatus}
        assert actual_statuses == expected_statuses


class TestTaskProgress:
    """Тесты для TaskProgress dataclass."""

    def test_create_minimal_task_progress(self) -> None:
        """Тест создания TaskProgress с минимальными данными."""
        progress = TaskProgress(task_name="test_task")
        assert progress.task_name == "test_task"
        assert progress.status == TaskStatus.PENDING
        assert progress.total_items is None
        assert progress.processed_items == 0
        assert progress.last_processed_id is None
        assert progress.started_at is None
        assert progress.completed_at is None
        assert progress.error_message is None
        assert progress.metadata == {}

    def test_create_full_task_progress(self) -> None:
        """Тест создания TaskProgress со всеми полями."""
        started = datetime(2024, 1, 1, 10, 0, 0)
        completed = datetime(2024, 1, 1, 11, 0, 0)

        progress = TaskProgress(
            task_name="test_task",
            status=TaskStatus.COMPLETED,
            total_items=100,
            processed_items=100,
            last_processed_id="item_100",
            started_at=started,
            completed_at=completed,
            error_message=None,
            metadata={"key": "value"},
        )

        assert progress.task_name == "test_task"
        assert progress.status == TaskStatus.COMPLETED
        assert progress.total_items == 100
        assert progress.processed_items == 100
        assert progress.last_processed_id == "item_100"
        assert progress.started_at == started
        assert progress.completed_at == completed
        assert progress.error_message is None
        assert progress.metadata == {"key": "value"}

    def test_task_progress_with_failed_status(self) -> None:
        """Тест создания TaskProgress со статусом FAILED."""
        progress = TaskProgress(
            task_name="test_task",
            status=TaskStatus.FAILED,
            error_message="Test error",
        )

        assert progress.status == TaskStatus.FAILED
        assert progress.error_message == "Test error"

    def test_task_progress_negative_processed_items_raises_error(
        self,
    ) -> None:
        """Тест проверяет, что отрицательное processed_items вызывает ошибку."""
        with pytest.raises(ValueError, match="processed_items cannot be negative"):
            TaskProgress(task_name="test_task", processed_items=-1)

    def test_task_progress_negative_total_items_raises_error(self) -> None:
        """Тест проверяет, что отрицательное total_items вызывает ошибку."""
        with pytest.raises(ValueError, match="total_items cannot be negative"):
            TaskProgress(task_name="test_task", total_items=-1)

    def test_task_progress_processed_greater_than_total_raises_error(
        self,
    ) -> None:
        """Тест проверяет, что processed_items > total_items вызывает ошибку."""
        with pytest.raises(
            ValueError,
            match="processed_items cannot be greater than total_items",
        ):
            TaskProgress(
                task_name="test_task",
                total_items=10,
                processed_items=11,
            )

    def test_task_progress_processed_equals_total_allowed(self) -> None:
        """Тест проверяет, что processed_items может равняться total_items."""
        progress = TaskProgress(
            task_name="test_task",
            total_items=10,
            processed_items=10,
        )
        assert progress.processed_items == progress.total_items

    def test_task_progress_metadata_default_factory(self) -> None:
        """Тест проверяет, что metadata использует default_factory."""
        progress1 = TaskProgress(task_name="task1")
        progress2 = TaskProgress(task_name="task2")

        progress1.metadata["key1"] = "value1"
        progress2.metadata["key2"] = "value2"

        assert progress1.metadata == {"key1": "value1"}
        assert progress2.metadata == {"key2": "value2"}
        assert progress1.metadata is not progress2.metadata

    def test_task_progress_with_in_progress_status(self) -> None:
        """Тест создания TaskProgress со статусом IN_PROGRESS."""
        started = datetime(2024, 1, 1, 10, 0, 0)
        progress = TaskProgress(
            task_name="test_task",
            status=TaskStatus.IN_PROGRESS,
            total_items=50,
            processed_items=25,
            last_processed_id="item_25",
            started_at=started,
        )

        assert progress.status == TaskStatus.IN_PROGRESS
        assert progress.processed_items == 25
        assert progress.total_items == 50
        assert progress.last_processed_id == "item_25"
        assert progress.started_at == started
        assert progress.completed_at is None



