"""Тесты для DependencyValidator."""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from task_sequencer.core import TaskRegistry
from task_sequencer.exceptions import DependencyError
from task_sequencer.interfaces import Task
from task_sequencer.validators import DependencyValidator


class TestDependencyValidator:
    """Тесты для DependencyValidator."""

    def test_validate_valid_dependencies(self) -> None:
        """Тест валидации корректных зависимостей."""
        # Создаем задачи без зависимостей
        task1 = Mock(spec=Task)
        task1.name = "task1"
        task1.depends_on = []

        task2 = Mock(spec=Task)
        task2.name = "task2"
        task2.depends_on = []

        registry = TaskRegistry([task1, task2])
        validator = DependencyValidator()

        # Не должно быть исключений
        validator.validate(["task1", "task2"], registry)

    def test_validate_valid_dependencies_with_deps(self) -> None:
        """Тест валидации корректных зависимостей между задачами."""
        task1 = Mock(spec=Task)
        task1.name = "task1"
        task1.depends_on = []

        task2 = Mock(spec=Task)
        task2.name = "task2"
        task2.depends_on = ["task1"]

        task3 = Mock(spec=Task)
        task3.name = "task3"
        task3.depends_on = ["task1", "task2"]

        registry = TaskRegistry([task1, task2, task3])
        validator = DependencyValidator()

        # Порядок корректен: task1 -> task2 -> task3
        validator.validate(["task1", "task2", "task3"], registry)

    def test_validate_missing_task_in_registry(self) -> None:
        """Тест проверяет, что валидация выбрасывает ошибку если задача не найдена в реестре."""
        task1 = Mock(spec=Task)
        task1.name = "task1"
        task1.depends_on = []

        registry = TaskRegistry([task1])
        validator = DependencyValidator()

        with pytest.raises(DependencyError, match="not found in registry"):
            validator.validate(["task1", "nonexistent_task"], registry)

    def test_validate_missing_dependency_in_task_order(self) -> None:
        """Тест: валидация выбрасывает ошибку если зависимость отсутствует."""
        task1 = Mock(spec=Task)
        task1.name = "task1"
        task1.depends_on = []

        task2 = Mock(spec=Task)
        task2.name = "task2"
        task2.depends_on = ["task1"]

        registry = TaskRegistry([task1, task2])
        validator = DependencyValidator()

        # task2 зависит от task1, но task1 не в task_order
        with pytest.raises(
            DependencyError, match="depends on tasks not in task_order"
        ):
            validator.validate(["task2"], registry)

    def test_validate_wrong_order(self) -> None:
        """Тест проверяет, что валидация выбрасывает ошибку если порядок задач нарушен."""
        task1 = Mock(spec=Task)
        task1.name = "task1"
        task1.depends_on = []

        task2 = Mock(spec=Task)
        task2.name = "task2"
        task2.depends_on = ["task1"]

        registry = TaskRegistry([task1, task2])
        validator = DependencyValidator()

        # task2 идет перед task1, но зависит от него
        with pytest.raises(
            DependencyError, match="depends on tasks that come after it"
        ):
            validator.validate(["task2", "task1"], registry)

    def test_validate_cyclic_dependency_simple(self) -> None:
        """Тест проверяет обнаружение простого цикла (A -> B -> A)."""
        task_a = Mock(spec=Task)
        task_a.name = "task_a"
        task_a.depends_on = ["task_b"]

        task_b = Mock(spec=Task)
        task_b.name = "task_b"
        task_b.depends_on = ["task_a"]

        registry = TaskRegistry([task_a, task_b])
        validator = DependencyValidator()

        with pytest.raises(DependencyError, match="Cyclic dependency detected"):
            validator.validate(["task_a", "task_b"], registry)

    def test_validate_cyclic_dependency_complex(self) -> None:
        """Тест проверяет обнаружение сложного цикла (A -> B -> C -> A)."""
        task_a = Mock(spec=Task)
        task_a.name = "task_a"
        task_a.depends_on = ["task_c"]

        task_b = Mock(spec=Task)
        task_b.name = "task_b"
        task_b.depends_on = ["task_a"]

        task_c = Mock(spec=Task)
        task_c.name = "task_c"
        task_c.depends_on = ["task_b"]

        registry = TaskRegistry([task_a, task_b, task_c])
        validator = DependencyValidator()

        with pytest.raises(DependencyError, match="Cyclic dependency detected"):
            validator.validate(["task_a", "task_b", "task_c"], registry)

    def test_validate_self_dependency(self) -> None:
        """Тест проверяет обнаружение самозависимости (A -> A)."""
        task_a = Mock(spec=Task)
        task_a.name = "task_a"
        task_a.depends_on = ["task_a"]

        registry = TaskRegistry([task_a])
        validator = DependencyValidator()

        with pytest.raises(DependencyError, match="Cyclic dependency detected"):
            validator.validate(["task_a"], registry)

    def test_validate_multiple_missing_tasks(self) -> None:
        """Тест проверяет обнаружение нескольких отсутствующих задач."""
        task1 = Mock(spec=Task)
        task1.name = "task1"
        task1.depends_on = []

        registry = TaskRegistry([task1])
        validator = DependencyValidator()

        with pytest.raises(DependencyError, match="not found in registry"):
            validator.validate(
                ["task1", "missing1", "missing2"], registry
            )

    def test_validate_multiple_missing_dependencies(self) -> None:
        """Тест проверяет обнаружение нескольких отсутствующих зависимостей."""
        task1 = Mock(spec=Task)
        task1.name = "task1"
        task1.depends_on = ["dep1", "dep2"]

        registry = TaskRegistry([task1])
        validator = DependencyValidator()

        with pytest.raises(
            DependencyError, match="depends on tasks not in task_order"
        ):
            validator.validate(["task1"], registry)

    def test_validate_multiple_wrong_order_dependencies(self) -> None:
        """Тест проверяет обнаружение нескольких зависимостей с неправильным порядком."""
        task1 = Mock(spec=Task)
        task1.name = "task1"
        task1.depends_on = []

        task2 = Mock(spec=Task)
        task2.name = "task2"
        task2.depends_on = []

        task3 = Mock(spec=Task)
        task3.name = "task3"
        task3.depends_on = ["task1", "task2"]

        registry = TaskRegistry([task1, task2, task3])
        validator = DependencyValidator()

        # task3 идет перед task1 и task2, но зависит от них
        with pytest.raises(
            DependencyError, match="depends on tasks that come after it"
        ):
            validator.validate(["task3", "task1", "task2"], registry)

    def test_validate_empty_task_order(self) -> None:
        """Тест валидации пустого списка задач."""
        registry = TaskRegistry()
        validator = DependencyValidator()

        # Пустой список должен проходить валидацию
        validator.validate([], registry)

    def test_validate_single_task_no_dependencies(self) -> None:
        """Тест валидации одной задачи без зависимостей."""
        task1 = Mock(spec=Task)
        task1.name = "task1"
        task1.depends_on = []

        registry = TaskRegistry([task1])
        validator = DependencyValidator()

        validator.validate(["task1"], registry)

    def test_validate_dependencies_not_in_task_order_ignored(self) -> None:
        """Тест проверяет, что зависимости вне task_order игнорируются при проверке порядка."""
        task1 = Mock(spec=Task)
        task1.name = "task1"
        task1.depends_on = []

        task2 = Mock(spec=Task)
        task2.name = "task2"
        task2.depends_on = ["task1", "external_task"]  # external_task не в task_order

        registry = TaskRegistry([task1, task2])
        validator = DependencyValidator()

        # external_task не в task_order, но это не должно вызывать ошибку порядка
        # Однако должна быть ошибка о том, что external_task не в task_order
        with pytest.raises(
            DependencyError, match="depends on tasks not in task_order"
        ):
            validator.validate(["task1", "task2"], registry)

    def test_validate_complex_valid_scenario(self) -> None:
        """Тест сложного корректного сценария с множественными зависимостями."""
        # Создаем граф: A -> B, A -> C, B -> D, C -> D, D -> E
        tasks = {}
        for name in ["task_a", "task_b", "task_c", "task_d", "task_e"]:
            task = Mock(spec=Task)
            task.name = name
            task.depends_on = []
            tasks[name] = task

        tasks["task_b"].depends_on = ["task_a"]
        tasks["task_c"].depends_on = ["task_a"]
        tasks["task_d"].depends_on = ["task_b", "task_c"]
        tasks["task_e"].depends_on = ["task_d"]

        registry = TaskRegistry(list(tasks.values()))
        validator = DependencyValidator()

        # Валидный порядок
        validator.validate(
            ["task_a", "task_b", "task_c", "task_d", "task_e"], registry
        )

