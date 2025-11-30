"""PostgreSQL адаптер для трекера прогресса."""

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
        "PostgreSQL adapter requires 'sqlalchemy' and 'psycopg2-binary'. "
        "Install it with: pip install task-sequencer[postgresql]"
    ) from e

from task_sequencer.exceptions import ProgressError
from task_sequencer.interfaces import ProgressTracker
from task_sequencer.progress import TaskProgress, TaskStatus

Base = declarative_base()


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


class PostgreSQLProgressTracker(ProgressTracker):
    """Трекер прогресса, хранящий данные в PostgreSQL.

    Использует SQLAlchemy для работы с базой данных PostgreSQL.
    Требует установки опциональных зависимостей: sqlalchemy и psycopg2-binary.

    Attributes:
        engine: SQLAlchemy engine для подключения к БД
        session_factory: Фабрика сессий SQLAlchemy
    """

    def __init__(self, connection_string: str, create_tables: bool = True) -> None:
        """Инициализирует трекер прогресса для PostgreSQL.

        Args:
            connection_string: Строка подключения к PostgreSQL в формате SQLAlchemy.
                Формат: `postgresql+psycopg2://user:password@host:port/database`
                
                **Важно**: Имя базы данных и таблицы указываются в connection string.
                Таблица `task_progress` создается автоматически при `create_tables=True`.
                
                Примеры:
                - `postgresql+psycopg2://user:pass@localhost:5432/task_sequencer`
                - `postgresql+psycopg2://user:pass@host:5432/my_database`
                
            create_tables: Если `True`, автоматически создает таблицу `task_progress`
                при инициализации. Если `False`, предполагается, что таблица уже существует.
                По умолчанию: `True`.

        Raises:
            ImportError: Если не установлены sqlalchemy или psycopg2-binary.
                Установите: `pip install task-sequencer[postgresql]`
            ProgressError: Если не удалось подключиться к БД

        Примеры:
            >>> # С автоматическим созданием таблиц
            >>> tracker = PostgreSQLProgressTracker(
            ...     connection_string="postgresql+psycopg2://user:pass@localhost:5432/task_sequencer",
            ...     create_tables=True
            ... )
            >>>
            >>> # Без создания таблиц (если таблицы уже существуют)
            >>> tracker = PostgreSQLProgressTracker(
            ...     connection_string="postgresql+psycopg2://user:pass@localhost:5432/task_sequencer",
            ...     create_tables=False
            ... )
            
        Примечание:
            Параметры `database_name` и `table_name` не поддерживаются.
            Укажите имя БД в connection string, имя таблицы фиксировано как `task_progress`.
        """
        try:
            self.engine = create_engine(connection_string, echo=False)
            self.session_factory = sessionmaker(bind=self.engine)
            self._session = None  # Текущая сессия для транзакций

            if create_tables:
                Base.metadata.create_all(self.engine)
        except Exception as e:
            raise ProgressError(f"Failed to initialize PostgreSQL connection: {e}") from e

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
                model = TaskProgressModel(
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
                stmt = select(TaskProgressModel).where(
                    TaskProgressModel.task_name == task_name
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
                stmt = select(TaskProgressModel).where(
                    TaskProgressModel.task_name == task_name
                )
                model = session.execute(stmt).scalar_one_or_none()

                now = datetime.now()
                if model is None:
                    # Создаем новый прогресс, если его нет
                    model = TaskProgressModel(
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
                stmt = select(TaskProgressModel).where(
                    TaskProgressModel.task_name == task_name
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

