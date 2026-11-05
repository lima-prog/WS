"""
ARQUIVOS DO PC — leitura das pastas do computador (Explorador de Arquivos) pelo sistema.

Os programas PPCP (Análise DBF, Agrupador, Etiquetas...) passam a abrir arquivos direto das
pastas do PC: unidades (C:, G:, H:, rede mapeada), Área de Trabalho, Documentos, Downloads,
pastas favoritas e recentes. Também aceita colar o caminho copiado do Explorador
("Copiar como caminho").

Segurança: só o próprio computador acessa estas funções (127.0.0.1). Quem entra pela
rede (--rede) usa o sistema normalmente, mas não enxerga os arquivos deste PC.
"""
from __future__ import annotations

import json
import mimetypes
import os
import string
import sys
import time
from pathlib import Path

from . import acesso_rapido, compactados
from .config import PASTA_DADOS

ARQ_PASTAS = PASTA_DADOS / "pastas.json"
LIMITE_LISTA = 3000          # itens por pasta mostrados de uma vez
LIMITE_BUSCA = 300           # resultados da busca
LIMITE_BUSCA_SEG = 8         # segundos máximos de busca
NO_WINDOWS = sys.platform.startswith("win")


# ---------------- caminhos ----------------
def limpar_caminho(texto: str) -> str:
    """Aceita o caminho do jeito que vem do Explorador: com aspas, com barra no fim, com %USERPROFILE%..."""
    c = (texto or "").strip().strip('"').strip("'").strip()
    c = os.path.expandvars(os.path.expanduser(c))
    if NO_WINDOWS and len(c) == 2 and c[1] == ":":
        c += "\\"
    return c


def _pasta_usuario(nome_registro: str, padrao: str) -> str | None:
    """Acha Área de Trabalho/Documentos/Downloads mesmo quando estão no OneDrive ou em outro lugar."""
    if NO_WINDOWS:
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders") as k:
                valor = os.path.expandvars(winreg.QueryValueEx(k, nome_registro)[0])
                if os.path.isdir(valor):
                    return valor
        except OSError:
            pass
    p = Path.home() / padrao
    return str(p) if p.is_dir() else None


def _unidades() -> list[dict]:
    if not NO_WINDOWS:
        return [{"nome": "Raiz (/)", "caminho": "/", "tipo": "unidade"}]
    saida = []
    tipos = {}
    try:
        import ctypes
        for letra in string.ascii_uppercase:
            tipos[letra] = ctypes.windll.kernel32.GetDriveTypeW(f"{letra}:\\")
    except Exception:
        pass
    nomes_tipo = {2: "Removível", 3: "Disco local", 4: "Rede", 5: "CD/DVD"}
    for letra in string.ascii_uppercase:
        raiz = f"{letra}:\\"
        if tipos.get(letra, 0) in (0, 1) and not os.path.exists(raiz):
            continue
        rotulo = nomes_tipo.get(tipos.get(letra, 3), "Unidade")
        saida.append({"nome": f"{rotulo} ({letra}:)", "caminho": raiz, "tipo": "unidade"})
    return saida


# ---------------- favoritos e recentes (ficam só neste PC) ----------------
def _ler_pastas() -> dict:
    try:
        d = json.loads(ARQ_PASTAS.read_text(encoding="utf-8"))
        d.setdefault("favoritos", []); d.setdefault("recentes", [])
        return d
    except (OSError, ValueError):
        return {"favoritos": [], "recentes": []}


def _gravar_pastas(d: dict) -> None:
    PASTA_DADOS.mkdir(parents=True, exist_ok=True)
    tmp = ARQ_PASTAS.with_suffix(".tmp")
    tmp.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, ARQ_PASTAS)


def locais() -> dict:
    """Painel da esquerda do seletor: unidades, pastas do usuário, favoritos e recentes."""
    pastas = []
    for chave, padrao, nome in (("Desktop", "Desktop", "Área de Trabalho"),
                                ("Personal", "Documents", "Documentos"),
                                ("{374DE290-123F-4565-9164-39C4925E467B}", "Downloads", "Downloads")):
        c = _pasta_usuario(chave, padrao)
        if c:
            pastas.append({"nome": nome, "caminho": c, "tipo": "pasta"})
    d = _ler_pastas()
    return {
        "unidades": _unidades(),
        "pastas": pastas,
        "favoritos": [f for f in d["favoritos"] if isinstance(f, dict) and f.get("caminho")],
        "recentes": [r for r in d["recentes"] if isinstance(r, str)][:8],
        "acesso_rapido": acesso_rapido.listar(),      # pastas fixadas no Explorador do Windows
        "separador": os.sep,
    }


def favoritar(caminho: str, nome: str | None = None, remover: bool = False) -> dict:
    caminho = limpar_caminho(caminho)
    d = _ler_pastas()
    d["favoritos"] = [f for f in d["favoritos"] if f.get("caminho") != caminho]
    if not remover:
        if not os.path.isdir(caminho):
            raise FileNotFoundError("Pasta não encontrada: " + caminho)
        d["favoritos"].append({"nome": nome or os.path.basename(caminho.rstrip("\\/")) or caminho, "caminho": caminho})
        acesso_rapido.fixar(caminho)          # também fixa no Acesso rápido do Explorador (se der)
    else:
        acesso_rapido.desafixar(caminho)
    _gravar_pastas(d)
    return locais()


def marcar_recente(caminho: str) -> None:
    d = _ler_pastas()
    d["recentes"] = [caminho] + [r for r in d["recentes"] if r != caminho][:11]
    try:
        _gravar_pastas(d)
    except OSError:
        pass


# ---------------- listar, buscar, ler ----------------
# Pastas normais E arquivos compactados (.zip, .7z, .tar...) — veja compactados.py
def _item(entrada: os.DirEntry) -> dict | None:
    try:
        pasta = entrada.is_dir()
        st = entrada.stat()
    except OSError:
        return None
    if entrada.name.startswith(("~$", ".")) or entrada.name in ("desktop.ini", "Thumbs.db"):
        return None
    return {"nome": entrada.name, "caminho": entrada.path, "pasta": pasta,
            "tamanho": 0 if pasta else st.st_size, "modificado": int(st.st_mtime),
            "pacote": (not pasta) and compactados.e_compactado(entrada.name)}


def _extensoes(filtro: str) -> set[str]:
    return {e.strip().lower() if e.strip().startswith(".") else "." + e.strip().lower()
            for e in (filtro or "").split(",") if e.strip() and "/" not in e and e.strip() != "*"}


def _aceito(i: dict, exts: set[str]) -> bool:
    """Pastas e compactados sempre aparecem (dá para entrar neles); arquivos só se o tipo for aceito."""
    if i["pasta"] or i.get("pacote") or not exts:
        return True
    nome = i["nome"].lower()
    return any(nome.endswith(e) for e in exts)


def _pai(caminho: str) -> str:
    pai = os.path.dirname(caminho.rstrip("\\/")) if caminho.rstrip("\\/") else ""
    if NO_WINDOWS and len(caminho.rstrip("\\")) == 2:   # raiz de unidade (C:\)
        return ""
    return pai if pai and pai != caminho else ""


def _erro_caminho(caminho: str) -> FileNotFoundError:
    if caminho.startswith("\\\\"):
        return FileNotFoundError("Pasta não encontrada na rede: " + caminho + " — confira o caminho e se a rede está conectada.")
    return FileNotFoundError("Pasta não encontrada: " + caminho + " — confira o caminho.")


def listar(caminho: str, filtro: str = "") -> dict:
    caminho = limpar_caminho(caminho)
    exts = _extensoes(filtro)
    dentro = None
    if not os.path.isdir(caminho):
        if os.path.isfile(caminho) and compactados.e_compactado(caminho):
            dentro = (caminho, "")                       # o próprio .zip: entra nele
        elif os.path.isfile(caminho):                    # colou o caminho de um arquivo: abre a pasta dele
            caminho = os.path.dirname(caminho)
        else:
            dentro = compactados.dividir(caminho)        # caminho que passa por dentro de um .zip
            if not dentro:
                raise _erro_caminho(caminho)
    itens, ocultos = [], 0
    if dentro:
        for i in compactados.listar(*dentro):
            if _aceito(i, exts):
                itens.append(i)
            else:
                ocultos += 1
    else:
        with os.scandir(caminho) as it:
            for e in it:
                i = _item(e)
                if not i:
                    continue
                if not _aceito(i, exts):
                    ocultos += 1
                    continue
                itens.append(i)
                if len(itens) >= LIMITE_LISTA:
                    break
    itens.sort(key=lambda x: (not (x["pasta"] or x.get("pacote")), x["nome"].lower()))
    marcar_recente(caminho)
    return {"caminho": caminho, "pai": _pai(caminho), "itens": itens, "compactado": bool(dentro),
            "ocultos_pelo_filtro": ocultos, "cortado": len(itens) >= LIMITE_LISTA}


def buscar(caminho: str, termo: str, filtro: str = "") -> dict:
    """Procura pelo nome na pasta, nas subpastas e dentro dos .zip (até 8 segundos / 300 resultados)."""
    caminho = limpar_caminho(caminho)
    termo = (termo or "").strip().lower()
    exts = _extensoes(filtro)
    achados, inicio = [], time.monotonic()
    dentro = compactados.dividir(caminho) if not os.path.isdir(caminho) else None
    if dentro or (os.path.isfile(caminho) and compactados.e_compactado(caminho)):
        arq = dentro[0] if dentro else caminho
        pref = os.path.join(arq, *dentro[1].split("/")) if dentro and dentro[1] else arq
        achados = [i for i in compactados.buscar(arq, termo) if i["caminho"].startswith(pref) and _aceito(i, exts)]
        return {"caminho": caminho, "termo": termo, "itens": achados[:LIMITE_BUSCA], "incompleta": len(achados) > LIMITE_BUSCA}
    pilha = [caminho]
    while pilha and len(achados) < LIMITE_BUSCA and time.monotonic() - inicio < LIMITE_BUSCA_SEG:
        atual = pilha.pop()
        try:
            with os.scandir(atual) as it:
                for e in it:
                    i = _item(e)
                    if not i:
                        continue
                    if i["pasta"]:
                        pilha.append(i["caminho"])
                    elif i["pacote"] and i["tamanho"] < 300 * 1024 * 1024:
                        achados.extend(x for x in compactados.buscar(i["caminho"], termo) if _aceito(x, exts) and not x["pasta"])
                    if termo in i["nome"].lower() and _aceito(i, exts):
                        achados.append(i)
        except OSError:
            continue
    achados.sort(key=lambda x: (not x["pasta"], -x["modificado"]))
    return {"caminho": caminho, "termo": termo, "itens": achados[:LIMITE_BUSCA],
            "incompleta": bool(pilha) or len(achados) >= LIMITE_BUSCA}


def ler_arquivo(caminho: str) -> tuple[bytes, str, str, int]:
    """Devolve (conteúdo, nome, tipo, data de modificação em ms). Lê também de dentro de .zip."""
    caminho = limpar_caminho(caminho)
    tipo = mimetypes.guess_type(caminho)[0] or "application/octet-stream"
    nome = os.path.basename(caminho.rstrip("\\/"))
    if os.path.isfile(caminho):
        with open(caminho, "rb") as f:
            dados = f.read()
        return dados, nome, tipo, int(os.path.getmtime(caminho) * 1000)
    dentro = compactados.dividir(caminho)
    if dentro and dentro[1]:
        dados, data = compactados.ler(*dentro)
        return dados, nome, tipo, data
    raise FileNotFoundError("Arquivo não encontrado: " + caminho)


def abrir_no_explorador(caminho: str) -> None:
    caminho = limpar_caminho(caminho)
    if not os.path.exists(caminho):
        dentro = compactados.dividir(caminho)          # dentro de um .zip: mostra o .zip no Explorador
        if not dentro:
            raise FileNotFoundError("Caminho não encontrado: " + caminho)
        caminho = dentro[0]
    if NO_WINDOWS:
        import subprocess
        if os.path.isfile(caminho):
            subprocess.Popen('explorer /select,"%s"' % caminho)
        else:
            os.startfile(caminho)  # type: ignore[attr-defined]
    else:
        raise OSError("Abrir no Explorador só funciona no Windows.")
