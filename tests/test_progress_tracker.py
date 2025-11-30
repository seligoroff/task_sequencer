"""Тесты для трекеров прогресса."""

from __future__ import annotations

from datetime import datetime

import pytest

from task_sequencer.adapters.memory import MemoryProgressTracker
from task_sequencer.exceptions import ProgressError
from task_sequencer.progress import TaskProgress, TaskStatus


class TestMemoryProgressTracker:
    """Тесты для MemoryProgressTracker."""

    def test_create_tracker(self) -> None:
        """Тест создания трекера прогресса."""
        tracker = MemoryProgressTracker()
        assert tracker._storage == {}

    def test_save_progress(self) -> None:
        """Тест сохранения прогресса."""
        tracker = MemoryProgressTracker()
        progress = TaskProgress(
            task_name="test_task",
            status=TaskStatus.IN_PROGRESS,
            processed_items=5,
            total_items=10,
        )

        tracker.save_progress("test_task", progress)
        assert "test_task" in tracker._storage
        assert tracker._storage["test_task"] == progress

    def test_get_progress_existing(self) -> None:
        """Тест получения существующего прогресса."""
        tracker = MemoryProgressTracker()
        progress = TaskProgress(
            task_name="test_task", status=TaskStatus.IN_PROGRESS
        )
        tracker.save_progress("test_task", progress)

        retrieved = tracker.get_progress("test_task")
        assert retrieved is not None
        assert retrieved.task_name == "test_task"
        assert retrieved.status == TaskStatus.IN_PROGRESS

    def test_get_progress_nonexistent(self) -> None:
        """Тест получения несуществующего прогресса."""
        tracker = MemoryProgressTracker()
        result = tracker.get_progress("nonexistent_task")
        assert result is None

    def test_get_progress_returns_copy(self) -> None:
        """Тест проверяет, что get_progress возвращает тот же объект (не копию)."""
        tracker = MemoryProgressTracker()
        progress = TaskProgress(
            task_name="test_task", status=TaskStatus.IN_PROGRESS
        )
        tracker.save_progress("test_task", progress)

        retrieved1 = tracker.get_progress("test_task")
        retrieved2 = tracker.get_progress("test_task")

        # Должны быть одним и тем же объектом
        assert retrieved1 is retrieved2
        assert retrieved1 is progress

    def test_mark_completed_existing_progress(self) -> None:
        """Тест отметки завершения для существующего прогресса."""
        tracker = MemoryProgressTracker()
        started_at = datetime(2024, 1, 1, 10, 0, 0)
        progress = TaskProgress(
            task_name="test_task",
            status=TaskStatus.IN_PROGRESS,
            started_at=started_at,
        )
        tracker.save_progress("test_task", progress)

        tracker.mark_completed("test_task")

        updated = tracker.get_progress("test_task")
        assert updated is not None
        assert updated.status == TaskStatus.COMPLETED
        assert updated.completed_at is not None
        assert updated.started_at == started_at  # Не изменяется

    def test_mark_completed_nonexistent_progress(self) -> None:
        """Тест отметки завершения для несуществующего прогресса."""
        tracker = MemoryProgressTracker()

        tracker.mark_completed("test_task")

        progress = tracker.get_progress("test_task")
        assert progress is not None
        assert progress.task_name == "test_task"
        assert progress.status == TaskStatus.COMPLETED
        assert progress.completed_at is not None
        assert progress.started_at is not None

    def test_clear_progress_existing(self) -> None:
        """Тест очистки существующего прогресса."""
        tracker = MemoryProgressTracker()
        progress = TaskProgress(
            task_name="test_task", status=TaskStatus.IN_PROGRESS
        )
        tracker.save_progress("test_task", progress)

        tracker.clear_progress("test_task")

        assert "test_task" not in tracker._storage
        assert tracker.get_progress("test_task") is None

    def test_clear_progress_nonexistent(self) -> None:
        """Тест очистки несуществующего прогресса (не должно быть ошибки)."""
        tracker = MemoryProgressTracker()

        # Не должно быть ошибки
        tracker.clear_progress("nonexistent_task")
        assert tracker.get_progress("nonexistent_task") is None

    def test_save_multiple_tasks(self) -> None:
        """Тест сохранения прогресса для нескольких задач."""
        tracker = MemoryProgressTracker()

        progress1 = TaskProgress(
            task_name="task1", status=TaskStatus.IN_PROGRESS
        )
        progress2 = TaskProgress(
            task_name="task2", status=TaskStatus.COMPLETED
        )

        tracker.save_progress("task1", progress1)
        tracker.save_progress("task2", progress2)

        assert len(tracker._storage) == 2
        assert tracker.get_progress("task1").status == TaskStatus.IN_PROGRESS
        assert tracker.get_progress("task2").status == TaskStatus.COMPLETED

    def test_update_progress(self) -> None:
        """Тест обновления существующего прогресса."""
        tracker = MemoryProgressTracker()

        progress1 = TaskProgress(
            task_name="test_task",
            status=TaskStatus.IN_PROGRESS,
            processed_items=5,
        )
        tracker.save_progress("test_task", progress1)

        progress2 = TaskProgress(
            task_name="test_task",
            status=TaskStatus.IN_PROGRESS,
            processed_items=10,
        )
        tracker.save_progress("test_task", progress2)

        retrieved = tracker.get_progress("test_task")
        assert retrieved.processed_items == 10

    def test_save_progress_empty_task_name_raises_error(self) -> None:
        """Тест проверяет, что сохранение с пустым именем задачи вызывает ошибку."""
        tracker = MemoryProgressTracker()
        progress = TaskProgress(task_name="", status=TaskStatus.PENDING)

        with pytest.raises(ProgressError, match="Task name cannot be empty"):
            tracker.save_progress("", progress)

    def test_get_progress_empty_task_name_raises_error(self) -> None:
        """Тест проверяет, что получение с пустым именем задачи вызывает ошибку."""
        tracker = MemoryProgressTracker()

        with pytest.raises(ProgressError, match="Task name cannot be empty"):
            tracker.get_progress("")

    def test_mark_completed_empty_task_name_raises_error(self) -> None:
        """Тест проверяет, что отметка завершения с пустым именем вызывает ошибку."""
        tracker = MemoryProgressTracker()

        with pytest.raises(ProgressError, match="Task name cannot be empty"):
            tracker.mark_completed("")

    def test_clear_progress_empty_task_name_raises_error(self) -> None:
        """Тест проверяет, что очистка с пустым именем задачи вызывает ошибку."""
        tracker = MemoryProgressTracker()

        with pytest.raises(ProgressError, match="Task name cannot be empty"):
            tracker.clear_progress("")

    def test_save_progress_task_name_mismatch_raises_error(self) -> None:
        """Тест проверяет, что несоответствие имен вызывает ошибку."""
        tracker = MemoryProgressTracker()
        progress = TaskProgress(
            task_name="task1", status=TaskStatus.IN_PROGRESS
        )

        with pytest.raises(
            ProgressError, match="Task name mismatch"
        ):
            tracker.save_progress("task2", progress)

    def test_mark_completed_sets_timestamps(self) -> None:
        """Тест проверяет, что mark_completed устанавливает временные метки."""
        tracker = MemoryProgressTracker()

        tracker.mark_completed("test_task")

        progress = tracker.get_progress("test_task")
        assert progress is not None
        assert progress.completed_at is not None
        assert progress.started_at is not None
        assert isinstance(progress.completed_at, datetime)
        assert isinstance(progress.started_at, datetime)

    def test_full_lifecycle(self) -> None:
        """Тест полного жизненного цикла прогресса."""
        tracker = MemoryProgressTracker()

        # Создание прогресса
        progress = TaskProgress(
            task_name="test_task",
            status=TaskStatus.IN_PROGRESS,
            processed_items=5,
            total_items=10,
        )
        tracker.save_progress("test_task", progress)

        # Обновление прогресса
        progress.processed_items = 8
        tracker.save_progress("test_task", progress)

        # Отметка завершения
        tracker.mark_completed("test_task")

        # Проверка
        final = tracker.get_progress("test_task")
        assert final is not None
        assert final.status == TaskStatus.COMPLETED
        assert final.processed_items == 8

        # Очистка
        tracker.clear_progress("test_task")
        assert tracker.get_progress("test_task") is None

    def test_save_progress_exception_handling(self) -> None:
        """Тест обработки исключений при сохранении прогресса."""
        tracker = MemoryProgressTracker()

        # Создаем mock-объект, который выбрасывает исключение при присваивании
        class FailingDict(dict):
            def __setitem__(self, key, value):
                raise RuntimeError("Storage error")

        tracker._storage = FailingDict()
        progress = TaskProgress(
            task_name="test_task", status=TaskStatus.IN_PROGRESS
        )

        with pytest.raises(ProgressError, match="Failed to save progress"):
            tracker.save_progress("test_task", progress)

    def test_get_progress_exception_handling(self) -> None:
        """Тест обработки исключений при получении прогресса."""
        tracker = MemoryProgressTracker()

        # Создаем mock-объект, который выбрасывает исключение при get
        class FailingDict(dict):
            def get(self, key, default=None):
                raise RuntimeError("Storage error")

        tracker._storage = FailingDict()

        with pytest.raises(ProgressError, match="Failed to get progress"):
            tracker.get_progress("test_task")

    def test_mark_completed_exception_handling(self) -> None:
        """Тест обработки исключений при отметке завершения."""
        tracker = MemoryProgressTracker()

        # Создаем mock-объект, который выбрасывает исключение
        class FailingDict(dict):
            def get(self, key, default=None):
                raise RuntimeError("Storage error")

        tracker._storage = FailingDict()

        with pytest.raises(
            ProgressError, match="Failed to mark task as completed"
        ):
            tracker.mark_completed("test_task")

    def test_clear_progress_exception_handling(self) -> None:
        """Тест обработки исключений при очистке прогресса."""
        tracker = MemoryProgressTracker()
        progress = TaskProgress(
            task_name="test_task", status=TaskStatus.IN_PROGRESS
        )
        tracker.save_progress("test_task", progress)

        # Создаем mock-объект, который выбрасывает исключение при удалении
        class FailingDict(dict):
            def __delitem__(self, key):
                raise RuntimeError("Storage error")

        tracker._storage = FailingDict({"test_task": progress})

        with pytest.raises(ProgressError, match="Failed to clear progress"):
            tracker.clear_progress("test_task")

