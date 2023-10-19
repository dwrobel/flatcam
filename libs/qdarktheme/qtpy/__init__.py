"""Package applying Qt compat of PyQt6, PySide6, PyQt5 and PySide2."""
from libs.qdarktheme.qtpy.qt_compat import QtImportError
from libs.qdarktheme.qtpy.qt_version import __version__

try:
    from libs.qdarktheme.qtpy import QtCore, QtGui, QtSvg, QtWidgets
except ImportError:
    from libs.qdarktheme.util import get_logger as __get_logger

    __logger = __get_logger(__name__)
    __logger.warning("Failed to import QtCore, QtGui, QtSvg and QtWidgets.")
