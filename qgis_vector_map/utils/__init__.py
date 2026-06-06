"""Utility modules for the Vector Map plugin."""

from .processing_history import (
    HISTORY_FILENAME,
    HistoryEntry,
    MAX_HISTORY,
    ProcessingHistoryManager,
    make_entry_from_result,
)
from .recent_files import MAX_RECENT, RECENT_FILENAME, RecentFilesManager

__all__ = [
    "HISTORY_FILENAME",
    "HistoryEntry",
    "MAX_HISTORY",
    "MAX_RECENT",
    "ProcessingHistoryManager",
    "RECENT_FILENAME",
    "RecentFilesManager",
    "make_entry_from_result",
]
