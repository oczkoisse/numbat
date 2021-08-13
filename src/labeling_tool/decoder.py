"""Provides Decoder, a utility class to decode video."""
import av
import numpy as np
from PySide6 import QtCore as qtc


class Decoder(qtc.QObject):
    """Decoder to read a video and emit decoded frames via signals.

    Attributes:
        decoded (PySide6.QtCore.Signal): Finished decoding.
    """

    decoded = qtc.Signal(float, tuple)

    def __init__(self, file_path: str):
        """Open the video at given path for decoding.

        Args:
            file_path: Path to video file.
        """
        super().__init__()
        self._path = file_path
        self._container = av.open(self._path, mode="r")
        # Default is SLICE: allows multiple threads to decode a single frame
        # FRAME: Enable multiple threads to decode independent frames
        self._container.streams.video[0].thread_type = "FRAME"
        self._decoder = self._container.decode(video=0)

    def on_decode(self):
        """Handle decode signal.

        Raises:
            ValueError: If the opened video file format is not supported.
        """
        frame = next(self._decoder, None)
        if frame is None:
            return

        if frame.format.name not in ["yuv420p", "yuvj420p"]:
            # Only supported pixel format are yuv420p and yuvj420p
            # yuvj420p is simply yuv420p but with full colors (0-255)
            raise ValueError(
                f"Unsupported pixel format '{frame.format.name} 'in video. "
                "Only yuv420p/yuvj420p videos are supported."
            )

        y, cb, cr = map(self._remove_padding, frame.planes)
        self.decoded.emit(frame.time, (y, cb, cr))

    def _remove_padding(self, plane: av.video.plane.VideoPlane) -> np.ndarray:
        """Remove padding from a video frame's plane.

        Args:
            plane: The plane to remove padding from.

        Returns:
            A 2D array representing the plane data with padding removed.
        """
        buf_width = plane.line_size
        bytes_per_pixel = 1
        frame_width = plane.width * bytes_per_pixel
        arr = np.frombuffer(plane, np.uint8)
        if buf_width != frame_width:
            # Slice (create a view) at the frame width
            arr = arr.reshape(-1, buf_width)[:, :frame_width]
        return arr.reshape(-1, frame_width)