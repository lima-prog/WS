# -*- coding: utf-8 -*-
"""
Aba "Conversor CAM → DXF": lê uma pasta de arquivos .CAM, lista as peças
numa tabela (com ordenação por coluna e seleção múltipla) e converte as
selecionadas para DXF no modo CORTE — mesma ferramenta do script original
`conversor_cam_dxf_corte_v14.py` (Tkinter), agora como aba PyQt5 sobre o
motor em conversor/processador.py.

CAMs com dobra (perfis com seção transversal, não chapa plana) só são
listados se o usuário marcar "Mostrar CAM com dobra" — e mesmo assim não
são convertidos nesta versão (modo DOBRA ainda não implementado), igual
ao script original.
"""
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QPushButton, QTableWidget, QTableWidgetItem,
                             QAbstractItemView, QHeaderView, QCheckBox, QDialog,
                             QMessageBox, QFrame, QFileDialog, QShortcut, QSizePolicy)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QKeySequence, QColor

from nucleo.estilo import COR_PAINEL, COR_BORDA, COR_TEXTO, COR_TEXTO_SUB, COR_DESTAQUE, COR_BG
from conversor.processador import ProcessadorConversor
from conversor.utilitarios import nome_dxf, normalizar_obra
from conversor.dialogos import DialogoEditarObra

# (chave em `dados`, rótulo da coluna) — mesma ordem/rótulos da tabela original,
# com "obra" acrescentada no final (não existia na versão original em Tkinter).
_COLUNAS = [
    ("posicao", "POSIÇÃO"),
    ("comprimento", "COMPRIMENTO"),
    ("largura", "LARGURA"),
    ("espessura", "ESPESSURA"),
    ("material", "MATERIAL"),
    ("quantidade", "QUANTIDADE"),
    ("obra", "OBRA"),
]
# Colunas clicáveis para ordenar e como comparar cada uma. POSIÇÃO/
# COMPRIMENTO/LARGURA/ESPESSURA -> numérico. MATERIAL/OBRA -> alfabético.
# QUANTIDADE não ordena (mesmo comportamento do script original).
_COLUNAS_TIPO = {
    "posicao": "numero",
    "comprimento": "numero",
    "largura": "numero",
    "espessura": "numero",
    "material": "texto",
    "obra": "texto",
}
_COLUNAS_COM_MM = {"comprimento", "largura", "espessura"}
# Largura inicial (px) de cada coluna — MATERIAL é a única que "estica"
# pra ocupar o espaço sobrando (nome de material varia bastante de tamanho).
_COLUNAS_LARGURA = {
    "posicao": 130, "comprimento": 175, "largura": 150,
    "espessura": 145, "material": 230, "quantidade": 140, "obra": 170,
}


def _obra_exibicao(dados):
    """
    Valor de obra que vale de verdade pra essa peça agora — o que aparece
    na coluna OBRA e no nome do DXF gerado (`nome_dxf`, em
    conversor/utilitarios.py, usa exatamente a mesma prioridade). Prioriza
    a sobreposição manual (`obra_manual`, gravada pelo botão "Editar
    Obra"); cai pro cálculo automático (`normalizar_obra`, a partir do
    nome da pasta) quando não há nenhuma.
    """
    manual = (dados.get("obra_manual") or "").strip()
    return manual if manual else normalizar_obra(dados.get("obra", ""))


class AbaConversor(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.processador = ProcessadorConversor(self)
        self.pasta = ""
        self.dados_arquivos = {}    # {nome_do_cam: dados}
        self._linhas = []           # [(nome_do_cam, dados), ...] — visíveis, já ordenadas
        self._sort_coluna = None
        self._sort_reverso = False
        self.setup_ui()

    # ── layout ───────────────────────────────────────────────────────────────

    def setup_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # cabeçalho
        header = QFrame()
        header.setFixedHeight(48)
        header.setStyleSheet(
            f"background:#E4E8ED; border-bottom:2px solid #0B3D91;")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(16, 0, 16, 0)
        lbl_titulo = QLabel("🗂  Conversor CAM → DXF")
        lbl_titulo.setStyleSheet(
            f"color:{COR_TEXTO}; font-size:15px; font-weight:bold;")
        lbl_modo = QLabel("MODO: CORTE")
        lbl_modo.setStyleSheet(
            f"color:white; background:{COR_DESTAQUE}; font-size:10px; "
            "font-weight:bold; border-radius:4px; padding:2px 10px;")
        lbl_sub = QLabel("SISTEMA - PPCPM")
        lbl_sub.setStyleSheet(f"color:{COR_TEXTO_SUB}; font-size:11px;")
        hl.addWidget(lbl_titulo)
        hl.addSpacing(10)
        hl.addWidget(lbl_modo)
        hl.addStretch()
        btn_ajuda = QPushButton("?  Ajuda")
        btn_ajuda.setObjectName("btn_limpar")
        btn_ajuda.clicked.connect(self.mostrar_ajuda)
        hl.addWidget(btn_ajuda)
        hl.addSpacing(10)
        hl.addWidget(lbl_sub)
        root_layout.addWidget(header)

        # corpo central
        corpo = QWidget()
        corpo_layout = QVBoxLayout(corpo)
        corpo_layout.setContentsMargins(14, 12, 14, 12)
        corpo_layout.setSpacing(8)
        root_layout.addWidget(corpo, 1)

        # configuração
        cfg_lay = QHBoxLayout()
        self.chk_mostrar_dobra = QCheckBox("Mostrar CAM com dobra")
        self.chk_mostrar_dobra.setChecked(False)
        self.chk_mostrar_dobra.stateChanged.connect(self.atualizar_visualizacao)
        cfg_lay.addWidget(self.chk_mostrar_dobra)
        lbl_dobra_info = QLabel("(o modo de conversão atual continua sendo somente CORTE)")
        lbl_dobra_info.setStyleSheet(f"color:{COR_TEXTO_SUB}; font-size:10px;")
        cfg_lay.addWidget(lbl_dobra_info)
        cfg_lay.addStretch()
        corpo_layout.addLayout(cfg_lay)

        # seleção de pasta
        pasta_lay = QHBoxLayout()
        self.lbl_pasta = QLabel("Nenhuma pasta selecionada")
        self.lbl_pasta.setStyleSheet(f"color:{COR_TEXTO_SUB}; font-size:11px;")
        pasta_lay.addWidget(self.lbl_pasta, 1)
        self.btn_limpar_lista = QPushButton("Limpar Lista")
        self.btn_limpar_lista.setObjectName("btn_limpar")
        self.btn_limpar_lista.clicked.connect(self.limpar_lista)
        pasta_lay.addWidget(self.btn_limpar_lista)
        self.btn_abrir = QPushButton("📁 Abrir Pasta")
        self.btn_abrir.setObjectName("btn_processar")
        self.btn_abrir.clicked.connect(self.abrir_pasta)
        pasta_lay.addWidget(self.btn_abrir)
        corpo_layout.addLayout(pasta_lay)

        # tabela
        self.tabela = QTableWidget(0, len(_COLUNAS))
        self.tabela.setHorizontalHeaderLabels([label for _, label in _COLUNAS])
        self.tabela.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tabela.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tabela.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.tabela.setAlternatingRowColors(True)
        self.tabela.verticalHeader().setVisible(False)
        self.tabela.horizontalHeader().setStretchLastSection(False)
        self.tabela.horizontalHeader().setMinimumSectionSize(80)
        for col, (chave, _) in enumerate(_COLUNAS):
            self.tabela.setColumnWidth(col, _COLUNAS_LARGURA[chave])
            modo = QHeaderView.Stretch if chave == "material" else QHeaderView.Interactive
            self.tabela.horizontalHeader().setSectionResizeMode(col, modo)
        self.tabela.setStyleSheet(f"""
            QTableWidget {{
                background:{COR_PAINEL}; alternate-background-color:#F6F7F9;
                color:{COR_TEXTO}; border:1px solid {COR_BORDA}; border-radius:4px;
                gridline-color:{COR_BORDA};
            }}
            QHeaderView::section {{ background:qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #E3E8EE, stop:1 #CDD4DE); color:#000000; font-weight:bold; padding:5px; border:none; border-right:1px solid #98A3B3; border-bottom:1px solid #98A3B3; }}
            QTableWidget::item:selected {{ background: #DBE8FB; color: #000000; }}
        """)
        self.tabela.horizontalHeader().sectionClicked.connect(self._ao_clicar_cabecalho)
        self.tabela.itemSelectionChanged.connect(self.atualizar_selecao)
        corpo_layout.addWidget(self.tabela, 1)

        atalho_selecionar_tudo = QShortcut(QKeySequence("Ctrl+A"), self.tabela)
        atalho_selecionar_tudo.setContext(Qt.WidgetShortcut)
        atalho_selecionar_tudo.activated.connect(self.tabela.selectAll)

        # rodapé: seleção / nome do dxf / status
        selecao_lay = QHBoxLayout()
        self.lbl_selecao = QLabel("0 peça(s) selecionada(s)")
        self.lbl_selecao.setStyleSheet(f"color:{COR_DESTAQUE}; font-size:11px; font-weight:bold;")
        selecao_lay.addWidget(self.lbl_selecao)
        selecao_lay.addStretch()
        self.btn_editar_obra = QPushButton("✎ Editar Obra")
        self.btn_editar_obra.setObjectName("btn_limpar")
        self.btn_editar_obra.setEnabled(False)
        self.btn_editar_obra.setToolTip(
            "Corrige manualmente a obra usada no nome do DXF, para "
            "peça(s) selecionada(s) — útil quando o nome da pasta foge "
            "do padrão que a regra automática espera.")
        self.btn_editar_obra.clicked.connect(self.editar_obra_selecionados)
        selecao_lay.addWidget(self.btn_editar_obra)
        corpo_layout.addLayout(selecao_lay)

        self.lbl_nome = QLabel("")
        self.lbl_nome.setStyleSheet(f"color:{COR_TEXTO_SUB}; font-size:10px;")
        self.lbl_nome.setWordWrap(True)
        corpo_layout.addWidget(self.lbl_nome)

        self.lbl_status = QLabel("Aguardando...")
        self.lbl_status.setStyleSheet(f"color:{COR_TEXTO_SUB}; font-size:10px;")
        corpo_layout.addWidget(self.lbl_status)

        # opção de organização da saída
        opcoes_lay = QHBoxLayout()
        self.chk_organizar_subpastas = QCheckBox(
            "Organizar DXFs em subpastas por espessura + material")
        self.chk_organizar_subpastas.setChecked(True)
        opcoes_lay.addWidget(self.chk_organizar_subpastas)
        opcoes_lay.addStretch()
        corpo_layout.addLayout(opcoes_lay)

        # converter — botão normal, ancorado no canto inferior esquerdo
        # (não estica pra largura toda: QVBoxLayout esticaria por padrão,
        # por isso vai dentro de um QHBoxLayout com addStretch() depois dele)
        converter_lay = QHBoxLayout()
        self.btn_converter = QPushButton("Converter Selecionados para DXF")
        self.btn_converter.setObjectName("btn_processar")
        self.btn_converter.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.btn_converter.clicked.connect(self.iniciar_conversao)
        converter_lay.addWidget(self.btn_converter)
        converter_lay.addStretch()
        corpo_layout.addLayout(converter_lay)

    # ── ajuda ────────────────────────────────────────────────────────────────

    def mostrar_ajuda(self):
        QMessageBox.information(
            self, "Ajuda",
            "• CTRL+clique para selecionar peças, SHIFT+clique para selecionar "
            "um intervalo, ou CTRL+A para selecionar todas.\n\n"
            "• Clique no cabeçalho de POSIÇÃO, COMPRIMENTO, LARGURA, "
            "ESPESSURA, MATERIAL ou OBRA para ordenar a tabela (clique de "
            "novo para inverter).\n\n"
            "• A coluna OBRA mostra o identificador que vai entrar no nome "
            "do DXF. Se o nome da pasta fugir do padrão esperado (ex.: um "
            "sufixo diferente de \"_L1\"/\"_L2\"), selecione a(s) peça(s) e "
            "clique em \"✎ Editar Obra\" pra corrigir manualmente — o valor "
            "digitado aparece em destaque na coluna e some se você fechar "
            "essa aba ou reabrir a pasta.\n\n"
            "• \"Mostrar CAM com dobra\" exibe peças que ainda não são "
            "convertidas neste modo (somente CORTE).\n\n"
            "• \"Limpar Lista\" remove os arquivos carregados sem precisar "
            "reabrir o programa.\n\n"
            "• Antes de converter, escolha se os DXFs vão para subpastas "
            "por espessura + material ou direto na pasta escolhida."
        )

    # ── pasta / carregamento ────────────────────────────────────────────────

    def abrir_pasta(self):
        pasta = QFileDialog.getExistingDirectory(
            self, "Selecione a pasta dos arquivos CAM")
        if not pasta:
            return

        self.pasta = pasta
        self.lbl_pasta.setText(pasta)
        self.lbl_pasta.setToolTip(pasta)
        self.dados_arquivos.clear()
        self._sort_coluna = None
        self._sort_reverso = False

        self.btn_abrir.setEnabled(False)
        QApplication.processEvents()
        try:
            self.dados_arquivos, erros, total = self.processador.carregar_pasta(pasta)
        finally:
            self.btn_abrir.setEnabled(True)

        self.atualizar_visualizacao()

        if erros:
            self.atualizar_status(self.lbl_status.text() + f" | {erros} arquivo(s) com erro")

        if total == 0:
            QMessageBox.warning(
                self, "Nenhum CAM", "Não encontrei arquivos .CAM nessa pasta.")

    def limpar_lista(self):
        if not self.dados_arquivos:
            return
        resposta = QMessageBox.question(
            self, "Limpar lista", "Deseja limpar a lista de CAMs carregada?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if resposta != QMessageBox.Yes:
            return

        self.pasta = ""
        self.dados_arquivos.clear()
        self._linhas = []
        self._sort_coluna = None
        self._sort_reverso = False
        self.tabela.setRowCount(0)
        self._atualizar_indicador_ordenacao()

        self.lbl_pasta.setText("Nenhuma pasta selecionada")
        self.lbl_pasta.setToolTip("")
        self.atualizar_status("Aguardando...")
        self.atualizar_selecao()

    # ── tabela: filtro, ordenação, preenchimento ────────────────────────────

    def atualizar_visualizacao(self):
        """
        Recalcula quais linhas aparecem conforme a configuração:
        - desmarcado: mostra somente CAMs planificados (PLANIFICADO);
        - marcado: mostra planificados + CAMs com dobra (DOBRADO).
        """
        mostrar_dobra = self.chk_mostrar_dobra.isChecked()
        visiveis, ocultos = [], 0

        for arquivo, dados in self.dados_arquivos.items():
            tipo = dados.get("tipo_cam", "DESCONHECIDO")
            if tipo == "DOBRADO" and not mostrar_dobra:
                ocultos += 1
                continue
            visiveis.append((arquivo, dados))

        self._linhas = visiveis
        self._aplicar_ordenacao()
        self._preencher_tabela()

        texto = f"{len(visiveis)} peça(s) exibida(s)"
        if ocultos:
            texto += f" | {ocultos} CAM(s) com dobra oculto(s)"
        self.atualizar_status(texto)
        self.atualizar_selecao()

    def _ao_clicar_cabecalho(self, indice_coluna):
        coluna, _ = _COLUNAS[indice_coluna]
        if coluna not in _COLUNAS_TIPO:  # QUANTIDADE não ordena
            return
        if self._sort_coluna == coluna:
            self._sort_reverso = not self._sort_reverso
        else:
            self._sort_coluna = coluna
            self._sort_reverso = False
        self._aplicar_ordenacao()
        self._preencher_tabela()

    def _aplicar_ordenacao(self):
        coluna = self._sort_coluna
        if coluna:
            tipo = _COLUNAS_TIPO.get(coluna, "texto")

            def chave(item):
                _, dados = item
                valor = _obra_exibicao(dados) if coluna == "obra" else (dados.get(coluna) or "")
                if tipo == "numero":
                    texto = str(valor).replace(",", ".").strip()
                    try:
                        return (0, float(texto))
                    except ValueError:
                        return (1, str(valor).lower())
                return (0, str(valor).lower())

            self._linhas.sort(key=chave, reverse=self._sort_reverso)

        self._atualizar_indicador_ordenacao()

    def _atualizar_indicador_ordenacao(self):
        rotulos = []
        for coluna, label in _COLUNAS:
            texto = label
            if coluna == self._sort_coluna:
                texto += "  ▼" if self._sort_reverso else "  ▲"
            rotulos.append(texto)
        self.tabela.setHorizontalHeaderLabels(rotulos)

    def _preencher_tabela(self):
        # mantém a seleção (por nome de arquivo) ao reordenar/refiltrar
        selecionados_antes = set(self._arquivos_selecionados())

        self.tabela.blockSignals(True)
        self.tabela.setRowCount(len(self._linhas))
        for linha, (arquivo, dados) in enumerate(self._linhas):
            for col, (chave, _) in enumerate(_COLUNAS):
                manual = False
                if chave == "obra":
                    valor = _obra_exibicao(dados)
                    manual = bool((dados.get("obra_manual") or "").strip())
                    texto = f"✎ {valor}" if manual else (valor or "—")
                else:
                    valor = dados.get(chave) or ""
                    if chave in _COLUNAS_COM_MM and valor:
                        texto = f"{valor} mm"
                    else:
                        texto = str(valor) if valor else "—"
                item = QTableWidgetItem(texto)
                item.setTextAlignment(Qt.AlignCenter)
                if manual:
                    item.setForeground(QColor(COR_DESTAQUE))
                    item.setToolTip(
                        f"Obra definida manualmente: \"{valor}\"\n"
                        "(botão \"Editar Obra\").")
                if col == 0:
                    item.setData(Qt.UserRole, arquivo)
                self.tabela.setItem(linha, col, item)
        self.tabela.blockSignals(False)

        # restaura seleção
        if selecionados_antes:
            self.tabela.clearSelection()
            for linha, (arquivo, _) in enumerate(self._linhas):
                if arquivo in selecionados_antes:
                    self.tabela.selectRow(linha)

        self.atualizar_selecao()

    # ── seleção ──────────────────────────────────────────────────────────────

    def _arquivos_selecionados(self):
        linhas = {idx.row() for idx in self.tabela.selectedIndexes()}
        arquivos = []
        for linha in sorted(linhas):
            item = self.tabela.item(linha, 0)
            if item is not None:
                arquivos.append(item.data(Qt.UserRole))
        return arquivos

    def atualizar_selecao(self):
        arquivos = self._arquivos_selecionados()
        qtd = len(arquivos)
        self.lbl_selecao.setText(f"{qtd} peça(s) selecionada(s)")
        self.btn_editar_obra.setEnabled(qtd > 0)

        if qtd == 1:
            dados = self.dados_arquivos.get(arquivos[0])
            self.lbl_nome.setText(f"DXF: {nome_dxf(dados)}" if dados else "")
        elif qtd > 1:
            self.lbl_nome.setText(
                "Vários arquivos selecionados — cada DXF terá seu nome automático.")
        else:
            self.lbl_nome.setText("")

    def editar_obra_selecionados(self):
        """
        Abre o diálogo "Editar Obra" pra sobrescrever manualmente a obra
        de todas as peças selecionadas de uma vez — o caso comum é
        selecionar a pasta inteira (Ctrl+A) quando ela tem um nome fora
        do padrão que `normalizar_obra()` reconhece.
        """
        arquivos = [a for a in self._arquivos_selecionados() if a in self.dados_arquivos]
        if not arquivos:
            return

        valores_atuais = {_obra_exibicao(self.dados_arquivos[a]) for a in arquivos}
        valor_inicial = valores_atuais.pop() if len(valores_atuais) == 1 else ""

        dialogo = DialogoEditarObra(len(arquivos), valor_inicial, parent=self)
        if dialogo.exec_() != QDialog.Accepted or dialogo.valor is None:
            return

        for arquivo in arquivos:
            dados = self.dados_arquivos[arquivo]
            if dialogo.valor:
                dados["obra_manual"] = dialogo.valor
            else:
                dados.pop("obra_manual", None)  # "Restaurar automático"

        self._preencher_tabela()

    # ── conversão ────────────────────────────────────────────────────────────

    def iniciar_conversao(self):
        arquivos_selecionados = self._arquivos_selecionados()
        if not arquivos_selecionados:
            QMessageBox.warning(self, "Atenção", "Selecione pelo menos uma peça.")
            return

        pasta_saida = QFileDialog.getExistingDirectory(
            self, "Escolha a pasta onde os DXFs serão salvos")
        if not pasta_saida:
            return

        subpastas = self.chk_organizar_subpastas.isChecked()
        total = len(arquivos_selecionados)

        self.btn_converter.setEnabled(False)
        QApplication.processEvents()
        try:
            sucesso, erros = self.processador.converter_arquivos(
                self.pasta, arquivos_selecionados, self.dados_arquivos,
                pasta_saida, subpastas)
        finally:
            self.btn_converter.setEnabled(True)

        if erros:
            texto = "\n".join(erros[:10])
            if len(erros) > 10:
                texto += f"\n... e mais {len(erros) - 10} erro(s)."
            QMessageBox.warning(
                self, "Conversão concluída com erros",
                f"Convertidos: {sucesso}\nErros: {len(erros)}\n\n{texto}")
        else:
            organizacao = (
                "Os DXFs foram separados automaticamente por espessura + material."
                if subpastas else
                "Os DXFs foram salvos direto na pasta escolhida, sem subpastas."
            )
            QMessageBox.information(
                self, "Conversão concluída",
                f"{sucesso} DXF(s) criado(s) com sucesso!\n\n"
                f"Pasta principal:\n{pasta_saida}\n\n"
                f"{organizacao}\n\n"
                "CAMs com dobra não são convertidos no modo CORTE.")

        self.atualizar_status(f"Finalizado: {sucesso} de {total} DXF(s) criado(s).")

    # ── callbacks chamados pelo ProcessadorConversor ──────────────────────────

    def atualizar_status(self, msg):
        self.lbl_status.setText(msg)
        QApplication.processEvents()
