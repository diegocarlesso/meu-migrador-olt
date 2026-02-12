from __future__ import annotations
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QApplication

METRO_BG = "#0b0c10"
METRO_PANEL = "#11131a"
METRO_TEXT = "#e8e8ea"
METRO_MUTED = "#a7a7b2"
METRO_BLUE = "#1183c6"
METRO_PINK = "#d81b60"
METRO_BORDER = "#232635"

def apply_metro_theme(app: QApplication) -> None:
    app.setFont(QFont("Segoe UI", 10))
    app.setStyleSheet(f"""
        QWidget {{
            background: {METRO_BG};
            color: {METRO_TEXT};
        }}
        QGroupBox {{
            border: 1px solid {METRO_BORDER};
            border-radius: 10px;
            margin-top: 12px;
            padding: 10px;
            background: {METRO_PANEL};
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            subcontrol-position: top left;
            padding: 0 8px;
            color: {METRO_MUTED};
        }}
        QLineEdit, QComboBox, QSpinBox, QTextEdit, QPlainTextEdit {{
            background: #0f1118;
            border: 1px solid {METRO_BORDER};
            border-radius: 8px;
            padding: 6px 8px;
            selection-background-color: {METRO_BLUE};
        }}
        QTableView {{
            background: #0f1118;
            gridline-color: {METRO_BORDER};
            border: 1px solid {METRO_BORDER};
            border-radius: 10px;
        }}
        QHeaderView::section {{
            background: {METRO_PANEL};
            border: 0px;
            padding: 6px 8px;
            color: {METRO_MUTED};
        }}
        QPushButton {{
            background: {METRO_PANEL};
            border: 1px solid {METRO_BORDER};
            border-radius: 10px;
            padding: 8px 12px;
            font-weight: 600;
        }}
        QPushButton:hover {{
            border-color: {METRO_BLUE};
        }}
        QPushButton:pressed {{
            background: #0f1118;
        }}
        QPushButton#Primary {{
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {METRO_PINK}, stop:1 {METRO_BLUE});
            border: 0px;
            color: white;
        }}
        QPushButton#Danger {{
            border-color: {METRO_PINK};
            color: {METRO_PINK};
        }}
        QLabel#Title {{
            font-size: 20px;
            font-weight: 800;
        }}
        QLabel#Subtitle {{
            color: {METRO_MUTED};
        }}
    """)
