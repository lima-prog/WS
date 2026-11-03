"""Junta as partes geradas (molde + CSS + JS + programas) e devolve a página completa do sistema."""
from __future__ import annotations

import re
from pathlib import Path

MARCA = "<!--PPCPM:{}-->"
_RE_MARCA = re.compile(r"<!--PPCPM:([a-z]+)(?::(pg\d+))?-->")

# Ponte Python ⇄ programas (pastas do PC). Só entra quando o Python serve a página.
PONTE_PAGINA = '<script src="/pc/ponte.js"></script>'
PONTE_MODULO = '<script src="/pc/ponte.js"><\\/script>'   # dentro do texto do programa o </script> fica escapado


def _ler(pasta: Path, nome: str) -> str:
    return (pasta / nome).read_text(encoding="utf-8")


def _antes_do_ultimo_body(html: str, trecho: str) -> str:
    i = html.rfind("</body>")
    return html + trecho if i < 0 else html[:i] + trecho + html[i:]


def montar(pasta: Path, com_ponte: bool = False) -> str:
    """Remonta o index.html a partir de ppcpm/gerado/.
    com_ponte=False -> idêntico ao HTML publicado na Vercel.
    com_ponte=True  -> igual, mais a ligação com as pastas do PC em todos os programas."""
    pasta = Path(pasta)
    molde = _ler(pasta, "molde.html")

    def troca(m: re.Match) -> str:
        tipo, pg = m.group(1), m.group(2)
        if tipo == "css":
            return "<style>" + _ler(pasta, "css/sistema.css") + "</style>"
        if tipo == "supabase":
            return "<script>" + _ler(pasta, "js/supabase.js") + "</script>"
        if tipo == "modulo":
            texto = _ler(pasta, f"modulos/{pg}.html")
            if com_ponte:
                texto = _antes_do_ultimo_body(texto, PONTE_MODULO)
            return f'<script type="text/plain" id="src-{pg}">' + texto + "</script>"
        if tipo == "sistema":
            return "<script>" + _ler(pasta, "js/sistema.js") + "</script>"
        raise ValueError("Marcador desconhecido: " + m.group(0))

    html = _RE_MARCA.sub(troca, molde)
    return _antes_do_ultimo_body(html, PONTE_PAGINA) if com_ponte else html
