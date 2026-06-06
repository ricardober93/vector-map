"""Vector Map dialog for simplified UX."""

from __future__ import annotations

import json
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, cast

_QDialog: Any
_QLabel: Any
_QLineEdit: Any
_QComboBox: Any
_QPushButton: Any
_QVBoxLayout: Any
_QHBoxLayout: Any
_QGridLayout: Any
_QWidget: Any
_QFileDialog: Any
_QGroupBox: Any
_QMessageBox: Any
_QProgressBar: Any
_QCheckBox: Any
_QListWidget: Any
_QTabWidget: Any
_QMimeData: Any
_QDragEnterEvent: Any
_QDropEvent: Any

# Try to import PyQt5/PyQt6 for Qt widgets
try:
    from PyQt5.QtCore import QMimeData as _QMimeData
    from PyQt5.QtCore import QPoint as _QPoint
    from PyQt5.QtCore import QRect as _QRect
    from PyQt5.QtCore import QSize as _QSize
    from PyQt5.QtCore import QUrl as _QUrl
    from PyQt5.QtGui import QDragEnterEvent as _QDragEnterEvent
    from PyQt5.QtGui import QDropEvent as _QDropEvent
    from PyQt5.QtWidgets import QDialog as _QDialog
    from PyQt5.QtWidgets import QLabel as _QLabel
    from PyQt5.QtWidgets import QLineEdit as _QLineEdit
    from PyQt5.QtWidgets import QComboBox as _QComboBox
    from PyQt5.QtWidgets import QPushButton as _QPushButton
    from PyQt5.QtWidgets import QVBoxLayout as _QVBoxLayout
    from PyQt5.QtWidgets import QHBoxLayout as _QHBoxLayout
    from PyQt5.QtWidgets import QGridLayout as _QGridLayout
    from PyQt5.QtWidgets import QWidget as _QWidget
    from PyQt5.QtWidgets import QFileDialog as _QFileDialog
    from PyQt5.QtWidgets import QGroupBox as _QGroupBox
    from PyQt5.QtWidgets import QMessageBox as _QMessageBox
    from PyQt5.QtWidgets import QProgressBar as _QProgressBar
    from PyQt5.QtWidgets import QCheckBox as _QCheckBox
    from PyQt5.QtWidgets import QListWidget as _QListWidget
    from PyQt5.QtWidgets import QListWidgetItem as _QListWidgetItem
    from PyQt5.QtWidgets import QTabWidget as _QTabWidget

    HAS_QT = True
except ImportError:
    try:
        from PyQt6.QtCore import QMimeData as _QMimeData
        from PyQt6.QtCore import QPoint as _QPoint
        from PyQt6.QtCore import QRect as _QRect
        from PyQt6.QtCore import QSize as _QSize
        from PyQt6.QtCore import QUrl as _QUrl
        from PyQt6.QtGui import QDragEnterEvent as _QDragEnterEvent
        from PyQt6.QtGui import QDropEvent as _QDropEvent
        from PyQt6.QtWidgets import QDialog as _QDialog
        from PyQt6.QtWidgets import QLabel as _QLabel
        from PyQt6.QtWidgets import QLineEdit as _QLineEdit
        from PyQt6.QtWidgets import QComboBox as _QComboBox
        from PyQt6.QtWidgets import QPushButton as _QPushButton
        from PyQt6.QtWidgets import QVBoxLayout as _QVBoxLayout
        from PyQt6.QtWidgets import QHBoxLayout as _QHBoxLayout
        from PyQt6.QtWidgets import QGridLayout as _QGridLayout
        from PyQt6.QtWidgets import QWidget as _QWidget
        from PyQt6.QtWidgets import QFileDialog as _QFileDialog
        from PyQt6.QtWidgets import QGroupBox as _QGroupBox
        from PyQt6.QtWidgets import QMessageBox as _QMessageBox
        from PyQt6.QtWidgets import QProgressBar as _QProgressBar
        from PyQt6.QtWidgets import QCheckBox as _QCheckBox
        from PyQt6.QtWidgets import QListWidget as _QListWidget
        from PyQt6.QtWidgets import QListWidgetItem as _QListWidgetItem
        from PyQt6.QtWidgets import QTabWidget as _QTabWidget

        HAS_QT = True
    except ImportError:
        HAS_QT = False

# Fallback classes when Qt is not available
if not HAS_QT:
    class _QDialog:
        def __init__(self, *args, **kwargs): pass

    class _QLabel:
        def __init__(self, *args, **kwargs): pass
        def setText(self, text): pass

    class _QLineEdit:
        def __init__(self, *args, **kwargs): pass
        def text(self): return ""
        def setText(self, text): pass

    class _QComboBox:
        def __init__(self, *args, **kwargs): pass
        def addItems(self, items): pass
        def currentText(self): return ""
        def currentIndex(self): return 0
        def setCurrentIndex(self, index): pass

    class _QPushButton:
        def __init__(self, *args, **kwargs): pass
        clicked = None  # Signal placeholder
        def setText(self, text): pass

    class _QVBoxLayout:
        def __init__(self, *args, **kwargs): pass
        def addWidget(self, widget): pass
        def addLayout(self, layout): pass

    class _QHBoxLayout:
        def __init__(self, *args, **kwargs): pass
        def addWidget(self, widget): pass
        def addLayout(self, layout): pass

    class _QGridLayout:
        def __init__(self, *args, **kwargs): pass
        def addWidget(self, widget, row, col): pass

    class _QWidget:
        def __init__(self, *args, **kwargs): pass
        def setLayout(self, layout): pass

    class _QFileDialog:
        @staticmethod
        def getOpenFileName(*args, **kwargs):
            return ("", "")

        @staticmethod
        def getSaveFileName(*args, **kwargs):
            return ("", "")

    class _QGroupBox:
        def __init__(self, *args, **kwargs): pass
        def setTitle(self, title): pass
        def setLayout(self, layout): pass

    class _QMessageBox:
        @staticmethod
        def information(*args, **kwargs): pass
        @staticmethod
        def warning(*args, **kwargs): pass
        @staticmethod
        def critical(*args, **kwargs): pass

    class _QProgressBar:
        def __init__(self, *args, **kwargs): pass
        def setValue(self, value): pass
        def setMaximum(self, value): pass
        def setMinimum(self, value): pass
        def setRange(self, min_val, max_val): pass

    class _QCheckBox:
        def __init__(self, *args, **kwargs): pass
        def isChecked(self): return False
        def setChecked(self, checked): pass

    class _QListWidget:
        def __init__(self, *args, **kwargs): pass
        def addItem(self, item): pass
        def addItems(self, items): pass
        def clear(self): pass
        def count(self): return 0
        def item(self, row): return None
        def currentItem(self): return None
        def currentRow(self): return -1
        def setCurrentRow(self, row): pass
        def currentText(self): return ""

    class _QListWidgetItem:
        def __init__(self, *args, **kwargs): pass
        def setText(self, text): pass
        def text(self): return ""
        def setData(self, role, value): pass
        def data(self, role): return None

    class _QTabWidget:
        def __init__(self, *args, **kwargs): pass
        def addTab(self, widget, label): pass
        def currentIndex(self): return 0
        def setCurrentIndex(self, index): pass
        def widget(self, index): return None

    class _QMimeData:
        @staticmethod
        def hasUrls(): return False
        def urls(self): return []

    class _QUrl:
        @staticmethod
        def fromLocalFile(path): return None
        def toLocalFile(self): return ""

    class _QDragEnterEvent:
        def __init__(self, *args, **kwargs): pass
        def acceptProposedAction(self): pass
        def ignore(self): pass
        def mimeData(self): return None

    class _QDropEvent:
        def __init__(self, *args, **kwargs): pass
        def acceptProposedAction(self): pass
        def ignore(self): pass
        def mimeData(self): return None


QDialog = cast(type, _QDialog)
QLabel = cast(type, _QLabel)
QLineEdit = cast(type, _QLineEdit)
QComboBox = cast(type, _QComboBox)
QPushButton = cast(type, _QPushButton)
QVBoxLayout = cast(type, _QVBoxLayout)
QHBoxLayout = cast(type, _QHBoxLayout)
QGridLayout = cast(type, _QGridLayout)
QWidget = cast(type, _QWidget)
QFileDialog = cast(type, _QFileDialog)
QGroupBox = cast(type, _QGroupBox)
QMessageBox = cast(type, _QMessageBox)
QProgressBar = cast(type, _QProgressBar)
QCheckBox = cast(type, _QCheckBox)
QListWidget = cast(type, _QListWidget)
QListWidgetItem = cast(type, _QListWidgetItem)
QTabWidget = cast(type, _QTabWidget)
QMimeData = cast(type, _QMimeData)
QUrl = cast(type, _QUrl)


class VectorMapDialog(_QDialog if HAS_QT else object):
    """Simplified UX dialog for Vector Map plugin.

    Provides a user-friendly interface for vectorizing raster images
    with visual parameter selection and real-time feedback.

    Drag & Drop
    -----------
    The dialog accepts raster files dropped from the system file manager.
    - Single file: populates the raster path and updates the preview.
    - Multiple files: populates with the first file AND triggers the
      :attr:`on_files_dropped` callback (if set) so the host can switch
      to batch mode. The list of paths is passed to the callback.

    To react to multi-file drops, set a callback before showing:
    >>> dialog = VectorMapDialog()
    >>> dialog.on_files_dropped = lambda paths: run_batch(paths)
    """

    # Callback: invoked when multiple files are dropped. Receives a list of paths.
    # Public so tests can patch it directly.
    on_files_dropped = None

    # Profile options
    PROFILE_OPTIONS = [
        "regional-high-precision",
        "edge-high-precision",
        "linear-high-precision",
    ]

    # Execution mode options
    EXECUTION_MODE_OPTIONS = [
        "auto",
        "strict",
        "tiled",
    ]

    # Output format options
    OUTPUT_FORMAT_OPTIONS = [
        "auto",
        "GeoPackage (.gpkg)",
        "GeoJSON (.geojson)",
        "ESRI Shapefile (.shp)",
    ]

    # Engine options
    ENGINE_OPTIONS = [
        "auto",
        "classic",
        "opencv",
    ]

    # Supported raster file extensions for drag & drop
    RASTER_EXTENSIONS = frozenset({
        ".tif", ".tiff", ".TIF", ".TIFF",
        ".png", ".PNG",
        ".jpg", ".jpeg", ".JPG", ".JPEG",
        ".bmp", ".BMP",
        ".gif", ".GIF",
        ".webp", ".WEBP",
    })

    @classmethod
    def is_raster_path(cls, path: str) -> bool:
        """Return True if the given path has a supported raster extension.

        Accepts paths with or without query strings, in case the user
        drags a URL-like object from some file managers. Extension
        comparison is case-insensitive (so .TIF, .Tif, .tif all match).
        """
        if not path:
            return False
        # Strip any query/fragment (e.g., from drag-dropped URLs)
        clean = path.split("?", 1)[0].split("#", 1)[0]
        ext = Path(clean).suffix
        if not ext:
            return False
        return ext.lower() in {e.lower() for e in cls.RASTER_EXTENSIONS}

    @classmethod
    def filter_raster_urls(cls, urls: list[Any]) -> list[str]:
        """Filter a list of QUrl-like objects and return only raster paths.

        Non-raster URLs are silently dropped. If no URLs have a recognized
        extension, returns an empty list.
        """
        result: list[str] = []
        for url in urls:
            # Support both QUrl and str
            if hasattr(url, "toLocalFile"):
                path = url.toLocalFile()
            else:
                path = str(url)
            if cls.is_raster_path(path):
                result.append(path)
        return result

    def __init__(self, parent=None):
        super().__init__(parent)

        if not HAS_QT:
            return

        self.setWindowTitle("Vector Map - Vectorize Image")
        self.setMinimumWidth(500)
        self.resize(550, 400)

        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self) -> None:
        """Setup the dialog UI components."""
        main_layout = QVBoxLayout(self)

        # Enable drag & drop of raster files
        self.setAcceptDrops(True)

        # Input section
        input_group = QGroupBox("Input")
        input_layout = QGridLayout()

        # Raster file selector
        self.raster_label = QLabel("Raster:")
        self.raster_path_edit = QLineEdit()
        self.raster_browse_btn = QPushButton("Browse...")

        input_layout.addWidget(self.raster_label, 0, 0)
        input_layout.addWidget(self.raster_path_edit, 0, 1)
        input_layout.addWidget(self.raster_browse_btn, 0, 2)

        # Apply tooltips
        self._apply_tooltip(self.raster_path_edit, "tip_input_raster")
        self._apply_tooltip(self.raster_browse_btn, "tip_browse")
        self._apply_tooltip(self.raster_label, "tip_input_raster")

        input_group.setLayout(input_layout)
        main_layout.addWidget(input_group)

        # Processing section
        processing_group = QGroupBox("Processing")
        processing_layout = QGridLayout()

        # Profile selector
        self.profile_label = QLabel("Profile:")
        self.profile_combo = QComboBox()
        self.profile_combo.addItems(self.PROFILE_OPTIONS)

        # Engine selector
        self.engine_label = QLabel("Engine:")
        self.engine_combo = QComboBox()
        self.engine_combo.addItems(self.ENGINE_OPTIONS)

        # Execution mode selector
        self.exec_mode_label = QLabel("Execution Mode:")
        self.exec_mode_combo = QComboBox()
        self.exec_mode_combo.addItems(self.EXECUTION_MODE_OPTIONS)

        processing_layout.addWidget(self.profile_label, 0, 0)
        processing_layout.addWidget(self.profile_combo, 0, 1, 1, 2)
        processing_layout.addWidget(self.engine_label, 1, 0)
        processing_layout.addWidget(self.engine_combo, 1, 1, 1, 2)
        processing_layout.addWidget(self.exec_mode_label, 2, 0)
        processing_layout.addWidget(self.exec_mode_combo, 2, 1, 1, 2)

        # Apply tooltips
        self._apply_tooltip(self.profile_combo, "tip_profile")
        self._apply_tooltip(self.profile_label, "tip_profile")
        self._apply_tooltip(self.engine_combo, "tip_engine")
        self._apply_tooltip(self.engine_label, "tip_engine")
        self._apply_tooltip(self.exec_mode_combo, "tip_execution_mode")
        self._apply_tooltip(self.exec_mode_label, "tip_execution_mode")

        processing_group.setLayout(processing_layout)
        main_layout.addWidget(processing_group)

        # Output section
        output_group = QGroupBox("Output")
        output_layout = QGridLayout()

        # Output format selector
        self.output_format_label = QLabel("Format:")
        self.output_format_combo = QComboBox()
        self.output_format_combo.addItems(self.OUTPUT_FORMAT_OPTIONS)

        # Layer name
        self.layer_name_label = QLabel("Layer Name:")
        self.layer_name_edit = QLineEdit()
        self.layer_name_edit.setText(self._generate_default_layer_name())

        # Output file selector
        self.output_file_label = QLabel("Output File:")
        self.output_file_edit = QLineEdit()
        self.output_browse_btn = QPushButton("Browse...")

        output_layout.addWidget(self.output_format_label, 0, 0)
        output_layout.addWidget(self.output_format_combo, 0, 1, 1, 2)
        output_layout.addWidget(self.layer_name_label, 1, 0)
        output_layout.addWidget(self.layer_name_edit, 1, 1, 1, 2)
        output_layout.addWidget(self.output_file_label, 2, 0)
        output_layout.addWidget(self.output_file_edit, 2, 1)
        output_layout.addWidget(self.output_browse_btn, 2, 2)

        # Apply tooltips
        self._apply_tooltip(self.output_format_combo, "tip_output_format")
        self._apply_tooltip(self.output_format_label, "tip_output_format")
        self._apply_tooltip(self.layer_name_edit, "tip_layer_name")
        self._apply_tooltip(self.layer_name_label, "tip_layer_name")
        self._apply_tooltip(self.output_file_edit, "tip_output_file")
        self._apply_tooltip(self.output_file_label, "tip_output_file")
        self._apply_tooltip(self.output_browse_btn, "tip_browse")

        output_group.setLayout(output_layout)
        main_layout.addWidget(output_group)

        # Preview section
        self.preview_label = QLabel("")
        self.preview_label.setStyleSheet("color: #666; font-size: 11px;")
        main_layout.addWidget(self.preview_label)

        # Progress bar (hidden by default)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setRange(0, 100)
        main_layout.addWidget(self.progress_bar)

        # Presets section
        presets_group = QGroupBox("Presets")
        presets_layout = QHBoxLayout()

        self.save_preset_btn = QPushButton("💾 Save Preset")
        self.load_preset_btn = QPushButton("📂 Load Preset")

        presets_layout.addWidget(self.save_preset_btn)
        presets_layout.addWidget(self.load_preset_btn)
        presets_layout.addStretch()

        # Apply tooltips
        self._apply_tooltip(self.save_preset_btn, "tip_save_preset")
        self._apply_tooltip(self.load_preset_btn, "tip_load_preset")

        presets_group.setLayout(presets_layout)
        main_layout.addWidget(presets_group)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.cancel_btn = QPushButton("Cancel")
        self.vectorize_btn = QPushButton("Vectorize ▶")
        self.vectorize_btn.setDefault(True)

        button_layout.addWidget(self.cancel_btn)
        button_layout.addWidget(self.vectorize_btn)

        # Apply tooltips
        self._apply_tooltip(self.cancel_btn, "tip_cancel")
        self._apply_tooltip(self.vectorize_btn, "tip_vectorize")

        main_layout.addLayout(button_layout)

        # Store references to main layout for later
        self._main_layout = main_layout

    def _apply_tooltip(self, widget: Any, message_id: str) -> None:
        """Apply a translated tooltip to a widget if Qt is available.

        Falls back silently when Qt is unavailable (used during tests).
        """
        if not HAS_QT:
            return
        try:
            from .i18n_helper import tr
        except ImportError:
            from .i18n_helper import tr
        text = tr(message_id)
        if not text or text == message_id:
            return
        try:
            widget.setToolTip(text)
        except Exception:  # pragma: no cover - defensive
            pass

    def _connect_signals(self) -> None:
        """Connect UI signals to slots."""
        self.raster_browse_btn.clicked.connect(self._on_browse_raster)
        self.output_browse_btn.clicked.connect(self._on_browse_output)
        self.cancel_btn.clicked.connect(self.reject)
        self.vectorize_btn.clicked.connect(self._on_vectorize)
        self.profile_combo.currentIndexChanged.connect(self._on_profile_changed)
        self.save_preset_btn.clicked.connect(self._on_save_preset)
        self.load_preset_btn.clicked.connect(self._on_load_preset)

    # =========================================================================
    # Drag & Drop handlers
    # =========================================================================

    def dragEnterEvent(self, event) -> None:  # noqa: N802 (Qt convention)
        """Accept the drag if it contains at least one raster file."""
        if not HAS_QT:
            return
        mime = event.mimeData()
        if mime is None or not mime.hasUrls():
            event.ignore()
            return
        raster_paths = self.filter_raster_urls(mime.urls())
        if raster_paths:
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event) -> None:  # noqa: N802 (Qt convention)
        """Accept the drag if it contains at least one raster file."""
        if not HAS_QT:
            return
        mime = event.mimeData()
        if mime is None or not mime.hasUrls():
            event.ignore()
            return
        raster_paths = self.filter_raster_urls(mime.urls())
        if raster_paths:
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event) -> None:  # noqa: N802 (Qt convention)
        """Handle dropped files: populate raster field or enable batch mode.

        Single file: fills the raster path and updates the preview.
        Multiple files: populates the raster field with the first one AND
        emits the ``filesDropped`` signal so the host application (or a
        test) can switch to batch mode.
        """
        if not HAS_QT:
            return
        mime = event.mimeData()
        if mime is None or not mime.hasUrls():
            event.ignore()
            return
        raster_paths = self.filter_raster_urls(mime.urls())
        if not raster_paths:
            event.ignore()
            return
        event.acceptProposedAction()

        # Single file: classic single-file flow
        if len(raster_paths) == 1:
            self.raster_path_edit.setText(raster_paths[0])
            self._update_preview()
            return

        # Multiple files: use first as the visible "active" raster and
        # invoke the on_files_dropped callback (if registered) so the host
        # can run a batch.
        self.raster_path_edit.setText(raster_paths[0])
        self._update_preview()
        callback = getattr(self, "on_files_dropped", None)
        if callable(callback):
            try:
                callback(raster_paths)
            except Exception:  # pragma: no cover - defensive
                # Don't let a buggy callback break the drop
                pass

    def _on_browse_raster(self) -> None:
        """Handle raster file browser button click."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Raster File",
            "",
            "Raster Files (*.tif *.tiff *.png *.jpg *.jpeg *.bmp);;All Files (*)"
        )
        if file_path:
            self.raster_path_edit.setText(file_path)
            self._update_preview()

    def _on_browse_output(self) -> None:
        """Handle output file browser button click."""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Select Output File",
            "",
            "GeoPackage (*.gpkg);;GeoJSON (*.geojson);;Shapefile (*.shp);;All Files (*)"
        )
        if file_path:
            self.output_file_edit.setText(file_path)

    def _on_profile_changed(self, index: int) -> None:
        """Handle profile selection change."""
        profile_id = self.PROFILE_OPTIONS[index]

        # Update layer name with new profile
        self.layer_name_edit.setText(self._generate_default_layer_name(profile_id))

        # Update execution mode availability
        if profile_id != "regional-high-precision":
            # Disable 'tiled' for non-regional profiles
            if self.exec_mode_combo.currentIndex() == 2:  # 'tiled'
                self.exec_mode_combo.setCurrentIndex(0)  # Switch to 'auto'

    def _on_vectorize(self) -> None:
        """Handle vectorize button click."""
        # Validate input
        raster_path = self.raster_path_edit.text().strip()
        if not raster_path:
            QMessageBox.warning(self, "Validation Error", "Please select a raster file.")
            return

        output_path = self.output_file_edit.text().strip()
        if not output_path:
            QMessageBox.warning(self, "Validation Error", "Please specify an output file.")
            return

        # Check tiled mode for non-regional profiles
        if self.exec_mode_combo.currentText() == "tiled" and self.profile_combo.currentText() != "regional-high-precision":
            QMessageBox.warning(
                self,
                "Invalid Configuration",
                "Tiled execution mode is only supported for 'regional-high-precision' profile."
            )
            return

        # All good - the actual vectorization will be handled by the algorithm
        self.accept()

    def _on_save_preset(self) -> None:
        """Handle save preset button click."""
        params = self.get_parameters()

        if not HAS_QT:
            QMessageBox.information(
                self,
                "Presets",
                "Preset functionality requires Qt."
            )
            return

        # Use QInputDialog for name input
        from PyQt5.QtWidgets import QInputDialog
        text, ok = QInputDialog.getText(
            self,
            "Save Preset",
            "Enter preset name:",
        )

        if not ok or not text.strip():
            return

        preset_name = text.strip()

        try:
            filepath = self.save_preset(preset_name, params)
            QMessageBox.information(
                self,
                "Preset Saved",
                f"Preset '{preset_name}' saved successfully!"
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to save preset: {e}"
            )

    def _on_load_preset(self) -> None:
        """Handle load preset button click."""
        if not HAS_QT:
            QMessageBox.information(
                self,
                "Presets",
                "Preset functionality requires Qt."
            )
            return

        presets = self.list_presets()

        if not presets:
            QMessageBox.information(
                self,
                "No Presets",
                "No presets found. Save a preset first!"
            )
            return

        # Show dialog to select preset
        preset_names = [p.get("name", "Unnamed") for p in presets]
        from PyQt5.QtWidgets import QInputDialog
        selected, ok = QInputDialog.getItem(
            self,
            "Load Preset",
            "Select a preset:",
            preset_names,
            0,
            False
        )

        if not ok or not selected:
            return

        # Load and apply the preset
        preset = self.load_preset(selected)
        if preset:
            self.apply_preset(preset)
            QMessageBox.information(
                self,
                "Preset Loaded",
                f"Preset '{selected}' loaded!"
            )

    def _update_preview(self) -> None:
        """Update the raster preview information."""
        raster_path = self.raster_path_edit.text().strip()

        if not raster_path:
            self.preview_label.setText("")
            return

        path = Path(raster_path)
        if not path.exists():
            self.preview_label.setText(f"⚠️ File not found: {raster_path}")
            return

        try:
            # Try to get raster metadata without loading the full image
            info = self._get_raster_preview_info(raster_path)

            preview_text = f"📊 Size: {info['width']} × {info['height']} ({info['pixels']:,} px)"

            if info.get("tile_count"):
                preview_text += f" | Tiles: ~{info['tile_count']} ({info['tile_size']}px)"

            if info.get("warnings"):
                preview_text += f" | ⚠️ {info['warnings'][0]}"

            self.preview_label.setText(preview_text)

        except Exception as e:
            self.preview_label.setText(f"📊 {raster_path}")

    def _get_raster_preview_info(self, raster_path: str) -> dict[str, Any]:
        """Get raster metadata for preview without loading full image."""
        info = {
            "width": 0,
            "height": 0,
            "pixels": 0,
            "tile_count": None,
            "tile_size": 2048,
            "warnings": [],
        }

        try:
            from osgeo import gdal  # type: ignore
        except ImportError:
            info["warnings"].append("GDAL not available for preview")
            return info

        try:
            dataset = gdal.Open(raster_path)
            if dataset is None:
                info["warnings"].append("Could not open raster")
                return info

            info["width"] = dataset.RasterXSize
            info["height"] = dataset.RasterYSize
            info["pixels"] = info["width"] * info["height"]

            # Estimate tiles
            tile_size = 2048
            tiles_x = (info["width"] + tile_size - 1) // tile_size
            tiles_y = (info["height"] + tile_size - 1) // tile_size
            info["tile_count"] = tiles_x * tiles_y
            info["tile_size"] = tile_size

            # Add warnings for large rasters
            if info["pixels"] > 150_000_000:
                info["warnings"].append(f"Large raster - auto will use tiled mode")

        except Exception as e:
            info["warnings"].append(f"Could not read metadata: {e}")

        return info

    def _generate_default_layer_name(self, profile_id: str | None = None) -> str:
        """Generate a descriptive layer name with timestamp."""
        if profile_id is None:
            profile_id = self.profile_combo.currentText() if hasattr(self, 'profile_combo') else "regional-high-precision"

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        profile_short = profile_id.replace("-high-precision", "").replace("-", "_")
        return f"vectorized_{profile_short}_{timestamp}"

    def get_parameters(self) -> dict[str, Any]:
        """Get the dialog parameters as a dictionary."""
        return {
            "raster_path": self.raster_path_edit.text().strip(),
            "profile": self.profile_combo.currentText(),
            "engine": self.engine_combo.currentText(),
            "execution_mode": self.exec_mode_combo.currentText(),
            "output_format": self.OUTPUT_FORMAT_OPTIONS[self.output_format_combo.currentIndex()],
            "layer_name": self.layer_name_edit.text().strip(),
            "output_path": self.output_file_edit.text().strip(),
        }

    def set_progress(self, value: int) -> None:
        """Set the progress bar value (0-100)."""
        if hasattr(self, 'progress_bar'):
            self.progress_bar.setValue(value)

    def show_progress(self, visible: bool = True) -> None:
        """Show or hide the progress bar."""
        if hasattr(self, 'progress_bar'):
            self.progress_bar.setVisible(visible)

    def enable_controls(self, enabled: bool = True) -> None:
        """Enable or disable the dialog controls."""
        if hasattr(self, 'raster_path_edit'):
            self.raster_path_edit.setEnabled(enabled)
            self.raster_browse_btn.setEnabled(enabled)
            self.profile_combo.setEnabled(enabled)
            self.engine_combo.setEnabled(enabled)
            self.exec_mode_combo.setEnabled(enabled)
            self.output_format_combo.setEnabled(enabled)
            self.layer_name_edit.setEnabled(enabled)
            self.output_file_edit.setEnabled(enabled)
            self.output_browse_btn.setEnabled(enabled)
            self.vectorize_btn.setEnabled(enabled)
            self.cancel_btn.setEnabled(enabled)

    # =========================================================================
    # Preset Management
    # =========================================================================

    @staticmethod
    def _get_presets_dir() -> Path:
        """Get the directory for storing presets."""
        # Store presets in user's home directory under .qgis_vector_map
        home = Path.home()
        presets_dir = home / ".qgis_vector_map" / "presets"
        presets_dir.mkdir(parents=True, exist_ok=True)
        return presets_dir

    @classmethod
    def list_presets(cls) -> list[dict[str, Any]]:
        """List all available presets."""
        presets_dir = cls._get_presets_dir()
        presets = []

        for preset_file in presets_dir.glob("*.json"):
            try:
                with open(preset_file, "r", encoding="utf-8") as f:
                    preset = json.load(f)
                    preset["_filename"] = preset_file.name
                    presets.append(preset)
            except (json.JSONDecodeError, OSError):
                continue

        return sorted(presets, key=lambda p: p.get("name", ""))

    @classmethod
    def load_preset(cls, preset_name: str) -> dict[str, Any] | None:
        """Load a preset by name."""
        presets_dir = cls._get_presets_dir()

        # Try exact match first
        for preset_file in presets_dir.glob("*.json"):
            try:
                with open(preset_file, "r", encoding="utf-8") as f:
                    preset = json.load(f)
                    if preset.get("name") == preset_name:
                        return preset
            except (json.JSONDecodeError, OSError):
                continue

        return None

    @classmethod
    def save_preset(cls, name: str, parameters: dict[str, Any]) -> Path:
        """Save a preset with the given name and parameters."""
        presets_dir = cls._get_presets_dir()

        # Create safe filename from name
        safe_name = "".join(c if c.isalnum() or c in " -_" else "_" for c in name)
        safe_name = safe_name.strip()
        if not safe_name:
            safe_name = "preset"

        # Add timestamp to ensure uniqueness
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{safe_name}_{timestamp}.json"
        filepath = presets_dir / filename

        preset_data = {
            "name": name,
            "created": datetime.now().isoformat(),
            "profile": parameters.get("profile", "regional-high-precision"),
            "engine": parameters.get("engine", "auto"),
            "execution_mode": parameters.get("execution_mode", "auto"),
            "output_format": parameters.get("output_format", "auto"),
            "parameters": parameters.get("parameters", {}),
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(preset_data, f, indent=2)

        return filepath

    @classmethod
    def delete_preset(cls, preset_name: str) -> bool:
        """Delete a preset by name."""
        presets_dir = cls._get_presets_dir()

        for preset_file in presets_dir.glob("*.json"):
            try:
                with open(preset_file, "r", encoding="utf-8") as f:
                    preset = json.load(f)
                    if preset.get("name") == preset_name:
                        preset_file.unlink()
                        return True
            except (json.JSONDecodeError, OSError):
                continue

        return False

    def apply_preset(self, preset: dict[str, Any]) -> None:
        """Apply preset values to the dialog controls."""
        # Map preset values to combo boxes
        profile_map = {
            "regional-high-precision": 0,
            "edge-high-precision": 1,
            "linear-high-precision": 2,
        }

        exec_mode_map = {
            "auto": 0,
            "strict": 1,
            "tiled": 2,
        }

        output_format_map = {
            "auto": 0,
            "GeoPackage (.gpkg)": 1,
            "GeoJSON (.geojson)": 2,
            "ESRI Shapefile (.shp)": 3,
        }

        engine_map = {
            "auto": 0,
            "classic": 1,
            "opencv": 2,
        }

        # Apply profile
        profile = preset.get("profile", "regional-high-precision")
        if profile in profile_map:
            self.profile_combo.setCurrentIndex(profile_map[profile])

        # Apply engine
        engine = preset.get("engine", "auto")
        if engine in engine_map:
            self.engine_combo.setCurrentIndex(engine_map[engine])

        # Apply execution mode
        exec_mode = preset.get("execution_mode", "auto")
        if exec_mode in exec_mode_map:
            self.exec_mode_combo.setCurrentIndex(exec_mode_map[exec_mode])

        # Apply output format
        output_format = preset.get("output_format", "auto")
        if output_format in output_format_map:
            self.output_format_combo.setCurrentIndex(output_format_map[output_format])

        # Update layer name based on new profile
        self.layer_name_edit.setText(self._generate_default_layer_name(profile))