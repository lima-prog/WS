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


def reparar_gerado() -> bool:
    """Se a pasta gerado/ sumiu (ou ficou sem config.json) no meio de uma troca de versão,
    traz de volta a mais nova entre gerado_novo* e gerado_velho*. True = gerado/ está ok."""
    import shutil
    if (PASTA_GERADO / "config.json").is_file():
        return True
    candidatas = [c for c in PASTA_GERADO.parent.glob(PASTA_GERADO.name + "_*")
                  if c.is_dir() and (c / "config.json").is_file() and (c / "modulos").is_dir()]
    candidatas.sort(key=lambda c: (c / "config.json").stat().st_mtime, reverse=True)
    for c in candidatas:
        try:
            if not PASTA_GERADO.exists():
                c.rename(PASTA_GERADO)
            else:
                shutil.copytree(c, PASTA_GERADO, dirs_exist_ok=True)
            if (PASTA_GERADO / "config.json").is_file():
                return True
        except OSError:
            try:
                shutil.copytree(c, PASTA_GERADO, dirs_exist_ok=True)
                if (PASTA_GERADO / "config.json").is_file():
                    return True
            except OSError:
                continue
    return False


def config() -> dict:
    """Lê o config.json (e relê se mudou no disco)."""
    arq = PASTA_GERADO / "config.json"
    if not arq.is_file():
        if not reparar_gerado() and _cache["dados"]:
            return _cache["dados"]          # segue com a versão que já estava carregada
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
reparar_gerado()
CONFIG = config()
VERSAO: str = CONFIG["versao"]
PACOTE_ATUAL = CONFIG["pacote_atual"]
OBRA_IMPRESSAO = CONFIG["obra_impressao"]
SUPABASE_URL: str = CONFIG["supabase_url"]
SUPABASE_CHAVE_PUBLICA: str = CONFIG["supabase_chave_publica"]
MODULOS: list = CONFIG["modulos"]
