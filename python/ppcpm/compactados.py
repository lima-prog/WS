"""
ARQUIVOS COMPACTADOS como se fossem pastas.

O sistema entra em .zip (e outros) do mesmo jeito que entra numa pasta, inclusive pelo caminho
colado do Explorador, por exemplo:

    \\\\172.25.0.7\\lib-eng\\LIBERAÇÕES ENGENHARIA\\2151\\2151-3-05_L1.zip\\DBF

Tipos lidos:
  .zip                                  -> sempre (já vem com o Python)
  .tar .tgz .tar.gz .tar.bz2 .tar.xz    -> sempre (já vem com o Python)
  .7z                                   -> com a biblioteca py7zr (INSTALAR_BIBLIOTECAS)
  .rar                                  -> com a biblioteca rarfile + o programa UnRAR/7-Zip no PC
Nada é extraído no disco: o arquivo é lido direto de dentro do compactado.
"""
from __future__ import annotations

import os
import tarfile
import time
import zipfile
from datetime import datetime

EXTENSOES = (".zip", ".tar", ".tgz", ".tar.gz", ".tar.bz2", ".tbz2", ".tar.xz", ".txz", ".7z", ".rar")
_CACHE: dict = {}          # caminho -> (mtime, tamanho, entradas)


def e_compactado(nome: str) -> bool:
    return nome.lower().endswith(EXTENSOES)


def extensao(nome: str) -> str:
    n = nome.lower()
    return next((e for e in sorted(EXTENSOES, key=len, reverse=True) if n.endswith(e)), "")


def dividir(caminho: str) -> tuple[str, str] | None:
    """'...\\x.zip\\DBF\\a.csv' -> ('...\\x.zip', 'DBF/a.csv'). None se o caminho não passa por um compactado."""
    p, resto = caminho.rstrip("\\/"), []
    while p and not os.path.exists(p):
        pai, nome = os.path.split(p)
        if not nome or pai == p:
            return None
        resto.insert(0, nome)
        p = pai
    if p and os.path.isfile(p) and e_compactado(p):
        return p, "/".join(resto)
    return None


# ---------------- leitura de cada tipo ----------------
def _nome_zip(info: zipfile.ZipInfo) -> str:
    """Zips feitos no Windows guardam acentos na página 850 (ex.: LIBERAÇÕES). Corrige o nome."""
    if info.flag_bits & 0x800:
        return info.filename
    try:
        return info.filename.encode("cp437").decode("cp850")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return info.filename


def _abrir(caminho: str):
    ext = extensao(caminho)
    if ext == ".zip":
        return "zip", zipfile.ZipFile(caminho)
    if ext == ".7z":
        try:
            import py7zr  # type: ignore
        except ImportError:
            raise OSError("Para abrir .7z instale as bibliotecas (INSTALAR_BIBLIOTECAS) — falta py7zr.")
        return "7z", py7zr.SevenZipFile(caminho, "r")
    if ext == ".rar":
        try:
            import rarfile  # type: ignore
        except ImportError:
            raise OSError("Para abrir .rar instale as bibliotecas (INSTALAR_BIBLIOTECAS) e o 7-Zip ou WinRAR no PC.")
        return "rar", rarfile.RarFile(caminho)
    return "tar", tarfile.open(caminho, "r:*")


def entradas(caminho: str) -> dict:
    """{'pasta/arquivo.csv': (é_pasta, tamanho, data, nome_original)} — guardado em memória até o arquivo mudar."""
    st = os.stat(caminho)
    c = _CACHE.get(caminho)
    if c and c[0] == st.st_mtime and c[1] == st.st_size:
        return c[2]
    tipo, arq = _abrir(caminho)
    saida: dict = {}
    try:
        if tipo == "zip":
            for i in arq.infolist():
                nome = _nome_zip(i).replace("\\", "/").strip("/")
                try:
                    data = time.mktime(i.date_time + (0, 0, -1))
                except (OverflowError, ValueError):
                    data = st.st_mtime
                saida[nome] = (i.is_dir(), i.file_size, data, i.filename)
        elif tipo == "tar":
            for m in arq.getmembers():
                if m.isdir() or m.isfile():
                    saida[m.name.strip("/")] = (m.isdir(), m.size, m.mtime, m.name)
        elif tipo == "7z":
            for i in arq.list():
                d = i.creationtime.timestamp() if isinstance(i.creationtime, datetime) else st.st_mtime
                saida[i.filename.replace("\\", "/").strip("/")] = (i.is_directory, i.uncompressed or 0, d, i.filename)
        else:  # rar
            for i in arq.infolist():
                saida[i.filename.replace("\\", "/").strip("/")] = (i.is_dir(), i.file_size,
                                                                     time.mktime(i.date_time + (0, 0, -1)), i.filename)
    finally:
        arq.close()
    # pastas que só existem dentro dos caminhos (zip sem entrada de pasta)
    for nome in list(saida):
        partes = nome.split("/")
        for k in range(1, len(partes)):
            saida.setdefault("/".join(partes[:k]), (True, 0, saida[nome][2], ""))
    if len(_CACHE) > 20:
        _CACHE.clear()
    _CACHE[caminho] = (st.st_mtime, st.st_size, saida)
    return saida


def _achar(ent: dict, interno: str) -> str | None:
    """Acha a entrada sem diferenciar maiúsculas/minúsculas (o Windows não diferencia)."""
    if interno in ent:
        return interno
    baixo = interno.lower()
    return next((n for n in ent if n.lower() == baixo), None)


def listar(arquivo: str, interno: str) -> list[dict]:
    ent = entradas(arquivo)
    interno = interno.strip("/")
    if interno:
        real = _achar(ent, interno)
        if real is None or not ent[real][0]:
            raise FileNotFoundError(f"Pasta não encontrada dentro de {os.path.basename(arquivo)}: {interno}")
        interno = real
    prefixo = interno + "/" if interno else ""
    itens = []
    for nome, (pasta, tam, data, _) in ent.items():
        if not nome.startswith(prefixo) or nome == interno:
            continue
        resto = nome[len(prefixo):]
        if "/" in resto or not resto:
            continue
        caminho = os.path.join(arquivo, *nome.split("/"))
        itens.append({"nome": resto, "caminho": caminho, "pasta": pasta, "tamanho": 0 if pasta else tam,
                      "modificado": int(data), "dentro_de": os.path.basename(arquivo),
                      "pacote": (not pasta) and e_compactado(resto)})
    return itens


def ler(arquivo: str, interno: str) -> tuple[bytes, int]:
    ent = entradas(arquivo)
    real = _achar(ent, interno.strip("/"))
    if real is None or ent[real][0]:
        raise FileNotFoundError(f"Arquivo não encontrado dentro de {os.path.basename(arquivo)}: {interno}")
    original, data = ent[real][3], int(ent[real][2] * 1000)
    tipo, arq = _abrir(arquivo)
    try:
        if tipo == "zip":
            return arq.read(original), data
        if tipo == "tar":
            f = arq.extractfile(original)
            return (f.read() if f else b""), data
        if tipo == "7z":   # py7zr extrai para uma pasta temporária, lê e apaga
            import tempfile
            with tempfile.TemporaryDirectory(prefix="ppcpm_") as tmp:
                arq.extract(path=tmp, targets=[original])
                with open(os.path.join(tmp, *original.replace("\\", "/").split("/")), "rb") as f:
                    return f.read(), data
        return arq.read(original), data
    finally:
        arq.close()


def buscar(arquivo: str, termo: str) -> list[dict]:
    """Procura pelo nome dentro do compactado (usado pela busca nas subpastas)."""
    try:
        ent = entradas(arquivo)
    except Exception:
        return []
    achados = []
    for nome, (pasta, tam, data, _) in ent.items():
        base = nome.rsplit("/", 1)[-1]
        if termo in base.lower():
            achados.append({"nome": base, "caminho": os.path.join(arquivo, *nome.split("/")), "pasta": pasta,
                            "tamanho": 0 if pasta else tam, "modificado": int(data),
                            "dentro_de": os.path.basename(arquivo), "pacote": False})
    return achados
