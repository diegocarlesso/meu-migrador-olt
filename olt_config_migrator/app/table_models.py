from __future__ import annotations
from typing import Any, Dict, List
from PyQt6.QtCore import Qt, QAbstractTableModel, QModelIndex, pyqtSignal
from .models import SectionSchema


class SectionTableModel(QAbstractTableModel):
    dataChangedSignal = pyqtSignal()

    def __init__(self, schema: SectionSchema, rows: List[Dict[str, Any]] | None = None):
        super().__init__()
        self.schema = schema
        self.rows: List[Dict[str, Any]] = rows or []

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self.rows)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self.schema.columns)

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole):
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        if orientation == Qt.Orientation.Horizontal:
            return self.schema.columns[section].label
        return str(section + 1)

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        col = self.schema.columns[index.column()]
        flags = Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled
        if col.editable:
            flags |= Qt.ItemFlag.ItemIsEditable
        return flags

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        row = self.rows[index.row()]
        col = self.schema.columns[index.column()]
        val = row.get(col.key, "")
        if role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole):
            return "" if val is None else str(val)
        return None

    def setData(self, index: QModelIndex, value: Any, role: int = Qt.ItemDataRole.EditRole) -> bool:
        if role != Qt.ItemDataRole.EditRole or not index.isValid():
            return False
        col = self.schema.columns[index.column()]
        if not col.editable:
            return False
        row = self.rows[index.row()]
        new_val = value
        if col.col_type == "int":
            try:
                new_val = int(str(value).strip())
            except Exception:
                new_val = 0
        else:
            new_val = str(value)
        row[col.key] = new_val
        self.dataChanged.emit(index, index, [Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole])
        self.dataChangedSignal.emit()
        return True

    def add_row(self):
        self.beginInsertRows(QModelIndex(), len(self.rows), len(self.rows))
        row = {c.key: (0 if c.col_type == "int" else "") for c in self.schema.columns}
        self.rows.append(row)
        self.endInsertRows()
        self.dataChangedSignal.emit()

    def remove_rows(self, indexes: List[int]):
        for r in sorted(set(indexes), reverse=True):
            if 0 <= r < len(self.rows):
                self.beginRemoveRows(QModelIndex(), r, r)
                self.rows.pop(r)
                self.endRemoveRows()
        self.dataChangedSignal.emit()

    def to_rows(self) -> List[Dict[str, Any]]:
        return self.rows
