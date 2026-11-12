"""
VERIFICAÇÃO DA INSTALAÇÃO — o próprio sistema confere se está tudo certo neste PC e avisa o que falta.

A Tela do sistema pergunta /api/pc/instalacao quando abre. Se faltar algo, mostra um aviso com a lista
e botões para resolver:
  - bibliotecas  -> instala as que faltam (pip no ambiente próprio do sistema, .venv). Sem .venv,
                    abre o INSTALAR_BIBLIOTECAS.bat (ele cria o .venv e instala).
  - arquivos     -> baixa de novo os arquivos do sistema que sumiram (do GitHub) e reinicia.
  - atalho       -> cria o atalho "SISTEMA - PPCPM" na Área de Trabalho.
  - instalar_pc  -> abre o INSTALAR.bat (quando o sistema está rodando pela cópia do drive da rede).
Não usa PowerShell.
"""
from __future__ import annotations

import os
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from importlib import invalidate_caches
from urllib.request import Request, urlopen

from . import bibliotecas
from .config import PASTA_APP, PASTA_DADOS, PASTA_GERADO, config, versao, versao_python

ARQUIVOS = [
    ("ABRIR_SISTEMA.bat", "abre o sistema"),
    ("INSTALAR.bat", "instala o sistema no PC"),
    ("INSTALAR_BIBLIOTECAS.bat", "instala as bibliotecas"),
    ("VERIFICAR_SISTEMA.bat", "confere a instalação"),
    ("ferramentas/achar_python.bat", "acha o Python do PC"),
    ("app.py", "programa principal"),
    ("versao_python.json", "versão do código Python"),
    ("icone.ico", "ícone do atalho"),
    ("bibliotecas/todas.txt", "lista de bibliotecas"),
    ("ppcpm/web/ponte.js", "ligação com os arquivos do PC"),
    ("ppcpm/web/icone.ico", "ícone das janelas"),
]

ESTADO: dict = {"rodando": False, "acao": "", "log": [], "fim": None, "ok": None, "msg": ""}
_trava = threading.Lock()
REINICIAR = {"fn": None}          # o app.py coloca aqui a função que reinicia o sistema


def _win() -> bool:
    return sys.platform.startswith("win")


def em_venv() -> bool:
    """Rodando no ambiente próprio do sistema (.venv desta pasta)?"""
    try:
        return sys.prefix != sys.base_prefix and os.path.normcase(os.path.realpath(sys.prefix)).startswith(
            os.path.normcase(os.path.realpath(PASTA_APP / ".venv")))
    except Exception:
        return False


def _no_drive() -> bool:
    if not _win():
        return False
    from .acesso_rapido import _rede
    return _rede(str(PASTA_APP))


def _item(grupo, nome, ok, detalhe="", nivel="erro", acao=None, botao=""):
    return {"grupo": grupo, "nome": nome, "ok": bool(ok), "nivel": "ok" if ok else nivel,
            "detalhe": detalhe, "acao": None if ok else acao, "botao": "" if ok else botao}


def _rede(url: str) -> tuple[bool, str]:
    try:
        with urlopen(Request(url, headers={"User-Agent": "SISTEMA-PPCPM"}), timeout=5) as r:
            return True, f"acessível (HTTP {r.status})"
    except Exception as e:
        codigo = getattr(e, "code", None)
        if codigo and codigo < 500:
            return True, f"acessível (HTTP {codigo})"
        return False, "sem acesso: " + str(getattr(e, "reason", e))[:80]


def verificar(rede: bool = True) -> dict:
    invalidate_caches()
    itens: list[dict] = []
    add = itens.append
    G = "Python"
    ok_py = sys.version_info >= (3, 8)
    add(_item(G, f"Python {sys.version.split()[0]}", ok_py, "precisa do Python 3.8 ou mais novo" if not ok_py else sys.executable))
    tem_venv = (PASTA_APP / ".venv" / ("Scripts" if _win() else "bin")).is_dir()
    if em_venv():
        add(_item(G, "Ambiente próprio do sistema (.venv)", True, "o sistema está usando o .venv desta pasta"))
    else:
        add(_item(G, "Ambiente próprio do sistema (.venv)", False,
                  ("existe, mas o sistema abriu com outro Python — feche e abra pelo atalho" if tem_venv else
                   "ainda não foi criado — é onde as bibliotecas ficam, sem mexer no resto do PC"),
                  "aviso", "bibliotecas", "Criar e instalar"))

    G = "Arquivos do sistema"
    faltando = [(a, d) for a, d in ARQUIVOS if not (PASTA_APP / a).is_file()]
    if not (PASTA_GERADO / "config.json").is_file() or not (PASTA_GERADO / "modulos").is_dir():
        faltando.append(("ppcpm/gerado", "telas do sistema"))
    if faltando:
        for a, d in faltando:
            add(_item(G, a, False, f"faltando ({d})", "erro", "arquivos", "Baixar de novo"))
    else:
        add(_item(G, f"{len(ARQUIVOS) + 1} arquivos e pastas principais", True, "todos no lugar"))

    G = "Instalação neste PC"
    drive = _no_drive()
    add(_item(G, "Instalado no próprio PC", not drive,
              "o sistema está abrindo pela cópia do drive da rede: ela não se atualiza. Rode o INSTALAR para "
              "instalar em C:\\Users\\<você>\\SISTEMA-PPCPM" if drive else str(PASTA_APP), "aviso", "instalar_pc", "Instalar no PC"))
    if _win() and not drive:
        from .atalho import existe
        tem = existe()
        add(_item(G, "Atalho na Área de Trabalho", tem, "\"SISTEMA - PPCPM\" com o ícone da Projeart" if tem else
                  "não achei o atalho \"SISTEMA - PPCPM\"", "aviso", "atalho", "Criar atalho"))
    try:
        PASTA_DADOS.mkdir(parents=True, exist_ok=True)
        t = PASTA_DADOS / ".teste_gravacao"
        t.write_text("ok", encoding="utf-8")
        t.unlink()
        add(_item(G, "Pasta de dados (dados_locais)", True, "dá para gravar"))
    except OSError as e:
        add(_item(G, "Pasta de dados (dados_locais)", False, f"sem permissão para gravar ({e})", "erro"))

    G = "Bibliotecas"
    usa: dict[str, list[str]] = {}
    for arq, nome, libs, opc in bibliotecas.SECOES:
        for n in libs:
            usa.setdefault(n, []).append(nome.split("›")[-1].strip())
    todas = [n for n in bibliotecas.todas() if _win() or n != "pywin32"]
    faltam = [n for n in todas if not bibliotecas.instalada(n)]
    for n in faltam:
        obrig = n in usa
        add(_item(G, n, False, bibliotecas.LIBS[n][2] + (" · usada em: " + ", ".join(usa[n]) if obrig else
                  " · opcional (o sistema funciona sem ela)"), "aviso" if obrig else "info", "bibliotecas", "Instalar"))
    if not [n for n in faltam if n in usa]:
        add(_item(G, f"{len(todas) - len(faltam)} de {len(todas)} bibliotecas instaladas", True,
                  "todas as que as seções usam estão instaladas"))

    pk = {}
    try:
        from . import pacotes
        pk = pacotes.estado()
    except Exception:
        pass
    if pk.get("caminho"):
        add(_item("Planilha de pacotes", "Planilha da Tela inicial", not pk.get("erro"), pk.get("erro") or pk["caminho"], "aviso"))

    if rede:
        from .atualizador import GITHUB_RAW, VERCEL
        c = config()
        alvos = [("Banco de dados (Supabase)", c.get("supabase_url", "") + "/auth/v1/health", "erro"),
                 ("Atualizações (GitHub)", GITHUB_RAW + "versao.json", "aviso"),
                 ("Sistema na internet (Vercel)", VERCEL + "versao.json", "aviso")]
        with ThreadPoolExecutor(3) as ex:
            res = list(ex.map(lambda a: _rede(a[1]), alvos))
        for (nome, _, nivel), (ok, det) in zip(alvos, res):
            add(_item("Conexões", nome, ok, det if ok else det + " — confira a internet ou peça para a T.I. liberar", nivel))

    problemas = [i for i in itens if not i["ok"] and i["nivel"] in ("erro", "aviso")]
    return {"itens": itens, "faltam": len(problemas), "erros": sum(i["nivel"] == "erro" for i in problemas),
            "pronto": not problemas, "em_venv": em_venv(), "versao": versao(),
            "pacote": versao_python().get("pacote"), "quando": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "trabalho": estado()}


def estado() -> dict:
    with _trava:
        return {k: (list(v) if isinstance(v, list) else v) for k, v in ESTADO.items()}


def _log(txt: str) -> None:
    with _trava:
        ESTADO["log"].append(txt.rstrip())
        del ESTADO["log"][:-300]


def _comecar(acao: str) -> bool:
    with _trava:
        if ESTADO["rodando"]:
            return False
        ESTADO.update(rodando=True, acao=acao, log=[], fim=None, ok=None, msg="")
        return True


def _terminar(ok: bool, msg: str) -> None:
    with _trava:
        ESTADO.update(rodando=False, ok=ok, msg=msg, fim=datetime.now().strftime("%H:%M:%S"))


def _abrir_bat(nome: str) -> dict:
    bat = PASTA_APP / nome
    if not bat.is_file():
        return {"ok": False, "msg": f"Não achei o {nome} nesta pasta."}
    if not _win():
        return {"ok": False, "msg": f"Abra o {nome} no Windows."}
    os.startfile(str(bat))          # abre numa janela própria (a pessoa vê o andamento)
    return {"ok": True, "janela": True, "msg": f"Abri o {nome} numa janela. Quando ele terminar, feche e abra o sistema de novo."}


def _pip(nomes: list[str]) -> None:
    pacotes = PASTA_APP / "pacotes"
    cmd = [sys.executable, "-m", "pip", "install", "--disable-pip-version-check", "--prefer-binary"]
    if pacotes.is_dir():
        cmd += ["--no-index", "--find-links", str(pacotes)]
        _log("Instalando SEM internet, pela pasta \"pacotes\"...")
    else:
        _log("Instalando pela internet...")
    cmd += [bibliotecas.LIBS[n][1] for n in nomes]
    _log("Bibliotecas: " + ", ".join(nomes))
    try:
        p = subprocess.Popen(cmd, cwd=str(PASTA_APP), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                             encoding="utf-8", errors="replace",
                             creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        for linha in p.stdout:
            if linha.strip():
                _log(linha)
        p.wait()
    except Exception as e:  # noqa: BLE001
        _log(f"Erro: {e}")
        return _terminar(False, f"Não consegui rodar o instalador de bibliotecas ({e}).")
    invalidate_caches()
    faltam = [n for n in nomes if not bibliotecas.instalada(n)]
    if p.returncode == 0 and not faltam:
        _terminar(True, f"{len(nomes)} biblioteca(s) instalada(s). Feche e abra o sistema para usar todas.")
    else:
        _terminar(False, ("Faltou instalar: " + ", ".join(faltam) + ". " if faltam else "") +
                  "Se a rede da empresa bloqueia a internet, use o BAIXAR_PACOTES_OFFLINE.bat num PC com internet "
                  "e copie a pasta \"pacotes\" para a pasta do sistema.")


def _arquivos() -> None:
    from .atualizador import atualizar_python, versoes_remotas
    _log("Conferindo a versão no GitHub...")
    remoto = versoes_remotas().get("python")
    if remoto is None:
        return _terminar(False, "Sem acesso ao GitHub agora (internet ou rede da empresa).")
    _log(f"Baixando o pacote {remoto} e repondo os arquivos que faltam...")
    if atualizar_python(remoto):
        _terminar(True, "Arquivos repostos. O sistema vai reiniciar.")
        if REINICIAR["fn"]:
            threading.Timer(2.0, REINICIAR["fn"]).start()
    else:
        _terminar(False, "Não consegui baixar os arquivos agora. Veja dados_locais/atualizacoes.log.")


def executar(acao: str) -> dict:
    if acao == "instalar_pc":
        return _abrir_bat("INSTALAR.bat")
    if acao == "atalho":
        from .atalho import garantir
        msg = garantir(forcar=True)
        return {"ok": msg.startswith("Atalho criado") or msg.startswith("Atalho OK"), "msg": msg}
    if acao == "bibliotecas":
        nomes = [n for n in bibliotecas.todas() if (_win() or n != "pywin32") and not bibliotecas.instalada(n)]
        if not nomes:
            return {"ok": True, "msg": "Todas as bibliotecas já estão instaladas."}
        if not em_venv():
            return _abrir_bat("INSTALAR_BIBLIOTECAS.bat")
        if not _comecar("bibliotecas"):
            return {"ok": False, "msg": "Já tem uma instalação em andamento."}
        threading.Thread(target=_pip, args=(nomes,), daemon=True, name="instalar-bibliotecas").start()
        return {"ok": True, "andamento": True, "msg": "Instalando as bibliotecas..."}
    if acao == "arquivos":
        if not _comecar("arquivos"):
            return {"ok": False, "msg": "Já tem uma instalação em andamento."}
        threading.Thread(target=_arquivos, daemon=True, name="repor-arquivos").start()
        return {"ok": True, "andamento": True, "msg": "Baixando os arquivos do sistema..."}
    return {"ok": False, "msg": "Ação desconhecida."}
