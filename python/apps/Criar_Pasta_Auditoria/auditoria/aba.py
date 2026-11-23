# -*- coding: utf-8 -*-
"""
Aba "Criar Pasta / Auditoria": cria a estrutura de pastas de um lote a
partir da planilha (com resgate automático da LOTE 9999) e audita a LOTE
9999 contra o que a planilha diz.

FASE 1 desta ferramenta: só as telas "Criar Pastas", "Auditar Lote 9999" e
"Configurações". FASE 2 soma a tela "Buscar Obra / Pacote" (originalmente
entregue como duas telas separadas, "Buscar por Obra" e "Buscar por
Pacote" — unificadas depois numa só, já que eram idênticas em tudo além do
campo de busca), com sua própria base local (auditoria_registros,
recarregada sob demanda pelo botão "🔄 Atualizar Base de Busca" em
Configurações — nunca automaticamente).

Ficou de fora, por escolha, o "auto-refresh" silencioso de 3 em 3 minutos
que o script original tinha (`_tick_auto_atualizacao`): reimportar a
planilha inteira sozinho, em segundo plano, enquanto o usuário está usando
outra tela, é mais fácil de causar confusão (dados mudando "sem motivo")
do que ajudar — o botão manual já cobre a necessidade. Dá pra portar depois
se fizer falta.

Extraído de `cria_pasta_auditoria.py` (customtkinter/Tkinter) — mesma
lógica de tela, mesmo texto, adaptado pros widgets do PyQt5 e à paleta
cinza-industrial do app (`nucleo/estilo.py`).
"""
import os

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton,
    QLineEdit, QFrame, QStackedWidget, QFileDialog, QMessageBox, QCheckBox,
    QScrollArea, QApplication, QTableWidget, QTableWidgetItem, QAbstractItemView,
    QHeaderView,
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QColor

from nucleo.estilo import (COR_PAINEL, COR_BORDA, COR_TEXTO, COR_TEXTO_SUB,
                           COR_VERDE, COR_VERMELHO, COR_DESTAQUE, COR_BG,
                           COR_AMARELO)
from nucleo.logging_config import logger

from auditoria import banco
from auditoria.processador import (
    processar, auditar_lote_9999, mover_pasta_of, verificar_nova_versao,
    importar_planilha_busca, VERSAO_ATUAL,
)
from auditoria.utilitarios import (
    encontrar_arquivo_xlsx, obter_pasta_9999, localizar_pasta_lote_existente,
    NOME_PASTA_9999, formatar_kg, chave_ordenacao, PLACEHOLDER_SEM_PESO,
)

# Cores extras específicas desta aba — nucleo/estilo.py não tem roxo nem um
# âmbar vivo o bastante pra badge de diagnóstico, e o painel de resultado
# usa um tom distinto de COR_PAINEL pra se destacar do fundo da página.
# Mesmo precedente de visualizador/estilo.py, que também define paleta
# própria por cima da base do app.
#
# Ajuste (paleta clara "Papel & Grafite"): COR_SIDEBAR, COR_PAINEL_RESULTADO
# e COR_TOTAL_BG/TEXTO eram tons escuros feitos sob medida pra paleta antiga
# (cinza-industrial) — só reimportar as cores novas de nucleo/estilo.py não
# bastava, porque estas 4 são hardcoded NESTE arquivo, não vêm de lá. Se
# deixasse como estava, a barra lateral e o painel de resultado teriam
# ficado escuros no meio de um app agora claro. Retonalizadas pro claro,
# mantendo a mesma FUNÇÃO de cada uma (barra lateral com tom próprio,
# painel de resultado se destacando do fundo, linha de TOTAL com destaque
# de cor).
COR_ROXO = "#818CF8"
COR_AMBAR = "#F59E0B"
# Variantes mais ESCURAS de COR_ROXO/vermelho, só pra uso como TEXTO de
# corpo em cima de fundo claro (ver `_CORES_DIAGNOSTICO` logo abaixo) — as
# cores de cima (COR_ROXO/COR_AMBAR) continuam servindo pra ícones/badges
# menores onde o contraste não é tão crítico.
COR_ROXO_TEXTO = "#5B4FC4"
COR_ROSA_TEXTO = "#A6296B"
COR_SIDEBAR = "#E4E8ED"
COR_PAINEL_RESULTADO = "#FFFFFF"
# Cores da linha de TOTAL nas tabelas de busca (FASE 2) — antes um azul
# escuro (do script original em ttk); agora um destaque âmbar, mesmo tom de
# COR_AMARELO da paleta nova, pra continuar lendo como "linha especial".
COR_TOTAL_BG = "#DBE8FB"
COR_TOTAL_TEXTO = "#0B3D91"

_ITENS_MENU = [
    ("criar", "📁  Criar Pastas"),
    ("auditoria", "🔍  Auditar Lote 9999"),
    ("buscar", "🔎  Buscar Obra / Pacote"),
    ("config", "⚙️  Configurações"),
]

# Ajuste (reportado pelo usuário com print de tela: linhas alternadas da
# tabela "Auditar Lote 9999" praticamente ilegíveis — texto escuro em cima
# de fundo quase preto): na 1ª passada da troca de paleta (ver seção
# "Paleta visual clara" no CONTINUIDADE.md), este dicionário foi
# deliberadamente deixado com fundos ESCUROS, por ter sido julgado como
# "chip de badge, independente do tema" — julgamento que valeria pra um
# selo pequeno com cor de texto PRÓPRIA, sempre garantida. Só que aqui o
# "fundo" (`fundo`) não é usado num selo pequeno: é o background da CÉLULA
# INTEIRA da coluna "OF" (linha 690 em diante), e essa coluna usa sempre
# `COR_TEXTO` — a cor de texto PADRÃO da página, que também mudou de clara
# (tema antigo) pra escura (tema novo). Fundo escuro + COR_TEXTO agora
# escuro = texto invisível. Corrigido virando os 5 fundos CLAROS (tons
# pastel do próprio tema "Papel & Grafite"), com a cor de destaque de cada
# um escolhida pra continuar legível em cima de fundo claro (ao contrário
# de antes, escolhida pra contrastar com fundo ESCURO).
_CORES_DIAGNOSTICO = {
    "bate":            ("#E9F3EA", COR_TEXTO_SUB),
    "lugar_errado":    ("#FBF0DC", COR_AMARELO),
    "nao_encontrada":  ("#FBE7E4", COR_VERMELHO),
    "sem_registro":    ("#EEEAFB", COR_ROXO_TEXTO),
    "duplicada":       ("#F8DADA", COR_ROSA_TEXTO),
}
_TEXTOS_DIAGNOSTICO = {
    "bate":           "✅ Bate",
    "lugar_errado":   "⚠️ Lugar errado",
    "nao_encontrada": "❌ Não encontrada",
    "sem_registro":   "👻 Sem registro",
    "duplicada":      "🔀 Duplicada",
}


# (chave, rótulo, largura inicial, âncora, é numérico "sujo" — precisa de
# formatar_kg/parse pra ordenar direito) — mesma coluna COLUNAS_PLANILHA do
# script original.
_COLUNAS_PLANILHA = [
    ("lote",        "Lote",            90,  False),
    ("of_trecho",   "OF-Trecho",       110, False),
    ("obra",        "Obra",            80,  False),
    ("trecho",      "Trecho",          70,  False),
    ("subtrecho",   "Subtrecho",       95,  False),
    ("ano_semana",  "Ano-Semana",      110, False),
    ("peso_lic",    "Peso Lic/Lote",   130, False),
    ("prep",        "QTD TT KG PREP",  145, True),
    ("nprep",       "QTD TT KG ÑPREP", 150, True),
    ("data_inicio", "Início Artia",    115, False),
    ("status",      "Status",          110, False),
]
# chave da coluna -> nome do campo em auditoria_registros / sqlite3.Row
_MAPA_CAMPO_BANCO = {
    "lote": "lote", "of_trecho": "of_trecho", "obra": "obra",
    "trecho": "trecho", "subtrecho": "subtrecho", "ano_semana": "ano_semana",
    "peso_lic": "peso_lic_lote", "prep": "qtd_tt_kg_prep", "nprep": "qtd_tt_kg_nprep",
    "data_inicio": "data_inicio_artia", "status": "status",
}


class TabelaPlanilha(QWidget):
    """
    Tabela "chapada" com cara de planilha, usada pelas duas buscas da tela
    "Buscar Obra / Pacote": cabeçalho fixo, linhas zebradas, linha de TOTAL
    destacada no fim (soma de PREP/ÑPREP) e ordenação por clique no
    cabeçalho. Reimplementação em QTableWidget da `TabelaPlanilha` original
    (ttk.Treeview) — mesma lógica de ordenação e mesmo padrão de
    ordenação-por-cabeçalho já usado em conversor/aba.py.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._registros = []
        self._ordenar_reverso = {}

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)

        self.tabela = QTableWidget(0, len(_COLUNAS_PLANILHA))
        self.tabela.setHorizontalHeaderLabels([c[1] for c in _COLUNAS_PLANILHA])
        self.tabela.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tabela.setSelectionMode(QAbstractItemView.NoSelection)
        self.tabela.setAlternatingRowColors(True)
        self.tabela.verticalHeader().setVisible(False)
        self.tabela.horizontalHeader().setStretchLastSection(False)
        self.tabela.horizontalHeader().setMinimumSectionSize(60)
        for col, (_chave, _rotulo, largura, _numerico) in enumerate(_COLUNAS_PLANILHA):
            self.tabela.setColumnWidth(col, largura)
            self.tabela.horizontalHeader().setSectionResizeMode(col, QHeaderView.Interactive)
        self.tabela.setStyleSheet(f"""
            QTableWidget {{
                background:{COR_PAINEL}; alternate-background-color:#F6F7F9;
                color:{COR_TEXTO}; border:1px solid {COR_BORDA}; border-radius:4px;
                gridline-color:{COR_BORDA};
            }}
            QHeaderView::section {{ background:qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #E3E8EE, stop:1 #CDD4DE); color:#000000; font-weight:bold; padding:5px; border:none; border-right:1px solid #98A3B3; border-bottom:1px solid #98A3B3; }}
        """)
        self.tabela.horizontalHeader().sectionClicked.connect(self._ao_clicar_cabecalho)
        lay.addWidget(self.tabela)

    def limpar(self):
        self._registros = []
        self.tabela.setRowCount(0)

    def preencher(self, registros):
        """Recebe uma lista/tupla de sqlite3.Row (ou objetos com __getitem__ por chave)."""
        self._registros = list(registros)
        self._redesenhar(self._registros)

    def _redesenhar(self, registros):
        self.tabela.setRowCount(0)
        total_prep = 0.0
        total_nprep = 0.0
        for registro in registros:
            total_prep += registro["qtd_tt_kg_prep"] or 0
            total_nprep += registro["qtd_tt_kg_nprep"] or 0
            valores = [
                registro["lote"], registro["of_trecho"], registro["obra"],
                registro["trecho"], registro["subtrecho"], registro["ano_semana"],
                registro["peso_lic_lote"] or PLACEHOLDER_SEM_PESO,
                formatar_kg(registro["qtd_tt_kg_prep"]), formatar_kg(registro["qtd_tt_kg_nprep"]),
                registro["data_inicio_artia"], registro["status"] or PLACEHOLDER_SEM_PESO,
            ]
            self._adicionar_linha(valores)
        if registros:
            valores_total = [
                "", "", "", "", "", "", "TOTAL",
                formatar_kg(total_prep), formatar_kg(total_nprep), "", "",
            ]
            self._adicionar_linha(valores_total, total=True)

    def _adicionar_linha(self, valores, total=False):
        linha_idx = self.tabela.rowCount()
        self.tabela.insertRow(linha_idx)
        for col, valor in enumerate(valores):
            item = QTableWidgetItem(str(valor))
            item.setTextAlignment(Qt.AlignCenter)
            if total:
                item.setBackground(QColor(COR_TOTAL_BG))
                item.setForeground(QColor(COR_TOTAL_TEXTO))
                fonte = item.font()
                fonte.setBold(True)
                item.setFont(fonte)
            self.tabela.setItem(linha_idx, col, item)

    def _ao_clicar_cabecalho(self, indice_coluna):
        if not self._registros:
            return
        chave = _COLUNAS_PLANILHA[indice_coluna][0]
        campo = _MAPA_CAMPO_BANCO[chave]
        reverso = self._ordenar_reverso.get(chave, False)

        def chave_final(registro):
            valor = registro[campo]
            if campo in ("qtd_tt_kg_prep", "qtd_tt_kg_nprep"):
                return valor if valor is not None else -1
            if campo in ("obra", "lote", "trecho", "subtrecho"):
                return chave_ordenacao(str(valor))
            return str(valor or "").lower()

        registros_ordenados = sorted(self._registros, key=chave_final, reverse=reverso)
        self._ordenar_reverso[chave] = not reverso
        self._redesenhar(registros_ordenados)


class AbaAuditoria(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        banco.inicializar_banco()
        self.botoes_menu = {}
        self.paginas = {}
        self._auditoria_resultado = None
        self._auditoria_mostrar_tudo = False
        self.setup_ui()
        self._carregar_caminhos_salvos()
        QTimer.singleShot(600, self._verificar_nova_versao_ui)

    # ── layout geral ─────────────────────────────────────────────────────────

    def setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        header = QFrame()
        header.setFixedHeight(48)
        header.setStyleSheet(f"background:#E4E8ED; border-bottom:2px solid #0B3D91;")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(16, 0, 16, 0)
        lbl_titulo = QLabel("📁  Criador de Pastas / Auditoria")
        lbl_titulo.setStyleSheet(f"color:{COR_TEXTO}; font-size:15px; font-weight:bold;")
        lbl_sub = QLabel("Organização de Lotes — SISTEMA - PPCPM")
        lbl_sub.setStyleSheet(f"color:{COR_TEXTO_SUB}; font-size:11px;")
        hl.addWidget(lbl_titulo)
        hl.addStretch()
        hl.addWidget(lbl_sub)
        root.addWidget(header)

        corpo = QWidget()
        corpo_layout = QHBoxLayout(corpo)
        corpo_layout.setContentsMargins(0, 0, 0, 0)
        corpo_layout.setSpacing(0)
        root.addWidget(corpo, 1)

        corpo_layout.addWidget(self._montar_menu(), 0)
        self.stack = QStackedWidget()
        corpo_layout.addWidget(self.stack, 1)

        self.paginas["criar"] = self._pagina_criar_pastas()
        self.paginas["auditoria"] = self._pagina_auditoria()
        self.paginas["buscar"] = self._pagina_buscar()
        self.paginas["config"] = self._pagina_configuracoes()
        for chave in ("criar", "auditoria", "buscar", "config"):
            self.stack.addWidget(self.paginas[chave])

        self._mostrar_pagina("criar")

    def _montar_menu(self):
        menu = QFrame()
        menu.setFixedWidth(200)
        menu.setStyleSheet(f"background:{COR_SIDEBAR}; border-right:1px solid {COR_BORDA};")
        lay = QVBoxLayout(menu)
        lay.setContentsMargins(10, 18, 10, 10)
        lay.setSpacing(2)
        lbl = QLabel("MENU")
        lbl.setStyleSheet(f"color:{COR_TEXTO_SUB}; font-size:10px; font-weight:bold;")
        lay.addWidget(lbl)
        lay.addSpacing(6)
        for chave, rotulo in _ITENS_MENU:
            btn = QPushButton(rotulo)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(self._estilo_botao_menu(False))
            btn.clicked.connect(lambda _, c=chave: self._mostrar_pagina(c))
            lay.addWidget(btn)
            self.botoes_menu[chave] = btn
        lay.addStretch()
        return menu

    def _estilo_botao_menu(self, ativo):
        # cor_texto era "#F1F5F9"/"#CBD5E1" (cinza quase branco) -- certo pra
        # paleta escura antiga, ilegível na barra lateral clara de agora.
        # Trocado pro texto escuro padrão do tema (destacado quando ativo).
        cor_fundo = COR_PAINEL if ativo else "transparent"
        cor_texto = COR_DESTAQUE if ativo else COR_TEXTO_SUB
        return (
            f"QPushButton {{ text-align:left; padding:10px 12px; border-radius:4px; "
            f"background:{cor_fundo}; color:{cor_texto}; font-size:12px; border:none; }}"
            f"QPushButton:hover {{ background:{COR_PAINEL}; }}"
        )

    def _mostrar_pagina(self, chave):
        self.stack.setCurrentWidget(self.paginas[chave])
        for k, btn in self.botoes_menu.items():
            btn.setStyleSheet(self._estilo_botao_menu(k == chave))

    def _limpar_layout(self, layout):
        """Remove todos os widgets/sub-layouts de `layout` sem deixar
        'fantasmas' na tela (mesmo padrão de corte/dialogos.py::PainelMedidas)."""
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)
                w.deleteLater()
            else:
                sub = item.layout()
                if sub:
                    self._limpar_layout(sub)

    # ── PÁGINA: Criar Pastas ────────────────────────────────────────────────

    def _pagina_criar_pastas(self):
        pagina = QWidget()
        lay = QVBoxLayout(pagina)
        lay.setContentsMargins(36, 24, 36, 24)
        lay.setSpacing(4)

        titulo = QLabel("Criar Pastas do Lote")
        titulo.setStyleSheet(f"color:{COR_TEXTO}; font-size:18px; font-weight:bold;")
        lay.addWidget(titulo)

        desc = QLabel(
            "Lê a planilha configurada, cria a estrutura de pastas do lote e resgata "
            "automaticamente as obras que já estiverem na LOTE 9999."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet(f"color:{COR_TEXTO_SUB}; font-size:11px;")
        lay.addWidget(desc)
        lay.addSpacing(14)

        lbl_lote = QLabel("🔢  Número do LOTE:")
        lbl_lote.setStyleSheet(f"color:{COR_TEXTO}; font-size:12px;")
        lay.addWidget(lbl_lote)

        linha_lote = QHBoxLayout()
        self.entry_lote = QLineEdit()
        self.entry_lote.setPlaceholderText("ex: 650")
        self.entry_lote.setFixedWidth(220)
        linha_lote.addWidget(self.entry_lote)
        linha_lote.addStretch()
        lay.addLayout(linha_lote)
        lay.addSpacing(16)

        linha_btn = QHBoxLayout()
        self.btn_criar = QPushButton("▶  Criar Pastas")
        self.btn_criar.setObjectName("btn_processar")
        self.btn_criar.clicked.connect(self._executar_criar)
        linha_btn.addWidget(self.btn_criar)
        linha_btn.addStretch()
        lay.addLayout(linha_btn)
        lay.addSpacing(18)

        self.frame_resultado = QFrame()
        self.frame_resultado.setStyleSheet(f"background:{COR_PAINEL_RESULTADO}; border-radius:4px;")
        rl = QVBoxLayout(self.frame_resultado)
        rl.setContentsMargins(18, 14, 18, 14)
        lbl_res = QLabel("RESULTADO")
        lbl_res.setStyleSheet(f"color:{COR_TEXTO_SUB}; font-size:11px; font-weight:bold;")
        rl.addWidget(lbl_res)

        cards_lay = QHBoxLayout()
        self.card_resgatadas = self._criar_card("📦", "Resgatadas da 9999", COR_ROXO)
        self.card_criadas = self._criar_card("📁", "Criadas do zero", COR_VERDE)
        self.card_existentes = self._criar_card("✅", "Já existentes", COR_TEXTO_SUB)
        cards_lay.addWidget(self.card_resgatadas["card"])
        cards_lay.addWidget(self.card_criadas["card"])
        cards_lay.addWidget(self.card_existentes["card"])
        rl.addLayout(cards_lay)

        self.label_resultado_detalhe = QLabel("Preencha o número do lote e clique em \"Criar Pastas\".")
        self.label_resultado_detalhe.setWordWrap(True)
        self.label_resultado_detalhe.setStyleSheet(f"color:{COR_TEXTO_SUB}; font-size:11px;")
        rl.addWidget(self.label_resultado_detalhe)

        self.label_aviso = QLabel("")
        self.label_aviso.setWordWrap(True)
        self.label_aviso.setStyleSheet(f"color:{COR_AMBAR}; font-size:10px; font-weight:bold;")
        rl.addWidget(self.label_aviso)

        lay.addWidget(self.frame_resultado)
        lay.addStretch()
        return pagina

    def _criar_card(self, icone, rotulo, cor):
        card = QFrame()
        card.setStyleSheet(f"background:{COR_PAINEL}; border-radius:4px;")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(16, 14, 16, 14)
        lbl_valor = QLabel(f"{icone}  —")
        lbl_valor.setStyleSheet(f"color:{cor}; font-size:22px; font-weight:bold;")
        lbl_rotulo = QLabel(rotulo)
        lbl_rotulo.setStyleSheet(f"color:{COR_TEXTO_SUB}; font-size:10px;")
        cl.addWidget(lbl_valor)
        cl.addWidget(lbl_rotulo)
        return {"card": card, "label_valor": lbl_valor, "icone": icone}

    def _executar_criar(self):
        diretorio = banco.carregar_config("caminho_planilha")
        destino = banco.carregar_config("caminho_destino")
        raizes = banco.listar_raizes()
        lote = self.entry_lote.text().strip()
        if not diretorio or not destino:
            QMessageBox.warning(
                self, "Configuração incompleta",
                "Defina a Planilha e o Destino na tela de Configurações antes de continuar.")
            self._mostrar_pagina("config")
            return
        if not lote:
            QMessageBox.warning(self, "Campo obrigatório", "Informe o número do LOTE.")
            return
        self.btn_criar.setEnabled(False)
        self.btn_criar.setText("⏳  Processando...")
        self._resultado_processando()
        QApplication.processEvents()
        resultado = processar(diretorio, lote, destino, raizes)
        self.btn_criar.setEnabled(True)
        self.btn_criar.setText("▶  Criar Pastas")
        if not resultado["ok"]:
            self._resultado_erro(resultado["msg"])
            QMessageBox.critical(self, "Erro", resultado["msg"])
            return
        self._atualizar_resultado_criacao(resultado, lote)

    def _resultado_processando(self):
        for card in (self.card_resgatadas, self.card_criadas, self.card_existentes):
            card["label_valor"].setText(f"{card['icone']}  …")
        self.label_resultado_detalhe.setText("Processando, aguarde...")
        self.label_resultado_detalhe.setStyleSheet(f"color:{COR_TEXTO_SUB}; font-size:11px;")
        self.label_aviso.setText("")

    def _resultado_erro(self, msg):
        for card in (self.card_resgatadas, self.card_criadas, self.card_existentes):
            card["label_valor"].setText(f"{card['icone']}  —")
        self.label_resultado_detalhe.setText(f"❌ {msg}")
        self.label_resultado_detalhe.setStyleSheet(f"color:{COR_VERMELHO}; font-size:11px;")
        self.label_aviso.setText("")

    def _atualizar_resultado_criacao(self, r, lote):
        self.card_resgatadas["label_valor"].setText(f"📦  {r['resgatadas']}")
        self.card_criadas["label_valor"].setText(f"📁  {r['criadas']}")
        self.card_existentes["label_valor"].setText(f"✅  {r['existentes']}")
        if r["vazio"]:
            self.label_resultado_detalhe.setText(
                f"⚠️  Nenhuma OF encontrada na planilha para o LOTE {lote}. Verifique o número informado.")
            self.label_resultado_detalhe.setStyleSheet(f"color:{COR_AMBAR}; font-size:11px;")
        else:
            self.label_resultado_detalhe.setText(
                f"LOTE {lote}  •  {r['total_ofs']} OF(s) na planilha  →  pasta criada em:\n{r['pasta_lote']}\n"
                f"Banco de dados: {r['inseridos_db']} registro(s) novo(s), {r['ignorados_db']} já existente(s)."
            )
            self.label_resultado_detalhe.setStyleSheet(f"color:{COR_TEXTO}; font-size:11px;")
        avisos = []
        if r["aviso_9999"]:
            avisos.append(f"ℹ️  {r['aviso_9999']}")
        if r["falhas_mover"]:
            avisos.append("⚠️  Falha ao mover da 9999 (pasta vazia criada no lugar): " + "; ".join(r["falhas_mover"]))
        self.label_aviso.setText("\n".join(avisos))

    # ── PÁGINA: Auditoria ────────────────────────────────────────────────────

    def _pagina_auditoria(self):
        pagina = QWidget()
        lay = QVBoxLayout(pagina)
        lay.setContentsMargins(36, 24, 36, 24)
        lay.setSpacing(4)

        titulo = QLabel("Auditar Lote 9999")
        titulo.setStyleSheet(f"color:{COR_TEXTO}; font-size:18px; font-weight:bold;")
        lay.addWidget(titulo)

        desc = QLabel(
            "Compara as obras marcadas como LOTE 9999 na planilha com o que realmente "
            "existe na pasta física LOTE 9999, e mostra onde cada uma está de verdade."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet(f"color:{COR_TEXTO_SUB}; font-size:11px;")
        lay.addWidget(desc)
        lay.addSpacing(14)

        linha_btn = QHBoxLayout()
        self.btn_auditar = QPushButton("🔍  Rodar Auditoria")
        self.btn_auditar.setObjectName("btn_limpar")
        self.btn_auditar.clicked.connect(self._executar_auditoria)
        linha_btn.addWidget(self.btn_auditar)
        linha_btn.addStretch()
        lay.addLayout(linha_btn)

        lbl_hint = QLabel("Usa a Planilha e os Diretórios raiz definidos em Configurações.")
        lbl_hint.setStyleSheet(f"color:{COR_TEXTO_SUB}; font-size:10px;")
        lay.addWidget(lbl_hint)
        lay.addSpacing(10)

        self.scroll_auditoria = QScrollArea()
        self.scroll_auditoria.setWidgetResizable(True)
        self.scroll_auditoria.setStyleSheet("QScrollArea { border: none; }")
        self.container_auditoria = QWidget()
        self.layout_auditoria = QVBoxLayout(self.container_auditoria)
        self.layout_auditoria.setContentsMargins(0, 0, 0, 0)
        self.scroll_auditoria.setWidget(self.container_auditoria)
        lay.addWidget(self.scroll_auditoria, 1)

        label_placeholder = QLabel("Os resultados da auditoria aparecerão aqui.")
        label_placeholder.setStyleSheet(f"color:{COR_TEXTO_SUB}; font-size:11px;")
        self.layout_auditoria.addWidget(label_placeholder)
        self.layout_auditoria.addStretch()

        return pagina

    def _executar_auditoria(self):
        diretorio = banco.carregar_config("caminho_planilha")
        raizes = banco.listar_raizes()
        if not diretorio or not raizes:
            QMessageBox.warning(
                self, "Configuração incompleta",
                "Defina a Planilha e cadastre ao menos um Diretório raiz na tela de "
                "Configurações antes de auditar.")
            self._mostrar_pagina("config")
            return
        self.btn_auditar.setEnabled(False)
        self.btn_auditar.setText("⏳  Auditando...")
        QApplication.processEvents()
        resultado = auditar_lote_9999(diretorio, raizes)
        self.btn_auditar.setEnabled(True)
        self.btn_auditar.setText("🔍  Rodar Auditoria")
        if not resultado["ok"]:
            QMessageBox.critical(self, "Erro na auditoria", resultado["msg"])
            return
        self._auditoria_resultado = resultado
        self._exibir_resultado_auditoria(resultado)

    def _exibir_resultado_auditoria(self, r):
        self._limpar_layout(self.layout_auditoria)

        resumo = QFrame()
        resumo.setStyleSheet(f"background:{COR_PAINEL_RESULTADO}; border-radius:4px;")
        rl = QVBoxLayout(resumo)
        rl.setContentsMargins(14, 10, 14, 10)
        rl.setSpacing(2)

        texto_reconc = (
            f"📄 {r['total_linhas']} linha(s) na planilha   →   "
            f"🔢 {r['total_unicas']} OF(s) única(s)   →   "
            f"📁 {r['total_pastas_fisicas']} pasta(s) física(s) na {NOME_PASTA_9999}"
        )
        lbl1 = QLabel(texto_reconc)
        lbl1.setWordWrap(True)
        lbl1.setStyleSheet(f"color:{COR_TEXTO}; font-size:11px; font-weight:bold;")
        rl.addWidget(lbl1)

        texto_status = (
            f"✅ Bate: {len(r['bate'])}     "
            f"⚠️ Lugar errado: {len(r['lugar_errado'])}     "
            f"❌ Não encontradas: {len(r['nao_encontradas'])}     "
            f"👻 Sem registro na planilha: {len(r['sem_registro'])}     "
            f"🔁 Duplicadas na planilha: {len(r['duplicadas'])}     "
            f"🔀 Duplicadas físicas: {len(r['duplicadas_fisicas'])}"
        )
        lbl2 = QLabel(texto_status)
        lbl2.setWordWrap(True)
        lbl2.setStyleSheet(f"color:{COR_TEXTO_SUB}; font-size:11px;")
        rl.addWidget(lbl2)
        if r["duplicadas_fisicas"]:
            lbl_alerta = QLabel(
                "🔀 Duplicidade física é a MESMA OF com pasta em mais de um "
                "lugar ao mesmo tempo (ex.: uma cópia esquecida na LOTE 9999 "
                "e outra já dentro do lote real) — resolva na mão pelos "
                "botões da linha \"🔀 Duplicada\" abaixo, nada é movido "
                "automaticamente nesse caso."
            )
            lbl_alerta.setWordWrap(True)
            lbl_alerta.setStyleSheet(f"color:{COR_VERMELHO}; font-size:10px; font-weight:bold;")
            rl.addWidget(lbl_alerta)

        todas_9999_ok = all(info["existe"] for info in r["raizes_info"])
        cor_diag = COR_VERDE if todas_9999_ok else COR_AMBAR
        texto_diag = (
            f"Raízes cadastradas: {len(r['raizes_info'])}   |   "
            f"Pastas de mês vistas: {r['qtd_pastas_mes_encontradas']}   |   "
            f"Pastas LOTE escaneadas: {r['total_lotes_escaneados']}"
        )
        lbl3 = QLabel(texto_diag)
        lbl3.setWordWrap(True)
        lbl3.setStyleSheet(f"color:{cor_diag}; font-size:9px;")
        rl.addWidget(lbl3)

        for info in r["raizes_info"]:
            status = "✅ LOTE 9999 encontrada" if info["existe"] else "⚠️ sem LOTE 9999"
            lbl = QLabel(f"   {status}  —  {info['raiz']}")
            lbl.setWordWrap(True)
            lbl.setStyleSheet(f"color:{COR_VERDE if info['existe'] else COR_AMBAR}; font-size:9px;")
            rl.addWidget(lbl)

        if r["raizes_invalidas"]:
            lbl = QLabel(
                f"🚫 {len(r['raizes_invalidas'])} raiz(es) cadastrada(s) não foram encontrada(s) "
                "no disco e ficaram de fora desta auditoria: " + "; ".join(r["raizes_invalidas"])
            )
            lbl.setWordWrap(True)
            lbl.setStyleSheet(f"color:{COR_VERMELHO}; font-size:9px; font-weight:bold;")
            rl.addWidget(lbl)

        if r["pastas_com_erro"]:
            texto_erro = (
                f"🚫 {len(r['pastas_com_erro'])} pasta(s) não puderam ser lidas na varredura "
                f"— cobertura pode estar incompleta: " + "; ".join(r["pastas_com_erro"][:3])
                + (" ..." if len(r["pastas_com_erro"]) > 3 else "")
            )
            lbl = QLabel(texto_erro)
            lbl.setWordWrap(True)
            lbl.setStyleSheet(f"color:{COR_VERMELHO}; font-size:9px; font-weight:bold;")
            rl.addWidget(lbl)

        self.layout_auditoria.addWidget(resumo)

        filtro_lay = QHBoxLayout()
        self.chk_mostrar_tudo = QCheckBox("Mostrar também as que batem (não só os problemas)")
        self.chk_mostrar_tudo.setChecked(self._auditoria_mostrar_tudo)
        self.chk_mostrar_tudo.stateChanged.connect(self._ao_alternar_mostrar_tudo)
        filtro_lay.addWidget(self.chk_mostrar_tudo)
        lbl_legenda = QLabel("   ✂️ move direto pro lote que a planilha aponta   ·   📂 deixa você escolher a pasta")
        lbl_legenda.setStyleSheet(f"color:{COR_TEXTO_SUB}; font-size:9px;")
        filtro_lay.addWidget(lbl_legenda)
        filtro_lay.addStretch()
        self.layout_auditoria.addLayout(filtro_lay)

        self.tabela_container = QWidget()
        self.tabela_layout = QGridLayout(self.tabela_container)
        self.tabela_layout.setHorizontalSpacing(6)
        self.tabela_layout.setVerticalSpacing(3)
        self.layout_auditoria.addWidget(self.tabela_container)
        self.layout_auditoria.addStretch()

        self._preencher_tabela_auditoria(r["linhas"], self._auditoria_mostrar_tudo)

    def _ao_alternar_mostrar_tudo(self, estado):
        self._auditoria_mostrar_tudo = (estado == Qt.Checked)
        if self._auditoria_resultado:
            self._preencher_tabela_auditoria(self._auditoria_resultado["linhas"], self._auditoria_mostrar_tudo)

    def _preencher_tabela_auditoria(self, linhas, mostrar_tudo):
        self._limpar_layout(self.tabela_layout)
        linhas_exibir = linhas if mostrar_tudo else [l for l in linhas if l["diagnostico"] != "bate"]

        colunas = ["OF", "Lote (planilha)", "Pasta encontrada em", "Diagnóstico", "Ação"]
        pesos = [2, 1, 5, 2, 3]
        for i, peso in enumerate(pesos):
            self.tabela_layout.setColumnStretch(i, peso)
        for i, col in enumerate(colunas):
            lbl = QLabel(col)
            lbl.setStyleSheet(f"color:{COR_TEXTO_SUB}; font-size:11px; font-weight:bold;")
            self.tabela_layout.addWidget(lbl, 0, i)

        if not linhas_exibir:
            lbl = QLabel("Nenhum item para mostrar com esse filtro. 🎉")
            lbl.setStyleSheet(f"color:{COR_TEXTO_SUB}; font-size:11px;")
            self.tabela_layout.addWidget(lbl, 1, 0, 1, 5)
            return

        for idx, linha in enumerate(linhas_exibir, start=1):
            diagnostico = linha["diagnostico"]
            fundo, cor_destaque = _CORES_DIAGNOSTICO[diagnostico]
            of_texto = linha["of"]
            if linha["n_ocorrencias"] > 1:
                of_texto += f"  🔁×{linha['n_ocorrencias']}"
            lote_texto = linha["lote_planilha"] or "—"
            lugar_texto = linha["lugar"] or "—"
            diag_texto = _TEXTOS_DIAGNOSTICO[diagnostico]
            valores = [of_texto, lote_texto, lugar_texto, diag_texto]
            for i, valor in enumerate(valores):
                cor_texto = cor_destaque if i in (1, 2, 3) and diagnostico != "bate" else COR_TEXTO
                lbl = QLabel(valor)
                lbl.setWordWrap(True)
                lbl.setStyleSheet(
                    f"background:{fundo}; color:{cor_texto}; font-size:11px; "
                    f"border-radius:4px; padding:5px 6px;"
                )
                self.tabela_layout.addWidget(lbl, idx, i)

            caminho_atual = linha.get("caminho_atual")
            celula = QFrame()
            celula.setStyleSheet(f"background:{fundo}; border-radius:4px;")
            cel_lay = QVBoxLayout(celula)
            cel_lay.setContentsMargins(6, 4, 6, 4)
            cel_lay.setSpacing(3)
            if diagnostico == "duplicada":
                # Nunca escolhe sozinho qual cópia é a certa — mostra um
                # botão "Mover para..." por cópia encontrada, pra decidir
                # na mão qual fica e pra onde vai. Não oferece "✂️ Mover
                # automático" aqui de propósito.
                locais = linha.get("locais_duplicados") or []
                for i, loc in enumerate(locais, start=1):
                    lbl_local = QLabel(f"📍 Cópia {i}: {loc['lugar']}")
                    lbl_local.setWordWrap(True)
                    lbl_local.setStyleSheet(f"color:{COR_TEXTO_SUB}; font-size:9px;")
                    cel_lay.addWidget(lbl_local)
                    btn_copia = QPushButton(f"📂 Mover cópia {i} para...")
                    btn_copia.setFixedHeight(24)
                    btn_copia.setStyleSheet(self._estilo_botao_acao())
                    btn_copia.clicked.connect(
                        lambda _, c=loc["caminho"]: self._mover_pasta_manual_ui({"caminho_atual": c}))
                    cel_lay.addWidget(btn_copia)
            elif caminho_atual and diagnostico != "bate":
                lote_alvo = linha.get("lote_planilha")
                if lote_alvo:
                    btn_auto = QPushButton(f"✂️ Mover p/ LOTE {lote_alvo}")
                    btn_auto.setFixedHeight(26)
                    btn_auto.setStyleSheet(self._estilo_botao_acao())
                    btn_auto.clicked.connect(lambda _, l=linha: self._mover_pasta_auto(l))
                    cel_lay.addWidget(btn_auto)
                btn_manual = QPushButton("📂 Mover para...")
                btn_manual.setFixedHeight(26)
                btn_manual.setStyleSheet(self._estilo_botao_acao())
                btn_manual.clicked.connect(lambda _, l=linha: self._mover_pasta_manual_ui(l))
                cel_lay.addWidget(btn_manual)
            else:
                lbl_vazio = QLabel("—")
                lbl_vazio.setStyleSheet(f"color:{COR_TEXTO_SUB}; font-size:10px;")
                cel_lay.addWidget(lbl_vazio)
            self.tabela_layout.addWidget(celula, idx, 4)

    def _estilo_botao_acao(self):
        # hover era "#475569" (cinza-escuro) -- ficava certo escurecendo em
        # cima do COR_BORDA escuro antigo; na paleta clara isso criava um
        # quadrado escuro com o MESMO texto escuro em cima (ilegível). Hover
        # agora só aprofunda o próprio tom claro de COR_BORDA.
        return (
            f"QPushButton {{ background:{COR_BORDA}; color:{COR_TEXTO}; font-size:10px; "
            f"border-radius:4px; border:none; }}"
            f"QPushButton:hover {{ background:#B8B8B8; }}"
        )

    def _mover_pasta_auto(self, linha):
        """
        Botão "✂️ Mover p/ LOTE X": corta a pasta direto pro lote que a
        planilha aponta (linha["lote_planilha"]), sem perguntar pra onde —
        só pede uma confirmação final antes de mover de verdade.
        """
        caminho_atual = linha.get("caminho_atual")
        lote_destino = linha.get("lote_planilha")
        if not caminho_atual or not os.path.isdir(caminho_atual):
            QMessageBox.critical(
                self, "Pasta não encontrada",
                "A pasta de origem não foi encontrada no disco — talvez já tenha sido movida "
                "ou renomeada. Rode a auditoria de novo pra atualizar a lista.")
            return
        if not lote_destino:
            QMessageBox.critical(
                self, "Sem lote de destino",
                "Esta linha não tem um lote de destino conhecido — use \"Mover para...\".")
            return
        raizes = banco.listar_raizes()
        pasta_destino = localizar_pasta_lote_existente(raizes, lote_destino)
        vai_criar = False
        if not pasta_destino:
            caminho_destino_padrao = banco.carregar_config("caminho_destino")
            if not caminho_destino_padrao or not os.path.isdir(caminho_destino_padrao):
                QMessageBox.critical(
                    self, "Pasta do lote não encontrada",
                    f"Não encontrei nenhuma pasta \"LOTE {lote_destino}\" nas raízes cadastradas, e o "
                    "Destino (pasta do mês) não está configurado pra criar uma nova ali.\n\n"
                    "Configure o Destino em Configurações, ou use \"Mover para...\" pra escolher o lugar na mão.")
                return
            pasta_destino = os.path.join(caminho_destino_padrao, f"LOTE {str(lote_destino).strip()}")
            vai_criar = True
        aviso_nova = "\n(essa pasta ainda não existe — será criada)" if vai_criar else ""
        resposta = QMessageBox.question(
            self, "Confirmar movimentação",
            f"Mover:\n{caminho_atual}\n\npara:\n{pasta_destino}{aviso_nova}\n\nConfirma?",
            QMessageBox.Yes | QMessageBox.No)
        if resposta != QMessageBox.Yes:
            return
        resultado = mover_pasta_of(caminho_atual, pasta_destino)
        if resultado["ok"]:
            QMessageBox.information(self, "Pasta movida", resultado["msg"])
            self._executar_auditoria()
        else:
            QMessageBox.critical(self, "Não foi possível mover", resultado["msg"])

    def _mover_pasta_manual_ui(self, linha):
        """Botão "📂 Mover para...": pergunta pro usuário em qual pasta colocar a OF."""
        caminho_atual = linha.get("caminho_atual")
        if not caminho_atual or not os.path.isdir(caminho_atual):
            QMessageBox.critical(
                self, "Pasta não encontrada",
                "A pasta de origem não foi encontrada no disco — talvez já tenha sido movida "
                "ou renomeada. Rode a auditoria de novo pra atualizar a lista.")
            return
        pasta_destino = QFileDialog.getExistingDirectory(
            self, "Selecione a pasta onde a OF deve ficar (ela será colocada dentro dela)")
        if not pasta_destino:
            return
        resposta = QMessageBox.question(
            self, "Confirmar movimentação",
            f"Mover:\n{caminho_atual}\n\npara dentro de:\n{pasta_destino}\n\nConfirma?",
            QMessageBox.Yes | QMessageBox.No)
        if resposta != QMessageBox.Yes:
            return
        resultado = mover_pasta_of(caminho_atual, pasta_destino)
        if resultado["ok"]:
            QMessageBox.information(self, "Pasta movida", resultado["msg"])
            self._executar_auditoria()
        else:
            QMessageBox.critical(self, "Não foi possível mover", resultado["msg"])

    # ── PÁGINA: Buscar (Obra / Pacote) ──────────────────────────────────────
    # Unificada a partir de duas páginas separadas ("Buscar por Obra" e
    # "Buscar por Pacote") que eram idênticas em tudo — mesmo título/tabela/
    # resultado, só um campo de busca e uma consulta ao banco diferentes —
    # a ponto de fazer mais sentido serem os dois campos de uma tela só, com
    # um resultado compartilhado embaixo (o que você buscar por último é o
    # que aparece na tabela).

    def _pagina_buscar(self):
        pagina = QWidget()
        lay = QVBoxLayout(pagina)
        lay.setContentsMargins(36, 24, 36, 24)
        lay.setSpacing(4)

        titulo = QLabel("Buscar Obra / Pacote")
        titulo.setStyleSheet(f"color:{COR_TEXTO}; font-size:18px; font-weight:bold;")
        lay.addWidget(titulo)
        lay.addSpacing(14)

        # campo Obra
        lbl_obra = QLabel("Por obra")
        lbl_obra.setStyleSheet(f"color:{COR_TEXTO}; font-size:12px; font-weight:bold;")
        lay.addWidget(lbl_obra)
        desc_obra = QLabel(
            "Só o número da obra soma todos os trechos/pacotes dela; o código completo "
            "(ex: 1956-2-01) mostra um trecho específico."
        )
        desc_obra.setWordWrap(True)
        desc_obra.setStyleSheet(f"color:{COR_TEXTO_SUB}; font-size:11px;")
        lay.addWidget(desc_obra)
        lay.addSpacing(4)

        linha_obra = QHBoxLayout()
        self.entry_obra = QLineEdit()
        self.entry_obra.setPlaceholderText("ex: 1956  ou  1956-2-01")
        self.entry_obra.returnPressed.connect(self._buscar_obra)
        linha_obra.addWidget(self.entry_obra, 1)
        btn_buscar_obra = QPushButton("🔍 Buscar Obra")
        btn_buscar_obra.setObjectName("btn_processar")
        btn_buscar_obra.setFixedWidth(140)
        btn_buscar_obra.clicked.connect(self._buscar_obra)
        linha_obra.addWidget(btn_buscar_obra)
        lay.addLayout(linha_obra)
        lay.addSpacing(16)

        # campo Pacote
        lbl_pacote = QLabel("Por pacote / lote")
        lbl_pacote.setStyleSheet(f"color:{COR_TEXTO}; font-size:12px; font-weight:bold;")
        lay.addWidget(lbl_pacote)
        desc_pacote = QLabel("Informe o número do lote/pacote para ver todas as obras e trechos dele.")
        desc_pacote.setWordWrap(True)
        desc_pacote.setStyleSheet(f"color:{COR_TEXTO_SUB}; font-size:11px;")
        lay.addWidget(desc_pacote)
        lay.addSpacing(4)

        linha_pacote = QHBoxLayout()
        self.entry_pacote = QLineEdit()
        self.entry_pacote.setPlaceholderText("ex: 427")
        self.entry_pacote.returnPressed.connect(self._buscar_pacote)
        linha_pacote.addWidget(self.entry_pacote, 1)
        btn_buscar_pacote = QPushButton("🔍 Buscar Pacote")
        btn_buscar_pacote.setObjectName("btn_processar")
        btn_buscar_pacote.setFixedWidth(140)
        btn_buscar_pacote.clicked.connect(self._buscar_pacote)
        linha_pacote.addWidget(btn_buscar_pacote)
        lay.addLayout(linha_pacote)
        lay.addSpacing(12)

        self.info_busca = QLabel("Faça uma busca para ver o resumo aqui.")
        self.info_busca.setWordWrap(True)
        self.info_busca.setStyleSheet(f"color:{COR_TEXTO_SUB}; font-size:11px;")
        lay.addWidget(self.info_busca)
        lay.addSpacing(8)

        self.tabela_busca = TabelaPlanilha()
        lay.addWidget(self.tabela_busca, 1)
        return pagina

    def _tratar_busca_vazia(self, mensagem_especifica):
        """
        Chamado quando uma busca (obra, OF-Trecho ou pacote) não encontra
        nenhum registro. Se a base de busca inteira estiver vazia (ninguém
        clicou em "🔄 Atualizar Base de Busca" ainda nesta sessão), mostra
        uma dica bem mais direta que o genérico "nada encontrado" — essa
        confusão específica já aconteceu de verdade (usuário testou e
        "não encontrava obra e pacote"; a causa era só a base nunca ter
        sido carregada, não um valor errado).
        """
        self.tabela_busca.limpar()
        if banco.contar_registros_busca() == 0:
            QMessageBox.warning(
                self, "Base de busca vazia",
                "A base de busca ainda não foi carregada nesta sessão.\n\n"
                "Vá em Configurações e clique em \"🔄 Atualizar Base de Busca\" "
                "antes de pesquisar.")
            self.info_busca.setText(
                "⚠ Base de busca vazia — clique em \"🔄 Atualizar Base de Busca\" em Configurações.")
        else:
            QMessageBox.information(self, "Nada encontrado", mensagem_especifica)
            self.info_busca.setText("Nenhum registro encontrado.")

    def _buscar_obra(self):
        valor = self.entry_obra.text().strip()
        if not valor:
            QMessageBox.warning(self, "Atenção", "Informe a obra ou o código OF-TRECHO.")
            return
        # código completo (com hífen) -> busca um OF-TRECHO específico
        if "-" in valor:
            registro = banco.buscar_por_of_trecho(valor)
            if not registro:
                self._tratar_busca_vazia(f"Nenhum registro para o OF-TRECHO {valor}.")
                return
            self.info_busca.setText(
                f"Lote {registro['lote']}   ·   "
                f"PREP: {formatar_kg(registro['qtd_tt_kg_prep'])}   ·   "
                f"ÑPREP: {formatar_kg(registro['qtd_tt_kg_nprep'])}"
            )
            self.tabela_busca.preencher([registro])
            return
        # só número -> agrega todos os trechos daquela obra
        registros = banco.buscar_por_obra(valor)
        if not registros:
            self._tratar_busca_vazia(f"Nenhum registro para a obra {valor}.")
            return
        total_prep = sum(r["qtd_tt_kg_prep"] or 0 for r in registros)
        total_nprep = sum(r["qtd_tt_kg_nprep"] or 0 for r in registros)
        self.info_busca.setText(
            f"Registros: {len(registros)}   ·   "
            f"PREP total: {formatar_kg(total_prep)}   ·   "
            f"ÑPREP total: {formatar_kg(total_nprep)}"
        )
        self.tabela_busca.preencher(registros)

    def _buscar_pacote(self):
        lote = self.entry_pacote.text().strip()
        if not lote:
            QMessageBox.warning(self, "Atenção", "Informe o número do pacote/lote.")
            return
        registros = banco.buscar_por_pacote(lote)
        if not registros:
            self._tratar_busca_vazia(f"Nenhum registro para o pacote {lote}.")
            return
        total_prep = sum(r["qtd_tt_kg_prep"] or 0 for r in registros)
        total_nprep = sum(r["qtd_tt_kg_nprep"] or 0 for r in registros)
        self.info_busca.setText(
            f"Registros: {len(registros)}   ·   "
            f"PREP total: {formatar_kg(total_prep)}   ·   "
            f"ÑPREP total: {formatar_kg(total_nprep)}"
        )
        self.tabela_busca.preencher(registros)

    def _atualizar_base_busca(self):
        """
        Botão "🔄 Atualizar Base de Busca" (em Configurações): reimporta a
        planilha configurada pra base usada em Buscar por Obra/Pacote.
        Nunca roda sozinho — só quando o usuário clica.
        """
        caminho = banco.carregar_config("caminho_planilha")
        if not caminho:
            QMessageBox.warning(
                self, "Configuração incompleta",
                "Defina a Planilha na tela de Configurações antes de atualizar a base.")
            self._mostrar_pagina("config")
            return
        xlsx = encontrar_arquivo_xlsx(caminho)
        if not xlsx:
            QMessageBox.critical(self, "Erro", f"Nenhum arquivo .xlsx encontrado em:\n{caminho}")
            return
        resultado = importar_planilha_busca(xlsx)
        if resultado["ok"]:
            QMessageBox.information(self, "Base atualizada", resultado["msg"])
        else:
            QMessageBox.critical(self, "Erro", resultado["msg"])

    # ── PÁGINA: Configurações ───────────────────────────────────────────────

    def _pagina_configuracoes(self):
        pagina = QWidget()
        outer = QVBoxLayout(pagina)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")
        outer.addWidget(scroll)

        conteudo = QWidget()
        lay = QVBoxLayout(conteudo)
        lay.setContentsMargins(36, 24, 36, 24)
        lay.setSpacing(4)
        scroll.setWidget(conteudo)

        titulo = QLabel("Configurações")
        titulo.setStyleSheet(f"color:{COR_TEXTO}; font-size:18px; font-weight:bold;")
        lay.addWidget(titulo)

        desc = QLabel(
            "Caminhos usados pela criação de pastas e pela auditoria. Ficam salvos e não "
            "precisam ser preenchidos de novo."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet(f"color:{COR_TEXTO_SUB}; font-size:11px;")
        lay.addWidget(desc)
        lay.addSpacing(16)

        self.entry_planilha = self._campo_config(
            lay, titulo_campo="📊  Planilha (.xlsx)",
            explicacao="Arquivo (ou pasta que contém o arquivo) com as colunas LOTE e OF/Trecho. "
                       "É lida por Criar Pastas e Auditoria.",
            chave_config="caminho_planilha", btn_cmd=self._selecionar_planilha,
        )
        self.label_xlsx = QLabel("")
        self.label_xlsx.setStyleSheet(f"color:{COR_TEXTO_SUB}; font-size:9px;")
        lay.addWidget(self.label_xlsx)
        lay.addSpacing(6)

        linha_atualizar_base = QHBoxLayout()
        btn_atualizar_base = QPushButton("🔄 Atualizar Base de Busca")
        btn_atualizar_base.setObjectName("btn_limpar")
        btn_atualizar_base.clicked.connect(self._atualizar_base_busca)
        linha_atualizar_base.addWidget(btn_atualizar_base)
        lbl_atualizar_base = QLabel(
            "  Reimporta a planilha acima pra base usada na tela \"Buscar Obra / Pacote\".")
        lbl_atualizar_base.setWordWrap(True)
        lbl_atualizar_base.setStyleSheet(f"color:{COR_TEXTO_SUB}; font-size:10px;")
        linha_atualizar_base.addWidget(lbl_atualizar_base, 1)
        lay.addLayout(linha_atualizar_base)
        lay.addSpacing(14)

        self.entry_salvar = self._campo_config(
            lay, titulo_campo="📂  Destino (pasta do mês)",
            explicacao="Pasta onde as pastas de cada LOTE são criadas — normalmente a pasta "
                       "do mês atual (ex: K:\\8.M08-2026).",
            chave_config="caminho_destino", btn_cmd=self._selecionar_destino,
        )
        lay.addSpacing(8)

        lbl_raizes = QLabel("🗄️  Diretórios raiz")
        lbl_raizes.setStyleSheet(f"color:{COR_TEXTO}; font-size:13px; font-weight:bold;")
        lay.addWidget(lbl_raizes)
        desc_raizes = QLabel(
            "Pastas que contêm as pastas de mês E a própria pasta LOTE 9999 (ex: K:\\). "
            "Cadastre quantas precisar — a auditoria e o resgate automático da 9999 juntam "
            "todas elas."
        )
        desc_raizes.setWordWrap(True)
        desc_raizes.setStyleSheet(f"color:{COR_TEXTO_SUB}; font-size:10px;")
        lay.addWidget(desc_raizes)

        linha_add = QHBoxLayout()
        btn_add_raiz = QPushButton("➕ Adicionar Diretório Raiz")
        btn_add_raiz.setObjectName("btn_limpar")
        btn_add_raiz.clicked.connect(self._adicionar_raiz_ui)
        linha_add.addWidget(btn_add_raiz)
        linha_add.addStretch()
        lay.addLayout(linha_add)

        self.lista_raizes_widget = QWidget()
        self.lista_raizes_layout = QVBoxLayout(self.lista_raizes_widget)
        self.lista_raizes_layout.setContentsMargins(0, 6, 0, 6)
        self.lista_raizes_layout.setSpacing(4)
        lay.addWidget(self.lista_raizes_widget)

        lay.addSpacing(20)
        lbl_versao = QLabel(f"Versão instalada: {VERSAO_ATUAL}")
        lbl_versao.setStyleSheet(f"color:{COR_TEXTO_SUB}; font-size:8px;")
        lay.addWidget(lbl_versao)
        lay.addStretch()
        return pagina

    def _campo_config(self, lay, titulo_campo, explicacao, chave_config, btn_cmd):
        """Cria um bloco padrão de campo de configuração: título, explicação, entry + botão."""
        lbl_titulo = QLabel(titulo_campo)
        lbl_titulo.setStyleSheet(f"color:{COR_TEXTO}; font-size:13px; font-weight:bold;")
        lay.addWidget(lbl_titulo)
        lbl_expl = QLabel(explicacao)
        lbl_expl.setWordWrap(True)
        lbl_expl.setStyleSheet(f"color:{COR_TEXTO_SUB}; font-size:10px;")
        lay.addWidget(lbl_expl)
        linha = QHBoxLayout()
        entry = QLineEdit()
        entry.setPlaceholderText("Selecione...")
        entry.editingFinished.connect(lambda c=chave_config, en=entry: banco.salvar_config(c, en.text().strip()))
        linha.addWidget(entry, 1)
        btn = QPushButton("📂 Selecionar")
        btn.setObjectName("btn_limpar")
        btn.setFixedWidth(140)
        btn.clicked.connect(btn_cmd)
        linha.addWidget(btn)
        lay.addLayout(linha)
        lay.addSpacing(4)
        return entry

    def _selecionar_planilha(self):
        arquivo, _ = QFileDialog.getOpenFileName(
            self, "Selecione a planilha .xlsx", "", "Planilha Excel (*.xlsx);;Todos os arquivos (*.*)")
        if arquivo:
            self.entry_planilha.setText(arquivo)
            banco.salvar_config("caminho_planilha", arquivo)
            self._atualizar_preview_xlsx(arquivo)

    def _selecionar_destino(self):
        pasta = QFileDialog.getExistingDirectory(self, "Selecione onde criar as pastas do lote")
        if pasta:
            self.entry_salvar.setText(pasta)
            banco.salvar_config("caminho_destino", pasta)
            if not banco.listar_raizes():
                sugestao = os.path.dirname(pasta)
                if banco.adicionar_raiz(sugestao):
                    self._atualizar_lista_raizes()

    def _adicionar_raiz_ui(self):
        pasta = QFileDialog.getExistingDirectory(self, "Selecione um diretório raiz (ex: K:\\)")
        if not pasta:
            return
        if not banco.adicionar_raiz(pasta):
            QMessageBox.information(self, "Já cadastrada", "Esse diretório já está na lista de raízes.")
        self._atualizar_lista_raizes()

    def _remover_raiz_ui(self, caminho):
        banco.remover_raiz(caminho)
        self._atualizar_lista_raizes()

    def _atualizar_lista_raizes(self):
        self._limpar_layout(self.lista_raizes_layout)
        raizes = banco.listar_raizes()
        if not raizes:
            lbl = QLabel("Nenhum diretório raiz cadastrado ainda.")
            lbl.setStyleSheet(f"color:{COR_TEXTO_SUB}; font-size:10px;")
            self.lista_raizes_layout.addWidget(lbl)
            return
        for caminho in raizes:
            linha = QFrame()
            linha.setStyleSheet(f"background:{COR_PAINEL_RESULTADO}; border-radius:4px;")
            ll = QHBoxLayout(linha)
            ll.setContentsMargins(12, 6, 8, 6)
            pasta_9999 = obter_pasta_9999(caminho)
            if not os.path.isdir(caminho):
                status_texto, status_cor = "🚫 pasta não encontrada", COR_VERMELHO
            elif os.path.isdir(pasta_9999):
                status_texto, status_cor = "✅ LOTE 9999 encontrada", COR_VERDE
            else:
                status_texto, status_cor = "⚠️  sem LOTE 9999", COR_AMBAR
            lbl_caminho = QLabel(caminho)
            lbl_caminho.setWordWrap(True)
            lbl_caminho.setStyleSheet(f"color:{COR_TEXTO}; font-size:11px;")
            ll.addWidget(lbl_caminho, 1)
            lbl_status = QLabel(status_texto)
            lbl_status.setStyleSheet(f"color:{status_cor}; font-size:9px;")
            ll.addWidget(lbl_status)
            btn_remover = QPushButton("🗑")
            btn_remover.setFixedWidth(32)
            btn_remover.setStyleSheet(
                "QPushButton { background:#7F1D1D; color:white; border-radius:4px; border:none; } "
                "QPushButton:hover { background:#991B1B; }")
            btn_remover.clicked.connect(lambda _, c=caminho: self._remover_raiz_ui(c))
            ll.addWidget(btn_remover)
            self.lista_raizes_layout.addWidget(linha)

    # ── auxiliares ───────────────────────────────────────────────────────────

    def _carregar_caminhos_salvos(self):
        planilha = banco.carregar_config("caminho_planilha")
        destino = banco.carregar_config("caminho_destino")
        if planilha:
            self.entry_planilha.setText(planilha)
            self._atualizar_preview_xlsx(planilha)
        if destino:
            self.entry_salvar.setText(destino)
        self._atualizar_lista_raizes()

    def _atualizar_preview_xlsx(self, pasta):
        xlsx = encontrar_arquivo_xlsx(pasta)
        if xlsx:
            nome = os.path.basename(xlsx)
            self.label_xlsx.setText(f"   📄 Planilha encontrada: {nome}")
            self.label_xlsx.setStyleSheet(f"color:{COR_VERDE}; font-size:9px;")
        else:
            self.label_xlsx.setText("   ⚠️  Nenhum arquivo .xlsx encontrado nesta pasta")
            self.label_xlsx.setStyleSheet(f"color:{COR_AMBAR}; font-size:9px;")

    def _verificar_nova_versao_ui(self):
        """Ao abrir a aba, avisa se existe uma versão mais nova desta ferramenta disponível."""
        try:
            info = verificar_nova_versao()
        except Exception as e:
            logger.error(f"Erro ao verificar versão (auditoria): {e}")
            return
        if info["tem_nova"]:
            QMessageBox.information(
                self, "Nova versão disponível",
                f"Você está usando a versão {VERSAO_ATUAL}.\n"
                f"Já existe a versão {info['versao_disponivel']} disponível.\n\n"
                "Peça pra atualizar o programa quando puder."
            )
