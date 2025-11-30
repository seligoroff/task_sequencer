"""Валидаторы для task-sequencer."""

from __future__ import annotations

from typing import TYPE_CHECKING

from task_sequencer.exceptions import DependencyError

if TYPE_CHECKING:
    from task_sequencer.core import TaskRegistry


class DependencyValidator:
    """Валидатор зависимостей между задачами.

    Проверяет корректность зависимостей в списке задач:
    - Все задачи существуют в реестре
    - Все зависимости присутствуют в task_order
    - Отсутствие циклических зависимостей
    - Порядок задач соответствует зависимостям

    Пример использования:
        >>> from task_sequencer import TaskRegistry, DependencyValidator
        >>> from task_sequencer.interfaces import Task, TaskResult, ExecutionContext
        >>>
        >>> class Task1(Task):
        ...     @property
        ...     def name(self) -> str:
        ...         return "task1"
        ...     @property
        ...     def depends_on(self) -> list[str]:
        ...         return []
        ...     def execute(self, context: ExecutionContext) -> TaskResult:
        ...         return TaskResult.success_result()
        >>>
        >>> class Task2(Task):
        ...     @property
        ...     def name(self) -> str:
        ...         return "task2"
        ...     @property
        ...     def depends_on(self) -> list[str]:
        ...         return ["task1"]
        ...     def execute(self, context: ExecutionContext) -> TaskResult:
        ...         return TaskResult.success_result()
        >>>
        >>> registry = TaskRegistry([Task1(), Task2()])
        >>> validator = DependencyValidator()
        >>> validator.validate(["task1", "task2"], registry)  # OK
        >>> validator.validate(["task2", "task1"], registry)  # Raises DependencyError
    """

    def validate(
        self, task_order: list[str], registry: "TaskRegistry"
    ) -> None:
        """Валидирует зависимости между задачами.

        Проверяет:
        - Все задачи из task_order существуют в реестре
        - Все зависимости задач присутствуют в task_order
        - Отсутствие циклических зависимостей
        - Порядок задач соответствует зависимостям

        Args:
            task_order: Список имен задач в порядке выполнения
            registry: Реестр задач

        Raises:
            DependencyError: Если обнаружены нарушения зависимостей:
                - Задача не найдена в реестре
                - Зависимость отсутствует в task_order
                - Обнаружены циклические зависимости
                - Порядок задач не соответствует зависимостям

        Пример:
            >>> registry = TaskRegistry([Task1(), Task2()])
            >>> validator = DependencyValidator()
            >>>
            >>> # Правильный порядок
            >>> validator.validate(["task1", "task2"], registry)  # OK
            >>>
            >>> # Неправильный порядок (task2 зависит от task1)
            >>> try:
            ...     validator.validate(["task2", "task1"], registry)
            ... except DependencyError as e:
            ...     print(f"Error: {e}")
        """
        self._check_all_tasks_exist(task_order, registry)
        self._check_cyclic_dependencies(task_order, registry)
        self._check_dependencies_in_order(task_order, registry)

    def _check_all_tasks_exist(
        self, task_order: list[str], registry: "TaskRegistry"
    ) -> None:
        """Проверяет, что все задачи из task_order существуют в реестре.

        Args:
            task_order: Список имен задач
            registry: Реестр задач

        Raises:
            DependencyError: Если какая-то задача не найдена в реестре
        """
        missing_tasks = []
        for task_name in task_order:
            try:
                registry.get(task_name)
            except KeyError:
                missing_tasks.append(task_name)

        if missing_tasks:
            tasks_str = ", ".join(f"'{t}'" for t in missing_tasks)
            raise DependencyError(
                f"Tasks not found in registry: {tasks_str}"
            )

    def _check_dependencies_in_order(
        self, task_order: list[str], registry: "TaskRegistry"
    ) -> None:
        """Проверяет, что все зависимости присутствуют в task_order и порядок корректен.

        Args:
            task_order: Список имен задач в порядке выполнения
            registry: Реестр задач

        Raises:
            DependencyError: Если зависимость отсутствует в task_order или порядок нарушен
        """
        task_order_set = set(task_order)
        task_positions = {task_name: i for i, task_name in enumerate(task_order)}

        for task_name in task_order:
            task = registry.get(task_name)
            dependencies = task.depends_on

            # Проверяем, что все зависимости присутствуют в task_order
            missing_deps = [
                dep for dep in dependencies if dep not in task_order_set
            ]
            if missing_deps:
                deps_str = ", ".join(f"'{d}'" for d in missing_deps)
                raise DependencyError(
                    f"Task '{task_name}' depends on tasks not in task_order: {deps_str}"
                )

            # Проверяем, что все зависимости выполняются раньше
            task_position = task_positions[task_name]
            invalid_order_deps = []
            for dep in dependencies:
                dep_position = task_positions[dep]
                if dep_position >= task_position:
                    invalid_order_deps.append(dep)

            if invalid_order_deps:
                deps_str = ", ".join(f"'{d}'" for d in invalid_order_deps)
                error_msg = (
                    f"Task '{task_name}' depends on tasks that come "
                    f"after it in task_order: {deps_str}"
                )
                raise DependencyError(error_msg)

    def _check_cyclic_dependencies(
        self, task_order: list[str], registry: "TaskRegistry"
    ) -> None:
        """Проверяет отсутствие циклических зависимостей (DFS, O(n)).

        Args:
            task_order: Список имен задач
            registry: Реестр задач

        Raises:
            DependencyError: Если обнаружены циклические зависимости
        """
        # Строим граф зависимостей
        graph: dict[str, list[str]] = {}
        for task_name in task_order:
            task = registry.get(task_name)
            # Берем только зависимости, которые есть в task_order
            graph[task_name] = [
                dep for dep in task.depends_on if dep in task_order
            ]

        # DFS для поиска циклов
        visited: set[str] = set()
        rec_stack: set[str] = set()

        def has_cycle(node: str, path: list[str] | None = None) -> bool:
            """Проверяет наличие цикла начиная с узла.

            Args:
                node: Текущий узел для проверки
                path: Путь от корня до текущего узла

            Returns:
                True если найден цикл
            """
            if path is None:
                path = []

            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    if has_cycle(neighbor, path):
                        return True
                elif neighbor in rec_stack:
                    # Найден цикл - строим путь цикла
                    cycle_start_idx = path.index(neighbor)
                    cycle = path[cycle_start_idx:] + [neighbor]
                    cycle_str = " -> ".join(cycle)
                    raise DependencyError(
                        f"Cyclic dependency detected: {cycle_str}"
                    )

            rec_stack.remove(node)
            path.pop()
            return False

        # Проверяем все узлы
        for task_name in task_order:
            if task_name not in visited:
                has_cycle(task_name)

