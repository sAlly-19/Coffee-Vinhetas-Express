"""Área interativa centralizada de arrastar e soltar fiel à referência Coffee."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCursor, QDragEnterEvent, QDragLeaveEvent, QDropEvent
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget

from ...core.constants import COLOR_AMBER, COLOR_TEXT, COLOR_TEXT_DIM
from ..icons import render_svg_pixmap


class AudioDropZone(QFrame):
    """Área de arrastar e soltar centralizada com ícone âmbar e texto em duas linhas."""

    files_dropped = Signal(list)
    clicked = Signal()

    def __init__(
        self,
        prompt_text: str,
        sub_text: str = "ou clique para selecionar",
        icon_name: str = "cloud_upload",
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setObjectName("DropZone")
        self.setProperty("dragActive", False)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(62)

        outer = QHBoxLayout(self)
        outer.setContentsMargins(14, 8, 14, 8)
        outer.setSpacing(12)
        outer.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._icon_label = QLabel()
        self._icon_label.setPixmap(render_svg_pixmap(icon_name, 30, COLOR_AMBER))
        self._icon_label.setFixedSize(32, 32)
        self._icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        text_col = QVBoxLayout()
        text_col.setSpacing(2)
        text_col.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self._text_label = QLabel(prompt_text)
        self._text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._text_label.setStyleSheet(f"color: {COLOR_TEXT}; font-size: 12px; font-weight: 600;")

        self._sub_label = QLabel(sub_text)
        self._sub_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._sub_label.setStyleSheet(f"color: {COLOR_TEXT_DIM}; font-size: 11px;")

        text_col.addWidget(self._text_label)
        text_col.addWidget(self._sub_label)

        outer.addStretch(1)
        outer.addWidget(self._icon_label)
        outer.addLayout(text_col)
        outer.addStretch(1)

    def _set_drag_active(self, active: bool) -> None:
        self.setProperty("dragActive", active)
        self.style().unpolish(self)
        self.style().polish(self)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            self._set_drag_active(True)
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragLeaveEvent(self, event: QDragLeaveEvent) -> None:
        self._set_drag_active(False)
        super().dragLeaveEvent(event)

    def dropEvent(self, event: QDropEvent) -> None:
        self._set_drag_active(False)
        urls = event.mimeData().urls()
        paths = [Path(u.toLocalFile()) for u in urls if u.isLocalFile()]
        if paths:
            self.files_dropped.emit(paths)
            event.acceptProposedAction()
        else:
            event.ignore()

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event) -> None:
        if event.key() in (Qt.Key.Key_Space, Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.clicked.emit()
            return
        super().keyPressEvent(event)
