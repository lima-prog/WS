"""
IMPRESSÃO DIRETA NA ZEBRA (cabo USB/rede, impressora instalada no Windows).

Mesmo método do antigo Etiquetas_Fluxos.exe (impressao.py):
  1º) RAW direto no spooler do Windows via win32print (biblioteca pywin32);
  2º) se falhar, grava um .zpl temporário e usa `copy /b` para o nome da impressora
      (funciona quando a impressora está compartilhada).
A aba "Impressão de Etiquetas" gera o ZPL e o Python só entrega para a impressora.
A última impressora usada fica guardada em dados_locais/etiquetas_impressora.json.
"""
from __future__ import annotations

import json
import os
import subprocess
import tempfile

from .config import PASTA_DADOS

try:  # só existe no Windows com pywin32 instalado (INSTALAR_BIBLIOTECAS)
    import win32print  # type: ignore
except ImportError:
    win32print = None

ARQ_IMPRESSORA = PASTA_DADOS / "etiquetas_impressora.json"


def _e_zebra(nome: str) -> bool:
    n = nome.lower()
    return "zebra" in n or "zdesigner" in n or "zpl" in n


def listar_impressoras() -> list[dict]:
    """Impressoras do Windows (Zebras primeiro), com a porta (USB001, IP...) e qual é a padrão."""
    if win32print is None:
        raise RuntimeError("Falta a biblioteca pywin32. Rode o INSTALAR_BIBLIOTECAS para imprimir direto na Zebra.")
    flags = win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
    try:
        padrao = win32print.GetDefaultPrinter()
    except Exception:
        padrao = ""
    saida = []
    for p in win32print.EnumPrinters(flags, None, 2):
        nome, porta = p.get("pPrinterName", ""), p.get("pPortName", "")
        saida.append({"name": nome, "connection": porta or "", "padrao": nome == padrao, "zebra": _e_zebra(nome)})
    saida.sort(key=lambda x: (not x["zebra"], x["name"].lower()))
    return saida


def ultima_impressora() -> str | None:
    try:
        return json.loads(ARQ_IMPRESSORA.read_text(encoding="utf-8")).get("ultima_impressora")
    except (OSError, ValueError):
        return None


def salvar_ultima_impressora(nome: str) -> None:
    try:
        PASTA_DADOS.mkdir(parents=True, exist_ok=True)
        ARQ_IMPRESSORA.write_text(json.dumps({"ultima_impressora": nome}, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError:
        pass


def _preparar(zpl: str) -> bytes:
    """Acentos (OBRA, observação) saem certos: liga UTF-8 na Zebra (^CI28) quando o texto tem acento."""
    if any(ord(c) > 127 for c in zpl) and "^CI" not in zpl:
        zpl = zpl.replace("^XA", "^XA^CI28", )
    return zpl.encode("utf-8")


def enviar_zpl(zpl: str, impressora: str) -> str:
    """Manda o ZPL para a impressora. Devolve o método usado. Levanta erro se os 2 métodos falharem."""
    if not impressora:
        raise ValueError("Escolha a impressora.")
    dados = _preparar(zpl)
    erro_raw = None
    if win32print is not None:
        try:
            h = win32print.OpenPrinter(impressora)
            try:
                win32print.StartDocPrinter(h, 1, ("Etiqueta PPCPM", None, "RAW"))
                win32print.StartPagePrinter(h)
                win32print.WritePrinter(h, dados)
                win32print.EndPagePrinter(h)
                win32print.EndDocPrinter(h)
            finally:
                win32print.ClosePrinter(h)
            salvar_ultima_impressora(impressora)
            return "raw"
        except Exception as e:
            erro_raw = e
    else:
        erro_raw = RuntimeError("falta a biblioteca pywin32 (INSTALAR_BIBLIOTECAS)")
    # 2º método: copiar o arquivo .zpl para a impressora (impressora compartilhada)
    with tempfile.NamedTemporaryFile(mode="wb", suffix=".zpl", delete=False) as f:
        f.write(dados)
        temp = f.name
    try:
        r = subprocess.run(f'copy /b "{temp}" "{impressora}"', shell=True, capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError((r.stderr or r.stdout or "").strip() or "falhou")
        salvar_ultima_impressora(impressora)
        return "copy"
    except Exception as e2:
        raise RuntimeError(f"Não foi possível imprimir em “{impressora}”. Direto: {erro_raw}. Cópia: {e2}")
    finally:
        try:
            os.unlink(temp)
        except OSError:
            pass
