"""Configuração do sistema, lida do config.json que o gerar_python.py cria a partir do index.html."""
from __future__ import annotations

import json
from pathlib import Path

PASTA_GERADO = Path(__file__).resolve().parent / "gerado"


def carregar() -> dict:
    return json.loads((PASTA_GERADO / "config.json").read_text(encoding="utf-8"))


CONFIG = carregar()
VERSAO: str = CONFIG["versao"]
PACOTE_ATUAL = CONFIG["pacote_atual"]
OBRA_IMPRESSAO = CONFIG["obra_impressao"]
SUPABASE_URL: str = CONFIG["supabase_url"]
SUPABASE_CHAVE_PUBLICA: str = CONFIG["supabase_chave_publica"]
MODULOS: list[dict] = CONFIG["modulos"]
