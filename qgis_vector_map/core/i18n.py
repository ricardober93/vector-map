"""Internationalization (i18n) for the Vector Map plugin.

The plugin uses a simple translation system based on Python dicts and a
:class:`Translator` that holds the current language. This works without
Qt and is easy to test in isolation.

The QGIS algorithm layer additionally uses ``QCoreApplication.translate``
when running inside QGIS. This module is the fallback for non-QGIS
contexts (tests, CLI, headless pipelines).

Usage
-----
>>> from qgis_vector_map.core.i18n import t, set_language
>>> set_language("es")
>>> t("Hello")
'Hola'

Supported languages: "en" (default) and "es".
"""

from __future__ import annotations

from typing import Any, Optional

# All translatable strings live here. Add new keys, never reuse keys.
# Format: message_id -> {"en": "...", "es": "..."}
_TRANSLATIONS: dict[str, dict[str, str]] = {
    # General
    "OK": {"en": "OK", "es": "Aceptar"},
    "Cancel": {"en": "Cancel", "es": "Cancelar"},
    "Error": {"en": "Error", "es": "Error"},
    "Warning": {"en": "Warning", "es": "Advertencia"},
    "Info": {"en": "Information", "es": "Información"},
    # Plugin
    "plugin_name": {
        "en": "Vector Map",
        "es": "Vector Map",
    },
    "plugin_description": {
        "en": "Local raster-to-vector processing plugin for QGIS Processing",
        "es": "Plugin local de procesamiento ráster-a-vector para QGIS",
    },
    # Dialog
    "dialog_title": {
        "en": "Vectorize Image",
        "es": "Vectorizar Imagen",
    },
    "input_raster": {"en": "Input Raster", "es": "Ráster de Entrada"},
    "browse": {"en": "Browse...", "es": "Examinar..."},
    "profile": {"en": "Profile", "es": "Perfil"},
    "engine": {"en": "Engine", "es": "Motor"},
    "execution_mode": {"en": "Execution Mode", "es": "Modo de Ejecución"},
    "output_format": {"en": "Output Format", "es": "Formato de Salida"},
    "output_crs": {"en": "Output CRS", "es": "CRS de Salida"},
    "layer_name": {"en": "Layer Name", "es": "Nombre de Capa"},
    "output_file": {"en": "Output File", "es": "Archivo de Salida"},
    "save_preset": {"en": "Save Preset", "es": "Guardar Preajuste"},
    "load_preset": {"en": "Load Preset", "es": "Cargar Preajuste"},
    "vectorize": {"en": "Vectorize", "es": "Vectorizar"},
    # Profiles
    "profile_regional": {
        "en": "Regional (high precision)",
        "es": "Regional (alta precisión)",
    },
    "profile_edge": {
        "en": "Edge (high precision)",
        "es": "Bordes (alta precisión)",
    },
    "profile_linear": {
        "en": "Linear (high precision)",
        "es": "Lineal (alta precisión)",
    },
    # Engines
    "engine_auto": {"en": "Auto (recommended)", "es": "Auto (recomendado)"},
    "engine_classic": {"en": "Classic (Python)", "es": "Clásico (Python)"},
    "engine_opencv": {"en": "OpenCV (faster)", "es": "OpenCV (más rápido)"},
    # Execution modes
    "exec_auto": {"en": "Auto (auto-detect)", "es": "Auto (detectar)"},
    "exec_strict": {"en": "Strict (in-memory)", "es": "Estricto (en memoria)"},
    "exec_tiled": {"en": "Tiled (large rasters)", "es": "Por teselas (ráster grandes)"},
    # Output formats
    "format_auto": {"en": "Auto (detect from extension)", "es": "Auto (detectar)"},
    "format_gpkg": {"en": "GeoPackage (.gpkg)", "es": "GeoPackage (.gpkg)"},
    "format_geojson": {"en": "GeoJSON (.geojson)", "es": "GeoJSON (.geojson)"},
    "format_shp": {"en": "ESRI Shapefile (.shp)", "es": "ESRI Shapefile (.shp)"},
    # CRS
    "crs_input": {"en": "Same as input raster", "es": "Igual al ráster de entrada"},
    "crs_custom": {"en": "Custom (specify below)", "es": "Personalizado (especificar abajo)"},
    # Errors / warnings
    "err_no_input": {
        "en": "Input raster is required.",
        "es": "Se requiere un ráster de entrada.",
    },
    "err_no_output": {
        "en": "Output file is required.",
        "es": "Se requiere un archivo de salida.",
    },
    "err_tiled_with_edge": {
        "en": "Tiled mode is only supported for the regional profile.",
        "es": "El modo por teselas solo es compatible con el perfil regional.",
    },
    "err_file_not_found": {
        "en": "File not found: {path}",
        "es": "Archivo no encontrado: {path}",
    },
    "err_invalid_crs": {
        "en": "Invalid CRS: {crs}. Use format like 'EPSG:4326'.",
        "es": "CRS inválido: {crs}. Use formato como 'EPSG:4326'.",
    },
    "err_cancelled": {
        "en": "Vectorization cancelled at stage '{stage}' after {after}.",
        "es": "Vectorización cancelada en etapa '{stage}' después de {after}.",
    },
    # Progress messages
    "progress_tile": {
        "en": "Tile {current}/{total}",
        "es": "Tesela {current}/{total}",
    },
    "progress_file": {
        "en": "File {current}/{total}",
        "es": "Archivo {current}/{total}",
    },
    "progress_elapsed": {"en": "elapsed {time}", "es": "transcurrido {time}"},
    "progress_eta": {"en": "ETA {time}", "es": "faltan {time}"},
    # Batch
    "batch_summary": {
        "en": "{succeeded}/{total} succeeded, {failed} failed",
        "es": "{succeeded}/{total} exitosos, {failed} fallaron",
    },
    "batch_summary_cancelled": {
        "en": "{succeeded}/{total} succeeded, {failed} failed, {cancelled} cancelled",
        "es": "{succeeded}/{total} exitosos, {failed} fallaron, {cancelled} cancelados",
    },
    # Presets
    "presets_none": {
        "en": "No presets found. Save a preset first!",
        "es": "No hay preajustes. ¡Guarda uno primero!",
    },
    "presets_saved": {
        "en": "Preset '{name}' saved.",
        "es": "Preajuste '{name}' guardado.",
    },
    "presets_loaded": {
        "en": "Preset '{name}' loaded.",
        "es": "Preajuste '{name}' cargado.",
    },
    # Recent files
    "recent_empty": {
        "en": "(no recent files)",
        "es": "(sin archivos recientes)",
    },
}

# Language registry
SUPPORTED_LANGUAGES = ("en", "es")
DEFAULT_LANGUAGE = "en"


class _TranslatorState:
    """Module-level state for the active language."""

    language: str = DEFAULT_LANGUAGE
    fallback: str = DEFAULT_LANGUAGE


def get_language() -> str:
    """Get the currently active language code (e.g. 'en', 'es')."""
    return _TranslatorState.language


def set_language(lang: str) -> None:
    """Set the active language.

    Parameters
    ----------
    lang:
        One of the supported language codes ("en", "es"). Unknown codes
        are ignored (no exception is raised).
    """
    if lang in SUPPORTED_LANGUAGES:
        _TranslatorState.language = lang


def available_languages() -> tuple[str, ...]:
    """Return the tuple of supported language codes."""
    return SUPPORTED_LANGUAGES


def register_translation(
    message_id: str,
    *,
    en: str,
    es: str,
    overwrite: bool = False,
) -> None:
    """Add or update a translation entry.

    Useful for plugins that want to add their own translatable strings.

    Parameters
    ----------
    message_id:
        Unique identifier for the string.
    en:
        English text.
    es:
        Spanish text.
    overwrite:
        If False (default), raise if the message_id already exists.
        If True, replace the existing entry.
    """
    if not overwrite and message_id in _TRANSLATIONS:
        raise ValueError(
            f"Translation key {message_id!r} already exists. "
            "Pass overwrite=True to replace."
        )
    _TRANSLATIONS[message_id] = {"en": en, "es": es}


def t(message_id: str, **kwargs: Any) -> str:
    """Translate a message.

    Parameters
    ----------
    message_id:
        The translation key.
    **kwargs:
        Optional named placeholders. The translated string is formatted
        with str.format(**kwargs). Unknown placeholders are left as-is.

    Returns
    -------
    The translated string, formatted with kwargs.

    Notes
    -----
    If the message_id is not found, returns the message_id itself.
    If the active language has no translation for the key, falls back
    to the default language (English).
    """
    entry = _TRANSLATIONS.get(message_id)
    if entry is None:
        # Unknown key: return as-is (with formatting applied)
        try:
            return message_id.format(**kwargs)
        except (KeyError, IndexError):
            return message_id

    lang = _TranslatorState.language
    text = entry.get(lang)
    if text is None and lang != _TranslatorState.fallback:
        text = entry.get(_TranslatorState.fallback)
    if text is None:
        # Last resort: any available language
        text = next(iter(entry.values()))

    if not kwargs:
        return text
    try:
        return text.format(**kwargs)
    except (KeyError, IndexError):
        return text


# Short alias
_ = t


__all__ = [
    "DEFAULT_LANGUAGE",
    "SUPPORTED_LANGUAGES",
    "available_languages",
    "get_language",
    "register_translation",
    "set_language",
    "t",
]
