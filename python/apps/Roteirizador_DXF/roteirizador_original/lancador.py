# -*- coding: utf-8 -*-
"""
Abre o ROTEIRIZADOR DXF PROJEART (o original, em Tkinter, com banco de memória)
a partir da área de trabalho do PPCP.

O roteirizador tem janela e laço de eventos próprios (Tkinter), então ele roda
como um PROGRAMA À PARTE (outro processo), iniciado pelo próprio main.py com o
argumento `--roteirizador`. Assim o script original fica 100% intacto e não
trava nem é travado pelo resto do PPCP.

  - só uma janela do roteirizador por vez (o banco de memória é um arquivo
    SQLite compartilhado): clicar de novo no ícone traz a janela pra frente;
  - fechar o PPCP não fecha o roteirizador (e vice-versa);
  - a memória (`roteirizador_memoria.db`) fica ao lado do script
    (roteirizador_original/) quando roda com `python main.py`, e ao lado do .exe
    quando roda empacotado (é o que o próprio script decide).
"""
import os
import subprocess
import sys

from nucleo.caminhos import RAIZ_PROJETO
from nucleo.logging_config import logger

TITULO_JANELA = "ROTEIRIZADOR DXF PROJEART"      # início do título da janela Tk (a versão vem depois)
TITULO_JANELA_ORDENS = "RELATÓRIO DE ORDENS PROJEART"   # idem, para o app Relatório de Ordens (mesmo script, argumento --ordens)
_CREATE_NO_WINDOW = 0x08000000


def _comando(modo="roteirizador"):
    flag = "--ordens" if modo == "ordens" else "--roteirizador"
    if getattr(sys, "frozen", False):
        return [sys.executable, flag]
    return [sys.executable, os.path.join(RAIZ_PROJETO, "main.py"), flag]


def _trazer_para_frente(pid, titulo=TITULO_JANELA):
    """Windows: acha a janela do processo `pid` pelo título e traz pra frente. Devolve True se achou."""
    if sys.platform != "win32":
        return False
    try:
        import ctypes
        from ctypes import wintypes
        user32 = ctypes.windll.user32
        achou = []
        EnumProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

        def cb(hwnd, _lp):
            if not user32.IsWindowVisible(hwnd):
                return True
            p = wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(p))
            if p.value != pid:
                return True
            n = user32.GetWindowTextLengthW(hwnd)
            buf = ctypes.create_unicode_buffer(n + 1)
            user32.GetWindowTextW(hwnd, buf, n + 1)
            if buf.value.upper().startswith(titulo):
                achou.append(hwnd)
                return False
            return True
        user32.EnumWindows(EnumProc(cb), 0)
        if not achou:
            return False
        user32.ShowWindow(achou[0], 9)            # SW_RESTORE
        user32.SetForegroundWindow(achou[0])
        return True
    except Exception:
        return False


class LancadorRoteirizador:
    """Fábrica "externa": a área de trabalho chama o objeto em vez de criar uma janela interna."""
    externo = True

    def __init__(self, modo="roteirizador"):
        self._modo = modo
        self._titulo = TITULO_JANELA_ORDENS if modo == "ordens" else TITULO_JANELA
        self._nome = "Relatório de Ordens" if modo == "ordens" else "Roteirizador DXF"
        self._proc = None

    def em_execucao(self):
        return self._proc is not None and self._proc.poll() is None

    def __call__(self):
        """Abre o roteirizador (ou traz pra frente). Devolve (mensagem, erro)."""
        if self.em_execucao():
            _trazer_para_frente(self._proc.pid, self._titulo)
            return f"{self._nome} já está aberto.", None
        try:
            flags = _CREATE_NO_WINDOW if sys.platform == "win32" else 0
            self._proc = subprocess.Popen(_comando(self._modo), cwd=RAIZ_PROJETO, creationflags=flags)
            logger.info(f"{self._nome} iniciado (pid {self._proc.pid}).")
            return f"Abrindo {self._nome}…", None
        except Exception as e:                                   # noqa: BLE001
            logger.exception(f"Falha ao iniciar: {self._nome}")
            return None, str(e)


def criar_app_embutido(modo="roteirizador"):
    """Roteirizador (ou, com modo="ordens", o Relatório de Ordens) DENTRO de uma janela do unificador
    (ver desktop/externo_embutido.py)."""
    from desktop.externo_embutido import AppExterno
    if modo == "ordens":
        return AppExterno("Relatório de Ordens", _comando("ordens"), TITULO_JANELA_ORDENS, cwd=RAIZ_PROJETO,
                          env_extra={"PPCP_EMBUTIDO": "1"})
    return AppExterno("Roteirizador DXF", _comando(), TITULO_JANELA, cwd=RAIZ_PROJETO,
                      env_extra={"PPCP_EMBUTIDO": "1"})
