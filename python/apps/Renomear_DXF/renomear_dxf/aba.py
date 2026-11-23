# -*- coding: utf-8 -*-
"""
Aba "Renomear DXF (Tekla/Tecno)": ferramenta separada do Conversor CAM →
DXF, pra um fluxo de trabalho diferente — quando o Tekla/Tecno já exportou
os arquivos .DXF/.DWG prontos por fora (não passam pelo motor de
conversão deste app) e só falta renomear cada um no formato "<posição> -
OF<obra/trecho> - Q<qtd>", usando a quantidade lida do .CAM
correspondente.

Unificada a partir de um .exe antigo separado — ver
renomear_dxf/utilitarios.py para o histórico completo e as correções
feitas em relação ao script original.
"""
import os

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QLineEdit, QTableWidget,
                             QTableWidgetItem, QAbstractItemView, QHeaderView,
                             QMessageBox, QFrame, QFileDialog, QShortcut,
                             QSizePolicy, QApplication)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QKeySequence, QColor

from nucleo.estilo import (COR_PAINEL, COR_BORDA, COR_TEXTO, COR_TEXTO_SUB,
                           COR_DESTAQUE, COR_VERDE, COR_VERMELHO, COR_AMARELO, COR_BG)
from renomear_dxf.utilitarios import derivar_obra_trecho, nome_renomeado
from renomear_dxf.processador import analisar, renomear

_COLUNAS = [
    ("arquivo_atual", "ARQUIVO ATUAL"),
    ("posicao", "POSIÇÃO"),
    ("quantidade", "QUANTIDADE"),
    ("nome_final", "NOME FINAL"),
    ("status", "STATUS"),
]
_COLUNAS_LARGURA = {
    "arquivo_atual": 200, "posicao": 100, "quantidade": 140,
    "nome_final": 260, "status": 260,
}
# (rótulo, cor de fundo do badge, cor do texto) por status. Até uma
# versão anterior, isso usava fundo ESCURO (mesmo estilo de badge que os
# diagnósticos da Auditoria usavam) — sobrou da época do tema escuro e
# nunca foi reconferido quando o app trocou pra paleta clara "Papel &
# Grafite": as cores de texto (COR_VERDE/COR_VERMELHO/COR_AMARELO) são
# tons escuros pensados pra ficar em cima de fundo CLARO, então texto
# escuro em cima de fundo quase preto ficava com contraste ruim — mesmo
# bug, mesma causa raiz, do `_CORES_DIAGNOSTICO` da Auditoria (ver
# CONTINUIDADE.md). Corrigido com o mesmo par de tons pastel claros já
# usado lá: fundo bem claro + a cor de texto correspondente por cima.
# "renomeado" e "erro_renomear" só aparecem DEPOIS de clicar em "Renomear
# Selecionados" (ver `renomear_selecionados`, mais abaixo) — nunca vêm de
# `analisar()`.
_STATUS_INFO = {
    "ok":              ("✅ Pronto pra renomear",     "#E9F3EA", COR_VERDE),
    "sem_cam":         ("❌ Sem .CAM correspondente",  "#FBE7E4", COR_VERMELHO),
    "sem_quantidade":  ("⚠ CAM sem QTA_PEZ",           "#FBF0DC", COR_AMARELO),
    "renomeado":       ("✅ Renomeado",                "#E9F3EA", COR_VERDE),
    "erro_renomear":   ("❌ Erro ao renomear",          "#FBE7E4", COR_VERMELHO),
}
# Estilo aplicado por cima do "btn_processar" padrão nos dois botões
# principais desta tela (Analisar / Renomear Selecionados) — pedido do
# usuário: o botão "Analisar" estava discreto demais, difícil de notar.
# Maior, mas sem exagero (mesma cor verde de sempre, só mais espaço).
_ESTILO_BOTAO_PRINCIPAL = "font-size:13px; padding:12px 28px;"


class AbaRenomearDxf(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.pasta_cam = ""
        self.pasta_dxf = ""
        self._linhas = []   # última análise (lista de dicts de processador.analisar)
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
        lbl_titulo = QLabel("🏷  Renomear DXF (Tekla/Tecno)")
        lbl_titulo.setStyleSheet(
            f"color:{COR_TEXTO}; font-size:15px; font-weight:bold;")
        lbl_sub = QLabel("SISTEMA - PPCPM")
        lbl_sub.setStyleSheet(f"color:{COR_TEXTO_SUB}; font-size:11px;")
        hl.addWidget(lbl_titulo)
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

        # pasta CAM — campo editável (aceita colar o caminho direto) + botão
        cam_lay = QHBoxLayout()
        lbl_cam_rotulo = QLabel("Pasta CAM:")
        lbl_cam_rotulo.setStyleSheet(f"color:{COR_TEXTO}; font-size:11px; font-weight:bold;")
        cam_lay.addWidget(lbl_cam_rotulo)
        self.entry_pasta_cam = QLineEdit()
        self.entry_pasta_cam.setPlaceholderText(
            "Cole aqui o caminho da pasta, ou use o botão ao lado")
        self.entry_pasta_cam.editingFinished.connect(self._pasta_cam_editada_manualmente)
        cam_lay.addWidget(self.entry_pasta_cam, 1)
        btn_pasta_cam = QPushButton("📁 Selecionar Pasta CAM")
        btn_pasta_cam.setObjectName("btn_limpar")
        btn_pasta_cam.clicked.connect(self.selecionar_pasta_cam)
        cam_lay.addWidget(btn_pasta_cam)
        corpo_layout.addLayout(cam_lay)

        # pasta DXF/DWG — mesma ideia: campo editável + botão
        dxf_lay = QHBoxLayout()
        lbl_dxf_rotulo = QLabel("Pasta DXF/DWG:")
        lbl_dxf_rotulo.setStyleSheet(f"color:{COR_TEXTO}; font-size:11px; font-weight:bold;")
        dxf_lay.addWidget(lbl_dxf_rotulo)
        self.entry_pasta_dxf = QLineEdit()
        self.entry_pasta_dxf.setPlaceholderText(
            "Cole aqui o caminho da pasta, ou use o botão ao lado")
        self.entry_pasta_dxf.editingFinished.connect(self._pasta_dxf_editada_manualmente)
        dxf_lay.addWidget(self.entry_pasta_dxf, 1)
        btn_pasta_dxf = QPushButton("📁 Selecionar Pasta DXF/DWG")
        btn_pasta_dxf.setObjectName("btn_limpar")
        btn_pasta_dxf.clicked.connect(self.selecionar_pasta_dxf)
        dxf_lay.addWidget(btn_pasta_dxf)
        corpo_layout.addLayout(dxf_lay)

        # obra/trecho (editável)
        obra_lay = QHBoxLayout()
        lbl_obra_rotulo = QLabel("Obra/Trecho:")
        lbl_obra_rotulo.setStyleSheet(f"color:{COR_TEXTO}; font-size:11px; font-weight:bold;")
        obra_lay.addWidget(lbl_obra_rotulo)
        self.entry_obra_trecho = QLineEdit()
        self.entry_obra_trecho.setPlaceholderText("preenchido ao selecionar a pasta CAM")
        self.entry_obra_trecho.setToolTip(
            "Identificador que entra no nome final dos arquivos. É "
            "preenchido automaticamente a partir do nome da pasta um "
            "nível acima da pasta CAM — corrija na mão se não bater, e "
            "clique em \"Analisar\" de novo pra atualizar a tabela.")
        self.entry_obra_trecho.setFixedWidth(220)
        obra_lay.addWidget(self.entry_obra_trecho)
        self.lbl_liberacao = QLabel("")
        self.lbl_liberacao.setStyleSheet(f"color:{COR_TEXTO_SUB}; font-size:10px;")
        obra_lay.addWidget(self.lbl_liberacao)
        obra_lay.addStretch()
        corpo_layout.addLayout(obra_lay)

        # "Analisar" — botão principal desta etapa, numa linha própria e
        # bem maior/mais visível do que antes (pedido do usuário: estava
        # escondido no fim da linha de Obra/Trecho, disputando espaço com
        # outros campos).
        analisar_lay = QHBoxLayout()
        self.btn_analisar = QPushButton("🔍 Analisar")
        self.btn_analisar.setObjectName("btn_processar")
        self.btn_analisar.setStyleSheet(_ESTILO_BOTAO_PRINCIPAL)
        self.btn_analisar.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.btn_analisar.setEnabled(False)
        self.btn_analisar.clicked.connect(self.analisar_pastas)
        analisar_lay.addWidget(self.btn_analisar)
        analisar_lay.addStretch()
        corpo_layout.addLayout(analisar_lay)

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
            modo = QHeaderView.Stretch if chave == "nome_final" else QHeaderView.Interactive
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
        self.tabela.itemSelectionChanged.connect(self.atualizar_selecao)
        corpo_layout.addWidget(self.tabela, 1)

        atalho_selecionar_tudo = QShortcut(QKeySequence("Ctrl+A"), self.tabela)
        atalho_selecionar_tudo.setContext(Qt.WidgetShortcut)
        atalho_selecionar_tudo.activated.connect(self.tabela.selectAll)

        # rodapé: seleção / renomear — mesmo tratamento de destaque do
        # "Analisar" acima, já que é a outra ação principal desta tela.
        rodape_lay = QHBoxLayout()
        self.lbl_selecao = QLabel("0 arquivo(s) selecionado(s)")
        self.lbl_selecao.setStyleSheet(f"color:{COR_DESTAQUE}; font-size:11px; font-weight:bold;")
        rodape_lay.addWidget(self.lbl_selecao)
        rodape_lay.addStretch()
        self.btn_renomear = QPushButton("✏ Renomear Selecionados")
        self.btn_renomear.setObjectName("btn_processar")
        self.btn_renomear.setStyleSheet(_ESTILO_BOTAO_PRINCIPAL)
        self.btn_renomear.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.btn_renomear.setEnabled(False)
        self.btn_renomear.clicked.connect(self.renomear_selecionados)
        rodape_lay.addWidget(self.btn_renomear)
        corpo_layout.addLayout(rodape_lay)

        self.lbl_status = QLabel("Selecione a pasta CAM e a pasta DXF/DWG pra começar.")
        self.lbl_status.setStyleSheet(f"color:{COR_TEXTO_SUB}; font-size:10px;")
        self.lbl_status.setWordWrap(True)
        corpo_layout.addWidget(self.lbl_status)

    # ── ajuda ────────────────────────────────────────────────────────────────

    def mostrar_ajuda(self):
        QMessageBox.information(
            self, "Ajuda",
            "Ferramenta separada do Conversor CAM → DXF: use quando o "
            "Tekla/Tecno já exportou os arquivos .DXF/.DWG prontos por "
            "fora (sem passar pelo conversor deste app) e só falta "
            "renomear cada um no formato \"<posição> - OF<obra/trecho> - "
            "Q<qtd>\".\n\n"
            "1) Informe a pasta CAM (onde estão os .CAM daquela obra) — "
            "cole o caminho direto no campo ou use o botão "
            "\"Selecionar Pasta CAM\". O campo \"Obra/Trecho\" é "
            "preenchido automaticamente a partir do nome da pasta um "
            "nível acima; corrija-o na mão se não bater com o esperado.\n\n"
            "2) Informe a pasta onde estão os .DXF/.DWG já exportados, do "
            "mesmo jeito (colar o caminho ou usar o botão) — a busca "
            "entra em todas as subpastas.\n\n"
            "3) Clique em \"🔍 Analisar\" pra ver, numa tabela, o nome "
            "final de cada arquivo ANTES de renomear de verdade.\n\n"
            "4) Selecione as linhas prontas (✅) e clique em \"✏ Renomear "
            "Selecionados\". Arquivos sem .CAM correspondente ou com "
            "problema no .CAM ficam marcados e não são renomeados.\n\n"
            "• Depois de renomear, a própria linha muda pra \"✅ "
            "Renomeado\" — é esperado que ela deixe de aparecer como "
            "\"pronta pra renomear\" (já foi feito) e NÃO é a mesma coisa "
            "que \"Sem .CAM correspondente\" (que indica um problema).\n\n"
            "• Se corrigir o campo \"Obra/Trecho\" depois de já ter "
            "analisado, clique em \"Analisar\" de novo pra os nomes "
            "finais da tabela refletirem a correção.\n\n"
            "• Nunca sobrescreve um arquivo já existente com o mesmo "
            "nome final — se acontecer, a linha vira \"❌ Erro ao "
            "renomear\"."
        )

    # ── seleção de pastas ────────────────────────────────────────────────────

    def _definir_pasta_cam(self, pasta):
        self.pasta_cam = pasta
        self.entry_pasta_cam.setText(pasta)
        self.entry_pasta_cam.setToolTip(pasta)

        obra_trecho, liberacao = derivar_obra_trecho(pasta)
        self.entry_obra_trecho.setText(obra_trecho)
        self.lbl_liberacao.setText(f"(pasta detectada: {liberacao})" if liberacao else "")

        self._atualizar_habilitacao_analisar()

    def selecionar_pasta_cam(self):
        pasta = QFileDialog.getExistingDirectory(
            self, "Selecione a pasta dos arquivos .CAM")
        if not pasta:
            return
        self._definir_pasta_cam(pasta)

    def _pasta_cam_editada_manualmente(self):
        """
        Chamado quando o usuário digita/cola um caminho direto no campo
        (Enter, ou sair do campo) em vez de usar o botão de diálogo.
        Aceita colar um caminho copiado do Windows Explorer (que às vezes
        vem entre aspas) e valida que a pasta existe antes de aceitar —
        se não existir, avisa e devolve o campo pro último valor válido.
        """
        caminho = self.entry_pasta_cam.text().strip().strip('"')
        if not caminho or caminho == self.pasta_cam:
            return
        if not os.path.isdir(caminho):
            QMessageBox.warning(
                self, "Pasta não encontrada",
                f"Não encontrei essa pasta:\n\n{caminho}")
            self.entry_pasta_cam.setText(self.pasta_cam)
            return
        self._definir_pasta_cam(caminho)

    def _definir_pasta_dxf(self, pasta):
        self.pasta_dxf = pasta
        self.entry_pasta_dxf.setText(pasta)
        self.entry_pasta_dxf.setToolTip(pasta)
        self._atualizar_habilitacao_analisar()

    def selecionar_pasta_dxf(self):
        sugestao = os.path.join(os.path.expanduser("~"), "Desktop", "DXF")
        diretorio_inicial = sugestao if os.path.isdir(sugestao) else os.path.expanduser("~")
        pasta = QFileDialog.getExistingDirectory(
            self, "Selecione a pasta dos arquivos .DXF/.DWG já exportados",
            diretorio_inicial)
        if not pasta:
            return
        self._definir_pasta_dxf(pasta)

    def _pasta_dxf_editada_manualmente(self):
        caminho = self.entry_pasta_dxf.text().strip().strip('"')
        if not caminho or caminho == self.pasta_dxf:
            return
        if not os.path.isdir(caminho):
            QMessageBox.warning(
                self, "Pasta não encontrada",
                f"Não encontrei essa pasta:\n\n{caminho}")
            self.entry_pasta_dxf.setText(self.pasta_dxf)
            return
        self._definir_pasta_dxf(caminho)

    def _atualizar_habilitacao_analisar(self):
        self.btn_analisar.setEnabled(bool(self.pasta_cam and self.pasta_dxf))

    # ── análise ──────────────────────────────────────────────────────────────

    def analisar_pastas(self):
        if not self.pasta_cam or not self.pasta_dxf:
            return

        obra_trecho_manual = self.entry_obra_trecho.text().strip()

        self.btn_analisar.setEnabled(False)
        QApplication.processEvents()
        try:
            linhas, obra_trecho_auto, liberacao, avisos = analisar(
                self.pasta_cam, self.pasta_dxf)
        finally:
            self.btn_analisar.setEnabled(True)

        # Se o usuário editou o campo "Obra/Trecho" (sobrescrevendo o
        # valor detectado automaticamente), esse valor manda no nome
        # final de cada linha "ok" — sem precisar reler CAM/DXF de novo.
        obra_trecho = obra_trecho_manual or obra_trecho_auto
        if obra_trecho != obra_trecho_auto:
            for linha in linhas:
                if linha["status"] == "ok":
                    ext = os.path.splitext(linha["arquivo_atual"])[1]
                    linha["nome_final"] = nome_renomeado(
                        linha["posicao"], obra_trecho, linha["quantidade"], ext)

        self._linhas = linhas
        self._preencher_tabela()

        prontos = sum(1 for l in linhas if l["status"] == "ok")
        texto = f"{len(linhas)} arquivo(s) encontrado(s) | {prontos} pronto(s) pra renomear"
        if avisos:
            texto += " | " + " | ".join(avisos)
        self.atualizar_status(texto)

    def _preencher_tabela(self):
        self.tabela.blockSignals(True)
        self.tabela.setRowCount(len(self._linhas))
        for linha_idx, linha in enumerate(self._linhas):
            status_texto, status_bg, status_fg = _STATUS_INFO.get(
                linha["status"], (linha["status"], COR_PAINEL, COR_TEXTO_SUB))
            valores = {
                "arquivo_atual": linha["arquivo_atual"],
                "posicao": linha["posicao"],
                "quantidade": linha["quantidade"] or "—",
                "nome_final": linha["nome_final"] or "—",
                "status": status_texto,
            }
            for col, (chave, _) in enumerate(_COLUNAS):
                item = QTableWidgetItem(str(valores[chave]))
                item.setTextAlignment(Qt.AlignCenter)
                if chave == "status":
                    item.setBackground(QColor(status_bg))
                    item.setForeground(QColor(status_fg))
                    erro_msg = linha.get("erro_renomear_msg")
                    if erro_msg:
                        item.setToolTip(erro_msg)
                if col == 0:
                    item.setData(Qt.UserRole, linha_idx)
                self.tabela.setItem(linha_idx, col, item)
        self.tabela.blockSignals(False)
        self.atualizar_selecao()

    # ── seleção ──────────────────────────────────────────────────────────────

    def _linhas_selecionadas(self):
        indices_linha = {idx.row() for idx in self.tabela.selectedIndexes()}
        resultado = []
        for linha_idx in sorted(indices_linha):
            item = self.tabela.item(linha_idx, 0)
            if item is not None:
                resultado.append(self._linhas[item.data(Qt.UserRole)])
        return resultado

    def atualizar_selecao(self):
        selecionadas = self._linhas_selecionadas()
        prontas = [l for l in selecionadas if l["status"] == "ok"]
        self.lbl_selecao.setText(
            f"{len(selecionadas)} arquivo(s) selecionado(s) "
            f"({len(prontas)} pronto(s) pra renomear)")
        self.btn_renomear.setEnabled(len(prontas) > 0)

    # ── renomear ─────────────────────────────────────────────────────────────

    def renomear_selecionados(self):
        selecionadas = [l for l in self._linhas_selecionadas() if l["status"] == "ok"]
        if not selecionadas:
            QMessageBox.warning(
                self, "Atenção",
                "Selecione pelo menos um arquivo com status "
                "\"✅ Pronto pra renomear\".")
            return

        resposta = QMessageBox.question(
            self, "Renomear arquivos",
            f"Renomear {len(selecionadas)} arquivo(s) selecionado(s)? "
            "Essa ação altera os arquivos na pasta de origem — não é "
            "possível desfazer automaticamente.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if resposta != QMessageBox.Yes:
            return

        self.btn_renomear.setEnabled(False)
        QApplication.processEvents()
        try:
            resultados = renomear(selecionadas)
        finally:
            self.btn_renomear.setEnabled(True)

        # Atualiza cada linha JÁ EXISTENTE em `self._linhas` em vez de
        # reanalisar as pastas do zero — reanalisar faria o arquivo recém
        # renomeado (que não bate mais com nenhuma posição de .CAM, porque
        # já tem o nome novo) aparecer como "Sem .CAM correspondente",
        # parecendo um erro quando na verdade deu certo (bug relatado pelo
        # usuário). `linha` aqui é o MESMO dict guardado em `self._linhas`
        # (não uma cópia — ver `_linhas_selecionadas`), então mutar em
        # lugar já atualiza a lista principal.
        sucesso = 0
        erros = []
        for r in resultados:
            linha = r["linha"]
            if r["sucesso"]:
                sucesso += 1
                linha["status"] = "renomeado"
                linha["caminho_atual"] = r["novo_caminho"]
                linha["arquivo_atual"] = os.path.basename(r["novo_caminho"])
            else:
                linha["status"] = "erro_renomear"
                linha["erro_renomear_msg"] = r["erro"]
                erros.append(f"{linha['arquivo_atual']}: {r['erro']}")

        self._preencher_tabela()

        texto = f"{sucesso} arquivo(s) renomeado(s) com sucesso."
        if erros:
            texto += f" | {len(erros)} erro(s)."
            QMessageBox.warning(
                self, "Alguns arquivos não foram renomeados", "\n".join(erros))
        self.atualizar_status(texto)

    def atualizar_status(self, texto):
        self.lbl_status.setText(texto)
