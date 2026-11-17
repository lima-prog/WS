"""
PyQt5 "DE MENTIRA" — para rodar a lógica dos programas do Validador de Fluxos DENTRO do PPCPM,
sem janela nenhuma.

Os programas novos (Agrupador | Base, Impressão Casada, Multi obra, Grupo LIC, Fluxo 4) são uma tela
PyQt5 (validador_fluxos_ppcp.py, copiado SEM NENHUMA ALTERAÇÃO). Aqui cada classe do Qt vira um objeto
que só GUARDA o estado (texto do rótulo, itens da árvore, caixas marcadas, cores…). Assim a tela original
roda inteira — inclusive o código que monta as árvores de resultado — e o PPCPM mostra esse estado no
navegador, no padrão do sistema.

O que precisa de uma pessoa (escolher arquivo, responder uma pergunta, digitar um texto) vira um PEDIDO
para a tela do PPCPM: a tarefa espera a resposta e continua de onde parou.
"""
from __future__ import annotations

import itertools
import os
import re
import sys
import threading
import types

# ------------------------------------------------------------------ contexto (um por sessão)
_tick = itertools.count(1)
_tick_lock = threading.Lock()


_local = threading.local()      # qual aba do PPCPM pediu a tarefa que está rodando nesta linha de execução


def aba_atual():
    return getattr(_local, "aba", None)


def definir_aba(aba):
    _local.aba = aba


def novo_tick() -> int:
    with _tick_lock:
        return next(_tick)


class Contexto:
    """Mensagens e pedidos (arquivo, pergunta…) da sessão que está rodando a tela."""

    def __init__(self):
        self.msgs: list[dict] = []           # avisos para mostrar (QMessageBox sem pergunta)
        self.pedido: dict | None = None      # o que a tarefa está esperando da pessoa
        self._resp = None
        self._ev = threading.Event()
        self._lock = threading.Lock()
        self.saida_padrao = None             # função (sugestao) -> caminho de saída
        self.pasta_temp = ""                 # arquivos enviados pelo navegador ficam aqui
        self.cancelado = False

    # chamado pela tarefa (bloqueia até a pessoa responder)
    def pedir(self, pedido: dict, timeout: float = 1800):
        with self._lock:
            self.pedido = dict(pedido, id=novo_tick(), aba=aba_atual())
            self._resp = None
            self._ev.clear()
        ok = self._ev.wait(timeout)
        with self._lock:
            r = self._resp if ok else None
            self.pedido = None
        return r

    # chamado pela tela do PPCPM
    def responder(self, pid, resposta) -> bool:
        with self._lock:
            if not self.pedido or self.pedido.get("id") != pid:
                return False
            self._resp = resposta
            self._ev.set()
            return True

    def avisar(self, tipo, titulo, texto, detalhes=""):
        self.msgs.append({"id": novo_tick(), "aba": aba_atual(), "tipo": tipo, "titulo": str(titulo or ""), "texto": str(texto or ""),
                          "detalhes": str(detalhes or "")})
        del self.msgs[:-60]


CTX = Contexto()          # trocado por sessão (ver motor.py)


def ctx() -> Contexto:
    return CTX


# ------------------------------------------------------------------ peças básicas
class _Flag(int):
    def __or__(self, o):
        return _Flag(int(self) | int(o))

    __ror__ = __or__

    def __and__(self, o):
        return _Flag(int(self) & int(o))

    __rand__ = __and__

    def __invert__(self):
        return _Flag(~int(self))


class _QtMeta(type):
    def __getattr__(cls, n):
        if n.startswith("_") or "_" in n:
            raise AttributeError(n)
        return _Flag(0)


class _Coisa:
    """Valor neutro devolvido por qualquer método que não importa (aceita tudo, vale 0/vazio)."""

    def __init__(self, *a, **k):
        pass

    def __getattr__(self, n):
        if n.startswith("__"):
            raise AttributeError(n)
        return _nada

    def __call__(self, *a, **k):
        return _Coisa()

    def __bool__(self):
        return False

    def __int__(self):
        return 0

    def __float__(self):
        return 0.0

    def __index__(self):
        return 0

    def __iter__(self):
        return iter(())

    def __len__(self):
        return 0

    def __str__(self):
        return ""

    def __add__(self, o):
        return o if isinstance(o, (int, float)) else 0

    __radd__ = __add__

    def __sub__(self, o):
        return 0

    __rsub__ = __mul__ = __rmul__ = __truediv__ = __floordiv__ = __sub__

    def __lt__(self, o):
        return False

    __gt__ = __le__ = __ge__ = __lt__

    def __or__(self, o):
        return o

    __ror__ = __or__


def _nada(*a, **k):
    return _Coisa()


class Sinal:
    def __init__(self):
        self._fns = []

    def connect(self, fn, *a, **k):
        self._fns.append(fn)

    def disconnect(self, fn=None):
        if fn is None:
            self._fns.clear()
        elif fn in self._fns:
            self._fns.remove(fn)

    def emit(self, *args):
        for fn in list(self._fns):
            _chamar(fn, args)


def _chamar(fn, args):
    """Chama o slot com quantos argumentos ele aceitar (como o Qt faz)."""
    import inspect
    try:
        sig = inspect.signature(fn)
        ps = list(sig.parameters.values())
        if any(p.kind == p.VAR_POSITIONAL for p in ps):
            return fn(*args)
        n = len([p for p in ps if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)])
        return fn(*args[:n])
    except (TypeError, ValueError):
        return fn(*args)


class pyqtSignal:
    """Descritor: cada objeto ganha o seu próprio Sinal."""

    def __init__(self, *tipos, **k):
        self._nome = None

    def __set_name__(self, dono, nome):
        self._nome = nome

    def __get__(self, obj, tipo=None):
        if obj is None:
            return self
        s = obj.__dict__.get("__sinal_" + self._nome)
        if s is None:
            s = Sinal()
            obj.__dict__["__sinal_" + self._nome] = s
        return s


def pyqtSlot(*a, **k):
    def dec(fn):
        return fn
    return dec


_NOMES_SINAIS = {
    "clicked", "toggled", "pressed", "released", "stateChanged", "textChanged", "textEdited", "returnPressed",
    "editingFinished", "currentIndexChanged", "currentTextChanged", "activated", "itemClicked", "itemDoubleClicked",
    "itemChanged", "itemActivated", "currentItemChanged", "itemSelectionChanged", "itemExpanded", "itemCollapsed",
    "currentRowChanged", "cellClicked", "cellDoubleClicked", "cellChanged", "valueChanged", "timeout", "finished",
    "started", "triggered", "accepted", "rejected", "customContextMenuRequested", "linkActivated", "sectionClicked",
    "buttonClicked", "idClicked", "currentChanged", "tabBarClicked", "sectionResized", "rowsInserted",
}

_QT_COM_TRACO = {"raise_", "exec_", "print_"}

_criados = []          # ordem de criação dos rótulos (para mostrar o conteúdo dos diálogos)
_criados_lock = threading.Lock()


class QObject(metaclass=_QtMeta):
    destroyed = pyqtSignal()

    def __init__(self, *a, **k):
        d = self.__dict__
        d["_ver"] = novo_tick()
        d["_props"] = {}
        d["_pai"] = None
        par = k.get("parent")
        if par is None:
            for x in a:
                if isinstance(x, QObject):
                    par = x
                    break
        d["_pai"] = par

    # tudo que a tela chamar e não estiver aqui: não faz nada. Nome com "_" é atributo do PROGRAMA
    # (ex.: imp_caminhos_cnc), não do Qt: aí tem que dar AttributeError para o getattr(self, x, padrão) funcionar.
    def __getattr__(self, n):
        if n.startswith("_") or ("_" in n and n not in _QT_COM_TRACO):
            raise AttributeError(n)
        if n in _NOMES_SINAIS:
            s = Sinal()
            self.__dict__[n] = s
            return s
        return _nada

    def _tocar(self):
        self.__dict__["_ver"] = novo_tick()

    def setObjectName(self, n):
        self._props["objectName"] = n

    def objectName(self):
        return self._props.get("objectName", "")

    def setProperty(self, k, v):
        self._props[k] = v

    def property(self, k):
        return self._props.get(k)

    def parent(self):
        return self._pai

    def blockSignals(self, b):
        old = self.__dict__.get("_bloq", False)
        self.__dict__["_bloq"] = bool(b)
        return old

    def signalsBlocked(self):
        return self.__dict__.get("_bloq", False)

    def _emitir(self, nome, *args):
        if self.__dict__.get("_bloq"):
            return
        getattr(self, nome).emit(*args)

    def deleteLater(self):
        pass


class QWidget(QObject):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        d = self.__dict__
        d["_vis"] = True
        d["_ativo"] = True
        d["_dica"] = ""
        d["_estilo"] = ""
        d["_layout"] = None

    def setVisible(self, v):
        self._vis = bool(v)
        self._tocar()

    def show(self):
        self.setVisible(True)

    def hide(self):
        self.setVisible(False)

    def isVisible(self):
        return self._vis

    def isHidden(self):
        return not self._vis

    def setHidden(self, h):
        self.setVisible(not h)

    def setEnabled(self, v):
        self._ativo = bool(v)
        self._tocar()

    def setDisabled(self, v):
        self.setEnabled(not v)

    def isEnabled(self):
        return self._ativo

    def setToolTip(self, t):
        self._dica = str(t or "")

    def toolTip(self):
        return self._dica

    def setStyleSheet(self, s):
        self._estilo = str(s or "")
        self._tocar()

    def styleSheet(self):
        return self._estilo

    def layout(self):
        return self._layout

    def setLayout(self, l):
        self._layout = l

    def window(self):
        return self

    def font(self):
        return QFont()

    def palette(self):
        return _Coisa()

    def width(self):
        return 1000

    def height(self):
        return 600

    def winId(self):
        return 0


# ---------- layouts
class _Layout(QObject):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self._itens = []
        if a and isinstance(a[0], QWidget):
            a[0].__dict__["_layout"] = self

    def addWidget(self, w, *a, **k):
        self._itens.append(w)

    def addLayout(self, l, *a, **k):
        self._itens.append(l)

    insertWidget = addWidget

    def count(self):
        return len(self._itens)

    def itemAt(self, i):
        return _Coisa()

    def takeAt(self, i):
        return _Coisa()


class QVBoxLayout(_Layout):
    pass


class QHBoxLayout(_Layout):
    pass


class QGridLayout(_Layout):
    pass


class QFormLayout(_Layout):
    def addRow(self, *a, **k):
        pass


class QStackedLayout(_Layout):
    pass


# ---------- widgets com texto
class _ComTexto(QWidget):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        t = ""
        for x in a:
            if isinstance(x, str):
                t = x
                break
        self.__dict__["_texto"] = t

    def setText(self, t):
        self._texto = "" if t is None else str(t)
        self._tocar()

    def text(self):
        return self._texto


class QLabel(_ComTexto):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        with _criados_lock:
            _criados.append(self)
            del _criados[:-4000]

    def setPixmap(self, *a):
        pass

    def setWordWrap(self, *a):
        pass


class QPushButton(_ComTexto):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.__dict__["_checavel"] = False
        self.__dict__["_marcado"] = False

    def setCheckable(self, b):
        self._checavel = bool(b)

    def isCheckable(self):
        return self._checavel

    def setChecked(self, b):
        b = bool(b)
        if b != self._marcado:
            self._marcado = b
            self._tocar()
            self._emitir("toggled", b)

    def isChecked(self):
        return self._marcado

    def click(self):
        if self._checavel:
            self.setChecked(not self._marcado)
        self._emitir("clicked", self._marcado)

    def setMenu(self, m):
        self._menu = m


class QToolButton(QPushButton):
    pass


class QCheckBox(QPushButton):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self._checavel = True

    def setChecked(self, b):
        b = bool(b)
        if b != self._marcado:
            self._marcado = b
            self._tocar()
            self._emitir("toggled", b)
            self._emitir("stateChanged", 2 if b else 0)

    def checkState(self):
        return 2 if self._marcado else 0

    def setCheckState(self, s):
        self.setChecked(int(s) == 2)


class QRadioButton(QCheckBox):
    pass


class QButtonGroup(QObject):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self._botoes = []

    def addButton(self, b, i=-1):
        self._botoes.append((b, i))

    def buttons(self):
        return [b for b, _ in self._botoes]

    def checkedButton(self):
        for b, _ in self._botoes:
            if b.isChecked():
                return b
        return None

    def checkedId(self):
        for b, i in self._botoes:
            if b.isChecked():
                return i
        return -1

    def setExclusive(self, *a):
        pass


class QLineEdit(_ComTexto):
    def setText(self, t):
        t = "" if t is None else str(t)
        if t != self._texto:
            self._texto = t
            self._tocar()
            self._emitir("textChanged", t)

    def clear(self):
        self.setText("")

    def setPlaceholderText(self, t):
        self._props["placeholder"] = str(t)


class QPlainTextEdit(QWidget):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        t = ""
        for x in a:
            if isinstance(x, str):
                t = x
        self.__dict__["_texto"] = t

    def setPlainText(self, t):
        t = "" if t is None else str(t)
        if t != self._texto:
            self._texto = t
            self._tocar()
            self._emitir("textChanged")

    setText = setPlainText
    setHtml = setPlainText

    def toPlainText(self):
        return self._texto

    toHtml = toPlainText

    def appendPlainText(self, t):
        self.setPlainText((self._texto + "\n" if self._texto else "") + str(t))

    append = appendPlainText

    def clear(self):
        self.setPlainText("")

    def setPlaceholderText(self, t):
        self._props["placeholder"] = str(t)


QTextEdit = QPlainTextEdit
QTextBrowser = QPlainTextEdit


class QComboBox(QWidget):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.__dict__["_itens"] = []
        self.__dict__["_idx"] = -1

    def addItem(self, *a):
        txt, dado = "", None
        for x in a:
            if isinstance(x, str) and not txt:
                txt = x
            elif not isinstance(x, (QIcon,)) and x is not None and txt:
                dado = x
        self._itens.append([txt, dado])
        if self._idx < 0:
            self._idx = 0
            self._emitir("currentIndexChanged", 0)
        self._tocar()

    def addItems(self, lst):
        for t in lst:
            self.addItem(str(t))

    def insertItem(self, i, *a):
        self.addItem(*a)
        it = self._itens.pop()
        self._itens.insert(i, it)

    def clear(self):
        self._itens.clear()
        self._idx = -1
        self._tocar()

    def count(self):
        return len(self._itens)

    def currentIndex(self):
        return self._idx

    def setCurrentIndex(self, i):
        i = int(i)
        if i != self._idx and -1 <= i < len(self._itens):
            self._idx = i
            self._tocar()
            self._emitir("currentIndexChanged", i)
            self._emitir("currentTextChanged", self.currentText())

    def currentText(self):
        return self._itens[self._idx][0] if 0 <= self._idx < len(self._itens) else ""

    def currentData(self, *a):
        return self._itens[self._idx][1] if 0 <= self._idx < len(self._itens) else None

    def itemText(self, i):
        return self._itens[i][0] if 0 <= i < len(self._itens) else ""

    def itemData(self, i, *a):
        return self._itens[i][1] if 0 <= i < len(self._itens) else None

    def setItemText(self, i, t):
        if 0 <= i < len(self._itens):
            self._itens[i][0] = str(t)
            self._tocar()

    def findText(self, t, *a):
        for i, (x, _) in enumerate(self._itens):
            if x == t:
                return i
        return -1

    def findData(self, d, *a):
        for i, (_, x) in enumerate(self._itens):
            if x == d:
                return i
        return -1

    def setCurrentText(self, t):
        i = self.findText(t)
        if i >= 0:
            self.setCurrentIndex(i)

    def removeItem(self, i):
        if 0 <= i < len(self._itens):
            self._itens.pop(i)
            if self._idx >= len(self._itens):
                self._idx = len(self._itens) - 1
            self._tocar()


class QSpinBox(QWidget):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.__dict__["_valor"] = 0

    def setValue(self, v):
        if v != self._valor:
            self._valor = v
            self._tocar()
            self._emitir("valueChanged", v)

    def value(self):
        return self._valor


QDoubleSpinBox = QSpinBox


# ---------- cores e fontes
class QColor(metaclass=_QtMeta):
    _NOMES = {"red": "#ff0000", "green": "#008000", "blue": "#0000ff", "black": "#000000", "white": "#ffffff",
              "gray": "#808080", "grey": "#808080", "yellow": "#ffff00", "orange": "#ffa500", "darkGray": "#404040",
              "lightGray": "#c0c0c0", "darkGreen": "#006400", "darkRed": "#8b0000", "transparent": "transparent"}

    def __init__(self, *a):
        self.hex = ""
        if not a:
            return
        x = a[0]
        if isinstance(x, QColor):
            self.hex = x.hex
        elif isinstance(x, str):
            self.hex = self._NOMES.get(x, x)
        elif len(a) >= 3:
            self.hex = "#%02x%02x%02x" % (int(a[0]) & 255, int(a[1]) & 255, int(a[2]) & 255)
        elif isinstance(x, int):
            self.hex = {2: "#000000", 3: "#ffffff", 7: "#ff0000", 8: "#008000", 9: "#0000ff", 5: "#808080"}.get(int(x), "")

    def name(self, *a):
        return self.hex

    def isValid(self):
        return bool(self.hex)

    def lighter(self, *a):
        return QColor(self)

    darker = lighter

    def setAlpha(self, *a):
        pass

    def red(self):
        return _hex_rgb(self.hex)[0]

    def green(self):
        return _hex_rgb(self.hex)[1]

    def blue(self):
        return _hex_rgb(self.hex)[2]


def _hex_rgb(h):
    try:
        h = h.lstrip("#")
        return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    except Exception:
        return 0, 0, 0


def _cor(x) -> str:
    if x is None:
        return ""
    if isinstance(x, QColor):
        return x.hex
    if isinstance(x, QBrush):
        return x.cor.hex
    if isinstance(x, str):
        return QColor(x).hex
    if isinstance(x, int):
        return QColor(x).hex
    return ""


class QBrush(metaclass=_QtMeta):
    def __init__(self, c=None, *a):
        self.cor = QColor(c) if c is not None else QColor()

    def color(self):
        return self.cor


class QFont(metaclass=_QtMeta):
    def __init__(self, *a, **k):
        self.negrito = False
        self.italico = False

    def setBold(self, b):
        self.negrito = bool(b)

    def bold(self):
        return self.negrito

    def setItalic(self, b):
        self.italico = bool(b)

    def italic(self):
        return self.italico

    def __getattr__(self, n):
        if n.startswith("__"):
            raise AttributeError(n)
        return _nada


class QIcon(metaclass=_QtMeta):
    def __init__(self, *a, **k):
        pass

    def __getattr__(self, n):
        if n.startswith("__"):
            raise AttributeError(n)
        return _nada


class QPixmap(QIcon):
    pass


class QPainter(QIcon):
    pass


class QPen(QIcon):
    pass


class QPalette(QIcon):
    pass


class QFontMetrics(QIcon):
    def horizontalAdvance(self, t):
        return 7 * len(str(t))

    width = horizontalAdvance


# ---------- listas
class QListWidgetItem(metaclass=_QtMeta):
    def __init__(self, *a):
        self.lista = None
        self.t = ""
        self.cor = ""
        self.fundo = ""
        self.dados = {}
        self.check = None
        self.dica = ""
        self.negrito = False
        self.oculto = False
        self.flags_ = _Flag(0)
        for x in a:
            if isinstance(x, str):
                self.t = x
            elif isinstance(x, QListWidget):
                x.addItem(self)

    def _tocar(self):
        if self.lista is not None:
            self.lista._tocar()

    def text(self):
        return self.t

    def setText(self, t):
        self.t = str(t)
        self._tocar()

    def setForeground(self, c):
        self.cor = _cor(c)
        self._tocar()

    def setBackground(self, c):
        self.fundo = _cor(c)
        self._tocar()

    def setData(self, role, v):
        self.dados[int(role)] = v

    def data(self, role):
        return self.dados.get(int(role))

    def setCheckState(self, s):
        self.check = int(s)
        self._tocar()

    def checkState(self):
        return self.check or 0

    def setToolTip(self, t):
        self.dica = str(t)

    def toolTip(self):
        return self.dica

    def setFlags(self, f):
        self.flags_ = f

    def flags(self):
        return self.flags_

    def setFont(self, f):
        self.negrito = bool(getattr(f, "negrito", False))

    def font(self):
        f = QFont()
        f.negrito = self.negrito
        return f

    def setHidden(self, h):
        self.oculto = bool(h)
        self._tocar()

    def isHidden(self):
        return self.oculto

    def listWidget(self):
        return self.lista

    def setSelected(self, *a):
        pass

    def setIcon(self, *a):
        pass

    def setSizeHint(self, *a):
        pass

    def setTextAlignment(self, *a):
        pass


class QListWidget(QWidget):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.__dict__["_itens"] = []
        self.__dict__["_atual"] = -1

    def addItem(self, x):
        it = x if isinstance(x, QListWidgetItem) else QListWidgetItem(str(x))
        it.lista = self
        self._itens.append(it)
        self._tocar()

    def addItems(self, lst):
        for t in lst:
            self.addItem(str(t))

    def insertItem(self, i, x):
        self.addItem(x)
        it = self._itens.pop()
        self._itens.insert(i, it)

    def clear(self):
        self._itens.clear()
        self._atual = -1
        self._tocar()

    def count(self):
        return len(self._itens)

    def item(self, i):
        return self._itens[i] if 0 <= i < len(self._itens) else None

    def takeItem(self, i):
        if 0 <= i < len(self._itens):
            it = self._itens.pop(i)
            self._tocar()
            return it
        return None

    def row(self, it):
        try:
            return self._itens.index(it)
        except ValueError:
            return -1

    def currentRow(self):
        return self._atual

    def setCurrentRow(self, i):
        self._atual = i
        self._emitir("currentRowChanged", i)

    def currentItem(self):
        return self.item(self._atual)

    def setCurrentItem(self, it):
        self.setCurrentRow(self.row(it))

    def selectedItems(self):
        it = self.currentItem()
        return [it] if it else []

    def findItems(self, t, *a):
        return [i for i in self._itens if i.t == t]


class QTreeWidgetItem(metaclass=_QtMeta):
    def __init__(self, *a):
        self.pai = None
        self.arvore = None
        self.filhos = []
        self.t = []
        self.cor = {}
        self.fundo = {}
        self.negrito = set()
        self.dados = {}
        self.check = {}
        self.dica = {}
        self.exp = False
        self.oculto = False
        self.flags_ = _Flag(0)
        self.span = False
        dono = None
        for x in a:
            if isinstance(x, (QTreeWidget, QTreeWidgetItem)):
                dono = x
            elif isinstance(x, (list, tuple)):
                self.t = [str(v) if v is not None else "" for v in x]
            elif isinstance(x, str):
                self.t = [x]
        if isinstance(dono, QTreeWidget):
            dono.addTopLevelItem(self)
        elif isinstance(dono, QTreeWidgetItem):
            dono.addChild(self)

    # --- avisar a árvore que mudou
    def _raiz(self):
        n = self
        while n.pai is not None:
            n = n.pai
        return n.arvore

    def _tocar(self):
        a = self._raiz()
        if a is not None:
            a._tocar()

    def _pendurar(self, arvore):
        self.arvore = arvore
        for f in self.filhos:
            f._pendurar(None)

    # --- texto
    def text(self, c=0):
        return self.t[c] if 0 <= c < len(self.t) else ""

    def setText(self, c, txt):
        while len(self.t) <= c:
            self.t.append("")
        self.t[c] = "" if txt is None else str(txt)
        self._tocar()

    def columnCount(self):
        return len(self.t)

    # --- filhos
    def addChild(self, it):
        it.pai = self
        it.arvore = None
        self.filhos.append(it)
        self._tocar()

    def addChildren(self, its):
        for it in its:
            self.addChild(it)

    def insertChild(self, i, it):
        self.addChild(it)
        self.filhos.pop()
        self.filhos.insert(i, it)

    def child(self, i):
        return self.filhos[i] if 0 <= i < len(self.filhos) else None

    def childCount(self):
        return len(self.filhos)

    def indexOfChild(self, it):
        try:
            return self.filhos.index(it)
        except ValueError:
            return -1

    def takeChild(self, i):
        if 0 <= i < len(self.filhos):
            it = self.filhos.pop(i)
            it.pai = None
            self._tocar()
            return it
        return None

    def takeChildren(self):
        fs = list(self.filhos)
        self.filhos.clear()
        for f in fs:
            f.pai = None
        self._tocar()
        return fs

    def removeChild(self, it):
        i = self.indexOfChild(it)
        if i >= 0:
            self.takeChild(i)

    def parent(self):
        return self.pai

    def treeWidget(self):
        return self._raiz()

    # --- aparência e dados
    def setForeground(self, c, cor):
        self.cor[c] = _cor(cor)
        self._tocar()

    def foreground(self, c):
        return QBrush(self.cor.get(c) or None)

    def setBackground(self, c, cor):
        self.fundo[c] = _cor(cor)
        self._tocar()

    def background(self, c):
        return QBrush(self.fundo.get(c) or None)

    def setFont(self, c, f):
        if getattr(f, "negrito", False):
            self.negrito.add(c)
        else:
            self.negrito.discard(c)
        self._tocar()

    def font(self, c):
        f = QFont()
        f.negrito = c in self.negrito
        return f

    def setData(self, c, role, v):
        self.dados[(c, int(role))] = v
        if int(role) == 0:
            self.setText(c, v)
        elif int(role) == 10:
            self.check[c] = int(v)

    def data(self, c, role):
        if int(role) == 0:
            return self.text(c)
        return self.dados.get((c, int(role)))

    def setCheckState(self, c, s):
        self.check[c] = int(s)
        self._tocar()

    def checkState(self, c):
        return self.check.get(c, 0)

    def setToolTip(self, c, t):
        self.dica[c] = str(t)

    def toolTip(self, c):
        return self.dica.get(c, "")

    def setExpanded(self, b):
        self.exp = bool(b)
        self._tocar()

    def isExpanded(self):
        return self.exp

    def setHidden(self, h):
        self.oculto = bool(h)
        self._tocar()

    def isHidden(self):
        return self.oculto

    def setFlags(self, f):
        self.flags_ = f

    def flags(self):
        return self.flags_

    def setFirstColumnSpanned(self, b):
        self.span = bool(b)

    def setSelected(self, *a):
        pass

    def isSelected(self):
        a = self._raiz()
        return a is not None and a._atual is self

    def setIcon(self, *a):
        pass

    def setTextAlignment(self, *a):
        pass

    def setSizeHint(self, *a):
        pass

    def setDisabled(self, *a):
        pass

    def sortChildren(self, *a):
        pass

    def __lt__(self, o):
        return self.text(0) < o.text(0)


class _Cabecalho(metaclass=_QtMeta):
    def __getattr__(self, n):
        if n.startswith("__"):
            raise AttributeError(n)
        return _nada


class QTreeWidget(QWidget):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        d = self.__dict__
        d["_raiz"] = QTreeWidgetItem()
        d["_raiz"].arvore = self
        d["_cab"] = []
        d["_atual"] = None
        d["_prof"] = None

    def invisibleRootItem(self):
        return self._raiz

    def setHeaderLabels(self, lst):
        self._cab = [str(x) for x in lst]
        self._tocar()

    def setHeaderLabel(self, t):
        self.setHeaderLabels([t])

    def headerItem(self):
        it = QTreeWidgetItem(self._cab)
        return it

    def header(self):
        return _Cabecalho()

    def setColumnCount(self, n):
        pass

    def columnCount(self):
        return len(self._cab) or 1

    def clear(self):
        self._raiz.filhos.clear()
        self._atual = None
        self._prof = None
        self._tocar()

    def addTopLevelItem(self, it):
        it.pai = None
        it.arvore = self
        self._raiz.filhos.append(it)
        self._tocar()

    def addTopLevelItems(self, its):
        for it in its:
            self.addTopLevelItem(it)

    def insertTopLevelItem(self, i, it):
        self.addTopLevelItem(it)
        self._raiz.filhos.pop()
        self._raiz.filhos.insert(i, it)

    def insertTopLevelItems(self, i, its):
        for k, it in enumerate(its):
            self.insertTopLevelItem(i + k, it)

    def topLevelItem(self, i):
        return self._raiz.child(i)

    def topLevelItemCount(self):
        return len(self._raiz.filhos)

    def indexOfTopLevelItem(self, it):
        return self._raiz.indexOfChild(it)

    def takeTopLevelItem(self, i):
        if 0 <= i < len(self._raiz.filhos):
            it = self._raiz.filhos.pop(i)
            it.arvore = None
            self._tocar()
            return it
        return None

    def currentItem(self):
        return self._atual

    def setCurrentItem(self, it, *a):
        ant = self._atual
        self._atual = it
        if it is not ant:
            self._emitir("currentItemChanged", it, ant)
            self._emitir("itemSelectionChanged")

    def selectedItems(self):
        return [self._atual] if self._atual else []

    def expandAll(self):
        self._prof = 99
        self._tocar()

    def collapseAll(self):
        self._prof = -1
        for it in _todos(self._raiz):
            it.exp = False
        self._tocar()

    def expandToDepth(self, n):
        self._prof = int(n)
        self._tocar()

    def expandItem(self, it):
        it.setExpanded(True)

    def collapseItem(self, it):
        it.setExpanded(False)

    def scrollToItem(self, *a):
        pass

    def resizeColumnToContents(self, *a):
        pass

    def setColumnWidth(self, *a):
        pass

    def setSortingEnabled(self, *a):
        pass

    def sortItems(self, *a):
        pass

    def findItems(self, t, *a):
        return [it for it in _todos(self._raiz) if it.text(0) == t]

    # botão dentro da linha (ex.: "📄 PDF deste grupo (marcados)")
    def setItemWidget(self, it, col, w):
        it.__dict__.setdefault("widgets", {})[int(col)] = w
        self._tocar()

    def itemWidget(self, it, col):
        return it.__dict__.get("widgets", {}).get(int(col))

    def removeItemWidget(self, it, col):
        it.__dict__.get("widgets", {}).pop(int(col), None)
        self._tocar()


def _todos(raiz):
    for f in raiz.filhos:
        yield f
        yield from _todos(f)


class QTableWidgetItem(QListWidgetItem):
    pass


class QTableWidget(QWidget):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        d = self.__dict__
        d["_lin"] = 0
        d["_col"] = 0
        d["_cab"] = []
        d["_cel"] = {}
        for x in a:
            if isinstance(x, int):
                if not d["_lin"]:
                    d["_lin"] = x
                else:
                    d["_col"] = x

    def setRowCount(self, n):
        self._lin = int(n)
        self._cel = {k: v for k, v in self._cel.items() if k[0] < n}
        self._tocar()

    def rowCount(self):
        return self._lin

    def setColumnCount(self, n):
        self._col = int(n)
        self._tocar()

    def columnCount(self):
        return self._col

    def setHorizontalHeaderLabels(self, lst):
        self._cab = [str(x) for x in lst]
        self._col = max(self._col, len(self._cab))
        self._tocar()

    def setItem(self, r, c, it):
        it.lista = self
        self._cel[(r, c)] = it
        self._tocar()

    def item(self, r, c):
        return self._cel.get((r, c))

    def clear(self):
        self._cel.clear()
        self._cab = []
        self._tocar()

    def clearContents(self):
        self._cel.clear()
        self._tocar()

    def insertRow(self, r):
        novas = {}
        for (a, b), v in self._cel.items():
            novas[(a + 1 if a >= r else a, b)] = v
        self._cel = novas
        self._lin += 1
        self._tocar()

    def horizontalHeader(self):
        return _Cabecalho()

    verticalHeader = horizontalHeader


# ---------- containers sem estado importante
class QFrame(QWidget):
    HLine = 4
    VLine = 5
    Sunken = 0x30
    StyledPanel = 6
    NoFrame = 0


class QGroupBox(QWidget):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.__dict__["_titulo"] = next((x for x in a if isinstance(x, str)), "")

    def setTitle(self, t):
        self._titulo = str(t)

    def title(self):
        return self._titulo


class QScrollArea(QWidget):
    def setWidget(self, w):
        self._w = w

    def widget(self):
        return self.__dict__.get("_w")


class QSplitter(QWidget):
    pass


class QStackedWidget(QWidget):
    pass


class QTabWidget(QWidget):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.__dict__["_abas"] = []
        self.__dict__["_idx"] = 0

    def addTab(self, w, *a):
        self._abas.append(w)
        return len(self._abas) - 1

    def count(self):
        return len(self._abas)

    def widget(self, i):
        return self._abas[i] if 0 <= i < len(self._abas) else None

    def currentIndex(self):
        return self._idx

    def setCurrentIndex(self, i):
        self._idx = i

    def tabBar(self):
        return QWidget()


class QProgressBar(QSpinBox):
    pass


class QHeaderView(metaclass=_QtMeta):
    Stretch = 1
    ResizeToContents = 3
    Interactive = 0
    Fixed = 2


class QAbstractItemView(metaclass=_QtMeta):
    NoEditTriggers = 0
    ExtendedSelection = 3
    SingleSelection = 1
    MultiSelection = 2
    SelectRows = 1
    NoSelection = 0
    ScrollPerPixel = 1


class QSizePolicy(metaclass=_QtMeta):
    Expanding = 7
    Preferred = 5
    Fixed = 0
    Minimum = 1
    Maximum = 4

    def __init__(self, *a):
        pass


class QAction(QObject):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.__dict__["_texto"] = next((x for x in a if isinstance(x, str)), "")
        self.__dict__["_dica"] = ""

    def text(self):
        return self._texto

    def setText(self, t):
        self._texto = str(t)

    def setToolTip(self, t):
        self._dica = str(t or "")

    def toolTip(self):
        return self._dica

    def trigger(self):
        self._emitir("triggered", False)


class QMenu(QWidget):
    """Menu (ex.: histórico 🕘 de arquivos): vira uma escolha na tela do PPCPM."""

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.__dict__["_acoes"] = []
        self.__dict__["_titulo"] = next((x for x in a if isinstance(x, str)), "")

    def addAction(self, *a, **k):
        act = a[0] if a and isinstance(a[0], QAction) else QAction(*[x for x in a if isinstance(x, str)])
        for x in a:
            if callable(x) and not isinstance(x, (str, QAction)):
                act.triggered.connect(x)
        self._acoes.append(act)
        return act

    def addSeparator(self):
        return QAction()

    def addMenu(self, *a):
        return QMenu()

    def actions(self):
        return list(self._acoes)

    def exec_(self, *a):
        acoes = [x for x in self._acoes if x.text()]
        if not acoes:
            return None
        itens = [x.text() + (f"  —  {x.toolTip()}" if x.toolTip() and x.toolTip() != x.text() else "") for x in acoes]
        r = CTX.pedir({"tipo": "escolha", "titulo": self._titulo or "Escolher", "texto": "Escolha um item:", "itens": itens,
                       "padrao": 0})
        if isinstance(r, int) and 0 <= r < len(acoes):
            acoes[r].trigger()
            return acoes[r]
        return None

    exec = exec_
    popup = exec_


class QTimer(QObject):
    """Timer de verdade (numa linha de execução à parte): o "girando…" do status e as fases da tarefa
    aparecem ao vivo na tela do PPCPM."""

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        d = self.__dict__
        d["_ms"] = 0
        d["_unico"] = False
        d["_vivo"] = None

    @staticmethod
    def singleShot(ms, fn, *a):
        if callable(fn):
            fn()

    def setSingleShot(self, b):
        self._unico = bool(b)

    def setInterval(self, ms):
        self._ms = int(ms)

    def start(self, ms=None):
        if ms is not None:
            self._ms = int(ms)
        self.stop()
        ev = threading.Event()
        self._vivo = ev
        intervalo = max(0.3, self._ms / 1000.0)
        aba = aba_atual()

        def corre():
            definir_aba(aba)
            while not ev.wait(intervalo):
                try:
                    self._emitir("timeout")
                except Exception:
                    pass
                if self._unico:
                    break
        threading.Thread(target=corre, daemon=True, name="ppcpm-timer").start()

    def stop(self):
        if self._vivo is not None:
            self._vivo.set()
            self._vivo = None

    def isActive(self):
        return self._vivo is not None


class QThread(QObject):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.__dict__["_t"] = None

    def start(self, *a):
        aba = aba_atual()

        def corre():
            definir_aba(aba)
            try:
                self.run()
            finally:
                self._emitir("finished")
        t = threading.Thread(target=corre, daemon=True, name="ppcpm-tarefa")
        self._t = t
        _TAREFAS[t] = aba
        t.start()

    def run(self):
        pass

    def isRunning(self):
        return bool(self._t and self._t.is_alive())

    def wait(self, *a):
        if self._t:
            self._t.join()
        return True

    def quit(self):
        pass

    def terminate(self):
        pass

    @staticmethod
    def currentThread():
        return None


_TAREFAS: dict = {}


def tarefas_rodando(aba=None) -> int:
    for t in [t for t in _TAREFAS if not t.is_alive()]:
        _TAREFAS.pop(t, None)
    return sum(1 for t, a in list(_TAREFAS.items()) if aba is None or a in (None, aba))


class QEventLoop(QObject):
    def exec_(self, *a):
        return 0


class QApplication(QObject):
    _inst = None

    @staticmethod
    def instance():
        return None

    @staticmethod
    def processEvents(*a):
        pass

    @staticmethod
    def clipboard():
        return _Area()

    @staticmethod
    def setOverrideCursor(*a):
        pass

    @staticmethod
    def restoreOverrideCursor(*a):
        pass

    @staticmethod
    def setStyle(*a):
        pass

    @staticmethod
    def desktop():
        return QWidget()

    @staticmethod
    def primaryScreen():
        return _Coisa()


class _Area:
    def setText(self, t, *a):
        CTX.avisar("copiar", "", str(t))

    def text(self, *a):
        return ""


# ---------- diálogos (viram pedidos para a tela do PPCPM)
class QDialog(QWidget):
    Accepted = 1
    Rejected = 0

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        with _criados_lock:
            self.__dict__["_ini"] = len(_criados)
            self.__dict__["_ini_obj"] = _criados[-1] if _criados else None
        self.__dict__["_titulo"] = ""
        self.__dict__["_res"] = 0

    def setWindowTitle(self, t):
        self._titulo = str(t)

    def windowTitle(self):
        return self._titulo

    def accept(self):
        self._res = 1
        self._emitir("accepted")

    def reject(self):
        self._res = 0
        self._emitir("rejected")

    def done(self, r):
        self._res = r

    def result(self):
        return self._res

    def exec_(self, *a):
        with _criados_lock:
            ini = self.__dict__.get("_ini_obj")
            k = _criados.index(ini) + 1 if ini in _criados else 0
            rotulos = [l.text() for l in _criados[k:] if l.text()]
        CTX.avisar("info", self._titulo, "\n".join(rotulos[:80]))
        return 0

    exec = exec_


class QMessageBox(QDialog):
    NoButton = 0
    Ok = 0x400
    Save = 0x800
    Open = 0x2000
    Yes = 0x4000
    YesToAll = 0x8000
    No = 0x10000
    NoToAll = 0x20000
    Abort = 0x40000
    Retry = 0x80000
    Ignore = 0x100000
    Close = 0x200000
    Cancel = 0x400000
    Discard = 0x800000
    Help = 0x1000000
    Apply = 0x2000000
    Reset = 0x4000000
    InvalidRole = -1
    AcceptRole = 0
    RejectRole = 1
    DestructiveRole = 2
    ActionRole = 3
    HelpRole = 4
    YesRole = 5
    NoRole = 6
    ResetRole = 7
    ApplyRole = 8
    NoIcon = 0
    Information = 1
    Warning = 2
    Critical = 3
    Question = 4
    StandardButton = int
    _NOMES_BT = {Ok: "OK", Save: "Salvar", Open: "Abrir", Yes: "Sim", YesToAll: "Sim para todos", No: "Não",
                 NoToAll: "Não para todos", Abort: "Abortar", Retry: "Tentar de novo", Ignore: "Ignorar",
                 Close: "Fechar", Cancel: "Cancelar", Discard: "Descartar", Apply: "Aplicar", Reset: "Restaurar"}

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        d = self.__dict__
        d["_texto"] = ""
        d["_info"] = ""
        d["_det"] = ""
        d["_icone"] = 0
        d["_botoes"] = []          # [(botão, papel)]
        d["_padroes"] = 0
        d["_clicado"] = None
        d["_padrao"] = None
        # QMessageBox(icone, titulo, texto, botoes, parent)
        strs = [x for x in a if isinstance(x, str)]
        ints = [x for x in a if isinstance(x, int) and not isinstance(x, bool)]
        if len(strs) >= 2:
            d["_titulo"], d["_texto"] = strs[0], strs[1]
        if ints:
            d["_icone"] = ints[0]
            if len(ints) > 1:
                d["_padroes"] = ints[1]

    def setText(self, t):
        self._texto = str(t)

    def text(self):
        return self._texto

    def setInformativeText(self, t):
        self._info = str(t)

    def setDetailedText(self, t):
        self._det = str(t)

    def setIcon(self, i):
        self._icone = int(i) if isinstance(i, int) else 0

    def setStandardButtons(self, b):
        self._padroes = int(b)

    def addButton(self, b, papel=None):
        if isinstance(b, str):
            bt = QPushButton(b)
        elif isinstance(b, int):
            bt = QPushButton(self._NOMES_BT.get(b, "OK"))
            bt.__dict__["_padrao_id"] = b
            papel = papel if papel is not None else (self.RejectRole if b in (self.Cancel, self.No, self.Close) else self.AcceptRole)
        else:
            bt = b
        self._botoes.append((bt, papel))
        return bt

    def buttons(self):
        return [b for b, _ in self._botoes]

    def buttonRole(self, b):
        for x, p in self._botoes:
            if x is b:
                return p
        return self.InvalidRole

    def setDefaultButton(self, b):
        self._padrao = b

    def setEscapeButton(self, b):
        pass

    def clickedButton(self):
        return self._clicado

    def button(self, which):
        for b, _ in self._botoes:
            if b.__dict__.get("_padrao_id") == which:
                return b
        return None

    def _tipo(self):
        return {1: "info", 2: "aviso", 3: "erro", 4: "pergunta"}.get(self._icone, "info")

    def exec_(self, *a):
        # botões padrão viram botões de verdade
        for bid, nome in self._NOMES_BT.items():
            if self._padroes & bid and not self.button(bid):
                self.addButton(bid)
        bts = [b for b, p in self._botoes if p != self.ActionRole]
        texto = self._texto + (("\n\n" + self._info) if self._info else "")
        if len(bts) <= 1:
            CTX.avisar(self._tipo(), self._titulo, texto, self._det)
            self._clicado = bts[0] if bts else None
            return int(self._clicado.__dict__.get("_padrao_id", 0)) if self._clicado else self.Ok
        idx_padrao = bts.index(self._padrao) if self._padrao in bts else 0
        r = CTX.pedir({"tipo": "pergunta", "titulo": self._titulo, "texto": texto, "detalhes": self._det,
                       "icone": self._tipo(), "botoes": [b.text() for b in bts], "padrao": idx_padrao})
        i = r if isinstance(r, int) and 0 <= r < len(bts) else next(
            (k for k, b in enumerate(bts) if self.buttonRole(b) == self.RejectRole), len(bts) - 1)
        self._clicado = bts[i]
        return int(self._clicado.__dict__.get("_padrao_id", i))

    exec = exec_

    # ---- estáticos
    @staticmethod
    def _simples(tipo, parent, titulo, texto, *a, **k):
        CTX.avisar(tipo, titulo, texto)
        return QMessageBox.Ok

    @staticmethod
    def information(parent, titulo, texto, *a, **k):
        return QMessageBox._simples("info", parent, titulo, texto)

    @staticmethod
    def warning(parent, titulo, texto, *a, **k):
        return QMessageBox._simples("aviso", parent, titulo, texto)

    @staticmethod
    def critical(parent, titulo, texto, *a, **k):
        return QMessageBox._simples("erro", parent, titulo, texto)

    @staticmethod
    def about(parent, titulo, texto, *a, **k):
        return QMessageBox._simples("info", parent, titulo, texto)

    @staticmethod
    def question(parent, titulo, texto, botoes=None, padrao=None, *a, **k):
        if botoes is None:
            botoes = QMessageBox.Yes | QMessageBox.No
        ids = [b for b in QMessageBox._NOMES_BT if int(botoes) & b]
        nomes = [QMessageBox._NOMES_BT[b] for b in ids]
        p = ids.index(int(padrao)) if padrao is not None and int(padrao) in ids else 0
        r = CTX.pedir({"tipo": "pergunta", "titulo": titulo, "texto": texto, "detalhes": "", "icone": "pergunta",
                       "botoes": nomes, "padrao": p})
        if isinstance(r, int) and 0 <= r < len(ids):
            return ids[r]
        return QMessageBox.No if QMessageBox.No in ids else (QMessageBox.Cancel if QMessageBox.Cancel in ids else ids[-1])


def _filtro_ext(filtro: str) -> str:
    """'PDF (*.pdf);;Todos (*)' -> '.pdf' (aceitar do navegador)."""
    exts = []
    for m in re.findall(r"\*(\.[A-Za-z0-9]+)", filtro or ""):
        m = m.lower()
        if m not in exts:
            exts.append(m)
    return ",".join(exts)


class QFileDialog(QDialog):
    @staticmethod
    def getOpenFileName(parent=None, titulo="", pasta="", filtro="", *a, **k):
        r = CTX.pedir({"tipo": "arquivos", "titulo": titulo, "multiplo": False, "aceita": _filtro_ext(filtro)})
        if isinstance(r, list) and r:
            return r[0], filtro
        return "", ""

    @staticmethod
    def getOpenFileNames(parent=None, titulo="", pasta="", filtro="", *a, **k):
        r = CTX.pedir({"tipo": "arquivos", "titulo": titulo, "multiplo": True, "aceita": _filtro_ext(filtro)})
        if isinstance(r, list) and r:
            return list(r), filtro
        return [], ""

    @staticmethod
    def getSaveFileName(parent=None, titulo="", sugestao="", filtro="", *a, **k):
        f = CTX.saida_padrao
        cam = f(sugestao, titulo) if f else ""
        return cam, filtro

    @staticmethod
    def getExistingDirectory(parent=None, titulo="", pasta="", *a, **k):
        if re.search(r"salv|sa[ií]da|destino|grav", titulo or "", re.I):
            f = CTX.saida_padrao
            cam = f(os.path.join(pasta or "", ""), titulo, pasta=True) if f else ""
            return cam
        r = CTX.pedir({"tipo": "pasta", "titulo": titulo})
        return r if isinstance(r, str) else ""


class QInputDialog(QDialog):
    @staticmethod
    def getText(parent, titulo, rotulo, *a, **k):
        texto = k.get("text", "")
        for x in a:
            if isinstance(x, str):
                texto = x
        r = CTX.pedir({"tipo": "texto", "titulo": titulo, "texto": rotulo, "valor": texto})
        if isinstance(r, str):
            return r, True
        return "", False

    @staticmethod
    def getItem(parent, titulo, rotulo, itens, atual=0, *a, **k):
        itens = [str(x) for x in itens]
        r = CTX.pedir({"tipo": "escolha", "titulo": titulo, "texto": rotulo, "itens": itens, "padrao": atual})
        if isinstance(r, int) and 0 <= r < len(itens):
            return itens[r], True
        return (itens[atual] if itens else ""), False

    @staticmethod
    def getInt(parent, titulo, rotulo, valor=0, *a, **k):
        r = CTX.pedir({"tipo": "texto", "titulo": titulo, "texto": rotulo, "valor": str(valor)})
        try:
            return int(r), True
        except (TypeError, ValueError):
            return valor, False


class QColorDialog(QDialog):
    @staticmethod
    def getColor(atual=None, *a, **k):
        return QColor(atual) if atual is not None else QColor()


# ---------- Qt (constantes)
class Qt(metaclass=_QtMeta):
    UserRole = _Flag(256)
    DisplayRole = _Flag(0)
    EditRole = _Flag(2)
    ToolTipRole = _Flag(3)
    ForegroundRole = _Flag(9)
    BackgroundRole = _Flag(8)
    CheckStateRole = _Flag(10)
    FontRole = _Flag(6)
    Unchecked = _Flag(0)
    PartiallyChecked = _Flag(1)
    Checked = _Flag(2)
    ItemIsUserCheckable = _Flag(16)
    ItemIsEnabled = _Flag(32)
    ItemIsSelectable = _Flag(1)
    ItemIsEditable = _Flag(2)
    ItemIsTristate = _Flag(64)
    ItemIsAutoTristate = _Flag(64)
    AlignLeft = _Flag(1)
    AlignRight = _Flag(2)
    AlignHCenter = _Flag(4)
    AlignCenter = _Flag(132)
    AlignVCenter = _Flag(128)
    AlignTop = _Flag(32)
    AlignBottom = _Flag(64)
    Horizontal = _Flag(1)
    Vertical = _Flag(2)
    AscendingOrder = _Flag(0)
    DescendingOrder = _Flag(1)
    black = _Flag(2)
    white = _Flag(3)
    red = _Flag(7)
    green = _Flag(8)
    blue = _Flag(9)
    gray = _Flag(5)


QtCore_names = {}


# ------------------------------------------------------------------ monta o pacote PyQt5 falso
def _modulo(nome, dic):
    m = types.ModuleType(nome)
    m.__dict__.update(dic)

    def __getattr__(n):           # qualquer classe que faltou vira um widget genérico
        if n.startswith("__"):
            raise AttributeError(n)
        if n[:1] == "Q":
            c = type(n, (QWidget,), {})
            setattr(m, n, c)
            return c
        raise AttributeError(n)
    m.__getattr__ = __getattr__
    return m


def instalar_falso() -> dict:
    """Coloca o PyQt5 falso em sys.modules. Devolve o que estava lá antes (para restaurar)."""
    g = globals()
    widgets = {k: v for k, v in g.items() if isinstance(v, type) and k.startswith("Q") and k not in (
        "QColor", "QBrush", "QFont", "QIcon", "QPixmap", "QPainter", "QPen", "QPalette", "QFontMetrics",
        "QObject", "QTimer", "QThread", "QEventLoop")}
    core = {"Qt": Qt, "QObject": QObject, "QTimer": QTimer, "QThread": QThread, "pyqtSignal": pyqtSignal,
            "pyqtSlot": pyqtSlot, "QEventLoop": QEventLoop, "QSize": _Coisa, "QPoint": _Coisa, "QRect": _Coisa,
            "QUrl": _Coisa, "QMimeData": _Coisa, "QCoreApplication": QApplication, "QByteArray": _Coisa,
            "QSettings": _Coisa, "QRectF": _Coisa, "QPointF": _Coisa, "QSizeF": _Coisa, "QItemSelectionModel": _Coisa}
    gui = {"QColor": QColor, "QBrush": QBrush, "QFont": QFont, "QIcon": QIcon, "QPixmap": QPixmap,
           "QPainter": QPainter, "QPen": QPen, "QPalette": QPalette, "QFontMetrics": QFontMetrics,
           "QGuiApplication": QApplication, "QCursor": _Coisa, "QKeySequence": _Coisa, "QImage": QPixmap,
           "QPainterPath": QPainter, "QLinearGradient": QPainter, "QDesktopServices": _Coisa,
           "QTextCursor": _Coisa, "QStandardItemModel": _Coisa, "QStandardItem": _Coisa}
    antes = {k: sys.modules.get(k) for k in ("PyQt5", "PyQt5.QtWidgets", "PyQt5.QtCore", "PyQt5.QtGui")}
    pkg = types.ModuleType("PyQt5")
    pkg.__path__ = []
    mw = _modulo("PyQt5.QtWidgets", widgets)
    mc = _modulo("PyQt5.QtCore", core)
    mg = _modulo("PyQt5.QtGui", gui)
    pkg.QtWidgets, pkg.QtCore, pkg.QtGui = mw, mc, mg
    sys.modules.update({"PyQt5": pkg, "PyQt5.QtWidgets": mw, "PyQt5.QtCore": mc, "PyQt5.QtGui": mg})
    return antes


def restaurar(antes: dict):
    for k, v in antes.items():
        if v is None:
            sys.modules.pop(k, None)
        else:
            sys.modules[k] = v


# ------------------------------------------------------------------ estado da tela -> JSON
def _item_json(it: QTreeWidgetItem, prof: int, prof_exp):
    d = {"t": list(it.t)}
    if it.cor:
        d["c"] = {str(k): v for k, v in it.cor.items() if v}
    if it.fundo:
        d["f"] = {str(k): v for k, v in it.fundo.items() if v}
    if it.negrito:
        d["b"] = sorted(it.negrito)
    if it.check:
        d["k"] = {str(k): v for k, v in it.check.items()}
    if it.dica:
        d["d"] = {str(k): v for k, v in it.dica.items() if v}
    if it.oculto:
        d["h"] = 1
    ws = it.__dict__.get("widgets")
    if ws:
        d["w"] = {str(k): {"t": getattr(w, "_texto", ""), "a": w.__dict__.get("_ativo", True)} for k, w in ws.items()
                  if isinstance(w, QWidget)}
    aberto = it.exp or (prof_exp is not None and prof <= prof_exp)
    if aberto:
        d["e"] = 1
    if it.filhos:
        d["n"] = [_item_json(f, prof + 1, prof_exp) for f in it.filhos]
    return d


def _cor_estilo(est: str) -> str:
    m = re.search(r"(?<![-\w])color\s*:\s*([^;}\s]+)", est or "")
    return m.group(1) if m else ""


def widget_json(w):
    """Estado de um widget, no formato que a tela do PPCPM entende (ou None)."""
    if not isinstance(w, QObject):
        return None
    base = {"vis": w.__dict__.get("_vis", True), "ativo": w.__dict__.get("_ativo", True)}
    if isinstance(w, QTreeWidget):
        return dict(base, tipo="arvore", cab=list(w._cab),
                    itens=[_item_json(f, 0, w._prof) for f in w._raiz.filhos],
                    atual=caminho_item(w._atual) if w._atual else None)
    if isinstance(w, QTableWidget):
        linhas = []
        for r in range(w._lin):
            linha = []
            for c in range(w._col):
                it = w._cel.get((r, c))
                linha.append({"t": it.t, "c": it.cor, "f": it.fundo} if it else {"t": ""})
            linhas.append(linha)
        return dict(base, tipo="tabela", cab=list(w._cab), linhas=linhas)
    if isinstance(w, QListWidget):
        return dict(base, tipo="lista", itens=[{"t": i.t, "c": i.cor, "f": i.fundo, "k": i.check, "d": i.dica,
                                                "h": 1 if i.oculto else 0} for i in w._itens], atual=w._atual)
    if isinstance(w, QComboBox):
        return dict(base, tipo="combo", itens=[t for t, _ in w._itens], idx=w._idx)
    if isinstance(w, QCheckBox):
        return dict(base, tipo="check", texto=w._texto, marcado=w._marcado, dica=w._dica)
    if isinstance(w, QPushButton):
        return dict(base, tipo="botao", texto=w._texto, marcado=w._marcado)
    if isinstance(w, QLineEdit):
        return dict(base, tipo="linha", texto=w._texto, ph=w._props.get("placeholder", ""))
    if isinstance(w, QPlainTextEdit):
        return dict(base, tipo="texto", texto=w._texto, ph=w._props.get("placeholder", ""))
    if isinstance(w, QSpinBox):
        return dict(base, tipo="numero", valor=w._valor)
    if isinstance(w, QLabel):
        return dict(base, tipo="rotulo", texto=w._texto, cor=_cor_estilo(w._estilo))
    if hasattr(w, "cartoes") and isinstance(getattr(w, "cartoes"), dict):      # FaixaKPI do validador
        cart = {}
        for k, c in w.cartoes.items():
            try:
                cart[k] = {"rotulo": c.lbl_rotulo.text(), "valor": c.lbl_valor.text(), "icone": c.lbl_icone.text(),
                           "cor": _cor_estilo(c.lbl_valor.styleSheet())}
            except Exception:
                pass
        return dict(base, tipo="kpis", cartoes=cart)
    return None


def versao_widget(w) -> int:
    v = w.__dict__.get("_ver", 0)
    if hasattr(w, "cartoes") and isinstance(getattr(w, "cartoes"), dict):
        for c in w.cartoes.values():
            try:
                v = max(v, c.lbl_valor.__dict__.get("_ver", 0))
            except Exception:
                pass
    return v


def caminho_item(it) -> list | None:
    if it is None:
        return None
    cam = []
    n = it
    while n.pai is not None:
        cam.append(n.pai.indexOfChild(n))
        n = n.pai
    a = n.arvore
    if a is None:
        return None
    cam.append(a._raiz.indexOfChild(n) if n is not a._raiz else 0)
    if n is a._raiz:
        cam.pop()
    return list(reversed(cam))


def item_por_caminho(arvore: QTreeWidget, cam: list):
    n = arvore._raiz
    for i in cam or []:
        n = n.child(int(i))
        if n is None:
            return None
    return None if n is arvore._raiz else n
