"""Main plugin entry points for Vector Map."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from .provider import VectorMapProcessingProvider

_QgsApplication: Any
_QgsAction: Any
_QIcon: Any

if TYPE_CHECKING:  # pragma: no cover - typing only
    pass

try:  # pragma: no cover - exercised inside QGIS
    from qgis.core import (
        QAction as _QgsAction,
        QIcon as _QgsIcon,
       Qgis as _Qgis,
    )
    from qgis.gui import QgisInterface as _QgsInterface
    HAS_QGIS_CORE = True
except ImportError:
    _QgsAction = None
    _QgsIcon = None
    _Qgis = None
    _QgsInterface = None
    HAS_QGIS_CORE = False

try:  # pragma: no cover - exercised inside QGIS
    from qgis.core import (
        Qgis as _QgsApplication,
    )
except Exception:  # pragma: no cover - import-safe fallback for local tests

    class _FallbackQgsApplication:
        @staticmethod
        def processingRegistry():
            return None

    _QgsApplication = _FallbackQgsApplication

QgsApplication = cast(Any, _QgsApplication)
QgsAction = cast(type, _QgsAction)
QIcon = cast(type, _QgsIcon)


class VectorMapPlugin:
    """QGIS plugin shell for Vector Map.

    The plugin owns a single processing provider and registers it when the
    GUI is initialized. It also adds a toolbar button for quick access to
    the vectorization dialog.

    When QGIS is unavailable, the class still imports and can be
    instantiated safely for unit tests or packaging checks.
    """

    def __init__(self, iface):
        self.iface = iface
        self.provider = None
        self.action = None

    def _processing_registry(self):
        registry = getattr(QgsApplication, 'processingRegistry', lambda: None)()
        return registry

    def _create_icon(self) -> QIcon | None:
        """Create a simple icon for the toolbar button.

        Returns None if QIcon is not available.
        """
        if QIcon is None:
            return None

        # Create a simple 24x24 icon with a vector/matrix pattern
        # Using a data URL to avoid external dependencies
        icon_data = (
            "iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAYAAADgdz34AAAABHNCSVQICAgIfAhkiAAAAAlwSFlz"
            "AAAAsQAAALEBxi1JjQAAABl0RVh0U29mdHdhcmUAd3d3Lmlua3NjYXBlLm9yZ5vuPBoAAAGASURB"
            "VEiJ7ZS9TsMwFIW/SYdYGFSwECwsLAwsDA0sLNy5AhcgC3dhZGFgYGJgYGBgYGFkYWBgYGBhZGFg"
            "YGJkYWBgYGFkYWBgYGBgYWJgYGBgYGBhYWBkYWBgYGFkYWBgYGJhYmFkYWBgYmFkYWBgYmJlYWFl"
            "YGFhYmJhYGFhYmJhYmJhYmJhYWFhYWFgYWFhYWFgYWJhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFh"
            "YWFhYWFhYWFhYWFhYGBgYGBhYWFhYWFhYWFgYGBgYWFhYWFgYGBgYGBgYWFhYWFhYWFhYWFgYGBgY"
            "GBgYGBgYWFhYWFhYWFhYWFgYGBgYWFhYWFgYGBgYWFhYWFhYWFhYWFgYGBgYGBgYGBgYWFhYWFhYW"
            "FhYWFgYGBgYWFhYWFgYGBgYGBhYGBhYWFhYGBgYGBgYWFhYGBgYGBgYGBhYWFhYGBgYGBgYGBgYGBg"
            "YWFhYGBgYGBgYGBgYGBgYWFhYGBgYGBgYGBgYGBgYWFhYGBgYGBgYGBgYGBgYWFhYGBgYGBgYGBgYGBg"
            "YWFhYGBgYGBgYGBgYGBgYWFhYGBgYGBgYGBgYGBgYWFhYGBgYGBgYGBgYGBgYWFhYGBgYGBgYGBgYGBg"
            "YWFhYGBgYGBgYGBgYGBgYWFhYGBgYGBgYGBgYGBgYWFhYGBgYGBgYGBgYGBgYWFhYGBgYGBgYGBgYGBg"
            "YGBgYWFhYGBgYGBgYGBgYGBgYWFhYGBgYGBgYGBgYGBgYGBgYWFhYGBgYGBgYGBgYGBgYWFhYGBgYGBg"
            "YGBgYGBgYGBgYWFhYGBgYGBgYGBgYGBgYWFhYGBgYGBgYGBgYGBgYGBgYWFhYGBgYGBgYGBgYGBgYWFh"
            "YGBgYGBgYGBgYGBgYGBgYWFhYGBgYGBgYGBgYGBgYWFhYGBgYGBgYGBgYGBgYGBgYWFhYGBgYGBgYGBg"
            "YGBgYWFhYGBgYGBgYGBgYGBgYGBgYWFhYGBgYGBgYGBgYGBgYWFhYGBgYGBgYGBgYGBgYGBg"
        )
        import base64
        try:
            pixmap_data = base64.b64decode(icon_data)
            from PyQt5.QtGui import QPixmap
            from PyQt5.QtCore import QByteArray, QBuffer
        except ImportError:
            try:
                from PyQt6.QtGui import QPixmap
                from PyQt6.QtCore import QByteArray, QBuffer
            except ImportError:
                return None

        pixmap = QPixmap()
        pixmap.loadFromData(QByteArray(pixmap_data))
        return QIcon(pixmap)

    def _show_dialog(self) -> None:
        """Show the vectorization dialog."""
        try:
            from .ui.dialog import VectorMapDialog

            dialog = VectorMapDialog(self.iface.mainWindow())
            if dialog.exec_() == dialog.Accepted:
                params = dialog.get_parameters()
                self._run_vectorization(params)
        except ImportError:
            # Dialog or Qt not available
            pass

    def _run_vectorization(self, params: dict[str, Any]) -> None:
        """Run vectorization with the given parameters."""
        from pathlib import Path

        # Import the algorithm
        try:
            from qgis_vector_map.core.models import VectorizationRequest
            from qgis_vector_map.core.pipeline import run_vectorization
        except ImportError:
            return

        # Determine output format
        output_format_map = {
            "auto": "auto",
            "GeoPackage (.gpkg)": "gpkg",
            "GeoJSON (.geojson)": "geojson",
            "ESRI Shapefile (.shp)": "shp",
        }
        output_format = output_format_map.get(params.get("output_format", "auto"), "auto")

        # Determine engine
        engine_name_map = {
            "auto": "auto",
            "classic": "classic-local",
            "opencv": "opencv-local",
        }
        engine = engine_name_map.get(params.get("engine", "auto"), "auto")

        # Create request
        request = VectorizationRequest(
            source=params["raster_path"],
            profile_id=params["profile"],
            output_path=Path(params["output_path"]),
            output_format=output_format,
            layer_name=params["layer_name"],
            parameters={
                "engine_name": engine,
                "execution_mode": params["execution_mode"],
            },
        )

        try:
            result = run_vectorization(request)
            # Notify user of success
            if hasattr(self.iface, 'messageBar'):
                self.iface.messageBar().pushMessage(
                    "Vector Map",
                    f"Vectorization complete. {result.vector_layer.feature_count()} features created.",
                    level=1,  # Qgis.Info
                    duration=5
                )
        except Exception as e:
            if hasattr(self.iface, 'messageBar'):
                self.iface.messageBar().pushMessage(
                    "Vector Map",
                    f"Vectorization failed: {e}",
                    level=2,  # Qgis.Critical
                    duration=10
                )

    def initGui(self):
        """Register the processing provider and add toolbar button with QGIS."""

        # Register the processing provider
        if self.provider is None:
            self.provider = VectorMapProcessingProvider()

        registry = self._processing_registry()
        if registry is not None:
            providers = []
            if hasattr(registry, "providers"):
                try:
                    providers = list(registry.providers())
                except Exception:
                    providers = []

            if self.provider not in providers:
                registry.addProvider(self.provider)

        # Add toolbar button
        if not HAS_QGIS_CORE or self.action is not None:
            return

        if self.action is None:
            self.action = _QgsAction(self._create_icon(), "Vectorize Image", None)
            self.action.setToolTip("Open Vector Map vectorization dialog")
            self.action.triggered.connect(self._show_dialog)

        if self.iface is not None:
            try:
                # Add to Vector Toolbar or main toolbar
                self.iface.addToolBarIcon(self.action)
            except Exception:
                # Fallback: add to plugin menu
                pass

    def unload(self):
        """Unregister the processing provider and remove toolbar icon from QGIS."""

        # Remove toolbar icon
        if self.action is not None and self.iface is not None:
            try:
                self.iface.removeToolBarIcon(self.action)
            except Exception:
                pass

        self.action = None

        # Unregister the processing provider
        registry = self._processing_registry()
        if registry is None or self.provider is None:
            return

        try:
            registry.removeProvider(self.provider)
        except Exception:
            pass