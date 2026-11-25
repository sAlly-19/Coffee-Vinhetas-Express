"""Widget QPainter luminoso da Curva de Atenuação (Ducking) fiel à referência."""

from __future__ import annotations

import math
from typing import Optional

from PySide6.QtCore import QPointF, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget

from ...core.constants import COLOR_TEXT_DIM


class DuckingCurveWidget(QWidget):
    """Curva ilustrativa luminosa de atenuação (ducking) com eixos dB e rótulos em 2 linhas."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._duck_percent = 75
        self._attack_ms = 150
        self._release_ms = 600
        self._entry_sec = 15
        self._jingle_sec = 12.0
        self.setMinimumSize(255, 134)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.MinimumExpanding)

    def sizeHint(self) -> QSize:
        return QSize(300, 146)

    def update_params(
        self,
        duck_percent: int,
        attack_ms: int,
        release_ms: int,
        entry_sec: int,
        jingle_sec: float,
    ) -> None:
        self._duck_percent = duck_percent
        self._attack_ms = attack_ms
        self._release_ms = release_ms
        self._entry_sec = entry_sec
        self._jingle_sec = jingle_sec if jingle_sec > 0 else 12.0
        self.update()

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = float(self.width())
        h = float(self.height())
        rect = QRectF(0.5, 0.5, w - 1.0, h - 1.0)
        painter.setPen(QPen(QColor("#3F2E22"), 1.0))
        painter.setBrush(QColor("#17100B"))
        painter.drawRoundedRect(rect, 10.0, 10.0)

        left = 44.0
        right = w - 12.0
        top = 12.0
        bottom = h - 32.0
        plot_w = max(40.0, right - left)
        plot_h = max(36.0, bottom - top)

        db_marks = [(0.0, "0 dB"), (-6.0, "-6 dB"), (-12.0, "-12 dB"), (-18.0, "-18 dB"), (-24.0, "-24 dB")]
        small_font = QFont(self.font())
        small_font.setPointSize(7)
        painter.setFont(small_font)

        for db_val, label in db_marks:
            y = top + (-db_val / 26.0) * plot_h
            painter.setPen(QPen(QColor("#2F221A"), 1.0, Qt.PenStyle.SolidLine))
            painter.drawLine(QPointF(left, y), QPointF(right, y))
            painter.setPen(QColor(COLOR_TEXT_DIM))
            painter.drawText(
                QRectF(3, y - 7, left - 7, 14),
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                label,
            )

        att_s = self._attack_ms / 1000.0
        rel_s = self._release_ms / 1000.0
        pre_s = 1.1
        hold_s = max(1.3, min(3.8, self._jingle_sec * 0.35))
        post_s = 1.1
        vis_att = max(0.32, min(1.4, att_s * 1.8))
        vis_rel = max(0.45, min(1.8, rel_s * 1.1))
        total_vis = pre_s + vis_att + hold_s + vis_rel + post_s

        def x_at(t: float) -> float:
            return left + (t / total_vis) * plot_w

        target_gain = max(0.05, 1.0 - self._duck_percent / 100.0)
        duck_db = max(-25.5, 20.0 * math.log10(target_gain))
        y_top = top + (2.5 / 26.0) * plot_h
        y_duck = top + (min(25.0, -duck_db + 2.5) / 26.0) * plot_h

        t_a = pre_s
        t_b = t_a + vis_att
        t_c = t_b + hold_s
        t_d = t_c + vis_rel

        # Guias verticais tracejadas
        painter.setPen(QPen(QColor("#785B45"), 1.0, Qt.PenStyle.DashLine))
        painter.drawLine(QPointF(x_at(t_a), top), QPointF(x_at(t_a), bottom))
        painter.drawLine(QPointF(x_at(t_d), top), QPointF(x_at(t_d), bottom))

        curve_path = QPainterPath()
        curve_path.moveTo(left, y_top)
        curve_path.lineTo(x_at(t_a), y_top)

        steps = 28
        for i in range(1, steps + 1):
            u = i / steps
            ease = 0.5 - 0.5 * math.cos(math.pi * u)
            curve_path.lineTo(x_at(t_a + u * (t_b - t_a)), y_top + ease * (y_duck - y_top))

        curve_path.lineTo(x_at(t_c), y_duck)

        for i in range(1, steps + 1):
            u = i / steps
            ease = 0.5 - 0.5 * math.cos(math.pi * u)
            curve_path.lineTo(x_at(t_c + u * (t_d - t_c)), y_duck + ease * (y_top - y_duck))

        curve_path.lineTo(right, y_top)

        # Preenchimento âmbar quente sob a curva
        fill_path = QPainterPath(curve_path)
        fill_path.lineTo(right, bottom)
        fill_path.lineTo(left, bottom)
        fill_path.closeSubpath()

        grad = QLinearGradient(0, y_top, 0, bottom)
        grad.setColorAt(0.0, QColor(228, 146, 60, 145))
        grad.setColorAt(0.55, QColor(186, 102, 34, 65))
        grad.setColorAt(1.0, QColor(120, 62, 18, 12))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(grad)
        painter.drawPath(fill_path)

        # Glow suave externo + linha brilhante interna
        glow_pen = QPen(QColor(246, 178, 92, 95), 5.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        painter.setPen(glow_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(curve_path)

        main_pen = QPen(QColor("#FFD392"), 2.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        painter.setPen(main_pen)
        painter.drawPath(curve_path)

        # Rótulos inferiores em 2 linhas
        painter.setPen(QColor("#DECBB9"))
        jingle_disp = f"{self._jingle_sec:.0f} s" if self._jingle_sec >= 10 else f"{self._jingle_sec:.1f} s"
        rel_disp = f"{self._release_ms / 1000.0:.1f} s".replace(".", ",")

        painter.drawText(
            QRectF(x_at(t_a) - 34, bottom + 3, 68, 26),
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
            f"Entrada\n({self._entry_sec} s)",
        )
        painter.drawText(
            QRectF(x_at(t_b) - 8, bottom + 3, (x_at(t_c) - x_at(t_b)) + 16, 26),
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
            f"Vinheta\n(≈ {jingle_disp})",
        )
        painter.drawText(
            QRectF(x_at(t_d) - 34, bottom + 3, 68, 26),
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
            f"Retorno\n(≈ {rel_disp})",
        )
