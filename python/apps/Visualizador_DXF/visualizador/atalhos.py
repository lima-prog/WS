# -*- coding: utf-8 -*-
"""
Dialogo de configuracao de atalhos de teclado da aba Visualizador.
"""
from PyQt5 import QtWidgets, QtCore, QtGui


class ShortcutConfigDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configurar Atalhos")
        self.setModal(True)
        self.resize(500, 400)
        layout = QtWidgets.QVBoxLayout(self)
        self.table = QtWidgets.QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["Ação", "Atalho"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        layout.addWidget(self.table)
        button_layout = QtWidgets.QHBoxLayout()
        self.btn_restore = QtWidgets.QPushButton("Restaurar Padrões")
        self.btn_save    = QtWidgets.QPushButton("Salvar")
        self.btn_cancel  = QtWidgets.QPushButton("Cancelar")
        button_layout.addWidget(self.btn_restore)
        button_layout.addStretch()
        button_layout.addWidget(self.btn_save)
        button_layout.addWidget(self.btn_cancel)
        layout.addLayout(button_layout)
        self.btn_restore.clicked.connect(self.restore_defaults)
        self.btn_save.clicked.connect(self.accept)
        self.btn_cancel.clicked.connect(self.reject)
        self.table.cellDoubleClicked.connect(self.on_cell_double_clicked)

    def load_shortcuts(self, shortcuts):
        self.table.setRowCount(len(shortcuts))
        for row, (action, shortcut) in enumerate(shortcuts.items()):
            self.table.setItem(row, 0, QtWidgets.QTableWidgetItem(action))
            si = QtWidgets.QTableWidgetItem(shortcut)
            si.setFlags(si.flags() | QtCore.Qt.ItemIsEditable)
            self.table.setItem(row, 1, si)
        self.table.resizeColumnsToContents()

    def get_shortcuts(self):
        shortcuts = {}
        for row in range(self.table.rowCount()):
            shortcuts[self.table.item(row, 0).text()] = self.table.item(row, 1).text()
        return shortcuts

    def restore_defaults(self):
        self.load_shortcuts({
            "Próximo arquivo": "Right", "Arquivo anterior": "Left",
            "Resetar zoom": "0",        "Ajustar na tela": "A",
            "Carregar pasta": "Ctrl+O", "Descartar arquivos": "Ctrl+D"
        })

    def on_cell_double_clicked(self, row, column):
        if column == 1:
            self.capture_shortcut(row)

    def capture_shortcut(self, row):
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("Pressione uma tecla...")
        dialog.setModal(True)
        dialog.resize(300, 100)
        layout = QtWidgets.QVBoxLayout(dialog)
        label = QtWidgets.QLabel("Pressione a tecla desejada...\n(Suporte a Ctrl, Alt, Shift)")
        label.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(label)

        def key_press_event(event):
            key = event.key()
            mod = event.modifiers()
            if key in (QtCore.Qt.Key_Control, QtCore.Qt.Key_Alt, QtCore.Qt.Key_Shift,
                       QtCore.Qt.Key_Meta, QtCore.Qt.Key_AltGr):
                return
            self.table.item(row, 1).setText(self.key_to_string(key, mod))
            dialog.accept()

        dialog.keyPressEvent = key_press_event
        dialog.exec_()

    def key_to_string(self, key, modifiers):
        mod = ""
        if modifiers & QtCore.Qt.ControlModifier: mod += "Ctrl+"
        if modifiers & QtCore.Qt.AltModifier:     mod += "Alt+"
        if modifiers & QtCore.Qt.ShiftModifier:   mod += "Shift+"
        if modifiers & QtCore.Qt.MetaModifier:    mod += "Meta+"
        special = {
            QtCore.Qt.Key_Left: "Left",   QtCore.Qt.Key_Right: "Right",
            QtCore.Qt.Key_Up: "Up",       QtCore.Qt.Key_Down: "Down",
            QtCore.Qt.Key_Space: "Space", QtCore.Qt.Key_Enter: "Enter",
            QtCore.Qt.Key_Return: "Return", QtCore.Qt.Key_Delete: "Delete",
            QtCore.Qt.Key_Home: "Home",   QtCore.Qt.Key_End: "End",
            QtCore.Qt.Key_PageUp: "PageUp", QtCore.Qt.Key_PageDown: "PageDown",
            QtCore.Qt.Key_Escape: "Escape", QtCore.Qt.Key_Tab: "Tab",
            QtCore.Qt.Key_Backspace: "Backspace", QtCore.Qt.Key_Insert: "Insert",
        }
        if key in special:
            return mod + special[key]
        kc = QtGui.QKeySequence(key).toString()
        return mod + (kc if kc else f"Key_{key}")
