# -*- coding: utf-8 -*-
"""
Preparação do processo do Roteirizador quando ele é aberto DENTRO do unificador
(variável de ambiente PPCP_EMBUTIDO=1, definida por desktop/externo_embutido.py).

O script do roteirizador só ganhou o parâmetro `modo` (roteirizador/ordens). Aqui só se faz, antes dele rodar:
  1. DPI: o Windows só aceita janela-filha entre processos com a MESMA "consciência de DPI".
     O unificador (Qt) é "por monitor" (2); o roteirizador chama SetProcessDpiAwareness(1) sozinho.
     Então, se o unificador for por monitor, travamos o mesmo modo aqui antes (a chamada do
     script depois é ignorada pelo Windows, sem erro).
  2. a janela do Tk nasce TRANSPARENTE (alpha 0) e só aparece quando já foi encaixada (ou após
     12 s, por segurança) — evita ela "piscar" solta na tela antes de entrar na janela do unificador.
Qualquer falha aqui é ignorada: o roteirizador abre normalmente.
"""
import os
import time


def _dpi():
    try:
        import ctypes
        nivel = os.environ.get("PPCP_DPI")
        if nivel == "2":
            try:
                ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))   # per-monitor v2
            except Exception:
                ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        pass


def _transparente_ate_encaixar():
    import ctypes
    import tkinter as tk
    original = tk.Tk.__init__
    user32 = ctypes.windll.user32
    user32.GetParent.restype = ctypes.c_void_p
    user32.GetParent.argtypes = [ctypes.c_void_p]

    def init(self, *a, **k):
        original(self, *a, **k)
        try:
            self.attributes("-alpha", 0.0)
        except Exception:
            return
        t0 = time.time()

        def checar():
            try:
                moldura = int(self.wm_frame(), 16)
                if (moldura and user32.GetParent(moldura)) or time.time() - t0 > 12:
                    self.attributes("-alpha", 1.0)
                    return
            except Exception:
                try:
                    self.attributes("-alpha", 1.0)
                except Exception:
                    pass
                return
            self.after(60, checar)
        self.after(60, checar)
    tk.Tk.__init__ = init


def preparar():
    try:
        _dpi()
    except Exception:
        pass
    try:
        _transparente_ate_encaixar()
    except Exception:
        pass
