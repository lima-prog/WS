# -*- coding: utf-8 -*-
"""
Aba "Espelhar DXF": pecas xadrez -- engenharia libera olhando a face lisa
(xadrez pra baixo), no corte a chapa vai com o xadrez pra cima -> sem
espelhar, a geometria assimetrica sai invertida. Essa aba pede a pasta,
espelha cada DXF (mirror em X + reancora em 0,0) e mostra a peca ANTES e
DEPOIS lado a lado, pra conferencia visual.
"""
import os

from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QPushButton, QTextEdit, QProgressBar,
                             QMessageBox, QGraphicsView, QGraphicsScene,
                             QCheckBox, QSpinBox, QGroupBox, QFrame, QFileDialog)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QBrush, QColor, QPainter

from nucleo.estilo import COR_BG, COR_PAINEL, COR_BORDA, COR_TEXTO, COR_TEXTO_SUB, COR_DESTAQUE
from dxf_util.preview import desenhar_preview_dxf
from espelhar.mirror import SUBPASTA_ESPELHADAS
from espelhar.processador import ProcessadorEspelhamento


class AbaEspelhar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.processador = ProcessadorEspelhamento(self)
        self.historico = []       # cada peca espelhada (antes+depois), pra rever com Anterior/Proximo
        self.indice_historico = -1
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
        lbl_titulo = QLabel("🪞  Espelhar DXF — Peças Xadrez")
        lbl_titulo.setStyleSheet(
            f"color:{COR_TEXTO}; font-size:15px; font-weight:bold;")
        lbl_sub = QLabel("SISTEMA - PPCPM")
        lbl_sub.setStyleSheet(f"color:{COR_TEXTO_SUB}; font-size:11px;")
        hl.addWidget(lbl_titulo)
        hl.addStretch()
        hl.addWidget(lbl_sub)
        root_layout.addWidget(header)

        # corpo central
        corpo = QWidget()
        corpo_layout = QHBoxLayout(corpo)
        corpo_layout.setContentsMargins(10, 10, 10, 10)
        corpo_layout.setSpacing(10)
        root_layout.addWidget(corpo, 1)

        corpo_layout.addWidget(self._painel_controle(), 0)
        corpo_layout.addWidget(self._painel_visual(), 1)

    def _painel_controle(self):
        w = QWidget()
        w.setFixedWidth(290)
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)

        # configurações
        grp_cfg = QGroupBox("Configurações")
        gl = QVBoxLayout(grp_cfg)
        self.chk_visualizacao = QCheckBox("Habilitar visualização")
        self.chk_visualizacao.setChecked(True)
        lbl_vel = QLabel("Velocidade (ms):")
        lbl_vel.setStyleSheet(f"color:{COR_TEXTO_SUB}; font-size:11px;")
        self.spn_velocidade = QSpinBox()
        self.spn_velocidade.setRange(100, 10000)
        self.spn_velocidade.setValue(1200)
        self.spn_velocidade.setSingleStep(100)
        gl.addWidget(self.chk_visualizacao)
        gl.addWidget(lbl_vel)
        gl.addWidget(self.spn_velocidade)
        lay.addWidget(grp_cfg)

        # caminho
        grp_cam = QGroupBox("Pasta de Origem")
        cl = QVBoxLayout(grp_cam)
        lbl_cam = QLabel("Cole o caminho da pasta com os DXFs:")
        lbl_cam.setStyleSheet(f"color:{COR_TEXTO_SUB}; font-size:10px;")
        self.txt_caminho = QTextEdit()
        self.txt_caminho.setMaximumHeight(52)
        # Caminho ACIMA, botão ABAIXO (empilhado) -- não lado a lado: numa
        # coluna estreita de 290px, campo+botão espremidos um do lado do
        # outro deixava o ícone "📁" cortado/escondido (reportado pelo
        # usuário, mesmo problema no Corte Inteligente). Empilhado, o botão
        # ganha a largura toda da coluna e o texto completo fica legível.
        btn_procurar = QPushButton("📁 Selecionar Pasta")
        btn_procurar.setObjectName("btn_limpar")
        btn_procurar.setToolTip("Procurar pasta…")
        btn_procurar.clicked.connect(self._procurar_pasta)
        cl.addWidget(lbl_cam)
        cl.addWidget(self.txt_caminho)
        cl.addWidget(btn_procurar)
        lbl_saida = QLabel(f"Salva em: <b>{SUBPASTA_ESPELHADAS}</b> (subpasta), mesmo nome do arquivo original.")
        lbl_saida.setStyleSheet(f"color:{COR_TEXTO_SUB}; font-size:10px;")
        lbl_saida.setWordWrap(True)
        cl.addWidget(lbl_saida)
        lay.addWidget(grp_cam)

        # botões
        btn_lay = QHBoxLayout()
        self.btn_espelhar = QPushButton("🪞  Espelhar")
        self.btn_espelhar.setObjectName("btn_processar")
        self.btn_espelhar.clicked.connect(self.iniciar_processamento)
        self.btn_limpar = QPushButton("Limpar")
        self.btn_limpar.setObjectName("btn_limpar")
        self.btn_limpar.clicked.connect(self.limpar_interface)
        btn_lay.addWidget(self.btn_espelhar)
        btn_lay.addWidget(self.btn_limpar)
        lay.addLayout(btn_lay)

        # progresso
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(100)
        lay.addWidget(self.progress_bar)

        # status
        self.lbl_status = QLabel("Aguardando processamento…")
        self.lbl_status.setStyleSheet(f"color:{COR_TEXTO_SUB}; font-size:10px;")
        self.lbl_status.setWordWrap(True)
        lay.addWidget(self.lbl_status)

        # log
        grp_log = QGroupBox("Log")
        ll = QVBoxLayout(grp_log)
        self.txt_log = QTextEdit()
        self.txt_log.setReadOnly(True)
        ll.addWidget(self.txt_log)
        lay.addWidget(grp_log, 1)

        return w

    def _painel_visual(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)

        lbl = QLabel("Antes → Depois do Espelhamento")
        lbl.setStyleSheet(f"color:{COR_TEXTO}; font-size:13px; font-weight:bold;")
        lay.addWidget(lbl)

        comparacao = QHBoxLayout()
        comparacao.setSpacing(8)

        # coluna ANTES
        col_antes = QVBoxLayout()
        lbl_antes = QLabel("ANTES  (xadrez para baixo — como veio da engenharia)")
        lbl_antes.setStyleSheet(f"color:{COR_TEXTO_SUB}; font-size:10px; font-weight:bold;")
        lbl_antes.setWordWrap(True)
        col_antes.addWidget(lbl_antes)
        self.scene_antes = QGraphicsScene()
        self.view_antes = QGraphicsView(self.scene_antes)
        self.view_antes.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
        self.view_antes.setBackgroundBrush(QBrush(QColor(COR_BG)))
        self.view_antes.setStyleSheet(f"border:1px solid {COR_BORDA}; border-radius:4px;")
        col_antes.addWidget(self.view_antes, 1)
        comparacao.addLayout(col_antes, 1)

        # coluna DEPOIS
        col_depois = QVBoxLayout()
        lbl_depois = QLabel("DEPOIS  (espelhado — pronto para corte com xadrez para cima)")
        lbl_depois.setStyleSheet(f"color:{COR_DESTAQUE}; font-size:10px; font-weight:bold;")
        lbl_depois.setWordWrap(True)
        col_depois.addWidget(lbl_depois)
        self.scene_depois = QGraphicsScene()
        self.view_depois = QGraphicsView(self.scene_depois)
        self.view_depois.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
        self.view_depois.setBackgroundBrush(QBrush(QColor(COR_BG)))
        self.view_depois.setStyleSheet(f"border:1px solid {COR_DESTAQUE}; border-radius:4px;")
        col_depois.addWidget(self.view_depois, 1)
        comparacao.addLayout(col_depois, 1)

        lay.addLayout(comparacao, 1)

        # navegação: rever qualquer peça já espelhada, sem reprocessar
        nav_lay = QHBoxLayout()
        self.btn_nav_anterior = QPushButton("◀ Anterior")
        self.btn_nav_anterior.setObjectName("btn_limpar")
        self.btn_nav_anterior.setEnabled(False)
        self.btn_nav_anterior.clicked.connect(self._navegar_anterior)
        self.lbl_nav_posicao = QLabel("—")
        self.lbl_nav_posicao.setAlignment(Qt.AlignCenter)
        self.lbl_nav_posicao.setStyleSheet(f"color:{COR_TEXTO_SUB}; font-size:10px;")
        self.btn_nav_proximo = QPushButton("Próximo ▶")
        self.btn_nav_proximo.setObjectName("btn_limpar")
        self.btn_nav_proximo.setEnabled(False)
        self.btn_nav_proximo.clicked.connect(self._navegar_proximo)
        nav_lay.addWidget(self.btn_nav_anterior)
        nav_lay.addWidget(self.lbl_nav_posicao, 1)
        nav_lay.addWidget(self.btn_nav_proximo)
        lay.addLayout(nav_lay)

        self.lbl_info = QLabel()
        self.lbl_info.setStyleSheet(f"color:{COR_TEXTO_SUB}; font-size:10px; padding:4px;")
        self.lbl_info.setWordWrap(True)
        lay.addWidget(self.lbl_info)

        return w

    def _procurar_pasta(self):
        pasta = QFileDialog.getExistingDirectory(self, "Selecionar pasta com os DXFs")
        if pasta:
            self.txt_caminho.setPlainText(pasta)

    # ── navegação (Anterior/Próximo) ────────────────────────────────────────

    def _navegar_anterior(self):
        if self.indice_historico > 0:
            self.indice_historico -= 1
            self._renderizar_indice_atual()

    def _navegar_proximo(self):
        if self.indice_historico < len(self.historico) - 1:
            self.indice_historico += 1
            self._renderizar_indice_atual()

    def _atualizar_botoes_navegacao(self):
        total = len(self.historico)
        self.btn_nav_anterior.setEnabled(self.indice_historico > 0)
        self.btn_nav_proximo.setEnabled(self.indice_historico < total - 1)
        self.lbl_nav_posicao.setText(f"{self.indice_historico + 1} / {total}" if total else "—")

    def _renderizar_indice_atual(self):
        if not self.historico:
            self.scene_antes.clear()
            self.scene_depois.clear()
            self.lbl_info.clear()
            self._atualizar_botoes_navegacao()
            return
        reg = self.historico[self.indice_historico]
        self._renderizar(reg['preview_antes'], reg['preview_depois'], reg['nome'], reg['avisos'])
        self._atualizar_botoes_navegacao()

    # ── visualização ─────────────────────────────────────────────────────────

    def mostrar_resultado(self, preview_antes, preview_depois, nome, avisos):
        """Chamado pelo ProcessadorEspelhamento apos espelhar um arquivo:
        grava o par antes/depois (ja como dados numericos, extraidos por
        extrair_preview_dxf) no historico e desenha."""
        registro = {
            'preview_antes': preview_antes,
            'preview_depois': preview_depois,
            'nome': nome,
            'avisos': avisos,
        }
        self.historico.append(registro)
        self.indice_historico = len(self.historico) - 1
        self._renderizar(preview_antes, preview_depois, nome, avisos)
        self._atualizar_botoes_navegacao()

    def _renderizar(self, preview_antes, preview_depois, nome, avisos):
        self.scene_antes.clear()
        desenhar_preview_dxf(self.scene_antes, preview_antes)
        rect = self.scene_antes.itemsBoundingRect()
        if not rect.isEmpty():
            self.scene_antes.setSceneRect(rect)
            self.view_antes.fitInView(rect, Qt.KeepAspectRatio)

        self.scene_depois.clear()
        desenhar_preview_dxf(self.scene_depois, preview_depois)
        rect2 = self.scene_depois.itemsBoundingRect()
        if not rect2.isEmpty():
            self.scene_depois.setSceneRect(rect2)
            self.view_depois.fitInView(rect2, Qt.KeepAspectRatio)

        texto = f"📄 {nome}"
        if avisos:
            texto += f"   ⚠ entidade(s) sem mirror: {', '.join(sorted(set(avisos)))} — confira manualmente"
        self.lbl_info.setText(texto)
        QApplication.processEvents()

    # ── controle ─────────────────────────────────────────────────────────────

    def iniciar_processamento(self):
        caminho = self.txt_caminho.toPlainText().strip()
        if not caminho or not os.path.isdir(caminho):
            QMessageBox.warning(self, "Caminho inválido",
                                "Por favor, informe um caminho de pasta válido.")
            return
        self.btn_espelhar.setEnabled(False)
        self.txt_log.clear()
        self.historico = []
        self.indice_historico = -1
        self._atualizar_botoes_navegacao()
        self.adicionar_log(f"📁 Pasta: {caminho}")
        QTimer.singleShot(100, lambda: self._executar(caminho))

    def _executar(self, caminho):
        ok = self.processador.processar_pasta(caminho)
        if ok:
            QMessageBox.information(self, "Concluído", "Todos os arquivos foram espelhados.")
        else:
            QMessageBox.warning(self, "Erros", "Alguns arquivos não puderam ser espelhados. Verifique o log.")
        self.btn_espelhar.setEnabled(True)
        self.progress_bar.setValue(100)

    def atualizar_progresso(self, atual, total):
        self.progress_bar.setValue(int(atual / total * 100))
        QApplication.processEvents()

    def atualizar_status(self, msg):
        self.lbl_status.setText(msg)
        QApplication.processEvents()

    def adicionar_log(self, msg):
        self.txt_log.append(msg)
        QApplication.processEvents()

    def visualizacao_habilitada(self):
        return self.chk_visualizacao.isChecked()

    def velocidade_visualizacao(self):
        return self.spn_velocidade.value()

    def limpar_interface(self):
        self.txt_caminho.clear()
        self.txt_log.clear()
        self.lbl_status.setText("Aguardando processamento…")
        self.progress_bar.setValue(0)
        self.scene_antes.clear()
        self.scene_depois.clear()
        self.lbl_info.clear()
        self.historico = []
        self.indice_historico = -1
        self._atualizar_botoes_navegacao()


