"""Тесты для проверки публичного API и импортов."""

from __future__ import annotations

import pytest


class TestPublicAPI:
    """Тесты для проверки публичного API."""

    def test_import_task_sequencer(self) -> None:
        """Тест импорта TaskOrchestrator."""
        from task_sequencer import TaskOrchestrator

        assert TaskOrchestrator is not None

    def test_import_task_registry(self) -> None:
        """Тест импорта TaskRegistry."""
        from task_sequencer import TaskRegistry

        assert TaskRegistry is not None

    def test_import_execution_result(self) -> None:
        """Тест импорта ExecutionResult."""
        from task_sequencer import ExecutionResult

        assert ExecutionResult is not None

    def test_import_task(self) -> None:
        """Тест импорта Task."""
        from task_sequencer import Task

        assert Task is not None

    def test_import_iterable_task(self) -> None:
        """Тест импорта IterableTask."""
        from task_sequencer import IterableTask

        assert IterableTask is not None

    def test_import_progress_tracker(self) -> None:
        """Тест импорта ProgressTracker."""
        from task_sequencer import ProgressTracker

        assert ProgressTracker is not None

    def test_import_task_progress(self) -> None:
        """Тест импорта TaskProgress."""
        from task_sequencer import TaskProgress

        assert TaskProgress is not None

    def test_import_task_status(self) -> None:
        """Тест импорта TaskStatus."""
        from task_sequencer import TaskStatus

        assert TaskStatus is not None

    def test_import_dependency_validator(self) -> None:
        """Тест импорта DependencyValidator."""
        from task_sequencer import DependencyValidator

        assert DependencyValidator is not None

    def test_import_resume_iterator(self) -> None:
        """Тест импорта ResumeIterator."""
        from task_sequencer import ResumeIterator

        assert ResumeIterator is not None

    def test_import_limiting_iterator(self) -> None:
        """Тест импорта LimitingIterator."""
        from task_sequencer import LimitingIterator

        assert LimitingIterator is not None

    def test_import_task_result(self) -> None:
        """Тест импорта TaskResult."""
        from task_sequencer import TaskResult

        assert TaskResult is not None

    def test_import_execution_context(self) -> None:
        """Тест импорта ExecutionContext."""
        from task_sequencer import ExecutionContext

        assert ExecutionContext is not None

    def test_import_dependency_error(self) -> None:
        """Тест импорта DependencyError."""
        from task_sequencer import DependencyError

        assert DependencyError is not None

    def test_import_task_execution_error(self) -> None:
        """Тест импорта TaskExecutionError."""
        from task_sequencer import TaskExecutionError

        assert TaskExecutionError is not None

    def test_import_progress_error(self) -> None:
        """Тест импорта ProgressError."""
        from task_sequencer import ProgressError

        assert ProgressError is not None

    def test_import_version(self) -> None:
        """Тест импорта версии."""
        import task_sequencer

        assert hasattr(task_sequencer, "__version__")
        assert task_sequencer.__version__ is not None
        assert isinstance(task_sequencer.__version__, str)

    def test_import_all_from_package(self) -> None:
        """Тест импорта всех публичных классов через __all__."""
        import task_sequencer

        assert hasattr(task_sequencer, "__all__")
        assert isinstance(task_sequencer.__all__, list)
        assert len(task_sequencer.__all__) > 0

        # Проверяем, что все элементы из __all__ доступны
        for name in task_sequencer.__all__:
            assert hasattr(task_sequencer, name), f"{name} not found in module"

    def test_import_memory_progress_tracker(self) -> None:
        """Тест импорта MemoryProgressTracker из adapters."""
        from task_sequencer.adapters import MemoryProgressTracker

        assert MemoryProgressTracker is not None

    def test_adapters_module_available(self) -> None:
        """Тест, что модуль adapters доступен после установки пакета."""
        import task_sequencer.adapters

        assert task_sequencer.adapters is not None
        assert hasattr(task_sequencer.adapters, "__all__")
        assert "MemoryProgressTracker" in task_sequencer.adapters.__all__

    def test_adapters_files_in_package(self) -> None:
        """Тест, что файлы адаптеров включены в пакет."""
        import task_sequencer.adapters
        import importlib.util

        # Проверяем, что модули адаптеров доступны
        adapters_path = task_sequencer.adapters.__path__[0]
        import os

        expected_files = [
            "__init__.py",
            "memory.py",
            "mysql.py",
            "mongodb.py",
            "postgresql.py",
        ]

        for filename in expected_files:
            filepath = os.path.join(adapters_path, filename)
            assert os.path.exists(filepath), f"Файл {filename} должен быть в пакете"

    def test_optional_adapters_import_with_dependencies(self) -> None:
        """Тест импорта опциональных адаптеров при наличии зависимостей."""
        from task_sequencer.adapters import MemoryProgressTracker

        # MemoryProgressTracker всегда доступен
        assert MemoryProgressTracker is not None

        # Опциональные адаптеры могут быть недоступны без зависимостей
        # Это нормальное поведение
        try:
            from task_sequencer.adapters import MySQLProgressTracker

            assert MySQLProgressTracker is not None
        except ImportError:
            # Это нормально, если зависимости не установлены
            pass

        try:
            from task_sequencer.adapters import MongoDBProgressTracker

            assert MongoDBProgressTracker is not None
        except ImportError:
            # Это нормально, если зависимости не установлены
            pass

        try:
            from task_sequencer.adapters import PostgreSQLProgressTracker

            assert PostgreSQLProgressTracker is not None
        except ImportError:
            # Это нормально, если зависимости не установлены
            pass

    def test_private_classes_not_exported(self) -> None:
        """Тест, что приватные классы не экспортируются."""
        import task_sequencer

        # Проверяем, что приватные классы не в __all__
        private_names = [
            "_TaskRegistry",
            "_TaskOrchestrator",
            "_DependencyValidator",
        ]

        for name in private_names:
            assert name not in task_sequencer.__all__

    def test_star_import_works(self) -> None:
        """Тест, что star import работает корректно."""
        # Проверяем, что __all__ определен и содержит нужные классы
        import task_sequencer

        expected_classes = [
            "TaskOrchestrator",
            "Task",
            "TaskStatus",
            "DependencyError",
        ]

        for class_name in expected_classes:
            assert class_name in task_sequencer.__all__
            assert hasattr(task_sequencer, class_name)

    def test_import_from_submodules(self) -> None:
        """Тест импорта из подмодулей."""
        from task_sequencer.core import TaskRegistry, TaskOrchestrator, ExecutionResult
        from task_sequencer.interfaces import Task, IterableTask, TaskResult
        from task_sequencer.progress import TaskProgress, TaskStatus
        from task_sequencer.exceptions import DependencyError, TaskExecutionError
        from task_sequencer.validators import DependencyValidator
        from task_sequencer.iterators import ResumeIterator, LimitingIterator

        # Проверяем, что все импорты успешны
        assert TaskRegistry is not None
        assert TaskOrchestrator is not None
        assert ExecutionResult is not None
        assert Task is not None
        assert IterableTask is not None
        assert TaskResult is not None
        assert TaskProgress is not None
        assert TaskStatus is not None
        assert DependencyError is not None
        assert TaskExecutionError is not None
        assert DependencyValidator is not None
        assert ResumeIterator is not None
        assert LimitingIterator is not None

