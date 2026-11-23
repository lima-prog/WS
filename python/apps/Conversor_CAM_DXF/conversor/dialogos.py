# -*- coding: utf-8 -*-
"""
Diálogo da aba Conversor: deixa o usuário digitar manualmente o
identificador da obra de uma ou mais peças da tabela, para os casos em que
a regra automática (`conversor/utilitarios.py::normalizar_obra()`) não dá
conta do nome da pasta — ela foi pensada pra cobrir os padrões conhecidos,
mas sempre pode aparecer um nome fora de qualquer padrão previsto.

O valor digitado aqui tem prioridade total sobre o valor calculado
automaticamente na hora de montar o nome do DXF — ver
`conversor/utilitarios.py::nome_dxf()`.
"""
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QLineEdit, QPushButton, QMessageBox)

from nucleo.estilo import ESTILO_GERAL, COR_TEXTO_SUB


class DialogoEditarObra(QDialog):
    """
    Pede o identificador da obra pra aplicar em `quantidade` peça(s)
    selecionada(s) na tabela do Conversor.

    `valor_inicial` pré-preenche o campo — quem chama passa o valor já
    aplicado hoje quando todas as linhas selecionadas concordam (manual ou
    automático), e vazio quando há mistura, pra não sugerir um valor errado
    pra alguma das peças.

    Depois de `exec_()`, `self.valor` guarda o resultado:
      - texto não vazio  -> usuário digitou/confirmou um valor manual;
      - ""               -> usuário clicou "Restaurar automático" (remove
                             qualquer sobreposição manual dessas peças);
      - None             -> diálogo cancelado, nada deve mudar.
    """

    def __init__(self, quantidade, valor_inicial="", parent=None):
        super().__init__(parent)
        self.valor = None
        self.setWindowTitle("Editar Obra")
        self.setStyleSheet(ESTILO_GERAL)
        self.setFixedWidth(380)
        self._montar_ui(quantidade, valor_inicial)

    def _montar_ui(self, quantidade, valor_inicial):
        lay = QVBoxLayout(self)

        plural = "peça selecionada" if quantidade == 1 else f"{quantidade} peças selecionadas"
        lbl_info = QLabel(f"Novo identificador de obra para {plural}:")
        lbl_info.setWordWrap(True)
        lay.addWidget(lbl_info)

        self.txt_obra = QLineEdit(valor_inicial)
        self.txt_obra.setPlaceholderText("Ex.: 2104-2-55-2")
        self.txt_obra.selectAll()
        self.txt_obra.returnPressed.connect(self._salvar)
        lay.addWidget(self.txt_obra)

        lbl_dica = QLabel(
            "Esse valor substitui, só para essas peças, o que seria "
            "calculado automaticamente a partir do nome da pasta. Vale só "
            "enquanto essa aba do Conversor estiver aberta — fechar a aba "
            "ou abrir a pasta de novo volta pro cálculo automático."
        )
        lbl_dica.setWordWrap(True)
        lbl_dica.setStyleSheet(f"color:{COR_TEXTO_SUB}; font-size:10px;")
        lay.addWidget(lbl_dica)

        botoes = QHBoxLayout()
        btn_restaurar = QPushButton("Restaurar automático")
        btn_restaurar.setObjectName("btn_limpar")
        btn_restaurar.clicked.connect(self._restaurar)
        botoes.addWidget(btn_restaurar)
        botoes.addStretch()
        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.setObjectName("btn_limpar")
        btn_cancelar.clicked.connect(self.reject)
        botoes.addWidget(btn_cancelar)
        btn_salvar = QPushButton("Salvar")
        btn_salvar.setObjectName("btn_processar")
        btn_salvar.clicked.connect(self._salvar)
        botoes.addWidget(btn_salvar)
        lay.addLayout(botoes)

    def _salvar(self):
        texto = self.txt_obra.text().strip()
        if not texto:
            QMessageBox.warning(
                self, "Obra vazia",
                "Digite um identificador de obra, ou use "
                "\"Restaurar automático\" para voltar ao valor calculado "
                "pela regra.")
            return
        self.valor = texto
        self.accept()

    def _restaurar(self):
        self.valor = ""  # sinaliza "remover sobreposição manual"
        self.accept()
