"""Тесты для ParameterizedIterableTask."""

from __future__ import annotations

from typing import Any

import pytest

from task_sequencer.interfaces import (
    ExecutionContext,
    ParameterizedIterableTask,
    TaskResult,
)
from task_sequencer.progress import TaskStatus


class TestParameterizedIterableTask:
    """Тесты для ParameterizedIterableTask."""

    def test_parameterized_task_implementation(self) -> None:
        """Тест базовой реализации ParameterizedIterableTask."""

        class StringParamTask(ParameterizedIterableTask[str]):
            def __init__(self) -> None:
                super().__init__()
                self.processed: list[str] = []

            @property
            def name(self) -> str:
                return "string_param_task"

            @property
            def depends_on(self) -> list[str]:
                return []

            def get_parameters(self, context: ExecutionContext) -> list[str]:
                return ["param1", "param2", "param3"]

            def execute_for_parameter(
                self, param: str, context: ExecutionContext
            ) -> None:
                self.processed.append(param)


        task = StringParamTask()
        context = ExecutionContext(
            task_order=["string_param_task"],
            results={},
            metadata={},
            progress_tracker=None,
            mode="run",
        )

        result = task.execute(context)

        assert result.success is True
        assert result.status == TaskStatus.COMPLETED
        assert task.processed == ["param1", "param2", "param3"]
        assert result.data["processed"] == 3
        assert result.data["total"] == 3

    def test_get_items_uses_get_parameters(self) -> None:
        """Тест, что get_items использует get_parameters."""

        class IntParamTask(ParameterizedIterableTask[int]):
            @property
            def name(self) -> str:
                return "int_param_task"

            @property
            def depends_on(self) -> list[str]:
                return []

            def get_parameters(self, context: ExecutionContext) -> list[int]:
                return [1, 2, 3]

            def execute_for_parameter(
                self, param: int, context: ExecutionContext
            ) -> None:
                pass


        task = IntParamTask()
        context = ExecutionContext(
            task_order=["int_param_task"],
            results={},
            metadata={},
            progress_tracker=None,
            mode="run",
        )

        items = list(task.get_items(context))
        assert items == [1, 2, 3]

    def test_execute_for_item_calls_execute_for_parameter(self) -> None:
        """Тест, что execute_for_item вызывает execute_for_parameter."""

        class TestTask(ParameterizedIterableTask[str]):
            def __init__(self) -> None:
                super().__init__()
                self.called_with: list[str] = []

            @property
            def name(self) -> str:
                return "test_task"

            @property
            def depends_on(self) -> list[str]:
                return []

            def get_parameters(self, context: ExecutionContext) -> list[str]:
                return []

            def execute_for_parameter(
                self, param: str, context: ExecutionContext
            ) -> None:
                self.called_with.append(param)


        task = TestTask()
        context = ExecutionContext(
            task_order=["test_task"],
            results={},
            metadata={},
            progress_tracker=None,
            mode="run",
        )

        task.execute_for_item("test_param", context)
        assert task.called_with == ["test_param"]

    def test_parameterized_task_with_context_data(self) -> None:
        """Тест ParameterizedIterableTask с данными из контекста."""

        class ContextParamTask(ParameterizedIterableTask[str]):
            def __init__(self) -> None:
                super().__init__()
                self.processed: list[str] = []

            @property
            def name(self) -> str:
                return "context_param_task"

            @property
            def depends_on(self) -> list[str]:
                return ["source_task"]

            def get_parameters(self, context: ExecutionContext) -> list[str]:
                source_result = context.results.get("source_task")
                if source_result and source_result.data:
                    return source_result.data.get("items", [])
                return []

            def execute_for_parameter(
                self, param: str, context: ExecutionContext
            ) -> None:
                self.processed.append(param)


        task = ContextParamTask()
        context = ExecutionContext(
            task_order=["source_task", "context_param_task"],
            results={
                "source_task": TaskResult.success_result(
                    data={"items": ["item1", "item2"]}
                )
            },
            metadata={},
            progress_tracker=None,
            mode="run",
        )

        result = task.execute(context)

        assert result.success is True
        assert task.processed == ["item1", "item2"]
        assert result.data["processed"] == 2
        assert result.data["total"] == 2

    def test_abstract_methods_must_be_implemented(self) -> None:
        """Тест, что абстрактные методы должны быть реализованы."""

        class IncompleteTask(ParameterizedIterableTask[str]):
            @property
            def name(self) -> str:
                return "incomplete_task"

            @property
            def depends_on(self) -> list[str]:
                return []

            # Не реализованы get_parameters, execute_for_parameter и execute

        with pytest.raises(TypeError):
            IncompleteTask()

    def test_error_strategy_stop(self) -> None:
        """Тест стратегии обработки ошибок 'stop'."""
        class FailingTask(ParameterizedIterableTask[str]):
            def __init__(self) -> None:
                super().__init__(error_strategy="stop")
                self.processed: list[str] = []

            @property
            def name(self) -> str:
                return "failing_task"

            @property
            def depends_on(self) -> list[str]:
                return []

            def get_parameters(self, context: ExecutionContext) -> list[str]:
                return ["param1", "param2", "param3"]

            def execute_for_parameter(
                self, param: str, context: ExecutionContext
            ) -> None:
                if param == "param2":
                    raise ValueError(f"Error processing {param}")
                self.processed.append(param)

        task = FailingTask()
        context = ExecutionContext(
            task_order=["failing_task"],
            results={},
            metadata={},
            progress_tracker=None,
            mode="run",
        )

        result = task.execute(context)

        assert result.success is False
        assert result.status == TaskStatus.FAILED
        assert task.processed == ["param1"]  # Остановилось на первой ошибке
        assert "errors" in result.data
        assert len(result.data["errors"]) == 1
        assert result.data["errors"][0][0] == "param2"

    def test_error_strategy_continue(self) -> None:
        """Тест стратегии обработки ошибок 'continue'."""
        class FailingTask(ParameterizedIterableTask[str]):
            def __init__(self) -> None:
                super().__init__(error_strategy="continue")
                self.processed: list[str] = []

            @property
            def name(self) -> str:
                return "failing_task"

            @property
            def depends_on(self) -> list[str]:
                return []

            def get_parameters(self, context: ExecutionContext) -> list[str]:
                return ["param1", "param2", "param3"]

            def execute_for_parameter(
                self, param: str, context: ExecutionContext
            ) -> None:
                if param == "param2":
                    raise ValueError(f"Error processing {param}")
                self.processed.append(param)

        task = FailingTask()
        context = ExecutionContext(
            task_order=["failing_task"],
            results={},
            metadata={},
            progress_tracker=None,
            mode="run",
        )

        result = task.execute(context)

        assert result.success is False
        assert result.status == TaskStatus.FAILED
        assert task.processed == ["param1", "param3"]  # Продолжило выполнение
        assert "errors" in result.data
        assert len(result.data["errors"]) == 1
        assert result.data["errors"][0][0] == "param2"
        assert result.data["processed"] == 2

    def test_error_strategy_retry(self) -> None:
        """Тест стратегии обработки ошибок 'retry'."""
        class RetryTask(ParameterizedIterableTask[str]):
            def __init__(self) -> None:
                super().__init__(error_strategy="retry", max_retries=2)
                self.processed: list[str] = []
                self.attempts: dict[str, int] = {}

            @property
            def name(self) -> str:
                return "retry_task"

            @property
            def depends_on(self) -> list[str]:
                return []

            def get_parameters(self, context: ExecutionContext) -> list[str]:
                return ["param1", "param2"]

            def execute_for_parameter(
                self, param: str, context: ExecutionContext
            ) -> None:
                self.attempts[param] = self.attempts.get(param, 0) + 1
                if param == "param1" and self.attempts[param] < 2:
                    raise ValueError(f"Error processing {param}")
                self.processed.append(param)

        task = RetryTask()
        context = ExecutionContext(
            task_order=["retry_task"],
            results={},
            metadata={},
            progress_tracker=None,
            mode="run",
        )

        result = task.execute(context)

        assert result.success is True
        assert result.status == TaskStatus.COMPLETED
        assert task.processed == ["param1", "param2"]  # Успешно после повтора
        assert task.attempts["param1"] == 2  # Было 2 попытки

    def test_custom_on_error(self) -> None:
        """Тест кастомной обработки ошибок через on_error."""
        class CustomErrorTask(ParameterizedIterableTask[str]):
            def __init__(self) -> None:
                super().__init__(error_strategy="stop")
                self.processed: list[str] = []
                self.errors_logged: list[tuple[str, str]] = []

            @property
            def name(self) -> str:
                return "custom_error_task"

            @property
            def depends_on(self) -> list[str]:
                return []

            def get_parameters(self, context: ExecutionContext) -> list[str]:
                return ["param1", "param2", "param3"]

            def execute_for_parameter(
                self, param: str, context: ExecutionContext
            ) -> None:
                if param == "param2":
                    raise ValueError(f"Error processing {param}")
                self.processed.append(param)

            def on_error(
                self, param: str, error: Exception, context: ExecutionContext
            ) -> bool:
                """Кастомная обработка - логируем и продолжаем."""
                self.errors_logged.append((param, str(error)))
                return True  # Продолжить выполнение

        task = CustomErrorTask()
        context = ExecutionContext(
            task_order=["custom_error_task"],
            results={},
            metadata={},
            progress_tracker=None,
            mode="run",
        )

        result = task.execute(context)

        assert result.success is False
        assert result.status == TaskStatus.FAILED
        assert task.processed == ["param1", "param3"]  # Продолжило благодаря on_error
        assert len(task.errors_logged) == 1
        assert task.errors_logged[0][0] == "param2"

    def test_error_strategy_retry_invalid_max_retries(self) -> None:
        """Тест проверки валидности max_retries для стратегии 'retry'."""
        with pytest.raises(ValueError, match="max_retries must be > 0"):
            class InvalidRetryTask(ParameterizedIterableTask[str]):
                def __init__(self) -> None:
                    super().__init__(error_strategy="retry", max_retries=0)

                @property
                def name(self) -> str:
                    return "invalid_retry_task"

                @property
                def depends_on(self) -> list[str]:
                    return []

                def get_parameters(self, context: ExecutionContext) -> list[str]:
                    return []

                def execute_for_parameter(
                    self, param: str, context: ExecutionContext
                ) -> None:
                    pass

            InvalidRetryTask()


