from typing import Tuple

from PySide6 import QtWidgets as qtw
from PySide6 import QtCore as qtc
from PySide6 import QtGui as qtg
import av
import av.video
import numpy as np

from labeling_tool.Ui_MainWindow import Ui_MainWindow
from labeling_tool.VideoTimer import VideoTimer


class MainWindow(qtw.QMainWindow):
    """Main window of our video player"""

    video_files_filter = "Videos (*.mkv *.avi *.mp4 *.mov)"
    all_files_filter = "All files (*)"

    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self._decoder = None
        self._timer = None

        self.ui.act_file_open.triggered.connect(self.on_file_open)

    @qtc.Slot()
    def on_file_open(self):
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


class Decoder(qtc.QObject):
    decoded = qtc.Signal(float, tuple)

    def __init__(self, file_path):
        super().__init__()
        self._path = file_path
        self._container = av.open(self._path, mode="r")
        # Default is SLICE: allows multiple threads to decode a single frame
        # FRAME: Enable multiple threads to decode independent frames
        self._container.streams.video[0].thread_type = "FRAME"
        self._decoder = self._container.decode(video=0)

    def on_decode(self):
        frame = next(self._decoder, None)
        if frame is None:
            return

        if frame.format.name not in ["yuv420p", "yuvj420p"]:
            # Only supported pixel format are yuv420p and yuvj420p
            # yuvj420p is simply yuv420p but with full colors (0-255)
            raise ValueError(
                f"Unsupported pixel format '{frame.format.name} 'in video. Only yuv420p/yuvj420p videos are supported."
            )

        y, cb, cr = map(self._remove_padding, frame.planes)
        self.decoded.emit(frame.time, (y, cb, cr))

    def _remove_padding(self, plane):
        """Remove padding from a video frame's plane.

        Args:
            plane (av.video.plane.VideoPlane): the plane to remove padding from

        Returns:
            numpy.array: 2D array representing the plane data sans the padding
        """
        buf_width = plane.line_size
        bytes_per_pixel = 1
        frame_width = plane.width * bytes_per_pixel
        arr = np.frombuffer(plane, np.uint8)
        if buf_width != frame_width:
            # Slice (create a view) at the frame width
            arr = arr.reshape(-1, buf_width)[:, :frame_width]
        return arr.reshape(-1, frame_width)


def main():
    import sys

    app = qtw.QApplication(sys.argv)
    wnd = MainWindow()
    wnd.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
