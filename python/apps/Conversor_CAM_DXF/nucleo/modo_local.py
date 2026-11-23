# -*- coding: utf-8 -*-
"""
Execução LOCAL automática (só biblioteca padrão — é importado ANTES de qualquer coisa pesada).

Problema medido no PC do Daniel: abrindo `main.py` direto da pasta de rede (A:\\), o programa levava ~16 s pra abrir e
cada app externo ~12 s (cada .py, ícone e biblioteca atravessa a rede). Solução: se o main.py perceber que está numa
unidade de REDE, ele copia o código (só o que mudou) pra `%LOCALAPPDATA%\\PPCP_Ferramentas\\app`, roda o programa de lá
e fica esperando; os DADOS (bancos, layout, ícones do usuário, memória do roteirizador) continuam na pasta do servidor
(variável PPCP_DADOS — ver nucleo/caminhos.py). É o mesmo esquema do `iniciar_ppcp.bat`, mas automático.

Quando NÃO faz nada (roda direto, como sempre): não é Windows; é um .exe (PyInstaller); a pasta não é de rede;
PPCP_DADOS já definida (já veio do .bat ou do processo pai); ou PPCP_SEM_LOCAL=1 (use isso pra depurar o código do servidor).
Se a cópia falhar por qualquer motivo, segue rodando do servidor (mais lento, mas funciona).
"""
import fnmatch
import os
import shutil
import subprocess
import sys

# Mesmas exclusões do iniciar_ppcp.bat: dados do usuário, logs e pastas antigas/inúteis NÃO vão pra cópia local.
PASTAS_EXCLUIDAS = {"__pycache__", "claude outputs", "relatorio", "roteirizador_dxf", "referencia_html",
                    "icones_usuario", ".git", ".vscode", ".idea", "venv", ".venv"}
ARQUIVOS_EXCLUIDOS = ("*.db", "*.db-journal", "*.db-wal", "*.db-shm", "app_dxf_ppcp_log.txt*", "layout_desktop_*.json",
                      "etiquetas_impressora.json", "continuidade.md", "*.bak", "*.pyc", "*.tmp")


def _em_unidade_de_rede(caminho):
    caminho = os.path.abspath(caminho)
    if caminho.startswith("\\\\"):
        return True
    try:
        import ctypes
        drv = os.path.splitdrive(caminho)[0] + "\\"
        return ctypes.windll.kernel32.GetDriveTypeW(drv) == 4        # DRIVE_REMOTE
    except Exception:
        return False


def _arquivo_excluido(nome):
    n = nome.lower()
    return any(fnmatch.fnmatch(n, p) for p in ARQUIVOS_EXCLUIDOS)


def _mesmo(origem, destino):
    try:
        a, b = os.stat(origem), os.stat(destino)
        return a.st_size == b.st_size and int(a.st_mtime) == int(b.st_mtime)
    except OSError:
        return False


def sincronizar(origem, destino):
    """Espelha o código de `origem` em `destino` (copia o que mudou, apaga o que sumiu). Devolve (copiados, apagados)."""
    copiados = apagados = 0
    esperados = set()
    for pasta, subs, arqs in os.walk(origem):
        subs[:] = [d for d in subs if d.lower() not in PASTAS_EXCLUIDAS]
        rel = os.path.relpath(pasta, origem)
        pasta_dest = destino if rel == "." else os.path.join(destino, rel)
        os.makedirs(pasta_dest, exist_ok=True)
        for nome in arqs:
            if _arquivo_excluido(nome):
                continue
            o, d = os.path.join(pasta, nome), os.path.join(pasta_dest, nome)
            esperados.add(os.path.normcase(d))
            if not _mesmo(o, d):
                shutil.copy2(o, d)
                copiados += 1
    # remove da cópia local o que não existe mais no servidor (só arquivos de código; __pycache__ fica)
    for pasta, subs, arqs in os.walk(destino):
        subs[:] = [d for d in subs if d.lower() not in PASTAS_EXCLUIDAS]
        for nome in arqs:
            d = os.path.join(pasta, nome)
            if os.path.normcase(d) not in esperados and not _arquivo_excluido(nome):
                try:
                    os.remove(d)
                    apagados += 1
                except OSError:
                    pass
    return copiados, apagados


def garantir_execucao_local(arquivo_main):
    """Chamar no topo do main.py. Se estiver em rede: sincroniza, roda de lá (espera) e encerra com o mesmo código de saída."""
    try:
        if sys.platform != "win32" or getattr(sys, "frozen", False):
            return
        if os.environ.get("PPCP_DADOS") or os.environ.get("PPCP_SEM_LOCAL") == "1":
            return
        raiz = os.path.dirname(os.path.abspath(arquivo_main))
        if not _em_unidade_de_rede(raiz):
            return
        base = os.environ.get("LOCALAPPDATA") or os.path.join(os.path.expanduser("~"), "AppData", "Local")
        destino = os.path.join(base, "PPCP_Ferramentas", "app")
        if os.path.normcase(os.path.abspath(destino)) == os.path.normcase(raiz):
            return
        sincronizar(raiz, destino)
        local_main = os.path.join(destino, "main.py")
        if not os.path.exists(local_main):
            return
    except Exception:
        return                                   # qualquer problema: segue do servidor
    env = os.environ.copy()
    env["PPCP_DADOS"] = raiz
    try:
        codigo = subprocess.call([sys.executable, local_main, *sys.argv[1:]], cwd=destino, env=env)
    except Exception:
        return
    sys.exit(codigo)
