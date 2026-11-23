# -*- coding: utf-8 -*-
"""
Paleta visual compartilhada pelas ferramentas Qt (Corte, Espelhar, Auditoria, Conversor, Renomear DXF e,
por cima desta base, o Visualizador — visualizador/estilo.py importa estas cores).

TEMA SISTEMA - PPCPM (docs/REQUISITOS_FLUXO_DE_TRABALHO.md, seção 10 "Padrão visual"):
  - Azul Projeart #0b3d91 (escuro #082e6e) nas faixas, ícones e destaques;
  - fundo das telas #eef1f5;
  - quadros com borda escura #545659, FAIXA AZUL DE 3px EM CIMA, cantos 4px e o título numa faixa cinza
    (#d7dce3 -> #c2c9d3, linha #aab2bd);
  - TODOS os botões de ação cinza-azulado (#e3e8ee -> #cdd4de, borda #98a3b3), letra preta negrito, cantos 4px;
  - campos (#f3f5f8 -> #e6eaf0, borda #98a3b3, texto preto negrito; ao focar ficam brancos);
  - tabelas: cabeçalho no tema dos botões com letra preta negrito, divisórias #98a3b3, linhas brancas
    alternando com #f6f7f9, selecionada #dbe8fb;
  - verde OK #1e9e4a / texto #15803d · vermelho erro #c62828 · laranja #ea580c.

Só APARÊNCIA: os nomes das constantes são os mesmos de antes, então nenhuma ferramenta muda de funcionamento.
"""
from PyQt5.QtGui import QColor

# --- Cores de referência do SISTEMA - PPCPM
COR_AZUL_MARCA  = "#0B3D91"   # azul Projeart (faixas, ícones, destaque)
COR_MARINHO     = "#082E6E"   # azul Projeart escuro

COR_BG          = "#EEF1F5"   # fundo da página das abas
COR_PAINEL      = "#FFFFFF"   # superfícies brancas (tabelas, áreas de texto, cabeçalhos)
COR_CAMPO       = "#F3F5F8"   # campos (input/select)
COR_BORDA       = "#98A3B3"   # borda padrão (campos, botões, divisórias de tabela)
COR_TEXTO       = "#000000"   # texto preto
COR_TEXTO_SUB   = "#4B5563"   # texto secundário/legenda
COR_DESTAQUE    = COR_AZUL_MARCA
COR_VERDE       = "#15803D"   # sucesso (texto)
COR_VERMELHO    = "#C62828"   # erro
COR_AMARELO     = "#B45309"   # aviso

# extras do tema (usados só aqui e nas folhas de estilo abaixo)
COR_QUADRO_BORDA   = "#545659"
COR_FAIXA_TITULO   = "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #D7DCE3, stop:1 #C2C9D3)"
COR_LINHA_TITULO   = "#AAB2BD"
COR_BOTAO          = "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #E3E8EE, stop:1 #CDD4DE)"
COR_BOTAO_HOVER    = "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #D9DFE7, stop:1 #C2CAD5)"
COR_BOTAO_BORDA_HV = "#808C9E"
COR_CAMPO_GRAD     = "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #F3F5F8, stop:1 #E6EAF0)"
COR_LINHA_ALT      = "#F6F7F9"
COR_LINHA_HOVER    = "#EEF4FB"
COR_LINHA_SEL      = "#DBE8FB"
COR_OK_FAIXA       = "#1E9E4A"
COR_OK_FUNDO       = "#DCF5E3"
COR_ERRO_FUNDO     = "#FDEEEE"
COR_ERRO_BORDA     = "#F1B9B9"
COR_LARANJA        = "#EA580C"

CORES_PARTES = [
    QColor(11,   61, 145, 210),   # azul Projeart
    QColor(30,  158,  74, 210),   # verde
    QColor(234,  88,  12, 210),   # laranja
    QColor(124,  58, 237, 210),   # roxo
    QColor(198,  40,  40, 210),   # vermelho
]

ESTILO_GERAL = f"""
QMainWindow, QWidget {{
    background-color: {COR_BG};
    color: {COR_TEXTO};
    font-family: 'Segoe UI', Roboto, Arial, sans-serif;
}}
QDialog {{ background-color: {COR_BG}; }}
QTabWidget::pane {{
    border: 1px solid {COR_QUADRO_BORDA};
    border-top: 3px solid {COR_AZUL_MARCA};
    border-radius: 4px;
    top: -1px;
}}
QTabBar::tab {{
    background: {COR_BOTAO};
    color: {COR_TEXTO};
    border: 1px solid {COR_BORDA};
    border-bottom: none;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    padding: 7px 16px;
    margin-right: 2px;
    font-weight: bold;
    font-size: 12px;
}}
QTabBar::tab:selected {{
    background: #FFFFFF;
    border-top: 3px solid {COR_AZUL_MARCA};
}}
QTabBar::tab:hover {{ background: {COR_BOTAO_HOVER}; }}

/* QUADROS: borda escura, faixa azul de 3px em cima, título numa faixa cinza */
QGroupBox {{
    background-color: {COR_BG};
    border: 1px solid {COR_QUADRO_BORDA};
    border-top: 3px solid {COR_AZUL_MARCA};
    border-radius: 4px;
    margin-top: 14px;
    padding: 18px 8px 8px 8px;
    font-weight: bold;
    color: {COR_TEXTO};
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 8px;
    top: 2px;
    padding: 3px 10px;
    background: {COR_FAIXA_TITULO};
    border: 1px solid {COR_LINHA_TITULO};
    border-radius: 3px;
    color: {COR_TEXTO};
}}

QTextEdit, QPlainTextEdit {{
    background-color: #FFFFFF;
    border: 1px solid {COR_BORDA};
    border-radius: 4px;
    color: {COR_TEXTO};
    font-family: 'Consolas', monospace;
    font-size: 11px;
    padding: 4px;
}}
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
    background: {COR_CAMPO_GRAD};
    border: 1px solid {COR_BORDA};
    border-radius: 4px;
    color: {COR_TEXTO};
    font-weight: bold;
    padding: 5px 8px;
    selection-background-color: {COR_LINHA_SEL};
    selection-color: {COR_TEXTO};
}}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
    background: #FFFFFF;
    border: 1px solid {COR_AZUL_MARCA};
}}
QLineEdit:disabled {{
    color: {COR_TEXTO_SUB};
    background: {COR_BG};
}}
QComboBox QAbstractItemView {{
    background: #FFFFFF;
    color: {COR_TEXTO};
    selection-background-color: {COR_LINHA_SEL};
    selection-color: {COR_TEXTO};
}}
QLabel {{ color: {COR_TEXTO}; background: transparent; }}
QCheckBox, QRadioButton {{ color: {COR_TEXTO}; spacing: 6px; background: transparent; }}
QCheckBox::indicator {{
    width: 14px; height: 14px;
    border: 1px solid {COR_BORDA};
    border-radius: 3px;
    background: #FFFFFF;
}}
QCheckBox::indicator:checked {{
    background: {COR_AZUL_MARCA};
    border-color: {COR_AZUL_MARCA};
}}
QProgressBar {{
    background-color: #FFFFFF;
    border: 1px solid {COR_BORDA};
    border-radius: 4px;
    height: 8px;
    text-align: center;
    color: transparent;
}}
QProgressBar::chunk {{
    background-color: {COR_AZUL_MARCA};
    border-radius: 3px;
}}

/* BOTÕES: todos cinza-azulado, letra preta negrito, cantos 4px */
QPushButton {{
    background: {COR_BOTAO};
    color: {COR_TEXTO};
    border: 1px solid {COR_BORDA};
    border-radius: 4px;
    padding: 6px 14px;
    font-weight: bold;
    font-size: 12px;
}}
QPushButton:hover {{ background: {COR_BOTAO_HOVER}; border-color: {COR_BOTAO_BORDA_HV}; }}
QPushButton:pressed {{ background: #C2CAD5; }}
QPushButton:disabled {{ color: #8A929E; border-color: #B9C0CA; }}
QPushButton#btn_processar {{ background: {COR_BOTAO}; color: {COR_TEXTO}; }}
QPushButton#btn_processar:hover {{ background: {COR_BOTAO_HOVER}; }}
QPushButton#btn_processar:disabled {{ color: #8A929E; }}
QPushButton#btn_limpar {{ background: {COR_BOTAO}; color: {COR_TEXTO}; }}
QPushButton#btn_limpar:hover {{ background: {COR_BOTAO_HOVER}; }}

/* TABELAS: cabeçalho no tema dos botões, letra preta negrito; linhas brancas alternando com #f6f7f9 */
QTableWidget, QTableView, QTreeWidget, QListWidget {{
    background: #FFFFFF;
    alternate-background-color: {COR_LINHA_ALT};
    color: {COR_TEXTO};
    border: 1px solid {COR_BORDA};
    gridline-color: #D5DAE1;
    selection-background-color: {COR_LINHA_SEL};
    selection-color: {COR_TEXTO};
}}
QHeaderView::section {{
    background: {COR_BOTAO};
    color: {COR_TEXTO};
    font-weight: bold;
    padding: 5px;
    border: none;
    border-right: 1px solid {COR_BORDA};
    border-bottom: 1px solid {COR_BORDA};
}}
QScrollBar:vertical {{
    background: #E9EDF1; width: 10px; border-radius: 4px;
}}
QScrollBar::handle:vertical {{
    background: #A9B8C8; border-radius: 4px; min-height: 20px;
}}
QScrollBar:horizontal {{
    background: #E9EDF1; height: 10px; border-radius: 4px;
}}
QScrollBar::handle:horizontal {{
    background: #A9B8C8; border-radius: 4px; min-width: 20px;
}}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0px; height: 0px; }}
QToolTip {{ background: #FFFFFF; color: {COR_TEXTO}; border: 1px solid {COR_BORDA}; }}
QMessageBox {{ background: {COR_BG}; }}
"""
