"""Switch deslizante animado para opções booleanas."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Property, QEasingCurve, QPropertyAnimation, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QCursor, QPainter, QPen
from PySide6.QtWidgets import QWidget

from ...core.constants import COLOR_AMBER, COLOR_BORDER, COLOR_ELEVATED, COLOR_GREEN, COLOR_TEXT, COLOR_TEXT_DIM


class ToggleSwitch(QWidget):
    """Switch deslizante nativo em estilo Coffee com animação suave e acessibilidade."""

    toggled = Signal(bool)

    def __init__(self, checked: bool = False, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._checked = checked
        self._offset = 1.0 if checked else 0.0
        self.setFixedSize(44, 24)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAccessibleName("Alternar repetição automática")

        self._anim = QPropertyAnimation(self, b"thumbOffset", self)
        self._anim.setDuration(150)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    def get_thumb_offset(self) -> float:
        return self._offset

    def set_thumb_offset(self, val: float) -> None:
        self._offset = val
        self.update()

    thumbOffset = Property(float, get_thumb_offset, set_thumb_offset)

    def isChecked(self) -> bool:
        return self._checked

    def setChecked(self, checked: bool, emit_signal: bool = False) -> None:
        if self._checked == checked:
            return
        self._checked = checked
        self._anim.stop()
        self._anim.setStartValue(self._offset)
        self._anim.setEndValue(1.0 if checked else 0.0)
        self._anim.start()
        if emit_signal:
            self.toggled.emit(self._checked)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self.isEnabled():
            self.setChecked(not self._checked, emit_signal=True)
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event) -> None:
        if event.key() in (Qt.Key.Key_Space, Qt.Key.Key_Return, Qt.Key.Key_Enter) and self.isEnabled():
            self.setChecked(not self._checked, emit_signal=True)
            return
        super().keyPressEvent(event)

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = QRectF(1, 1, self.width() - 2, self.height() - 2)
        if not self.isEnabled():
            track_color = QColor("#302A26")
        elif self._checked:
            track_color = QColor(COLOR_GREEN)
        else:
            track_color = QColor(COLOR_ELEVATED)

        border_color = QColor(COLOR_AMBER if self.hasFocus() else COLOR_BORDER)
        painter.setPen(QPen(border_color, 1.5 if self.hasFocus() else 1.0))
        painter.setBrush(track_color)
        painter.drawRoundedRect(rect, rect.height() / 2.0, rect.height() / 2.0)

        thumb_d = self.height() - 6
        x_min = 3.0
        x_max = self.width() - thumb_d - 3.0
        x = x_min + (x_max - x_min) * self._offset
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(COLOR_TEXT if self.isEnabled() else COLOR_TEXT_DIM))
        painter.drawEllipse(QRectF(x, 3.0, thumb_d, thumb_d))
