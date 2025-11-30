"""Тесты для TaskRegistry."""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from task_sequencer.core import TaskRegistry
from task_sequencer.interfaces import ExecutionContext, Task, TaskResult


class TestTaskRegistry:
    """Тесты для TaskRegistry."""

    def test_create_empty_registry(self) -> None:
        """Тест создания пустого реестра."""
        registry = TaskRegistry()
        assert len(registry.get_all()) == 0

    def test_create_registry_with_tasks(self) -> None:
        """Тест создания реестра с начальным списком задач."""
        task1 = Mock(spec=Task)
        task1.name = "task1"
        task2 = Mock(spec=Task)
        task2.name = "task2"

        registry = TaskRegistry([task1, task2])
        assert len(registry.get_all()) == 2
        assert registry.get("task1") is task1
        assert registry.get("task2") is task2

    def test_register_task(self) -> None:
        """Тест регистрации задачи."""
        registry = TaskRegistry()
        task = Mock(spec=Task)
        task.name = "test_task"

        registry.register(task)
        assert registry.get("test_task") is task
        assert len(registry.get_all()) == 1

    def test_register_multiple_tasks(self) -> None:
        """Тест регистрации нескольких задач."""
        registry = TaskRegistry()
        task1 = Mock(spec=Task)
        task1.name = "task1"
        task2 = Mock(spec=Task)
        task2.name = "task2"
        task3 = Mock(spec=Task)
        task3.name = "task3"

        registry.register(task1)
        registry.register(task2)
        registry.register(task3)

        assert len(registry.get_all()) == 3
        assert registry.get("task1") is task1
        assert registry.get("task2") is task2
        assert registry.get("task3") is task3

    def test_register_duplicate_name_raises_error(self) -> None:
        """Тест проверяет, что регистрация задачи с дублирующимся именем вызывает ошибку."""
        registry = TaskRegistry()
        task1 = Mock(spec=Task)
        task1.name = "duplicate_task"
        task2 = Mock(spec=Task)
        task2.name = "duplicate_task"

        registry.register(task1)
        with pytest.raises(ValueError, match="already registered"):
            registry.register(task2)

    def test_register_duplicate_name_in_init_raises_error(self) -> None:
        """Тест проверяет, что дублирующиеся имена в конструкторе вызывают ошибку."""
        task1 = Mock(spec=Task)
        task1.name = "duplicate_task"
        task2 = Mock(spec=Task)
        task2.name = "duplicate_task"

        with pytest.raises(ValueError, match="already registered"):
            TaskRegistry([task1, task2])

    def test_get_existing_task(self) -> None:
        """Тест получения существующей задачи."""
        registry = TaskRegistry()
        task = Mock(spec=Task)
        task.name = "existing_task"
        registry.register(task)

        retrieved_task = registry.get("existing_task")
        assert retrieved_task is task

    def test_get_nonexistent_task_raises_keyerror(self) -> None:
        """Тест проверяет, что получение несуществующей задачи вызывает KeyError."""
        registry = TaskRegistry()
        with pytest.raises(KeyError, match="not found in registry"):
            registry.get("nonexistent_task")

    def test_get_all_returns_all_tasks(self) -> None:
        """Тест получения всех задач."""
        registry = TaskRegistry()
        task1 = Mock(spec=Task)
        task1.name = "task1"
        task2 = Mock(spec=Task)
        task2.name = "task2"
        task3 = Mock(spec=Task)
        task3.name = "task3"

        registry.register(task1)
        registry.register(task2)
        registry.register(task3)

        all_tasks = registry.get_all()
        assert len(all_tasks) == 3
        assert task1 in all_tasks
        assert task2 in all_tasks
        assert task3 in all_tasks

    def test_get_all_returns_copy(self) -> None:
        """Тест проверяет, что get_all возвращает копию списка."""
        registry = TaskRegistry()
        task = Mock(spec=Task)
        task.name = "test_task"
        registry.register(task)

        all_tasks1 = registry.get_all()
        all_tasks2 = registry.get_all()

        assert all_tasks1 is not all_tasks2
        assert all_tasks1 == all_tasks2

    def test_get_all_empty_registry(self) -> None:
        """Тест получения всех задач из пустого реестра."""
        registry = TaskRegistry()
        assert registry.get_all() == []

    def test_register_after_get_all(self) -> None:
        """Тест регистрации задачи после вызова get_all."""
        registry = TaskRegistry()
        task1 = Mock(spec=Task)
        task1.name = "task1"
        registry.register(task1)

        all_tasks_before = registry.get_all()
        assert len(all_tasks_before) == 1

        task2 = Mock(spec=Task)
        task2.name = "task2"
        registry.register(task2)

        all_tasks_after = registry.get_all()
        assert len(all_tasks_after) == 2

    def test_task_registry_with_real_task_implementation(self) -> None:
        """Тест реестра с реальной реализацией задачи."""
        class RealTask(Task):
            @property
            def name(self) -> str:
                return "real_task"

            @property
            def depends_on(self) -> list[str]:
                return []

            def execute(self, context: ExecutionContext) -> TaskResult:
                return TaskResult.success_result()

        registry = TaskRegistry()
        task = RealTask()
        registry.register(task)

        retrieved_task = registry.get("real_task")
        assert retrieved_task is task
        assert isinstance(retrieved_task, RealTask)

    def test_contains_operator(self) -> None:
        """Тест оператора in для проверки наличия задачи."""
        registry = TaskRegistry()
        task = Mock(spec=Task)
        task.name = "test_task"
        registry.register(task)

        assert "test_task" in registry
        assert "nonexistent_task" not in registry

    def test_contains_operator_empty_registry(self) -> None:
        """Тест оператора in для пустого реестра."""
        registry = TaskRegistry()
        assert "any_task" not in registry

    def test_getitem_operator(self) -> None:
        """Тест оператора [] для получения задачи."""
        registry = TaskRegistry()
        task = Mock(spec=Task)
        task.name = "test_task"
        registry.register(task)

        retrieved_task = registry["test_task"]
        assert retrieved_task is task

    def test_getitem_operator_nonexistent_task_raises_keyerror(self) -> None:
        """Тест проверяет, что оператор [] для несуществующей задачи вызывает KeyError."""
        registry = TaskRegistry()
        with pytest.raises(KeyError):
            _ = registry["nonexistent_task"]

    def test_getitem_operator_equivalent_to_get(self) -> None:
        """Тест проверяет, что оператор [] эквивалентен методу get()."""
        registry = TaskRegistry()
        task = Mock(spec=Task)
        task.name = "test_task"
        registry.register(task)

        task1 = registry["test_task"]
        task2 = registry.get("test_task")
        assert task1 is task2

    def test_tasks_property(self) -> None:
        """Тест свойства tasks для получения словаря всех задач."""
        registry = TaskRegistry()
        task1 = Mock(spec=Task)
        task1.name = "task1"
        task2 = Mock(spec=Task)
        task2.name = "task2"
        registry.register(task1)
        registry.register(task2)

        all_tasks = registry.tasks
        assert isinstance(all_tasks, dict)
        assert len(all_tasks) == 2
        assert "task1" in all_tasks
        assert "task2" in all_tasks
        assert all_tasks["task1"] is task1
        assert all_tasks["task2"] is task2

    def test_tasks_property_returns_copy(self) -> None:
        """Тест проверяет, что свойство tasks возвращает копию словаря."""
        registry = TaskRegistry()
        task = Mock(spec=Task)
        task.name = "test_task"
        registry.register(task)

        tasks1 = registry.tasks
        tasks2 = registry.tasks

        assert tasks1 is not tasks2
        assert tasks1 == tasks2

    def test_tasks_property_is_readonly(self) -> None:
        """Тест проверяет, что свойство tasks возвращает read-only копию."""
        registry = TaskRegistry()
        task = Mock(spec=Task)
        task.name = "test_task"
        registry.register(task)

        tasks = registry.tasks
        # Модификация копии не должна влиять на оригинал
        tasks["new_task"] = Mock(spec=Task)

        # Оригинальный реестр не должен измениться
        assert "new_task" not in registry
        assert len(registry.get_all()) == 1

    def test_tasks_property_empty_registry(self) -> None:
        """Тест свойства tasks для пустого реестра."""
        registry = TaskRegistry()
        all_tasks = registry.tasks
        assert isinstance(all_tasks, dict)
        assert len(all_tasks) == 0

    def test_pythonic_api_combined(self) -> None:
        """Тест комбинированного использования Pythonic API."""
        registry = TaskRegistry()
        task1 = Mock(spec=Task)
        task1.name = "task1"
        task2 = Mock(spec=Task)
        task2.name = "task2"
        registry.register(task1)
        registry.register(task2)

        # Проверка наличия
        if "task1" in registry:
            # Доступ через []
            retrieved_task = registry["task1"]
            assert retrieved_task is task1

        # Получение словаря
        all_tasks = registry.tasks
        for name, task in all_tasks.items():
            assert name in registry
            assert registry[name] is task

    def test_backward_compatibility(self) -> None:
        """Тест обратной совместимости - старые методы продолжают работать."""
        registry = TaskRegistry()
        task = Mock(spec=Task)
        task.name = "test_task"
        registry.register(task)

        # Старые методы должны работать
        retrieved_task = registry.get("test_task")
        assert retrieved_task is task

        all_tasks_list = registry.get_all()
        assert isinstance(all_tasks_list, list)
        assert task in all_tasks_list

        # Новые методы также работают
        assert "test_task" in registry
        assert registry["test_task"] is task
        assert isinstance(registry.tasks, dict)



