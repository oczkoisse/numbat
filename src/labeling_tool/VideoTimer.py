from PySide6 import QtCore as qtc


class VideoTimer(qtc.QObject):
    """A timer class to present video frames at their presentation time.

    Frames in a video file have presentation timestamps that indicate an
    absolute time in terms of video duration when the frame should be rendered.
    A VideoTimer emits two signals: 'decode' and 'render'. A receiver
    that connects to 'decode' signal is interested in timing its decoding
    process to remain in sync with a renderer. A receiver that connects to
    'render' is interested in timing its rendering process to a frame's
    presentation timestamp.
    """

    # Indicate that a receiver should start decoding
    decode = qtc.Signal()

    # Indicate that a receiver should start rendering
    render = qtc.Signal()

    def __init__(self):
        """Create a video timer."""
        self._timer = qtc.QElapsedTimer()
        # Create a single shot timer that sends the 'render' signal on timeout
        self._render_timer = qtc.QTimer()
        self._render_timer.setSingleShot(True)
        self._render_timer.setTimerType(qtc.Qt.TimerType.PreciseTimer)
        self._render_timer.timeout.connect(self.render)
        # Previous presentation time in ms
        self._prev_pt_ms = 0
        # Time until presentation in ms
        self._pt_ms = 0

    @qtc.Slot
    def on_decoded(self, pt_sec):
        """Get notified when a frame is decoded.

        Args:
            pt_sec (int): presentation time in milliseconds

        Raises:
            ValueError: if presentation time is lesser than the previous one
        """
        pt_ms = pt_sec * 1000
        if pt_ms <= self._prev_pt_ms:
            # Presentation timestamps should be monotonic but are not
            raise ValueError(
                "Encountered non-monotonic pts value {cur} after {prv}".format(
                    cur=pt_ms, prv=self._prev_pt_ms
                )
            )
        self._pt_ms = pt_ms - self._prev_pt_ms
        self._prev_mt_ms = pt_ms

        self.prepare.emit()

    @qtc.Slot
    def on_rendered(self):
        """Get notified when rendering is finished."""
        self._timer.start()
        self.decode.emit()

    @qtc.Slot
    def on_prepared(self):
        """Get notified when resource allocation for rendering is complete."""
        time_spent_ms = self._timer.elapsed()
        self._render_timer.startTimer(max(self._pt_ms - time_spent_ms, 0))

    def stop(self):
        """Stop the timer."""
        self._render_timer.stop()
