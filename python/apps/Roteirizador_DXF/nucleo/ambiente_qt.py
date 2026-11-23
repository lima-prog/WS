# -*- coding: utf-8 -*-
"""
Variáveis de ambiente do Qt que precisam ser setadas ANTES de qualquer
`import PyQt5` ou `import pyqtgraph` acontecer em QUALQUER lugar do programa
(inclusive indiretamente, através de outro módulo nosso).

Por isso este módulo não importa nada do PyQt5/pyqtgraph — só usa `os` — e
`main.py` importa ele como a PRIMEIRA linha de código, antes de qualquer
outro módulo nosso (que aí sim importam PyQt5/pyqtgraph).

Histórico do porquê cada uma existe (mantido aqui pra não se perder o
contexto se alguém precisar mexer de novo):

- QT_STYLE_OVERRIDE=Fusion: o Qt, ao construir o QApplication, tenta
  inicializar o estilo visual NATIVO do Windows ("Vista") antes mesmo de
  terminar de se montar — em algumas combinações de Windows/driver de vídeo
  isso cria um widget auxiliar interno cedo demais e crasha com "QWidget:
  Must construct a QApplication before a QWidget", sem gerar nenhuma
  exceção Python. Forçar Fusion evita o Qt sequer tentar tocar no estilo
  nativo Vista.

- PYQTGRAPH_QT_LIB=PyQt5: o pyqtgraph escolhe sozinho qual biblioteca Qt
  usar (PyQt5, PySide6, PyQt6...). Se a máquina tiver mais de uma
  instalada (ex: PySide6 de outro projeto), ele pode escolher uma
  DIFERENTE da que o resto do programa usa — aí ficam dois Qt rodando no
  mesmo processo, cada um com seu próprio QApplication "global"
  independente, e widgets do pyqtgraph não enxergam o QApplication que a
  gente criou. Essa variável obriga o pyqtgraph a usar sempre o PyQt5.
"""
import os

os.environ.setdefault("QT_STYLE_OVERRIDE", "Fusion")
os.environ.setdefault("PYQTGRAPH_QT_LIB", "PyQt5")
