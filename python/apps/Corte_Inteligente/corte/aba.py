# -*- coding: utf-8 -*-
"""
Aba "Corte Inteligente": tela que amarra o ProcessadorDXF (motor) com a
visualizacao grafica, o historico de Anterior/Proximo e os dialogos de
Diagnostico/Arquivos Processados.
"""
import os

from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QPushButton, QTextEdit, QProgressBar,
                             QMessageBox, QGraphicsView, QGraphicsScene,
                             QGraphicsRectItem, QGraphicsLineItem, QGraphicsEllipseItem,
                             QCheckBox, QSpinBox, QGroupBox, QFrame, QFileDialog)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QBrush, QColor, QPen, QPainter

from nucleo.estilo import COR_BG, COR_PAINEL, COR_BORDA, COR_TEXTO, COR_TEXTO_SUB, CORES_PARTES
from corte.processador import ProcessadorDXF
from corte.dialogos import PainelMedidas, DialogoDiagnostico, DialogoArquivosProcessados


class AbaCorte(QWidget):
    def __init__(self, banco_dados, parent=None):
        super().__init__(parent)
        self.banco_dados = banco_dados
        self.processador = ProcessadorDXF(self, self.banco_dados)
        self.historico = []       # cada item processado, pra poder rever com Anterior/Proximo
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
        lbl_titulo = QLabel("⚙  Sistema de Corte Inteligente")
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

        # painel esquerdo
        corpo_layout.addWidget(self._painel_controle(), 0)
        # painel direito
        corpo_layout.addWidget(self._painel_visual(), 1)

        # painel de medidas (rodapé)
        self.painel_medidas = PainelMedidas()
        root_layout.addWidget(self.painel_medidas)

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
        self.spn_velocidade.setValue(2000)
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
        # usuário). Empilhado, o botão ganha a largura toda da coluna e o
        # texto completo (não só o ícone) fica legível.
        btn_procurar = QPushButton("📁 Selecionar Pasta")
        btn_procurar.setObjectName("btn_limpar")
        btn_procurar.setToolTip("Procurar pasta…")
        btn_procurar.clicked.connect(self._procurar_pasta)
        cl.addWidget(lbl_cam)
        cl.addWidget(self.txt_caminho)
        cl.addWidget(btn_procurar)
        lay.addWidget(grp_cam)

        # botões
        btn_lay = QHBoxLayout()
        self.btn_processar = QPushButton("▶  Processar")
        self.btn_processar.setObjectName("btn_processar")
        self.btn_processar.clicked.connect(self.iniciar_processamento)
        self.btn_limpar = QPushButton("Limpar")
        self.btn_limpar.setObjectName("btn_limpar")
        self.btn_limpar.clicked.connect(self.limpar_interface)
        btn_lay.addWidget(self.btn_processar)
        btn_lay.addWidget(self.btn_limpar)
        lay.addLayout(btn_lay)

        self.btn_diagnostico = QPushButton("📊 Diagnóstico")
        self.btn_diagnostico.setObjectName("btn_limpar")
        self.btn_diagnostico.clicked.connect(self.abrir_diagnostico)
        lay.addWidget(self.btn_diagnostico)

        self.btn_arquivos = QPushButton("🗂 Arquivos Processados")
        self.btn_arquivos.setObjectName("btn_limpar")
        self.btn_arquivos.clicked.connect(self.abrir_arquivos_processados)
        lay.addWidget(self.btn_arquivos)

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

        lbl = QLabel("Visualização do Corte")
        lbl.setStyleSheet(
            f"color:{COR_TEXTO}; font-size:13px; font-weight:bold;")
        lay.addWidget(lbl)

        self.scene = QGraphicsScene()
        self.view  = QGraphicsView(self.scene)
        self.view.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
        self.view.setBackgroundBrush(QBrush(QColor(COR_BG)))
        self.view.setStyleSheet(
            f"border:1px solid {COR_BORDA}; border-radius:4px;")
        lay.addWidget(self.view, 1)

        # navegação: rever qualquer peça já processada, sem reprocessar
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
        self.lbl_info.setStyleSheet(
            f"color:{COR_TEXTO_SUB}; font-size:10px; padding:4px;")
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
            self.scene.clear()
            self.lbl_info.clear()
            self.painel_medidas.limpar()
            self._atualizar_botoes_navegacao()
            return
        dados = self.historico[self.indice_historico]
        self._renderizar_corte(dados)
        self._atualizar_botoes_navegacao()

    # ── visualização ─────────────────────────────────────────────────────────

    def mostrar_visualizacao(self, dimensoes, partes, furos, nome,
                             estrategia, eficiencia, perda):
        """Chamado pelo ProcessadorDXF durante o processamento: grava esse
        arquivo no historico (pra poder rever com Anterior/Proximo depois)
        e desenha."""
        dados = {
            'dimensoes': dimensoes, 'partes': partes, 'furos': furos,
            'nome': nome, 'estrategia': estrategia,
            'eficiencia': eficiencia, 'perda': perda,
        }
        self.historico.append(dados)
        self.indice_historico = len(self.historico) - 1
        self._renderizar_corte(dados)
        self._atualizar_botoes_navegacao()

    def _renderizar_corte(self, dados):
        """Desenho puro (sem mexer no historico) — usado tanto durante o
        processamento quanto ao navegar com Anterior/Proximo."""
        dimensoes, partes, furos = dados['dimensoes'], dados['partes'], dados['furos']
        nome = dados['nome']
        estrategia, eficiencia, perda = dados['estrategia'], dados['eficiencia'], dados['perda']
        comprimento, altura = dimensoes
        self.scene.clear()
        self.scene.setSceneRect(0, 0, comprimento, altura)

        # fundo da peça
        rect_bg = QGraphicsRectItem(0, 0, comprimento, altura)
        rect_bg.setBrush(QBrush(QColor(COR_PAINEL)))
        rect_bg.setPen(QPen(QColor(COR_BORDA), 1))
        self.scene.addItem(rect_bg)

        # partes coloridas
        for i, (xa, xb) in enumerate(partes):
            cor = CORES_PARTES[i % len(CORES_PARTES)]
            rect = QGraphicsRectItem(xa, 0, xb - xa, altura)
            rect.setBrush(QBrush(cor))
            rect.setPen(QPen(Qt.NoPen))
            self.scene.addItem(rect)

            # borda escura
            borda = QGraphicsRectItem(xa, 0, xb - xa, altura)
            borda.setBrush(QBrush(Qt.NoBrush))
            borda.setPen(QPen(QColor(255, 255, 255, 40), 1))
            self.scene.addItem(borda)

            # rótulo
            letra = chr(65 + i)
            txt   = self.scene.addText(f"[{letra}]\n{xb-xa:.0f}mm")
            txt.setDefaultTextColor(Qt.white)
            txt.setFont(QFont("Segoe UI", max(6, int(altura * 0.12)), QFont.Bold))
            tw = txt.boundingRect().width()
            th = txt.boundingRect().height()
            txt.setPos(xa + (xb - xa) / 2 - tw / 2, altura / 2 - th / 2)

        # furos
        for f in furos:
            cx, cy = f['center']
            r = f['radius']
            circ = QGraphicsEllipseItem(cx - r, cy - r, r * 2, r * 2)
            circ.setBrush(QBrush(QColor(COR_BG)))
            circ.setPen(QPen(QColor(255, 80, 80), 1.5))
            self.scene.addItem(circ)

        # linhas de corte
        for i, (xa, xb) in enumerate(partes[:-1]):
            linha = QGraphicsLineItem(xb, 0, xb, altura)
            linha.setPen(QPen(QColor(255, 255, 255, 180), 2, Qt.DashLine))
            self.scene.addItem(linha)
            lbl_corte = self.scene.addText(f"↕ {xb:.0f}")
            lbl_corte.setDefaultTextColor(QColor(255, 255, 255, 160))
            lbl_corte.setFont(QFont("Segoe UI", max(5, int(altura * 0.08))))
            lbl_corte.setPos(xb + 4, 2)

        self.view.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio)

        # painel de medidas
        self.painel_medidas.atualizar(partes)

        # info texto
        self.lbl_info.setText(
            f"📄 {nome}   |   {estrategia}   |   "
            f"{comprimento:.0f}×{altura:.0f}mm   |   "
            f"{len(partes)} parte(s)   |   {len(furos)} furo(s)"
        )
        QApplication.processEvents()

    # ── controle ─────────────────────────────────────────────────────────────

    def iniciar_processamento(self):
        caminho = self.txt_caminho.toPlainText().strip()
        if not caminho or not os.path.isdir(caminho):
            QMessageBox.warning(self, "Caminho inválido",
                                "Por favor, informe um caminho de pasta válido.")
            return
        self.btn_processar.setEnabled(False)
        self.txt_log.clear()
        self.historico = []
        self.indice_historico = -1
        self._atualizar_botoes_navegacao()
        self.adicionar_log(f"📁 Pasta: {caminho}")
        QTimer.singleShot(100, lambda: self._executar(caminho))

    def _executar(self, caminho):
        ok = self.processador.processar_pasta(caminho)
        if ok:
            self.adicionar_log("✅ Processamento concluído!")
            QMessageBox.information(self, "Concluído", "Todos os arquivos foram processados.")
        else:
            self.adicionar_log("⚠ Concluído com erros. Verifique o log.")
            QMessageBox.warning(self, "Erros", "Alguns arquivos não puderam ser processados.")
        self.btn_processar.setEnabled(True)
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

    def abrir_diagnostico(self):
        dialogo = DialogoDiagnostico(self.banco_dados, self)
        dialogo.exec_()

    def abrir_arquivos_processados(self):
        dialogo = DialogoArquivosProcessados(self.banco_dados, self)
        dialogo.exec_()

    def limpar_interface(self):
        self.txt_caminho.clear()
        self.txt_log.clear()
        self.lbl_status.setText("Aguardando processamento…")
        self.progress_bar.setValue(0)
        self.scene.clear()
        self.lbl_info.clear()
        self.painel_medidas.limpar()
        self.historico = []
        self.indice_historico = -1
        self._atualizar_botoes_navegacao()


