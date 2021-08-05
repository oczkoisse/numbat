from PySide6 import QtCore as qtc
import numpy as np
from typing import Tuple


class VideoTimer(qtc.QObject):
    """A timer class to present video frames at their presentation time.

    Frames in a video file have presentation timestamps that indicate an
    absolute time in terms of video duration when the frame should be rendered.
    A VideoTimer emits signals: 'decode', 'prepare' and 'render'. A receiver
    that connects to 'decode' signal is interested in timing its decoding
    process to remain in sync with presenation timestamps. A receiver that
    connects to 'prepare' and 'render' is interested in timing its remain in
    sync with presenation timestamps.
    """

    # Indicate that a receiver should start decoding
    decode = qtc.Signal()

    # Indicate that a receiver should start preparing
    prepare = qtc.Signal(tuple)

    # Indicate that a receiver should start rendering
    render = qtc.Signal()

    def __init__(self):
        """Create a video timer."""
        super().__init__()
        self._clock = qtc.QElapsedTimer()
        # Create a single shot timer that sends the 'render' signal on timeout
        self._timer = qtc.QTimer()
        self._timer.setSingleShot(True)
        self._timer.setTimerType(qtc.Qt.TimerType.PreciseTimer)
        self._timer.timeout.connect(self.render)
        # Previous presentation time in ms
        self._last_presented_at = -1
        # Time until presentation in ms
        self._present_after_ms = 0

    @qtc.Slot(float, tuple)
    def on_decoded(
        self, pt_sec: float, frame: Tuple[np.ndarray, np.ndarray, np.ndarray]
    ):
        """Get notified when a frame is decoded.

        Args:
            pt_sec (float): presentation time in seconds
            frame: frame components received from decoder

        Raises:
            ValueError: if presentation time is lesser than the previous one
        """
        present_at_ms = pt_sec * 1000
        if present_at_ms <= self._last_presented_at:
            # Presentation timestamps should be monotonic but are not
            raise ValueError(
                "Encountered non-monotonic pts value {cur} after {prv}".format(
                    cur=present_at_ms, prv=self._last_presented_at
                )
            )
        self._present_after_ms = present_at_ms - self._last_presented_at
        self._last_presented_at = present_at_ms

        self.prepare.emit(frame)

    @qtc.Slot()
    def on_rendered(self):
        """Get notified when rendering is finished."""
        # Start the cycle again
        self.start()

    @qtc.Slot()
    def on_prepared(self):
        """Get notified when resource allocation for rendering is complete."""
        time_spent_ms = self._clock.elapsed()
        self._timer.start(max(self._present_after_ms - time_spent_ms, 0))

    def stop(self):
        """Stop the timer."""
        self._timer.stop()

    def start(self):
        """Begin decoding and rendering.

        Must bind a decoder and renderer before calling.
        """
        self._clock.start()
        self.decode.emit()

    def bind_decoder(self, decoder):
        decoder.decoded.connect(self.on_decoded)
        self.decode.connect(decoder.on_decode)

    def bind_renderer(self, renderer):
        self.prepare.connect(renderer.on_prepare)
        renderer.prepared.connect(self.on_prepared)
        self.render.connect(renderer.on_render)
        renderer.rendered.connect(self.on_rendered)
