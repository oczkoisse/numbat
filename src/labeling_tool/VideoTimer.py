"""Provides VideoTimer, a utility class to coordinate frame timings."""
from typing import Any, Tuple

from PySide6 import QtCore as qtc


class VideoTimer(qtc.QObject):
    """A timer to present video frames at their presentation time.

    Frames in a video file have presentation timestamps that indicate an
    absolute time in terms of video duration when the frame should be rendered.
    A video timer provides the functionality to time the various stages of
    reading a video by emitting 'decode', 'prepare' and 'render' signals.

    Attributes:
        decode (PySide6.QtCore.Signal): Start decoding
        prepare (PySide6.QtCore.Signal): Allocate resources for rendering
        render (PySide6.QtCore.Signal): Start rendering
    """

    decode = qtc.Signal()
    prepare = qtc.Signal(tuple)
    render = qtc.Signal()

    def __init__(self):
        """Create a video timer."""
        super().__init__()
        # Reference clock to compare the timestamps with
        self._clock = qtc.QElapsedTimer()
        # Single shot timer that sends the 'render' signal on timeout
        self._timer = qtc.QTimer()
        self._timer.setSingleShot(True)
        self._timer.setTimerType(qtc.Qt.TimerType.PreciseTimer)
        self._timer.timeout.connect(self._on_timeout)
        # Previous presentation time in ms
        # Initially -1 so that first timestamp >= this timestamp
        self._last_presented_at = -1
        # Presentation time in ms
        self._present_at = 0

    @qtc.Slot(float, tuple)
    def on_decoded(self, pt_sec: float, frame: Tuple):
        """Get notified when a frame is decoded.

        Args:
            pt_sec (float): Presentation time in seconds
            frame (Tuple): Frame components received from decoder
        """
        # First frame
        if self._last_presented_at < 0:
            # Start the clock only after decoding the first frame
            self._clock.start()

        present_at_ms = int(pt_sec * 1000)
        if present_at_ms <= self._last_presented_at:
            # Skip frame since last frame was drawn too late
            qtc.qDebug("Skipping frame with pts {}".format(present_at_ms))
            self.decode.emit()
            return
        # Update current presentation time for later timer call
        self._present_at = present_at_ms
        self.prepare.emit(frame)

    @qtc.Slot()
    def _on_timeout(self):
        """Handle timer expiration.

        Timer is started after resources are allocated for rendering and only
        if some positive time is left for render call.
        """
        self._last_presented_at = self._clock.elapsed()
        qtc.qDebug(
            "Presented frame with pts {} at {} ms".format(
                self._present_at, self._last_presented_at
            )
        )
        self.render.emit()

    @qtc.Slot()
    def on_rendered(self):
        """Get notified when rendering is finished."""
        # Start the cycle again
        self.decode.emit()

    @qtc.Slot()
    def on_prepared(self):
        """Get notified when resource allocation for rendering is complete."""
        rem = self._present_at - self._clock.elapsed()
        if rem <= 0:
            # No time left, just trigger timeout handler directly
            self._on_timeout()
        else:
            self._timer.start(rem)

    def stop(self):
        """Stop the timer."""
        self._timer.stop()

    def start(self):
        """Start sending timed signals to decoder and renderer.

        Must bind a decoder and renderer before calling.
        """
        self.decode.emit()

    def bind_decoder(self, decoder: Any):
        """Bind a decoder with this timer.

        A decoder object must implement 'decoded' signal. Additionally, it must
        implement 'on_decode' slot to handle 'decode' signal of timer.

        Args:
            decoder: An object that behaves like a decoder
        """
        decoder.decoded.connect(self.on_decoded)
        self.decode.connect(decoder.on_decode)

    def bind_renderer(self, renderer: Any):
        """Bind a renderer with this timer.

        A renderer object must implement 'prepared' and 'rendered' signals.
        Additionally, a renderer object must implement 'on_prepare' and
        'on_render' slots to handle 'prepare' and 'render' signal of timer.

        Args:
            renderer: An object that behaves like a renderer
        """
        self.prepare.connect(renderer.on_prepare)
        renderer.prepared.connect(self.on_prepared)
        self.render.connect(renderer.on_render)
        renderer.rendered.connect(self.on_rendered)
