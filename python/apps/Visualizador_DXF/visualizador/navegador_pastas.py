# -*- coding: utf-8 -*-
"""
Navegador contextual de pastas da aba Visualizador: exibe a arvore
completa a partir da raiz carregada, com a pasta atual destacada. Duplo
clique ou Enter carrega os DXFs da pasta selecionada.
"""
import os

from PyQt5 import QtWidgets, QtCore, QtGui

from visualizador.estilo import make_btn_style


class FolderNavigatorDialog(QtWidgets.QDialog):
    """
    Navegador contextual de pastas.
    Exibe a árvore completa a partir da raiz carregada, com a pasta atual
    destacada. Duplo clique ou Enter carrega os DXFs da pasta selecionada.
    """

    folder_selected = QtCore.pyqtSignal(str)   # emite o caminho escolhido

    def __init__(self, root_path, current_path, parent=None):
        super().__init__(parent)
        self.root_path    = root_path
        self.current_path = current_path

        self.setWindowTitle("Navegar Pastas")
        self.setModal(True)
        self.setWindowFlags(
            QtCore.Qt.Dialog |
            QtCore.Qt.FramelessWindowHint |
            QtCore.Qt.WindowStaysOnTopHint
        )
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.resize(480, 520)

        self._build_ui()
        self._populate_tree()
        self._expand_to_current()

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        outer = QtWidgets.QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        # Card com fundo semitransparente
        card = QtWidgets.QFrame()
        card.setStyleSheet("""
            QFrame#navCard {
                background-color: #FFFFFF;
                border: 2px solid #0B3D91;
                border-radius:4px;
            }
        """)
        card.setObjectName("navCard")
        outer.addWidget(card)

        layout = QtWidgets.QVBoxLayout(card)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)

        # ── Título ──
        title_row = QtWidgets.QHBoxLayout()
        icon_lbl = QtWidgets.QLabel("📂")
        icon_lbl.setStyleSheet("font-size: 16px; background: transparent;")
        title_lbl = QtWidgets.QLabel("Navegador de Pastas")
        title_lbl.setStyleSheet("""
            font-size: 13px;
            font-weight: bold;
            color: #0B3D91;
            background: transparent;
        """)
        hint_lbl = QtWidgets.QLabel("Enter / duplo clique para carregar  ·  Esc para fechar")
        hint_lbl.setStyleSheet("font-size: 10px; color: #4D4C4C; background: transparent;")
        hint_lbl.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        title_row.addWidget(icon_lbl)
        title_row.addWidget(title_lbl)
        title_row.addStretch()
        title_row.addWidget(hint_lbl)
        layout.addLayout(title_row)

        # Linha separadora
        sep = QtWidgets.QFrame()
        sep.setFrameShape(QtWidgets.QFrame.HLine)
        sep.setStyleSheet("background-color: #CCCCCC; border: none; max-height: 1px;")
        layout.addWidget(sep)

        # ── Árvore ──
        self.tree = QtWidgets.QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setIndentation(18)
        self.tree.setAnimated(True)
        self.tree.setStyleSheet("""
            QTreeWidget {
                background-color: #FFFFFF;
                color: #1D1D1B;
                border: 1px solid #CCCCCC;
                border-radius:4px;
                font-size: 12px;
                outline: none;
            }
            QTreeWidget::item {
                padding: 5px 4px;
                border-radius: 3px;
            }
            QTreeWidget::item:hover {
                background-color: #E6E6E6;
            }
            QTreeWidget::item:selected {
                background-color: #0B3D91;
                color: #ffffff;
            }
        """)
        layout.addWidget(self.tree)

        # ── Rodapé ──
        footer = QtWidgets.QHBoxLayout()
        self.path_lbl = QtWidgets.QLabel("")
        self.path_lbl.setStyleSheet("font-size: 10px; color: #4D4C4C; background: transparent;")
        self.path_lbl.setWordWrap(True)

        btn_close = QtWidgets.QPushButton("Fechar")
        btn_close.setStyleSheet(make_btn_style(fs=10))
        btn_close.setFixedWidth(80)
        btn_close.clicked.connect(self.reject)

        footer.addWidget(self.path_lbl, 1)
        footer.addWidget(btn_close)
        layout.addLayout(footer)

        # Conexões
        self.tree.itemDoubleClicked.connect(self._on_double_click)
        self.tree.itemSelectionChanged.connect(self._on_selection_changed)

    # ── POPULANDO A ÁRVORE ────────────────────────────────────────────────────

    def _has_dxf(self, path):
        """Verifica recursivamente se há algum DXF na pasta."""
        try:
            for f in os.listdir(path):
                fp = os.path.join(path, f)
                if os.path.isfile(fp) and f.lower().endswith('.dxf'):
                    return True
                if os.path.isdir(fp):
                    if self._has_dxf(fp):
                        return True
        except PermissionError:
            pass
        return False

    def _dxf_count(self, path):
        """Conta DXFs diretos na pasta (não recursivo)."""
        try:
            return sum(1 for f in os.listdir(path)
                       if os.path.isfile(os.path.join(path, f)) and f.lower().endswith('.dxf'))
        except Exception:
            return 0

    def _populate_tree(self):
        self.tree.clear()
        self._path_map = {}   # item → caminho absoluto

        root_name = os.path.basename(self.root_path) or self.root_path
        root_item = QtWidgets.QTreeWidgetItem(self.tree, [f"📁  {root_name}"])
        root_item.setData(0, QtCore.Qt.UserRole, self.root_path)
        root_item.setForeground(0, QtGui.QColor("#0B3D91"))
        root_item.setFont(0, self._font(bold=True))
        self._path_map[id(root_item)] = self.root_path

        self._add_children(root_item, self.root_path)
        self.tree.addTopLevelItem(root_item)

    def _add_children(self, parent_item, dir_path):
        try:
            entries = sorted(
                [e for e in os.listdir(dir_path)
                 if os.path.isdir(os.path.join(dir_path, e))],
                key=lambda x: x.lower()
            )
        except PermissionError:
            return

        for entry in entries:
            full_path  = os.path.join(dir_path, entry)
            is_current = os.path.normpath(full_path) == os.path.normpath(self.current_path)
            count      = self._dxf_count(full_path)

            # Label
            if count > 0:
                label = f"📂  {entry}  [{count} DXF]"
            else:
                label = f"📁  {entry}"

            item = QtWidgets.QTreeWidgetItem(parent_item, [label])
            item.setData(0, QtCore.Qt.UserRole, full_path)
            self._path_map[id(item)] = full_path

            if is_current:
                # Destaque visual da pasta atual
                item.setBackground(0, QtGui.QColor("#0B3D91"))
                item.setForeground(0, QtGui.QColor("#FFFFFF"))
                item.setFont(0, self._font(bold=True))
                # Adiciona marcador visual
                item.setText(0, f"▶  {entry}  ◀" + (f"  [{count} DXF]" if count else ""))
                self._current_item = item
            elif count > 0:
                item.setForeground(0, QtGui.QColor("#000000"))
                item.setFont(0, self._font(bold=False))
            else:
                item.setForeground(0, QtGui.QColor("#8A8A8A"))
                item.setFont(0, self._font(bold=False))

            # Recursão para subpastas
            self._add_children(item, full_path)

    def _font(self, bold=False):
        f = QtGui.QFont()
        f.setBold(bold)
        f.setPointSize(10)
        return f

    def _expand_to_current(self):
        """Expande a árvore até a pasta atual e rola até ela."""
        if not hasattr(self, '_current_item'):
            self.tree.expandAll()
            return

        # Expande todos os pais
        item = self._current_item
        while item:
            self.tree.expandItem(item)
            item = item.parent()

        self.tree.setCurrentItem(self._current_item)
        self.tree.scrollToItem(self._current_item, QtWidgets.QAbstractItemView.PositionAtCenter)

    # ── INTERAÇÃO ─────────────────────────────────────────────────────────────

    def _on_selection_changed(self):
        items = self.tree.selectedItems()
        if not items:
            self.path_lbl.setText("")
            return
        path = items[0].data(0, QtCore.Qt.UserRole)
        if path:
            # Mostra caminho relativo à raiz
            try:
                rel = os.path.relpath(path, os.path.dirname(self.root_path))
            except ValueError:
                rel = path
            self.path_lbl.setText(rel)

    def _on_double_click(self, item, column):
        self._load_selected(item)

    def _load_selected(self, item=None):
        if item is None:
            items = self.tree.selectedItems()
            if not items:
                return
            item = items[0]

        path = item.data(0, QtCore.Qt.UserRole)
        if not path or not os.path.isdir(path):
            return

        count = self._dxf_count(path)
        if count == 0:
            # Sem DXF direto nesta pasta: não interrompe a navegação.
            # O usuário pode continuar expandindo/selecionando subpastas
            # normalmente — a árvore já mostra tudo que existe abaixo.
            return

        self.folder_selected.emit(path)
        self.accept()

    # ── TECLADO ───────────────────────────────────────────────────────────────

    def keyPressEvent(self, event):
        if event.key() in (QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter):
            items = self.tree.selectedItems()
            if items:
                self._load_selected(items[0])
        elif event.key() == QtCore.Qt.Key_Escape:
            self.reject()
        else:
            super().keyPressEvent(event)

    # ── POSICIONAMENTO ────────────────────────────────────────────────────────

    def center_on_parent(self):
        if self.parent():
            pg_rect = self.parent().geometry()
            x = pg_rect.x() + (pg_rect.width()  - self.width())  // 2
            y = pg_rect.y() + (pg_rect.height() - self.height()) // 2
            self.move(x, y)


# ═══════════════════════════════════════════════════════════════════════════════
#  DIALOG DE CONFIGURAÇÃO DE ATALHOS
# ═══════════════════════════════════════════════════════════════════════════════

