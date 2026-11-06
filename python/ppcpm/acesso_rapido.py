"""
ACESSO RÁPIDO DO WINDOWS — as mesmas pastas fixadas do Explorador de Arquivos.

Lê e altera o "Acesso rápido" (Início) do Explorador pelo próprio Windows (Shell.Application, via pywin32).
Assim, fixar uma pasta no PPCPM - ARQUIVOS também fixa no Explorador, e vice-versa.
Sem pywin32 (ou fora do Windows) nada quebra: o sistema usa só os favoritos dele (pastas.json).
Não usa PowerShell.

IMPORTANTE: o Windows pode demorar (ou travar) para responder — por exemplo com pastas de rede
desconectadas no Acesso rápido. Por isso tudo roda numa linha de trabalho separada e o sistema
NUNCA espera mais que alguns segundos: se o Windows não respondeu, usa a última lista conhecida.
"""
from __future__ import annotations

import os
import queue
import sys
import threading
import time

ACESSO_RAPIDO = "shell:::{679f85cb-0220-4080-b29b-5540cc05aab6}"
ESPERA_LISTA = 2.0      # segundos esperando o Windows ao listar (depois usa a última lista)
ESPERA_FIXAR = 6.0      # segundos esperando ao fixar/desafixar
VALIDADE = 60           # segundos que a lista vale antes de pedir de novo ao Windows

_cache: dict = {"t": 0.0, "itens": [], "pedindo": False}
_fila: "queue.Queue" = queue.Queue()
_trabalhador: threading.Thread | None = None
_trava = threading.Lock()


def _disponivel() -> bool:
    if not sys.platform.startswith("win"):
        return False
    try:
        import win32com.client  # noqa: F401
        return True
    except Exception:
        return False


def _rede(caminho: str) -> bool:
    """Pasta de rede (\\\\servidor\\... ou unidade mapeada): não testamos se existe (pode demorar muito)."""
    if caminho.startswith("\\\\"):
        return True
    try:
        import ctypes
        return ctypes.windll.kernel32.GetDriveTypeW(caminho[:3]) == 4   # DRIVE_REMOTE
    except Exception:
        return False


def _ler(sh) -> list[dict]:
    itens: list[dict] = []
    ns = sh.Namespace(ACESSO_RAPIDO)
    for it in (ns.Items() if ns is not None else []):
        try:
            caminho = str(it.Path or "")
            if not it.IsFolder or not caminho or caminho.startswith("::"):
                continue
            try:
                fixada = it.ExtendedProperty("System.Home.IsPinned")
            except Exception:
                fixada = None
            if fixada is not None and not bool(fixada):        # pasta "frequente" (não fixada): não entra
                continue
            if not _rede(caminho) and not os.path.isdir(caminho):
                continue
            itens.append({"nome": str(it.Name or os.path.basename(caminho.rstrip("\\/")) or caminho),
                          "caminho": caminho, "windows": True})
        except Exception:
            continue
    return itens


def _verbo(sh, caminho: str, verbo: str) -> bool:
    if verbo == "pintohome":
        pasta = sh.Namespace(caminho)
        if pasta is None:
            return False
        pasta.Self.InvokeVerb("pintohome")
        return True
    alvo = os.path.normcase(os.path.normpath(caminho))
    ns = sh.Namespace(ACESSO_RAPIDO)
    for it in (ns.Items() if ns is not None else []):
        try:
            if os.path.normcase(os.path.normpath(str(it.Path or ""))) == alvo:
                it.InvokeVerb("unpinfromhome")
                return True
        except Exception:
            continue
    return False


def _laco() -> None:
    """Linha de trabalho do Windows (COM): uma tarefa por vez, separada do servidor."""
    sh = None
    try:
        import pythoncom
        import win32com.client
        pythoncom.CoInitialize()
        sh = win32com.client.Dispatch("Shell.Application")
    except Exception:
        sh = None
    while True:
        tarefa, caminho, resposta = _fila.get()
        try:
            if sh is None:
                resultado = None
            elif tarefa == "listar":
                resultado = _ler(sh)
                _cache.update(t=time.time(), itens=resultado)
            else:
                resultado = _verbo(sh, caminho, tarefa)
                _cache["t"] = 0
        except Exception:
            resultado = None
        finally:
            if tarefa == "listar":
                _cache["pedindo"] = False
        resposta.put(resultado)


def _pedir(tarefa: str, caminho: str, espera: float):
    global _trabalhador
    if not _disponivel():
        return None
    with _trava:
        if _trabalhador is None or not _trabalhador.is_alive():
            _trabalhador = threading.Thread(target=_laco, name="acesso-rapido", daemon=True)
            _trabalhador.start()
    resposta: "queue.Queue" = queue.Queue()
    _fila.put((tarefa, caminho, resposta))
    try:
        return resposta.get(timeout=espera)
    except queue.Empty:
        return None          # o Windows não respondeu a tempo: segue sem esperar


def listar(forcar: bool = False) -> list[dict]:
    """Pastas fixadas no Acesso rápido do Windows (na ordem do Explorador). Nunca trava o sistema."""
    if not forcar and time.time() - _cache["t"] < VALIDADE:
        return list(_cache["itens"])
    if _cache["pedindo"]:                  # já pediu e o Windows ainda não respondeu: usa a última lista
        return list(_cache["itens"])
    _cache["pedindo"] = True
    r = _pedir("listar", "", ESPERA_LISTA)
    return list(r) if r is not None else list(_cache["itens"])


def ultima() -> list[dict]:
    """A última lista conhecida, sem perguntar ao Windows (resposta imediata)."""
    return list(_cache["itens"])


def fixar(caminho: str) -> bool:
    """Fixa a pasta no Acesso rápido do Windows. True = deu certo."""
    return bool(_pedir("pintohome", caminho, ESPERA_FIXAR))


def desafixar(caminho: str) -> bool:
    """Tira a pasta do Acesso rápido do Windows. True = deu certo."""
    return bool(_pedir("unpinfromhome", caminho, ESPERA_FIXAR))
