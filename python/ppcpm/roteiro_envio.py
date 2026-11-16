"""
GERENCIAMENTO DE ROTEIRO - ERP — guarda a planilha essencial (modelo_alteracao_roteiro) e abre o envio no intranet.

Igual ao app "Alteração de Roteiro" (PyQt) que veio separado:
  - toda planilha gerada fica num LOCAL FIXO, uma pasta por usuário do Windows, sempre com o mesmo nome
    (dados_locais/envio_roteiro/<usuário>/modelo_alteracao_roteiro_pcp.xlsx) + uma cópia datada em historico/
    (guarda as 40 mais recentes);
  - "Abrir página de envio": com o pacote playwright instalado (e o Edge ou o Chrome), abre o intranet JÁ COM A
    PLANILHA ANEXADA — quem confere e clica em "Enviar Planilha" é a pessoa (o sistema nunca envia sozinho);
    sem playwright: mostra a planilha no Explorer (o caminho vai para a área de transferência pelo navegador)
    e o navegador abre a página.
Não usa PowerShell.
"""
from __future__ import annotations

import getpass
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from .config import PASTA_DADOS

URL_ENVIO = "http://intranet.projeart.ind.br:8000/upload_route_pcp"
NOME = "modelo_alteracao_roteiro_pcp.xlsx"
ESTADO = {"ultimo": ""}


def pasta_envio() -> Path:
    usuario = os.environ.get("USERNAME") or getpass.getuser() or "usuario"
    usuario = "".join(c for c in usuario if c.isalnum() or c in "._- ") or "usuario"
    return PASTA_DADOS / "envio_roteiro" / usuario


def salvar(conteudo: bytes) -> dict:
    if not conteudo or conteudo[:2] != b"PK":
        raise ValueError("A planilha gerada veio vazia ou inválida.")
    pasta = pasta_envio()
    hist = pasta / "historico"
    hist.mkdir(parents=True, exist_ok=True)
    datado = hist / f"modelo_alteracao_roteiro_pcp_{datetime.now():%Y%m%d_%H%M%S}.xlsx"
    datado.write_bytes(conteudo)
    atual, aviso = pasta / NOME, ""
    try:
        shutil.copyfile(datado, atual)
        usado = atual
    except PermissionError:          # a "atual" está aberta no Excel: usa a cópia datada
        usado = datado
        aviso = "A planilha atual está aberta no Excel e não pôde ser substituída — usei a cópia datada."
    try:
        for f in sorted(p for p in hist.iterdir() if p.suffix.lower() == ".xlsx")[:-40]:
            f.unlink()
    except OSError:
        pass
    ESTADO["ultimo"] = str(usado)
    return {"ok": True, "caminho": str(usado), "aviso": aviso}


def ultima() -> str:
    u = ESTADO.get("ultimo") or ""
    if u and os.path.isfile(u):
        return u
    fixo = pasta_envio() / NOME
    return str(fixo) if fixo.is_file() else ""


def tem_playwright() -> bool:
    import importlib.util
    try:
        return importlib.util.find_spec("playwright") is not None
    except Exception:
        return False


def _explorer(caminho: str) -> None:
    if sys.platform.startswith("win"):
        try:
            subprocess.Popen(["explorer", "/select,", os.path.normpath(caminho)])
        except OSError:
            pass


def abrir_envio() -> dict:
    """Abre o envio com a última planilha. Devolve {modo: 'automatico'|'manual'|'sem_planilha', caminho, url}."""
    c = ultima()
    if not c:
        return {"modo": "sem_planilha", "caminho": "", "url": URL_ENVIO}
    if tem_playwright():
        script = Path(__file__).with_name("envio_intranet.py")
        try:
            subprocess.Popen([sys.executable, str(script), os.path.normpath(c), URL_ENVIO],
                             creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            return {"modo": "automatico", "caminho": c, "url": URL_ENVIO}
        except OSError:
            pass
    _explorer(c)
    return {"modo": "manual", "caminho": c, "url": URL_ENVIO}


def abrir_planilha() -> dict:
    c = ultima()
    if not c:
        return {"ok": False, "msg": "Ainda não há planilha gerada."}
    try:
        if sys.platform.startswith("win"):
            os.startfile(c)  # noqa: S606
        else:
            subprocess.Popen(["xdg-open", c])
        return {"ok": True, "caminho": c}
    except OSError as e:
        return {"ok": False, "msg": f"Não consegui abrir a planilha ({e})."}


def mostrar_pasta() -> dict:
    c = ultima()
    if not c:
        return {"ok": False, "msg": "Ainda não há planilha gerada."}
    _explorer(c)
    return {"ok": True, "caminho": c}
