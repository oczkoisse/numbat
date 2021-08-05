from PySide6 import QtWidgets as qtw
from PySide6 import QtCore as qtc
from PySide6 import QtGui as qtg
import av
import av.video
import numpy as np
from typing import Tuple

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
        self._decoder = self._container.decode(video=0)

    def on_decode(self):
        frame = next(self._decoder, None)
        if frame is None:
            return

        frame_components = self.frame_to_ycbcr(frame)
        self.decoded.emit(frame.time, frame_components)

    def frame_to_ycbcr(self, frame) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        if frame.format.name not in ["yuv420p", "yuvj420p"]:
            # Only supported pixel format are yuv420p and yuvj420p
            # yuvj420p is simply yuv420p but with full colors (0-255)
            raise ValueError(
                f"Unsupported pixel format '{frame.format.name} 'in video. Only yuv420p/yuvj420p videos are supported."
            )

        # By default, src_colorspace and dst_colorspace are set to
        # None, which translates to sws_cs_DEFAULT colorspace
        # Undocumented, but if both src and dst colorspaces are same,
        # even if they are not the same as the colorspace of the frame,
        # no new frame copy is created and frame_data is a numpy
        # array created using the buffer protocol
        frame_data = frame.to_ndarray(format=frame.format.name)

        # For YCbCr 420p frames, the returned array is shaped with the
        # same width as the full frame. First comes the Luma channel
        # with the same height as the full frame. Next come the chroma
        # channels with the same width as the full frame but height is
        # a quarter of the full frame height
        start_offset = 0
        end_offset = frame.height
        y_data = frame_data[start_offset:end_offset, :]
        start_offset = end_offset
        end_offset = (5 * frame.height) // 4
        cb_data = frame_data[start_offset:end_offset, :].reshape(-1, frame.width // 2)
        start_offset = end_offset
        end_offset = None
        cr_data = frame_data[start_offset:, :].reshape(-1, frame.width // 2)

        return y_data, cb_data, cr_data


def main():
    import sys

    app = qtw.QApplication(sys.argv)
    wnd = MainWindow()
    wnd.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
