"""MongoDB адаптер для трекера прогресса."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime
from typing import ContextManager

try:
    from pymongo import MongoClient
    from pymongo.collection import Collection
    from pymongo.database import Database
except ImportError as e:
    raise ImportError(
        "MongoDB adapter requires 'pymongo'. "
        "Install it with: pip install task-sequencer[mongodb]"
    ) from e

from task_sequencer.exceptions import ProgressError
from task_sequencer.interfaces import ProgressTracker
from task_sequencer.progress import TaskProgress, TaskStatus


class MongoDBProgressTracker(ProgressTracker):
    """Трекер прогресса, хранящий данные в MongoDB.

    Использует pymongo для работы с базой данных MongoDB.
    Требует установки опциональной зависимости: pymongo.

    Attributes:
        client: MongoDB client
        database: База данных MongoDB
        collection: Коллекция для хранения прогресса
    """

    def __init__(
        self,
        connection_string: str,
        database_name: str | None = None,
        collection_name: str = "task_progress",
    ) -> None:
        """Инициализирует трекер прогресса для MongoDB.

        Args:
            connection_string: Строка подключения к MongoDB
                Формат: `mongodb://[username:password@]host[:port][/database]`
                
                **Улучшение**: Если `database_name` не указан, автоматически извлекается
                из connection string (если присутствует). Это упрощает использование:
                - `mongodb://user:pass@host:27017/task_sequencer` - БД извлечется автоматически
                - `mongodb://localhost:27017/` - используется значение по умолчанию
                
            database_name: Имя базы данных для выбора БД после подключения.
                Если `None`, пытается извлечь из connection string.
                Если не найдено в connection string, используется `"task_sequencer"` по умолчанию.
                По умолчанию: `None` (автоматическое определение).
                
            collection_name: Имя коллекции для хранения прогресса.
                По умолчанию: `"task_progress"`.

        Raises:
            ImportError: Если не установлен pymongo. Установите: `pip install task-sequencer[mongodb]`
            ProgressError: Если не удалось подключиться к БД

        Примеры:
            >>> # Автоматическое извлечение database_name из connection string
            >>> tracker = MongoDBProgressTracker(
            ...     connection_string="mongodb://user:pass@host:27017/task_sequencer"
            ...     # database_name извлечется автоматически
            ... )
            >>>
            >>> # Явное указание database_name (приоритет над connection string)
            >>> tracker = MongoDBProgressTracker(
            ...     connection_string="mongodb://localhost:27017/",
            ...     database_name="my_database"
            ... )
            >>>
            >>> # Без database в connection string - используется значение по умолчанию
            >>> tracker = MongoDBProgressTracker(
            ...     connection_string="mongodb://localhost:27017/"
            ...     # database_name будет "task_sequencer" по умолчанию
            ... )
        """
        try:
            # Извлекаем database_name из connection string, если не указан явно
            if database_name is None:
                database_name = self._extract_database_name(connection_string)
                if database_name is None:
                    database_name = "task_sequencer"  # Значение по умолчанию

            self.client = MongoClient(connection_string)
            self.database: Database = self.client[database_name]
            self.collection: Collection = self.database[collection_name]

            # Создаем индекс по task_name для быстрого поиска
            self.collection.create_index("task_name", unique=True)
        except Exception as e:
            raise ProgressError(f"Failed to initialize MongoDB connection: {e}") from e

    @staticmethod
    def _extract_database_name(connection_string: str) -> str | None:
        """Извлекает имя базы данных из connection string.

        Args:
            connection_string: Строка подключения MongoDB

        Returns:
            Имя базы данных или None, если не найдено
        """
        # Формат: mongodb://[username:password@]host[:port][/database]
        # Ищем последний слэш после порта
        try:
            # Разбираем URL
            from urllib.parse import urlparse

            parsed = urlparse(connection_string)
            # Путь после слэша содержит имя БД
            if parsed.path and len(parsed.path) > 1:
                # Убираем ведущий слэш
                db_name = parsed.path.lstrip("/")
                # Убираем параметры запроса, если есть
                if "?" in db_name:
                    db_name = db_name.split("?")[0]
                if db_name:
                    return db_name
        except Exception:
            # Если не удалось разобрать, возвращаем None
            pass
        return None

    def save_progress(
        self, task_name: str, progress: TaskProgress
    ) -> None:
        """Сохраняет прогресс выполнения задачи.

        Args:
            task_name: Имя задачи
            progress: Информация о прогрессе

        Raises:
            ProgressError: Если не удалось сохранить прогресс
        """
        if not task_name:
            raise ProgressError("Task name cannot be empty")

        if progress.task_name != task_name:
            raise ProgressError(
                f"Task name mismatch: expected '{task_name}', "
                f"got '{progress.task_name}'"
            )

        try:
            # Преобразуем TaskProgress в словарь для MongoDB
            doc = {
                "task_name": task_name,
                "status": progress.status.value,
                "total_items": progress.total_items,
                "processed_items": progress.processed_items,
                "last_processed_id": progress.last_processed_id,
                "started_at": (
                    progress.started_at.isoformat() if progress.started_at else None
                ),
                "completed_at": (
                    progress.completed_at.isoformat() if progress.completed_at else None
                ),
                "error_message": progress.error_message,
                "metadata": progress.metadata,
            }

            # Используем upsert для обновления существующей записи или создания новой
            self.collection.update_one(
                {"task_name": task_name}, {"$set": doc}, upsert=True
            )
        except Exception as e:
            raise ProgressError(f"Failed to save progress: {e}") from e

    def get_progress(self, task_name: str) -> TaskProgress | None:
        """Получает сохраненный прогресс выполнения задачи.

        Args:
            task_name: Имя задачи

        Returns:
            TaskProgress или None, если прогресс не найден

        Raises:
            ProgressError: Если произошла ошибка при загрузке прогресса
        """
        if not task_name:
            raise ProgressError("Task name cannot be empty")

        try:
            doc = self.collection.find_one({"task_name": task_name})

            if doc is None:
                return None

            # Преобразуем документ MongoDB в TaskProgress
            from datetime import datetime

            started_at = None
            if doc.get("started_at"):
                started_at = datetime.fromisoformat(doc["started_at"])

            completed_at = None
            if doc.get("completed_at"):
                completed_at = datetime.fromisoformat(doc["completed_at"])

            return TaskProgress(
                task_name=doc["task_name"],
                status=TaskStatus(doc["status"]),
                total_items=doc.get("total_items"),
                processed_items=doc.get("processed_items", 0),
                last_processed_id=doc.get("last_processed_id"),
                started_at=started_at,
                completed_at=completed_at,
                error_message=doc.get("error_message"),
                metadata=doc.get("metadata", {}),
            )
        except Exception as e:
            raise ProgressError(f"Failed to get progress: {e}") from e

    def mark_completed(self, task_name: str) -> None:
        """Отмечает задачу как завершенную.

        Args:
            task_name: Имя задачи

        Raises:
            ProgressError: Если не удалось обновить статус
        """
        if not task_name:
            raise ProgressError("Task name cannot be empty")

        try:
            now = datetime.now()
            update_doc = {
                "$set": {
                    "status": TaskStatus.COMPLETED.value,
                    "completed_at": now.isoformat(),
                }
            }

            # Если started_at не установлен, устанавливаем его
            existing = self.collection.find_one({"task_name": task_name})
            if existing is None or not existing.get("started_at"):
                update_doc["$set"]["started_at"] = now.isoformat()

            self.collection.update_one(
                {"task_name": task_name}, update_doc, upsert=True
            )
        except Exception as e:
            raise ProgressError(f"Failed to mark task as completed: {e}") from e

    def clear_progress(self, task_name: str) -> None:
        """Очищает сохраненный прогресс задачи.

        Args:
            task_name: Имя задачи

        Raises:
            ProgressError: Если не удалось очистить прогресс
        """
        if not task_name:
            raise ProgressError("Task name cannot be empty")

        try:
            self.collection.delete_one({"task_name": task_name})
        except Exception as e:
            raise ProgressError(f"Failed to clear progress: {e}") from e

    @contextmanager
    def transaction(self) -> ContextManager[None]:
        """Создает изолированную транзакцию для сохранения прогресса.

        MongoDB поддерживает транзакции начиная с версии 4.0.
        Для более старых версий это заглушка.

        Returns:
            Контекстный менеджер для транзакции
        """
        # MongoDB транзакции требуют replica set или sharded cluster
        # Для простоты используем заглушку, которая просто выполняет операции
        # В реальном использовании можно добавить поддержку транзакций через
        # client.start_session() и session.with_transaction()
        yield

    def close(self) -> None:
        """Закрывает соединение с MongoDB."""
        if hasattr(self, "client"):
            self.client.close()

