from __future__ import annotations
from typing import Any, Dict, List
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableView, QAbstractItemView
from .models import SectionSchema
from .table_models import SectionTableModel

class SectionEditor(QWidget):
    def __init__(self, schema: SectionSchema, rows: List[Dict[str, Any]]):
        super().__init__()
        self.schema = schema
        self.model = SectionTableModel(schema, rows)

        root = QVBoxLayout(self)
        if schema.description:
            desc = QLabel(schema.description)
            desc.setWordWrap(True)
            desc.setStyleSheet("color: #a7a7b2;")
            root.addWidget(desc)

        self.table = QTableView()
        self.table.setModel(self.model)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        root.addWidget(self.table)

        bar = QHBoxLayout()
        self.btn_add = QPushButton("＋ ADD")
        self.btn_add.setObjectName("Primary")
        self.btn_del = QPushButton("Remover selecionados")
        self.btn_del.setObjectName("Danger")
        bar.addWidget(self.btn_add)
        bar.addWidget(self.btn_del)
        bar.addStretch(1)
        root.addLayout(bar)

        self.btn_add.clicked.connect(self.model.add_row)
        self.btn_del.clicked.connect(self._remove_selected)

    def _remove_selected(self):
        sel = self.table.selectionModel().selectedRows()
        rows = [i.row() for i in sel]
        self.model.remove_rows(rows)

    def rows(self) -> List[Dict[str, Any]]:
        return self.model.to_rows()
