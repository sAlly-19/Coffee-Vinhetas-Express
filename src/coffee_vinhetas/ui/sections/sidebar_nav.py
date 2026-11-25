"""Barra lateral de navegação Coffee com 5 abas e ilustração da xícara na base."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QRect, QSize, Qt, Signal
from PySide6.QtGui import QColor, QCursor, QLinearGradient, QPainter, QPixmap
from PySide6.QtWidgets import QFrame, QPushButton, QVBoxLayout, QWidget

from ...core.constants import COLOR_AMBER_HOVER, COLOR_TEXT_DIM, get_asset_path
from ..icons import make_svg_icon


class SidebarNav(QFrame):
    """Sidebar esquerda com abas Início, Processo, Histórico, Configurações e Sobre."""

    page_selected = Signal(int)

    NAV_ITEMS: tuple[tuple[str, str], ...] = (
        ("Início", "home"),
        ("Processo", "sliders"),
        ("Histórico", "history"),
        ("Configurações", "settings"),
        ("Sobre", "info"),
    )

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("SidebarFrame")
        self.setFixedWidth(152)

        cup_path = get_asset_path("sidebar_cup.png")
        self._cup_pixmap = QPixmap(str(cup_path)) if cup_path.is_file() else QPixmap()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 74, 10, 12)
        layout.setSpacing(6)

        self._buttons: list[QPushButton] = []
        for idx, (label, icon_name) in enumerate(self.NAV_ITEMS):
            btn = QPushButton(f" {label}")
            btn.setObjectName("SidebarBtn")
            btn.setProperty("active", idx == 0)
            btn.setIcon(make_svg_icon(icon_name, 16, COLOR_AMBER_HOVER if idx == 0 else COLOR_TEXT_DIM))
            btn.setIconSize(QSize(16, 16))
            btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            btn.clicked.connect(lambda _=False, i=idx: self._on_btn_clicked(i))
            layout.addWidget(btn)
            self._buttons.append(btn)

        layout.addStretch(1)

    def _on_btn_clicked(self, index: int) -> None:
        self.set_active_index(index)
        self.page_selected.emit(index)

    def set_active_index(self, index: int) -> None:
        for idx, btn in enumerate(self._buttons):
            active = idx == index
            btn.setProperty("active", active)
            icon_name = self.NAV_ITEMS[idx][1]
            btn.setIcon(make_svg_icon(icon_name, 16, "#FFF4E6" if active else COLOR_TEXT_DIM))
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        if self._cup_pixmap.isNull():
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        w = self.width() - 1
        h = self.height()
        cup_h = min(220, int(h * 0.34))
        scaled = self._cup_pixmap.scaled(
            w, cup_h, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation
        )
        src_x = max(0, (scaled.width() - w) // 2)
        src_y = max(0, scaled.height() - cup_h)
        target_rect = QRect(0, h - cup_h, w, cup_h)
        painter.setOpacity(0.88)
        painter.drawPixmap(target_rect, scaled, QRect(src_x, src_y, w, cup_h))
        painter.setOpacity(1.0)

        # Fade suave no topo da imagem para fundir com o fundo da sidebar
        fade = QLinearGradient(0, h - cup_h, 0, h - cup_h + 70)
        fade.setColorAt(0.0, QColor(20, 14, 10, 255))
        fade.setColorAt(1.0, QColor(20, 14, 10, 0))
        painter.fillRect(QRect(0, h - cup_h, w, 70), fade)
