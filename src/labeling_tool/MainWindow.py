from PySide6 import QtWidgets as qtw
from PySide6 import QtCore as qtc
from PySide6 import QtGui as qtg
import av
import av.video

from labeling_tool.Ui_MainWindow import Ui_MainWindow


class MainWindow(qtw.QMainWindow):
    """Main window of our video player"""

    video_files_filter = "Videos (*.mkv *.avi *.mp4 *.mov)"
    all_files_filter = "All files (*)"

    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.ui.act_file_open.triggered.connect(self.on_file_open)

    def frame_to_ycbcr(self, frame):
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
            container = av.open(file_path, mode="r")
            decoder = container.decode(video=0)

            elapsedTimer = qtc.QElapsedTimer()
            timer = qtc.QTimer()
            timer.setSingleShot(True)

            elapsedTimer.start()
            frame = next(decoder)
            y, cb, cr = self.frame_to_ycbcr(frame)
            self.ui.glwgt_video.refresh_frame(y, cb, cr)
            self.ui.glwgt_video.update()

            timer.timeout.connect(timeout_action)
            timer.start()


if __name__ == "__main__":
    import sys

    app = qtw.QApplication(sys.argv)
    wnd = MainWindow()
    wnd.show()
    sys.exit(app.exec())
