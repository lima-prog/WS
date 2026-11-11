"""
PACOTES — leitura da "PLANILHA DE CONTROLE DE PACOTES ENTREGUES" (aba LIBERAÇÃO DE PCTS) para a Tela inicial.

O caminho da planilha (no drive do PPCPM) fica guardado em dados_locais/pacotes.json.
A Tela inicial pergunta a cada minuto; quando a planilha muda (novo pacote, nova obra), o sistema já lê de novo.
Lê o .xlsx direto (zip + XML), sem precisar do Excel aberto e sem biblioteca de fora.
"""
from __future__ import annotations

import json
import os
import re
import threading
import unicodedata
import zipfile
from pathlib import Path

from .config import PASTA_DADOS

ARQ_CFG = PASTA_DADOS / "pacotes.json"
COLUNAS = ["lote", "of_trecho", "ano_semana", "peso_lic", "kg_prep", "kg_nprep", "data_inicio", "status"]
_cache: dict = {"chave": None, "dados": None}
_trava = threading.Lock()


def _norm(t) -> str:
    t = unicodedata.normalize("NFD", str(t or ""))
    return "".join(c for c in t if unicodedata.category(c) != "Mn").upper().strip()


def caminho() -> str:
    try:
        return json.loads(ARQ_CFG.read_text(encoding="utf-8")).get("caminho") or ""
    except (OSError, ValueError):
        return ""


def definir(c: str) -> dict:
    c = (c or "").strip().strip('"')
    if not c:
        raise ValueError("Escolha a planilha de controle de pacotes.")
    if not os.path.isfile(c):
        raise ValueError("Arquivo não encontrado: " + c)
    ler(c)                               # confere se é a planilha certa antes de guardar
    PASTA_DADOS.mkdir(parents=True, exist_ok=True)
    ARQ_CFG.write_text(json.dumps({"caminho": c}, ensure_ascii=False), encoding="utf-8")
    return estado()


def limpar() -> dict:
    """Botão Atualizar da Tela inicial: desliga a planilha (para colocar uma nova, com novos lotes)."""
    try:
        ARQ_CFG.unlink()
    except OSError:
        pass
    with _trava:
        _cache["chave"] = None
        _cache["dados"] = None
    return {"caminho": "", "erro": ""}


def _col(ref: str) -> int:
    n = 0
    for ch in re.match(r"[A-Z]+", ref).group(0):
        n = n * 26 + ord(ch) - 64
    return n


def _txt(xml: str) -> str:
    partes = re.findall(r"<(?:[\w.-]+:)?t\b[^>]*>(.*?)</(?:[\w.-]+:)?t>", xml, re.S)
    s = "".join(partes)
    return (s.replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"').replace("&apos;", "'").replace("&amp;", "&"))


def ler(c: str) -> list[dict]:
    """Linhas da aba LIBERAÇÃO DE PCTS: LOTE, OF-TRECHO, ANO-SEMANA, PESO LIC/LOTE, KG PREP, KG ÑPREP, DATA INÍCIO, STATUS."""
    with zipfile.ZipFile(c) as z:
        wb = z.read("xl/workbook.xml").decode("utf-8")
        rels = z.read("xl/_rels/workbook.xml.rels").decode("utf-8")
        alvo = {}
        for m in re.finditer(r"<(?:[\w.-]+:)?Relationship\b([^>]*)>", rels):
            i = re.search(r'\sId="([^"]*)"', m.group(1))
            t = re.search(r'\sTarget="([^"]*)"', m.group(1))
            if i and t:
                alvo[i.group(1)] = t.group(1)
        aba = None
        for m in re.finditer(r"<(?:[\w.-]+:)?sheet\b([^>]*)/?>", wb):
            nome = re.search(r'\sname="([^"]*)"', m.group(1))
            rid = re.search(r'\s(?:[\w.-]+:)?id="([^"]*)"', m.group(1))
            if nome and rid and "LIBERA" in _norm(nome.group(1)):
                t = alvo.get(rid.group(1), "")
                aba = t[1:] if t.startswith("/") else "xl/" + t.replace("../", "")
                break
        if not aba:
            raise ValueError('A planilha não tem a aba "LIBERAÇÃO DE PCTS".')
        ss = []
        if "xl/sharedStrings.xml" in z.namelist():
            sx = z.read("xl/sharedStrings.xml").decode("utf-8")
            ss = [_txt(m.group(0)) for m in re.finditer(r"<(?:[\w.-]+:)?si\b.*?</(?:[\w.-]+:)?si>", sx, re.S)]
        xml = z.read(aba).decode("utf-8")
    linhas, cab = [], None
    for mr in re.finditer(r"<(?:[\w.-]+:)?row\b([^>]*?)(?:/>|>(.*?)</(?:[\w.-]+:)?row>)", xml, re.S):
        corpo = mr.group(2) or ""
        rnum = re.search(r'\sr="(\d+)"', mr.group(1))
        vals = {}
        for mc in re.finditer(r"<(?:[\w.-]+:)?c\b([^>]*?)(?:/>|>(.*?)</(?:[\w.-]+:)?c>)", corpo, re.S):
            a, dentro = mc.group(1), mc.group(2) or ""
            ref = re.search(r'\sr="([A-Z]+)\d+"', a)
            if not ref:
                continue
            col = _col(ref.group(1))
            if col > 8:
                continue
            tipo = re.search(r'\st="([^"]*)"', a)
            tipo = tipo.group(1) if tipo else ""
            v = re.search(r"<(?:[\w.-]+:)?v>(.*?)</(?:[\w.-]+:)?v>", dentro, re.S)
            if tipo == "s" and v:
                try:
                    val = ss[int(v.group(1))]
                except (ValueError, IndexError):
                    val = ""
            elif tipo == "inlineStr":
                val = _txt(dentro)
            elif tipo in ("str", "e"):
                val = (v.group(1).replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"')
                       .replace("&apos;", "'").replace("&amp;", "&")) if v else ""
            elif v:
                try:
                    f = float(v.group(1))
                    val = int(f) if f.is_integer() else f
                except ValueError:
                    val = v.group(1)
            else:
                val = None
            vals[col] = val
        if cab is None:
            if _norm(vals.get(1)) == "LOTE" and "TRECHO" in _norm(vals.get(2)):
                cab = int(rnum.group(1)) if rnum else 0
            continue
        lote, obra = vals.get(1), vals.get(2)
        if lote in (None, "") or obra in (None, ""):
            continue
        d = {k: vals.get(i + 1) for i, k in enumerate(COLUNAS)}
        d["lote"] = str(int(lote)) if isinstance(lote, (int, float)) else str(lote).strip()
        d["of_trecho"] = str(obra).strip()
        for k in ("ano_semana", "peso_lic", "data_inicio", "status"):
            if d[k] is not None and not isinstance(d[k], str):
                d[k] = str(d[k])
        for k in ("kg_prep", "kg_nprep"):
            if not isinstance(d[k], (int, float)):
                d[k] = None
        d["linha"] = int(rnum.group(1)) if rnum else None
        linhas.append(d)
    if cab is None:
        raise ValueError('Não achei o cabeçalho "LOTE | OF-TRECHO" na aba LIBERAÇÃO DE PCTS.')
    return linhas


def estado(com_linhas: bool = False, desde: str = "") -> dict:
    """{caminho, modificado, linhas?}. Só manda as linhas quando a planilha mudou desde 'desde'."""
    c = caminho()
    if not c:
        return {"caminho": "", "erro": ""}
    try:
        st = os.stat(c)
    except OSError:
        return {"caminho": c, "erro": "A planilha não está acessível agora (drive desconectado?)."}
    mod = f"{int(st.st_mtime)}-{st.st_size}"
    r = {"caminho": c, "modificado": mod, "erro": ""}
    if com_linhas and mod != desde:
        with _trava:
            if _cache["chave"] != (c, mod):
                try:
                    _cache["dados"] = ler(c)
                    _cache["chave"] = (c, mod)
                except Exception as e:  # noqa: BLE001 — planilha sendo salva / bloqueada: tenta no próximo minuto
                    return {**r, "erro": f"Não consegui ler a planilha agora ({e}). Tento de novo em 1 minuto."}
            r["linhas"] = _cache["dados"]
    return r
