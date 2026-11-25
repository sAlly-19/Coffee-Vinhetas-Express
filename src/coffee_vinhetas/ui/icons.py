"""Ícones vetoriais SVG e geração de setas QSS minimalistas."""

from __future__ import annotations

from PySide6.QtCore import QByteArray, QRectF, Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

from ..core.constants import COLOR_TEXT
from ..core.logging_setup import get_app_data_dir

SVG_TEMPLATES: dict[str, str] = {
    "logo": """
        <svg viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M10 18H31V27C31 32.5 26.5 37 21 37H20C14.5 37 10 32.5 10 27V18Z"
                fill="#2E1F16" stroke="#F0B56E" stroke-width="2.4" stroke-linejoin="round"/>
          <path d="M31 20H34.8C37 20 38.8 21.8 38.8 24C38.8 26.2 37 28 34.8 28H31"
                stroke="#F0B56E" stroke-width="2.4" stroke-linecap="round"/>
          <path d="M8 40H33" stroke="#F0B56E" stroke-width="2.4" stroke-linecap="round"/>
          <path d="M14.5 26.5V29.5M17.5 23.5V31.5M20.5 21V32.5M23.5 24V30.5M26.5 26V29"
                stroke="#FFE0B2" stroke-width="2.1" stroke-linecap="round"/>
          <path d="M16 12C16 10 18 9.2 18 7M21.5 12C21.5 10 23.5 9.2 23.5 7M27 12C27 10 29 9.2 29 7"
                stroke="#F0B56E" stroke-width="2" stroke-linecap="round"/>
        </svg>
    """,
    "home": """
        <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M4 11L12 4L20 11V19.5C20 20.1 19.6 20.5 19 20.5H14.5V15H9.5V20.5H5C4.4 20.5 4 20.1 4 19.5V11Z"
                stroke="{color}" stroke-width="1.9" stroke-linejoin="round"/>
        </svg>
    """,
    "history": """
        <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <circle cx="12" cy="12" r="8.5" stroke="{color}" stroke-width="1.9"/>
          <path d="M12 7.5V12.2L15.2 14" stroke="{color}" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
    """,
    "clock": """
        <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <circle cx="12" cy="12" r="8.5" stroke="{color}" stroke-width="1.8"/>
          <path d="M12 7.5V12L15 13.8" stroke="{color}" stroke-width="1.8" stroke-linecap="round"/>
        </svg>
    """,
    "speaker": """
        <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M4.5 9.5H8.5L13.5 5.5V18.5L8.5 14.5H4.5V9.5Z" stroke="{color}" stroke-width="1.8" stroke-linejoin="round"/>
          <path d="M16.5 9C17.6 10.2 17.6 13.8 16.5 15M19 6.8C21 9.4 21 14.6 19 17.2" stroke="{color}" stroke-width="1.8" stroke-linecap="round"/>
        </svg>
    """,
    "repeat": """
        <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M17 4L20 7L17 10" stroke="{color}" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"/>
          <path d="M4 11V9C4 7.9 4.9 7 6 7H19.5" stroke="{color}" stroke-width="1.9" stroke-linecap="round"/>
          <path d="M7 20L4 17L7 14" stroke="{color}" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"/>
          <path d="M20 13V15C20 16.1 19.1 17 18 17H4.5" stroke="{color}" stroke-width="1.9" stroke-linecap="round"/>
        </svg>
    """,
    "cloud_upload": """
        <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M7 18H6C3.8 18 2 16.2 2 14C2 12 3.5 10.3 5.5 10C6.2 7.1 8.8 5 12 5C15.5 5 18.4 7.6 18.9 11C20.7 11.4 22 13 22 14.8C22 16.6 20.6 18 18.8 18H17"
                stroke="{color}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
          <path d="M12 19V11.5M12 11.5L9.2 14.3M12 11.5L14.8 14.3" stroke="{color}" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
    """,
    "cpu": """
        <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <rect x="7" y="7" width="10" height="10" rx="2" stroke="{color}" stroke-width="1.8"/>
          <rect x="10" y="10" width="4" height="4" rx="0.5" fill="{color}"/>
          <path d="M9.5 4V7M14.5 4V7M9.5 17V20M14.5 17V20M4 9.5H7M4 14.5H7M17 9.5H20M17 14.5H20"
                stroke="{color}" stroke-width="1.8" stroke-linecap="round"/>
        </svg>
    """,
    "curve": """
        <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M3 16L8 10L13 14L20 7" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          <circle cx="8" cy="10" r="1.5" fill="{color}"/>
          <circle cx="13" cy="14" r="1.5" fill="{color}"/>
          <circle cx="20" cy="7" r="1.5" fill="{color}"/>
        </svg>
    """,
    "waveform_mini": """
        <svg viewBox="0 0 28 20" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M3 9V11M6.5 6V14M10 4V16M13.5 2V18M17 5V15M20.5 7V13M24 9V11"
                stroke="{color}" stroke-width="1.8" stroke-linecap="round"/>
        </svg>
    """,
    "chevrons_right": """
        <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M7 6L13 12L7 18M13 6L19 12L13 18" stroke="{color}" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
    """,
    "win_min": """
        <svg viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M3.5 8.5H12.5" stroke="{color}" stroke-width="1.5" stroke-linecap="round"/>
        </svg>
    """,
    "win_max": """
        <svg viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
          <rect x="3.5" y="3.5" width="9" height="9" rx="1" stroke="{color}" stroke-width="1.4"/>
        </svg>
    """,
    "win_close": """
        <svg viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M4 4L12 12M12 4L4 12" stroke="{color}" stroke-width="1.5" stroke-linecap="round"/>
        </svg>
    """,
    "music": """
        <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M9 18V6L20 4V16" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          <circle cx="6.5" cy="18.5" r="2.5" stroke="{color}" stroke-width="2"/>
          <circle cx="17.5" cy="16.5" r="2.5" stroke="{color}" stroke-width="2"/>
        </svg>
    """,
    "folder": """
        <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M3 7C3 5.9 3.9 5 5 5H9.5L11.5 7H19C20.1 7 21 7.9 21 9V17C21 18.1 20.1 19 19 19H5C3.9 19 3 18.1 3 17V7Z"
                stroke="{color}" stroke-width="2" stroke-linejoin="round"/>
        </svg>
    """,
    "upload": """
        <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M12 15V4M12 4L7.5 8.5M12 4L16.5 8.5" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          <path d="M4 15V18C4 19.1 4.9 20 6 20H18C19.1 20 20 19.1 20 18V15" stroke="{color}" stroke-width="2" stroke-linecap="round"/>
        </svg>
    """,
    "play": """
        <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M7.5 5.5L18.5 12L7.5 18.5V5.5Z" fill="{color}" stroke="{color}" stroke-width="1.5" stroke-linejoin="round"/>
        </svg>
    """,
    "play_circle": """
        <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <circle cx="12" cy="12" r="9.5" stroke="{color}" stroke-width="1.8"/>
          <path d="M10 8.2L16.2 12L10 15.8V8.2Z" fill="{color}"/>
        </svg>
    """,
    "pause": """
        <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <rect x="6.5" y="5" width="4" height="14" rx="1" fill="{color}"/>
          <rect x="13.5" y="5" width="4" height="14" rx="1" fill="{color}"/>
        </svg>
    """,
    "stop": """
        <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <rect x="6" y="6" width="12" height="12" rx="2" fill="{color}"/>
        </svg>
    """,
    "settings": """
        <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <circle cx="12" cy="12" r="3" stroke="{color}" stroke-width="2"/>
          <path d="M19.4 15A1.65 1.65 0 0 0 19.73 16.82L19.79 16.88A2 2 0 1 1 16.96 19.71L16.9 19.65A1.65 1.65 0 0 0 15.08 19.32A1.65 1.65 0 0 0 14.08 20.83V21A2 2 0 1 1 10.08 21V20.91A1.65 1.65 0 0 0 9 19.4A1.65 1.65 0 0 0 7.18 19.73L7.12 19.79A2 2 0 1 1 4.29 16.96L4.35 16.9A1.65 1.65 0 0 0 4.68 15.08A1.65 1.65 0 0 0 3.17 14.08H3A2 2 0 1 1 3 10.08H3.09A1.65 1.65 0 0 0 4.6 9A1.65 1.65 0 0 0 4.27 7.18L4.21 7.12A2 2 0 1 1 7.04 4.29L7.1 4.35A1.65 1.65 0 0 0 8.92 4.68H9A1.65 1.65 0 0 0 10 3.17V3A2 2 0 1 1 14 3V3.09A1.65 1.65 0 0 0 15 4.6A1.65 1.65 0 0 0 16.82 4.27L16.88 4.21A2 2 0 1 1 19.71 7.04L19.65 7.1A1.65 1.65 0 0 0 19.32 8.92V9A1.65 1.65 0 0 0 20.83 10H21A2 2 0 1 1 21 14H20.91A1.65 1.65 0 0 0 19.4 15Z"
                stroke="{color}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
    """,
    "info": """
        <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <circle cx="12" cy="12" r="9" stroke="{color}" stroke-width="2"/>
          <path d="M12 11V16" stroke="{color}" stroke-width="2" stroke-linecap="round"/>
          <circle cx="12" cy="8" r="1.2" fill="{color}"/>
        </svg>
    """,
    "check": """
        <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <circle cx="12" cy="12" r="9.5" fill="#183A22" stroke="{color}" stroke-width="1.8"/>
          <path d="M8 12.2L10.8 15L16.2 9.4" stroke="{color}" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
    """,
    "sliders": """
        <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M4 7H14M18 7H20M4 12H8M12 12H20M4 17H14M18 17H20" stroke="{color}" stroke-width="2" stroke-linecap="round"/>
          <circle cx="16" cy="7" r="2" stroke="{color}" stroke-width="2"/>
          <circle cx="10" cy="12" r="2" stroke="{color}" stroke-width="2"/>
          <circle cx="16" cy="17" r="2" stroke="{color}" stroke-width="2"/>
        </svg>
    """,
    "trash": """
        <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M5 7H19M9 7V5H15V7M8 7V19H16V7" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
    """,
    "scissors": """
        <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <circle cx="6.5" cy="7" r="2.5" stroke="{color}" stroke-width="1.9"/>
          <circle cx="6.5" cy="17" r="2.5" stroke="{color}" stroke-width="1.9"/>
          <path d="M8.6 8.4L19 16M8.6 15.6L19 8" stroke="{color}" stroke-width="1.9" stroke-linecap="round"/>
        </svg>
    """,
    "bolt": """
        <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M13 2L4.5 13.5H11.5L10.5 22L19.5 10.5H12.5L13 2Z" stroke="{color}" stroke-width="2" stroke-linejoin="round"/>
        </svg>
    """,
}


def render_svg_pixmap(name: str, size: int, color: str = COLOR_TEXT, dpr: float = 2.0) -> QPixmap:
    svg_str = SVG_TEMPLATES[name].replace("{color}", color)
    renderer = QSvgRenderer(QByteArray(svg_str.encode("utf-8")))
    px_size = max(1, int(round(size * dpr)))
    pixmap = QPixmap(px_size, px_size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    renderer.render(painter, QRectF(0, 0, px_size, px_size))
    painter.end()
    pixmap.setDevicePixelRatio(dpr)
    return pixmap


def make_svg_icon(name: str, size: int = 18, color: str = COLOR_TEXT) -> QIcon:
    return QIcon(render_svg_pixmap(name, size=size, color=color, dpr=2.0))


def ensure_qss_arrow_assets() -> dict[str, str]:
    """Gera pequenos ícones SVG em disco para setas minimalistas de SpinBox e ComboBox."""
    asset_dir = get_app_data_dir() / "ui_assets"
    asset_dir.mkdir(parents=True, exist_ok=True)
    svgs = {
        "chevron_up": (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 12 12">'
            '<path d="M2.5 7.5L6 4L9.5 7.5" fill="none" stroke="#D9B99B" stroke-width="1.6" '
            'stroke-linecap="round" stroke-linejoin="round"/></svg>'
        ),
        "chevron_down": (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 12 12">'
            '<path d="M2.5 4.5L6 8L9.5 4.5" fill="none" stroke="#D9B99B" stroke-width="1.6" '
            'stroke-linecap="round" stroke-linejoin="round"/></svg>'
        ),
    }
    paths: dict[str, str] = {}
    for key, content in svgs.items():
        p = asset_dir / f"{key}.svg"
        if not p.exists() or p.read_text(encoding="utf-8") != content:
            p.write_text(content, encoding="utf-8")
        paths[key] = p.resolve().as_posix()
    return paths
