"""
Configuração do sistema.

- gerado/config.json   -> vem do index.html (versão, pacote atual, obra, menu, Supabase). É relido
                          sozinho quando o atualizador traz uma versão nova, sem precisar reiniciar.
- dados_locais/        -> o que é só deste computador (pastas favoritas, recentes, registro de
                          atualizações). O atualizador NUNCA apaga essa pasta.
"""
from __future__ import annotations

import json
from pathlib import Path

PASTA_APP = Path(__file__).resolve().parent.parent          # pasta onde está o app.py
PASTA_GERADO = Path(__file__).resolve().parent / "gerado"
PASTA_DADOS = PASTA_APP / "dados_locais"
ARQ_VERSAO_PYTHON = PASTA_APP / "versao_python.json"

_cache: dict = {"mtime": None, "dados": {}}


def config() -> dict:
    """Lê o config.json (e relê se mudou no disco)."""
    arq = PASTA_GERADO / "config.json"
    mtime = arq.stat().st_mtime
    if _cache["mtime"] != mtime:
        _cache["dados"] = json.loads(arq.read_text(encoding="utf-8"))
        _cache["mtime"] = mtime
    return _cache["dados"]


def versao_python() -> dict:
    try:
        return json.loads(ARQ_VERSAO_PYTHON.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"pacote": 0}


def versao() -> str:
    return config().get("versao", "")


# Atalhos (valores do momento em que o sistema abriu)
CONFIG = config()
VERSAO: str = CONFIG["versao"]
PACOTE_ATUAL = CONFIG["pacote_atual"]
OBRA_IMPRESSAO = CONFIG["obra_impressao"]
SUPABASE_URL: str = CONFIG["supabase_url"]
SUPABASE_CHAVE_PUBLICA: str = CONFIG["supabase_chave_publica"]
MODULOS: list = CONFIG["modulos"]
