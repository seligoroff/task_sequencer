"""Тесты для адаптеров трекеров прогресса."""

from __future__ import annotations

import sys
from datetime import datetime
from unittest.mock import MagicMock, Mock, patch

import pytest

from task_sequencer.exceptions import ProgressError
from task_sequencer.progress import TaskProgress, TaskStatus


def mock_sqlalchemy_dependencies():
    """Мокает зависимости SQLAlchemy для тестирования."""
    # Создаем класс для TaskProgressModel
    class MockTaskProgressModel:
        task_name = None

    mock_sqlalchemy = MagicMock()
    mock_sqlalchemy.create_engine = Mock()
    mock_sqlalchemy.Column = Mock()
    mock_sqlalchemy.String = Mock()
    mock_sqlalchemy.Integer = Mock()
    mock_sqlalchemy.DateTime = Mock()
    mock_sqlalchemy.Text = Mock()
    mock_sqlalchemy.select = Mock(return_value=Mock())
    # Мокаем select() чтобы он возвращал объект с where()
    mock_select_obj = Mock()
    mock_select_obj.where = Mock(return_value=mock_select_obj)
    mock_sqlalchemy.select = Mock(return_value=mock_select_obj)
    # Сохраняем класс модели
    mock_sqlalchemy._TaskProgressModel = MockTaskProgressModel

    mock_orm = MagicMock()
    mock_orm.Session = Mock()
    mock_orm.sessionmaker = Mock()
    mock_base = MagicMock()
    mock_base.metadata = MagicMock()
    # В SQLAlchemy 2.0 declarative_base находится в sqlalchemy.orm
    mock_orm.declarative_base = Mock(return_value=mock_base)

    sys.modules["sqlalchemy"] = mock_sqlalchemy
    sys.modules["sqlalchemy.orm"] = mock_orm
    # Оставляем для обратной совместимости, но не используем
    mock_declarative = MagicMock()
    sys.modules["sqlalchemy.ext.declarative"] = mock_declarative

    return mock_sqlalchemy, mock_orm, mock_declarative, mock_base


def mock_pymongo_dependencies():
    """Мокает зависимости pymongo для тестирования."""
    mock_pymongo = MagicMock()
    mock_pymongo.MongoClient = Mock()

    sys.modules["pymongo"] = mock_pymongo
    sys.modules["pymongo.collection"] = MagicMock()
    sys.modules["pymongo.database"] = MagicMock()

    return mock_pymongo


class TestMemoryProgressTracker:
    """Тесты для MemoryProgressTracker (уже протестирован в test_progress_tracker.py)."""

    def test_memory_tracker_import(self) -> None:
        """Тест импорта MemoryProgressTracker."""
        from task_sequencer.adapters.memory import MemoryProgressTracker

        assert MemoryProgressTracker is not None


class TestMySQLProgressTracker:
    """Тесты для MySQLProgressTracker с mock-объектами."""

    def setup_method(self) -> None:
        """Настройка перед каждым тестом."""
        # Очищаем кэш импортов
        if "task_sequencer.adapters.mysql" in sys.modules:
            del sys.modules["task_sequencer.adapters.mysql"]

    def test_mysql_tracker_initialization(self) -> None:
        """Тест инициализации MySQLProgressTracker."""
        mock_sqlalchemy, mock_orm, mock_declarative, mock_base = mock_sqlalchemy_dependencies()

        mock_engine = Mock()
        mock_sqlalchemy.create_engine.return_value = mock_engine
        mock_session_factory = Mock()
        mock_orm.sessionmaker.return_value = mock_session_factory
        mock_base = Mock()
        mock_orm.declarative_base.return_value = mock_base

        from task_sequencer.adapters.mysql import MySQLProgressTracker

        tracker = MySQLProgressTracker("mysql+pymysql://user:pass@localhost/db")

        assert tracker.engine == mock_engine
        assert tracker.session_factory == mock_session_factory
        mock_base.metadata.create_all.assert_called_once_with(mock_engine)

    def test_mysql_tracker_save_progress(self) -> None:
        """Тест сохранения прогресса в MySQL."""
        mock_sqlalchemy, mock_orm, mock_declarative, _ = mock_sqlalchemy_dependencies()

        mock_engine = Mock()
        mock_sqlalchemy.create_engine.return_value = mock_engine
        mock_session = Mock()
        mock_session_factory = Mock(return_value=mock_session)
        mock_orm.sessionmaker.return_value = mock_session_factory
        mock_orm.declarative_base.return_value = Mock()

        from task_sequencer.adapters.mysql import MySQLProgressTracker

        tracker = MySQLProgressTracker("mysql+pymysql://user:pass@localhost/db", create_tables=False)

        progress = TaskProgress(
            task_name="test_task",
            status=TaskStatus.IN_PROGRESS,
            processed_items=5,
        )

        tracker.save_progress("test_task", progress)

        mock_session.merge.assert_called_once()
        mock_session.commit.assert_called_once()
        mock_session.close.assert_called_once()

    def test_mysql_tracker_get_progress(self) -> None:
        """Тест получения прогресса из MySQL."""
        mock_sqlalchemy, mock_orm, mock_declarative, _ = mock_sqlalchemy_dependencies()

        mock_engine = Mock()
        mock_sqlalchemy.create_engine.return_value = mock_engine
        mock_session = Mock()
        mock_session_factory = Mock(return_value=mock_session)
        mock_orm.sessionmaker.return_value = mock_session_factory
        mock_orm.declarative_base.return_value = Mock()

        # Мокаем результат запроса
        mock_model = Mock()
        mock_model.task_name = "test_task"
        mock_model.status = TaskStatus.IN_PROGRESS.value
        mock_model.total_items = None
        mock_model.processed_items = 5
        mock_model.last_processed_id = None
        mock_model.started_at = None
        mock_model.completed_at = None
        mock_model.error_message = None
        mock_model.metadata_json = None

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_model
        mock_session.execute.return_value = mock_result

        # Мокаем TaskProgressModel для select()
        with patch("task_sequencer.adapters.mysql.TaskProgressModel") as mock_model_class:
            mock_model_class.task_name = Mock()
            from task_sequencer.adapters.mysql import MySQLProgressTracker

            tracker = MySQLProgressTracker("mysql+pymysql://user:pass@localhost/db", create_tables=False)

            result = tracker.get_progress("test_task")

            assert result is not None
            assert result.task_name == "test_task"
            assert result.status == TaskStatus.IN_PROGRESS
            assert result.processed_items == 5
            mock_session.close.assert_called_once()

    def test_mysql_tracker_get_progress_not_found(self) -> None:
        """Тест получения несуществующего прогресса из MySQL."""
        mock_sqlalchemy, mock_orm, mock_declarative, _ = mock_sqlalchemy_dependencies()

        mock_engine = Mock()
        mock_sqlalchemy.create_engine.return_value = mock_engine
        mock_session = Mock()
        mock_session_factory = Mock(return_value=mock_session)
        mock_orm.sessionmaker.return_value = mock_session_factory
        mock_orm.declarative_base.return_value = Mock()

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        with patch("task_sequencer.adapters.mysql.TaskProgressModel") as mock_model_class:
            mock_model_class.task_name = Mock()
            from task_sequencer.adapters.mysql import MySQLProgressTracker

            tracker = MySQLProgressTracker("mysql+pymysql://user:pass@localhost/db", create_tables=False)

            result = tracker.get_progress("nonexistent_task")

            assert result is None
            mock_session.close.assert_called_once()

    def test_mysql_tracker_mark_completed(self) -> None:
        """Тест отметки задачи как завершенной в MySQL."""
        mock_sqlalchemy, mock_orm, mock_declarative, _ = mock_sqlalchemy_dependencies()

        mock_engine = Mock()
        mock_sqlalchemy.create_engine.return_value = mock_engine
        mock_session = Mock()
        mock_session_factory = Mock(return_value=mock_session)
        mock_orm.sessionmaker.return_value = mock_session_factory
        mock_orm.declarative_base.return_value = Mock()

        # Мокаем существующий прогресс
        mock_model = Mock()
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_model
        mock_session.execute.return_value = mock_result

        with patch("task_sequencer.adapters.mysql.TaskProgressModel") as mock_model_class:
            mock_model_class.task_name = Mock()
            from task_sequencer.adapters.mysql import MySQLProgressTracker

            tracker = MySQLProgressTracker("mysql+pymysql://user:pass@localhost/db", create_tables=False)

            tracker.mark_completed("test_task")

            assert mock_model.status == TaskStatus.COMPLETED.value
            assert mock_model.completed_at is not None
            mock_session.commit.assert_called_once()
            mock_session.close.assert_called_once()

    def test_mysql_tracker_clear_progress(self) -> None:
        """Тест очистки прогресса в MySQL."""
        mock_sqlalchemy, mock_orm, mock_declarative, _ = mock_sqlalchemy_dependencies()

        mock_engine = Mock()
        mock_sqlalchemy.create_engine.return_value = mock_engine
        mock_session = Mock()
        mock_session_factory = Mock(return_value=mock_session)
        mock_orm.sessionmaker.return_value = mock_session_factory
        mock_orm.declarative_base.return_value = Mock()

        mock_model = Mock()
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_model
        mock_session.execute.return_value = mock_result

        with patch("task_sequencer.adapters.mysql.TaskProgressModel") as mock_model_class:
            mock_model_class.task_name = Mock()
            from task_sequencer.adapters.mysql import MySQLProgressTracker

            tracker = MySQLProgressTracker("mysql+pymysql://user:pass@localhost/db", create_tables=False)

            tracker.clear_progress("test_task")

            mock_session.delete.assert_called_once_with(mock_model)
            mock_session.commit.assert_called_once()
            mock_session.close.assert_called_once()

    def test_mysql_tracker_with_database_name(self) -> None:
        """Тест инициализации MySQLProgressTracker с database_name."""
        mock_sqlalchemy, mock_orm, mock_declarative, mock_base = mock_sqlalchemy_dependencies()

        mock_engine = Mock()
        mock_sqlalchemy.create_engine.return_value = mock_engine
        mock_session_factory = Mock()
        mock_orm.sessionmaker.return_value = mock_session_factory
        mock_base = Mock()
        mock_orm.declarative_base.return_value = mock_base

        from task_sequencer.adapters.mysql import MySQLProgressTracker

        # Тест с database_name параметром
        tracker = MySQLProgressTracker(
            "mysql+pymysql://user:pass@localhost:3306/",
            database_name="my_database",
        )

        assert tracker.engine == mock_engine
        assert tracker.session_factory == mock_session_factory
        # Проверяем, что connection string была обновлена
        call_args = mock_sqlalchemy.create_engine.call_args[0][0]
        assert "my_database" in call_args

    def test_mysql_tracker_with_table_name(self) -> None:
        """Тест инициализации MySQLProgressTracker с table_name."""
        mock_sqlalchemy, mock_orm, mock_declarative, mock_base = mock_sqlalchemy_dependencies()

        mock_engine = Mock()
        mock_sqlalchemy.create_engine.return_value = mock_engine
        mock_session_factory = Mock()
        mock_orm.sessionmaker.return_value = mock_session_factory
        mock_base = Mock()
        mock_orm.declarative_base.return_value = mock_base

        from task_sequencer.adapters.mysql import MySQLProgressTracker

        # Тест с table_name параметром (без создания таблиц для упрощения теста)
        tracker = MySQLProgressTracker(
            "mysql+pymysql://user:pass@localhost:3306/db",
            table_name="my_progress",
            create_tables=False,  # Не создаем таблицы, чтобы избежать проблем с мокированием
        )

        assert tracker.engine == mock_engine
        assert tracker.table_name == "my_progress"
        assert tracker._use_dynamic_model is True
        assert tracker.TaskProgressModel is not None

    def test_mysql_tracker_import_error(self) -> None:
        """Тест обработки отсутствия зависимостей для MySQL."""
        # Очищаем кэш
        modules_to_remove = [
            "task_sequencer.adapters.mysql",
            "sqlalchemy",
            "sqlalchemy.orm",
            "sqlalchemy.ext.declarative",
        ]
        for mod in modules_to_remove:
            if mod in sys.modules:
                del sys.modules[mod]

        # Мокаем отсутствие sqlalchemy
        original_import = __import__

        def mock_import(name, *args, **kwargs):
            if name == "sqlalchemy":
                raise ImportError("No module named 'sqlalchemy'")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            with pytest.raises(ImportError, match="MySQL adapter requires"):
                import importlib

                importlib.reload(sys.modules.get("task_sequencer.adapters.mysql", None) or importlib.import_module("task_sequencer.adapters.mysql"))


class TestMongoDBProgressTracker:
    """Тесты для MongoDBProgressTracker с mock-объектами."""

    def setup_method(self) -> None:
        """Настройка перед каждым тестом."""
        if "task_sequencer.adapters.mongodb" in sys.modules:
            del sys.modules["task_sequencer.adapters.mongodb"]

    def test_mongodb_tracker_initialization(self) -> None:
        """Тест инициализации MongoDBProgressTracker."""
        mock_pymongo = mock_pymongo_dependencies()

        mock_client = MagicMock()
        mock_database = MagicMock()
        mock_collection = MagicMock()
        mock_client.__getitem__ = Mock(return_value=mock_database)
        mock_database.__getitem__ = Mock(return_value=mock_collection)
        mock_pymongo.MongoClient.return_value = mock_client

        from task_sequencer.adapters.mongodb import MongoDBProgressTracker

        tracker = MongoDBProgressTracker("mongodb://localhost:27017/")

        assert tracker.client == mock_client
        assert tracker.database == mock_database
        assert tracker.collection == mock_collection
        mock_collection.create_index.assert_called_once_with("task_name", unique=True)

    def test_mongodb_tracker_extract_database_name(self) -> None:
        """Тест извлечения database_name из connection string."""
        from task_sequencer.adapters.mongodb import MongoDBProgressTracker

        # С database в connection string
        db_name = MongoDBProgressTracker._extract_database_name(
            "mongodb://user:pass@host:27017/my_database"
        )
        assert db_name == "my_database"

        # Без database в connection string
        db_name = MongoDBProgressTracker._extract_database_name(
            "mongodb://localhost:27017/"
        )
        assert db_name is None

        # С параметрами запроса
        db_name = MongoDBProgressTracker._extract_database_name(
            "mongodb://host:27017/my_db?replicaSet=rs0"
        )
        assert db_name == "my_db"

    def test_mongodb_tracker_auto_extract_database(self) -> None:
        """Тест автоматического извлечения database_name."""
        mock_pymongo = mock_pymongo_dependencies()

        mock_client = MagicMock()
        mock_database = MagicMock()
        mock_collection = MagicMock()
        mock_client.__getitem__ = Mock(return_value=mock_database)
        mock_database.__getitem__ = Mock(return_value=mock_collection)
        mock_pymongo.MongoClient.return_value = mock_client

        from task_sequencer.adapters.mongodb import MongoDBProgressTracker

        # Без явного database_name - должно извлечься из connection string
        tracker = MongoDBProgressTracker("mongodb://localhost:27017/my_db")

        # Проверяем, что использовалось извлеченное имя БД
        mock_client.__getitem__.assert_called_with("my_db")

    def test_mongodb_tracker_explicit_database_name(self) -> None:
        """Тест явного указания database_name (приоритет над connection string)."""
        mock_pymongo = mock_pymongo_dependencies()

        mock_client = MagicMock()
        mock_database = MagicMock()
        mock_collection = MagicMock()
        mock_client.__getitem__ = Mock(return_value=mock_database)
        mock_database.__getitem__ = Mock(return_value=mock_collection)
        mock_pymongo.MongoClient.return_value = mock_client

        from task_sequencer.adapters.mongodb import MongoDBProgressTracker

        # С явным database_name - должен использоваться он, а не из connection string
        tracker = MongoDBProgressTracker(
            "mongodb://localhost:27017/other_db", database_name="my_database"
        )

        # Проверяем, что использовалось явно указанное имя БД
        mock_client.__getitem__.assert_called_with("my_database")

    def test_mongodb_tracker_save_progress(self) -> None:
        """Тест сохранения прогресса в MongoDB."""
        mock_pymongo = mock_pymongo_dependencies()

        mock_client = MagicMock()
        mock_database = MagicMock()
        mock_collection = MagicMock()
        mock_client.__getitem__ = Mock(return_value=mock_database)
        mock_database.__getitem__ = Mock(return_value=mock_collection)
        mock_pymongo.MongoClient.return_value = mock_client

        from task_sequencer.adapters.mongodb import MongoDBProgressTracker

        tracker = MongoDBProgressTracker("mongodb://localhost:27017/")

        progress = TaskProgress(
            task_name="test_task",
            status=TaskStatus.IN_PROGRESS,
            processed_items=5,
        )

        tracker.save_progress("test_task", progress)

        mock_collection.update_one.assert_called_once()
        call_args = mock_collection.update_one.call_args
        assert call_args[0][0] == {"task_name": "test_task"}
        assert "$set" in call_args[0][1]
        assert call_args[1]["upsert"] is True

    def test_mongodb_tracker_get_progress(self) -> None:
        """Тест получения прогресса из MongoDB."""
        mock_pymongo = mock_pymongo_dependencies()

        mock_client = MagicMock()
        mock_database = MagicMock()
        mock_collection = MagicMock()
        mock_client.__getitem__ = Mock(return_value=mock_database)
        mock_database.__getitem__ = Mock(return_value=mock_collection)
        mock_pymongo.MongoClient.return_value = mock_client

        mock_collection.find_one.return_value = {
            "task_name": "test_task",
            "status": TaskStatus.IN_PROGRESS.value,
            "total_items": None,
            "processed_items": 5,
            "last_processed_id": None,
            "started_at": None,
            "completed_at": None,
            "error_message": None,
            "metadata": {},
        }

        from task_sequencer.adapters.mongodb import MongoDBProgressTracker

        tracker = MongoDBProgressTracker("mongodb://localhost:27017/")

        result = tracker.get_progress("test_task")

        assert result is not None
        assert result.task_name == "test_task"
        assert result.status == TaskStatus.IN_PROGRESS
        assert result.processed_items == 5

    def test_mongodb_tracker_get_progress_not_found(self) -> None:
        """Тест получения несуществующего прогресса из MongoDB."""
        mock_pymongo = mock_pymongo_dependencies()

        mock_client = MagicMock()
        mock_database = MagicMock()
        mock_collection = MagicMock()
        mock_client.__getitem__ = Mock(return_value=mock_database)
        mock_database.__getitem__ = Mock(return_value=mock_collection)
        mock_pymongo.MongoClient.return_value = mock_client

        mock_collection.find_one.return_value = None

        from task_sequencer.adapters.mongodb import MongoDBProgressTracker

        tracker = MongoDBProgressTracker("mongodb://localhost:27017/")

        result = tracker.get_progress("nonexistent_task")

        assert result is None

    def test_mongodb_tracker_mark_completed(self) -> None:
        """Тест отметки задачи как завершенной в MongoDB."""
        mock_pymongo = mock_pymongo_dependencies()

        mock_client = MagicMock()
        mock_database = MagicMock()
        mock_collection = MagicMock()
        mock_client.__getitem__ = Mock(return_value=mock_database)
        mock_database.__getitem__ = Mock(return_value=mock_collection)
        mock_pymongo.MongoClient.return_value = mock_client

        from task_sequencer.adapters.mongodb import MongoDBProgressTracker

        tracker = MongoDBProgressTracker("mongodb://localhost:27017/")

        tracker.mark_completed("test_task")

        mock_collection.update_one.assert_called_once()
        call_args = mock_collection.update_one.call_args
        assert call_args[0][0] == {"task_name": "test_task"}
        assert "$set" in call_args[0][1]
        assert call_args[0][1]["$set"]["status"] == TaskStatus.COMPLETED.value

    def test_mongodb_tracker_clear_progress(self) -> None:
        """Тест очистки прогресса в MongoDB."""
        mock_pymongo = mock_pymongo_dependencies()

        mock_client = MagicMock()
        mock_database = MagicMock()
        mock_collection = MagicMock()
        mock_client.__getitem__ = Mock(return_value=mock_database)
        mock_database.__getitem__ = Mock(return_value=mock_collection)
        mock_pymongo.MongoClient.return_value = mock_client

        from task_sequencer.adapters.mongodb import MongoDBProgressTracker

        tracker = MongoDBProgressTracker("mongodb://localhost:27017/")

        tracker.clear_progress("test_task")

        mock_collection.delete_one.assert_called_once_with({"task_name": "test_task"})

    def test_mongodb_tracker_import_error(self) -> None:
        """Тест обработки отсутствия зависимостей для MongoDB."""
        # Очищаем кэш
        modules_to_remove = [
            "task_sequencer.adapters.mongodb",
            "pymongo",
            "pymongo.collection",
            "pymongo.database",
        ]
        for mod in modules_to_remove:
            if mod in sys.modules:
                del sys.modules[mod]

        # Мокаем отсутствие pymongo
        original_import = __import__

        def mock_import(name, *args, **kwargs):
            if name == "pymongo":
                raise ImportError("No module named 'pymongo'")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            with pytest.raises(ImportError, match="MongoDB adapter requires"):
                import importlib

                importlib.reload(sys.modules.get("task_sequencer.adapters.mongodb", None) or importlib.import_module("task_sequencer.adapters.mongodb"))


class TestPostgreSQLProgressTracker:
    """Тесты для PostgreSQLProgressTracker с mock-объектами."""

    def setup_method(self) -> None:
        """Настройка перед каждым тестом."""
        if "task_sequencer.adapters.postgresql" in sys.modules:
            del sys.modules["task_sequencer.adapters.postgresql"]

    def test_postgresql_tracker_initialization(self) -> None:
        """Тест инициализации PostgreSQLProgressTracker."""
        mock_sqlalchemy, mock_orm, mock_declarative, mock_base = mock_sqlalchemy_dependencies()

        mock_engine = Mock()
        mock_sqlalchemy.create_engine.return_value = mock_engine
        mock_session_factory = Mock()
        mock_orm.sessionmaker.return_value = mock_session_factory
        mock_base = Mock()
        mock_orm.declarative_base.return_value = mock_base

        from task_sequencer.adapters.postgresql import PostgreSQLProgressTracker

        tracker = PostgreSQLProgressTracker("postgresql+psycopg2://user:pass@localhost/db")

        assert tracker.engine == mock_engine
        assert tracker.session_factory == mock_session_factory
        mock_base.metadata.create_all.assert_called_once_with(mock_engine)

    def test_postgresql_tracker_save_progress(self) -> None:
        """Тест сохранения прогресса в PostgreSQL."""
        mock_sqlalchemy, mock_orm, mock_declarative, _ = mock_sqlalchemy_dependencies()

        mock_engine = Mock()
        mock_sqlalchemy.create_engine.return_value = mock_engine
        mock_session = Mock()
        mock_session_factory = Mock(return_value=mock_session)
        mock_orm.sessionmaker.return_value = mock_session_factory
        mock_orm.declarative_base.return_value = Mock()

        from task_sequencer.adapters.postgresql import PostgreSQLProgressTracker

        tracker = PostgreSQLProgressTracker(
            "postgresql+psycopg2://user:pass@localhost/db", create_tables=False
        )

        progress = TaskProgress(
            task_name="test_task",
            status=TaskStatus.IN_PROGRESS,
            processed_items=5,
        )

        tracker.save_progress("test_task", progress)

        mock_session.merge.assert_called_once()
        mock_session.commit.assert_called_once()
        mock_session.close.assert_called_once()

    def test_postgresql_tracker_get_progress(self) -> None:
        """Тест получения прогресса из PostgreSQL."""
        mock_sqlalchemy, mock_orm, mock_declarative, _ = mock_sqlalchemy_dependencies()

        mock_engine = Mock()
        mock_sqlalchemy.create_engine.return_value = mock_engine
        mock_session = Mock()
        mock_session_factory = Mock(return_value=mock_session)
        mock_orm.sessionmaker.return_value = mock_session_factory
        mock_orm.declarative_base.return_value = Mock()

        mock_model = Mock()
        mock_model.task_name = "test_task"
        mock_model.status = TaskStatus.IN_PROGRESS.value
        mock_model.total_items = None
        mock_model.processed_items = 5
        mock_model.last_processed_id = None
        mock_model.started_at = None
        mock_model.completed_at = None
        mock_model.error_message = None
        mock_model.metadata_json = None

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_model
        mock_session.execute.return_value = mock_result

        with patch("task_sequencer.adapters.postgresql.TaskProgressModel") as mock_model_class:
            mock_model_class.task_name = Mock()
            from task_sequencer.adapters.postgresql import PostgreSQLProgressTracker

            tracker = PostgreSQLProgressTracker(
                "postgresql+psycopg2://user:pass@localhost/db", create_tables=False
            )

            result = tracker.get_progress("test_task")

            assert result is not None
            assert result.task_name == "test_task"
            assert result.status == TaskStatus.IN_PROGRESS
            assert result.processed_items == 5
            mock_session.close.assert_called_once()

    def test_postgresql_tracker_import_error(self) -> None:
        """Тест обработки отсутствия зависимостей для PostgreSQL."""
        # Очищаем кэш
        modules_to_remove = [
            "task_sequencer.adapters.postgresql",
            "sqlalchemy",
            "sqlalchemy.orm",
            "sqlalchemy.ext.declarative",
        ]
        for mod in modules_to_remove:
            if mod in sys.modules:
                del sys.modules[mod]

        # Мокаем отсутствие sqlalchemy
        original_import = __import__

        def mock_import(name, *args, **kwargs):
            if name == "sqlalchemy":
                raise ImportError("No module named 'sqlalchemy'")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            with pytest.raises(ImportError, match="PostgreSQL adapter requires"):
                import importlib

                importlib.reload(sys.modules.get("task_sequencer.adapters.postgresql", None) or importlib.import_module("task_sequencer.adapters.postgresql"))
