"""VERIFICAR SISTEMA — mostra se este PC está pronto para rodar o SISTEMA - PPCPM."""
from __future__ import annotations

import platform
import socket
import sys
from urllib.request import Request, urlopen

from . import arquivos_pc, bibliotecas
from .atualizador import ARQ_LOG, GITHUB_RAW, VERCEL
from .config import PASTA_APP, config, versao_python

OK, NAO, AVISO = "[ OK ]", "[FALTA]", "[ !! ]"


def _rede(url: str) -> str:
    try:
        with urlopen(Request(url, headers={"User-Agent": "SISTEMA-PPCPM"}), timeout=8) as r:
            return f"{OK} acessível (HTTP {r.status})"
    except Exception as e:
        codigo = getattr(e, "code", None)
        if codigo and codigo < 500:
            return f"{OK} acessível (HTTP {codigo})"
        return f"{NAO} sem acesso ({str(getattr(e, 'reason', e))[:60]})"


def _porta(p: int) -> str:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return f"{AVISO} em uso (o sistema usa a próxima livre)" if s.connect_ex(("127.0.0.1", p)) == 0 else f"{OK} livre"


def relatorio() -> str:
    c = config()
    L = []
    add = L.append
    add("=" * 66)
    add(f" VERIFICAR SISTEMA - PPCPM   ({c.get('versao')} · pacote Python {versao_python().get('pacote')})")
    add("=" * 66)
    add(f" Python ............ {platform.python_version()}  ({sys.executable})")
    add(f" Sistema ........... {platform.platform()}")
    add(f" Pasta do sistema .. {PASTA_APP}")
    ok_py = sys.version_info >= (3, 8)
    add(f" Python 3.8+ ....... {OK if ok_py else NAO}")
    add("")
    add(" CONEXÕES")
    add(f"   Banco Supabase .. {_rede(c.get('supabase_url', '') + '/auth/v1/health')}")
    add(f"   GitHub (versões)  {_rede(GITHUB_RAW + 'versao.json')}")
    add(f"   Vercel (sistema)  {_rede(VERCEL + 'versao.json')}")
    add(f"   Porta 5000 ...... {_porta(5000)}")
    add("")
    add(" PASTAS DO PC")
    loc = arquivos_pc.locais()
    for p in loc["pastas"]:
        add(f"   {OK} {p['nome']}: {p['caminho']}")
    add("   Unidades: " + ", ".join(u["nome"] for u in loc["unidades"]))
    if loc["favoritos"]:
        add("   Favoritos: " + ", ".join(f["nome"] for f in loc["favoritos"]))
    add("")
    add(" BIBLIOTECAS POR SEÇÃO  (o sistema abre sem elas; servem para os programas em Python)")
    faltam: set[str] = set()
    for arq, nome, libs, opc in bibliotecas.SECOES:
        status = []
        for n in libs + opc:
            v = bibliotecas.instalada(n)
            if not v and n not in opc:
                faltam.add(n)
            status.append(f"{n} {v}" if v else f"{n} ✗" + (" (opcional)" if n in opc else ""))
        marca = OK if all(bibliotecas.instalada(n) for n in libs) else NAO
        add(f"   {marca} {nome}")
        if status:
            add("          " + " · ".join(status))
    add("")
    if faltam:
        add(f" Faltam {len(faltam)} biblioteca(s): {', '.join(sorted(faltam))}")
        add(" Para instalar: INSTALAR_BIBLIOTECAS.bat")
    else:
        add(" Todas as bibliotecas instaladas.")
    try:
        ult = ARQ_LOG.read_text(encoding="utf-8").strip().splitlines()[-3:]
        if ult:
            add("")
            add(" ÚLTIMAS ATUALIZAÇÕES")
            L.extend("   " + x for x in ult)
    except OSError:
        pass
    add("=" * 66)
    return "\n".join(L)
