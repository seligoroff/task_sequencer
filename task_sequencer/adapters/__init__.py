"""Адаптеры для трекеров прогресса."""

from __future__ import annotations

from task_sequencer.adapters.memory import MemoryProgressTracker

__all__ = ["MemoryProgressTracker"]

# Опциональные адаптеры импортируются только при наличии зависимостей
try:
    from task_sequencer.adapters.mysql import MySQLProgressTracker  # noqa: F401

    __all__.append("MySQLProgressTracker")
except ImportError:
    pass

try:
    from task_sequencer.adapters.mongodb import MongoDBProgressTracker  # noqa: F401

    __all__.append("MongoDBProgressTracker")
except ImportError:
    pass

try:
    from task_sequencer.adapters.postgresql import PostgreSQLProgressTracker  # noqa: F401

    __all__.append("PostgreSQLProgressTracker")
except ImportError:
    pass

