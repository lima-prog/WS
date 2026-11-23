# -*- coding: utf-8 -*-
"""
Paleta visual compartilhada pela maioria das abas (Corte, Espelhar,
Relatório de Fluxos, Auditoria, Conversor, Renomear DXF).
A aba Visualizador usa uma paleta PROPRIA (visualizador/estilo.py) por
decisao explicita do projeto -- ver nota la (reconfirmado ao trocar de
paleta abaixo: usuário pediu explicitamente pra deixar o Visualizador como
está).

Ajuste (paleta clara "Papel & Grafite"): trocada a paleta cinza-industrial
escura original por uma paleta clara, a pedido do usuário -- ele reportou
que o visual escuro "não fica limpo" e que praticamente tudo (fundo do
app, card e campo de texto) usava a MESMA cor, sem contraste nenhum entre
as camadas. Consertado criando uma escada de contraste real:

    COR_BG (fundo da tela, papel cru)
        > COR_PAINEL (superfície do card, papel branco)
        > COR_CAMPO (campo de texto DENTRO do card, tom do fundo de novo
          -- fica "afundado" em relação ao branco do card ao redor, em vez
          de se confundir com ele)

Além disso, a maioria das bordas fortes virou border sutil (mesmo tom
próximo do fundo, quase invisível) -- Qt Style Sheets não têm suporte a
"box-shadow" de verdade (diferente de CSS de navegador), então a
"elevação" dos cards não pôde ser feita por sombra; o substituto usado foi
essa escada de contraste + bordas bem discretas, só ficando com peso
visual mesmo no campo em foco (o usuário está editando aquele campo
específico).

`COR_AZUL` (nome antigo) virou `COR_DESTAQUE`: a cor de destaque deixou de
ser azul (agora é um laranja queimado, da proposta que o usuário escolheu)
-- manter o nome antigo ia deixar `COR_AZUL = "#C1611D"` (um laranja) no
código, o que confundiria qualquer um lendo depois. Todos os arquivos que
importavam `COR_AZUL` foram atualizados junto.
"""
from PyQt5.QtGui import QColor

# --- Paleta oficial da Projeart (imagem "Paleta de cores" enviada pelo usuário)
#     #1003AA azul | #1A1A37 azul-marinho | #1D1D1B quase preto
#     #4D4C4C cinza escuro | #CCCCCC cinza | #E6E6E6 cinza claro
# Tema claro: fundo cinza claro, cards brancos, texto quase preto, azul da
# marca nos botões principais e destaques. Visualizador mantém a paleta própria.
COR_AZUL_MARCA  = "#1003AA"   # azul Projeart (destaque principal)
COR_MARINHO     = "#1A1A37"   # azul-marinho (hover / realces escuros)

COR_BG          = "#E6E6E6"   # fundo da tela (cinza claro da marca)
COR_PAINEL      = "#FFFFFF"   # superfície do card (branco)
COR_CAMPO       = "#F3F3F3"   # campo de texto (levemente mais escuro que o card branco)
COR_BORDA       = "#CCCCCC"   # linha sutil (cinza da marca)
COR_TEXTO       = "#1D1D1B"   # texto principal (quase preto da marca)
COR_TEXTO_SUB   = "#4D4C4C"   # texto secundário/legenda (cinza escuro da marca)
COR_DESTAQUE    = COR_AZUL_MARCA   # destaque/ação (azul Projeart)
COR_VERDE       = "#1A7F37"   # sucesso / ação "ir em frente"
COR_VERMELHO    = "#B42318"   # erro
COR_AMARELO     = "#8A5A1E"   # aviso

CORES_PARTES = [
    QColor(16,    3, 170, 210),   # azul Projeart
    QColor(35,  134,  54, 210),   # verde
    QColor(188, 140,  24, 210),   # amarelo
    QColor(163,  72, 161, 210),   # roxo
    QColor(214,  84,  74, 210),   # vermelho
]

ESTILO_GERAL = f"""
QMainWindow, QWidget {{
    background-color: {COR_BG};
    color: {COR_TEXTO};
    font-family: 'Segoe UI', Arial, sans-serif;
}}
QTabWidget::pane {{
    border: 1px solid {COR_BORDA};
    border-radius: 6px;
    top: -1px;
}}
QTabBar::tab {{
    background: {COR_PAINEL};
    color: {COR_TEXTO_SUB};
    border: 1px solid {COR_BORDA};
    border-bottom: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    padding: 8px 18px;
    margin-right: 2px;
    font-weight: bold;
    font-size: 12px;
}}
QTabBar::tab:selected {{
    background: {COR_BG};
    color: {COR_DESTAQUE};
    border-color: {COR_DESTAQUE};
}}
QTabBar::tab:hover {{
    color: {COR_TEXTO};
}}
QGroupBox {{
    background-color: {COR_PAINEL};
    border: 1px solid {COR_BORDA};
    border-radius: 6px;
    margin-top: 12px;
    padding: 8px;
    font-weight: bold;
    color: {COR_TEXTO};
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
    color: {COR_DESTAQUE};
}}
QTextEdit {{
    background-color: {COR_CAMPO};
    border: 1px solid {COR_BORDA};
    border-radius: 4px;
    color: {COR_TEXTO};
    font-family: 'Consolas', monospace;
    font-size: 11px;
    padding: 4px;
}}
QLineEdit {{
    background-color: {COR_CAMPO};
    border: 1px solid {COR_BORDA};
    border-radius: 5px;
    color: {COR_TEXTO};
    padding: 6px 10px;
    selection-background-color: {COR_DESTAQUE};
    selection-color: white;
}}
QLineEdit:focus {{
    border: 1px solid {COR_DESTAQUE};
}}
QLineEdit:disabled {{
    color: {COR_TEXTO_SUB};
    background-color: {COR_BG};
}}
/* transparente: dentro dos cards brancos o rótulo não pode formar uma
   "faixa" cinza (fundo da tela) atrás do texto */
QLabel {{ color: {COR_TEXTO}; background: transparent; }}
QCheckBox {{ color: {COR_TEXTO}; spacing: 6px; background: transparent; }}
QCheckBox::indicator {{
    width: 14px; height: 14px;
    border: 1px solid {COR_BORDA};
    border-radius: 3px;
    background: {COR_CAMPO};
}}
QCheckBox::indicator:checked {{
    background: {COR_DESTAQUE};
    border-color: {COR_DESTAQUE};
}}
QSpinBox {{
    background-color: {COR_CAMPO};
    border: 1px solid {COR_BORDA};
    border-radius: 4px;
    color: {COR_TEXTO};
    padding: 3px 6px;
}}
QProgressBar {{
    background-color: {COR_CAMPO};
    border: 1px solid {COR_BORDA};
    border-radius: 4px;
    height: 8px;
    text-align: center;
    color: transparent;
}}
QProgressBar::chunk {{
    background-color: {COR_DESTAQUE};
    border-radius: 4px;
}}
QPushButton {{
    border-radius: 5px;
    padding: 7px 16px;
    font-weight: bold;
    font-size: 12px;
    border: none;
}}
QPushButton#btn_processar {{
    background-color: {COR_DESTAQUE};
    color: white;
}}
QPushButton#btn_processar:hover  {{ background-color: {COR_MARINHO}; }}
QPushButton#btn_processar:disabled {{ background-color: {COR_BORDA}; color: #8A8A8A; }}
QPushButton#btn_limpar {{
    background-color: {COR_PAINEL};
    color: {COR_TEXTO};
    border: 1px solid {COR_BORDA};
}}
QPushButton#btn_limpar:hover {{ background-color: {COR_BG}; }}
QScrollBar:vertical {{
    background: {COR_PAINEL}; width: 8px; border-radius: 4px;
}}
QScrollBar::handle:vertical {{
    background: {COR_BORDA}; border-radius: 4px; min-height: 20px;
}}
"""
