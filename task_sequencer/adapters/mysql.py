"""MySQL адаптер для трекера прогресса."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime
from typing import ContextManager

try:
    from sqlalchemy import (
        Column,
        DateTime,
        Integer,
        String,
        Text,
        create_engine,
        select,
    )
    from sqlalchemy.orm import declarative_base, sessionmaker
except ImportError as e:
    raise ImportError(
        "MySQL adapter requires 'sqlalchemy' and 'pymysql'. "
        "Install it with: pip install task-sequencer[mysql]"
    ) from e

from task_sequencer.exceptions import ProgressError
from task_sequencer.interfaces import ProgressTracker
from task_sequencer.progress import TaskProgress, TaskStatus

Base = declarative_base()


# Статическая модель для обратной совместимости (используется по умолчанию)
class TaskProgressModel(Base):  # type: ignore[misc,valid-type]
    """Модель SQLAlchemy для хранения прогресса задач."""

    __tablename__ = "task_progress"

    task_name = Column(String(255), primary_key=True)
    status = Column(String(50), nullable=False)
    total_items = Column(Integer, nullable=True)
    processed_items = Column(Integer, default=0, nullable=False)
    last_processed_id = Column(String(255), nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    metadata_json = Column(Text, nullable=True)


def create_task_progress_model(table_name: str = "task_progress"):
    """Создает модель TaskProgressModel с указанным именем таблицы.

    Args:
        table_name: Имя таблицы для модели

    Returns:
        Класс модели SQLAlchemy
    """
    class DynamicTaskProgressModel(Base):  # type: ignore[misc,valid-type]
        """Модель SQLAlchemy для хранения прогресса задач (динамическая)."""

        __tablename__ = table_name

        task_name = Column(String(255), primary_key=True)
        status = Column(String(50), nullable=False)
        total_items = Column(Integer, nullable=True)
        processed_items = Column(Integer, default=0, nullable=False)
        last_processed_id = Column(String(255), nullable=True)
        started_at = Column(DateTime, nullable=True)
        completed_at = Column(DateTime, nullable=True)
        error_message = Column(Text, nullable=True)
        metadata_json = Column(Text, nullable=True)

    return DynamicTaskProgressModel


class MySQLProgressTracker(ProgressTracker):
    """Трекер прогресса, хранящий данные в MySQL.

    Использует SQLAlchemy для работы с базой данных MySQL.
    Требует установки опциональных зависимостей: sqlalchemy и pymysql.

    Attributes:
        engine: SQLAlchemy engine для подключения к БД
        session_factory: Фабрика сессий SQLAlchemy
    """

    def __init__(
        self,
        connection_string: str,
        create_tables: bool = True,
        database_name: str | None = None,
        table_name: str | None = None,
    ) -> None:
        """Инициализирует трекер прогресса для MySQL.

        Args:
            connection_string: Строка подключения к MySQL в формате SQLAlchemy.
                Формат: `mysql+pymysql://user:password@host:port[/database]`
                
                **Улучшение**: Если `database_name` указан, он будет использован вместо
                значения из connection string. Это упрощает использование:
                - `mysql+pymysql://user:pass@host:3306/` + `database_name="my_db"`
                - `mysql+pymysql://user:pass@host:3306/task_sequencer` (БД в connection string)
                
                Примеры:
                - `mysql+pymysql://user:pass@localhost:3306/task_sequencer`
                - `mysql+pymysql://user:pass@host:3306/` (с database_name параметром)
                
            create_tables: Если `True`, автоматически создает таблицу при инициализации.
                Если `False`, предполагается, что таблица уже существует.
                По умолчанию: `True`.
                
            database_name: Имя базы данных (опционально).
                Если указан, используется вместо значения из connection string.
                Если `None`, используется значение из connection string.
                По умолчанию: `None`.
                
            table_name: Имя таблицы для хранения прогресса (опционально).
                Если указан, используется вместо `"task_progress"`.
                Если `None`, используется `"task_progress"`.
                По умолчанию: `None`.

        Raises:
            ImportError: Если не установлены sqlalchemy или pymysql.
                Установите: `pip install task-sequencer[mysql]`
            ProgressError: Если не удалось подключиться к БД

        Примеры:
            >>> # С database_name и table_name в connection string (старый способ)
            >>> tracker = MySQLProgressTracker(
            ...     connection_string="mysql+pymysql://user:pass@localhost:3306/task_sequencer",
            ...     create_tables=True
            ... )
            >>>
            >>> # С явным указанием database_name и table_name (новый способ)
            >>> tracker = MySQLProgressTracker(
            ...     connection_string="mysql+pymysql://user:pass@localhost:3306/",
            ...     database_name="task_sequencer",
            ...     table_name="my_progress",
            ...     create_tables=True
            ... )
            >>>
            >>> # Без создания таблиц
            >>> tracker = MySQLProgressTracker(
            ...     connection_string="mysql+pymysql://user:pass@localhost:3306/task_sequencer",
            ...     create_tables=False
            ... )
        """
        try:
            # Если указан database_name, модифицируем connection string
            if database_name:
                connection_string = self._update_connection_string_database(
                    connection_string, database_name
                )

            self.engine = create_engine(connection_string, echo=False)
            self.session_factory = sessionmaker(bind=self.engine)
            self._session = None  # Текущая сессия для транзакций

            # Определяем имя таблицы
            self.table_name = table_name or "task_progress"

            # Создаем модель с нужным именем таблицы
            if table_name and table_name != "task_progress":
                # Используем динамическую модель только если имя таблицы отличается от дефолтного
                self.TaskProgressModel = create_task_progress_model(self.table_name)
                self._use_dynamic_model = True
            else:
                # Используем статическую модель для обратной совместимости
                self.TaskProgressModel = TaskProgressModel
                self._use_dynamic_model = False

            if create_tables:
                # Для обратной совместимости используем Base.metadata.create_all для статической модели
                if self._use_dynamic_model:
                    self.TaskProgressModel.__table__.create(self.engine, checkfirst=True)
                else:
                    Base.metadata.create_all(self.engine)
        except Exception as e:
            raise ProgressError(f"Failed to initialize MySQL connection: {e}") from e

    @staticmethod
    def _update_connection_string_database(
        connection_string: str, database_name: str
    ) -> str:
        """Обновляет имя базы данных в connection string.

        Args:
            connection_string: Исходная строка подключения
            database_name: Новое имя базы данных

        Returns:
            Обновленная строка подключения
        """
        from urllib.parse import urlparse, urlunparse

        parsed = urlparse(connection_string)
        # Заменяем путь (последний компонент после слэша)
        new_path = f"/{database_name}"
        updated = parsed._replace(path=new_path)
        return urlunparse(updated)

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
            session = self._session if self._session else self.session_factory()
            try:
                import json

                # Преобразуем TaskProgress в модель
                model = self.TaskProgressModel(
                    task_name=task_name,
                    status=progress.status.value,
                    total_items=progress.total_items,
                    processed_items=progress.processed_items,
                    last_processed_id=progress.last_processed_id,
                    started_at=progress.started_at,
                    completed_at=progress.completed_at,
                    error_message=progress.error_message,
                    metadata_json=json.dumps(progress.metadata) if progress.metadata else None,
                )

                # Используем merge для обновления существующей записи или создания новой
                session.merge(model)
                if not self._session:
                    session.commit()
            finally:
                if not self._session:
                    session.close()
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
            session = self._session if self._session else self.session_factory()
            try:
                stmt = select(self.TaskProgressModel).where(
                    self.TaskProgressModel.task_name == task_name
                )
                result = session.execute(stmt).scalar_one_or_none()

                if result is None:
                    return None

                # Преобразуем модель в TaskProgress
                import json

                return TaskProgress(
                    task_name=result.task_name,
                    status=TaskStatus(result.status),
                    total_items=result.total_items,
                    processed_items=result.processed_items,
                    last_processed_id=result.last_processed_id,
                    started_at=result.started_at,
                    completed_at=result.completed_at,
                    error_message=result.error_message,
                    metadata=json.loads(result.metadata_json) if result.metadata_json else {},
                )
            finally:
                if not self._session:
                    session.close()
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
            session = self._session if self._session else self.session_factory()
            try:
                stmt = select(self.TaskProgressModel).where(
                    self.TaskProgressModel.task_name == task_name
                )
                model = session.execute(stmt).scalar_one_or_none()

                now = datetime.now()
                if model is None:
                    # Создаем новый прогресс, если его нет
                    model = self.TaskProgressModel(
                        task_name=task_name,
                        status=TaskStatus.COMPLETED.value,
                        started_at=now,
                        completed_at=now,
                    )
                    session.add(model)
                else:
                    # Обновляем существующий прогресс
                    model.status = TaskStatus.COMPLETED.value
                    model.completed_at = now
                    if model.started_at is None:
                        model.started_at = now

                if not self._session:
                    session.commit()
            finally:
                if not self._session:
                    session.close()
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
            session = self._session if self._session else self.session_factory()
            try:
                stmt = select(self.TaskProgressModel).where(
                    self.TaskProgressModel.task_name == task_name
                )
                model = session.execute(stmt).scalar_one_or_none()

                if model is not None:
                    session.delete(model)
                    if not self._session:
                        session.commit()
            finally:
                if not self._session:
                    session.close()
        except Exception as e:
            raise ProgressError(f"Failed to clear progress: {e}") from e

    @contextmanager
    def transaction(self) -> ContextManager[None]:
        """Создает изолированную транзакцию для сохранения прогресса.

        Returns:
            Контекстный менеджер для транзакции
        """
        fresh_session = self.session_factory()
        old_session = self._session
        self._session = fresh_session
        try:
            with fresh_session.begin():
                yield
        finally:
            self._session = old_session
            fresh_session.close()

