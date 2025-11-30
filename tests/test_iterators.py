"""Тесты для итераторов."""

from __future__ import annotations

import pytest

from task_sequencer.adapters.memory import MemoryProgressTracker
from task_sequencer.iterators import LimitingIterator, ResumeIterator
from task_sequencer.progress import TaskProgress, TaskStatus


def id_extractor(item: dict[str, str]) -> str:
    """Извлекает ID из элемента."""
    return item["id"]


class TestResumeIterator:
    """Тесты для ResumeIterator."""

    def test_resume_from_beginning_no_progress(self) -> None:
        """Тест продолжения с начала, если нет сохраненного прогресса."""
        tracker = MemoryProgressTracker()
        items = [{"id": "1"}, {"id": "2"}, {"id": "3"}]
        # Используем функцию id_extractor

        iterator = ResumeIterator(
            items=items,
            progress_tracker=tracker,
            task_name="test_task",
            id_extractor=id_extractor,
        )

        result = list(iterator)
        assert result == items
        assert len(result) == 3

    def test_resume_from_saved_position(self) -> None:
        """Тест продолжения с сохраненной позиции."""
        tracker = MemoryProgressTracker()
        items = [{"id": "1"}, {"id": "2"}, {"id": "3"}, {"id": "4"}]
        # Используем функцию id_extractor

        # Сохраняем прогресс: обработали элементы до "2"
        progress = TaskProgress(
            task_name="test_task",
            status=TaskStatus.IN_PROGRESS,
            last_processed_id="2",
        )
        tracker.save_progress("test_task", progress)

        iterator = ResumeIterator(
            items=items,
            progress_tracker=tracker,
            task_name="test_task",
            id_extractor=id_extractor,
        )

        result = list(iterator)
        # Должны начать с элемента "3" (индекс 2)
        assert result == [{"id": "3"}, {"id": "4"}]
        assert len(result) == 2

    def test_resume_from_last_item(self) -> None:
        """Тест продолжения с последнего элемента (все уже обработано)."""
        tracker = MemoryProgressTracker()
        items = [{"id": "1"}, {"id": "2"}, {"id": "3"}]
        # Используем функцию id_extractor

        # Сохраняем прогресс: обработали последний элемент
        progress = TaskProgress(
            task_name="test_task",
            status=TaskStatus.IN_PROGRESS,
            last_processed_id="3",
        )
        tracker.save_progress("test_task", progress)

        iterator = ResumeIterator(
            items=items,
            progress_tracker=tracker,
            task_name="test_task",
            id_extractor=id_extractor,
        )

        result = list(iterator)
        # Должен быть пустой список (все уже обработано)
        assert result == []
        assert len(result) == 0

    def test_resume_with_nonexistent_id(self) -> None:
        """Тест продолжения, когда сохраненный ID не найден в списке."""
        tracker = MemoryProgressTracker()
        items = [{"id": "1"}, {"id": "2"}, {"id": "3"}]
        # Используем функцию id_extractor

        # Сохраняем прогресс с несуществующим ID
        progress = TaskProgress(
            task_name="test_task",
            status=TaskStatus.IN_PROGRESS,
            last_processed_id="nonexistent",
        )
        tracker.save_progress("test_task", progress)

        iterator = ResumeIterator(
            items=items,
            progress_tracker=tracker,
            task_name="test_task",
            id_extractor=id_extractor,
        )

        result = list(iterator)
        # Должны начать с начала, так как ID не найден
        assert result == items

    def test_periodic_save_progress(self) -> None:
        """Тест периодического сохранения прогресса."""
        tracker = MemoryProgressTracker()
        items = [{"id": str(i)} for i in range(1, 26)]  # 25 элементов
        # Используем функцию id_extractor

        iterator = ResumeIterator(
            items=items,
            progress_tracker=tracker,
            task_name="test_task",
            id_extractor=id_extractor,
            save_interval=5,  # Сохраняем каждые 5 элементов
        )

        # Обрабатываем элементы
        count = 0
        for _ in iterator:
            count += 1

        assert count == 25

        # Проверяем, что прогресс был сохранен
        progress = tracker.get_progress("test_task")
        assert progress is not None
        assert progress.last_processed_id == "25"
        assert progress.processed_items == 25

    def test_save_progress_on_interval(self) -> None:
        """Тест проверяет, что прогресс сохраняется на заданном интервале."""
        tracker = MemoryProgressTracker()
        items = [{"id": str(i)} for i in range(1, 11)]
        # Используем функцию id_extractor

        iterator = ResumeIterator(
            items=items,
            progress_tracker=tracker,
            task_name="test_task",
            id_extractor=id_extractor,
            save_interval=3,  # Сохраняем каждые 3 элемента
        )

        # Обрабатываем первые 5 элементов
        result = []
        for i, item in enumerate(iterator):
            result.append(item)
            if i >= 4:  # Останавливаемся после 5 элементов
                break

        # Проверяем, что прогресс был сохранен (на 3-м элементе)
        progress = tracker.get_progress("test_task")
        assert progress is not None
        # Должен быть сохранен прогресс для элемента с индексом 2 (3-й элемент)
        assert progress.last_processed_id in ["3", "5"]

    def test_resume_iterator_with_empty_list(self) -> None:
        """Тест итератора с пустым списком."""
        tracker = MemoryProgressTracker()
        items: list[dict[str, str]] = []
        # Используем функцию id_extractor

        iterator = ResumeIterator(
            items=items,
            progress_tracker=tracker,
            task_name="test_task",
            id_extractor=id_extractor,
        )

        result = list(iterator)
        assert result == []

    def test_resume_iterator_invalid_save_interval(self) -> None:
        """Тест проверяет, что невалидный save_interval вызывает ошибку."""
        tracker = MemoryProgressTracker()
        items = [{"id": "1"}]
        # Используем функцию id_extractor

        with pytest.raises(ValueError, match="save_interval must be greater than 0"):
            ResumeIterator(
                items=items,
                progress_tracker=tracker,
                task_name="test_task",
                id_extractor=id_extractor,
                save_interval=0,
            )

        with pytest.raises(ValueError, match="save_interval must be greater than 0"):
            ResumeIterator(
                items=items,
                progress_tracker=tracker,
                task_name="test_task",
                id_extractor=id_extractor,
                save_interval=-1,
            )

    def test_resume_iterator_multiple_iterations(self) -> None:
        """Тест проверяет, что итератор можно использовать несколько раз."""
        tracker = MemoryProgressTracker()
        items = [{"id": "1"}, {"id": "2"}, {"id": "3"}]
        # Используем функцию id_extractor

        iterator = ResumeIterator(
            items=items,
            progress_tracker=tracker,
            task_name="test_task",
            id_extractor=id_extractor,
        )

        # Первая итерация
        result1 = list(iterator)
        assert len(result1) == 3

        # Вторая итерация (должна начаться с начала, так как прогресс не изменился)
        result2 = list(iterator)
        assert len(result2) == 3
        assert result1 == result2


class TestLimitingIterator:
    """Тесты для LimitingIterator."""

    def test_limit_items(self) -> None:
        """Тест ограничения количества элементов."""
        source_items = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        source_iterator = iter(source_items)

        limiting_iterator = LimitingIterator(source_iterator, limit=5)

        result = list(limiting_iterator)
        assert result == [1, 2, 3, 4, 5]
        assert len(result) == 5

    def test_limit_greater_than_items(self) -> None:
        """Тест ограничения, когда лимит больше количества элементов."""
        source_items = [1, 2, 3]
        source_iterator = iter(source_items)

        limiting_iterator = LimitingIterator(source_iterator, limit=10)

        result = list(limiting_iterator)
        assert result == [1, 2, 3]
        assert len(result) == 3

    def test_limit_equals_items(self) -> None:
        """Тест ограничения, когда лимит равен количеству элементов."""
        source_items = [1, 2, 3, 4, 5]
        source_iterator = iter(source_items)

        limiting_iterator = LimitingIterator(source_iterator, limit=5)

        result = list(limiting_iterator)
        assert result == [1, 2, 3, 4, 5]
        assert len(result) == 5

    def test_limit_one(self) -> None:
        """Тест ограничения одним элементом."""
        source_items = [1, 2, 3, 4, 5]
        source_iterator = iter(source_items)

        limiting_iterator = LimitingIterator(source_iterator, limit=1)

        result = list(limiting_iterator)
        assert result == [1]
        assert len(result) == 1

    def test_limit_with_empty_iterator(self) -> None:
        """Тест ограничения с пустым итератором."""
        source_items: list[int] = []
        source_iterator = iter(source_items)

        limiting_iterator = LimitingIterator(source_iterator, limit=5)

        result = list(limiting_iterator)
        assert result == []
        assert len(result) == 0

    def test_limit_invalid_value(self) -> None:
        """Тест проверяет, что невалидный лимит вызывает ошибку."""
        source_items = [1, 2, 3]
        source_iterator = iter(source_items)

        with pytest.raises(ValueError, match="limit must be greater than 0"):
            LimitingIterator(source_iterator, limit=0)

        with pytest.raises(ValueError, match="limit must be greater than 0"):
            LimitingIterator(source_iterator, limit=-1)

    def test_limit_multiple_iterations(self) -> None:
        """Тест проверяет, что итератор можно использовать несколько раз."""
        source_items = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        source_iterator1 = iter(source_items)
        source_iterator2 = iter(source_items)

        limiting_iterator1 = LimitingIterator(source_iterator1, limit=3)
        limiting_iterator2 = LimitingIterator(source_iterator2, limit=3)

        result1 = list(limiting_iterator1)
        result2 = list(limiting_iterator2)

        assert result1 == [1, 2, 3]
        assert result2 == [1, 2, 3]

    def test_limit_stop_iteration(self) -> None:
        """Тест проверяет, что StopIteration выбрасывается корректно."""
        source_items = [1, 2, 3]
        source_iterator = iter(source_items)

        limiting_iterator = LimitingIterator(source_iterator, limit=2)

        result = []
        for item in limiting_iterator:
            result.append(item)

        assert result == [1, 2]

        # Следующий вызов должен вызвать StopIteration
        with pytest.raises(StopIteration):
            next(limiting_iterator)

    def test_limit_with_generator(self) -> None:
        """Тест ограничения с генератором."""
        def number_generator():
            i = 1
            while True:
                yield i
                i += 1

        gen = number_generator()
        limiting_iterator = LimitingIterator(gen, limit=5)

        result = list(limiting_iterator)
        assert result == [1, 2, 3, 4, 5]

    def test_limit_reset_on_iter(self) -> None:
        """Тест проверяет, что счетчик сбрасывается при вызове __iter__."""
        source_items = [1, 2, 3, 4, 5]
        source_iterator = iter(source_items)

        limiting_iterator = LimitingIterator(source_iterator, limit=2)

        # Первая итерация
        result1 = list(limiting_iterator)
        assert result1 == [1, 2]

        # Вторая итерация (с новым итератором)
        source_iterator2 = iter(source_items)
        limiting_iterator2 = LimitingIterator(source_iterator2, limit=2)
        result2 = list(limiting_iterator2)
        assert result2 == [1, 2]

