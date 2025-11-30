# Task Sequencer

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

Универсальный Python-компонент для управления последовательным выполнением задач с зависимостями, отслеживанием прогресса и возможностью восстановления с места остановки.

## Описание

`task-sequencer` — это переиспользуемый компонент, он предоставляет гибкий механизм для управления последовательным выполнением задач с поддержкой зависимостей, отслеживания прогресса и восстановления после прерываний.

Компонент абстрагирован от доменной логики и работает через интерфейсы (ABC), что делает его универсальным для различных сценариев использования.

## Основные возможности

- ✅ **Управление порядком выполнения** — задачи выполняются в указанном порядке с проверкой зависимостей
- ✅ **Отслеживание прогресса** — детальное отслеживание состояния выполнения каждой задачи
- ✅ **Восстановление с места остановки** — возможность продолжить выполнение после прерывания
- ✅ **Валидация зависимостей** — автоматическая проверка корректности зависимостей между задачами
- ✅ **Итеративные задачи** — поддержка обработки коллекций элементов с возможностью прерывания
- ✅ **Гибкое хранилище прогресса** — поддержка различных адаптеров (Memory, MySQL, MongoDB, PostgreSQL)

## Установка

### Базовая установка

```bash
pip install task-sequencer
```

### С опциональными зависимостями

Для использования адаптеров БД установите соответствующие опциональные зависимости:

```bash
# MySQL адаптер
pip install task-sequencer[mysql]

# MongoDB адаптер
pip install task-sequencer[mongodb]

# PostgreSQL адаптер
pip install task-sequencer[postgresql]

# Все адаптеры
pip install task-sequencer[mysql,mongodb,postgresql]
```

## Быстрый старт

Минимальный пример использования библиотеки для выполнения простой задачи:

```python
from task_sequencer import Task, TaskRegistry, TaskOrchestrator, DependencyValidator
from task_sequencer.adapters import MemoryProgressTracker

# 1. Определяем задачу
class MyTask(Task):
    @property
    def name(self) -> str:
        return "my_task"
    
    @property
    def depends_on(self) -> list[str]:
        return []
    
    def execute(self, context):
        print("Task executed!")
        return TaskResult.success_result()

# 2. Создаем компоненты
registry = TaskRegistry([MyTask()])
tracker = MemoryProgressTracker()
validator = DependencyValidator()
orchestrator = TaskOrchestrator(registry, tracker, validator)

# 3. Выполняем задачу
result = orchestrator.execute(["my_task"])
print(f"Status: {result.status.value}")
```

### Простой пример

```python
from task_sequencer import (
    DependencyValidator,
    ExecutionContext,
    Task,
    TaskOrchestrator,
    TaskRegistry,
    TaskResult,
)
from task_sequencer.adapters.memory import MemoryProgressTracker


class MyTask(Task):
    """Простая задача."""

    @property
    def name(self) -> str:
        return "my_task"

    @property
    def depends_on(self) -> list[str]:
        return []

    def execute(self, context: ExecutionContext) -> TaskResult:
        print("Executing task...")
        return TaskResult.success_result(data={"message": "Task completed"})


# Создаем компоненты
registry = TaskRegistry([MyTask()])
tracker = MemoryProgressTracker()
validator = DependencyValidator()
orchestrator = TaskOrchestrator(registry, tracker, validator)

# Выполняем задачу
result = orchestrator.execute(["my_task"])

print(f"Status: {result.status.value}")
print(f"Completed: {result.completed_tasks}")
```

### Пример с зависимостями

```python
class TaskA(Task):
    @property
    def name(self) -> str:
        return "task_a"

    @property
    def depends_on(self) -> list[str]:
        return []

    def execute(self, context: ExecutionContext) -> TaskResult:
        return TaskResult.success_result()


class TaskB(Task):
    @property
    def name(self) -> str:
        return "task_b"

    @property
    def depends_on(self) -> list[str]:
        return ["task_a"]  # Зависит от task_a

    def execute(self, context: ExecutionContext) -> TaskResult:
        return TaskResult.success_result()


registry = TaskRegistry([TaskA(), TaskB()])
tracker = MemoryProgressTracker()
validator = DependencyValidator()
orchestrator = TaskOrchestrator(registry, tracker, validator)

# task_a выполнится первой, затем task_b
result = orchestrator.execute(["task_a", "task_b"])
```

### Пример с ParameterizedIterableTask

Для задач, которые обрабатывают элементы, зависящие от результатов предыдущих задач:

```python
from task_sequencer import ParameterizedIterableTask
from task_sequencer.interfaces import ExecutionContext, TaskResult

class ProcessStatsForMatchTask(ParameterizedIterableTask[str]):
    @property
    def name(self) -> str:
        return "process_stats_for_match"
    
    @property
    def depends_on(self) -> list[str]:
        return ["extract_matches"]
    
    def get_parameters(self, context: ExecutionContext) -> list[str]:
        """Получает параметры из результата предыдущей задачи."""
        extract_result = context.results.get("extract_matches")
        if extract_result and extract_result.data:
            return extract_result.data.get("match_ids", [])
        return []
    
    def execute_for_parameter(self, match_id: str, context: ExecutionContext) -> None:
        """Обрабатывает один параметр."""
        print(f"Processing match: {match_id}")
    
    def execute(self, context: ExecutionContext) -> TaskResult:
        for param in self.get_parameters(context):
            self.execute_for_parameter(param, context)
        return TaskResult.success_result()
```

См. полный пример в `examples/parameterized_task_example.py`.

### Пример с итеративной задачей и восстановлением

```python
from task_sequencer import IterableTask
from task_sequencer.iterators import ResumeIterator


class ProcessItemsTask(IterableTask):
    @property
    def name(self) -> str:
        return "process_items"

    @property
    def depends_on(self) -> list[str]:
        return []

    def execute(self, context: ExecutionContext) -> TaskResult:
        items = list(self.get_items(context))
        
        # Используем ResumeIterator для поддержки восстановления
        if context.metadata.get("resume", False):
            id_extractor = lambda x: x["id"]
            items_iterator = ResumeIterator(
                items=items,
                progress_tracker=context.progress_tracker,
                task_name=self.name,
                id_extractor=id_extractor,
            )
        else:
            items_iterator = iter(items)
        
        for item in items_iterator:
            self.execute_for_item(item, context)
        
        return TaskResult.success_result()

    def get_items(self, context: ExecutionContext) -> list[dict]:
        return [{"id": str(i), "data": f"item_{i}"} for i in range(1, 101)]

    def execute_for_item(self, item: dict, context: ExecutionContext) -> None:
        # Обработка элемента
        print(f"Processing {item['id']}")


# Первый запуск
orchestrator.execute(["process_items"])

# Второй запуск с восстановлением
orchestrator.execute(["process_items"], resume=True)
```

## Логирование

`task-sequencer` использует стандартный модуль `logging` для отслеживания прогресса выполнения задач.

### Настройка логирования

```python
from task_sequencer.logging import setup_logging
import logging

# Настройка логирования с уровнем INFO
setup_logging(logging.INFO)

# Или используйте стандартную настройку Python logging
import logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(name)s: %(message)s'
)
```

### Примеры логов

При выполнении задач вы увидите логи вида:

```
[task-sequencer] core: Starting execution of 2 tasks
[task-sequencer] task1: Task started
[task-sequencer] task1: Task completed successfully
[task-sequencer] task2: Task started
[task-sequencer] task2: Processing 100 items
[task-sequencer] task2: Task completed: 100/100 items processed
[task-sequencer] core: Execution completed: 2 completed, 0 failed
```

## Примеры использования

В папке `examples/` доступны полные примеры:

- **`basic_usage.py`** — простой пример с одной задачей
- **`etl_example.py`** — пример ETL процесса с зависимостями
- **`sync_example.py`** — пример синхронизации данных с восстановлением
- **`parameterized_task_example.py`** — пример использования ParameterizedIterableTask
- **`adapters_usage.py`** — примеры использования всех адаптеров ProgressTracker
- **`custom_tracker.py`** — пример создания кастомного ProgressTracker

Запуск примеров:

```bash
python examples/basic_usage.py
python examples/etl_example.py
python examples/sync_example.py
python examples/adapters_usage.py
python examples/custom_tracker.py
```

## API Reference

### TaskOrchestrator

Основной класс для управления выполнением задач.

**Инициализация:**
```python
from task_sequencer import TaskOrchestrator, TaskRegistry, DependencyValidator
from task_sequencer.adapters import MemoryProgressTracker

orchestrator = TaskOrchestrator(
    task_registry=TaskRegistry([...]),
    progress_tracker=MemoryProgressTracker(),
    dependency_validator=DependencyValidator(),
)
```

**Методы:**

- `execute(task_order: list[str], mode: str = "run", resume: bool = False) -> ExecutionResult`
  - Выполняет задачи в указанном порядке
  - `task_order`: список имен задач в порядке выполнения
  - `mode`: режим выполнения (`"run"`, `"dry-run"`, `"resume"`)
  - `resume`: если `True`, продолжает выполнение с места остановки

**Пример:**
```python
result = orchestrator.execute(
    task_order=["task1", "task2"],
    mode="run",
    resume=False,
)

print(f"Status: {result.status.value}")
print(f"Completed: {result.completed_tasks}")
print(f"Failed: {result.failed_tasks}")
```

### TaskRegistry

Реестр задач для управления и доступа к задачам.

**Инициализация:**
```python
from task_sequencer import TaskRegistry, Task

registry = TaskRegistry([Task1(), Task2()])
```

**Методы:**

- `register(task: Task) -> None` - регистрирует задачу
- `get(task_name: str) -> Task` - получает задачу по имени (выбрасывает `KeyError` если не найдена)
- `get_all() -> list[Task]` - получает все зарегистрированные задачи

**Pythonic API (рекомендуется):**

- `task_name in registry` - проверка наличия задачи (оператор `in`)
- `registry[task_name]` - получение задачи через оператор `[]`
- `registry.tasks` - словарь всех задач (read-only, `dict[str, Task]`)

**Пример:**
```python
# Регистрация задачи
registry.register(MyTask())

# Проверка наличия задачи (новый способ - Pythonic)
if "my_task" in registry:
    task = registry["my_task"]
    print("Task found")

# Получение задачи через оператор [] (новый способ - Pythonic)
task = registry["my_task"]

# Получение словаря всех задач (новый способ - Pythonic)
all_tasks = registry.tasks  # dict[str, Task]
for name, task in all_tasks.items():
    print(f"{name}: {task}")

# Старые методы продолжают работать (обратная совместимость)
try:
    task = registry.get("my_task")
except KeyError:
    print("Task not found")

all_tasks_list = registry.get_all()  # list[Task]
```

### DependencyValidator

Валидатор зависимостей между задачами.

**Инициализация:**
```python
from task_sequencer import DependencyValidator

validator = DependencyValidator()
```

**Методы:**

- `validate(task_order: list[str], registry: TaskRegistry) -> None`
  - Валидирует зависимости между задачами
  - Выбрасывает `DependencyError` при обнаружении проблем:
    - Задача не найдена в реестре
    - Циклические зависимости
    - Зависимости не присутствуют в `task_order`
    - Порядок задач не соответствует зависимостям

**Пример:**
```python
from task_sequencer import DependencyError

try:
    validator.validate(["task1", "task2"], registry)
    print("Dependencies are valid")
except DependencyError as e:
    print(f"Dependency error: {e}")
```

### Task, IterableTask, ParameterizedIterableTask

Абстрактные классы для определения задач.

**Task** - базовая задача:
```python
from task_sequencer import Task, TaskResult, ExecutionContext

class MyTask(Task):
    @property
    def name(self) -> str:
        return "my_task"

    @property
    def depends_on(self) -> list[str]:
        return ["other_task"]  # Зависимости

    def execute(self, context: ExecutionContext) -> TaskResult:
        # Логика выполнения
        return TaskResult.success_result(data={"result": "ok"})
```

**IterableTask** - задача для обработки коллекций:
```python
from task_sequencer import IterableTask

class ProcessItemsTask(IterableTask):
    @property
    def name(self) -> str:
        return "process_items"
    
    def get_items(self, context: ExecutionContext) -> list[Any]:
        return [1, 2, 3, 4, 5]
    
    def execute_for_item(self, item: Any, context: ExecutionContext) -> None:
        print(f"Processing {item}")
```

**ParameterizedIterableTask** - задача с параметрами из предыдущих задач:
```python
from task_sequencer import ParameterizedIterableTask

class ProcessForMatchTask(ParameterizedIterableTask[str]):
    @property
    def name(self) -> str:
        return "process_for_match"
    
    @property
    def depends_on(self) -> list[str]:
        return ["extract_matches"]
    
    def get_parameters(self, context: ExecutionContext) -> list[str]:
        result = context.results.get("extract_matches")
        return result.data.get("match_ids", []) if result else []
    
    def execute_for_parameter(self, match_id: str, context: ExecutionContext) -> None:
        print(f"Processing match {match_id}")
```

**Обработка ошибок в ParameterizedIterableTask:**

По умолчанию выполнение останавливается при первой ошибке. Можно настроить стратегию обработки ошибок:

```python
# Продолжить выполнение при ошибке
class MyTask(ParameterizedIterableTask[str]):
    def __init__(self):
        super().__init__(error_strategy="continue")
    
    # ... остальные методы ...

# Повторить попытку при ошибке
class MyTask(ParameterizedIterableTask[str]):
    def __init__(self):
        super().__init__(error_strategy="retry", max_retries=3)
    
    # ... остальные методы ...

# Кастомная обработка ошибок
class MyTask(ParameterizedIterableTask[str]):
    def on_error(self, param: str, error: Exception, context: ExecutionContext) -> bool:
        # Логируем ошибку
        logger.error(f"Error processing {param}: {error}")
        # Продолжаем для остальных элементов
        return True
```

**Стратегии обработки ошибок:**
- `"stop"` (по умолчанию) - остановить выполнение при первой ошибке
- `"continue"` - продолжить выполнение для остальных элементов
- `"retry"` - повторить попытку (требует `max_retries > 0`)

### ProgressTracker

Абстрактный класс для отслеживания прогресса. Все трекеры реализуют следующие методы:

**Методы:**

- `save_progress(task_name: str, progress: TaskProgress) -> None` - сохраняет прогресс
- `get_progress(task_name: str) -> TaskProgress | None` - получает сохраненный прогресс
- `mark_completed(task_name: str) -> None` - отмечает задачу как завершенную
- `clear_progress(task_name: str) -> None` - очищает прогресс
- `transaction() -> ContextManager[None]` - контекстный менеджер для транзакций

**Реализации:**

- `MemoryProgressTracker` — хранение в памяти (встроенный, не требует зависимостей)
- `MySQLProgressTracker` — MySQL (требует `task-sequencer[mysql]`)
- `MongoDBProgressTracker` — MongoDB (требует `task-sequencer[mongodb]`)
- `PostgreSQLProgressTracker` — PostgreSQL (требует `task-sequencer[postgresql]`)

**Пример создания кастомного трекера:**
```python
from task_sequencer.interfaces import ProgressTracker
from task_sequencer.progress import TaskProgress, TaskStatus

class MyProgressTracker(ProgressTracker):
    def __init__(self):
        self._storage = {}
    
    def save_progress(self, task_name: str, progress: TaskProgress) -> None:
        self._storage[task_name] = progress
    
    def get_progress(self, task_name: str) -> TaskProgress | None:
        return self._storage.get(task_name)
    
    def mark_completed(self, task_name: str) -> None:
        if task_name in self._storage:
            self._storage[task_name].status = TaskStatus.COMPLETED
    
    def clear_progress(self, task_name: str) -> None:
        self._storage.pop(task_name, None)
    
    def transaction(self):
        from contextlib import nullcontext
        return nullcontext()  # Для in-memory трекера транзакции не нужны
```

## Database Adapters

Библиотека предоставляет адаптеры для хранения прогресса в различных базах данных.

### MemoryProgressTracker

Встроенный трекер, хранящий данные в памяти. Не требует зависимостей.

```python
from task_sequencer.adapters import MemoryProgressTracker

tracker = MemoryProgressTracker()
```

**Особенности:**
- Данные теряются при перезапуске приложения
- Подходит для тестирования и простых случаев
- Не требует настройки

### MongoDBProgressTracker

Трекер для MongoDB. Требует установки `task-sequencer[mongodb]`.

**Параметры конструктора:**

- `connection_string: str` - строка подключения к MongoDB
  - Формат: `mongodb://[username:password@]host[:port][/database]`
  - **Улучшение**: Если `database_name` не указан, автоматически извлекается из connection string
- `database_name: str | None = None` - имя базы данных (опционально)
  - Если `None`, автоматически извлекается из connection string
  - Если не найдено, используется `"task_sequencer"` по умолчанию
  - Если указан явно, используется он (приоритет над connection string)
- `collection_name: str = "task_progress"` - имя коллекции для хранения прогресса

**Примеры:**

```python
from task_sequencer.adapters import MongoDBProgressTracker

# Автоматическое извлечение database_name (новый способ - упрощенный)
tracker = MongoDBProgressTracker(
    connection_string="mongodb://user:pass@host:27017/task_sequencer"
    # database_name извлечется автоматически
)

# Явное указание database_name (приоритет над connection string)
tracker = MongoDBProgressTracker(
    connection_string="mongodb://localhost:27017/",
    database_name="my_database"
)

# Без database в connection string - используется значение по умолчанию
tracker = MongoDBProgressTracker(
    connection_string="mongodb://localhost:27017/"
    # database_name будет "task_sequencer" по умолчанию
)
```

**Особенности:**
- Автоматически создает индекс по `task_name` для быстрого поиска
- Требует установки `pymongo>=4.0.0`

### MySQLProgressTracker

Трекер для MySQL. Требует установки `task-sequencer[mysql]`.

**Параметры конструктора:**

- `connection_string: str` - строка подключения к MySQL
  - Формат SQLAlchemy: `mysql+pymysql://user:password@host:port[/database]`
  - **Улучшение**: Если `database_name` указан, он используется вместо значения из connection string
- `create_tables: bool = True` - если `True`, создает таблицы при инициализации
- `database_name: str | None = None` - имя базы данных (опционально)
  - Если указан, используется вместо значения из connection string
  - Если `None`, используется значение из connection string
- `table_name: str | None = None` - имя таблицы для хранения прогресса (опционально)
  - Если указан, используется вместо `"task_progress"`
  - Если `None`, используется `"task_progress"`

**Примеры:**

```python
from task_sequencer.adapters import MySQLProgressTracker

# Старый способ (все еще работает)
tracker = MySQLProgressTracker(
    connection_string="mysql+pymysql://user:password@localhost:3306/task_sequencer",
    create_tables=True
)

# Новый способ с database_name
tracker = MySQLProgressTracker(
    connection_string="mysql+pymysql://user:password@localhost:3306/",
    database_name="task_sequencer",
    create_tables=True
)

# Новый способ с table_name
tracker = MySQLProgressTracker(
    connection_string="mysql+pymysql://user:password@localhost:3306/task_sequencer",
    table_name="my_progress",
    create_tables=True
)

# Комбинация database_name и table_name
tracker = MySQLProgressTracker(
    connection_string="mysql+pymysql://user:password@localhost:3306/",
    database_name="task_sequencer",
    table_name="my_progress",
    create_tables=True
)
```

**Особенности:**
- Поддерживает кастомное имя таблицы через параметр `table_name`
- Требует установки `pymysql>=1.0.0` и `sqlalchemy>=1.4.0`
- Поддерживает транзакции через `transaction()`

### PostgreSQLProgressTracker

Трекер для PostgreSQL. Требует установки `task-sequencer[postgresql]`.

**Параметры конструктора:**

- `connection_string: str` - строка подключения к PostgreSQL
  - Формат SQLAlchemy: `postgresql+psycopg2://user:password@host:port/database`
- `create_tables: bool = True` - если `True`, создает таблицы при инициализации

**Примеры:**

```python
from task_sequencer.adapters import PostgreSQLProgressTracker

tracker = PostgreSQLProgressTracker(
    connection_string="postgresql+psycopg2://user:password@localhost:5432/task_sequencer",
    create_tables=True
)
```

**Особенности:**
- Использует таблицу `task_progress` (имя фиксировано)
- Требует установки `psycopg2-binary>=2.9.0` и `sqlalchemy>=1.4.0`
- Поддерживает транзакции через `transaction()`

## Troubleshooting

### Проблемы с импортом адаптеров

**Проблема:** `ModuleNotFoundError: No module named 'task_sequencer.adapters'`

**Решение:** Убедитесь, что установлена последняя версия пакета:
```bash
pip install --upgrade task-sequencer
```

Если проблема сохраняется, проверьте, что подпакет `adapters` включен в установленный пакет.

### Проблемы с опциональными адаптерами

**Проблема:** `ImportError: cannot import name 'MySQLProgressTracker'`

**Решение:** Установите соответствующие опциональные зависимости:
```bash
# Для MySQL
pip install task-sequencer[mysql]

# Для MongoDB
pip install task-sequencer[mongodb]

# Для PostgreSQL
pip install task-sequencer[postgresql]
```

### Проблемы с MongoDB аутентификацией

**Проблема:** Ошибка аутентификации при использовании `MongoDBProgressTracker`

**Решение:** Для аутентификации через базу данных, имя БД должно быть в connection string. 
Теперь `database_name` автоматически извлекается из connection string, если не указан явно:
```python
# Упрощенный способ (автоматическое извлечение)
tracker = MongoDBProgressTracker(
    connection_string="mongodb://user:pass@host:27017/task_sequencer"
    # database_name извлечется автоматически
)

# Явное указание (приоритет)
tracker = MongoDBProgressTracker(
    connection_string="mongodb://localhost:27017/",
    database_name="task_sequencer"
)
```

### Проблемы с MySQL параметрами

**Проблема:** `TypeError: __init__() got an unexpected keyword argument 'database_name'`

**Решение:** В новых версиях `MySQLProgressTracker` поддерживает параметры `database_name` и `table_name`:
```python
# Новый способ (рекомендуется)
tracker = MySQLProgressTracker(
    connection_string="mysql+pymysql://user:pass@host:3306/",
    database_name="task_sequencer",
    table_name="my_progress",
    create_tables=True
)

# Старый способ (все еще работает)
tracker = MySQLProgressTracker(
    connection_string="mysql+pymysql://user:pass@host:3306/task_sequencer",
    create_tables=True
)
```

### Проблемы с обработкой ошибок в ParameterizedIterableTask

**Проблема:** Как обрабатывать ошибки для отдельных элементов в `ParameterizedIterableTask`?

**Решение:** Используйте стратегию обработки ошибок или кастомный callback `on_error`:
```python
# Стратегия "continue" - продолжить выполнение
class MyTask(ParameterizedIterableTask[str]):
    def __init__(self):
        super().__init__(error_strategy="continue")
    
    def execute_for_parameter(self, param: str, context: ExecutionContext) -> None:
        # Может выбросить исключение
        process_item(param)

# Кастомная обработка через on_error
class MyTask(ParameterizedIterableTask[str]):
    def on_error(self, param: str, error: Exception, context: ExecutionContext) -> bool:
        logger.error(f"Error processing {param}: {error}")
        return True  # Продолжить выполнение
```

**Результат выполнения содержит информацию об ошибках:**
```python
result = task.execute(context)
if not result.success:
    errors = result.data.get("errors", [])  # [(param, error_message), ...]
    processed = result.data.get("processed", 0)  # Количество успешно обработанных
```

### Проблемы с валидацией зависимостей

**Проблема:** `DependencyError: Task 'task2' dependencies not satisfied`

**Решение:** Убедитесь, что:
1. Все зависимости присутствуют в `task_order`
2. Зависимости указаны перед зависимыми задачами
3. Нет циклических зависимостей

```python
# Правильно: task_a выполняется перед task_b
result = orchestrator.execute(["task_a", "task_b"])

# Неправильно: task_b зависит от task_a, но указана первой
result = orchestrator.execute(["task_b", "task_a"])  # DependencyError
```

### Проблемы с проверкой наличия задачи в TaskRegistry

**Проблема:** Как проверить, что задача зарегистрирована?

**Решение:** Используйте оператор `in` (рекомендуется) или метод `get()` с обработкой исключения:
```python
# Новый способ (рекомендуется) - Pythonic API
if "task_name" in registry:
    task = registry["task_name"]
    print("Task found")

# Старый способ (все еще работает)
try:
    task = registry.get("task_name")
    print("Task found")
except KeyError:
    print("Task not found")
```

**Примечание:** В будущих версиях планируется добавление поддержки `"task_name" in registry` (см. Issue #013).

### Проблемы с кастомным ProgressTracker

**Проблема:** `TypeError: Can't instantiate abstract class MyProgressTracker`

**Решение:** Убедитесь, что реализованы все абстрактные методы:
- `save_progress(task_name: str, progress: TaskProgress) -> None`
- `get_progress(task_name: str) -> TaskProgress | None`
- `mark_completed(task_name: str) -> None`
- `clear_progress(task_name: str) -> None`
- `transaction() -> ContextManager[None]`

См. пример реализации в разделе "API Reference" → "ProgressTracker".

### Часто задаваемые вопросы (FAQ)

**Q: Можно ли выполнять задачи параллельно?**  
A: Нет, библиотека выполняет задачи последовательно. Параллельное выполнение может быть добавлено в будущих версиях.

**Q: Как обработать ошибки в ParameterizedIterableTask?**  
A: Используйте стратегию обработки ошибок (`error_strategy`) или кастомный callback `on_error`:
```python
# Продолжить при ошибке
class MyTask(ParameterizedIterableTask[str]):
    def __init__(self):
        super().__init__(error_strategy="continue")
    
    def execute_for_parameter(self, param: str, context: ExecutionContext) -> None:
        process_item(param)

# Кастомная обработка
class MyTask(ParameterizedIterableTask[str]):
    def on_error(self, param: str, error: Exception, context: ExecutionContext) -> bool:
        logger.error(f"Error processing {param}: {error}")
        return True  # Продолжить выполнение
```

Доступные стратегии: `"stop"` (по умолчанию), `"continue"`, `"retry"`.

**Q: Можно ли автоматически определить порядок задач на основе зависимостей?**  
A: В текущей версии порядок задач нужно указывать явно. Автоматическое определение порядка может быть добавлено в будущих версиях.

**Q: Как использовать resume для ParameterizedIterableTask?**  
A: Resume работает автоматически через `ProgressTracker`. Библиотека сохраняет прогресс для каждого параметра и пропускает уже обработанные элементы при `resume=True`.

## Требования

- Python 3.8+
- Для опциональных адаптеров БД:
  - MySQL: `pymysql>=1.0.0`, `sqlalchemy>=1.4.0`
  - MongoDB: `pymongo>=4.0.0`
  - PostgreSQL: `psycopg2-binary>=2.9.0`, `sqlalchemy>=1.4.0`

## Разработка

### Установка для разработки

```bash
git clone git@github.com:seligoroff/task_sequencer.git
cd task_sequencer
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# или
.venv\Scripts\activate  # Windows

pip install -e ".[dev]"
```

### Запуск тестов

```bash
pytest tests/ -v --cov=task_sequencer --cov-report=html
```

### Форматирование кода

```bash
black --line-length=100 task_sequencer/ tests/ examples/
```

### Проверка линтером

```bash
flake8 task_sequencer/ tests/ examples/
```

### Проверка типов

```bash
mypy task_sequencer/
```

## Документация

Полная документация доступна в папке `docs/` или на [Read the Docs](https://task-sequencer.readthedocs.io) (после публикации).

## Лицензия

MIT License - см. файл [LICENSE](LICENSE) для деталей.

## Авторы

[Ваше имя/команда]

## Поддержка

Для вопросов и предложений создавайте issues в [GitHub](https://github.com/seligoroff/task_sequencer/issues).

