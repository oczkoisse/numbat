"""Main window of application."""
from PySide6 import QtCore as qtc
from PySide6 import QtWidgets as qtw

from labeling_tool.decoder import Decoder
from labeling_tool.Ui_MainWindow import Ui_MainWindow
from labeling_tool.VideoTimer import VideoTimer


class MainWindow(qtw.QMainWindow):
    """Main window of application."""

    video_files_filter = "Videos (*.mkv *.avi *.mp4 *.mov)"
    all_files_filter = "All files (*)"

    def __init__(self):
        """Create the window."""
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self._decoder = None
        self._timer = None

        self.ui.act_file_open.triggered.connect(self.on_file_open)

    @qtc.Slot()
    def on_file_open(self):
        """Handle file open dialog."""
        file_path, _ = qtw.QFileDialog.getOpenFileName(
            self,
            "Choose video",
            qtc.QDir.homePath(),
            filter=";;".join(
                [MainWindow.video_files_filter, MainWindow.all_files_filter]
            ),
            selectedFilter=MainWindow.video_files_filter,
        )

        # Open file for FFMpeg
        if len(file_path) > 0:
            self._decoder = Decoder(file_path)
            self._timer = VideoTimer()
            self._timer.bind_decoder(self._decoder)
            self._timer.bind_renderer(self.ui.glwgt_video)
            self._timer.start()


def main():
    """Start the application and enter Qt event loop."""
    import sys

    app = qtw.QApplication(sys.argv)
    wnd = MainWindow()
    wnd.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
