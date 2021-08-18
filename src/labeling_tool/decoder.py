"""Provides Decoder, a utility class to decode video."""
from fractions import Fraction

import av
import numpy as np
from PySide6 import QtCore as qtc


class Decoder(qtc.QObject):
    """Decoder to read a video and emit decoded frames via signals.

    Signals:
        decoded: Finished decoding. Provides 3 values: a stream timestamp in
            seconds, a tuple of video planes and a bool to indicate that the
            decoded frame was result of a seek operation.
        finished: All frames have been decoded and resources deallocated.
            Any code referencing the decoded object should set it to None.
            Using decoder beyond this point has undefined behavior.
    """

    decoded = qtc.Signal(float, tuple, bool)
    finished = qtc.Signal()

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
        # Most up to date position to seek to
        self._seek = None

    def on_decode(self):
        """Handle decode signal.

        If decoding results in a new frame, 'decoded' signal is emitted.

        Raises:
            ValueError: If the opened video file format is not supported.
        """
        if self.is_closed():
            return

        seeked = self._seek is not None
        if seeked:
            # Seek to a keyframe near offset specified in stream.time_base
            # since we specified stream explicitly
            self._container.seek(self._seek, stream=self._container.streams.video[0])
            self._seek = None

        frame = next(self._decoder, None)
        if frame is None:
            self.close()
            self.finished.emit()
            return

        if frame.format.name not in ["yuv420p", "yuvj420p"]:
            # Only supported pixel format are yuv420p and yuvj420p
            # yuvj420p is simply yuv420p but with full colors (0-255)
            raise ValueError(
                f"Unsupported pixel format '{frame.format.name} 'in video. "
                "Only yuv420p/yuvj420p videos are supported."
            )

        y, cb, cr = map(self._remove_padding, frame.planes)
        self.decoded.emit(frame.time, (y, cb, cr), seeked)

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

    @property
    def duration(self) -> int:
        """Duration in stream.time_base units."""
        stream = self._container.streams.video[0]
        duration = stream.duration
        if duration is None:
            duration = self._container.duration / av.time_base / stream.time_base
        return int(duration + 0.5)

    @property
    def time_base(self) -> Fraction:
        """Time base of stream."""
        return self._container.streams.video[0].time_base

    def seek(self, to: int):
        """Seek to the specified timestamp in stream.

        Args:
            to (int): timestamp in stream's time base units.
        """
        self._seek = to

    def close(self):
        """Deallocate all decoding resources."""
        self._container.close()
        self._decoder = None
        self._container = None
        self._seek = None

    def is_closed(self):
        """Check if decoder has been closed."""
        return self._container is None
