from typing import Tuple

from PySide6 import QtCore as qtc


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

    # Start decoding
    decode = qtc.Signal()

    # Start allocating resources for rendering
    prepare = qtc.Signal(tuple)

    # Start rendering
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
        self._timer.timeout.connect(self.render)
        # Previous presentation time in ms
        # Initially -1 so that first timestamp >= this timestamp
        self._last_presented_at = -1
        # Time until presentation in ms
        self._present_after_ms = 0

    @qtc.Slot(float, tuple)
    def on_decoded(self, pt_sec: float, frame: Tuple):
        """Get notified when a frame is decoded.

        Args:
            pt_sec (float): presentation time in seconds
            frame (Tuple): frame components received from decoder

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
        """Start sending timed signals to decoder and renderer.

        Must bind a decoder and renderer before calling.
        """
        self._clock.start()
        self.decode.emit()

    def bind_decoder(self, decoder):
        """Bind a decoder with this timer.

        A decoder object must implement 'decoded' signal. Additionally, it must
        implement 'on_decode' slot to handle 'decode' signal of timer.

        Args:
            decoder (Any): any object that behaves like a decoder
        """
        decoder.decoded.connect(self.on_decoded)
        self.decode.connect(decoder.on_decode)

    def bind_renderer(self, renderer):
        """Bind a renderer with this timer.

        A renderer object must implement 'prepared' and 'rendered' signals.
        Additionally, a renderer object must implement 'on_prepare' and
        'on_render' slots to handle 'prepare' and 'render' signal of timer.

        Args:
            renderer (Any): any object that behaves like a renderer
        """
        self.prepare.connect(renderer.on_prepare)
        renderer.prepared.connect(self.on_prepared)
        self.render.connect(renderer.on_render)
        renderer.rendered.connect(self.on_rendered)
