"""Widget QPainter de forma de onda real com suporte a visualização e alças de corte."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QCursor, QLinearGradient, QPainter, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget

from ...core.constants import COLOR_AMBER, COLOR_AMBER_HOVER, COLOR_TEXT, COLOR_TEXT_DIM


class WaveformWidget(QWidget):
    """Exibe a forma de onda real em degradê âmbar com região de corte e alças arrastáveis opcionais."""

    seek_requested = Signal(float)  # fração 0..1
    trim_changed = Signal(float, float)  # start_frac, end_frac

    def __init__(self, interactive_trim: bool = False, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._peaks: list[float] = []
        self._progress: float = 0.0
        self._loading: bool = False
        self._trim_start: float = 0.0
        self._trim_end: float = 1.0
        self._interactive_trim = interactive_trim
        self._dragging_handle: Optional[str] = None  # "start" | "end" | None

        if interactive_trim:
            self.setMinimumHeight(112)
            self.setMaximumHeight(136)
            self.setMouseTracking(True)
            self.setToolTip("Arraste as alças laterais para definir início e fim do corte, ou clique no centro para ouvir.")
        else:
            self.setMinimumHeight(40)
            self.setMaximumHeight(46)
            self.setToolTip("Forma de onda real da vinheta. Clique para avançar ou retroceder na reprodução.")

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

    def set_loading(self, loading: bool) -> None:
        self._loading = loading
        if loading:
            self._peaks = []
            self._progress = 0.0
            self._trim_start = 0.0
            self._trim_end = 1.0
        self.update()

    def set_peaks(self, peaks: list[float]) -> None:
        self._loading = False
        self._peaks = peaks
        self.update()

    def set_progress(self, fraction: float) -> None:
        self._progress = max(0.0, min(1.0, fraction))
        self.update()

    def set_trim_range(self, start_frac: float, end_frac: float) -> None:
        s = max(0.0, min(0.98, start_frac))
        e = max(s + 0.01, min(1.0, end_frac))
        self._trim_start = s
        self._trim_end = e
        self.update()

    def clear(self) -> None:
        self._loading = False
        self._peaks = []
        self._progress = 0.0
        self._trim_start = 0.0
        self._trim_end = 1.0
        self.update()

    def _x_to_frac(self, x: float) -> float:
        pad_x = 8.0 if self._interactive_trim else 4.0
        draw_w = max(10.0, self.width() - 2 * pad_x)
        return max(0.0, min(1.0, (x - pad_x) / draw_w))

    def _frac_to_x(self, frac: float) -> float:
        pad_x = 8.0 if self._interactive_trim else 4.0
        draw_w = max(10.0, self.width() - 2 * pad_x)
        return pad_x + frac * draw_w

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._peaks and self.width() > 0:
            x = event.position().x()
            if self._interactive_trim:
                sx = self._frac_to_x(self._trim_start)
                ex = self._frac_to_x(self._trim_end)
                tol = 12.0
                if abs(x - sx) <= tol and abs(x - sx) <= abs(x - ex):
                    self._dragging_handle = "start"
                    return
                if abs(x - ex) <= tol:
                    self._dragging_handle = "end"
                    return
            frac = self._x_to_frac(x)
            self.seek_requested.emit(frac)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._interactive_trim and self._peaks:
            x = event.position().x()
            if self._dragging_handle == "start":
                new_s = max(0.0, min(self._trim_end - 0.015, self._x_to_frac(x)))
                self._trim_start = new_s
                self.trim_changed.emit(self._trim_start, self._trim_end)
                self.update()
                return
            if self._dragging_handle == "end":
                new_e = min(1.0, max(self._trim_start + 0.015, self._x_to_frac(x)))
                self._trim_end = new_e
                self.trim_changed.emit(self._trim_start, self._trim_end)
                self.update()
                return

            sx = self._frac_to_x(self._trim_start)
            ex = self._frac_to_x(self._trim_end)
            if abs(x - sx) <= 12.0 or abs(x - ex) <= 12.0:
                self.setCursor(QCursor(Qt.CursorShape.SizeHorCursor))
            else:
                self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if self._dragging_handle is not None:
            self._dragging_handle = None
            return
        super().mouseReleaseEvent(event)

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = float(self.width())
        h = float(self.height())
        mid_y = h / 2.0

        if self._interactive_trim:
            painter.setPen(QPen(QColor("#4D392B"), 1.0))
            painter.setBrush(QColor("#16100B"))
            painter.drawRoundedRect(QRectF(0.5, 0.5, w - 1.0, h - 1.0), 10.0, 10.0)

        painter.setPen(QPen(QColor("#3E2D21"), 1.0))
        painter.drawLine(QPointF(4, mid_y), QPointF(w - 4, mid_y))

        if self._loading:
            painter.setPen(QColor(COLOR_TEXT_DIM))
            painter.drawText(QRectF(0, 0, w, h), Qt.AlignmentFlag.AlignCenter, "Calculando forma de onda...")
            return

        if not self._peaks:
            painter.setPen(QColor("#6E594A"))
            painter.drawText(
                QRectF(0, 0, w, h),
                Qt.AlignmentFlag.AlignCenter,
                "Selecione uma vinheta para visualizar a forma de onda",
            )
            return

        pad_x = 8.0 if self._interactive_trim else 4.0
        pad_y = 10.0 if self._interactive_trim else 3.0
        draw_w = max(10.0, w - 2 * pad_x)
        max_half_h = max(4.0, (h - 2 * pad_y) / 2.0)

        bar_step = 3.0
        bar_w = 1.8
        bar_count = max(16, int(draw_w // bar_step))
        play_x = pad_x + self._progress * draw_w
        sx = pad_x + self._trim_start * draw_w
        ex = pad_x + self._trim_end * draw_w
        has_trim = self._trim_start > 0.002 or self._trim_end < 0.998

        active_grad = QLinearGradient(0, pad_y, 0, h - pad_y)
        active_grad.setColorAt(0.0, QColor("#FFD08A"))
        active_grad.setColorAt(0.5, QColor("#E79346"))
        active_grad.setColorAt(1.0, QColor("#FFD08A"))

        outside_brush = QColor("#544032")

        for i in range(bar_count):
            src_idx = min(len(self._peaks) - 1, int(i * len(self._peaks) / bar_count))
            amp = max(0.05, self._peaks[src_idx])
            bar_h = amp * max_half_h
            x = pad_x + i * bar_step
            in_trim = (x >= sx - 1.0) and (x <= ex + 1.0)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(active_grad if in_trim else outside_brush)
            painter.drawRoundedRect(QRectF(x, mid_y - bar_h, bar_w, bar_h * 2.0), 0.9, 0.9)

        # Sombreamento fora da região selecionada
        if has_trim or self._interactive_trim:
            shade = QColor(12, 8, 5, 145)
            if sx > pad_x:
                painter.fillRect(QRectF(pad_x, 2.0, sx - pad_x, h - 4.0), shade)
            if ex < w - pad_x:
                painter.fillRect(QRectF(ex, 2.0, (w - pad_x) - ex, h - 4.0), shade)

            # Moldura superior/inferior da região ativa
            painter.setPen(QPen(QColor(COLOR_AMBER), 1.5))
            painter.drawLine(QPointF(sx, 2.0), QPointF(ex, 2.0))
            painter.drawLine(QPointF(sx, h - 2.0), QPointF(ex, h - 2.0))

            # Linhas verticais de corte
            painter.setPen(QPen(QColor(COLOR_AMBER_HOVER), 2.0))
            painter.drawLine(QPointF(sx, 2.0), QPointF(sx, h - 2.0))
            painter.drawLine(QPointF(ex, 2.0), QPointF(ex, h - 2.0))

            if self._interactive_trim:
                # Alças arrastáveis visuais
                for hx in (sx, ex):
                    handle_rect = QRectF(hx - 6.0, mid_y - 16.0, 12.0, 32.0)
                    painter.setPen(QPen(QColor("#FFF0DC"), 1.2))
                    painter.setBrush(QColor(COLOR_AMBER))
                    painter.drawRoundedRect(handle_rect, 4.0, 4.0)
                    painter.setPen(QPen(QColor("#1A120C"), 1.4))
                    painter.drawLine(QPointF(hx - 1.5, mid_y - 7.0), QPointF(hx - 1.5, mid_y + 7.0))
                    painter.drawLine(QPointF(hx + 1.5, mid_y - 7.0), QPointF(hx + 1.5, mid_y + 7.0))

        if self._progress > 0:
            painter.setPen(QPen(QColor(COLOR_TEXT), 1.6))
            painter.drawLine(QPointF(play_x, 2.0), QPointF(play_x, h - 2.0))
