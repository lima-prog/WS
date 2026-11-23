"""
PREPARAÇÃO FÁBRICA — os 7 apps de DXF/CAM/pastas (python/apps/<App>).

Cada app é o programa original (PyQt5 ou Tkinter), copiado sem mudança da lógica. O sistema só:
  • confere se o app e as bibliotecas dele estão neste PC (estado);
  • abre o app numa janela própria, com o Python do sistema (abrir);
  • mostra a pasta de dados que ele usa (a mesma "Pasta de dados do PCP" do Agrupador | Base).
Só o próprio computador do sistema pode abrir (app.py confere com _do_proprio_pc).
"""
from __future__ import annotations

import os
import subprocess
import sys
import time
from importlib.util import find_spec
from pathlib import Path

PASTA_APPS = Path(__file__).resolve().parent.parent / "apps"
PASTA_DADOS_PRODUCAO = Path(__file__).resolve().parent.parent / "dados_locais" / "producao"

# id da aba: (pasta do app, nome, bibliotecas que ele precisa [nome no pip])
APPS = {
    "pg16": ("Visualizador_DXF", "Visualizador DXF", ["PyQt5", "ezdxf", "numpy", "pyqtgraph"]),
    "pg17": ("Espelhar_DXF", "Espelhar DXF", ["PyQt5", "ezdxf"]),
    "pg18": ("Corte_Inteligente", "Corte Inteligente", ["PyQt5", "ezdxf"]),
    "pg19": ("Renomear_DXF", "Renomear DXF", ["PyQt5"]),
    "pg20": ("Conversor_CAM_DXF", "Conversor CAM → DXF", ["PyQt5", "ezdxf"]),
    "pg21": ("Criar_Pasta_Auditoria", "Criar Pasta / Auditoria", ["PyQt5", "openpyxl"]),
    "pg22": ("Roteirizador_DXF", "Roteirizador DXF", ["ezdxf", "numpy", "openpyxl", "pandas", "xlrd"]),
}
# nome para importar de cada biblioteca do pip
IMPORTA = {"PyQt5": "PyQt5", "ezdxf": "ezdxf", "numpy": "numpy", "pyqtgraph": "pyqtgraph",
           "openpyxl": "openpyxl", "pandas": "pandas", "xlrd": "xlrd"}

_PROCESSOS: dict[str, subprocess.Popen] = {}
_ABERTO_EM: dict[str, float] = {}


def _instalada(lib: str) -> bool:
    try:
        return find_spec(IMPORTA.get(lib, lib)) is not None
    except (ImportError, ValueError):
        return False


def _pasta_dados() -> str:
    """A pasta de dados que o app vai usar (mesma regra do main.py dos apps)."""
    if os.environ.get("PPCP_DADOS", "").strip():
        return os.environ["PPCP_DADOS"].strip()
    arq = PASTA_DADOS_PRODUCAO / "pasta_dados.txt"
    try:
        c = arq.read_text(encoding="utf-8-sig").strip().strip('"')
        if c and os.path.isdir(c):
            return c
    except OSError:
        pass
    return str(PASTA_DADOS_PRODUCAO)


def _rodando(aba: str) -> bool:
    p = _PROCESSOS.get(aba)
    return bool(p and p.poll() is None)


def estado(aba: str) -> dict:
    if aba not in APPS:
        return {"ok": False, "erro": "App desconhecido."}
    pasta, nome, libs = APPS[aba]
    raiz = PASTA_APPS / pasta
    faltam = [l for l in libs if not _instalada(l)]
    return {"ok": True, "aba": aba, "nome": nome, "existe": (raiz / "main.py").is_file(), "pasta": str(raiz),
            "bibliotecas": [{"nome": l, "ok": l not in faltam} for l in libs], "faltam": faltam,
            "rodando": _rodando(aba), "aberto_em": _ABERTO_EM.get(aba), "dados": _pasta_dados()}


def _python_janela() -> list[str]:
    """Python do sistema sem janela preta (pythonw.exe no Windows)."""
    exe = Path(sys.executable)
    if sys.platform == "win32":
        w = exe.with_name("pythonw.exe")
        if w.is_file():
            return [str(w)]
    return [str(exe)]


def abrir(aba: str, mensagens: bool = False) -> dict:
    est = estado(aba)
    if not est.get("ok"):
        return est
    if not est["existe"]:
        return {"ok": False, "erro": f"O app {est['nome']} não está nesta instalação (pasta apps/{APPS[aba][0]})."}
    if est["faltam"]:
        return {"ok": False, "faltam": est["faltam"],
                "erro": f"Faltam bibliotecas para o {est['nome']}: {', '.join(est['faltam'])}. Clique em \"Instalar bibliotecas\"."}
    if _rodando(aba):
        return {"ok": True, "ja_aberto": True, "nome": est["nome"]}
    raiz = PASTA_APPS / APPS[aba][0]
    env = dict(os.environ)
    env["PPCP_APP_ORIGEM"] = str(raiz)        # o main.py lê o pasta_dados.txt a partir daqui
    env.setdefault("PYTHONIOENCODING", "utf-8")
    cmd = ([sys.executable] if mensagens else _python_janela()) + [str(raiz / "main.py")]
    flags = 0
    if sys.platform == "win32":
        flags = subprocess.CREATE_NEW_CONSOLE if mensagens else getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        p = subprocess.Popen(cmd, cwd=str(raiz), env=env, creationflags=flags,
                             stdin=subprocess.DEVNULL,
                             stdout=None if mensagens else subprocess.DEVNULL,
                             stderr=None if mensagens else subprocess.DEVNULL)
    except OSError as e:
        return {"ok": False, "erro": f"Não consegui abrir o {est['nome']}: {e}"}
    _PROCESSOS[aba] = p
    _ABERTO_EM[aba] = time.time()
    time.sleep(1.2)
    if p.poll() is not None and p.returncode not in (0, None):
        return {"ok": False, "erro": f"O {est['nome']} fechou logo ao abrir (código {p.returncode}). "
                                     "Clique em \"Abrir com mensagens\" para ver o motivo."}
    return {"ok": True, "nome": est["nome"]}


def abrir_pasta(aba: str, qual: str) -> dict:
    """Abre no Explorador a pasta do app ou a pasta de dados."""
    if aba not in APPS:
        return {"ok": False, "erro": "App desconhecido."}
    alvo = _pasta_dados() if qual == "dados" else str(PASTA_APPS / APPS[aba][0])
    try:
        os.makedirs(alvo, exist_ok=True)
        if sys.platform == "win32":
            os.startfile(alvo)  # type: ignore[attr-defined]
        else:
            subprocess.Popen(["xdg-open", alvo], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return {"ok": True, "pasta": alvo}
    except OSError as e:
        return {"ok": False, "erro": str(e)}
