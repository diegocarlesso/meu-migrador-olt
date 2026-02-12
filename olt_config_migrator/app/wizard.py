from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from PyQt6.QtWidgets import (
    QWizard, QWizardPage, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QLineEdit,
    QPushButton, QFileDialog, QGroupBox, QFormLayout, QCheckBox, QTabWidget,
    QPlainTextEdit, QMessageBox
)
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt

from .utils import read_text_smart
from .vendors.registry import get_registry
from .models import NormalizedConfig, SectionSchema
from .widgets import SectionEditor


@dataclass
class AppState:
    src_vendor: str = ""
    src_path: str = ""
    src_text: str = ""
    normalized: NormalizedConfig = field(default_factory=NormalizedConfig)

    dst_vendor: str = ""
    options: Dict[str, bool] = field(default_factory=lambda: {
        "vlans": True,
        "ips_routes": True,
        "profiles": True,
    })

    target_data: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)


class MigrationWizard(QWizard):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("OLT Config Migrator")
        self.setWizardStyle(QWizard.WizardStyle.ModernStyle)
        self.setMinimumSize(980, 680)

        self.registry = get_registry()
        self.state = AppState()

        self.page1 = SourcePage(self)
        self.page2 = TargetPage(self)
        self.page3 = EditPage(self)
        self.page4 = PreviewPage(self)

        self.addPage(self.page1)
        self.addPage(self.page2)
        self.addPage(self.page3)
        self.addPage(self.page4)

        self.button(QWizard.WizardButton.FinishButton).setText("Fechar")
        self.button(QWizard.WizardButton.NextButton).setText("Avançar →")
        self.button(QWizard.WizardButton.BackButton).setText("← Voltar")


class Header(QWidget):
    def __init__(self, title: str, subtitle: str):
        super().__init__()
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)

        logo = QLabel()
        try:
            px = QPixmap("resources/metro_network.png")
            if not px.isNull():
                logo.setPixmap(px.scaledToHeight(70, Qt.TransformationMode.SmoothTransformation))
        except Exception:
            pass
        lay.addWidget(logo)

        txt = QVBoxLayout()
        t = QLabel(title)
        t.setObjectName("Title")
        s = QLabel(subtitle)
        s.setObjectName("Subtitle")
        s.setWordWrap(True)
        txt.addWidget(t)
        txt.addWidget(s)
        lay.addLayout(txt)
        lay.addStretch(1)


class SourcePage(QWizardPage):
    def __init__(self, wiz: MigrationWizard):
        super().__init__(wiz)
        self.wiz = wiz
        self.setTitle("Origem")

        root = QVBoxLayout(self)
        root.addWidget(Header("Metro Network", "Migração de configurações de OLT: escolha o fabricante de origem e carregue o backup."))

        box = QGroupBox("Fonte")
        form = QFormLayout(box)

        self.cmb_vendor = QComboBox()
        for vid, ad in self.wiz.registry.items():
            self.cmb_vendor.addItem(ad.label, vid)

        self.ed_path = QLineEdit()
        btn_browse = QPushButton("Procurar…")
        row = QWidget()
        row_l = QHBoxLayout(row)
        row_l.setContentsMargins(0, 0, 0, 0)
        row_l.addWidget(self.ed_path, 1)
        row_l.addWidget(btn_browse)

        self.lbl_summary = QLabel("Nenhum arquivo carregado.")
        self.lbl_summary.setStyleSheet("color: #a7a7b2;")
        self.lbl_summary.setWordWrap(True)

        form.addRow("Fabricante de origem:", self.cmb_vendor)
        form.addRow("Arquivo de backup:", row)
        form.addRow("Resumo:", self.lbl_summary)

        root.addWidget(box)
        root.addStretch(1)

        btn_browse.clicked.connect(self._browse)
        self.cmb_vendor.currentIndexChanged.connect(self._on_vendor_changed)

    def _on_vendor_changed(self):
        # se já tem arquivo, reparse
        if self.ed_path.text().strip():
            self._load_and_parse(self.ed_path.text().strip())

    def _browse(self):
        path, _ = QFileDialog.getOpenFileName(self, "Selecione o backup", "", "Config (*.txt *.cfg *.conf *.bak *.*)")
        if path:
            self.ed_path.setText(path)
            self._load_and_parse(path)

    def _load_and_parse(self, path: str):
        vid = self.cmb_vendor.currentData()
        adapter = self.wiz.registry[vid]
        try:
            text = read_text_smart(path)
            normalized = adapter.parse_to_normalized(text)
            self.wiz.state.src_vendor = vid
            self.wiz.state.src_path = path
            self.wiz.state.src_text = text
            self.wiz.state.normalized = normalized

            self.lbl_summary.setText(
                f"VLANs: {len(normalized.vlans)} | IPs: {len(normalized.interfaces)} | Rotas: {len(normalized.routes)} | "
                f"Profiles: DBA {len(normalized.dba_profiles)}, Line {len(normalized.line_profiles)}, ONU {len(normalized.onu_profiles)}, "
                f"Band {len(normalized.bandwidth_profiles)}, ServiceVLAN {len(normalized.service_vlans)}"
            )
            self.completeChanged.emit()
        except Exception as e:
            QMessageBox.critical(self, "Erro ao carregar", str(e))
            self.lbl_summary.setText("Erro ao parsear o arquivo.")

    def isComplete(self) -> bool:
        return bool(self.wiz.state.src_text and self.wiz.state.src_vendor)


class TargetPage(QWizardPage):
    def __init__(self, wiz: MigrationWizard):
        super().__init__(wiz)
        self.wiz = wiz
        self.setTitle("Destino")

        root = QVBoxLayout(self)
        root.addWidget(Header("Destino", "Escolha o fabricante de destino e marque o que deseja migrar/editar."))

        box = QGroupBox("Destino e opções")
        form = QFormLayout(box)

        self.cmb_vendor = QComboBox()
        for vid, ad in self.wiz.registry.items():
            self.cmb_vendor.addItem(ad.label, vid)

        self.chk_vlans = QCheckBox("Migrar VLANs")
        self.chk_ips = QCheckBox("Migrar IPs e Rotas")
        self.chk_prof = QCheckBox("Migrar Profiles (quando aplicável)")
        self.chk_vlans.setChecked(True)
        self.chk_ips.setChecked(True)
        self.chk_prof.setChecked(True)

        form.addRow("Fabricante de destino:", self.cmb_vendor)
        form.addRow("Opções:", self.chk_vlans)
        form.addRow("", self.chk_ips)
        form.addRow("", self.chk_prof)

        root.addWidget(box)
        root.addStretch(1)

    def validatePage(self) -> bool:
        self.wiz.state.dst_vendor = self.cmb_vendor.currentData()
        self.wiz.state.options = {
            "vlans": self.chk_vlans.isChecked(),
            "ips_routes": self.chk_ips.isChecked(),
            "profiles": self.chk_prof.isChecked(),
        }
        return True


class EditPage(QWizardPage):
    def __init__(self, wiz: MigrationWizard):
        super().__init__(wiz)
        self.wiz = wiz
        self.setTitle("Adicionar / Modificar")

        self.root = QVBoxLayout(self)
        self.root.addWidget(Header("Editor", "Edite apenas os campos editáveis (IDs, nomes e valores). Use o botão ADD para criar linhas."))

        self.tabs = QTabWidget()
        self.root.addWidget(self.tabs, 1)

        bar = QHBoxLayout()
        self.btn_rebuild = QPushButton("Recarregar do arquivo de origem")
        self.btn_rebuild.setObjectName("Primary")
        bar.addWidget(self.btn_rebuild)
        bar.addStretch(1)
        self.root.addLayout(bar)

        self.btn_rebuild.clicked.connect(self._rebuild_tabs)
        self._built = False

    def initializePage(self):
        self._rebuild_tabs()

    def _rebuild_tabs(self):
        dst = self.wiz.state.dst_vendor
        if not dst:
            return
        adapter = self.wiz.registry[dst]
        schema = adapter.schema()

        # Converte Normalized -> target_data
        target_data = adapter.from_normalized(self.wiz.state.normalized)

        # Aplica opções (remove seções não desejadas)
        opts = self.wiz.state.options
        if not opts.get("vlans", True) and "vlans" in target_data:
            target_data["vlans"] = []
        if not opts.get("ips_routes", True):
            if "interfaces" in target_data:
                target_data["interfaces"] = []
            if "routes" in target_data:
                target_data["routes"] = []
        if not opts.get("profiles", True):
            for k in list(target_data.keys()):
                if k in ("dba_profiles", "line_profiles", "onu_profiles", "bandwidth_profiles", "service_vlans"):
                    target_data[k] = []

        self.wiz.state.target_data = target_data

        # UI
        self.tabs.clear()
        self.editors: Dict[str, SectionEditor] = {}
        for sec in schema:
            rows = target_data.get(sec.key, [])
            ed = SectionEditor(sec, rows)
            self.editors[sec.key] = ed
            self.tabs.addTab(ed, sec.title)
            ed.model.dataChangedSignal.connect(self._sync_state)

        self._built = True
        self._sync_state()

    def _sync_state(self):
        if not getattr(self, "editors", None):
            return
        for k, ed in self.editors.items():
            self.wiz.state.target_data[k] = ed.rows()

    def validatePage(self) -> bool:
        self._sync_state()
        return True


class PreviewPage(QWizardPage):
    def __init__(self, wiz: MigrationWizard):
        super().__init__(wiz)
        self.wiz = wiz
        self.setTitle("Conferência e geração")

        root = QVBoxLayout(self)
        root.addWidget(Header("Prévia", "Confira o script final e gere o arquivo no formato do fabricante de destino."))

        self.txt = QPlainTextEdit()
        self.txt.setReadOnly(True)
        self.txt.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.txt.setStyleSheet("font-family: Consolas, 'Courier New', monospace; font-size: 10pt;")
        root.addWidget(self.txt, 1)

        bar = QHBoxLayout()
        self.btn_save = QPushButton("Gerar Script (Salvar)")
        self.btn_save.setObjectName("Primary")
        bar.addWidget(self.btn_save)
        bar.addStretch(1)
        root.addLayout(bar)

        self.btn_save.clicked.connect(self._save)

    def initializePage(self):
        self._refresh()

    def _refresh(self):
        dst = self.wiz.state.dst_vendor
        adapter = self.wiz.registry[dst]
        script = adapter.render(self.wiz.state.target_data)
        self.txt.setPlainText(script)

    def _save(self):
        self._refresh()
        dst = self.wiz.state.dst_vendor
        adapter = self.wiz.registry[dst]
        default_ext = adapter.default_extension
        path, _ = QFileDialog.getSaveFileName(self, "Salvar script", f"script{default_ext}", f"*{default_ext};;All (*.*)")
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self.txt.toPlainText())
            QMessageBox.information(self, "OK", "Script gerado com sucesso.")
        except Exception as e:
            QMessageBox.critical(self, "Erro", str(e))
