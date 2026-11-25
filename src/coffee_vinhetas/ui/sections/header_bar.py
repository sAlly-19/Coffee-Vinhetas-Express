"""Cabeçalho frameless com identidade Coffee, grãos de café e controles − □ ×."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QPoint, QRect, QSize, Qt, Signal
from PySide6.QtGui import QColor, QCursor, QLinearGradient, QPainter, QPixmap
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QToolButton, QVBoxLayout, QWidget

from ...core.constants import APP_NAME, APP_SUBTITLE, COLOR_AMBER, COLOR_ERROR, COLOR_TEXT, COLOR_TEXT_DIM, get_asset_path
from ..icons import make_svg_icon, render_svg_pixmap


class HeaderBar(QFrame):
    """Cabeçalho superior arrastável com imagem de grãos de café e botões de janela."""

    ffmpeg_clicked = Signal()
    minimize_requested = Signal()
    maximize_requested = Signal()
    close_requested = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(74)
        self._drag_offset: Optional[QPoint] = None

        beans_path = get_asset_path("header_beans.png")
        self._beans_pixmap = QPixmap(str(beans_path)) if beans_path.is_file() else QPixmap()

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 8, 12, 8)
        layout.setSpacing(12)

        logo_lbl = QLabel()
        logo_lbl.setPixmap(render_svg_pixmap("logo", 46))
        logo_lbl.setFixedSize(48, 48)

        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        title_col.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        title_lbl = QLabel(
            f'<span style="color:{COLOR_TEXT};">{APP_NAME}</span>'
            f'<span style="color:{COLOR_AMBER}; font-weight:400;"> — Inserção em Massa</span>'
        )
        title_lbl.setStyleSheet("font-size: 20px; font-weight: 700;")

        sub_lbl = QLabel(APP_SUBTITLE)
        sub_lbl.setStyleSheet(f"font-size: 12px; color: {COLOR_TEXT_DIM};")

        title_col.addWidget(title_lbl)
        title_col.addWidget(sub_lbl)

        # Coluna direita: controles da janela no topo + badge discreto de FFmpeg abaixo
        right_col = QVBoxLayout()
        right_col.setSpacing(6)
        right_col.setContentsMargins(0, 0, 0, 0)

        win_row = QHBoxLayout()
        win_row.setSpacing(5)
        win_row.addStretch(1)

        self.min_btn = QToolButton()
        self.min_btn.setObjectName("WinCtrlBtn")
        self.min_btn.setIcon(make_svg_icon("win_min", 13, COLOR_TEXT))
        self.min_btn.setIconSize(QSize(13, 13))
        self.min_btn.setFixedSize(26, 22)
        self.min_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.min_btn.setToolTip("Minimizar")
        self.min_btn.clicked.connect(self.minimize_requested.emit)

        self.max_btn = QToolButton()
        self.max_btn.setObjectName("WinCtrlBtn")
        self.max_btn.setIcon(make_svg_icon("win_max", 12, COLOR_TEXT))
        self.max_btn.setIconSize(QSize(12, 12))
        self.max_btn.setFixedSize(26, 22)
        self.max_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.max_btn.setToolTip("Maximizar / Restaurar")
        self.max_btn.clicked.connect(self.maximize_requested.emit)

        self.close_btn = QToolButton()
        self.close_btn.setObjectName("WinCloseBtn")
        self.close_btn.setIcon(make_svg_icon("win_close", 12, COLOR_TEXT))
        self.close_btn.setIconSize(QSize(12, 12))
        self.close_btn.setFixedSize(26, 22)
        self.close_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.close_btn.setToolTip("Fechar")
        self.close_btn.clicked.connect(self.close_requested.emit)

        win_row.addWidget(self.min_btn)
        win_row.addWidget(self.max_btn)
        win_row.addWidget(self.close_btn)

        badge_row = QHBoxLayout()
        badge_row.addStretch(1)
        self.ffmpeg_badge = QPushButton("FFmpeg: verificando...")
        self.ffmpeg_badge.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.ffmpeg_badge.setToolTip("Status real do FFmpeg/FFprobe. Clique para configurar ou inspecionar.")
        self.ffmpeg_badge.clicked.connect(self.ffmpeg_clicked.emit)
        badge_row.addWidget(self.ffmpeg_badge)

        right_col.addLayout(win_row)
        right_col.addLayout(badge_row)

        layout.addWidget(logo_lbl)
        layout.addLayout(title_col, 1)
        layout.addLayout(right_col)

    def set_ffmpeg_available(self, available: bool) -> None:
        if available:
            self.ffmpeg_badge.setText("FFmpeg: pronto")
            self.ffmpeg_badge.setStyleSheet(
                "background-color: rgba(24, 52, 32, 0.85); color: #82E899; border: 1px solid #306940; "
                "border-radius: 10px; padding: 2px 9px; font-size: 10px; font-weight: 600;"
            )
        else:
            self.ffmpeg_badge.setText("FFmpeg: ausente")
            self.ffmpeg_badge.setStyleSheet(
                f"background-color: rgba(68, 28, 28, 0.90); color: {COLOR_ERROR}; border: 1px solid #7E3A3A; "
                "border-radius: 10px; padding: 2px 9px; font-size: 10px; font-weight: 600;"
            )

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        w = self.width()
        h = self.height()

        if not self._beans_pixmap.isNull():
            img_w = min(380, int(w * 0.44))
            scaled = self._beans_pixmap.scaled(
                img_w, h, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation
            )
            src_y = max(0, (scaled.height() - h) // 2)
            target = QRect(w - img_w, 0, img_w, h)
            painter.setOpacity(0.75)
            painter.drawPixmap(target, scaled, QRect(0, src_y, img_w, h))
            painter.setOpacity(1.0)

            fade_left = QLinearGradient(w - img_w, 0, w - img_w + 130, 0)
            fade_left.setColorAt(0.0, QColor(20, 14, 10, 255))
            fade_left.setColorAt(1.0, QColor(20, 14, 10, 0))
            painter.fillRect(QRect(w - img_w, 0, 130, h), fade_left)

            fade_bot = QLinearGradient(0, h - 22, 0, h)
            fade_bot.setColorAt(0.0, QColor(20, 14, 10, 0))
            fade_bot.setColorAt(1.0, QColor(20, 14, 10, 220))
            painter.fillRect(QRect(w - img_w, h - 22, img_w, 22), fade_bot)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            win = self.window()
            if win and not win.isMaximized():
                self._drag_offset = event.globalPosition().toPoint() - win.frameGeometry().topLeft()
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._drag_offset is not None and event.buttons() & Qt.MouseButton.LeftButton:
            win = self.window()
            if win:
                win.move(event.globalPosition().toPoint() - self._drag_offset)
                event.accept()
                return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        self._drag_offset = None
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.maximize_requested.emit()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)
