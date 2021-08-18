"""Custom widgets."""
from PySide6 import QtCore as qtc
from PySide6 import QtGui as qtg
from PySide6 import QtWidgets as qtw


class SeekBar(qtw.QSlider):
    """A slider widget repurposed as a seekbar for a stream.

    It allows mouse click to immediately switch slider to the clicked at
    position.

    Signals:
        seeked: Slider position changed either due to a click or dragging of
            slider. Provides new position as an integer in slider's range.
    """

    seeked = qtc.Signal(int)

    def __init__(self, parent: qtw.QWidget = None):
        """Create a new seek bar.

        Args:
            parent (optional): Parent widget. Defaults to None.
        """
        super().__init__(parent)

    def mousePressEvent(self, ev: qtg.QMouseEvent):
        """Handle mouse press events.

        Only left clicks are handled by setting slider value to clicked at
        position.

        Args:
            ev: Mouse event.
        """
        self.setSliderDown(True)
        if ev.button() == qtc.Qt.LeftButton:
            self.setValue(self._val_for_position(ev.x()))

    def mouseMoveEvent(self, ev: qtg.QMouseEvent):
        """Handle mouse dragging events.

        Slider value is set to position just moved to.

        Args:
            ev: Mouse event.
        """
        # No need to check which button; it is always Qt.NoButton
        self.setValue(self._val_for_position(ev.x()))

    def mouseReleaseEvent(self, ev: qtg.QMouseEvent):
        """Handle mouse release events.

        It emits 'seek' signal on every call.

        Args:
            ev: Mouse event.
        """
        self.setSliderDown(False)
        self.seeked.emit(self.value())

    def _val_for_position(self, pos):
        """Calculates slider value corresponding to the click's position."""
        return qtw.QStyle.sliderValueFromPosition(
            self.minimum(), self.maximum(), pos, self.width()
        )
