# -*- coding: utf-8 -*-
"""
Estilo do Visualizador DXF — PADRÃO PROJEART (o mesmo das outras ferramentas: fundo cinza-claro, cartões
brancos, texto quase preto, azul da marca #0B3D91 nos destaques). Antes esta ferramenta tinha uma paleta
própria azul-aço escura; agora segue `nucleo/estilo.py`, então qualquer ajuste de cor da marca vale aqui também.

Só a TELA DE DESENHO do DXF continua escura (azul-marinho da marca, `COR_TELA`): é onde as linhas coloridas
das peças aparecem com mais contraste (padrão em visualizadores de CAD).

self.setStyleSheet(STYLE), aplicado na própria AbaVisualizador, cria uma "ilha" de estilo (QSS cascateia a
partir do widget mais próximo).
"""
from nucleo.estilo import (COR_BG, COR_PAINEL, COR_CAMPO, COR_BORDA, COR_TEXTO, COR_TEXTO_SUB, COR_DESTAQUE,
                           COR_MARINHO)

COR_TELA = "#0B2150"            # fundo da área de desenho do DXF
COR_TELA_BORDA = "#545659"
COR_DESABILITADO = "#9A9AA2"
COR_HINT = "#8A8A8A"

STYLE = f"""
    QMainWindow, QWidget {{
        background-color: {COR_BG};
        color: {COR_TEXTO};
        font-family: 'Segoe UI', Arial, sans-serif;
    }}
    QDialog {{
        background-color: {COR_BG};
        color: {COR_TEXTO};
    }}
    QTableWidget {{
        background-color: {COR_PAINEL};
        color: {COR_TEXTO};
        border: 1px solid {COR_BORDA};
        gridline-color: {COR_BORDA};
    }}
    QTableWidget::item:selected {{
        background-color: #DBE8FB;
        color: #000000;
    }}
    QHeaderView::section {{ background:qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #E3E8EE, stop:1 #CDD4DE); color:#000000; font-weight:bold; padding:5px; border:none; border-right:1px solid #98A3B3; border-bottom:1px solid #98A3B3; }}
    QPushButton {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #E3E8EE, stop:1 #CDD4DE);
        color: #000000;
        border: 1px solid #98A3B3;
        border-radius: 4px;
        padding: 6px 14px;
        font-weight: bold;
    }}
    QPushButton:hover {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #D9DFE7, stop:1 #C2CAD5);
        border-color: #808C9E;
    }}
    QPushButton:pressed {{
        background: #C2CAD5;
    }}
    QPushButton:disabled {{
        color: #8A929E;
        border-color: #B9C0CA;
    }}
    QMessageBox {{
        background-color: {COR_PAINEL};
        color: {COR_TEXTO};
    }}
    QMessageBox QPushButton {{
        min-width: 80px;
    }}
    QMenu {{
        background-color: {COR_PAINEL};
        color: {COR_TEXTO};
        border: 1px solid {COR_BORDA};
        padding: 4px;
    }}
    QMenu::item {{ padding: 6px 24px; border-radius: 4px; }}
    QMenu::item:selected {{
        background-color: #DBE8FB;
        color: #000000;
    }}
    QMenu::separator {{
        background-color: {COR_BORDA};
        height: 1px;
        margin: 4px 8px;
    }}
    QScrollBar:vertical {{
        background-color: transparent;
        width: 10px;
        border-radius:4px;
    }}
    QScrollBar::handle:vertical {{
        background-color: {COR_BORDA};
        border-radius:4px;
        min-height: 20px;
    }}
    QScrollBar::handle:vertical:hover {{ background-color: {COR_DESTAQUE}; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
    QScrollBar:horizontal {{
        background-color: transparent;
        height: 10px;
        border-radius:4px;
    }}
    QScrollBar::handle:horizontal {{
        background-color: {COR_BORDA};
        border-radius:4px;
        min-width: 20px;
    }}
    QScrollBar::handle:horizontal:hover {{ background-color: {COR_DESTAQUE}; }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0px; }}
    QLabel {{ color: {COR_TEXTO}; background: transparent; }}
    QSlider::groove:horizontal {{
        background-color: {COR_BORDA};
        height: 4px;
        border-radius: 2px;
    }}
    QSlider::handle:horizontal {{
        background-color: {COR_DESTAQUE};
        width: 16px;
        margin: -6px 0;
        border-radius:4px;
    }}
    QSlider::handle:horizontal:hover {{ background-color: {COR_MARINHO}; }}
    QSlider::sub-page:horizontal {{
        background-color: {COR_DESTAQUE};
        border-radius: 2px;
    }}
    QTreeWidget {{
        background-color: {COR_PAINEL};
        color: {COR_TEXTO};
        border: none;
        outline: none;
    }}
    QTreeWidget::item {{
        padding: 4px 6px;
        border-radius: 3px;
    }}
    QTreeWidget::item:hover {{
        background-color: {COR_BG};
    }}
    QTreeWidget::item:selected {{
        background-color: #DBE8FB;
        color: #000000;
    }}
    QTreeWidget::branch {{
        background-color: {COR_PAINEL};
    }}
    QTreeWidget::branch:has-children:!has-siblings:closed,
    QTreeWidget::branch:closed:has-children:has-siblings {{
        image: none;
        border-image: none;
    }}
"""


def make_btn_style(border=COR_BORDA, hover=COR_DESTAQUE, pressed=COR_MARINHO,
                   bg=COR_PAINEL, text=COR_TEXTO, fs=11, primario=False):
    """Estilo de botão do Visualizador. `primario=True`: azul Projeart cheio (ação principal da tela)."""
    if primario:
        bg, text, border = COR_DESTAQUE, "#ffffff", COR_DESTAQUE
    hover_bg = COR_MARINHO if primario else COR_DESTAQUE
    return f"""
        QPushButton {{
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #E3E8EE, stop:1 #CDD4DE);
            color: #000000;
            font-weight: bold;
            font-size: {fs}px;
            padding: 8px 12px;
            border: 1px solid {border};
            border-radius: 4px;
            margin: 3px;
        }}
        QPushButton:hover {{
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #D9DFE7, stop:1 #C2CAD5);
            border-color: {hover};
        }}
        QPushButton:pressed {{
            background: #C2CAD5;
        }}
        QPushButton:disabled {{
            color: #8A929E;
            border-color: #B9C0CA;
        }}
    """
