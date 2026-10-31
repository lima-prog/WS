"""Junta as partes geradas (molde + CSS + JS + programas) e devolve a página completa do sistema."""
from __future__ import annotations

import re
from pathlib import Path

MARCA = "<!--PPCPM:{}-->"
_RE_MARCA = re.compile(r"<!--PPCPM:([a-z]+)(?::(pg\d+))?-->")


def _ler(pasta: Path, nome: str) -> str:
    return (pasta / nome).read_text(encoding="utf-8")


def montar(pasta: Path) -> str:
    """Remonta o index.html a partir de ppcpm/gerado/. O resultado é idêntico ao HTML original."""
    pasta = Path(pasta)
    molde = _ler(pasta, "molde.html")

    def troca(m: re.Match) -> str:
        tipo, pg = m.group(1), m.group(2)
        if tipo == "css":
            return "<style>" + _ler(pasta, "css/sistema.css") + "</style>"
        if tipo == "supabase":
            return "<script>" + _ler(pasta, "js/supabase.js") + "</script>"
        if tipo == "modulo":
            return f'<script type="text/plain" id="src-{pg}">' + _ler(pasta, f"modulos/{pg}.html") + "</script>"
        if tipo == "sistema":
            return "<script>" + _ler(pasta, "js/sistema.js") + "</script>"
        raise ValueError("Marcador desconhecido: " + m.group(0))

    return _RE_MARCA.sub(troca, molde)
