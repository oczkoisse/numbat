"""Main window of application."""
from PySide6 import QtCore as qtc
from PySide6 import QtWidgets as qtw

from numbat.aboutdialog import AboutDialog
from numbat.decoder import Decoder
from numbat.mainwindow_ui import Ui_MainWindow
from numbat.videotimer import VideoTimer


class MainWindow(qtw.QMainWindow):
    """Main window of application."""

    video_files_filter = "Videos (*.mkv *.avi *.mp4 *.mov)"
    all_files_filter = "All files (*)"

    def __init__(self):
        """Create the window."""
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        # Play/pause button and seekbar are disabled by default
        self.ui.btn_play.setEnabled(False)
        self.ui.seek_bar.setEnabled(False)
        self._decoder = None
        self._timer = None

        self.ui.act_file_open.triggered.connect(self.on_file_open)
        self.ui.act_about.triggered.connect(self._on_about_dialog)
        self.ui.seek_bar.seeked.connect(self._on_seeked)
        self.ui.btn_play.clicked.connect(self._on_play)

    @qtc.Slot()
    def on_file_open(self):
        """Handle file open dialog."""
        if self._timer is not None and not self._timer.is_paused():
            self._timer.pause()

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
            # Enable play/pause button and seekbar
            self.ui.btn_play.setEnabled(True)
            self.ui.seek_bar.setEnabled(True)
            self.ui.seek_bar.setRange(0, self._decoder.duration)
            self._decoder.decoded.connect(self._on_decoded)
            self._decoder.finished.connect(self._on_finished)
            self._timer = VideoTimer()
            self._timer.bind_decoder(self._decoder)
            self._timer.bind_renderer(self.ui.glwgt_video)

        if self._timer is not None:
            self._timer.start()

    def _on_decoded(self, pts_sec):
        """Update seek bar to decoded frame's timestamp."""
        # If slider is being held down, seek bar should not be updated
        if not self.ui.seek_bar.isSliderDown():
            # Convert pts_sec to stream's time_base
            seek_to = int(pts_sec / self._decoder.time_base)
            self.ui.seek_bar.setValue(seek_to)

    def _on_seeked(self, val: int):
        """Handle seek signal emitted by seek bar."""
        self._decoder.seek(val)
        if self._timer.is_paused():
            self._timer.decode.emit()

    def _on_finished(self):
        """Handle end of video playback."""
        self._decoder = None
        self.ui.seek_bar.setValue(0)
        self.ui.seek_bar.setDisabled(True)
        self.ui.btn_play.setDisabled(True)

    def _on_play(self):
        """Handle play/pause button click.

        Toggles the video timer.
        """
        if self._timer is not None:
            if self._timer.is_paused():
                self._timer.start()
            else:
                self._timer.pause()

    def _on_about_dialog(self):
        dlg_about = AboutDialog(self)
        dlg_about.exec()


def main():
    """Start the application and enter Qt event loop."""
    import sys

    app = qtw.QApplication(sys.argv)
    wnd = MainWindow()
    wnd.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
