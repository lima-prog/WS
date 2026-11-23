# -*- coding: utf-8 -*-
"""
Aba "Visualizador DXF": navegador de pasta + organizador de arquivos.
Antigo app avulso "DXFViewer" (QMainWindow), convertido pra QWidget de aba.
Usa pyqtgraph pra desenho (diferente do QGraphicsScene nativo usado nas
abas de Corte e Espelhar) -- mantido assim de proposito, e' o motor de
renderizacao ja validado dessa ferramenta.
"""
import os
import re
import shutil
import platform
import subprocess
import ezdxf
import numpy as np
import pyqtgraph as pg
from PyQt5 import QtWidgets, QtCore, QtGui

from visualizador.estilo import STYLE, make_btn_style, COR_TELA, COR_BORDA, COR_DESTAQUE
from visualizador.navegador_pastas import FolderNavigatorDialog
from visualizador.atalhos import ShortcutConfigDialog


def _sem_borda_nos_rotulos(frame):
    """QLabel é um QFrame: sem isso, os rótulos herdam a borda/padding do quadro onde estão (viravam "caixinhas")."""
    frame.setStyleSheet(frame.styleSheet() + "\nQLabel { border: none; padding: 0; margin: 0; background: transparent; }")


class AbaVisualizador(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        # Mantém o mesmo identificador de QSettings do app avulso original
        # (SuaEmpresa/DXFViewer) de propósito: se o Diego já vinha usando essa
        # ferramenta separadamente, as preferências salvas (última pasta,
        # atalhos customizados, auto-fit) continuam valendo aqui, sem resetar.
        self.settings        = QtCore.QSettings("SuaEmpresa", "DXFViewer")
        self.folder_path     = self.settings.value("last_folder", "", type=str)
        self.root_path       = self.folder_path          # raiz carregada pelo usuário
        self.current_file_folders = []
        self.shortcuts       = self.settings.value("shortcuts", {
            "next_file": "Right", "prev_file": "Left",
            "reset_zoom": "0",    "fit_view": "A",
            "load_folder": "Tab", "discard_files": "D"
        }, type=dict)
        self.auto_fit_enabled = self.settings.value("auto_fit", True, type=bool)
        self.dxf_files        = []
        self.current_index    = 0
        self.base_scale       = 10
        self.current_zoom     = 100
        self.drawing_units    = 1.0
        self.unit             = 'mm'
        self.create_folder_buttons = {}
        self.move_file_buttons     = {}

        self.setStyleSheet(STYLE)   # padrão Projeart (visualizador/estilo.py)

        self.main_layout = QtWidgets.QVBoxLayout(self)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout.setSpacing(8)

        self.setup_header_area()

        self.content_layout = QtWidgets.QHBoxLayout()
        self.content_layout.setSpacing(10)
        self.main_layout.addLayout(self.content_layout)

        self.setup_folder_creation_panel()
        self.setup_visualization_area()
        self.setup_move_file_panel()
        self.setup_info_panel()
        self.setup_controls()
        self.setup_status_bar()
        self.setup_connections()
        self.show_empty_state()

    # ── CABEÇALHO ─────────────────────────────────────────────────────────────

    def setup_header_area(self):
        header_frame = QtWidgets.QFrame()
        header_frame.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border: 1px solid #CCCCCC;
                border-radius:4px;
            }
        """)
        _sem_borda_nos_rotulos(header_frame)
        header_frame.setMaximumHeight(52)
        hl = QtWidgets.QHBoxLayout(header_frame)
        hl.setContentsMargins(12, 6, 12, 6)
        hl.setSpacing(10)

        self.file_name_label = QtWidgets.QLabel("Nenhum arquivo carregado")
        self.file_name_label.setStyleSheet(
            "font-weight: bold; font-size: 13px; color: #1D1D1B; background: transparent;")
        self.file_name_label.setAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft)

        sep = QtWidgets.QFrame()
        sep.setFrameShape(QtWidgets.QFrame.VLine)
        sep.setStyleSheet("color: #CCCCCC; background: #CCCCCC;")
        sep.setMaximumWidth(1)

        loc_icon = QtWidgets.QLabel("📂")
        loc_icon.setStyleSheet("background: transparent; font-size: 12px;")

        self.current_folders_label = QtWidgets.QLabel("—")
        self.current_folders_label.setStyleSheet(
            "font-size: 11px; color: #4D4C4C; background: transparent; font-style: italic;")
        self.current_folders_label.setAlignment(QtCore.Qt.AlignVCenter)

        # Dica do atalho de navegação
        nav_hint = QtWidgets.QLabel("  ESPAÇO → Navegar pastas")
        nav_hint.setStyleSheet(
            "font-size: 10px; color: #8A8A8A; background: transparent; font-style: italic;")

        hl.addWidget(self.file_name_label, 5)
        hl.addWidget(sep)
        hl.addWidget(loc_icon)
        hl.addWidget(self.current_folders_label, 4)
        hl.addStretch()
        hl.addWidget(nav_hint)

        self.main_layout.addWidget(header_frame)

    # ── ÁREA DE VISUALIZAÇÃO + HUD ────────────────────────────────────────────

    def setup_visualization_area(self):
        visualization_frame = QtWidgets.QFrame()
        visualization_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COR_TELA};
                border: 1px solid {COR_BORDA};
                border-radius:4px;
            }}
        """)
        vl = QtWidgets.QVBoxLayout(visualization_frame)
        vl.setContentsMargins(2, 2, 2, 2)
        vl.setSpacing(0)

        view_container = QtWidgets.QWidget()
        view_container.setStyleSheet("background: transparent;")
        stack = QtWidgets.QGridLayout(view_container)
        stack.setContentsMargins(0, 0, 0, 0)

        self.graphics_view = pg.GraphicsView()
        self.plot_item     = pg.PlotItem()
        self.plot_item.getViewBox().setBackgroundColor(COR_TELA)
        self.plot_item.setAspectLocked(True)
        self.plot_item.hideAxis('left')
        self.plot_item.hideAxis('bottom')
        self.graphics_view.setCentralItem(self.plot_item)
        self.plot_item.setMenuEnabled(False)
        self.plot_item.vb.setMenuEnabled(False)

        stack.addWidget(self.graphics_view, 0, 0)

        # ── HUD overlay de dimensões ──
        self.hud_frame = QtWidgets.QFrame(view_container)
        self.hud_frame.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 255, 255, 235);
                border: 1px solid #CCCCCC;
                border-radius:4px;
            }
        """)
        _sem_borda_nos_rotulos(self.hud_frame)
        self.hud_frame.setFixedWidth(200)
        hud_l = QtWidgets.QVBoxLayout(self.hud_frame)
        hud_l.setContentsMargins(8, 6, 8, 6)
        hud_l.setSpacing(2)

        hud_title = QtWidgets.QLabel("📐 Dimensões")
        hud_title.setStyleSheet("""
            font-size: 10px; font-weight: bold; color: #0B3D91;
            background: transparent; border-bottom: 1px solid #CCCCCC; padding-bottom: 3px;
        """)
        self.hud_dims = QtWidgets.QLabel("—")
        self.hud_dims.setStyleSheet(
            "font-size: 11px; font-weight: bold; color: #1D1D1B; background: transparent;")
        self.hud_dims.setWordWrap(True)

        hud_l.addWidget(hud_title)
        hud_l.addWidget(self.hud_dims)
        self.hud_frame.raise_()
        self._hud_margin = 10

        vl.addWidget(view_container)
        self.content_layout.addWidget(visualization_frame, stretch=6)
        self._view_container = view_container

        self.setup_context_menu()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._reposition_hud()

    def showEvent(self, event):
        super().showEvent(event)
        QtCore.QTimer.singleShot(50, self._reposition_hud)

    def _reposition_hud(self):
        if not hasattr(self, '_view_container') or not hasattr(self, 'hud_frame'):
            return
        self.hud_frame.move(self._hud_margin, self._hud_margin)
        self.hud_frame.adjustSize()

    # ── CONTEXT MENU ─────────────────────────────────────────────────────────

    def setup_context_menu(self):
        self.graphics_view.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.graphics_view.customContextMenuRequested.connect(self.show_context_menu)

    def show_context_menu(self, position):
        menu = QtWidgets.QMenu(self)
        menu.addAction("🔍 Ajustar na Tela").triggered.connect(self.fit_to_view)
        menu.addAction("🔄 Resetar Zoom").triggered.connect(self.reset_zoom)
        menu.addSeparator()
        menu.addAction("◀ Arquivo Anterior").triggered.connect(self.previous_file)
        menu.addAction("▶ Próximo Arquivo").triggered.connect(self.next_file)
        menu.addSeparator()
        menu.addAction("📂 Navegar Pastas  [Espaço]").triggered.connect(self.open_folder_navigator)
        menu.addSeparator()
        menu.addAction("⚙️ Configurar Atalhos").triggered.connect(self.configure_shortcuts)
        aa = menu.addAction("📐 Auto-Ajuste")
        aa.setCheckable(True)
        aa.setChecked(self.auto_fit_enabled)
        aa.triggered.connect(self.toggle_auto_fit)
        menu.exec_(self.graphics_view.mapToGlobal(position))

    # ── NAVEGADOR DE PASTAS ───────────────────────────────────────────────────

    def open_folder_navigator(self):
        """Abre a telinha de navegação centralizada no visualizador."""
        if not self.root_path or not os.path.isdir(self.root_path):
            QtWidgets.QMessageBox.warning(
                self, "Aviso", "Nenhuma pasta carregada!\nUse 'Carregar Pasta' primeiro.")
            return

        current = self.folder_path if self.folder_path else self.root_path

        dlg = FolderNavigatorDialog(self.root_path, current, parent=self)
        dlg.folder_selected.connect(self._load_folder_from_navigator)

        # Centraliza no visualizador (graphics_view)
        gv_rect  = self.graphics_view.rect()
        gv_global = self.graphics_view.mapToGlobal(gv_rect.topLeft())
        x = gv_global.x() + (gv_rect.width()  - dlg.width())  // 2
        y = gv_global.y() + (gv_rect.height() - dlg.height()) // 2
        dlg.move(x, y)

        dlg.exec_()

    def _load_folder_from_navigator(self, path):
        """Carrega os DXFs da pasta selecionada no navegador."""
        self.folder_path = path
        self.settings.setValue("last_folder", path)
        self.dxf_files   = self._get_dxf_files()
        self.current_index = 0
        if self.dxf_files:
            self.load_current_file()
            self._show_status(
                f"Carregados {len(self.dxf_files)} arquivos de: {os.path.basename(path)}", 3000)
        else:
            self.show_empty_state()
        self.btn_open_current_folder.setEnabled(True)
        self.btn_refresh_folders.setEnabled(True)
        self.update_move_buttons_state()

    # ── PAINÉIS LATERAIS ─────────────────────────────────────────────────────

    def _make_scroll_panel(self, title_text, min_w=155, max_w=190):
        container = QtWidgets.QScrollArea()
        container.setWidgetResizable(True)
        container.setStyleSheet("QScrollArea { background-color: transparent; border: none; }")
        frame = QtWidgets.QFrame()
        frame.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border: 1px solid #CCCCCC;
                border-radius:4px;
            }
        """)
        _sem_borda_nos_rotulos(frame)
        layout = QtWidgets.QVBoxLayout(frame)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(2)

        title = QtWidgets.QLabel(title_text)
        title.setStyleSheet("""
            QLabel {
                font-weight: bold; font-size: 11px; color: #0B3D91;
                padding: 6px; background-color: #E6E6E6;
                border-radius: 3px; border: 1px solid #CCCCCC;
            }
        """)
        title.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(title)

        container.setWidget(frame)
        container.setMinimumWidth(min_w)
        container.setMaximumWidth(max_w)
        return container, layout

    def setup_folder_creation_panel(self):
        container, layout = self._make_scroll_panel("📁 CRIAR PASTAS")

        folder_buttons = [(t, COR_BORDA, COR_DESTAQUE) for t in (
            "Fluxo 1", "Fluxo 2", "Fluxo 3", "Fluxo 4", "Acessórios Padrão",
            "Perfiladeira U E C", "Perfiladeira L", "Joist", "Terça Z")]
        for text, border, hover in folder_buttons:
            btn = QtWidgets.QPushButton(text)
            btn.setStyleSheet(make_btn_style(border=border, hover=hover, fs=10))
            btn.clicked.connect(lambda checked, t=text: self.create_folder(t))
            self.create_folder_buttons[text] = btn
            layout.addWidget(btn)

        self.btn_open_current_folder = QtWidgets.QPushButton("Abrir Pasta Atual")
        self.btn_open_current_folder.setStyleSheet(make_btn_style(fs=10))
        self.btn_open_current_folder.clicked.connect(self.open_current_folder)
        self.btn_open_current_folder.setEnabled(False)
        layout.addWidget(self.btn_open_current_folder)
        layout.addStretch()
        self.content_layout.addWidget(container)

    def setup_move_file_panel(self):
        container, layout = self._make_scroll_panel("🚚 MOVER ARQUIVO")

        info = QtWidgets.QLabel("Mover arquivo atual para:")
        info.setStyleSheet(
            "font-size: 10px; color: #4D4C4C; font-style: italic; padding: 3px; background: transparent;")
        info.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(info)

        for folder_type in ["Fluxo 1","Fluxo 2","Fluxo 3","Fluxo 4",
                             "Acessórios Padrão","Perfiladeira U E C","Perfiladeira L",
                             "Joist","Terça Z"]:
            btn = QtWidgets.QPushButton(folder_type)
            btn.setStyleSheet(make_btn_style(fs=10))
            btn.clicked.connect(lambda checked, t=folder_type: self.move_current_file(t))
            self.move_file_buttons[folder_type] = btn
            btn.setEnabled(False)
            layout.addWidget(btn)

        self.btn_refresh_folders = QtWidgets.QPushButton("🔄 Atualizar Pastas")
        self.btn_refresh_folders.setStyleSheet(make_btn_style(fs=10))
        self.btn_refresh_folders.clicked.connect(self.update_move_buttons_state)
        self.btn_refresh_folders.setEnabled(False)
        layout.addWidget(self.btn_refresh_folders)
        layout.addStretch()
        self.content_layout.addWidget(container)

    def setup_info_panel(self):
        info_frame = QtWidgets.QFrame()
        info_frame.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border: 1px solid #CCCCCC;
                border-radius:4px;
            }
        """)
        il = QtWidgets.QVBoxLayout(info_frame)
        il.setContentsMargins(5, 5, 5, 5)

        self.info_panel  = QtWidgets.QFrame()
        self.info_panel.setStyleSheet("QFrame { background: transparent; border: none; }")
        self.info_layout = QtWidgets.QVBoxLayout(self.info_panel)

        self.info_scroll = QtWidgets.QScrollArea()
        self.info_scroll.setWidgetResizable(True)
        self.info_scroll.setWidget(self.info_panel)
        self.info_scroll.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")

        il.addWidget(self.info_scroll)
        self.content_layout.addWidget(info_frame)
        info_frame.setMinimumWidth(250)
        info_frame.setMaximumWidth(320)

    # ── CONTROLES ─────────────────────────────────────────────────────────────

    def setup_controls(self):
        control_frame = QtWidgets.QFrame()
        control_frame.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border: 1px solid #CCCCCC;
                border-radius:4px;
                padding: 6px;
            }
        """)
        _sem_borda_nos_rotulos(control_frame)
        cl = QtWidgets.QHBoxLayout(control_frame)
        cl.setSpacing(10)

        self.btn_load    = QtWidgets.QPushButton("📁 Carregar Pasta")
        self.btn_load.setStyleSheet(make_btn_style(fs=13, primario=True))
        self.btn_discard = QtWidgets.QPushButton("🗑️ Descartar")
        self.btn_discard.setStyleSheet(make_btn_style(fs=13))
        self.btn_discard.setEnabled(False)

        zoom_container = QtWidgets.QFrame()
        zoom_container.setStyleSheet("""
            QFrame {
                background-color: #E6E6E6;
                border: 1px solid #CCCCCC;
                border-radius: 4px;
                padding: 5px;
            }
        """)
        _sem_borda_nos_rotulos(zoom_container)
        zl = QtWidgets.QHBoxLayout(zoom_container)
        zl.setSpacing(8)
        zl.addWidget(self._lbl("🔍 Zoom:", bold=True, color="#0B3D91"))
        self.zoom_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.zoom_slider.setRange(10, 500)
        self.zoom_slider.setValue(100)
        self.zoom_slider.setEnabled(False)
        self.zoom_slider.setMinimumWidth(130)
        self.zoom_label = QtWidgets.QLabel("100%")
        self.zoom_label.setStyleSheet(
            "font-weight: bold; font-size: 12px; color: #0B3D91; background: transparent;")
        self.zoom_label.setFixedWidth(48)
        self.zoom_label.setAlignment(QtCore.Qt.AlignCenter)
        zl.addWidget(self.zoom_slider)
        zl.addWidget(self.zoom_label)

        self.btn_reset = QtWidgets.QPushButton("🔄 Reset Zoom (0)")
        self.btn_reset.setStyleSheet(make_btn_style(fs=12))
        self.btn_reset.setEnabled(False)

        nav_container = QtWidgets.QFrame()
        nav_container.setStyleSheet("""
            QFrame {
                background-color: #E6E6E6;
                border: 1px solid #CCCCCC;
                border-radius: 4px;
                padding: 3px;
            }
        """)
        _sem_borda_nos_rotulos(nav_container)
        nl = QtWidgets.QHBoxLayout(nav_container)
        nl.setSpacing(5)
        self.btn_prev = QtWidgets.QPushButton("◀ Anterior")
        self.btn_prev.setStyleSheet(make_btn_style(fs=12))
        self.btn_prev.setEnabled(False)
        self.btn_next = QtWidgets.QPushButton("Próximo ▶")
        self.btn_next.setStyleSheet(make_btn_style(fs=12, primario=True))
        self.btn_next.setEnabled(False)
        nl.addWidget(self.btn_prev)
        nl.addWidget(self.btn_next)

        cl.addWidget(self.btn_load)
        cl.addWidget(self.btn_discard)
        cl.addWidget(zoom_container, stretch=2)
        cl.addWidget(self.btn_reset)
        cl.addWidget(nav_container)

        self.main_layout.addWidget(control_frame)

    def _lbl(self, text, bold=False, color="#000000", fs=12):
        l = QtWidgets.QLabel(text)
        l.setStyleSheet(
            f"font-weight: {'bold' if bold else 'normal'}; font-size: {fs}px; color: {color}; background: transparent;")
        return l

    def setup_status_bar(self):
        """QWidget não tem QStatusBar (isso é privilégio de QMainWindow), então
        essa aba usa um QLabel no rodapé com o mesmo visual, e _show_status()
        abaixo imita o comportamento do showMessage(msg, timeout_ms) nativo."""
        self.status_label = QtWidgets.QLabel("")
        self.status_label.setStyleSheet("""
            QLabel {
                background-color: #E6E6E6;
                color: #4D4C4C;
                border-top: 1px solid #CCCCCC;
                padding: 4px 8px;
                font-size: 11px;
            }
        """)
        self.main_layout.addWidget(self.status_label)

    def _show_status(self, msg, timeout=0):
        self.status_label.setText(msg)
        if timeout:
            QtCore.QTimer.singleShot(timeout, lambda: self._clear_status_if_unchanged(msg))

    def _clear_status_if_unchanged(self, msg):
        # só limpa se nenhuma mensagem mais nova sobrescreveu essa nesse meio tempo
        if self.status_label.text() == msg:
            self.status_label.setText("")

    def setup_connections(self):
        self.btn_load.clicked.connect(self.load_folder)
        self.btn_discard.clicked.connect(self.discard_files)
        self.btn_prev.clicked.connect(self.previous_file)
        self.btn_next.clicked.connect(self.next_file)
        self.btn_reset.clicked.connect(self.reset_zoom)
        self.zoom_slider.valueChanged.connect(self.update_zoom)
        self.setup_shortcuts()

    def setup_shortcuts(self):
        self.shortcut_objects = []
        shortcuts_map = {
            self.shortcuts.get("next_file",    "Right"): self.next_file,
            self.shortcuts.get("prev_file",    "Left"):  self.previous_file,
            self.shortcuts.get("reset_zoom",   "0"):     self.reset_zoom,
            self.shortcuts.get("fit_view",     "A"):     self.fit_to_view,
            self.shortcuts.get("load_folder",  "Tab"):   self.load_folder,
            self.shortcuts.get("discard_files","D"):     self.discard_files,
        }
        for ks, cb in shortcuts_map.items():
            if ks:
                try:
                    sc = QtWidgets.QShortcut(QtGui.QKeySequence(ks), self)
                    sc.activated.connect(cb)
                    self.shortcut_objects.append(sc)
                except Exception as e:
                    print(f"Erro ao criar atalho {ks}: {e}")

        # Atalho ESPAÇO para o navegador de pastas
        sc_nav = QtWidgets.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key_Space), self)
        sc_nav.activated.connect(self.open_folder_navigator)
        self.shortcut_objects.append(sc_nav)

        # Atalhos só devem disparar quando ESSA aba estiver ativa — senão
        # ficariam roubando teclas das outras abas (seta, Espaço, D, Tab
        # tem tudo cara de atalho comum). A JanelaPrincipal chama
        # set_atalhos_ativos(True/False) no currentChanged do QTabWidget;
        # aqui começam desligados pois essa aba não abre em primeiro plano.
        self.set_atalhos_ativos(False)

    def set_atalhos_ativos(self, ativo):
        """Liga/desliga todos os atalhos de teclado dessa aba de uma vez.
        Chamado pela JanelaPrincipal quando o usuário troca de aba."""
        for sc in self.shortcut_objects:
            sc.setEnabled(ativo)

    # ── ESTADO VAZIO ──────────────────────────────────────────────────────────

    def show_empty_state(self):
        self.plot_item.clear()
        text = pg.TextItem(
            "Nenhum arquivo carregado\n\nClique em 'Carregar Pasta' ou pressione TAB\nPressione ESPAÇO para navegar pastas",
            color='#8C8CC8', anchor=(0.5, 0.5))
        text.setPos(0, 0)
        self.plot_item.addItem(text)
        self.clear_info_panel()
        self.file_name_label.setText("Nenhum arquivo carregado")
        self.file_name_label.setStyleSheet(
            "font-size: 13px; color: #8A8A8A; font-style: italic; background: transparent;")
        self.current_file_folders = []
        self.update_current_folders_display()
        self.update_hud(None)
        self.btn_open_current_folder.setEnabled(False)
        self.btn_refresh_folders.setEnabled(False)
        for btn in self.move_file_buttons.values():
            btn.setEnabled(False)
        self._show_status(
            "Pronto — TAB para carregar pasta  |  ESPAÇO para navegar")
        self.update_buttons_state()

    def clear_info_panel(self):
        while self.info_layout.count():
            child = self.info_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        t = QtWidgets.QLabel("ESPECIFICAÇÕES")
        t.setStyleSheet(
            "font-style: italic; color: #8A8A8A; font-size: 12px; padding: 10px; background: transparent;")
        t.setAlignment(QtCore.Qt.AlignCenter)
        self.info_layout.addWidget(t)
        self.info_layout.addStretch()

    def update_buttons_state(self):
        has = len(self.dxf_files) > 0
        self.btn_discard.setEnabled(has)
        self.btn_prev.setEnabled(has and self.current_index > 0)
        self.btn_next.setEnabled(has and self.current_index < len(self.dxf_files) - 1)
        self.zoom_slider.setEnabled(has)
        self.btn_reset.setEnabled(has)
        self.btn_open_current_folder.setEnabled(bool(self.folder_path))
        self.btn_refresh_folders.setEnabled(bool(self.folder_path))

    # ── HUD ───────────────────────────────────────────────────────────────────

    def update_hud(self, info):
        if not info:
            self.hud_dims.setText("—")
            return
        self.hud_dims.setText(
            f"L: {info['width']:.2f} {info['units']}\n"
            f"A: {info['height']:.2f} {info['units']}"
        )
        self.hud_frame.adjustSize()

    # ── PASTAS / NAVEGAÇÃO ────────────────────────────────────────────────────

    def update_current_folders_display(self):
        if not self.current_file_folders or not any(self.current_file_folders):
            self.current_folders_label.setText("—")
            return
        f1, f2 = self.current_file_folders
        if f1 and f2:
            self.current_folders_label.setText(f"{f1}  /  {f2}")
        elif f1:
            self.current_folders_label.setText(f1)
        else:
            self.current_folders_label.setText("Pasta raiz")

    def extract_folder_structure(self, file_path):
        try:
            dir_path = os.path.dirname(file_path)
            parts, current = [], dir_path
            while current and current != os.path.dirname(current):
                part = os.path.basename(current)
                if part:
                    parts.append(part)
                current = os.path.dirname(current)
            if len(parts) >= 2:
                return parts[1], parts[0]
            elif parts:
                return parts[0], ""
            return "", ""
        except Exception as e:
            print(f"Erro ao extrair estrutura de pastas: {e}")
            return "", ""

    def is_fluxo_folder(self, folder_path):
        if not folder_path:
            return False
        name = os.path.basename(folder_path)
        return any(k in name for k in ["Fluxo","Acessórios Padrão","Perfiladeira","Joist","Terça Z"])

    def extract_thickness_from_folder_name(self, folder_name):
        try:
            patterns = [r'(\d+[\.,]\d+)', r'(\d+)\s*mm',
                        r'esp[.:]?\s*(\d+[\.,]?\d*)', r'thick[.:]?\s*(\d+[\.,]?\d*)']
            for p in patterns:
                m = re.search(p, folder_name, re.IGNORECASE)
                if m:
                    return m.group(1).replace(',', '.')
            m = re.search(r'(\d+[\.,]?\d*)', folder_name)
            return m.group(1).replace(',', '.') if m else ""
        except Exception as e:
            print(f"Erro ao extrair espessura: {e}")
            return ""

    def create_folder(self, folder_type):
        if not self.folder_path:
            QtWidgets.QMessageBox.warning(self, "Aviso", "Nenhuma pasta carregada!")
            return
        try:
            if self.is_fluxo_folder(self.folder_path):
                base_path = os.path.dirname(self.folder_path)
                thickness = self.extract_thickness_from_folder_name(os.path.basename(base_path))
            else:
                base_path = self.folder_path
                thickness = self.extract_thickness_from_folder_name(os.path.basename(self.folder_path))

            existing = [i for i in os.listdir(base_path)
                        if os.path.isdir(os.path.join(base_path, i)) and i.startswith(folder_type)]

            if existing:
                r = QtWidgets.QMessageBox.question(
                    self, 'Pastas Existentes',
                    f'Já existem pastas do tipo "{folder_type}":\n\n' + "\n".join(existing) +
                    "\n\nDeseja criar uma nova mesmo assim?",
                    QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.No)
                if r == QtWidgets.QMessageBox.No:
                    return

            new_name = f"{folder_type} [{thickness}]" if thickness else folder_type
            new_path = os.path.join(base_path, new_name)

            if os.path.exists(new_path):
                self._show_status(f"Pasta '{new_name}' já existe.", 3000)
                return

            os.makedirs(new_path, exist_ok=True)
            self._show_status(f"✔ Pasta '{new_name}' criada com sucesso!", 3000)
            self.update_move_buttons_state()

        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Erro", f"Erro ao criar pasta:\n{str(e)}")

    def update_move_buttons_state(self):
        if not self.folder_path or not os.path.exists(self.folder_path):
            return
        try:
            base = os.path.dirname(self.folder_path) if self.is_fluxo_folder(self.folder_path) else self.folder_path
            existing = [i for i in os.listdir(base) if os.path.isdir(os.path.join(base, i))]
            for ft, btn in self.move_file_buttons.items():
                match = [f for f in existing if f.startswith(ft)]
                btn.setEnabled(bool(match))
                btn.setToolTip(f"Mover para: {match[0]}" if match else f"Pasta '{ft}' não encontrada")
            n = sum(1 for b in self.move_file_buttons.values() if b.isEnabled())
            self._show_status(f"{n} pastas disponíveis para mover arquivos", 2000)
        except Exception as e:
            print(f"Erro ao atualizar botões de mover: {e}")

    def move_current_file(self, target_folder_type):
        if not self.dxf_files or self.current_index >= len(self.dxf_files):
            QtWidgets.QMessageBox.warning(self, "Aviso", "Nenhum arquivo para mover!")
            return
        try:
            filename    = self.dxf_files[self.current_index]
            source_path = os.path.join(self.folder_path, filename)
            if not os.path.exists(source_path):
                QtWidgets.QMessageBox.warning(self, "Erro", f"Arquivo não encontrado: {filename}")
                return
            base = os.path.dirname(self.folder_path) if self.is_fluxo_folder(self.folder_path) else self.folder_path
            target_name = next((i for i in os.listdir(base)
                                if os.path.isdir(os.path.join(base, i)) and i.startswith(target_folder_type)), None)
            if not target_name:
                QtWidgets.QMessageBox.warning(self, "Erro", f"Pasta '{target_folder_type}' não encontrada!")
                return
            target_dir  = os.path.join(base, target_name)
            target_path = os.path.join(target_dir, filename)
            if os.path.exists(target_path):
                r = QtWidgets.QMessageBox.question(
                    self, 'Arquivo Existente',
                    f'"{filename}" já existe em "{target_name}". Substituir?',
                    QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.No)
                if r == QtWidgets.QMessageBox.No:
                    return
            r = QtWidgets.QMessageBox.question(
                self, 'Confirmar Movimento',
                f'Mover "{filename}" para "{target_name}"?',
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.No)
            if r == QtWidgets.QMessageBox.Yes:
                shutil.move(source_path, target_path)
                self.dxf_files = self._get_dxf_files()
                if self.current_index >= len(self.dxf_files):
                    self.current_index = max(0, len(self.dxf_files) - 1)
                self._show_status(f"✔ '{filename}' movido para '{target_name}'", 3000)
                if self.dxf_files:
                    self.load_current_file()
                else:
                    self.show_empty_state()
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Erro", f"Erro ao mover arquivo:\n{str(e)}")

    def open_current_folder(self):
        if self.folder_path and os.path.exists(self.folder_path):
            self.open_folder_in_explorer(self.folder_path)
        else:
            QtWidgets.QMessageBox.warning(self, "Aviso", "Nenhuma pasta válida para abrir!")

    def open_folder_in_explorer(self, folder_path):
        try:
            if platform.system() == "Windows":
                os.startfile(folder_path)
            elif platform.system() == "Darwin":
                subprocess.run(["open", folder_path])
            else:
                subprocess.run(["xdg-open", folder_path])
        except Exception as e:
            print(f"Erro ao abrir pasta: {e}")

    # ── CONFIGURAÇÕES ─────────────────────────────────────────────────────────

    def toggle_auto_fit(self):
        self.auto_fit_enabled = not self.auto_fit_enabled
        self.settings.setValue("auto_fit", self.auto_fit_enabled)
        if self.auto_fit_enabled and self.dxf_files:
            self.fit_to_view()

    def configure_shortcuts(self):
        dialog = ShortcutConfigDialog(self)
        friendly = {
            "next_file": "Próximo arquivo", "prev_file": "Arquivo anterior",
            "reset_zoom": "Resetar zoom",   "fit_view": "Ajustar na tela",
            "load_folder": "Carregar pasta","discard_files": "Descartar arquivos"
        }
        dialog.load_shortcuts({friendly[k]: v for k, v in self.shortcuts.items() if k in friendly})
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            new = dialog.get_shortcuts()
            rev = {v: k for k, v in friendly.items()}
            self.shortcuts = {rev[fn]: sc for fn, sc in new.items() if fn in rev}
            self.settings.setValue("shortcuts", self.shortcuts)
            self.setup_shortcuts()

    # ── CARGA E NAVEGAÇÃO ─────────────────────────────────────────────────────

    def load_folder(self):
        path = QtWidgets.QFileDialog.getExistingDirectory(
            self, "Selecione a pasta com arquivos DXF", self.folder_path)
        if path:
            self.folder_path = path
            self.root_path   = path          # define a raiz para o navegador
            self.settings.setValue("last_folder", path)
            self.dxf_files   = self._get_dxf_files()
            self.current_index = 0
            if self.dxf_files:
                self.load_current_file()
            else:
                self.show_empty_state()
                QtWidgets.QMessageBox.warning(self, "Pasta vazia",
                    "A pasta não contém arquivos DXF válidos.")
            self.btn_open_current_folder.setEnabled(True)
            self.btn_refresh_folders.setEnabled(True)
            self.update_move_buttons_state()

    def discard_files(self):
        r = QtWidgets.QMessageBox.question(
            self, 'Confirmar', 'Descartar os arquivos carregados?',
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.No)
        if r == QtWidgets.QMessageBox.Yes:
            self.dxf_files     = []
            self.current_index = 0
            self.show_empty_state()

    def navigate(self, step):
        ni = self.current_index + step
        if 0 <= ni < len(self.dxf_files):
            self.current_index = ni
            self.load_current_file()

    def previous_file(self): self.navigate(-1)
    def next_file(self):     self.navigate(1)

    def _get_dxf_files(self):
        if not os.path.isdir(self.folder_path):
            return []
        return sorted([f for f in os.listdir(self.folder_path)
                       if f.lower().endswith('.dxf') and
                       os.path.isfile(os.path.join(self.folder_path, f))])

    # ── DXF: LEITURA E ANÁLISE ────────────────────────────────────────────────

    def _get_dxf_units(self, doc):
        try:
            u = doc.header.get('$INSUNITS', 1)
            return {1:1.0,4:1.0,5:1.0,2:1.0,3:1.0,6:1.0,7:1.0,8:25.4,9:304.8,10:1.0,11:1.0}.get(u, 1.0)
        except:
            return 1.0

    def _safe_convert(self, value, default=0.0):
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    def _calculate_normalization(self, doc):
        try:
            msp = doc.modelspace()
            all_coords = []
            for entity in msp:
                if entity.dxftype() == 'LINE':
                    all_coords += [
                        [self._safe_convert(entity.dxf.start[0]), self._safe_convert(entity.dxf.start[1])],
                        [self._safe_convert(entity.dxf.end[0]),   self._safe_convert(entity.dxf.end[1])]]
                elif entity.dxftype() in ('CIRCLE','ARC'):
                    cx = self._safe_convert(entity.dxf.center[0])
                    cy = self._safe_convert(entity.dxf.center[1])
                    r  = self._safe_convert(getattr(entity.dxf, 'radius', 0))
                    all_coords += [[cx,cy],[cx+r,cy]]
                elif entity.dxftype() == 'LWPOLYLINE':
                    for p in entity.get_points('xy'):
                        all_coords.append([self._safe_convert(p[0]), self._safe_convert(p[1])])
            if not all_coords:
                return 1.0, (0,0)
            arr   = np.array(all_coords)
            mx    = np.max(np.abs(arr))
            scale = 0.9 * self.base_scale / mx if mx > 0 else 1.0
            return scale, np.mean(arr, axis=0)
        except Exception as e:
            print(f"Erro normalização: {e}")
            return 1.0, (0,0)

    def _bulge_to_arc(self, p1, p2, bulge):
        if abs(bulge) < 1e-9: return None
        theta = 4 * np.arctan(bulge)
        chord = np.hypot(p2[0]-p1[0], p2[1]-p1[1])
        if chord < 1e-9 or abs(np.sin(theta/2)) < 1e-9: return None
        r  = abs(chord / (2*np.sin(theta/2)))
        mx, my = (p1[0]+p2[0])/2, (p1[1]+p2[1])/2
        d  = r * np.cos(theta/2)
        dx, dy = p2[0]-p1[0], p2[1]-p1[1]
        nx, ny = -dy/chord, dx/chord
        s  = 1.0 if bulge > 0 else -1.0
        cx, cy = mx+s*d*nx, my+s*d*ny
        sa = np.degrees(np.arctan2(p1[1]-cy, p1[0]-cx)) % 360
        ea = np.degrees(np.arctan2(p2[1]-cy, p2[0]-cx)) % 360
        if bulge < 0: sa, ea = ea, sa
        return {'center':(cx,cy),'radius':r,'start_angle':sa,'end_angle':ea,'used':False}

    def _bulge_arc_points(self, p1, p2, bulge, segments=24):
        if abs(bulge) < 1e-9: return [p1, p2]
        theta = 4 * np.arctan(bulge)
        chord = np.hypot(p2[0]-p1[0], p2[1]-p1[1])
        if chord < 1e-9 or abs(np.sin(theta/2)) < 1e-9: return [p1, p2]
        r  = abs(chord / (2*np.sin(theta/2)))
        mx, my = (p1[0]+p2[0])/2, (p1[1]+p2[1])/2
        d  = r * np.cos(theta/2)
        dx, dy = p2[0]-p1[0], p2[1]-p1[1]
        nx, ny = -dy/chord, dx/chord
        s  = 1.0 if bulge > 0 else -1.0
        cx, cy = mx+s*d*nx, my+s*d*ny
        sa = np.arctan2(p1[1]-cy, p1[0]-cx)
        n  = max(2, int(segments*min(abs(theta)/(2*np.pi),1.0))+2)
        angles = np.linspace(sa, sa+theta, n)
        return [(cx+r*np.cos(a), cy+r*np.sin(a)) for a in angles]

    def _collect_arcs_and_lines(self, msp):
        arcs, lines = [], []
        for entity in msp:
            et = entity.dxftype()
            try:
                if et == 'ARC':
                    arcs.append({
                        'center': (self._safe_convert(entity.dxf.center[0]),
                                   self._safe_convert(entity.dxf.center[1])),
                        'radius': self._safe_convert(entity.dxf.radius),
                        'start_angle': self._safe_convert(entity.dxf.start_angle) % 360,
                        'end_angle':   self._safe_convert(entity.dxf.end_angle)   % 360,
                        'used': False})
                elif et == 'LINE':
                    lines.append({'start':(self._safe_convert(entity.dxf.start[0]),
                                           self._safe_convert(entity.dxf.start[1])),
                                  'end':  (self._safe_convert(entity.dxf.end[0]),
                                           self._safe_convert(entity.dxf.end[1]))})
                elif et == 'LWPOLYLINE':
                    pts = [(self._safe_convert(p[0]),self._safe_convert(p[1]),self._safe_convert(p[2]))
                           for p in entity.get_points('xyb')]
                    n = len(pts)
                    for i in range(n if entity.closed else n-1):
                        x1,y1,b = pts[i]; x2,y2,_ = pts[(i+1)%n]
                        if abs(b)>1e-9:
                            a = self._bulge_to_arc((x1,y1),(x2,y2),b)
                            if a: arcs.append(a)
                        else:
                            lines.append({'start':(x1,y1),'end':(x2,y2)})
                elif et == 'POLYLINE':
                    verts = list(entity.vertices)
                    pts = [(self._safe_convert(v.dxf.location[0]),
                            self._safe_convert(v.dxf.location[1]),
                            self._safe_convert(getattr(v.dxf,'bulge',0.0))) for v in verts]
                    n = len(pts)
                    closed = getattr(entity,'is_closed',False)
                    for i in range(n if closed else n-1):
                        x1,y1,b = pts[i]; x2,y2,_ = pts[(i+1)%n]
                        if abs(b)>1e-9:
                            a = self._bulge_to_arc((x1,y1),(x2,y2),b)
                            if a: arcs.append(a)
                        else:
                            lines.append({'start':(x1,y1),'end':(x2,y2)})
            except Exception as e:
                print(f"Erro ao coletar {et}: {e}")
        return arcs, lines

    def _arc_span(self, arc):
        return (arc['end_angle'] - arc['start_angle']) % 360

    def _arc_endpoints(self, arc):
        cx,cy = arc['center']; r = arc['radius']
        return (
            (cx+r*np.cos(np.radians(arc['start_angle'])), cy+r*np.sin(np.radians(arc['start_angle']))),
            (cx+r*np.cos(np.radians(arc['end_angle'])),   cy+r*np.sin(np.radians(arc['end_angle'])))
        )

    def _points_close(self, p1, p2, tol):
        return np.hypot(p1[0]-p2[0], p1[1]-p2[1]) <= tol

    def _detect_oblong_holes(self, msp):
        arcs, lines = self._collect_arcs_and_lines(msp)
        oblongs = []
        u   = self.drawing_units or 1.0
        tol = 1.0 / u if u else 1.0
        n   = len(arcs)
        for i in range(n):
            if arcs[i]['used']: continue
            si = self._arc_span(arcs[i])
            if not (150 <= si <= 210): continue
            for j in range(i+1, n):
                if arcs[j]['used']: continue
                if not (150 <= self._arc_span(arcs[j]) <= 210): continue
                if abs(arcs[i]['radius']-arcs[j]['radius']) > tol: continue
                cxi,cyi = arcs[i]['center']; cxj,cyj = arcs[j]['center']
                if not (abs(cxi-cxj)<=tol or abs(cyi-cyj)<=tol): continue
                p1a,p1b = self._arc_endpoints(arcs[i])
                p2a,p2b = self._arc_endpoints(arcs[j])
                conn = 0
                for line in lines:
                    ls,le = line['start'],line['end']
                    for pi in [p1a,p1b]:
                        for pj in [p2a,p2b]:
                            if (self._points_close(ls,pi,tol) and self._points_close(le,pj,tol)) or \
                               (self._points_close(ls,pj,tol) and self._points_close(le,pi,tol)):
                                conn += 1; break
                        else: continue
                        break
                if conn >= 2:
                    arcs[i]['used'] = arcs[j]['used'] = True
                    r = arcs[i]['radius']
                    dist = np.hypot(cxi-cxj, cyi-cyj)
                    oblongs.append({'width':2*r*u,'length':(dist+2*r)*u,
                                    'center':((cxi+cxj)/2,(cyi+cyj)/2)})
                    break
        return oblongs

    def _analyze_piece(self, doc):
        info = {'width':0,'height':0,'holes':[],'oblong_holes':[],
                'rounded_corners':[],'depressions':[],'units':'mm'}
        try:
            msp = doc.modelspace()
            all_pts = []
            for entity in msp:
                et = entity.dxftype()
                if et == 'LINE':
                    all_pts += [
                        (self._safe_convert(entity.dxf.start[0]), self._safe_convert(entity.dxf.start[1])),
                        (self._safe_convert(entity.dxf.end[0]),   self._safe_convert(entity.dxf.end[1]))]
                elif et == 'CIRCLE':
                    cx = self._safe_convert(entity.dxf.center[0])
                    cy = self._safe_convert(entity.dxf.center[1])
                    r  = self._safe_convert(entity.dxf.radius)
                    info['holes'].append({'position':(cx,cy),'diameter':2*r*self.drawing_units})
                elif et == 'ARC':
                    cx = self._safe_convert(entity.dxf.center[0])
                    cy = self._safe_convert(entity.dxf.center[1])
                    r  = self._safe_convert(entity.dxf.radius)
                    sa = np.radians(self._safe_convert(entity.dxf.start_angle))
                    ea = np.radians(self._safe_convert(entity.dxf.end_angle))
                    info['rounded_corners'].append({
                        'radius': r*self.drawing_units,
                        'start_point': (cx+r*np.cos(sa), cy+r*np.sin(sa)),
                        'end_point':   (cx+r*np.cos(ea), cy+r*np.sin(ea))})
                elif et == 'LWPOLYLINE':
                    pts = [[self._safe_convert(p[0]), self._safe_convert(p[1])]
                           for p in entity.get_points('xy')]
                    all_pts.extend(pts)
                    if entity.closed and len(pts) >= 3:
                        area = self._calculate_polygon_area(pts)
                        if area < (info['width']*info['height']*0.1):
                            info['depressions'].append({'area':area*(self.drawing_units**2)})
            if all_pts:
                arr = np.array(all_pts)
                mn, mx = np.min(arr,axis=0), np.max(arr,axis=0)
                info['width']  = (mx[0]-mn[0])*self.drawing_units
                info['height'] = (mx[1]-mn[1])*self.drawing_units
            info['oblong_holes'] = self._detect_oblong_holes(msp)
        except Exception as e:
            print(f"Erro na análise da peça: {e}")
        return info

    def _calculate_polygon_area(self, points):
        x = [p[0] for p in points]; y = [p[1] for p in points]
        return 0.5 * np.abs(np.dot(x, np.roll(y,1)) - np.dot(y, np.roll(x,1)))

    def display_piece_info(self, info):
        while self.info_layout.count():
            child = self.info_layout.takeAt(0)
            if child.widget(): child.widget().deleteLater()
        if not info: return

        title = QtWidgets.QLabel("ESPECIFICAÇÕES")
        title.setStyleSheet("""
            font-weight: bold; font-size: 11pt; color: #0B3D91;
            margin-bottom: 10px; padding: 8px 4px;
            background-color: #E6E6E6; border-radius: 3px; border: 1px solid #CCCCCC;
        """)
        title.setAlignment(QtCore.Qt.AlignCenter)
        self.info_layout.addWidget(title)

        def make_card(border, tc, bg, icon_title):
            card = QtWidgets.QFrame()
            card.setStyleSheet(f"""
                QFrame {{
                    background-color: #FFFFFF;
                    border: 1px solid {border};
                    border-radius:4px;
                    padding: 8px;
                    margin: 3px 0;
                }}
            """)
            _sem_borda_nos_rotulos(card)
            lay = QtWidgets.QVBoxLayout(card)
            ct  = QtWidgets.QLabel(icon_title)
            ct.setStyleSheet(f"font-weight: bold; color: {tc}; background: transparent; font-size: 11px;")
            lay.addWidget(ct)
            return card, lay, bg

        self.update_hud(info)

        if info['holes']:
            card, lay, bg = make_card("#1a7a92","#0E5E73","#E3F3F7",f"⭕ Furos Circulares ({len(info['holes'])})")
            for i,h in enumerate(info['holes'],1):
                it = QtWidgets.QLabel(f"Furo {i}: ⌀{h['diameter']:.2f}{info['units']}")
                it.setStyleSheet(f"color:#1D1D1B;font-size:12px;padding:3px 5px;background-color:{bg};border-radius:3px;margin:1px 0;")
                it.setWordWrap(True); lay.addWidget(it)
            self.info_layout.addWidget(card)

        if info['oblong_holes']:
            card, lay, bg = make_card("#A67C2E","#7A5A12","#FBF3E0",f"⬭ Furos Oblongos ({len(info['oblong_holes'])})")
            for i,o in enumerate(info['oblong_holes'],1):
                it = QtWidgets.QLabel(f"Oblongo {i}: {o['width']:.2f} x {o['length']:.2f} {info['units']}")
                it.setStyleSheet(f"color:#1D1D1B;font-size:12px;padding:3px 5px;background-color:{bg};border-radius:3px;margin:1px 0;")
                it.setWordWrap(True); lay.addWidget(it)
            self.info_layout.addWidget(card)

        if info['depressions']:
            card, lay, bg = make_card("#8A2E6A","#8A2E6A","#F9E9F3",f"▬ Rebaixos/Rasgos ({len(info['depressions'])})")
            for i,d in enumerate(info['depressions'],1):
                it = QtWidgets.QLabel(f"Área {i}: {d['area']:.2f} {info['units']}²")
                it.setStyleSheet(f"color:#1D1D1B;font-size:12px;padding:3px 5px;background-color:{bg};border-radius:3px;margin:1px 0;")
                it.setWordWrap(True); lay.addWidget(it)
            self.info_layout.addWidget(card)

        self.info_layout.addStretch()

    # ── RENDERIZAÇÃO DXF ──────────────────────────────────────────────────────

    def load_current_file(self):
        self.plot_item.clear()
        filename  = self.dxf_files[self.current_index]
        file_path = os.path.join(self.folder_path, filename)
        try:
            f1, f2 = self.extract_folder_structure(file_path)
            self.current_file_folders = [f1, f2]
            self.update_current_folders_display()

            doc = ezdxf.readfile(file_path)
            self.drawing_units = self._get_dxf_units(doc)
            piece_info = self._analyze_piece(doc)
            self.display_piece_info(piece_info)

            self.file_name_label.setText(f"  {filename}")
            self.file_name_label.setStyleSheet(
                "font-weight: bold; font-size: 13px; color: #1D1D1B; background: transparent;")

            self.scale, self.center = self._calculate_normalization(doc)
            msp = doc.modelspace()

            line_pen   = pg.mkPen(color=(180,110,110), width=2)
            circle_pen = pg.mkPen(color=(100,160,210), width=2)
            poly_pen   = pg.mkPen(color=(100,200,150), width=2)
            arc_pen    = pg.mkPen(color=(210,180, 90), width=2)

            for entity in msp:
                try:
                    et = entity.dxftype()
                    if et == 'LINE':
                        sx = self._safe_convert(entity.dxf.start[0]) * self.scale
                        sy = self._safe_convert(entity.dxf.start[1]) * self.scale
                        ex = self._safe_convert(entity.dxf.end[0])   * self.scale
                        ey = self._safe_convert(entity.dxf.end[1])   * self.scale
                        self.plot_item.addItem(pg.PlotCurveItem(x=[sx,ex],y=[sy,ey],pen=line_pen))

                    elif et == 'CIRCLE':
                        cx = self._safe_convert(entity.dxf.center[0]) * self.scale
                        cy = self._safe_convert(entity.dxf.center[1]) * self.scale
                        r  = self._safe_convert(entity.dxf.radius)    * self.scale
                        c  = QtWidgets.QGraphicsEllipseItem(cx-r,cy-r,r*2,r*2)
                        c.setPen(circle_pen); self.plot_item.addItem(c)

                    elif et == 'ARC':
                        cx  = self._safe_convert(entity.dxf.center[0]) * self.scale
                        cy  = self._safe_convert(entity.dxf.center[1]) * self.scale
                        r   = self._safe_convert(entity.dxf.radius)    * self.scale
                        sa  = self._safe_convert(entity.dxf.start_angle) % 360
                        ea  = self._safe_convert(entity.dxf.end_angle)   % 360
                        if ea < sa: ea += 360
                        ang = np.linspace(np.radians(sa), np.radians(ea), 30)
                        self.plot_item.addItem(pg.PlotCurveItem(
                            x=cx+r*np.cos(ang), y=cy+r*np.sin(ang), pen=arc_pen))

                    elif et == 'LWPOLYLINE':
                        raw = [(self._safe_convert(p[0]),self._safe_convert(p[1]),self._safe_convert(p[2]))
                               for p in entity.get_points('xyb')]
                        n = len(raw)
                        if n >= 2:
                            full = [(raw[0][0],raw[0][1])]
                            for i in range(n if entity.closed else n-1):
                                x1,y1,b = raw[i]; x2,y2,_ = raw[(i+1)%n]
                                if abs(b)>1e-9:
                                    full.extend(self._bulge_arc_points((x1,y1),(x2,y2),b,24)[1:])
                                else:
                                    full.append((x2,y2))
                            pts = np.array(full) * self.scale
                            self.plot_item.addItem(pg.PlotCurveItem(x=pts[:,0],y=pts[:,1],pen=poly_pen))

                    elif et == 'POLYLINE':
                        verts = list(entity.vertices)
                        raw = [(self._safe_convert(v.dxf.location[0]),
                                self._safe_convert(v.dxf.location[1]),
                                self._safe_convert(getattr(v.dxf,'bulge',0.0))) for v in verts]
                        n = len(raw)
                        if n >= 2:
                            closed = getattr(entity,'is_closed',False)
                            full = [(raw[0][0],raw[0][1])]
                            for i in range(n if closed else n-1):
                                x1,y1,b = raw[i]; x2,y2,_ = raw[(i+1)%n]
                                if abs(b)>1e-9:
                                    full.extend(self._bulge_arc_points((x1,y1),(x2,y2),b,24)[1:])
                                else:
                                    full.append((x2,y2))
                            pts = np.array(full) * self.scale
                            self.plot_item.addItem(pg.PlotCurveItem(x=pts[:,0],y=pts[:,1],pen=poly_pen))

                except Exception as e:
                    print(f"Erro ao renderizar {entity.dxftype()}: {e}")

            self.apply_view()
            if self.auto_fit_enabled:
                QtCore.QTimer.singleShot(100, self.fit_to_view)
            QtCore.QTimer.singleShot(150, self._reposition_hud)

            self.update_status()
            self.update_buttons_state()
            self.update_move_buttons_state()

        except Exception as e:
            self.show_error(f"Erro ao processar arquivo:\n{filename}\n\n{str(e)}")

    # ── ZOOM / VIEW ───────────────────────────────────────────────────────────

    def apply_view(self):
        if hasattr(self,'scale') and hasattr(self,'center'):
            vs = self.base_scale / (self.current_zoom/100)
            cx = self.center[0] * self.scale
            cy = self.center[1] * self.scale
            self.plot_item.setXRange(cx-vs, cx+vs)
            self.plot_item.setYRange(cy-vs, cy+vs)

    def update_zoom(self, value):
        self.current_zoom = value
        self.zoom_label.setText(f"{value}%")
        self.apply_view()
        self.update_status()

    def update_status(self):
        if self.dxf_files:
            fn = self.dxf_files[self.current_index]
            self._show_status(
                f"Arquivo {self.current_index+1}/{len(self.dxf_files)}: {fn}  |  "
                f"Zoom: {self.current_zoom:.1f}%  |  ← → navegar  |  0 reset  |  ESPAÇO navegar pastas")

    def reset_zoom(self):
        self.zoom_slider.setValue(100)
        self.current_zoom = 100
        self.zoom_label.setText("100%")
        self.apply_view()

    def _plot_items(self):
        """Compatibilidade entre versões do pyqtgraph: em versões mais antigas
        PlotItem.items é um MÉTODO; a partir da 0.14 virou uma lista/atributo.
        Essa função funciona nos dois casos."""
        items = self.plot_item.items
        return items() if callable(items) else items

    def fit_to_view(self):
        if not self.dxf_files: return
        try:
            items = [i for i in self._plot_items()
                     if hasattr(i,'boundingRect') and not isinstance(i, pg.TextItem)]
            if not items: return
            mn_x = mn_y =  float('inf')
            mx_x = mx_y = -float('inf')
            for item in items:
                r = item.boundingRect()
                mn_x = min(mn_x, r.left());  mn_y = min(mn_y, r.top())
                mx_x = max(mx_x, r.right()); mx_y = max(mx_y, r.bottom())
            if mn_x == float('inf'): return
            w = max(mx_x-mn_x,1); h = max(mx_y-mn_y,1)
            # setXRange()+setYRange() em chamadas SEPARADAS não funciona direito
            # com setAspectLocked(True): a segunda chamada recalcula e encolhe
            # o que a primeira acabou de definir (mais visível quanto mais
            # alongada for a peça). setRange() com os dois eixos numa única
            # chamada deixa o pyqtgraph resolver o aspect lock de uma vez só.
            self.plot_item.setRange(
                xRange=(mn_x-w*0.1, mx_x+w*0.1),
                yRange=(mn_y-h*0.1, mx_y+h*0.1),
            )
        except Exception as e:
            print(f"Erro ao ajustar na tela: {e}")

    def show_error(self, message):
        self.plot_item.clear()
        self.plot_item.addItem(pg.TextItem(text=message, color='#FF8A80'))
        self._show_status("Erro ao carregar arquivo")
