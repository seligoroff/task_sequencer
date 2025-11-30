"""Итераторы для работы с итеративными задачами."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import Any

from task_sequencer.interfaces import ProgressTracker
from task_sequencer.progress import TaskProgress, TaskStatus


class ResumeIterator:
    """Итератор для продолжения обработки с места остановки.

    Определяет начальный индекс на основе сохраненного прогресса
    и периодически сохраняет прогресс обработки.

    Attributes:
        items: Список элементов для обработки
        progress_tracker: Трекер прогресса для сохранения состояния
        task_name: Имя задачи
        id_extractor: Функция для извлечения ID из элемента
        save_interval: Интервал сохранения прогресса (каждые N элементов)
        _current_index: Текущий индекс в списке элементов
        _start_index: Начальный индекс (определяется из прогресса)
    """

    def __init__(
        self,
        items: list[Any],
        progress_tracker: ProgressTracker,
        task_name: str,
        id_extractor: Callable[[Any], str],
        save_interval: int = 10,
    ) -> None:
        """Инициализирует итератор для продолжения обработки.

        Args:
            items: Список элементов для обработки
            progress_tracker: Трекер прогресса
            task_name: Имя задачи
            id_extractor: Функция для извлечения ID из элемента
            save_interval: Интервал сохранения прогресса (по умолчанию 10)

        Raises:
            ValueError: Если save_interval <= 0
        """
        if save_interval <= 0:
            raise ValueError("save_interval must be greater than 0")

        self.items = items
        self.progress_tracker = progress_tracker
        self.task_name = task_name
        self.id_extractor = id_extractor
        self.save_interval = save_interval
        self._current_index = 0
        self._start_index = self._find_start_index()

    def __iter__(self) -> Iterator[Any]:
        """Возвращает итератор, начиная с сохраненной позиции.

        Returns:
            Итератор элементов, начиная с _start_index
        """
        self._current_index = self._start_index
        return self

    def __next__(self) -> Any:
        """Возвращает следующий элемент.

        Returns:
            Следующий элемент из списка

        Raises:
            StopIteration: Если достигнут конец списка
        """
        if self._current_index >= len(self.items):
            raise StopIteration

        item = self.items[self._current_index]
        self._current_index += 1

        # Периодически сохраняем прогресс
        if (self._current_index - self._start_index) % self.save_interval == 0:
            self._save_progress(self._current_index - 1)

        return item

    def _find_start_index(self) -> int:
        """Определяет начальный индекс на основе сохраненного прогресса.

        Returns:
            Индекс элемента, с которого нужно начать обработку
        """
        progress = self.progress_tracker.get_progress(self.task_name)

        if progress is None or progress.last_processed_id is None:
            return 0

        last_id = progress.last_processed_id

        # Ищем элемент с таким ID
        for i, item in enumerate(self.items):
            item_id = self.id_extractor(item)
            if item_id == last_id:
                # Начинаем со следующего элемента
                return i + 1

        # Если элемент не найден, начинаем с начала
        return 0

    def _save_progress(self, index: int) -> None:
        """Сохраняет текущий прогресс обработки.

        Args:
            index: Индекс последнего обработанного элемента
        """
        if index < 0 or index >= len(self.items):
            return

        item = self.items[index]
        item_id = self.id_extractor(item)

        progress = TaskProgress(
            task_name=self.task_name,
            status=TaskStatus.IN_PROGRESS,
            total_items=len(self.items),
            processed_items=index + 1,
            last_processed_id=item_id,
        )

        self.progress_tracker.save_progress(self.task_name, progress)


class LimitingIterator:
    """Итератор для ограничения количества обрабатываемых элементов.

    Останавливается при достижении указанного лимита элементов.

    Attributes:
        iterator: Исходный итератор
        limit: Максимальное количество элементов для обработки
        _count: Текущее количество обработанных элементов
    """

    def __init__(self, iterator: Iterator[Any], limit: int) -> None:
        """Инициализирует ограничивающий итератор.

        Args:
            iterator: Исходный итератор
            limit: Максимальное количество элементов для обработки

        Raises:
            ValueError: Если limit <= 0
        """
        if limit <= 0:
            raise ValueError("limit must be greater than 0")

        self.iterator = iterator
        self.limit = limit
        self._count = 0

    def __iter__(self) -> Iterator[Any]:
        """Возвращает итератор.

        Returns:
            Сам итератор
        """
        self._count = 0
        return self

    def __next__(self) -> Any:
        """Возвращает следующий элемент до достижения лимита.

        Returns:
            Следующий элемент из исходного итератора

        Raises:
            StopIteration: Если достигнут лимит или конец исходного итератора
        """
        if self._count >= self.limit:
            raise StopIteration

        try:
            item = next(self.iterator)
            self._count += 1
            return item
        except StopIteration:
            # Достигнут конец исходного итератора
            raise


