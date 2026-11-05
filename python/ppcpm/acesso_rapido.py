"""
ACESSO RÁPIDO DO WINDOWS — as mesmas pastas fixadas do Explorador de Arquivos.

Lê e altera o "Acesso rápido" (Início) do Explorador pelo próprio Windows (Shell.Application, via pywin32).
Assim, fixar uma pasta no PPCPM - ARQUIVOS também fixa no Explorador, e vice-versa.
Sem pywin32 (ou fora do Windows) nada quebra: o sistema usa só os favoritos dele (pastas.json).
Não usa PowerShell.
"""
from __future__ import annotations

import os
import sys
import threading
import time

ACESSO_RAPIDO = "shell:::{679f85cb-0220-4080-b29b-5540cc05aab6}"
_trava = threading.Lock()
_cache: dict = {"t": 0.0, "itens": []}


def _shell():
    if not sys.platform.startswith("win"):
        return None
    try:
        import pythoncom  # noqa: F401  (vem com o pywin32)
        import win32com.client
        pythoncom.CoInitialize()
        return win32com.client.Dispatch("Shell.Application")
    except Exception:
        return None


def _fixada(item) -> bool | None:
    try:
        v = item.ExtendedProperty("System.Home.IsPinned")
        return None if v is None else bool(v)
    except Exception:
        return None


def listar(forcar: bool = False) -> list[dict]:
    """Pastas fixadas no Acesso rápido do Windows (na ordem do Explorador)."""
    with _trava:
        if not forcar and time.time() - _cache["t"] < 30:
            return list(_cache["itens"])
        itens: list[dict] = []
        sh = _shell()
        if sh is not None:
            try:
                ns = sh.Namespace(ACESSO_RAPIDO)
                for it in (ns.Items() if ns is not None else []):
                    try:
                        caminho = str(it.Path or "")
                        if not it.IsFolder or not caminho or caminho.startswith("::") or not os.path.isdir(caminho):
                            continue
                        if _fixada(it) is False:          # pasta "frequente" (não fixada): não entra
                            continue
                        itens.append({"nome": str(it.Name or os.path.basename(caminho.rstrip("\\/")) or caminho),
                                      "caminho": caminho, "windows": True})
                    except Exception:
                        continue
            except Exception:
                itens = []
        _cache.update(t=time.time(), itens=itens)
        return list(itens)


def fixar(caminho: str) -> bool:
    """Fixa a pasta no Acesso rápido do Windows. True = deu certo."""
    sh = _shell()
    if sh is None:
        return False
    try:
        pasta = sh.Namespace(caminho)
        if pasta is None:
            return False
        pasta.Self.InvokeVerb("pintohome")
        _cache["t"] = 0
        return True
    except Exception:
        return False


def desafixar(caminho: str) -> bool:
    """Tira a pasta do Acesso rápido do Windows. True = deu certo."""
    sh = _shell()
    if sh is None:
        return False
    alvo = os.path.normcase(os.path.normpath(caminho))
    try:
        ns = sh.Namespace(ACESSO_RAPIDO)
        for it in (ns.Items() if ns is not None else []):
            try:
                if os.path.normcase(os.path.normpath(str(it.Path or ""))) == alvo:
                    it.InvokeVerb("unpinfromhome")
                    _cache["t"] = 0
                    return True
            except Exception:
                continue
    except Exception:
        pass
    return False
