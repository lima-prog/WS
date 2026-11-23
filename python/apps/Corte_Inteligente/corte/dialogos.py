# -*- coding: utf-8 -*-
"""
Widgets auxiliares da aba Corte: o paineizinho de medidas no rodape da
visualizacao, e os dois dialogos de consulta (Diagnostico de Cortes e
Arquivos Processados), que leem do banco de dados compartilhado.
"""
from PyQt5.QtWidgets import (QFrame, QHBoxLayout, QVBoxLayout, QLabel,
                             QDialog, QComboBox, QLineEdit, QPushButton,
                             QMessageBox, QTableWidget, QTableWidgetItem,
                             QHeaderView, QAbstractItemView)

from nucleo.estilo import ESTILO_GERAL, CORES_PARTES, COR_PAINEL, COR_BORDA, COR_TEXTO, COR_TEXTO_SUB


class PainelMedidas(QFrame):
    """Painel inferior que exibe as medidas de cada parte com cores."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(64)
        self.setStyleSheet(f"background:{COR_PAINEL}; border-top:1px solid {COR_BORDA};")
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(12, 6, 12, 6)
        self._layout.setSpacing(8)
        self._label_vazio = QLabel("Nenhum processamento ainda")
        self._label_vazio.setStyleSheet(f"color:{COR_TEXTO_SUB}; font-size:11px;")
        self._layout.addWidget(self._label_vazio)
        self._layout.addStretch()

    def _limpar_layout(self):
        """Remove todos os widgets do layout SEM deixar 'fantasmas' na tela.
        setParent(None) desliga o widget da árvore de exibição na hora;
        deleteLater() só libera a memória depois, quando o Qt tiver folga."""
        while self._layout.count():
            item = self._layout.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)
                w.deleteLater()

    def atualizar(self, partes):
        # trava o repaint do painel inteiro enquanto desmonta e remonta,
        # assim o usuário nunca vê um estado parcial (isso é o que causava o "pisca/corta")
        self.setUpdatesEnabled(False)
        try:
            self._limpar_layout()

            for i, (xa, xb) in enumerate(partes):
                letra = chr(65 + i)
                comp  = xb - xa
                cor   = CORES_PARTES[i % len(CORES_PARTES)]

                frame = QFrame()
                frame.setStyleSheet(
                    f"background: rgba({cor.red()},{cor.green()},{cor.blue()},40);"
                    f"border: 1px solid rgba({cor.red()},{cor.green()},{cor.blue()},180);"
                    f"border-radius:4px;"
                )
                fl = QVBoxLayout(frame)
                fl.setContentsMargins(10, 4, 10, 4)
                fl.setSpacing(1)

                lbl_letra = QLabel(f"[{letra}]")
                lbl_letra.setStyleSheet(
                    f"color: rgb({cor.red()},{cor.green()},{cor.blue()});"
                    f"font-weight:bold; font-size:13px; border:none; background:transparent;")
                lbl_comp = QLabel(f"{comp:.0f} mm")
                lbl_comp.setStyleSheet(
                    f"color:{COR_TEXTO}; font-size:11px; border:none; background:transparent;")

                fl.addWidget(lbl_letra)
                fl.addWidget(lbl_comp)
                self._layout.addWidget(frame)

                if i < len(partes) - 1:
                    sep = QLabel("→")
                    sep.setStyleSheet(f"color:{COR_TEXTO_SUB}; font-size:14px;")
                    self._layout.addWidget(sep)

            self._layout.addStretch()
        finally:
            self.setUpdatesEnabled(True)

    def limpar(self):
        self.setUpdatesEnabled(False)
        try:
            self._limpar_layout()
            lbl = QLabel("Nenhum processamento ainda")
            lbl.setStyleSheet(f"color:{COR_TEXTO_SUB}; font-size:11px;")
            self._layout.addWidget(lbl)
            self._layout.addStretch()
        finally:
            self.setUpdatesEnabled(True)


class DialogoDiagnostico(QDialog):
    """Tela de consulta dos eventos de corte (forçado, bloqueado, erro) gravados no banco."""

    TIPOS = {
        "Todos":              "Todos",
        "Corte forçado":      "corte_forcado",
        "Segmento bloqueado": "segmento_bloqueado",
        "Erro":               "erro",
    }

    def __init__(self, banco_dados, parent=None):
        super().__init__(parent)
        self.banco_dados = banco_dados
        self.setWindowTitle("📊 Diagnóstico de Cortes")
        self.resize(900, 520)
        self.setStyleSheet(ESTILO_GERAL)
        self._montar_ui()
        self._buscar()

    def _montar_ui(self):
        lay = QVBoxLayout(self)

        # filtros
        filtros = QHBoxLayout()

        self.cmb_tipo = QComboBox()
        self.cmb_tipo.addItems(self.TIPOS.keys())

        self.txt_arquivo = QLineEdit()
        self.txt_arquivo.setPlaceholderText("Filtrar por nome do arquivo…")

        self.txt_data = QLineEdit()
        self.txt_data.setPlaceholderText("Desde (AAAA-MM-DD)")

        btn_filtrar = QPushButton("🔍 Filtrar")
        btn_filtrar.setObjectName("btn_processar")
        btn_filtrar.clicked.connect(self._buscar)

        filtros.addWidget(QLabel("Tipo:"))
        filtros.addWidget(self.cmb_tipo)
        filtros.addWidget(self.txt_arquivo, 1)
        filtros.addWidget(self.txt_data)
        filtros.addWidget(btn_filtrar)
        lay.addLayout(filtros)

        # tabela
        self.tabela = QTableWidget(0, 6)
        self.tabela.setHorizontalHeaderLabels(
            ["Data/Hora", "Arquivo", "Tipo", "Detalhe", "Posição X", "Comprimento (mm)"])
        self.tabela.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tabela.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tabela.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.tabela.setStyleSheet(
            f"QTableWidget {{ background:{COR_PAINEL}; gridline-color:{COR_BORDA}; }}"
            f"QHeaderView::section {{ background:qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #E3E8EE, stop:1 #CDD4DE); color:#000000; font-weight:bold; padding:5px; border:none; border-right:1px solid #98A3B3; border-bottom:1px solid #98A3B3; }}")
        lay.addWidget(self.tabela, 1)

        self.lbl_total = QLabel()
        self.lbl_total.setStyleSheet(f"color:{COR_TEXTO_SUB}; font-size:10px;")
        lay.addWidget(self.lbl_total)

    def _buscar(self):
        tipo = self.TIPOS[self.cmb_tipo.currentText()]
        arquivo = self.txt_arquivo.text().strip() or None
        data_desde = self.txt_data.text().strip() or None

        try:
            linhas = self.banco_dados.buscar_eventos(tipo=tipo, nome_arquivo=arquivo, data_desde=data_desde)
        except Exception as e:
            QMessageBox.warning(self, "Erro na consulta", f"Não foi possível consultar o banco:\n{e}")
            return

        self.tabela.setRowCount(0)
        for row_idx, (data_hora, nome_arquivo, tipo_evento, detalhe, pos_x, comp_mm) in enumerate(linhas):
            self.tabela.insertRow(row_idx)
            valores = [
                data_hora,
                nome_arquivo,
                tipo_evento,
                detalhe,
                "" if pos_x is None else f"{pos_x:.0f}",
                "" if comp_mm is None else f"{comp_mm:.0f}",
            ]
            for col, valor in enumerate(valores):
                self.tabela.setItem(row_idx, col, QTableWidgetItem(str(valor)))

        self.lbl_total.setText(f"{len(linhas)} evento(s) encontrado(s)")


class DialogoArquivosProcessados(QDialog):
    """Tela com a lista de arquivos processados.

    Uma caixa de marcação (checkbox) alterna entre duas visões:
    - Partes editadas: cada pedaço gerado pela divisão (nome e comprimento).
    - Arquivos originais: cada peça antes da divisão, com a estratégia usada
      e quantas partes foram geradas a partir dela.
    """

    def __init__(self, banco_dados, parent=None):
        super().__init__(parent)
        self.banco_dados = banco_dados
        self.setWindowTitle("🗂 Arquivos Processados")
        self.resize(950, 520)
        self.setStyleSheet(ESTILO_GERAL)
        self._montar_ui()
        self._buscar()

    def _montar_ui(self):
        lay = QVBoxLayout(self)

        topo = QHBoxLayout()
        self.chk_originais = QCheckBox("Ver arquivos originais (desmarcado = ver partes editadas)")
        self.chk_originais.stateChanged.connect(self._buscar)
        topo.addWidget(self.chk_originais)
        topo.addStretch()

        self.txt_filtro = QLineEdit()
        self.txt_filtro.setPlaceholderText("Filtrar por nome do arquivo…")
        self.txt_filtro.textChanged.connect(self._buscar)
        topo.addWidget(self.txt_filtro, 1)
        lay.addLayout(topo)

        self.tabela = QTableWidget(0, 5)
        self.tabela.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tabela.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tabela.setStyleSheet(
            f"QTableWidget {{ background:{COR_PAINEL}; gridline-color:{COR_BORDA}; }}"
            f"QHeaderView::section {{ background:qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #E3E8EE, stop:1 #CDD4DE); color:#000000; font-weight:bold; padding:5px; border:none; border-right:1px solid #98A3B3; border-bottom:1px solid #98A3B3; }}")
        lay.addWidget(self.tabela, 1)

        self.lbl_total = QLabel()
        self.lbl_total.setStyleSheet(f"color:{COR_TEXTO_SUB}; font-size:10px;")
        lay.addWidget(self.lbl_total)

    def _buscar(self):
        filtro = self.txt_filtro.text().strip() or None
        if self.chk_originais.isChecked():
            self._mostrar_originais(filtro)
        else:
            self._mostrar_editados(filtro)

    def _mostrar_editados(self, filtro):
        try:
            linhas = self.banco_dados.buscar_partes_editadas(nome_arquivo=filtro)
        except Exception as e:
            QMessageBox.warning(self, "Erro na consulta", f"Não foi possível consultar o banco:\n{e}")
            return

        self.tabela.setHorizontalHeaderLabels(
            ["Data/Hora", "Arquivo Original", "Parte Editada", "Comprimento (mm)", "Qtd. Furos"])
        self.tabela.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.tabela.setRowCount(0)
        for row_idx, (data_hora, nome_original, nome_parte, comprimento, qtd_furos) in enumerate(linhas):
            self.tabela.insertRow(row_idx)
            valores = [data_hora, nome_original, nome_parte, f"{comprimento:.0f}", qtd_furos]
            for col, valor in enumerate(valores):
                self.tabela.setItem(row_idx, col, QTableWidgetItem(str(valor)))
        self.lbl_total.setText(f"{len(linhas)} parte(s) editada(s) encontrada(s)")

    def _mostrar_originais(self, filtro):
        try:
            linhas = self.banco_dados.buscar_arquivos_originais(nome_arquivo=filtro)
        except Exception as e:
            QMessageBox.warning(self, "Erro na consulta", f"Não foi possível consultar o banco:\n{e}")
            return

        self.tabela.setHorizontalHeaderLabels(
            ["Data/Hora", "Arquivo Original", "Estratégia", "Qtd. Partes Geradas", "Perda (mm)"])
        self.tabela.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.tabela.setRowCount(0)
        for row_idx, (data_hora, nome_original, estrategia, qtd_partes, perda_mm) in enumerate(linhas):
            self.tabela.insertRow(row_idx)
            valores = [data_hora, nome_original, estrategia, qtd_partes, f"{perda_mm:.0f}"]
            for col, valor in enumerate(valores):
                self.tabela.setItem(row_idx, col, QTableWidgetItem(str(valor)))
        self.lbl_total.setText(f"{len(linhas)} arquivo(s) original(is) encontrado(s)")


