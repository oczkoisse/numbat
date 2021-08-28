"""Application's About dialog."""

from PySide6 import QtWidgets as qtw

from numbat.aboutdialog_ui import Ui_AboutDialog


class AboutDialog(qtw.QDialog):
    """Application's About dialog."""

    def __init__(self, parent):
        """Creates the About dialog."""
        super().__init__(parent)
        self.ui = Ui_AboutDialog()
        self.ui.setupUi(self)
