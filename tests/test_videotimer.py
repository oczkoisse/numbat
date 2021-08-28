import time

from PySide6 import QtCore as qtc

from numbat.videotimer import VideoTimer


class DummyDecoder(qtc.QObject):
    decoded = qtc.Signal(float, tuple, bool)
    finished = qtc.Signal()

    def __init__(self, seq_pts, decode_time=0.1):
        super().__init__()
        self._seq_pts = iter(seq_pts)
        self._decode_time = decode_time

    @qtc.Slot()
    def on_decode(self):
        pts_sec = next(self._seq_pts, None)
        if pts_sec is not None:
            time.sleep(self._decode_time)
            self.decoded.emit(pts_sec, None, False)
        else:
            self.finished.emit()


class DummyRenderer(qtc.QObject):
    prepared = qtc.Signal()
    rendered = qtc.Signal()

    def __init__(self, prep_time=0.1, render_time=0.1):
        super().__init__()
        self._prep_time = prep_time
        self._render_time = render_time

    @qtc.Slot(tuple)
    def on_prepare(self, frame_components):
        time.sleep(self._prep_time)
        self.prepared.emit()

    @qtc.Slot()
    def on_render(self):
        time.sleep(self._render_time)
        self.rendered.emit()


def test_video_timer_signal_seq(qtbot):
    timer = VideoTimer()

    decoder = DummyDecoder([1.0])
    renderer = DummyRenderer()

    timer.bind_decoder(decoder)
    timer.bind_renderer(renderer)

    signals = [
        (timer.decode, "decode"),
        (decoder.decoded, "decoded"),
        (timer.prepare, "prepare"),
        (renderer.prepared, "prepared"),
        (timer.render, "render"),
        (renderer.rendered, "rendered"),
    ]

    # checking order using 'order' arg seems buggy
    with qtbot.waitSignals(signals):
        timer.start()
