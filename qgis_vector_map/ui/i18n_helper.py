"""i18n helper for UI components.

Thin wrapper over :mod:`qgis_vector_map.core.i18n` that is convenient to
import from the UI layer without creating a circular dependency.
"""

from __future__ import annotations

from typing import Any

from ..core.i18n import t as _t


def tr(message_id: str, **kwargs: Any) -> str:
    """Translate a message using the core i18n system.

    Parameters
    ----------
    message_id:
        The translation key (see ``core/i18n.py``).
    **kwargs:
        Optional placeholder values for str.format.

    Returns
    -------
    The translated string.
    """
    return _t(message_id, **kwargs)


__all__ = ["tr"]
