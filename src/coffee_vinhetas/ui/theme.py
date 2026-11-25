"""Tema QSS Coffee Design System fiel à atmosfera espresso-âmbar da referência."""

from __future__ import annotations

import ctypes
import sys

from PySide6.QtWidgets import QWidget

from ..core.constants import (
    COLOR_AMBER,
    COLOR_AMBER_HOVER,
    COLOR_BG,
    COLOR_BORDER,
    COLOR_ELEVATED,
    COLOR_ERROR,
    COLOR_GREEN,
    COLOR_GREEN_HOVER,
    COLOR_SURFACE,
    COLOR_TEXT,
    COLOR_TEXT_DIM,
)
from .icons import ensure_qss_arrow_assets


def apply_windows_dark_titlebar(widget: QWidget) -> None:
    """Aplica barra de título escura nativa em diálogos no Windows 10/11 via DWM API."""
    if sys.platform != "win32":
        return
    try:
        hwnd = int(widget.winId())
        dwmapi = ctypes.windll.dwmapi
        dark_mode = ctypes.c_int(1)
        dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(dark_mode), ctypes.sizeof(dark_mode))
        caption_bgr = ctypes.c_int(0x000A0E14)  # BGR de #140E0A
        dwmapi.DwmSetWindowAttribute(hwnd, 35, ctypes.byref(caption_bgr), ctypes.sizeof(caption_bgr))
        border_bgr = ctypes.c_int(0x00283649)  # BGR de #493628
        dwmapi.DwmSetWindowAttribute(hwnd, 34, ctypes.byref(border_bgr), ctypes.sizeof(border_bgr))
    except Exception:
        pass


def build_stylesheet() -> str:
    arrows = ensure_qss_arrow_assets()
    up_url = arrows["chevron_up"]
    down_url = arrows["chevron_down"]

    return f"""
        QMainWindow, QDialog, QScrollArea {{
            background-color: {COLOR_BG};
            color: {COLOR_TEXT};
            font-family: "Segoe UI", Arial, sans-serif;
            font-size: 12px;
        }}
        QFrame#WindowShell {{
            background-color: {COLOR_BG};
            border: 1px solid #493527;
            border-radius: 12px;
        }}
        QWidget {{
            color: {COLOR_TEXT};
            font-family: "Segoe UI", Arial, sans-serif;
            font-size: 12px;
        }}
        QLabel, QCheckBox {{
            background-color: transparent;
        }}
        QFrame#SidebarFrame {{
            background: qlineargradient(
                x1:0, y1:0, x2:0, y2:1,
                stop:0 #1D140E, stop:0.65 #17100B, stop:1 #110B08
            );
            border-right: 1px solid #3C2B20;
            border-top-left-radius: 11px;
            border-bottom-left-radius: 11px;
        }}
        QPushButton#SidebarBtn {{
            background-color: transparent;
            color: #C7B6A6;
            border: 1px solid transparent;
            border-radius: 9px;
            padding: 9px 10px;
            text-align: left;
            font-size: 12px;
            font-weight: 500;
        }}
        QPushButton#SidebarBtn:hover {{
            background-color: rgba(223, 155, 87, 0.10);
            color: {COLOR_TEXT};
            border: 1px solid rgba(223, 155, 87, 0.25);
        }}
        QPushButton#SidebarBtn[active="true"] {{
            background: qlineargradient(
                x1:0, y1:0, x2:1, y2:1,
                stop:0 #6E4122, stop:0.55 #4A2B17, stop:1 #2B1A10
            );
            color: #FFF4E6;
            border: 1px solid #B57543;
            font-weight: 700;
        }}
        QToolButton#WinCtrlBtn {{
            background-color: rgba(20, 14, 10, 0.55);
            border: 1px solid rgba(90, 66, 48, 0.45);
            border-radius: 6px;
        }}
        QToolButton#WinCtrlBtn:hover {{
            background-color: rgba(223, 155, 87, 0.22);
            border-color: {COLOR_AMBER};
        }}
        QToolButton#WinCloseBtn {{
            background-color: rgba(20, 14, 10, 0.55);
            border: 1px solid rgba(90, 66, 48, 0.45);
            border-radius: 6px;
        }}
        QToolButton#WinCloseBtn:hover {{
            background-color: #C0392B;
            border-color: #E05A47;
        }}
        QFrame#Card {{
            background: qlineargradient(
                x1:0, y1:0, x2:0, y2:1,
                stop:0 #261B14, stop:1 #1B130E
            );
            border: 1px solid #4F3A2B;
            border-radius: 12px;
        }}
        QFrame#InnerCard {{
            background: qlineargradient(
                x1:0, y1:0, x2:1, y2:0,
                stop:0 #342419, stop:0.45 #261B14, stop:1 #1E1510
            );
            border: 1px solid #594130;
            border-radius: 10px;
        }}
        QFrame#FileIconBox {{
            background: qlineargradient(
                x1:0, y1:0, x2:1, y2:1,
                stop:0 #6E4728, stop:1 #452C19
            );
            border: 1px solid #8E5E38;
            border-radius: 8px;
        }}
        QFrame#DropZone {{
            background-color: rgba(24, 17, 12, 0.72);
            border: 1px dashed #7A5C45;
            border-radius: 10px;
        }}
        QFrame#DropZone:hover, QFrame#DropZone:focus {{
            background-color: rgba(45, 31, 21, 0.85);
            border: 1px dashed {COLOR_AMBER_HOVER};
        }}
        QFrame#DropZone[dragActive="true"] {{
            background-color: rgba(78, 50, 30, 0.85);
            border: 2px dashed {COLOR_AMBER_HOVER};
        }}
        QToolButton#IconToolBtn {{
            background-color: {COLOR_ELEVATED};
            border: 1px solid {COLOR_BORDER};
            border-radius: 8px;
            padding: 4px;
        }}
        QToolButton#IconToolBtn:hover {{
            background-color: #3F2E22;
            border-color: {COLOR_AMBER};
        }}
        QToolButton#PlayCircleBtn {{
            background: qlineargradient(
                x1:0, y1:0, x2:1, y2:1,
                stop:0 #4A311E, stop:1 #2A1C12
            );
            border: 2px solid {COLOR_AMBER};
            border-radius: 18px;
        }}
        QToolButton#PlayCircleBtn:hover {{
            background: qlineargradient(
                x1:0, y1:0, x2:1, y2:1,
                stop:0 #5E3F27, stop:1 #3A2618
            );
            border-color: {COLOR_AMBER_HOVER};
        }}
        QToolButton#RemoveItemBtn {{
            background-color: transparent;
            color: {COLOR_TEXT_DIM};
            border: none;
            border-radius: 4px;
            font-size: 14px;
            font-weight: 700;
        }}
        QToolButton#RemoveItemBtn:hover {{
            background-color: #4A2424;
            color: {COLOR_ERROR};
        }}
        QPushButton {{
            background-color: {COLOR_ELEVATED};
            color: {COLOR_TEXT};
            border: 1px solid {COLOR_BORDER};
            border-radius: 8px;
            padding: 6px 12px;
            font-weight: 600;
        }}
        QPushButton:hover {{
            border-color: {COLOR_AMBER};
            background-color: #3D2D22;
        }}
        QPushButton:focus {{
            border: 1px solid {COLOR_AMBER_HOVER};
        }}
        QPushButton:disabled {{
            background-color: #211914;
            color: #6E5F54;
            border-color: #33271F;
        }}
        QPushButton#GhostBtn {{
            background-color: #281D16;
            padding: 5px 10px;
            font-size: 11px;
        }}
        QPushButton#GhostBtn:hover {{
            background-color: #3A2A1F;
            border-color: {COLOR_AMBER};
        }}
        QPushButton#LinkBtn {{
            background-color: transparent;
            border: none;
            color: {COLOR_AMBER};
            font-size: 11px;
            font-weight: 600;
            padding: 2px 4px;
        }}
        QPushButton#LinkBtn:hover {{
            color: {COLOR_AMBER_HOVER};
        }}
        QPushButton#AmberBtn {{
            background: qlineargradient(
                x1:0, y1:0, x2:1, y2:0,
                stop:0 #D49250, stop:1 #EBB472
            );
            color: #18100B;
            border: none;
            padding: 7px 14px;
            font-weight: 700;
        }}
        QPushButton#AmberBtn:hover {{
            background: qlineargradient(
                x1:0, y1:0, x2:1, y2:0,
                stop:0 #E09F5A, stop:1 #F5C384
            );
        }}
        QPushButton#PreviewBtn {{
            background: qlineargradient(
                x1:0, y1:0, x2:0, y2:1,
                stop:0 #4A301E, stop:0.5 #312015, stop:1 #22160E
            );
            color: #FFF2E2;
            border: 1.5px solid #C88B51;
            border-radius: 10px;
            font-size: 13px;
            font-weight: 700;
            padding: 8px 18px;
        }}
        QPushButton#PreviewBtn:hover {{
            background: qlineargradient(
                x1:0, y1:0, x2:0, y2:1,
                stop:0 #5C3D26, stop:1 #302015
            );
            border-color: {COLOR_AMBER_HOVER};
        }}
        QPushButton#PreviewBtn:disabled {{
            background: #231A14;
            color: #7D6D60;
            border: 1px solid #413125;
        }}
        QPushButton#PrimaryGreenBtn {{
            background: qlineargradient(
                x1:0, y1:0, x2:0, y2:1,
                stop:0 #35C95D, stop:0.45 #22AA47, stop:1 #167E32
            );
            color: #FFFFFF;
            border: 1.5px solid #63E885;
            border-radius: 10px;
            font-size: 14px;
            font-weight: 700;
            padding: 8px 20px;
        }}
        QPushButton#PrimaryGreenBtn:hover {{
            background: qlineargradient(
                x1:0, y1:0, x2:0, y2:1,
                stop:0 #42D66A, stop:1 #1B8F3A
            );
        }}
        QPushButton#PrimaryGreenBtn:disabled {{
            background: qlineargradient(
                x1:0, y1:0, x2:0, y2:1,
                stop:0 #233B2A, stop:1 #1A2B1F
            );
            color: #7B9B82;
            border: 1px solid #304D38;
        }}
        QPushButton#CancelRedBtn {{
            background: qlineargradient(
                x1:0, y1:0, x2:0, y2:1,
                stop:0 #D14848, stop:1 #992929
            );
            color: #FFFFFF;
            border: 1.5px solid #EE6E6E;
            border-radius: 10px;
            font-size: 14px;
            font-weight: 700;
            padding: 8px 20px;
        }}
        QPushButton#CancelRedBtn:hover {{
            background: qlineargradient(
                x1:0, y1:0, x2:0, y2:1,
                stop:0 #DE5454, stop:1 #AD3131
            );
        }}
        QSlider::groove:horizontal {{
            background: #33251C;
            height: 6px;
            border-radius: 3px;
            border: 1px solid #4A3628;
        }}
        QSlider::sub-page:horizontal {{
            background: qlineargradient(
                x1:0, y1:0, x2:1, y2:0,
                stop:0 #C97A39, stop:1 #F4B970
            );
            border-radius: 3px;
        }}
        QSlider::handle:horizontal {{
            background: #FFF4E6;
            border: 2px solid #E59D56;
            width: 15px;
            height: 15px;
            margin: -5px 0;
            border-radius: 8px;
        }}
        QSlider::handle:horizontal:hover {{
            background: #FFFFFF;
            border-color: #FFD194;
        }}
        QSpinBox, QDoubleSpinBox, QComboBox, QLineEdit {{
            background-color: #211711;
            color: {COLOR_TEXT};
            border: 1px solid #594232;
            border-radius: 8px;
            padding: 3px 8px;
            min-height: 22px;
        }}
        QSpinBox, QDoubleSpinBox {{
            padding-right: 22px;
            font-weight: 600;
        }}
        QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus, QLineEdit:focus {{
            border-color: {COLOR_AMBER_HOVER};
        }}
        QSpinBox::up-button, QSpinBox::down-button,
        QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{
            subcontrol-origin: border;
            width: 20px;
            background-color: #2C1F17;
            border-left: 1px solid #4E3A2C;
        }}
        QSpinBox::up-button, QDoubleSpinBox::up-button {{
            subcontrol-position: top right;
            border-top-right-radius: 7px;
            border-bottom: 1px solid #4E3A2C;
        }}
        QSpinBox::down-button, QDoubleSpinBox::down-button {{
            subcontrol-position: bottom right;
            border-bottom-right-radius: 7px;
        }}
        QSpinBox::up-button:hover, QSpinBox::down-button:hover,
        QDoubleSpinBox::up-button:hover, QDoubleSpinBox::down-button:hover {{
            background-color: #3E2C20;
        }}
        QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {{
            image: url("{up_url}");
            width: 10px;
            height: 10px;
        }}
        QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {{
            image: url("{down_url}");
            width: 10px;
            height: 10px;
        }}
        QComboBox {{
            padding-right: 24px;
        }}
        QComboBox::drop-down {{
            subcontrol-origin: padding;
            subcontrol-position: top right;
            width: 22px;
            border-left: 1px solid #4E3A2C;
            background-color: #2C1F17;
            border-top-right-radius: 7px;
            border-bottom-right-radius: 7px;
        }}
        QComboBox::drop-down:hover {{
            background-color: #3E2C20;
        }}
        QComboBox::down-arrow {{
            image: url("{down_url}");
            width: 11px;
            height: 11px;
        }}
        QComboBox QAbstractItemView {{
            background-color: #281D16;
            color: {COLOR_TEXT};
            selection-background-color: #5A3B24;
            border: 1px solid #594232;
            outline: none;
        }}
        QListWidget, QTableWidget {{
            background-color: #19120D;
            border: 1px solid #463427;
            border-radius: 8px;
            outline: none;
        }}
        QListWidget::item {{
            background-color: transparent;
            border-bottom: 1px solid #291E17;
        }}
        QListWidget::item:selected, QTableWidget::item:selected {{
            background-color: #3E2A1C;
        }}
        QScrollBar:vertical {{
            background: #17100B;
            width: 8px;
            margin: 2px 1px 2px 1px;
            border-radius: 4px;
        }}
        QScrollBar::handle:vertical {{
            background: #543D2D;
            min-height: 22px;
            border-radius: 4px;
        }}
        QScrollBar::handle:vertical:hover {{
            background: {COLOR_AMBER};
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
            background: none;
            height: 0px;
        }}
        QHeaderView::section {{
            background-color: #281D16;
            color: {COLOR_TEXT};
            padding: 6px;
            border: none;
            border-bottom: 1px solid #493628;
            font-weight: 600;
        }}
        QProgressBar {{
            background-color: #382C25;
            border: 1px solid #594333;
            border-radius: 8px;
        }}
        QProgressBar::chunk {{
            background: qlineargradient(
                x1:0, y1:0, x2:1, y2:0,
                stop:0 #22A846, stop:0.65 #33C959, stop:1 #52E075
            );
            border-radius: 7px;
        }}
        QGroupBox {{
            border: 1px solid #4A3628;
            border-radius: 10px;
            margin-top: 10px;
            padding-top: 10px;
            font-weight: 600;
            color: {COLOR_AMBER};
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 6px;
        }}
        QCheckBox {{
            spacing: 6px;
            color: {COLOR_TEXT};
        }}
        QCheckBox::indicator {{
            width: 15px;
            height: 15px;
            border-radius: 4px;
            border: 1px solid #5A4333;
            background-color: #1D1510;
        }}
        QCheckBox::indicator:checked {{
            background-color: {COLOR_AMBER};
            border-color: {COLOR_AMBER};
        }}
        QToolTip {{
            background-color: #2B1F17;
            color: {COLOR_TEXT};
            border: 1px solid {COLOR_AMBER};
            padding: 5px 8px;
            border-radius: 6px;
        }}
    """
